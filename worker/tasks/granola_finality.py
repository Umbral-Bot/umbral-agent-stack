"""
Granola transcript finality / stability / reconciliation helpers.

These helpers are pure utilities used by ``worker.tasks.granola`` to decide whether
a raw transcript ingest should:

- proceed normally (first-time ingest, new or updated content)
- defer (content looks fresh in Granola and still inside the stability window,
  so it is likely still being transcribed)
- reconcile an existing raw page (same ``granola_document_id`` but new or more
  complete content, e.g. the real "partial -> complete" case observed with
  "Comgrap Dynamo" where Notion AI detected the page ended mid-sentence)
- noop (everything is already up to date)

They also provide a small truncation detector that flags transcripts likely
cut mid-sentence so we never capitalize unfinished content.

Everything here is deterministic, side-effect-free, and independent from
Notion/Granola network calls so it is cheap to unit-test.
"""

from __future__ import annotations

import hashlib
import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Default window during which a freshly-updated Granola document is treated as
# still being transcribed and should not be capitalized yet.
DEFAULT_STABILITY_WINDOW_SECONDS = 15 * 60  # 15 minutes

# Minimum transcript length before we even consider "finality" — anything below
# this is almost surely still being captured.
DEFAULT_MIN_STABLE_CHARS = 200

# Chars that look like a reasonable sentence/paragraph ending; anything else
# at the tail of the transcript is considered suspicious for truncation.
_SENTENCE_END_CHARS = set(".!?…")
_QUOTE_CLOSERS = set('"”»\')]}')

# Suffix tokens that are almost always truncation markers.
_TRUNCATION_SUFFIX_MARKERS = (
    ",",
    ";",
    ":",
    "-",
    "—",
    "–",
)


# ---------------------------------------------------------------------------
# Env helpers
# ---------------------------------------------------------------------------


def stability_window_seconds(override: Any = None) -> int:
    """Resolve the configured stability window in seconds.

    Precedence:
        1. explicit override argument (non-None)
        2. ``GRANOLA_STABILITY_WINDOW_SECONDS`` env var
        3. ``DEFAULT_STABILITY_WINDOW_SECONDS``
    """
    if override is not None:
        try:
            value = int(override)
            return max(0, value)
        except (TypeError, ValueError):
            pass
    raw = str(os.environ.get("GRANOLA_STABILITY_WINDOW_SECONDS") or "").strip()
    if raw:
        try:
            return max(0, int(raw))
        except ValueError:
            return DEFAULT_STABILITY_WINDOW_SECONDS
    return DEFAULT_STABILITY_WINDOW_SECONDS


def min_stable_chars(override: Any = None) -> int:
    if override is not None:
        try:
            return max(0, int(override))
        except (TypeError, ValueError):
            pass
    raw = str(os.environ.get("GRANOLA_MIN_STABLE_CHARS") or "").strip()
    if raw:
        try:
            return max(0, int(raw))
        except ValueError:
            return DEFAULT_MIN_STABLE_CHARS
    return DEFAULT_MIN_STABLE_CHARS


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TranscriptMetrics:
    """Deterministic fingerprint of a transcript payload."""

    char_count: int
    segment_count: int
    content_hash: str
    last_chars: str
    normalized_last_chars: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "char_count": self.char_count,
            "segment_count": self.segment_count,
            "content_hash": self.content_hash,
            "last_chars": self.last_chars,
        }


