#!/usr/bin/env python3
"""Driver: real Stage 7.5 multi-format eval matrix.

Runs ``score_copy_<format>`` for each combination of (format × fixture × temperature)
against the OpenClaw gateway and writes a single consolidated JSON report.

Usage:
    python -m scripts.discovery.run_stage7_5_multiformat_real \
        --formats linkedin_standalone,linkedin_share,blog \
        --fixture-ids F1-bim-only-clash-detection,F2-ai-disrupcion-arq,F3-iot-edificios-energia,F4-ifc-export-revit-pain \
        --temperatures 0.3,0.7,1.0 \
        --model openclaw/main

Output:
    reports/stage7_5_multiformat_real_v<n>.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

from scripts.discovery import eval_stage7_5_copy as e
from scripts.discovery import stage7_5_copy_writer as w

DEFAULT_FIXTURES_DIR = Path("tests/discovery/fixtures")
DEFAULT_REPORTS_DIR = Path("reports")


def _next_report_path(reports_dir: Path) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(reports_dir.glob("stage7_5_multiformat_real_v*.json"))
    nums: list[int] = []
    for p in existing:
        try:
            nums.append(int(p.stem.rsplit("v", 1)[-1]))
        except ValueError:
            pass
    nxt = (max(nums) + 1) if nums else 1
    return reports_dir / f"stage7_5_multiformat_real_v{nxt}.json"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--fixtures-dir", default=str(DEFAULT_FIXTURES_DIR))
    p.add_argument("--prompt-dir", default=str(w.PROMPT_DIR_DEFAULT))
    p.add_argument("--model", default="openclaw/main")
    p.add_argument("--gateway-url", default="http://127.0.0.1:18789")
    p.add_argument("--formats", default="linkedin_standalone,linkedin_share,blog")
    p.add_argument("--fixture-ids", default="",
                   help="Comma-separated fixture IDs; empty = all")
    p.add_argument("--temperatures", default="0.3,0.7,1.0")
    p.add_argument("--out", default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    fixtures_dir = Path(args.fixtures_dir)
    proposals_all = json.loads((fixtures_dir / "stage7_5_proposals.json").read_text(encoding="utf-8"))
    rules_cfg = json.loads((fixtures_dir / "stage7_5_golden_copies.json").read_text(encoding="utf-8"))

    fixture_ids = [s.strip() for s in args.fixture_ids.split(",") if s.strip()]
    if fixture_ids:
        proposals = [p for p in proposals_all if p["id"] in fixture_ids]
        missing = set(fixture_ids) - {p["id"] for p in proposals}
        if missing:
            print(f"ERROR: unknown fixture ids: {sorted(missing)}", file=sys.stderr)
            return 2
    else:
        proposals = proposals_all

    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    for f in formats:
        if f not in e.FORMAT_NAMES_EVAL:
            print(f"ERROR: unknown format {f!r}", file=sys.stderr)
            return 2
    temperatures = [float(t) for t in args.temperatures.split(",") if t.strip()]

    n_calls = len(formats) * len(proposals) * len(temperatures)
    print(f"Matrix: formats={formats} fixtures={[p['id'] for p in proposals]} "
          f"temps={temperatures} → {n_calls} LLM calls")

    if args.dry_run:
        def make_llm(_t: float):
            return lambda s, u: ""
    else:
        def make_llm(t: float):
            def _call(system: str, user: str) -> str:
                return e.call_gateway(
                    system, user, model=args.model,
                    gateway_url=args.gateway_url, temperature=t,
                )
            return _call

    rows: list[dict] = []
    t_start = time.time()
    for fmt in formats:
        for temp in temperatures:
            print(f"\n>>> format={fmt} temp={temp}")
            llm = make_llm(temp)
            results = e.run_evaluator(
                proposals, rules_cfg, llm_call=llm, model=args.model,
                prompt_dir=Path(args.prompt_dir), format_name=fmt,
            )
            for r in results:
                row = asdict(r)
                row["rules"] = [asdict(rr) for rr in r.rules]
                row["format"] = fmt
                row["temperature"] = temp
                rows.append(row)
                status = "ERR" if r.error else f"score={r.score:.3f}"
                print(f"  {r.fixture_id}: {status}")

    elapsed = round(time.time() - t_start, 2)

    # Aggregate per (format, temp)
    agg: dict = {}
    for fmt in formats:
        agg[fmt] = {}
        for temp in temperatures:
            slice_rows = [r for r in rows if r["format"] == fmt and r["temperature"] == temp and r["error"] is None]
            if not slice_rows:
                agg[fmt][str(temp)] = {"n": 0, "score": 0.0, "errors": 1}
                continue
            n = len(slice_rows)
            score = sum(r["score"] for r in slice_rows) / n
            agg[fmt][str(temp)] = {
                "n": n,
                "score": round(score, 4),
                "hard_pass_avg": round(
                    sum(r["hard_pass_ratio"] for r in slice_rows) / n, 4),
                "soft_pass_avg": round(
                    sum(r["soft_pass_ratio"] for r in slice_rows) / n, 4),
            }

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": args.model,
        "gateway_url": args.gateway_url,
        "formats": formats,
        "fixture_ids": [p["id"] for p in proposals],
        "temperatures": temperatures,
        "n_calls": n_calls,
        "elapsed_sec": elapsed,
        "aggregate_per_format_temp": agg,
        "rows": rows,
    }
    out_path = Path(args.out) if args.out else _next_report_path(DEFAULT_REPORTS_DIR)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== Aggregate (score per format × temp) ===")
    for fmt in formats:
        for temp in temperatures:
            a = agg[fmt][str(temp)]
            print(f"  {fmt:>22s} t={temp}: n={a.get('n')} score={a.get('score', 0.0):.3f}")
    print(f"\nReport: {out_path}")
    print(f"Elapsed: {elapsed}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
