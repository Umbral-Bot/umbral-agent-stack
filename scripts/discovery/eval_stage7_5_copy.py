#!/usr/bin/env python3
"""Stage 7.5 — LinkedIn copy evaluator.

Loads proposals + rules from `tests/discovery/fixtures/`, builds prompts from
`prompts/rick/linkedin-copy-{system,user}.md`, calls the OpenClaw gateway
chat-completions endpoint (default `openclaw/main`), and scores each generated
copy against R1..R12 rules described in
`docs/discovery/rick-linkedin-voice.md`.

Outputs:
  * Detailed JSON report at the path given by ``--out`` (default
    ``reports/stage7_5_eval_v{N}.json`` where N is auto-incremented).
  * Stdout summary table.

Usage::

    python scripts/discovery/eval_stage7_5_copy.py \\
        --fixtures-dir tests/discovery/fixtures \\
        --model openclaw/main

Exit code: 0 if final aggregate score ≥ threshold (default 0.80) AND every
hard rule passes 100%, else 1.

The script is also imported by ``tests/discovery/test_eval_stage7_5_copy.py``
which uses the public functions ``score_copy``, ``run_evaluator`` (the latter
with a stub LLM) — no real gateway call is made in tests.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time
from collections import Counter
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURES_DIR = REPO_ROOT / "tests" / "discovery" / "fixtures"
DEFAULT_PROMPT_DIR = REPO_ROOT / "prompts" / "rick"
DEFAULT_REPORTS_DIR = REPO_ROOT / "reports"

DEFAULT_GATEWAY_URL = os.environ.get("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789")
DEFAULT_MODEL = "openclaw/main"
DEFAULT_THRESHOLD = 0.80

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
HASHTAG_RE = re.compile(r"#[A-Za-z][A-Za-z0-9_]*")


# ----------------------------- Rule definitions ----------------------------- #

# R17 (source_url_verified, hard) was introduced 2026-05-08 alongside the
# pre-LLM source verifier. Fixtures bypass it via
# ``fixture_skip_source_verify=true`` so the canned eval (which uses sandbox
# example.* URLs) does not require live HTTP probes.
HARD_RULES = ("R1", "R2", "R4", "R5", "R7", "R8", "R9", "R11", "R17")
SOFT_RULES = ("R3", "R6", "R10", "R12")


@dataclass
class RuleResult:
    rule_id: str
    description: str
    passed: bool
    severity: str  # "hard" | "soft"
    detail: str = ""


@dataclass
class CopyEval:
    fixture_id: str
    model: str
    copy_text: str
    rules: list[RuleResult] = field(default_factory=list)
    score: float = 0.0
    hard_pass_ratio: float = 0.0
    soft_pass_ratio: float = 0.0
    error: str | None = None

    # Voice v3 additions — defaults preserve backwards compat with existing tests.
    voice_match_score: float = 0.0
    voice_dimensions: dict[str, Any] = field(default_factory=dict)
    approved: bool = False
    hard_reject_rule_ids: list[str] = field(default_factory=list)
    hard_rejects: list[dict[str, Any]] = field(default_factory=list)
    batch_repetition_findings: list[dict[str, Any]] = field(default_factory=list)
    source_verification_mode: str = "unknown"


# --------------------------- Voice v3 dimension data ----------------------- #

# Stop-words to drop before computing 4-grams (very small list per spec).
_STOP_WORDS = {"de", "la", "el", "en", "y", "a", "que", "los", "las",
               "un", "una", "por", "para"}

# AECO technical & operational vocab for technical_clarity.
_AECO_TECH_TERMS = [
    "BIM", "BEP", "IFC", "CDE", "QA", "LOD", "Revit", "Dynamo", "Navisworks",
    "modelo federado", "clashes", "familias", "parámetros", "coordinación",
    "entregables", "oficina técnica", "obra", "especialidades", "MEP", "ArchiCAD",
]
_AECO_OPERATIONAL_TERMS = [
    "obra", "oficina técnica", "entrega", "licitación", "coordinación",
    "revisión", "QA", "BEP", "modelo", "cliente", "disciplina", "especialidad",
    "entregable",
]
_HYPE_TERMS = ["revolucionar", "game changer", "next level",
               "el futuro ya llegó", "sin precedentes"]

# Practical-exit terms (used by 5.2 + 5.5 + HR4 + HR5).
_PRACTICAL_EXIT_TERMS = [
    "criterio", "proceso", "protocolo", "responsable", "trazabilidad",
    "BEP", "estándar", "estandar", "QA", "validar", "documentar",
    "versionar", "revisión", "revision", "gobernanza",
    "bajar a operación", "dejar trazado", "definir", "ordenar",
]

_DAVID_STANCE_PHRASES = [
    "para mí", "mi lectura", "yo veo", "me parece",
    "lo importante", "el punto", "la pregunta",
]

_TECH_TERMS_DAVID_FIT = ["IA", "BIM", "automatiz", "IFC", "Revit"]
_LIMIT_CRITERION_TERMS = [
    "criterio", "proceso", "límite", "limite", "sin", "sólo", "solo",
    "no basta", "no alcanza",
]

_BAD_REGISTER_TERMS = ["usted", "ustedes", "vuestro", "vuestra", "vosotros"]


def _ngrams(text: str, n: int = 4) -> list[tuple[str, ...]]:
    """Extract relevant n-grams: lowercase, no URLs/hashtags/Fuente, drop stopwords."""
    cleaned = URL_RE.sub(" ", text or "")
    cleaned = HASHTAG_RE.sub(" ", cleaned)
    cleaned = re.sub(r"(?im)^\s*(fuente|vía|via|origen)\s*[:\-].*$", " ", cleaned)
    cleaned = cleaned.lower()
    cleaned = re.sub(r"[^0-9a-záéíóúñü\s]", " ", cleaned, flags=re.UNICODE)
    tokens = [t for t in cleaned.split() if t and t not in _STOP_WORDS]
    if len(tokens) < n:
        return []
    return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def _normalized_hook(text: str) -> str:
    """First-line lowercase normalized to first 8 alphanumeric tokens."""
    first = (text or "").strip().splitlines()[0] if (text or "").strip() else ""
    cleaned = re.sub(r"[^0-9a-záéíóúñü\s]", " ", first.lower(), flags=re.UNICODE)
    toks = [t for t in cleaned.split() if t]
    return " ".join(toks[:8])


def _moderated_phrases(rules_cfg: dict[str, Any]) -> list[str]:
    return list(rules_cfg.get("scoring", {}).get("voice_v3", {})
                .get("moderated_phrases", []))


def _moderated_used_in_copy(copy_text: str, rules_cfg: dict[str, Any]) -> list[str]:
    text_lower = (copy_text or "").lower()
    return [p for p in _moderated_phrases(rules_cfg) if p.lower() in text_lower]


def verify_source(url: str) -> bool:
    """Lightweight live-source verifier (stub).

    Returns True iff the URL has a non-example domain and parses as a real URL.
    Real network verification is intentionally out of scope here; the writer
    runs in fixture-skip mode by default and live mode is an opt-in path.
    """
    if not url:
        return False
    m = re.match(r"https?://([^/]+)", url, re.IGNORECASE)
    if not m:
        return False
    host = m.group(1).lower()
    if "example." in host:
        return False
    return True


# ----------------------- Voice v3 dimension scorers ------------------------ #

def _score_technical_clarity(
    copy_text: str,
    fixture: dict[str, Any] | None,
    batch_context: dict[str, Any] | None,  # noqa: ARG001
    source_payload: dict[str, Any] | None,
) -> tuple[float, list[str]]:
    text = copy_text or ""
    text_lower = text.lower()
    score = 0.0
    reasons: list[str] = []
    disciplines = (fixture or {}).get("disciplines") or []
    if any(str(d).lower() in text_lower for d in disciplines):
        score += 0.20
        reasons.append("discipline_mentioned")
    tech_hits = sum(1 for t in _AECO_TECH_TERMS if t.lower() in text_lower)
    if tech_hits >= 2:
        score += 0.20
        reasons.append(f"tech_terms_{tech_hits}")
    if any(t.lower() in text_lower for t in _AECO_OPERATIONAL_TERMS):
        score += 0.20
        reasons.append("operational_term")
    if not any(t.lower() in text_lower for t in _HYPE_TERMS):
        score += 0.20
        reasons.append("no_hype")
    sp = source_payload or {}
    src_titular = str(sp.get("titular", ""))
    src_kp = sp.get("key_points") or []
    src_match = False
    for chunk in [src_titular] + [str(p) for p in src_kp]:
        for piece in re.split(r"[\.\,\:\;\!\?]", chunk):
            piece = piece.strip()
            if len(piece) > 5 and piece.lower() in text_lower:
                src_match = True
                break
        if src_match:
            break
    if src_match:
        score += 0.20
        reasons.append("source_substring_present")
    return min(1.0, score), reasons


def _score_operational_criteria(
    copy_text: str,
    fixture: dict[str, Any] | None,  # noqa: ARG001
    batch_context: dict[str, Any] | None,  # noqa: ARG001
    source_payload: dict[str, Any] | None,  # noqa: ARG001
) -> tuple[float, list[str]]:
    text = copy_text or ""
    score = 0.0
    reasons: list[str] = []
    if re.search(r"\b(criterio|proceso|protocolo|estándar|estandar|BEP|regla|QA|gobernanza|trazabilidad)\b",
                 text, re.IGNORECASE):
        score += 0.25
        reasons.append("criterion_term")
    if re.search(r"\b(responsable|quién|decisión|validar|aprobar|cerrar|revisar|coordinar|dueño)\b",
                 text, re.IGNORECASE):
        score += 0.25
        reasons.append("ownership_term")
    if re.search(r"\b(hay que|necesit[ao]s?|conviene|defin[ie]|ordenar|documentar|versionar|validar|dejar trazado|bajar a operación)\b",
                 text, re.IGNORECASE):
        score += 0.25
        reasons.append("imperative_term")
    tail = text[-200:].lower()
    if any(t.lower() in tail for t in _PRACTICAL_EXIT_TERMS):
        score += 0.25
        reasons.append("tail_practical_exit")
    return min(1.0, score), reasons


def _score_david_voice_fit(
    copy_text: str,
    fixture: dict[str, Any] | None,  # noqa: ARG001
    batch_context: dict[str, Any] | None,  # noqa: ARG001
    source_payload: dict[str, Any] | None,  # noqa: ARG001
) -> tuple[float, list[str]]:
    text = copy_text or ""
    text_lower = text.lower()
    score = 0.0
    reasons: list[str] = []
    has_tu = bool(re.search(r"\b(tu|tus|te|vos)\b", text, re.IGNORECASE))
    has_bad = any(re.search(rf"\b{re.escape(b)}\b", text, re.IGNORECASE)
                  for b in _BAD_REGISTER_TERMS)
    if has_tu and not has_bad:
        score += 0.20
        reasons.append("tuteo")
    if any(p.lower() in text_lower for p in _DAVID_STANCE_PHRASES):
        score += 0.20
        reasons.append("stance_phrase")
    has_tech = any(t.lower() in text_lower for t in _TECH_TERMS_DAVID_FIT)
    has_limit = any(re.search(rf"\b{re.escape(t)}\b", text, re.IGNORECASE)
                    for t in _LIMIT_CRITERION_TERMS)
    if has_tech and has_limit:
        score += 0.20
        reasons.append("tech_plus_limit")
    sentences = [s.strip() for s in re.split(r"[\.!?]", text) if s.strip()]
    word_counts = [len(s.split()) for s in sentences]
    if len(word_counts) >= 2:
        try:
            sd = statistics.stdev(word_counts)
        except statistics.StatisticsError:
            sd = 0.0
        if 4.0 <= sd <= 25.0 and any(c < 10 for c in word_counts) and any(c > 15 for c in word_counts):
            score += 0.20
            reasons.append("rhythm_ok")
    moderated = _moderated_phrases(
        {"scoring": {"voice_v3": {"moderated_phrases": [
            "Mi lectura es simple", "Mi lectura es", "Para mí, el punto",
            "El problema no es", "La decisión no es", "La pregunta útil es",
            "En LATAM veo", "Lo que veo en proyecto", "PDF decorativo",
            "automatizar ruido", "la IA no te salva",
        ]}}})
    repeated_moderated = any(text_lower.count(p.lower()) > 1 for p in moderated)
    has_guru_close = bool(re.search(
        r"\b(comenta|qué opinas|agenda|link en bio|escríbeme)\b",
        text, re.IGNORECASE))
    if (not repeated_moderated) and (not has_guru_close):
        score += 0.20
        reasons.append("no_repeat_no_guru")
    # Penalties.
    if "Mi lectura es simple" in text:
        score -= 0.25
        reasons.append("penalty_lectura_simple")
    if "El problema no es" in text and "La decisión no es" in text:
        score -= 0.20
        reasons.append("penalty_dual_negation")
    if re.search(r"\btu (desorden|equipo no|oficina no|BIM no)\b", text, re.IGNORECASE):
        score -= 0.20
        reasons.append("penalty_blame_hook")
    return max(0.0, min(1.0, score)), reasons


def _score_low_repetition(
    copy_text: str,
    fixture: dict[str, Any] | None,  # noqa: ARG001
    batch_context: dict[str, Any] | None,
    source_payload: dict[str, Any] | None,  # noqa: ARG001
    rules_cfg: dict[str, Any] | None = None,
) -> tuple[float, list[str]]:
    text = copy_text or ""
    text_lower = text.lower()
    moderated = _moderated_phrases(rules_cfg or {})
    counts_in_self = {p: text_lower.count(p.lower()) for p in moderated if p.lower() in text_lower}
    max_self_count = max(counts_in_self.values()) if counts_in_self else 0

    if not batch_context or batch_context.get("copy_index", 0) == 0:
        if max_self_count <= 1:
            return 1.0, ["solo_no_repeat"]
        if max_self_count == 2:
            return 0.75, ["solo_one_internal_dup"]
        return 0.50, ["solo_many_internal_dups"]

    seen_ngrams: Counter = batch_context.get("ngrams_seen") or Counter()
    self_ngrams = set(_ngrams(text))
    collisions = sum(1 for ng in self_ngrams if seen_ngrams.get(ng, 0) >= 1)

    used_phrases: list[str] = batch_context.get("moderated_phrases_used") or []
    repeated_moderated_in_batch = any(
        p.lower() in text_lower and p in used_phrases for p in moderated
    )

    if repeated_moderated_in_batch:
        return 0.0, [f"moderated_repeat_batch:{collisions}"]
    if collisions == 0:
        return 1.0, ["zero_collisions"]
    if 1 <= collisions <= 2:
        return 0.75, [f"low_collisions:{collisions}"]
    if 3 <= collisions <= 5:
        return 0.50, [f"medium_collisions:{collisions}"]
    return 0.25, [f"high_collisions:{collisions}"]


def _score_organizational_sensitivity(
    copy_text: str,
    fixture: dict[str, Any] | None,  # noqa: ARG001
    batch_context: dict[str, Any] | None,  # noqa: ARG001
    source_payload: dict[str, Any] | None,  # noqa: ARG001
) -> tuple[float, list[str]]:
    text = copy_text or ""
    score = 0.0
    reasons: list[str] = []
    if re.search(r"\b(equipo|coordinador|BIM Manager|oficina técnica|cliente|jefatura|especialista|disciplina|obra)\b",
                 text, re.IGNORECASE):
        score += 0.20
        reasons.append("actor_term")
    if re.search(r"\b(adopción|adopcion|cambio|resistencia|confianza|criterio compartido|colaboración|colaboracion|flujo|responsabilidad)\b",
                 text, re.IGNORECASE):
        score += 0.20
        reasons.append("change_term")
    sentences = re.split(r"(?<=[\.!?])\s+", text)
    tools = ["Revit", "BIM", "IA", "Dynamo", "Navisworks", "modelo", "IFC"]
    procs = ["proceso", "flujo", "procedimiento", "protocolo",
             "coordinación", "revisión", "BEP"]
    for s in sentences:
        sl = s.lower()
        if any(t.lower() in sl for t in tools) and any(p.lower() in sl for p in procs):
            score += 0.20
            reasons.append("tool_plus_process")
            break
    if re.search(r"\b(criterio humano|interpretación|interpretacion|adopción gradual|madurez|capacitación|capacitacion|tiempo de equipo)\b",
                 text, re.IGNORECASE):
        score += 0.20
        reasons.append("human_limits")
    if not re.search(r"\b(no sabes|no entienden|fracas[ao]|está mal|estan mal|están mal)\b",
                     text, re.IGNORECASE):
        score += 0.20
        reasons.append("no_blame_tone")
    return min(1.0, score), reasons


def _score_source_verifiability(
    copy_text: str,
    fixture: dict[str, Any] | None,
    batch_context: dict[str, Any] | None,  # noqa: ARG001
    source_payload: dict[str, Any] | None,
    source_verification_mode: str = "fixture",
) -> tuple[float, list[str], str]:
    """Returns (score, reasons, resolved_mode)."""
    text = copy_text or ""
    sp = source_payload or {}
    fixture = fixture or {}
    score = 0.0
    reasons: list[str] = []
    src_url = (sp.get("source_url") or "").strip()

    if src_url and f"Fuente: {src_url}" in text:
        score += 0.30
        reasons.append("fuente_line_present")

    # Factual support check.
    factuals = _extract_factuals(text)
    if not factuals:
        score += 0.30
        reasons.append("no_factuals")
    else:
        blob = _build_source_blob(sp)
        unsupported = [f for f in factuals if not _factual_in_blob(f, blob)]
        if not unsupported:
            score += 0.30
            reasons.append("all_factuals_supported")

    other_urls = [u for u in URL_RE.findall(text) if u != src_url]
    if not other_urls:
        score += 0.20
        reasons.append("no_extra_urls")

    resolved_mode = "unknown"
    if source_verification_mode == "fixture" and fixture.get("fixture_skip_source_verify", False):
        score += 0.20
        reasons.append("fixture_skipped")
        resolved_mode = "fixture_skipped"
    elif source_verification_mode == "live":
        if src_url and verify_source(src_url):
            score += 0.20
            reasons.append("live_verified")
            resolved_mode = "live_verified"
        else:
            resolved_mode = "live_unverified"
    elif source_verification_mode == "fixture":
        resolved_mode = "fixture"
    return min(1.0, max(0.0, score)), reasons, resolved_mode


# ------------------------- Voice v3 fact extraction ----------------------- #

_PCT_RE = re.compile(r"\b\d+(?:[.,]\d+)?\s*%")
_YEAR_RE = re.compile(r"\b20\d{2}\b")
_BIG_NUM_RE = re.compile(r"\b\d{3,}(?:[.,]\d+)?\b|\b\d+[.,]\d+\b")
_SOURCE_MENTION_RE = re.compile(
    r"\b(paper|preprint|estudio|informe|encuesta|investigación|investigacion)\b",
    re.IGNORECASE)


def _extract_factuals(text: str) -> list[dict[str, str]]:
    """Return list of {kind, raw, normalized} factuals to verify against source."""
    text = text or ""
    cleaned_for_url_scan = text
    out: list[dict[str, str]] = []
    # Hashtag bodies should be stripped to avoid false positives like #IFC2025.
    hashtag_free = HASHTAG_RE.sub(" ", text)
    url_free = URL_RE.sub(" ", hashtag_free)

    for m in _PCT_RE.finditer(url_free):
        raw = m.group(0)
        norm = re.sub(r"\s+", "", raw).replace(",", ".")
        out.append({"kind": "pct", "raw": raw, "normalized": norm})
    for m in _YEAR_RE.finditer(url_free):
        raw = m.group(0)
        # Only flag year if followed by a factual hint (cifra/dato anexo).
        ctx = url_free[max(0, m.start()-40): m.end()+40]
        has_anchor = any(kw in ctx.lower() for kw in [
            "%", "estudio", "encuesta", "informe", "paper", "preprint",
            "datos", "n=", "(n=",
        ])
        if has_anchor:
            out.append({"kind": "year", "raw": raw, "normalized": raw})
    for m in _BIG_NUM_RE.finditer(url_free):
        raw = m.group(0)
        # Skip if it's actually inside a percentage match already captured.
        if "%" in url_free[m.end(): m.end()+2]:
            continue
        norm = raw.replace(",", ".")
        out.append({"kind": "num", "raw": raw, "normalized": norm})
    for m in URL_RE.finditer(cleaned_for_url_scan):
        out.append({"kind": "url", "raw": m.group(0),
                    "normalized": m.group(0).lower()})
    for m in _SOURCE_MENTION_RE.finditer(url_free):
        raw = m.group(0)
        out.append({"kind": "source_mention", "raw": raw,
                    "normalized": raw.lower()})
    return out


def _build_source_blob(source_payload: dict[str, Any] | None) -> str:
    sp = source_payload or {}
    parts = [
        str(sp.get("titular", "")),
        str(sp.get("summary", "")),
        " ".join(str(p) for p in (sp.get("key_points") or [])),
        str(sp.get("source_url", "")),
    ]
    return " ".join(parts).lower().replace(",", ".")


def _factual_in_blob(factual: dict[str, str], blob: str) -> bool:
    norm = factual["normalized"].lower()
    if factual["kind"] == "pct":
        # Compare as "41%" or "41 %" — just match the digits + "%".
        digits = re.sub(r"[^0-9.]", "", norm)
        return f"{digits}%" in re.sub(r"\s+", "", blob) or digits in blob
    if factual["kind"] == "year":
        return norm in blob
    if factual["kind"] == "num":
        return norm in blob
    if factual["kind"] == "url":
        return norm in blob
    if factual["kind"] == "source_mention":
        # Accept if any source-mention term appears in source blob.
        return bool(_SOURCE_MENTION_RE.search(blob))
    return True


# --------------------- Voice v3 hard reject rule funcs --------------------- #

def check_v3_hr2_unsupported_fact(
    copy_text: str,
    fixture: dict[str, Any] | None,  # noqa: ARG001
    rules_cfg: dict[str, Any] | None,  # noqa: ARG001
    source_payload: dict[str, Any] | None,
) -> dict[str, Any] | None:
    factuals = _extract_factuals(copy_text or "")
    if not factuals:
        return None
    blob = _build_source_blob(source_payload)
    for f in factuals:
        if not _factual_in_blob(f, blob):
            return {
                "rule_id": "V3_HR2_UNSUPPORTED_FACT",
                "reason": f"factual not present in source: {f['kind']}={f['raw']!r}",
                "evidence": f["raw"],
            }
    return None


def check_v3_hr3_unverified_source_live(
    copy_text: str,
    fixture: dict[str, Any] | None,
    rules_cfg: dict[str, Any] | None,  # noqa: ARG001
    source_payload: dict[str, Any] | None,
    source_verification_mode: str,
) -> dict[str, Any] | None:
    fixture = fixture or {}
    if source_verification_mode != "live":
        return None
    if fixture.get("fixture_skip_source_verify"):
        return None
    sp = source_payload or {}
    src_url = (sp.get("source_url") or "").strip()
    if not src_url:
        return {"rule_id": "V3_HR3_UNVERIFIED_SOURCE_LIVE",
                "reason": "empty source_url", "evidence": ""}
    if re.search(r"(example\.|\.example\.)", src_url, re.IGNORECASE):
        return {"rule_id": "V3_HR3_UNVERIFIED_SOURCE_LIVE",
                "reason": "example domain", "evidence": src_url}
    # URL in `Fuente: ...` line must match.
    m = re.search(r"(?im)^\s*fuente\s*[:\-]\s*(\S+)", copy_text or "")
    if m and m.group(1).rstrip(".,;)") != src_url:
        return {"rule_id": "V3_HR3_UNVERIFIED_SOURCE_LIVE",
                "reason": "fuente line url mismatch", "evidence": m.group(1)}
    if not verify_source(src_url):
        return {"rule_id": "V3_HR3_UNVERIFIED_SOURCE_LIVE",
                "reason": "verify_source returned False", "evidence": src_url}
    return None


def check_v3_hr4_confrontational_no_pedagogy(
    copy_text: str,
    fixture: dict[str, Any] | None,  # noqa: ARG001
    rules_cfg: dict[str, Any] | None,  # noqa: ARG001
) -> dict[str, Any] | None:
    text = copy_text or ""
    sentences = [s.strip() for s in re.split(r"(?<=[\.!?])\s+", text) if s.strip()]
    hook = sentences[0] if sentences else ""

    signals = 0
    found: list[str] = []

    if (re.search(r"\btu (desorden|equipo no|oficina no|BIM no|gente no)\b",
                  hook, re.IGNORECASE)
            or re.search(r"\bsi tu BIM no\b", hook, re.IGNORECASE)
            or re.search(r"\bno estás haciendo BIM\b", hook, re.IGNORECASE)):
        signals += 1
        found.append("hook_blame")

    for s in sentences:
        if (re.search(r"\b(siempre|nunca|todos|nadie|sólo|solo)\b", s, re.IGNORECASE)
                and len(s.split()) < 15
                and re.search(r"[\.!]\s*$", s)):
            signals += 1
            found.append("absolutism")
            break

    if re.search(r"\b(no sabes|no entiende|fracas[ao]|está mal|estan mal|están mal)\b",
                 text, re.IGNORECASE):
        signals += 1
        found.append("direct_judgment")

    tail = text[-200:]
    if re.search(r"\b(comenta|qué opinas|agenda|link en bio|escríbeme|próxim[oa] nivel|game changer)\b",
                 tail, re.IGNORECASE):
        signals += 1
        found.append("guru_close")

    if signals < 2:
        return None

    text_lower = text.lower()
    practical = _PRACTICAL_EXIT_TERMS + [
        "define", "documenta", "versiona", "valida", "traza", "ordena",
        "protocolo", "criterio", "responsable", "revisión", "gobernanza",
    ]
    if any(p.lower() in text_lower for p in practical):
        return None
    return {"rule_id": "V3_HR4_CONFRONTATIONAL_NO_PEDAGOGY",
            "reason": f"signals={signals} {found} without practical exit",
            "evidence": ",".join(found)}


_DIAGNOSIS_RE = re.compile(
    r"\b(problema|dolor|brecha|riesgo|cuello de botella|desorden|ruido|falla|fricción|friccion)\b",
    re.IGNORECASE)
_PRACTICAL_RE = re.compile(
    r"\b(criterio|proceso|protocolo|responsable|trazabilidad|BEP|estándar|estandar|QA|"
    r"validar|documentar|versionar|revisión|revision|gobernanza|"
    r"bajar a operación|dejar trazado|definir|ordenar|versionar)\b",
    re.IGNORECASE)


def check_v3_hr5_diagnosis_without_practical_exit(
    copy_text: str,
    fixture: dict[str, Any] | None,  # noqa: ARG001
    rules_cfg: dict[str, Any] | None,  # noqa: ARG001
) -> dict[str, Any] | None:
    text = copy_text or ""
    diag = _DIAGNOSIS_RE.search(text)
    if not diag:
        return None
    if _PRACTICAL_RE.search(text):
        return None
    return {"rule_id": "V3_HR5_DIAGNOSIS_WITHOUT_PRACTICAL_EXIT",
            "reason": "diagnosis without practical exit",
            "evidence": diag.group(0)}


# --------------------------------- Helpers --------------------------------- #

def _split_post(copy: str) -> dict[str, str]:
    """Split a copy into hook / body / tail (source line + hashtags)."""
    text = copy.strip()
    parts = re.split(r"\n\s*\n", text)
    hook = parts[0].strip() if parts else ""
    # Hashtag line is the LAST non-empty line that is dominated by hashtags.
    lines = [ln for ln in text.splitlines() if ln.strip()]
    hashtag_line = ""
    if lines:
        last = lines[-1].strip()
        # consider hashtag line if ≥3 hashtags OR line is only hashtags+spaces
        if len(HASHTAG_RE.findall(last)) >= 3 or re.fullmatch(r"(\s*#[A-Za-z][\w]*)+\s*", last):
            hashtag_line = last
    # Body: everything between hook and hashtag line, excluding any line that
    # starts with "Fuente:" / "Vía:" / "Origen:".
    body_text = text
    if hashtag_line:
        body_text = body_text.rsplit(hashtag_line, 1)[0]
    if parts:
        body_text = body_text[len(parts[0]):]
    body_lines: list[str] = []
    source_line = ""
    for ln in body_text.splitlines():
        s = ln.strip()
        if not s:
            body_lines.append(ln)
            continue
        if re.match(r"^(fuente|vía|via|origen)\s*[:\-]", s, re.IGNORECASE):
            source_line = s
            continue
        body_lines.append(ln)
    body = "\n".join(body_lines).strip()
    return {
        "hook": hook,
        "body": body,
        "source_line": source_line,
        "hashtag_line": hashtag_line,
    }


def _count_paragraphs(body: str) -> int:
    return len([p for p in re.split(r"\n\s*\n", body) if p.strip()])


# ----------------------------- Rule evaluations ---------------------------- #

def score_copy(
    copy_text: str,
    fixture: dict[str, Any],
    rules_cfg: dict[str, Any],
    *,
    batch_context: dict[str, Any] | None = None,
    source_payload: dict[str, Any] | None = None,
    source_verification_mode: str = "fixture",
) -> CopyEval:
    g = rules_cfg["global_rules"]
    text = copy_text or ""
    parts = _split_post(text)
    total_len = len(text)
    hook = parts["hook"]
    body = parts["body"]
    hashtag_line = parts["hashtag_line"]
    source_line = parts["source_line"]
    hashtags_found = HASHTAG_RE.findall(hashtag_line) if hashtag_line else HASHTAG_RE.findall(text)

    results: list[RuleResult] = []

    # R1 total length
    ok = g["R1_total_len_min"] <= total_len <= g["R1_total_len_max"]
    results.append(RuleResult("R1", "Total length in [400,3000]", ok, "hard",
                              f"len={total_len}"))

    # R2 hook ≤120
    ok = bool(hook) and len(hook) <= g["R2_hook_max_chars"]
    results.append(RuleResult("R2", "Hook ≤120 chars and non-empty", ok, "hard",
                              f"hook_len={len(hook)}"))

    # R3 body length [600,1800] soft
    body_len = len(body)
    ok = g["R3_body_min"] <= body_len <= g["R3_body_max"]
    results.append(RuleResult("R3", "Body length in [600,1800]", ok, "soft",
                              f"body_len={body_len}"))

    # R4 contains URL
    ok = bool(URL_RE.search(text))
    results.append(RuleResult("R4", "Contains source URL", ok, "hard"))

    # R5 hashtag count
    n = len(hashtags_found)
    ok = g["R5_hashtag_min"] <= n <= g["R5_hashtag_max"]
    results.append(RuleResult("R5", "Hashtag count in [3,5]", ok, "hard",
                              f"count={n}"))

    # R6 hashtag allowlist (soft) — every hashtag must be in allowlist (case-sensitive on the visible token)
    allow = set(g["R6_hashtag_allowlist"])
    bad_tags = [h for h in hashtags_found if h not in allow]
    results.append(RuleResult("R6", "All hashtags in allowlist", not bad_tags, "soft",
                              f"unknown={bad_tags}" if bad_tags else ""))

    # R7 no decorative emojis
    blocked_emojis = [e for e in g["R7_emoji_blocklist"] if e in text]
    results.append(RuleResult("R7", "No decorative emojis", not blocked_emojis, "hard",
                              f"found={blocked_emojis}" if blocked_emojis else ""))

    # R8 no marketing-slop tokens (case insensitive)
    text_lower = text.lower()
    blocked_tokens = [t for t in g["R8_token_blocklist"] if t.lower() in text_lower]
    results.append(RuleResult("R8", "No marketing-slop tokens", not blocked_tokens, "hard",
                              f"found={blocked_tokens}" if blocked_tokens else ""))

    # R9 no "usted"/"vosotros" — word-boundary, case-insensitive
    bad_register = []
    for tok in g["R9_register_blocklist"]:
        if re.search(rf"\b{re.escape(tok)}\b", text, re.IGNORECASE):
            bad_register.append(tok)
    results.append(RuleResult("R9", "No usted/vosotros", not bad_register, "hard",
                              f"found={bad_register}" if bad_register else ""))

    # R10 ≥3 paragraphs in body (soft)
    pcount = _count_paragraphs(body)
    results.append(RuleResult("R10", "Body has ≥3 paragraphs", pcount >= g["R10_min_paragraphs"], "soft",
                              f"paragraphs={pcount}"))

    # R11 no commercial CTA (case insensitive substring)
    ctas = [c for c in g["R11_cta_blocklist"] if c.lower() in text_lower]
    results.append(RuleResult("R11", "No commercial CTA", not ctas, "hard",
                              f"found={ctas}" if ctas else ""))

    # R12 mentions ≥1 expected discipline (soft)
    expected = fixture.get("disciplines", []) or []
    disciplines_hit = [d for d in expected if d.lower() in text_lower]
    results.append(RuleResult("R12", "Mentions ≥1 expected discipline", bool(disciplines_hit), "soft",
                              f"hit={disciplines_hit}"))

    # R17 source URL verified (hard).
    # Fixture flag ``fixture_skip_source_verify=true`` short-circuits with
    # PASS — required because the canned fixtures use ``example.*`` URLs
    # which the live verifier (rightly) blocklists. Real evaluator runs
    # against real proposals will exercise the verifier end-to-end.
    if fixture.get("fixture_skip_source_verify", False):
        results.append(RuleResult(
            "R17", "Source URL verified", True, "hard",
            "fixture_skip_source_verify=True",
        ))
    else:
        try:
            from scripts.discovery import source_verifier as _sv  # type: ignore
        except Exception as e:  # noqa: BLE001
            results.append(RuleResult(
                "R17", "Source URL verified", False, "hard",
                f"verifier_unavailable:{e!s:.120s}",
            ))
        else:
            src_url = ""
            for u in URL_RE.findall(text):
                src_url = u.rstrip(",.;:)")
                break
            if not src_url:
                src_url = fixture.get("source_url", "") or ""
            try:
                v = _sv.verify_source(src_url)
                ok_v = bool(v.get("ok"))
                detail = f"reason={v.get('reason') or 'ok'} url={src_url}"
            except Exception as e:  # noqa: BLE001
                ok_v = False
                detail = f"verifier_crash:{e!s:.120s}"
            results.append(RuleResult("R17", "Source URL verified", ok_v, "hard", detail))

    # Aggregate
    hard_total = sum(1 for r in results if r.severity == "hard")
    soft_total = sum(1 for r in results if r.severity == "soft")
    hard_pass = sum(1 for r in results if r.severity == "hard" and r.passed)
    soft_pass = sum(1 for r in results if r.severity == "soft" and r.passed)
    hard_ratio = hard_pass / hard_total if hard_total else 0.0
    soft_ratio = soft_pass / soft_total if soft_total else 0.0
    score = 0.7 * hard_ratio + 0.3 * soft_ratio

    ev = CopyEval(
        fixture_id=fixture.get("id", "?"),
        model="(set by caller)",
        copy_text=copy_text,
        rules=results,
        score=round(score, 4),
        hard_pass_ratio=round(hard_ratio, 4),
        soft_pass_ratio=round(soft_ratio, 4),
    )

    # ----- Voice v3 dimensions ----- #
    voice_cfg = rules_cfg.get("scoring", {}).get("voice_v3", {}) or {}
    weights = voice_cfg.get("weights") or {}
    dims: dict[str, dict[str, Any]] = {}

    s, r = _score_technical_clarity(text, fixture, batch_context, source_payload)
    dims["technical_clarity"] = {"score": round(s, 4), "reasons": r}
    s, r = _score_operational_criteria(text, fixture, batch_context, source_payload)
    dims["operational_criteria"] = {"score": round(s, 4), "reasons": r}
    s, r = _score_david_voice_fit(text, fixture, batch_context, source_payload)
    dims["david_voice_fit"] = {"score": round(s, 4), "reasons": r}
    s, r = _score_low_repetition(text, fixture, batch_context, source_payload, rules_cfg)
    dims["low_repetition"] = {"score": round(s, 4), "reasons": r}
    s, r = _score_organizational_sensitivity(text, fixture, batch_context, source_payload)
    dims["organizational_sensitivity"] = {"score": round(s, 4), "reasons": r}
    s, r, resolved_mode = _score_source_verifiability(
        text, fixture, batch_context, source_payload, source_verification_mode)
    dims["source_verifiability"] = {"score": round(s, 4), "reasons": r}
    ev.source_verification_mode = resolved_mode or source_verification_mode

    voice_score = sum(dims[k]["score"] * float(weights.get(k, 0.0)) for k in dims)
    ev.voice_match_score = round(min(1.0, max(0.0, voice_score)), 4)
    ev.voice_dimensions = dims

    # ----- Voice v3 hard rejects (HR2..HR5; HR1 in score_batch) ----- #
    for chk in (
        check_v3_hr2_unsupported_fact(text, fixture, rules_cfg, source_payload),
        check_v3_hr3_unverified_source_live(text, fixture, rules_cfg,
                                            source_payload, source_verification_mode),
        check_v3_hr4_confrontational_no_pedagogy(text, fixture, rules_cfg),
        check_v3_hr5_diagnosis_without_practical_exit(text, fixture, rules_cfg),
    ):
        if chk:
            ev.hard_rejects.append(chk)
            ev.hard_reject_rule_ids.append(chk["rule_id"])

    # ----- Approved gate ----- #
    score_threshold = rules_cfg.get("scoring", {}).get("threshold", 0.80)
    voice_threshold = voice_cfg.get("voice_match_score_threshold", 0.80)
    ev.approved = bool(
        ev.error is None
        and ev.hard_pass_ratio >= 1.0
        and ev.score >= score_threshold
        and ev.voice_match_score >= voice_threshold
        and not ev.hard_reject_rule_ids
    )
    return ev


# -------------------------- LLM call (gateway) ----------------------------- #

def _resolve_gateway_token() -> str:
    tok = os.environ.get("OPENCLAW_GATEWAY_TOKEN")
    if tok:
        return tok
    cfg = Path.home() / ".openclaw" / "openclaw.json"
    if cfg.is_file():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            return data["gateway"]["auth"]["token"]
        except Exception:
            pass
    raise RuntimeError(
        "No gateway token available (set OPENCLAW_GATEWAY_TOKEN or have ~/.openclaw/openclaw.json with gateway.auth.token)."
    )


def call_gateway(system: str, user: str, *, model: str, gateway_url: str,
                 timeout: float = 120.0, temperature: float = 0.7) -> str:
    import httpx
    token = _resolve_gateway_token()
    url = gateway_url.rstrip("/") + "/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
    }
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=payload)
        resp.raise_for_status()
        data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


# ----------------------------- Prompt loader ------------------------------- #

def build_copy_prompt(proposal: dict[str, Any], prompt_dir: Path = DEFAULT_PROMPT_DIR) -> tuple[str, str]:
    """Return (system, user) prompt strings for a given proposal.

    This is the canonical helper Hilo A (`stage7_5_copy_writer`) MUST use to
    keep prompt content in sync with the voice doc. Do not reformat the
    template files in place — that breaks the placeholder contract.
    """
    system = (prompt_dir / "linkedin-copy-system.md").read_text(encoding="utf-8")
    user_tmpl = (prompt_dir / "linkedin-copy-user.md").read_text(encoding="utf-8")
    user = user_tmpl.format(
        titular=proposal["titular"],
        summary=proposal["summary"],
        source_url=proposal["source_url"],
        disciplines=", ".join(proposal.get("disciplines", []) or ["BIM"]),
        key_points="\n".join(f"- {p}" for p in proposal.get("key_points", [])) or "- (sin puntos específicos)",
    )
    return system, user


# ------------------------------ Orchestrator ------------------------------- #

def score_batch(
    copy_texts: list[str],
    fixtures: list[dict[str, Any]],
    rules_cfg: dict[str, Any],
    *,
    model: str = "(set by caller)",
    source_payloads: list[dict[str, Any]] | None = None,
    source_verification_mode: str = "fixture",
) -> list[CopyEval]:
    """Score a batch with cross-copy repetition detection (V3_HR1)."""
    n = len(copy_texts)
    if len(fixtures) != n:
        raise ValueError("copy_texts/fixtures length mismatch")
    if source_payloads is None:
        source_payloads = [{} for _ in range(n)]
    elif len(source_payloads) != n:
        raise ValueError("source_payloads length mismatch")

    batch_context: dict[str, Any] = {
        "prior_texts": [],
        "moderated_phrases_used": [],
        "ngrams_seen": Counter(),
        "hooks_seen": [],
        "closures_seen": [],
        "copy_index": 0,
    }

    results: list[CopyEval] = []
    moderated_phrases = _moderated_phrases(rules_cfg)

    for i, (text, fixture, payload) in enumerate(zip(copy_texts, fixtures, source_payloads)):
        batch_context["copy_index"] = i
        ev = score_copy(
            text or "",
            fixture,
            rules_cfg,
            batch_context=batch_context,
            source_payload=payload,
            source_verification_mode=source_verification_mode,
        )
        ev.model = model
        results.append(ev)

        # Update batch_context AFTER scoring this copy.
        batch_context["prior_texts"].append(text or "")
        for ng in _ngrams(text or ""):
            batch_context["ngrams_seen"][ng] += 1
        for p in moderated_phrases:
            if p.lower() in (text or "").lower() and p not in batch_context["moderated_phrases_used"]:
                batch_context["moderated_phrases_used"].append(p)
        batch_context["hooks_seen"].append(_normalized_hook(text or ""))
        batch_context["closures_seen"].append((text or "")[-200:].strip().lower())

    # ---- V3_HR1 batch-aware repetition detection ---- #
    voice_cfg = rules_cfg.get("scoring", {}).get("voice_v3", {}) or {}
    ngram_max = int(voice_cfg.get("ngram_max_copies", 2))

    # Per-copy ngram occurrence (set per copy, then count copies containing each ngram).
    per_copy_ngrams = [set(_ngrams(t or "")) for t in copy_texts]
    ngram_copies: Counter = Counter()
    for s in per_copy_ngrams:
        for ng in s:
            ngram_copies[ng] += 1

    # Moderated phrase: count of copies containing it (case-insensitive).
    phrase_copies: dict[str, list[int]] = {}
    for p in moderated_phrases:
        idxs = [i for i, t in enumerate(copy_texts) if p.lower() in (t or "").lower()]
        if idxs:
            phrase_copies[p] = idxs

    # Hook normalization counts.
    hook_norm = [_normalized_hook(t or "") for t in copy_texts]
    hook_counts: Counter = Counter(hook_norm)

    # Apply HR1 to each offending copy.
    for i, ev in enumerate(results):
        findings: list[dict[str, Any]] = []
        # 1) Moderated phrase appearing in >1 copy.
        for p, idxs in phrase_copies.items():
            if len(idxs) > 1 and i in idxs:
                findings.append({"type": "moderated_phrase", "value": p,
                                 "copies": idxs})
        # 2) 4-gram appearing in >ngram_max copies and present in this copy.
        if ngram_max < 1:
            ngram_max = 2
        for ng, c in ngram_copies.items():
            if c > ngram_max and ng in per_copy_ngrams[i]:
                findings.append({"type": "ngram", "value": " ".join(ng),
                                 "count": c})
        # 3) Hook duplicated (>1 occurrence) and this copy's hook == it.
        h = hook_norm[i]
        if h and hook_counts[h] > 1:
            findings.append({"type": "hook", "value": h,
                             "count": hook_counts[h]})

        if findings:
            ev.batch_repetition_findings = findings
            ev.hard_rejects.append({
                "rule_id": "V3_HR1_BATCH_REPETITION",
                "reason": f"{len(findings)} batch repetition finding(s)",
                "evidence": "; ".join(
                    f"{f['type']}={f['value']!r}" for f in findings),
            })
            ev.hard_reject_rule_ids.append("V3_HR1_BATCH_REPETITION")
            # Re-evaluate approval gate.
            ev.approved = False

    return results


def run_evaluator(
    proposals: list[dict[str, Any]],
    rules_cfg: dict[str, Any],
    *,
    llm_call: Callable[[str, str], str],
    model: str,
    prompt_dir: Path = DEFAULT_PROMPT_DIR,
    source_verification_mode: str = "fixture",
) -> list[CopyEval]:
    fixture_rules = {f["id"]: f for f in rules_cfg.get("per_fixture", [])}

    # Generate all copies first (errors recorded as per-fixture stub evals).
    copies: list[str] = []
    fixtures: list[dict[str, Any]] = []
    payloads: list[dict[str, Any]] = []
    error_evals: dict[int, CopyEval] = {}
    for idx, prop in enumerate(proposals):
        merged_fixture = {**prop, **fixture_rules.get(prop["id"], {})}
        fixtures.append(merged_fixture)
        payloads.append({
            "id": str(prop.get("id", "")),
            "titular": prop.get("titular", ""),
            "summary": prop.get("summary", ""),
            "key_points": prop.get("key_points") or [],
            "source_url": prop.get("source_url", ""),
            "fixture_skip_source_verify": prop.get("fixture_skip_source_verify", False),
        })
        try:
            system, user = build_copy_prompt(prop, prompt_dir=prompt_dir)
            copy = llm_call(system, user)
        except Exception as exc:  # noqa: BLE001
            error_evals[idx] = CopyEval(
                fixture_id=prop["id"], model=model, copy_text="", rules=[],
                error=f"{type(exc).__name__}: {exc}",
            )
            copies.append("")
            continue
        copies.append(re.sub(r"^```[a-zA-Z]*\n|\n```$", "", copy.strip()))

    # Score the batch (errors get replaced after).
    batch_results = score_batch(
        copies, fixtures, rules_cfg,
        model=model, source_payloads=payloads,
        source_verification_mode=source_verification_mode,
    )
    # Splice in the original error evals.
    for idx, ev in error_evals.items():
        batch_results[idx] = ev
    return batch_results


# ------------------------------- Reporting --------------------------------- #

def aggregate(results: Iterable[CopyEval], rules_cfg: dict[str, Any]) -> dict[str, Any]:
    all_results = list(results)
    valid = [r for r in all_results if r.error is None]
    if not valid:
        return {"score": 0.0, "rule_pass_pct": {}, "n": 0,
                "voice_match_score_avg": 0.0, "approved_count": 0,
                "approved_ratio": 0.0, "hard_reject_counts_by_rule": {},
                "source_verification_modes": {},
                "batch_repetition_findings_count": 0}
    n = len(valid)
    score = sum(r.score for r in valid) / n
    rule_ids = [r.rule_id for r in valid[0].rules]
    pass_pct = {rid: 0.0 for rid in rule_ids}
    for r in valid:
        for rr in r.rules:
            pass_pct[rr.rule_id] += 1.0 if rr.passed else 0.0
    pass_pct = {rid: round(v / n, 4) for rid, v in pass_pct.items()}
    hard_all_100 = all(pass_pct.get(rid, 0.0) >= 1.0 for rid in HARD_RULES)

    voice_avg = sum(r.voice_match_score for r in valid) / n
    approved_count = sum(1 for r in valid if r.approved)
    hr_counts: dict[str, int] = {}
    for r in valid:
        for rid in r.hard_reject_rule_ids:
            hr_counts[rid] = hr_counts.get(rid, 0) + 1
    sv_modes: dict[str, int] = {}
    for r in valid:
        sv_modes[r.source_verification_mode] = sv_modes.get(r.source_verification_mode, 0) + 1
    findings_count = sum(len(r.batch_repetition_findings) for r in valid)

    return {
        "n": n,
        "score": round(score, 4),
        "rule_pass_pct": pass_pct,
        "hard_all_100": hard_all_100,
        "voice_match_score_avg": round(voice_avg, 4),
        "approved_count": approved_count,
        "approved_ratio": round(approved_count / n, 4),
        "hard_reject_counts_by_rule": hr_counts,
        "source_verification_modes": sv_modes,
        "batch_repetition_findings_count": findings_count,
    }


def _next_report_path(reports_dir: Path) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(reports_dir.glob("stage7_5_eval_v*.json"))
    nums = []
    for p in existing:
        m = re.search(r"v(\d+)\.json$", p.name)
        if m:
            nums.append(int(m.group(1)))
    nxt = (max(nums) + 1) if nums else 1
    return reports_dir / f"stage7_5_eval_v{nxt}.json"


def _run_one_pass(
    *, proposals: list[dict[str, Any]],
    rules_cfg: dict[str, Any],
    model: str,
    gateway_url: str,
    prompt_dir: Path,
    temperature: float,
    dry_run: bool,
    source_verification_mode: str,
) -> tuple[list[CopyEval], dict[str, Any], float]:
    if dry_run:
        def _stub(_s: str, _u: str) -> str:
            return ""
        llm: Callable[[str, str], str] = _stub
    else:
        def _real(s: str, u: str) -> str:
            return call_gateway(s, u, model=model, gateway_url=gateway_url,
                                temperature=temperature)
        llm = _real
    t0 = time.time()
    results = run_evaluator(
        proposals, rules_cfg, llm_call=llm, model=model,
        prompt_dir=prompt_dir,
        source_verification_mode=source_verification_mode,
    )
    elapsed = round(time.time() - t0, 2)
    agg = aggregate(results, rules_cfg)
    return results, agg, elapsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures-dir", default=str(DEFAULT_FIXTURES_DIR))
    parser.add_argument("--fixtures", default=None,
                        help="optional path; overrides fixtures-dir/stage7_5_proposals.json")
    parser.add_argument("--rules", default=None,
                        help="optional path; overrides fixtures-dir/stage7_5_golden_copies.json")
    parser.add_argument("--prompt-dir", default=str(DEFAULT_PROMPT_DIR))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--gateway-url", default=DEFAULT_GATEWAY_URL)
    parser.add_argument("--out", default=None, help="output JSON path")
    parser.add_argument("--report", default=None, help="alias for --out")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--temperatures", default=None,
                        help="comma-separated, e.g. 0.6,0.8,0.95")
    parser.add_argument("--source-verification-mode",
                        choices=["fixture", "live"], default="fixture")
    parser.add_argument("--dry-run", action="store_true",
                        help="don't call gateway, emit a fake copy (for smoke)")
    args = parser.parse_args(argv)

    # Resolve --report vs --out.
    if args.report and args.out and args.report != args.out:
        print("ERROR: --report and --out provided with different values", file=sys.stderr)
        return 2
    out_arg = args.out or args.report

    fixtures_dir = Path(args.fixtures_dir)
    proposals_path = Path(args.fixtures) if args.fixtures \
        else fixtures_dir / "stage7_5_proposals.json"
    rules_path = Path(args.rules) if args.rules \
        else fixtures_dir / "stage7_5_golden_copies.json"
    proposals = json.loads(proposals_path.read_text(encoding="utf-8"))
    rules_cfg = json.loads(rules_path.read_text(encoding="utf-8"))

    prompt_dir = Path(args.prompt_dir)

    temperatures: list[float]
    multi = bool(args.temperatures)
    if multi:
        try:
            temperatures = [float(t.strip()) for t in args.temperatures.split(",") if t.strip()]
        except ValueError:
            print("ERROR: invalid --temperatures CSV", file=sys.stderr)
            return 2
    else:
        temperatures = [args.temperature]

    out_path = Path(out_arg) if out_arg else _next_report_path(DEFAULT_REPORTS_DIR)

    if not multi:
        results, agg, elapsed = _run_one_pass(
            proposals=proposals, rules_cfg=rules_cfg,
            model=args.model, gateway_url=args.gateway_url,
            prompt_dir=prompt_dir, temperature=temperatures[0],
            dry_run=args.dry_run,
            source_verification_mode=args.source_verification_mode,
        )
        report = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "model": args.model,
            "gateway_url": args.gateway_url,
            "elapsed_sec": elapsed,
            "threshold": args.threshold,
            "temperature": temperatures[0],
            "source_verification_mode": args.source_verification_mode,
            "aggregate": agg,
            "per_fixture": [
                {**asdict(r), "rules": [asdict(rr) for rr in r.rules]}
                for r in results
            ],
        }
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        _print_summary(args, agg, results)
        print(f"\nReport: {out_path}")
        errs = [r for r in results if r.error]
        pass_overall = (
            agg["score"] >= args.threshold
            and agg.get("hard_all_100", False)
            and not errs
        )
        return 0 if pass_overall else 1

    # Multi-temperature consolidated run.
    runs_by_temp: dict[str, Any] = {}
    agg_by_temp: dict[str, Any] = {}
    overall_pass = True
    for t in temperatures:
        results, agg, elapsed = _run_one_pass(
            proposals=proposals, rules_cfg=rules_cfg,
            model=args.model, gateway_url=args.gateway_url,
            prompt_dir=prompt_dir, temperature=t,
            dry_run=args.dry_run,
            source_verification_mode=args.source_verification_mode,
        )
        key = f"{t}"
        runs_by_temp[key] = {
            "elapsed_sec": elapsed,
            "per_fixture": [
                {**asdict(r), "rules": [asdict(rr) for rr in r.rules]}
                for r in results
            ],
        }
        agg_by_temp[key] = agg
        errs = [r for r in results if r.error]
        if not (agg["score"] >= args.threshold and agg.get("hard_all_100", False) and not errs):
            overall_pass = False
        print(f"\n--- temperature={t} ---")
        _print_summary(args, agg, results)

    overall = {
        "n_temps": len(temperatures),
        "voice_match_score_avg_overall": round(
            sum(a.get("voice_match_score_avg", 0.0) for a in agg_by_temp.values())
            / max(1, len(agg_by_temp)), 4),
        "approved_ratio_overall": round(
            sum(a.get("approved_ratio", 0.0) for a in agg_by_temp.values())
            / max(1, len(agg_by_temp)), 4),
    }
    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": args.model,
        "gateway_url": args.gateway_url,
        "threshold": args.threshold,
        "source_verification_mode": args.source_verification_mode,
        "runs_by_temperature": runs_by_temp,
        "aggregate_by_temperature": agg_by_temp,
        "overall": overall,
    }
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"\nReport: {out_path}")
    return 0 if overall_pass else 1


def _print_summary(args, agg, results):
    print(f"=== Stage 7.5 LinkedIn copy eval — model={args.model} ===")
    print(f"Fixtures evaluated : {agg['n']}/{len(results)}")
    print(f"Aggregate score    : {agg['score']:.3f} (threshold {args.threshold:.2f})")
    print(f"Hard rules @ 100%  : {agg.get('hard_all_100', False)}")
    print(f"Voice match avg    : {agg.get('voice_match_score_avg', 0.0):.3f}")
    print(f"Approved           : {agg.get('approved_count', 0)}/{agg['n']} "
          f"(ratio {agg.get('approved_ratio', 0.0):.2f})")
    if agg.get("hard_reject_counts_by_rule"):
        print(f"Hard rejects       : {agg['hard_reject_counts_by_rule']}")
    if agg.get("source_verification_modes"):
        print(f"Source modes       : {agg['source_verification_modes']}")
    print("Per-rule pass pct  :")
    for rid, pct in agg["rule_pass_pct"].items():
        sev = "hard" if rid in HARD_RULES else "soft"
        print(f"  {rid:>3} [{sev}] {pct*100:5.1f}%")
    errs = [r for r in results if r.error]
    if errs:
        print(f"Errors ({len(errs)}):")
        for r in errs:
            print(f"  {r.fixture_id}: {r.error}")


if __name__ == "__main__":
    sys.exit(main())