def compute_transcript_metrics(content: str) -> TranscriptMetrics:
    """Compute ``char_count``, ``segment_count`` and ``content_hash`` for a transcript.

    ``segment_count`` is a best-effort count of speaker-tagged turns or action-item
    bullets — it captures the number of dialog segments we can see in the body.
    Fallback: non-empty lines if no explicit segment markers are present.
    """
    text = content or ""
    char_count = len(text)

    # Prefer bullet-tagged speaker turns (the format emitted by the exporter).
    speaker_bullets = re.findall(r"^\s*-\s+\*\*[^*]+\*\*:\s*", text, flags=re.MULTILINE)
    if speaker_bullets:
        segment_count = len(speaker_bullets)
    else:
        # Fallback: markdown bullets or newline-separated non-empty lines.
        bullets = re.findall(r"^\s*[-*]\s+", text, flags=re.MULTILINE)
        if bullets:
            segment_count = len(bullets)
        else:
            segment_count = sum(1 for line in text.splitlines() if line.strip())

    content_hash = hashlib.sha1(text.encode("utf-8", errors="replace")).hexdigest()
    # Keep tail short but meaningful — enough to carry the real sentence end.
    tail = text[-200:].strip()
    normalized_tail = _normalize_tail(tail)
    return TranscriptMetrics(
        char_count=char_count,
        segment_count=segment_count,
        content_hash=content_hash,
        last_chars=tail,
        normalized_last_chars=normalized_tail,
    )


def _normalize_tail(tail: str) -> str:
    text = unicodedata.normalize("NFKD", tail or "").strip()
    return text


# ---------------------------------------------------------------------------
# Truncation detector
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TruncationReport:
    truncated: bool
    reason: str
    last_chars: str
    tail_terminator: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "truncated": self.truncated,
            "reason": self.reason,
            "last_chars": self.last_chars,
            "tail_terminator": self.tail_terminator,
        }


def detect_truncation(
    content: str,
    *,
    min_chars: int | None = None,
    min_chars_for_tail_check: int = 120,
) -> TruncationReport:
    """Flag transcripts that likely ended mid-sentence.

    The real Comgrap Dynamo case ended in:
        "... De hecho, lo lo planteé a la señora,"
    — notice the trailing comma after "señora,". That kind of tail is what we
    catch here: transcripts whose last non-whitespace character is a comma,
    semicolon, dash or quote-opener are almost surely cut mid-phrase.

    Heuristics applied (in order):
        1. empty / too-short transcripts -> truncated=True
        2. last non-whitespace char is a comma / semicolon / colon / dash -> truncated
        3. last sentence has fewer than ~3 tokens and no terminator -> truncated
        4. otherwise -> not truncated
    """
    text = (content or "").rstrip()
    effective_min = min_chars if min_chars is not None else min_stable_chars()

    if not text:
        return TruncationReport(
            truncated=True,
            reason="empty_content",
            last_chars="",
        )

    if len(text) < max(1, effective_min):
        return TruncationReport(
            truncated=True,
            reason=f"content_too_short (<{effective_min})",
            last_chars=text[-80:],
        )

    last_chars = text[-200:]
    last_char = text[-1]

    if last_char in _TRUNCATION_SUFFIX_MARKERS:
        return TruncationReport(
            truncated=True,
            reason=f"tail_ends_with_marker:{last_char!r}",
            last_chars=last_chars,
            tail_terminator=last_char,
        )

    if last_char in _SENTENCE_END_CHARS:
        return TruncationReport(
            truncated=False,
            reason="",
            last_chars=last_chars,
            tail_terminator=last_char,
        )

    if last_char in _QUOTE_CLOSERS and len(text) >= 2 and text[-2] in _SENTENCE_END_CHARS:
        return TruncationReport(
            truncated=False,
            reason="",
            last_chars=last_chars,
            tail_terminator=text[-2],
        )

    if len(text) < min_chars_for_tail_check:
        return TruncationReport(
            truncated=True,
            reason=f"tail_unterminated_and_short (<{min_chars_for_tail_check})",
            last_chars=last_chars,
            tail_terminator="",
        )

    # Last fallback: look back for the last sentence terminator. If the final
    # fragment after it is short, assume the sentence was cut.
    tail_fragment = _last_sentence_fragment(text)
    if tail_fragment is not None and len(tail_fragment.split()) < 4:
        return TruncationReport(
            truncated=True,
            reason="tail_fragment_too_short_after_last_terminator",
            last_chars=last_chars,
            tail_terminator="",
        )

    return TruncationReport(
        truncated=False,
        reason="",
        last_chars=last_chars,
        tail_terminator="",
    )


