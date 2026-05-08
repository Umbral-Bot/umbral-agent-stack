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
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURES_DIR = REPO_ROOT / "tests" / "discovery" / "fixtures"
DEFAULT_PROMPT_DIR = REPO_ROOT / "prompts" / "rick"
DEFAULT_REPORTS_DIR = REPO_ROOT / "reports"

DEFAULT_GATEWAY_URL = os.environ.get("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789")
DEFAULT_MODEL = "openclaw/main"
DEFAULT_THRESHOLD = 0.85  # v2 raised from 0.80

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
HASHTAG_RE = re.compile(r"#[A-Za-z][A-Za-z0-9_]*")
WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]+")


# ----------------------------- Rule definitions ----------------------------- #

# v2: R13 (anti-repetition cross-batch) and R14 (organizational sensitivity)
# are now hard. R15 (balance pedagógico), R16 (muletilla), R17 (verificabilidad)
# are soft.
HARD_RULES = ("R1", "R2", "R4", "R5", "R7", "R8", "R9", "R11", "R13", "R14")
SOFT_RULES = ("R3", "R6", "R10", "R12", "R15", "R16", "R17")

# v2 weighted scoring dimensions. Sum of weights = 1.0.
# Each dimension's score is the mean pass-ratio (0/1 per rule per copy) over
# its constituent rules. The 'sensibilidad_organizacional' dimension is R14
# again, giving R14 effective double weight as required by the spec.
VOICE_DIMENSIONS = (
    ("claridad_tecnica",            0.25, ("R1", "R2", "R3")),
    ("criterio_operativo",          0.20, ("R12", "R14")),
    ("tono_david",                  0.20, ("R6", "R8", "R9", "R11", "R15")),
    ("baja_muletilla",              0.15, ("R13", "R16")),
    ("sensibilidad_organizacional", 0.10, ("R14",)),
    ("verificabilidad",             0.10, ("R4", "R17")),
)


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


def _word_tokens_lower(text: str) -> list[str]:
    return [w.lower() for w in WORD_RE.findall(text)]


