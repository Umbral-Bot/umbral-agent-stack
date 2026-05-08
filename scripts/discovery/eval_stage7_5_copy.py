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
DEFAULT_THRESHOLD = 0.80

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
HASHTAG_RE = re.compile(r"#[A-Za-z][A-Za-z0-9_]*")


# ----------------------------- Rule definitions ----------------------------- #

HARD_RULES = ("R1", "R2", "R4", "R5", "R7", "R8", "R9", "R11")
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

    # Aggregate
    hard_total = sum(1 for r in results if r.severity == "hard")
    soft_total = sum(1 for r in results if r.severity == "soft")
    hard_pass = sum(1 for r in results if r.severity == "hard" and r.passed)
    soft_pass = sum(1 for r in results if r.severity == "soft" and r.passed)
    hard_ratio = hard_pass / hard_total if hard_total else 0.0
    soft_ratio = soft_pass / soft_total if soft_total else 0.0
    score = 0.7 * hard_ratio + 0.3 * soft_ratio

    return CopyEval(
        fixture_id=fixture.get("id", "?"),
        model="(set by caller)",
        copy_text=copy_text,
        rules=results,
        score=round(score, 4),
        hard_pass_ratio=round(hard_ratio, 4),
        soft_pass_ratio=round(soft_ratio, 4),
    )


# --------------------- Multi-format scoring (Stage 7.5 multiformat) -------- #
#
# Per-format wrappers around ``score_copy`` that apply the format-specific
# rule overrides defined in ``stage7_5_golden_copies.json`` under the
# ``formats`` block. Universal rules (R7 emojis, R8 marketing-slop, R9
# register, R11 CTA, R12 disciplines) are kept identical across formats.
# Length, hashtag count, paragraph count and source/blog URL requirements
# are remapped per format.

FORMAT_NAMES_EVAL = ("linkedin_standalone", "linkedin_share", "blog")


def _format_overrides(rules_cfg: dict[str, Any], format_name: str) -> dict[str, Any]:
    """Return a deep-copy of ``rules_cfg`` with ``global_rules`` overridden
    by the per-format settings in ``rules_cfg['formats'][format_name]``.

    If the ``formats`` block is missing (legacy fixture file), the base
    ``rules_cfg`` is returned unchanged — in which case scoring degrades
    gracefully to the linkedin_standalone defaults.
    """
    if format_name not in FORMAT_NAMES_EVAL:
        raise ValueError(f"unknown format {format_name!r}")
    fmt_cfg = (rules_cfg.get("formats") or {}).get(format_name)
    if fmt_cfg is None:
        return rules_cfg
    out = json.loads(json.dumps(rules_cfg))  # cheap deep-copy
    g = out["global_rules"]
    # Length
    g["R1_total_len_min"] = int(fmt_cfg.get("total_len_min", g["R1_total_len_min"]))
    g["R1_total_len_max"] = int(fmt_cfg.get("total_len_max", g["R1_total_len_max"]))
    g["R2_hook_max_chars"] = int(fmt_cfg.get("hook_max_chars", g["R2_hook_max_chars"]))
    g["R3_body_min"] = int(fmt_cfg.get("body_min", g["R3_body_min"]))
    g["R3_body_max"] = int(fmt_cfg.get("body_max", g["R3_body_max"]))
    # Hashtags
    g["R5_hashtag_min"] = int(fmt_cfg.get("hashtag_min", g["R5_hashtag_min"]))
    g["R5_hashtag_max"] = int(fmt_cfg.get("hashtag_max", g["R5_hashtag_max"]))
    # Paragraphs
    g["R10_min_paragraphs"] = int(fmt_cfg.get("min_paragraphs", g["R10_min_paragraphs"]))
    out["_active_format"] = format_name
    out["_format_cfg"] = fmt_cfg
    return out


def _maybe_swap_url_rule(ev: CopyEval, copy_text: str, fixture: dict[str, Any],
                        format_name: str) -> CopyEval:
    """For ``linkedin_share`` and ``blog``, R4 semantics shift:

      * linkedin_share: R4 must check ``blog_url`` substring (NOT source_url).
      * blog: R4 keeps source_url semantics (already correct).

    For blog format additionally adds R13_blog_h1 rule (hard).
    """
    if format_name == "linkedin_share":
        blog_url = fixture.get("blog_url") or ""
        for r in ev.rules:
            if r.rule_id == "R4":
                r.description = "Contains blog URL"
                r.passed = bool(blog_url) and (blog_url in copy_text)
                r.detail = f"blog_url_present={r.passed}"
                break
    if format_name == "blog":
        h1_ok = bool(re.search(r"^\s*#\s+\S+", copy_text, re.MULTILINE))
        ev.rules.append(RuleResult(
            "R13", "Blog has H1 (line starting with '# ')", h1_ok, "hard",
            f"h1_present={h1_ok}",
        ))
        # Recompute aggregates after appending
        hard_total = sum(1 for r in ev.rules if r.severity == "hard")
        soft_total = sum(1 for r in ev.rules if r.severity == "soft")
        hard_pass = sum(1 for r in ev.rules if r.severity == "hard" and r.passed)
        soft_pass = sum(1 for r in ev.rules if r.severity == "soft" and r.passed)
        hard_ratio = hard_pass / hard_total if hard_total else 0.0
        soft_ratio = soft_pass / soft_total if soft_total else 0.0
        ev.score = round(0.7 * hard_ratio + 0.3 * soft_ratio, 4)
        ev.hard_pass_ratio = round(hard_ratio, 4)
        ev.soft_pass_ratio = round(soft_ratio, 4)
    return ev