def _last_sentence_fragment(text: str) -> str | None:
    for i in range(len(text) - 1, -1, -1):
        ch = text[i]
        if ch in _SENTENCE_END_CHARS:
            return text[i + 1 :].strip()
    return None


# ---------------------------------------------------------------------------
# Reconciliation decision
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReconciliationDecision:
    """Represents the decision taken for a given transcript ingest call."""

    action: str  # one of: create, reconcile, noop, defer
    reason: str
    stability_wait_seconds: int = 0
    truncation: TruncationReport | None = None
    previous_metrics: Dict[str, Any] | None = None
    new_metrics: Dict[str, Any] | None = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "reason": self.reason,
            "stability_wait_seconds": self.stability_wait_seconds,
            "truncation": self.truncation.as_dict() if self.truncation else None,
            "previous_metrics": self.previous_metrics,
            "new_metrics": self.new_metrics,
        }


def parse_iso_datetime(value: Any) -> Optional[datetime]:
    """Parse an ISO-8601 datetime (tolerates trailing ``Z`` and missing tz)."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    raw_norm = raw.rstrip().replace("Z", "+00:00")
    # Some feeds use "+0000" without colon; fromisoformat rejects that.
    raw_norm = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", raw_norm)
    try:
        dt = datetime.fromisoformat(raw_norm)
    except ValueError:
        # Try a couple of looser formats before giving up.
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(raw, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _parse_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def compare_metrics(
    previous: Dict[str, Any] | None,
    new: TranscriptMetrics,
) -> Tuple[bool, str]:
    """Return ``(changed, reason)`` for a previous vs. new metrics tuple.

    Treats any change in hash / char_count / segment_count as a real change.
    Growth is preferred (reconcile); shrinkage is still flagged but tagged so
    operators notice. Returns ``(False, "")`` when nothing changed.
    """
    if not previous:
        return True, "no_previous_metrics"

    prev_hash = str(previous.get("content_hash") or "").strip()
    prev_char = _parse_int(previous.get("char_count"))
    prev_seg = _parse_int(previous.get("segment_count"))

    if prev_hash and prev_hash == new.content_hash and prev_char == new.char_count:
        return False, "identical_hash_and_char_count"

    reasons: list[str] = []
    if prev_hash and prev_hash != new.content_hash:
        reasons.append("content_hash_changed")
    if prev_char and new.char_count > prev_char:
        reasons.append(f"char_count_grew({prev_char}->{new.char_count})")
    elif prev_char and new.char_count < prev_char:
        reasons.append(f"char_count_shrunk({prev_char}->{new.char_count})")
    if prev_seg and new.segment_count > prev_seg:
        reasons.append(f"segment_count_grew({prev_seg}->{new.segment_count})")
    elif prev_seg and new.segment_count < prev_seg:
        reasons.append(f"segment_count_shrunk({prev_seg}->{new.segment_count})")

    if not reasons:
        reasons.append("metrics_differ")
    return True, "|".join(reasons)


def decide_reconciliation(
    *,
    existing: Dict[str, Any] | None,
    new_content: str,
    source_updated_at: str,
    now: datetime | None = None,
    stability_window: int | None = None,
    min_chars: int | None = None,
    force_reconcile: bool = False,
) -> ReconciliationDecision:
    """Decide which action to take for a given incoming transcript.

    ``existing`` is the dict returned by ``_build_existing_raw_candidate`` (or
    ``None`` if no match was found). The decision encodes one of:

        - ``create``    — no existing page, proceed with create
        - ``reconcile`` — existing page, new content differs (or force), update it
        - ``noop``      — existing page identical, no write needed
        - ``defer``     — fresh transcript still inside the stability window,
                          skip now and let a later run pick it up

    The ``defer`` action only fires for first-time ingests (no existing page) so
    we never hold back an *update* that is already known to be more complete
    than what is on Notion. Reconciliation always wins over stability.
    """
    now = now or datetime.now(timezone.utc)
    window = stability_window if stability_window is not None else stability_window_seconds()
    effective_min = min_chars if min_chars is not None else min_stable_chars()

    new_metrics = compute_transcript_metrics(new_content)
    truncation = detect_truncation(new_content, min_chars=effective_min)

    previous_metrics = None
    if existing:
        previous_metrics = {
            "char_count": _parse_int(existing.get("char_count")),
            "segment_count": _parse_int(existing.get("segment_count")),
            "content_hash": str(existing.get("content_hash") or "").strip(),
            "source_updated_at": str(existing.get("source_updated_at") or "").strip(),
            "truncation_detected": bool(existing.get("truncation_detected")),
        }

    if force_reconcile and existing:
        return ReconciliationDecision(
            action="reconcile",
            reason="force_reconcile",
            truncation=truncation,
            previous_metrics=previous_metrics,
            new_metrics=new_metrics.as_dict(),
        )

    if existing is None:
        source_dt = parse_iso_datetime(source_updated_at)
        if window > 0 and source_dt is not None:
            age_seconds = int((now - source_dt).total_seconds())
            if age_seconds < window:
                return ReconciliationDecision(
                    action="defer",
                    reason=(
                        f"source_updated_at too recent: age={age_seconds}s < "
                        f"stability_window={window}s"
                    ),
                    stability_wait_seconds=max(0, window - age_seconds),
                    truncation=truncation,
                    previous_metrics=None,
                    new_metrics=new_metrics.as_dict(),
                )
        if truncation.truncated and window > 0 and source_dt is None:
            # No timestamp but content looks cut mid-sentence: still proceed
            # with create (so we don't lose evidence), but flag it.
            return ReconciliationDecision(
                action="create",
                reason="truncation_suspected_no_source_timestamp",
                truncation=truncation,
                previous_metrics=None,
                new_metrics=new_metrics.as_dict(),
            )
        return ReconciliationDecision(
            action="create",
            reason="no_existing_page",
            truncation=truncation,
            previous_metrics=None,
            new_metrics=new_metrics.as_dict(),
        )

    changed, change_reason = compare_metrics(previous_metrics, new_metrics)

    # Source timestamp signal — newer source_updated_at always wins, even when
    # the hash column is empty on the legacy row.
    prev_source_ts = parse_iso_datetime(
        (previous_metrics or {}).get("source_updated_at")
    )
    new_source_ts = parse_iso_datetime(source_updated_at)
    if new_source_ts and prev_source_ts and new_source_ts > prev_source_ts:
        changed = True
        change_reason = f"source_updated_at_newer({prev_source_ts.isoformat()}->{new_source_ts.isoformat()})"

    # If the existing page was flagged as truncated and the new payload is no
    # longer truncated, reconcile even if raw metrics look similar.
    if (
        previous_metrics
        and previous_metrics.get("truncation_detected")
        and not truncation.truncated
    ):
        changed = True
        change_reason = (change_reason + "|" if changed else "") + "recovered_from_truncation"

    if not changed:
        return ReconciliationDecision(
            action="noop",
            reason=change_reason or "metrics_identical",
            truncation=truncation,
            previous_metrics=previous_metrics,
            new_metrics=new_metrics.as_dict(),
        )

    return ReconciliationDecision(
        action="reconcile",
        reason=change_reason,
        truncation=truncation,
        previous_metrics=previous_metrics,
        new_metrics=new_metrics.as_dict(),
    )


__all__ = [
    "DEFAULT_STABILITY_WINDOW_SECONDS",
    "DEFAULT_MIN_STABLE_CHARS",
    "TranscriptMetrics",
    "TruncationReport",
    "ReconciliationDecision",
    "compute_transcript_metrics",
    "detect_truncation",
    "compare_metrics",
    "decide_reconciliation",
    "parse_iso_datetime",
    "stability_window_seconds",
    "min_stable_chars",
]