def _ngrams(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    if len(tokens) < n:
        return set()
    return {tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def _count_substr_ci(text: str, needle: str) -> int:
    if not needle:
        return 0
    return text.lower().count(needle.lower())


# ----------------------------- Rule evaluations ---------------------------- #

def score_copy(copy_text: str, fixture: dict[str, Any], rules_cfg: dict[str, Any]) -> CopyEval:
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

    # R13 anti-repetition cross-batch (hard): single-copy mode passes by
    # default — the batch pass is computed by ``apply_batch_rules`` after all
    # copies are scored. Here we only flag intra-copy duplicate 4-grams
    # repeated more than twice as a soft tell, which never trips the rule on
    # its own.
    results.append(RuleResult("R13", "No 4-gram repeated in >2 copies of batch", True, "hard",
                              "batch-deferred"))

    # R14 organizational sensitivity (hard): mention ≥1 org token.
    org_tokens = g.get("R14_org_tokens", [])
    org_hits = [t for t in org_tokens if t.lower() in text_lower]
    results.append(RuleResult("R14", "Mentions ≥1 organizational token", bool(org_hits), "hard",
                              f"hit={org_hits[:5]}"))

    # R15 balance pedagógico (soft): if hook is confrontational, body must
    # contain ≥R15_min_propositive propositive tokens.
    confront_tokens = g.get("R15_confrontational_tokens", [])
    proposit_tokens = g.get("R15_propositive_tokens", [])
    min_prop = int(g.get("R15_min_propositive", 2))
    hook_lower = hook.lower()
    is_confrontational = any(t.lower() in hook_lower for t in confront_tokens)
    if is_confrontational:
        body_lower = body.lower()
        prop_hits = [t for t in proposit_tokens if t.lower() in body_lower]
        passed = len(prop_hits) >= min_prop
        detail = f"confrontational hook; propositive_hits={prop_hits}"
    else:
        passed = True
        detail = "hook not confrontational"
    results.append(RuleResult("R15", "Balance crítico-propositivo", passed, "soft", detail))

    # R16 muletilla (soft): max R16_max_per_copy occurrences of any muletilla
    # phrase per copy. Cross-batch enforcement is in apply_batch_rules.
    muletillas = g.get("R16_muletilla_phrases", [])
    max_per_copy = int(g.get("R16_max_per_copy", 1))
    counts = {m: _count_substr_ci(text, m) for m in muletillas}
    over = {m: c for m, c in counts.items() if c > max_per_copy}
    results.append(RuleResult("R16", "Muletilla 'Mi lectura es simple' bajo cupo", not over, "soft",
                              f"counts={counts}"))

    # R17 verificabilidad (soft): URL appears on a dedicated source line whose
    # prefix is one of R17_attribution_prefixes.
    prefixes = g.get("R17_attribution_prefixes", ["fuente", "vía", "via", "origen"])
    src_lower = source_line.lower()
    has_prefix = any(re.match(rf"^{re.escape(pref)}\s*[:\-]", src_lower) for pref in prefixes)
    has_url = bool(URL_RE.search(source_line))
    results.append(RuleResult("R17", "URL en línea de atribución dedicada", has_prefix and has_url, "soft",
                              f"source_line='{source_line[:80]}'"))

    # Aggregate (hard/soft simple ratios kept for back-compat reporting; the
    # canonical score is now ``voice_match_score`` — computed below).
    hard_total = sum(1 for r in results if r.severity == "hard")
    soft_total = sum(1 for r in results if r.severity == "soft")
    hard_pass = sum(1 for r in results if r.severity == "hard" and r.passed)
    soft_pass = sum(1 for r in results if r.severity == "soft" and r.passed)
    hard_ratio = hard_pass / hard_total if hard_total else 0.0
    soft_ratio = soft_pass / soft_total if soft_total else 0.0
    score = compute_voice_match_score(results)

    return CopyEval(
        fixture_id=fixture.get("id", "?"),
        model="(set by caller)",
        copy_text=copy_text,
        rules=results,
        score=round(score, 4),
        hard_pass_ratio=round(hard_ratio, 4),
        soft_pass_ratio=round(soft_ratio, 4),
    )


def compute_voice_match_score(rules: list[RuleResult]) -> float:
    """v2 weighted voice-match score over VOICE_DIMENSIONS.

    Each dimension contributes ``weight * mean(pass-ratio over its rules)``.
    A missing rule is treated as 0 to keep the function defensive.
    """
    pass_by_id = {r.rule_id: (1.0 if r.passed else 0.0) for r in rules}
    total = 0.0
    for _name, weight, rule_ids in VOICE_DIMENSIONS:
        if not rule_ids:
            continue
        contrib = sum(pass_by_id.get(rid, 0.0) for rid in rule_ids) / len(rule_ids)
        total += weight * contrib
    return total


def apply_batch_rules(results: list["CopyEval"], rules_cfg: dict[str, Any]) -> None:
    """Apply cross-fixture rules R13 and R16 in-place on a batch of evals.

    R13: any 4-gram (configurable size) appearing in more copies than
    ``R13_max_copies_per_ngram`` causes every copy that contains it to fail R13.
    R16: of all copies that contain the muletilla phrase, only the first
    (in input order) keeps R16 passing; subsequent copies fail R16.

    After flipping rule outcomes, recomputes ``score`` and the hard/soft
    ratios so the aggregate report reflects batch context.
    """
    g = rules_cfg.get("global_rules", {})
    n_size = int(g.get("R13_ngram_size", 4))
    max_copies = int(g.get("R13_max_copies_per_ngram", 2))
    muletillas = g.get("R16_muletilla_phrases", [])
    max_per_batch = int(g.get("R16_max_per_batch", 1))

    valid = [r for r in results if r.error is None and r.copy_text]
    if len(valid) < 2:
        return

    # ---- R13: cross-batch n-gram repetition --------------------------------
    ngram_to_copies: dict[tuple[str, ...], set[int]] = {}
    per_copy_ngrams: list[set[tuple[str, ...]]] = []
    for idx, ev in enumerate(valid):
        toks = _word_tokens_lower(ev.copy_text)
        ngs = _ngrams(toks, n_size)
        per_copy_ngrams.append(ngs)
        for ng in ngs:
            ngram_to_copies.setdefault(ng, set()).add(idx)

    overused = {ng for ng, idxs in ngram_to_copies.items() if len(idxs) > max_copies}
    for idx, ev in enumerate(valid):
        if per_copy_ngrams[idx] & overused:
            offenders = sorted(" ".join(ng) for ng in (per_copy_ngrams[idx] & overused))[:3]
            for r in ev.rules:
                if r.rule_id == "R13":
                    r.passed = False
                    r.detail = f"shares {len(per_copy_ngrams[idx] & overused)} 4-gram(s) with >2 copies; e.g. {offenders}"

    # ---- R16: muletilla cap per batch --------------------------------------
    if muletillas:
        seen = 0
        for ev in valid:
            has = any(_count_substr_ci(ev.copy_text, m) > 0 for m in muletillas)
            if not has:
                continue
            seen += 1
            if seen > max_per_batch:
                for r in ev.rules:
                    if r.rule_id == "R16":
                        r.passed = False
                        r.detail = f"{r.detail}; batch cap exceeded ({seen}>{max_per_batch})"

    # ---- Recompute scores --------------------------------------------------
    for ev in valid:
        hard_total = sum(1 for r in ev.rules if r.severity == "hard")
        soft_total = sum(1 for r in ev.rules if r.severity == "soft")
        hard_pass = sum(1 for r in ev.rules if r.severity == "hard" and r.passed)
        soft_pass = sum(1 for r in ev.rules if r.severity == "soft" and r.passed)
        ev.hard_pass_ratio = round(hard_pass / hard_total if hard_total else 0.0, 4)
        ev.soft_pass_ratio = round(soft_pass / soft_total if soft_total else 0.0, 4)
        ev.score = round(compute_voice_match_score(ev.rules), 4)


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

def run_evaluator(
    proposals: list[dict[str, Any]],
    rules_cfg: dict[str, Any],
    *,
    llm_call: Callable[[str, str], str],
    model: str,
    prompt_dir: Path = DEFAULT_PROMPT_DIR,
) -> list[CopyEval]:
    out: list[CopyEval] = []
    fixture_rules = {f["id"]: f for f in rules_cfg.get("per_fixture", [])}
    for prop in proposals:
        try:
            system, user = build_copy_prompt(prop, prompt_dir=prompt_dir)
            copy = llm_call(system, user)
        except Exception as exc:  # noqa: BLE001
            ev = CopyEval(fixture_id=prop["id"], model=model, copy_text="", rules=[], error=f"{type(exc).__name__}: {exc}")
            out.append(ev)
            continue
        # Strip code fences if model wrapped output
        copy_clean = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", copy.strip())
        merged_fixture = {**prop, **fixture_rules.get(prop["id"], {})}
        ev = score_copy(copy_clean, merged_fixture, rules_cfg)
        ev.model = model
        out.append(ev)
    return out


# ------------------------------- Reporting --------------------------------- #

def aggregate(results: Iterable[CopyEval], rules_cfg: dict[str, Any]) -> dict[str, Any]:
    results = [r for r in results if r.error is None]
    if not results:
        return {"score": 0.0, "rule_pass_pct": {}, "n": 0}
    n = len(results)
    score = sum(r.score for r in results) / n
    # per-rule pass rate
    rule_ids = [r.rule_id for r in results[0].rules]
    pass_pct = {rid: 0.0 for rid in rule_ids}
    for r in results:
        for rr in r.rules:
            pass_pct[rr.rule_id] += 1.0 if rr.passed else 0.0
    pass_pct = {rid: round(v / n, 4) for rid, v in pass_pct.items()}
    hard_all_100 = all(pass_pct.get(rid, 0.0) >= 1.0 for rid in HARD_RULES)
    return {
        "n": n,
        "score": round(score, 4),
        "rule_pass_pct": pass_pct,
        "hard_all_100": hard_all_100,
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures-dir", default=str(DEFAULT_FIXTURES_DIR))
    parser.add_argument("--prompt-dir", default=str(DEFAULT_PROMPT_DIR))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--gateway-url", default=DEFAULT_GATEWAY_URL)
    parser.add_argument("--out", default=None, help="output JSON path (auto if omitted)")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--dry-run", action="store_true", help="don't call gateway, emit a fake copy (for smoke)")
    parser.add_argument("--batch-mode", dest="batch_mode", action="store_true", default=True,
                        help="apply cross-fixture R13 (n-gram) and R16 (muletilla) rules (default: on)")
    parser.add_argument("--no-batch-mode", dest="batch_mode", action="store_false",
                        help="disable cross-fixture batch rules (R13/R16 evaluate per-copy only)")
    args = parser.parse_args(argv)

    fixtures_dir = Path(args.fixtures_dir)
    proposals = json.loads((fixtures_dir / "stage7_5_proposals.json").read_text(encoding="utf-8"))
    rules_cfg = json.loads((fixtures_dir / "stage7_5_golden_copies.json").read_text(encoding="utf-8"))

    if args.dry_run:
        def _stub(_s: str, _u: str) -> str:
            return ""
        llm = _stub
    else:
        def _real(s: str, u: str) -> str:
            return call_gateway(s, u, model=args.model, gateway_url=args.gateway_url, temperature=args.temperature)
        llm = _real

    t0 = time.time()
    results = run_evaluator(proposals, rules_cfg, llm_call=llm, model=args.model, prompt_dir=Path(args.prompt_dir))
    if args.batch_mode:
        apply_batch_rules(results, rules_cfg)
    elapsed = round(time.time() - t0, 2)

    agg = aggregate(results, rules_cfg)
    out_path = Path(args.out) if args.out else _next_report_path(DEFAULT_REPORTS_DIR)
    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": args.model,
        "gateway_url": args.gateway_url,
        "elapsed_sec": elapsed,
        "threshold": args.threshold,
        "temperature": args.temperature,
        "batch_mode": args.batch_mode,
        "scoring_version": "v2",
        "aggregate": agg,
        "per_fixture": [
            {**asdict(r), "rules": [asdict(rr) for rr in r.rules]}
            for r in results
        ],
    }
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Stdout summary
    print(f"\n=== Stage 7.5 LinkedIn copy eval — model={args.model} ===")
    print(f"Fixtures evaluated : {agg['n']}/{len(proposals)}")
    print(f"Aggregate score    : {agg['score']:.3f} (threshold {args.threshold:.2f})")
    print(f"Hard rules @ 100%  : {agg['hard_all_100']}")
    print(f"Per-rule pass pct  :")
    for rid, pct in agg["rule_pass_pct"].items():
        sev = "hard" if rid in HARD_RULES else "soft"
        print(f"  {rid:>3} [{sev}] {pct*100:5.1f}%")
    errs = [r for r in results if r.error]
    if errs:
        print(f"\nErrors ({len(errs)}):")
        for r in errs:
            print(f"  {r.fixture_id}: {r.error}")
    print(f"\nReport: {out_path}")

    pass_overall = (
        agg["score"] >= args.threshold
        and agg["hard_all_100"]
        and not errs
    )
    return 0 if pass_overall else 1


if __name__ == "__main__":
    sys.exit(main())