def score_copy_standalone(copy_text: str, fixture: dict[str, Any],
                          rules_cfg: dict[str, Any]) -> CopyEval:
    """Score copy assuming linkedin_standalone format (= legacy ``score_copy``)."""
    cfg = _format_overrides(rules_cfg, "linkedin_standalone")
    ev = score_copy(copy_text, fixture, cfg)
    return _maybe_swap_url_rule(ev, copy_text, fixture, "linkedin_standalone")


def score_copy_share(copy_text: str, fixture: dict[str, Any],
                     rules_cfg: dict[str, Any]) -> CopyEval:
    """Score copy assuming linkedin_share format (short, links to blog_url)."""
    cfg = _format_overrides(rules_cfg, "linkedin_share")
    ev = score_copy(copy_text, fixture, cfg)
    return _maybe_swap_url_rule(ev, copy_text, fixture, "linkedin_share")


def score_copy_blog(copy_text: str, fixture: dict[str, Any],
                    rules_cfg: dict[str, Any]) -> CopyEval:
    """Score copy assuming blog format (long-form, no hashtags, requires H1)."""
    cfg = _format_overrides(rules_cfg, "blog")
    ev = score_copy(copy_text, fixture, cfg)
    return _maybe_swap_url_rule(ev, copy_text, fixture, "blog")


SCORERS_BY_FORMAT = {
    "linkedin_standalone": score_copy_standalone,
    "linkedin_share": score_copy_share,
    "blog": score_copy_blog,
}


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
    format_name: str = "linkedin_standalone",
) -> list[CopyEval]:
    """Run the evaluator across all proposals for a single ``format_name``.

    For the legacy ``linkedin_standalone`` format the existing
    ``build_copy_prompt`` (linkedin-copy-{system,user}.md) is used to keep
    backward compat with the v1 voice fixture; for the other formats the
    writer's ``build_format_prompt`` is used so prompt content stays in
    sync between writer and evaluator.
    """
    out: list[CopyEval] = []
    fixture_rules = {f["id"]: f for f in rules_cfg.get("per_fixture", [])}
    scorer = SCORERS_BY_FORMAT.get(format_name, score_copy_standalone)
    use_writer_loader = format_name in ("linkedin_share", "blog")
    if use_writer_loader:
        # Lazy import — keeps the evaluator usable even if the writer
        # module fails to import for unrelated reasons (e.g. missing httpx).
        from scripts.discovery.stage7_5_copy_writer import (  # type: ignore
            build_format_prompt as _writer_build,
        )
    for prop in proposals:
        try:
            if use_writer_loader:
                system, user = _writer_build(format_name, prop, prompt_dir=prompt_dir)
            else:
                system, user = build_copy_prompt(prop, prompt_dir=prompt_dir)
            copy = llm_call(system, user)
        except Exception as exc:  # noqa: BLE001
            ev = CopyEval(fixture_id=prop["id"], model=model, copy_text="",
                          rules=[], error=f"{type(exc).__name__}: {exc}")
            out.append(ev)
            continue
        # Strip code fences if model wrapped output
        copy_clean = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", copy.strip())
        merged_fixture = {**prop, **fixture_rules.get(prop["id"], {})}
        ev = scorer(copy_clean, merged_fixture, rules_cfg)
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
    parser.add_argument(
        "--format", dest="format_name",
        default="linkedin_standalone",
        choices=list(FORMAT_NAMES_EVAL),
        help="Copy format to evaluate. Default: linkedin_standalone (legacy).",
    )
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
    results = run_evaluator(
        proposals, rules_cfg, llm_call=llm, model=args.model,
        prompt_dir=Path(args.prompt_dir), format_name=args.format_name,
    )
    elapsed = round(time.time() - t0, 2)

    agg = aggregate(results, rules_cfg)
    out_path = Path(args.out) if args.out else _next_report_path(DEFAULT_REPORTS_DIR)
    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": args.model,
        "format": args.format_name,
        "gateway_url": args.gateway_url,
        "elapsed_sec": elapsed,
        "threshold": args.threshold,
        "aggregate": agg,
        "per_fixture": [
            {**asdict(r), "rules": [asdict(rr) for rr in r.rules]}
            for r in results
        ],
    }
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Stdout summary
    print(f"\n=== Stage 7.5 copy eval — model={args.model} format={args.format_name} ===")
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
