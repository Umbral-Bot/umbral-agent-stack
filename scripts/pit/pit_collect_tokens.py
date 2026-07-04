#!/usr/bin/env python3
"""Read-only token-ledger collector for a PIT tournament (PIT-P6).

Aggregates, per lane, the token usage that two independent subsystems already
record on disk and emits a single ``token_ledger.yaml``:

* **OpenClaw lane sessions** — ``<openclaw_root>/agents/<pit_id>-lane-*/``.
  The canonical store is ``sessions/sessions.json`` (a dict of sessions with
  camelCase ``inputTokens`` / ``outputTokens`` / ``totalTokens`` / ``cacheRead``,
  the same shape consumed by ``scripts/openclaw_runtime_snapshot.py``). Any
  ``sessions/*.jsonl`` transcripts are also scanned for usage as a fallback.

* **Copilot CLI broker audit** — ``<audit_root>/**/<mission_run_id>.jsonl``
  (P4 contract). Events are filtered by ``metadata.pit_id`` and bucketed by
  ``lane_id``; we count calls (dry-run vs real), an exit-code histogram and
  duration. GitHub Copilot CLI does not surface token counts, so the per-lane
  ``tokens`` block degrades to ``source: not_reported_by_github_copilot_cli``
  unless a future audit event carries a populated ``tokens`` object.

The collector is strictly read-only against runtime state: it never mutates
OpenClaw/broker files, never prints secrets/PAT material (only numeric usage,
model names and correlation ids are read), and tolerates missing files by
emitting warnings instead of crashing. The only writes are the ledger YAML
itself and — with ``--update-outcome`` — the ``budget`` block of
``pit/<pit_id>/outcome/pit_outcome_report.yaml`` (billing truth, quality gate
post ``pit-dev-ifc-viewer``: a PIT-DEV tournament must not close "green"
while reporting ``tokens_total: not_reported``).

USD estimation (documented formula)
-----------------------------------
``usd = (input*rate_in + cache_read*rate_cache + output*rate_out) / 1e6``

Rates are USD per 1M tokens. The default table is a conservative
GPT-5.x-class blend (``pricing_source: default_gpt5_class_per_mtok_v1``);
override per run with ``--usd-per-mtok-input/--usd-per-mtok-cache-read/
--usd-per-mtok-output`` (``pricing_source: cli_override``). This is an
*estimate from tokens*, not provider billing — the ledger and the outcome
record ``pricing_source`` so nobody confuses it with an invoice.

Exit codes
----------
``0``  collector ran and wrote the YAML (warnings allowed).
``2``  ``pit_id`` is invalid, or the output/outcome could not be written.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:  # PyYAML is a project dependency; degrade with a clear message if absent.
    import yaml
except ImportError:  # pragma: no cover - exercised only without the dep
    yaml = None  # type: ignore[assignment]

PIT_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
NOT_REPORTED = "not_reported_by_github_copilot_cli"

# Billing truth (post pit-dev-ifc-viewer): value written to the outcome when
# the collector finds NO token data at all. The PIT-DEV deliver gate fails
# closed on it — better an honest "not_reported" than a fake 0.
TOKENS_NOT_REPORTED = "not_reported"

# USD per 1M tokens — conservative GPT-5.x-class blend (documented formula in
# the module docstring). Override via CLI flags; pricing_source records which
# table produced the estimate.
DEFAULT_PRICING_PER_MTOK: Dict[str, float] = {
    "input": 1.25,
    "cache_read": 0.125,
    "output": 10.0,
}
DEFAULT_PRICING_SOURCE = "default_gpt5_class_per_mtok_v1"
CLI_PRICING_SOURCE = "cli_override"

# Audit decisions that mean the broker actually executed against Docker (a
# "real" call) rather than a gated / dry-run no-op.
REAL_DECISIONS = frozenset({"execute_started", "completed", "secret_pattern_redacted"})

DEFAULT_OPENCLAW_ROOT = "~/.openclaw"
DEFAULT_VAULT_ROOT = "~/umbral-pit-vault"
DEFAULT_AUDIT_ROOT = "reports/copilot-cli"


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_int(value: Any) -> int:
    try:
        if isinstance(value, bool):
            return 0
        return int(value)
    except (TypeError, ValueError):
        return 0


def validate_pit_id(pit_id: str) -> bool:
    return bool(pit_id) and bool(PIT_ID_RE.match(pit_id))


def lane_from_agent_dir(name: str, pit_id: str) -> Optional[str]:
    """Map an OpenClaw agent directory name to a lane id.

    The canonical on-disk convention is ``<pit_id>-lane-<slug>`` where the
    ``pit_id`` already carries its ``pit-`` prefix, e.g.
    ``pit-umbral-bim2-sharepoint-acc-lane-foundry-tools`` -> ``lane-foundry-tools``.
    A directory named exactly ``<pit_id>`` maps to the synthetic ``_pit_root``
    lane. When the ``pit_id`` does not already start with ``pit-`` we also
    tolerate the documented ``pit-<pit_id>`` form. Returns ``None`` when the
    directory does not belong to this tournament.
    """

    bases = [pit_id]
    if not pit_id.startswith("pit-"):
        bases.append(f"pit-{pit_id}")
    for base in bases:
        if name == base:
            return "_pit_root"
        prefix = f"{base}-"
        if name.startswith(prefix):
            return name[len(prefix):] or "_pit_root"
    return None


def _empty_openclaw() -> Dict[str, Any]:
    return {
        "input": 0,
        "output": 0,
        "cache_read": 0,
        "total": 0,
        "model": None,
        "sessions": 0,
        "events": 0,
    }


def _empty_copilot() -> Dict[str, Any]:
    return {
        "calls": 0,
        "dry_run": 0,
        "real": 0,
        "exit_codes": {},
        "duration_sec": {"sum": 0.0, "avg": None},
        "tokens": {"source": NOT_REPORTED},
    }


# ---------------------------------------------------------------------------
# Usage extraction (tolerant to several provider shapes)
# ---------------------------------------------------------------------------
def extract_session_usage(item: Dict[str, Any]) -> Dict[str, Any]:
    """Pull token usage from one ``sessions.json`` entry (camelCase + fallbacks)."""

    usage = item.get("usage") if isinstance(item.get("usage"), dict) else {}

    def pick(*keys: str) -> int:
        for source in (item, usage):
            for key in keys:
                if key in source and source[key] is not None:
                    return _safe_int(source[key])
        return 0

    input_tokens = pick("inputTokens", "input_tokens", "prompt_tokens", "input")
    output_tokens = pick("outputTokens", "output_tokens", "completion_tokens", "output")
    total_tokens = pick("totalTokens", "total_tokens", "total")
    cache_read = pick(
        "cacheRead", "cache_read", "cache_read_input_tokens", "cacheReadInputTokens"
    )
    if total_tokens == 0:
        total_tokens = input_tokens + output_tokens
    model = item.get("model") or usage.get("model")
    return {
        "input": input_tokens,
        "output": output_tokens,
        "total": total_tokens,
        "cache_read": cache_read,
        "model": str(model) if model else None,
    }


def extract_jsonl_usage(event: Dict[str, Any]) -> Dict[str, Any]:
    """Pull token usage from a single JSONL session event, if any."""

    usage = event.get("usage")
    if not isinstance(usage, dict):
        message = event.get("message")
        if isinstance(message, dict) and isinstance(message.get("usage"), dict):
            usage = message["usage"]
        else:
            usage = {}
    merged = {**event, **usage}

    def pick(*keys: str) -> int:
        for key in keys:
            if key in merged and merged[key] is not None:
                return _safe_int(merged[key])
        return 0

    input_tokens = pick("inputTokens", "input_tokens", "prompt_tokens")
    output_tokens = pick("outputTokens", "output_tokens", "completion_tokens")
    total_tokens = pick("totalTokens", "total_tokens")
    cache_read = pick(
        "cacheRead", "cache_read", "cache_read_input_tokens", "cacheReadInputTokens"
    )
    if total_tokens == 0:
        total_tokens = input_tokens + output_tokens
    model = merged.get("model") or (
        event.get("message", {}).get("model") if isinstance(event.get("message"), dict) else None
    )
    return {
        "input": input_tokens,
        "output": output_tokens,
        "total": total_tokens,
        "cache_read": cache_read,
        "model": str(model) if model else None,
    }


# ---------------------------------------------------------------------------
# OpenClaw collection
# ---------------------------------------------------------------------------
def collect_openclaw(
    openclaw_root: Path, pit_id: str
) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    warnings: List[str] = []
    lanes: Dict[str, Dict[str, Any]] = defaultdict(_empty_openclaw)
    model_weight: Dict[str, Counter] = defaultdict(Counter)

    agents_dir = openclaw_root / "agents"
    if not agents_dir.exists():
        # Tolerate ``--openclaw-root`` pointed straight at the agents directory.
        agents_dir = openclaw_root
    if not agents_dir.exists():
        warnings.append(f"openclaw agents dir missing: {agents_dir}")
        return {}, warnings

    matched_any = False
    for agent_dir in sorted(p for p in agents_dir.iterdir() if p.is_dir()):
        lane = lane_from_agent_dir(agent_dir.name, pit_id)
        if lane is None:
            continue
        matched_any = True
        bucket = lanes[lane]
        sessions_dir = agent_dir / "sessions"

        sessions_json = sessions_dir / "sessions.json"
        if sessions_json.exists():
            try:
                payload = json.loads(sessions_json.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                warnings.append(f"unreadable {sessions_json.name} in {agent_dir.name}: {exc.__class__.__name__}")
                payload = None
            if isinstance(payload, dict):
                for item in payload.values():
                    if not isinstance(item, dict):
                        continue
                    usage = extract_session_usage(item)
                    bucket["input"] += usage["input"]
                    bucket["output"] += usage["output"]
                    bucket["total"] += usage["total"]
                    bucket["cache_read"] += usage["cache_read"]
                    bucket["sessions"] += 1
                    if usage["model"]:
                        model_weight[lane][usage["model"]] += usage["total"] or 1

        if sessions_dir.exists():
            for jsonl_path in sorted(sessions_dir.glob("*.jsonl")):
                file_had_event = False
                try:
                    with jsonl_path.open("r", encoding="utf-8") as handle:
                        for line in handle:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                event = json.loads(line)
                            except json.JSONDecodeError:
                                continue
                            if not isinstance(event, dict):
                                continue
                            file_had_event = True
                            bucket["events"] += 1
                            usage = extract_jsonl_usage(event)
                            bucket["input"] += usage["input"]
                            bucket["output"] += usage["output"]
                            bucket["total"] += usage["total"]
                            bucket["cache_read"] += usage["cache_read"]
                            if usage["model"]:
                                model_weight[lane][usage["model"]] += usage["total"] or 1
                except OSError as exc:
                    warnings.append(f"unreadable session jsonl {jsonl_path.name}: {exc.__class__.__name__}")
                    continue
                if file_had_event:
                    bucket["sessions"] += 1

    if not matched_any:
        warnings.append(f"no openclaw lane agents matched {pit_id}-* under {agents_dir}")

    for lane, counter in model_weight.items():
        if counter:
            lanes[lane]["model"] = counter.most_common(1)[0][0]

    return dict(lanes), warnings


# ---------------------------------------------------------------------------
# Copilot CLI audit collection
# ---------------------------------------------------------------------------
def collect_copilot_cli(
    audit_root: Path, pit_id: str
) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    warnings: List[str] = []
    if not audit_root.exists():
        warnings.append(f"copilot-cli audit root missing: {audit_root}")
        return {}, warnings

    # Per-lane, per-run accumulation so a call is counted once even though its
    # JSONL file holds several phase events.
    lane_runs: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(
        lambda: defaultdict(lambda: {"executed": False, "exit_codes": [], "durations": [], "tokens": []})
    )

    matched_files = 0
    for jsonl_path in sorted(audit_root.rglob("*.jsonl")):
        try:
            with jsonl_path.open("r", encoding="utf-8") as handle:
                lines = handle.readlines()
        except OSError as exc:
            warnings.append(f"unreadable audit {jsonl_path.name}: {exc.__class__.__name__}")
            continue
        file_matched = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict) or event.get("pit_id") != pit_id:
                continue
            file_matched = True
            lane = event.get("lane_id") or "_no_lane"
            run_id = event.get("mission_run_id") or jsonl_path.stem
            run = lane_runs[lane][run_id]
            if "exit_code" in event and event["exit_code"] is not None:
                run["exit_codes"].append(_safe_int(event["exit_code"]))
            if event.get("decision") in REAL_DECISIONS or ("exit_code" in event):
                run["executed"] = True
            duration = event.get("duration_sec")
            if isinstance(duration, (int, float)) and not isinstance(duration, bool):
                run["durations"].append(float(duration))
            tokens = event.get("tokens")
            if isinstance(tokens, dict):
                run["tokens"].append(tokens)
        if file_matched:
            matched_files += 1

    if matched_files == 0:
        warnings.append(f"no copilot-cli audit events matched pit_id={pit_id} under {audit_root}")

    lanes: Dict[str, Dict[str, Any]] = {}
    for lane, runs in lane_runs.items():
        bucket = _empty_copilot()
        exit_hist: Counter = Counter()
        durations: List[float] = []
        token_input = token_output = token_total = 0
        token_seen = False
        for run in runs.values():
            bucket["calls"] += 1
            if run["executed"]:
                bucket["real"] += 1
            else:
                bucket["dry_run"] += 1
            for code in run["exit_codes"]:
                exit_hist[str(code)] += 1
            durations.extend(run["durations"])
            for tok in run["tokens"]:
                ti, to, tt = tok.get("input"), tok.get("output"), tok.get("total")
                if any(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (ti, to, tt)):
                    token_seen = True
                    token_input += _safe_int(ti)
                    token_output += _safe_int(to)
                    token_total += _safe_int(tt)
        bucket["exit_codes"] = dict(sorted(exit_hist.items()))
        if durations:
            total = round(sum(durations), 3)
            bucket["duration_sec"] = {"sum": total, "avg": round(total / len(durations), 3)}
        if token_seen:
            if token_total == 0:
                token_total = token_input + token_output
            bucket["tokens"] = {
                "input": token_input,
                "output": token_output,
                "total": token_total,
                "source": "copilot_cli_audit",
            }
        lanes[lane] = bucket

    return lanes, warnings


# ---------------------------------------------------------------------------
# Budget (best-effort, optional)
# ---------------------------------------------------------------------------
def load_lane_budgets(vault_root: Path, pit_id: str) -> Dict[str, Optional[float]]:
    """Best-effort per-lane allocated budget from the vault pit_spec.

    Returns an empty dict on any problem (missing spec, unparseable, no budget).
    Never raises.
    """

    if yaml is None:
        return {}
    spec_path = vault_root / "pit" / pit_id / "spec" / "pit_spec.yaml"
    if not spec_path.exists():
        return {}
    try:
        raw = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    if not isinstance(raw, dict):
        return {}
    lanes = raw.get("lanes")
    if not isinstance(lanes, list) or not lanes:
        return {}

    total_budget = raw.get("budget_usd_total")
    even_share: Optional[float] = None
    if isinstance(total_budget, (int, float)) and not isinstance(total_budget, bool):
        even_share = round(float(total_budget) / len(lanes), 4)

    out: Dict[str, Optional[float]] = {}
    for lane in lanes:
        if not isinstance(lane, dict):
            continue
        lane_id = lane.get("lane_id") or lane.get("id") or lane.get("name")
        if not lane_id:
            continue
        own = lane.get("budget_usd")
        if isinstance(own, (int, float)) and not isinstance(own, bool):
            out[str(lane_id)] = round(float(own), 4)
        elif even_share is not None:
            out[str(lane_id)] = even_share
    return out


# ---------------------------------------------------------------------------
# USD estimation (billing truth)
# ---------------------------------------------------------------------------
def estimate_usd(
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int,
    pricing_per_mtok: Optional[Dict[str, float]] = None,
) -> float:
    """USD estimate from token counts — documented formula (module docstring).

    ``usd = (input*rate_in + cache_read*rate_cache + output*rate_out) / 1e6``.
    Estimation from tokens, NOT provider billing.
    """

    rates = pricing_per_mtok or DEFAULT_PRICING_PER_MTOK
    usd = (
        _safe_int(input_tokens) * float(rates.get("input", 0.0))
        + _safe_int(cache_read_tokens) * float(rates.get("cache_read", 0.0))
        + _safe_int(output_tokens) * float(rates.get("output", 0.0))
    ) / 1_000_000
    return round(usd, 4)


# ---------------------------------------------------------------------------
# Ledger assembly
# ---------------------------------------------------------------------------
def build_ledger(
    pit_id: str,
    openclaw_lanes: Dict[str, Dict[str, Any]],
    copilot_lanes: Dict[str, Dict[str, Any]],
    budgets: Optional[Dict[str, Optional[float]]] = None,
    warnings: Optional[List[str]] = None,
    sources: Optional[Dict[str, Any]] = None,
    pricing_per_mtok: Optional[Dict[str, float]] = None,
    pricing_source: str = DEFAULT_PRICING_SOURCE,
) -> Dict[str, Any]:
    budgets = budgets or {}
    warnings = warnings or []
    pricing = pricing_per_mtok or DEFAULT_PRICING_PER_MTOK
    lane_ids = sorted(set(openclaw_lanes) | set(copilot_lanes) | set(budgets))

    lanes_out: Dict[str, Any] = {}
    openclaw_total = 0
    copilot_calls_total = 0
    total_input = total_output = total_cache = total_tokens = 0
    usd_estimated_total = 0.0
    for lane_id in lane_ids:
        oc = {**_empty_openclaw(), **openclaw_lanes.get(lane_id, {})}
        cc = {**_empty_copilot(), **copilot_lanes.get(lane_id, {})}
        openclaw_total += _safe_int(oc.get("total"))
        copilot_calls_total += _safe_int(cc.get("calls"))

        lane_input = _safe_int(oc.get("input"))
        lane_output = _safe_int(oc.get("output"))
        lane_cache = _safe_int(oc.get("cache_read"))
        lane_total = _safe_int(oc.get("total"))
        cc_tokens = cc.get("tokens") or {}
        if cc_tokens.get("source") != NOT_REPORTED:
            lane_input += _safe_int(cc_tokens.get("input"))
            lane_output += _safe_int(cc_tokens.get("output"))
            lane_total += _safe_int(cc_tokens.get("total"))
        lane_usd = estimate_usd(lane_input, lane_output, lane_cache, pricing)

        total_input += lane_input
        total_output += lane_output
        total_cache += lane_cache
        total_tokens += lane_total
        usd_estimated_total = round(usd_estimated_total + lane_usd, 4)

        lanes_out[lane_id] = {
            "openclaw": oc,
            "copilot_cli": cc,
            "budget_usd_allocated": budgets.get(lane_id),
            "budget_usd_estimated": lane_usd,
        }

    ledger: Dict[str, Any] = {
        "pit_id": pit_id,
        "generated_at_utc": _now_iso(),
        "schema_version": 2,
        "lanes": lanes_out,
        "tournament_total": {
            "openclaw_total": openclaw_total,
            "copilot_cli_calls": copilot_calls_total,
            "tokens": {
                "input": total_input,
                "output": total_output,
                "cache_read": total_cache,
                "total": total_tokens,
            },
            "usd_estimated_total": usd_estimated_total,
            "lanes": len(lanes_out),
            "notes": list(dict.fromkeys(warnings)),
        },
        "pricing": {
            "source": pricing_source,
            "usd_per_mtok": dict(pricing),
            "formula": "usd = (input*rate_in + cache_read*rate_cache + output*rate_out) / 1e6",
        },
    }
    if sources is not None:
        ledger["sources"] = sources
    return ledger


def default_output_path(vault_root: Path, pit_id: str) -> Path:
    return vault_root / "pit" / pit_id / "metrics" / "token_ledger.yaml"


def default_outcome_path(vault_root: Path, pit_id: str) -> Path:
    return vault_root / "pit" / pit_id / "outcome" / "pit_outcome_report.yaml"


def ledger_has_token_data(ledger: Dict[str, Any]) -> bool:
    """True when at least one lane reported real token usage (>0)."""

    total = ledger.get("tournament_total") or {}
    tokens = total.get("tokens") or {}
    return _safe_int(tokens.get("total")) > 0


def update_outcome_budget(
    outcome_path: Path,
    ledger: Dict[str, Any],
    ledger_rel_path: str,
) -> Dict[str, Any]:
    """Populate billing truth in the outcome report ``budget`` block.

    With real token data: ``tokens_total`` (int), ``usd_estimated_spent``
    (documented estimate), ``pricing_source`` and the ``token_ledger`` path.
    Without any token data: ``tokens_total: not_reported`` (honest fail-closed
    marker — the PIT-DEV deliver gate rejects it) and ``usd_estimated_spent``
    is left untouched. ``budget_usd`` (the CEILING David authorised) is never
    modified. Raises ``ValueError`` if the outcome is missing/unparseable.
    """

    if yaml is None:  # pragma: no cover - dependency guaranteed in project
        raise ValueError("pyyaml required to update the outcome report")
    if not outcome_path.is_file():
        raise ValueError(f"outcome_missing:{outcome_path}")
    try:
        raw = yaml.safe_load(outcome_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"outcome_unparseable:{exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"outcome_not_a_mapping:{outcome_path}")

    budget = raw.get("budget")
    if not isinstance(budget, dict):
        budget = {}
        raw["budget"] = budget

    total = ledger.get("tournament_total") or {}
    tokens = total.get("tokens") or {}
    pricing = ledger.get("pricing") or {}
    if ledger_has_token_data(ledger):
        budget["tokens_total"] = _safe_int(tokens.get("total"))
        budget["tokens_input"] = _safe_int(tokens.get("input"))
        budget["tokens_output"] = _safe_int(tokens.get("output"))
        budget["tokens_cache_read"] = _safe_int(tokens.get("cache_read"))
        budget["usd_estimated_spent"] = float(total.get("usd_estimated_total") or 0.0)
        budget["pricing_source"] = str(pricing.get("source") or DEFAULT_PRICING_SOURCE)
    else:
        # Honest marker: no data is NOT zero spend. usd_estimated_spent stays.
        budget["tokens_total"] = TOKENS_NOT_REPORTED
        budget["pricing_source"] = str(pricing.get("source") or DEFAULT_PRICING_SOURCE)
    budget["token_ledger"] = ledger_rel_path

    outcome_path.write_text(
        yaml.safe_dump(raw, sort_keys=False, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )
    return budget


def dump_yaml(data: Dict[str, Any]) -> str:
    if yaml is None:  # pragma: no cover - dependency guaranteed in project
        return json.dumps(data, indent=2, ensure_ascii=False)
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pit_collect_tokens",
        description="Read-only token ledger collector for a PIT tournament (P6).",
    )
    parser.add_argument("--pit-id", required=True, help="Tournament id (^[A-Za-z0-9._-]{1,64}$).")
    parser.add_argument("--vault-root", default=DEFAULT_VAULT_ROOT, help="PIT vault root.")
    parser.add_argument("--openclaw-root", default=DEFAULT_OPENCLAW_ROOT, help="OpenClaw root (expects an agents/ subdir).")
    parser.add_argument("--audit-root", default=DEFAULT_AUDIT_ROOT, help="Copilot CLI audit root.")
    parser.add_argument("--output", default=None, help="Output YAML path (default: <vault>/pit/<pit_id>/metrics/token_ledger.yaml).")
    parser.add_argument("--stdout", action="store_true", help="Also print the ledger YAML to stdout.")
    parser.add_argument(
        "--update-outcome",
        action="store_true",
        help="Populate budget.tokens_total / usd_estimated_spent / pricing_source in "
        "pit/<pit_id>/outcome/pit_outcome_report.yaml (billing truth; PIT-DEV deliver gate).",
    )
    parser.add_argument("--usd-per-mtok-input", type=float, default=None,
                        help=f"Override input rate (USD per 1M tokens; default {DEFAULT_PRICING_PER_MTOK['input']}).")
    parser.add_argument("--usd-per-mtok-cache-read", type=float, default=None,
                        help=f"Override cache-read rate (default {DEFAULT_PRICING_PER_MTOK['cache_read']}).")
    parser.add_argument("--usd-per-mtok-output", type=float, default=None,
                        help=f"Override output rate (default {DEFAULT_PRICING_PER_MTOK['output']}).")
    return parser


def resolve_pricing(args: argparse.Namespace) -> Tuple[Dict[str, float], str]:
    """Rate table + pricing_source from CLI overrides (default: documented blend)."""

    overrides = {
        "input": args.usd_per_mtok_input,
        "cache_read": args.usd_per_mtok_cache_read,
        "output": args.usd_per_mtok_output,
    }
    if all(value is None for value in overrides.values()):
        return dict(DEFAULT_PRICING_PER_MTOK), DEFAULT_PRICING_SOURCE
    pricing = dict(DEFAULT_PRICING_PER_MTOK)
    for key, value in overrides.items():
        if value is not None:
            pricing[key] = float(value)
    return pricing, CLI_PRICING_SOURCE


def run(args: argparse.Namespace) -> int:
    pit_id = str(args.pit_id)
    if not validate_pit_id(pit_id):
        print(f"error: invalid_pit_id:{pit_id!r} must match ^[A-Za-z0-9._-]{{1,64}}$", file=sys.stderr)
        return 2

    vault_root = Path(args.vault_root).expanduser()
    openclaw_root = Path(args.openclaw_root).expanduser()
    audit_root = Path(args.audit_root).expanduser()
    pricing, pricing_source = resolve_pricing(args)

    warnings: List[str] = []
    openclaw_lanes, oc_warn = collect_openclaw(openclaw_root, pit_id)
    warnings.extend(oc_warn)
    copilot_lanes, cc_warn = collect_copilot_cli(audit_root, pit_id)
    warnings.extend(cc_warn)
    budgets = load_lane_budgets(vault_root, pit_id)

    sources = {
        "openclaw_root": str(openclaw_root),
        "openclaw_found": (openclaw_root / "agents").exists() or openclaw_root.exists(),
        "audit_root": str(audit_root),
        "audit_found": audit_root.exists(),
        "vault_root": str(vault_root),
        "vault_found": vault_root.exists(),
    }

    ledger = build_ledger(
        pit_id,
        openclaw_lanes,
        copilot_lanes,
        budgets,
        warnings=warnings,
        sources=sources,
        pricing_per_mtok=pricing,
        pricing_source=pricing_source,
    )

    output_path = Path(args.output).expanduser() if args.output else default_output_path(vault_root, pit_id)
    text = dump_yaml(ledger)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot write output {output_path}: {exc}", file=sys.stderr)
        return 2

    total = ledger["tournament_total"]
    print(f"# pit token ledger -> {output_path}")
    print(f"# lanes={len(ledger['lanes'])} openclaw_total={total['openclaw_total']} "
          f"copilot_cli_calls={total['copilot_cli_calls']} "
          f"usd_estimated_total={total['usd_estimated_total']} "
          f"pricing_source={ledger['pricing']['source']} warnings={len(warnings)}")
    for note in total["notes"]:
        print(f"# warning: {note}")

    if args.update_outcome:
        outcome_path = default_outcome_path(vault_root, pit_id)
        try:
            rel = output_path.relative_to(vault_root)
        except ValueError:
            rel = output_path
        try:
            budget = update_outcome_budget(outcome_path, ledger, str(rel))
        except (ValueError, OSError) as exc:
            print(f"error: cannot update outcome budget: {exc}", file=sys.stderr)
            return 2
        print(f"# outcome budget updated -> {outcome_path}")
        print(f"# budget.tokens_total={budget.get('tokens_total')} "
              f"usd_estimated_spent={budget.get('usd_estimated_spent')} "
              f"pricing_source={budget.get('pricing_source')}")

    if args.stdout:
        print(text)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
