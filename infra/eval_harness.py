"""Core evaluation harness v0.

Deterministic, offline suites only.  Live service and LLM-as-judge evals are
explicit future extensions, not default behavior.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

from infra.editorial_gold_set import (
    load_dimensions,
    load_gold_set,
    summarize_gold_set,
    validate_dimension_weights,
    validate_gold_set_cases,
)
from scripts.discovery import stage5_rank_candidates as stage5


REPO_ROOT = Path(__file__).resolve().parents[1]
HARNESS_VERSION = "0.1.0"
DEFAULT_REPORT_DIR = Path("reports/evals/generated")

EDITORIAL_SUITE = "editorial_gold_set"
STAGE5_SUITE = "stage5_ranking"
AGENT_OUTPUT_SUITE = "agent_output_gold_set"
ALL_SUITES = (EDITORIAL_SUITE, STAGE5_SUITE, AGENT_OUTPUT_SUITE)

STAGE5_FIXED_NOW = datetime(2026, 5, 7, 18, 0, 0, tzinfo=timezone.utc)
STAGE5_PRECISION_AT_5_THRESHOLD = 0.8

AGENT_OUTPUT_REQUIRED_FIELDS = (
    "id",
    "task",
    "scenario",
    "input",
    "expected_behavior",
    "must_include",
    "must_avoid",
    "evaluation_dimensions",
    "minimum_score",
    "live_allowed_by_default",
)


@dataclass(frozen=True)
class SuiteResult:
    name: str
    status: str
    score: float
    metrics: dict[str, Any]
    evidence: list[str]
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "score": self.score,
            "metrics": self.metrics,
            "evidence": self.evidence,
            "errors": self.errors,
        }


def _require_yaml() -> None:
    if yaml is None:
        raise ImportError("PyYAML is required. Install with: pip install pyyaml")


def _repo_path(repo_root: Path, *parts: str) -> Path:
    return repo_root.joinpath(*parts)


def _status(errors: list[str]) -> str:
    return "fail" if errors else "pass"


def _score(errors: list[str], passed_score: float = 1.0) -> float:
    return 0.0 if errors else passed_score


def run_editorial_gold_set(repo_root: Path = REPO_ROOT) -> SuiteResult:
    """Validate the editorial gold-set data layer."""
    gold_set_path = _repo_path(repo_root, "evals", "editorial", "gold-set-minimum.yaml")
    dimensions_path = _repo_path(repo_root, "evals", "editorial", "dimensions.yaml")

    errors: list[str] = []
    try:
        dimensions = load_dimensions(dimensions_path)
        cases = load_gold_set(gold_set_path)
        errors.extend(validate_dimension_weights(dimensions))
        errors.extend(validate_gold_set_cases(cases, dimensions))
        summary = summarize_gold_set(cases)
    except (FileNotFoundError, ValueError, ImportError) as exc:
        errors.append(str(exc))
        summary = {
            "total_cases": 0,
            "channels_covered": [],
            "input_types_covered": [],
            "audience_stages_covered": [],
            "dimensions_used": [],
            "all_have_human_gate": False,
        }

    return SuiteResult(
        name=EDITORIAL_SUITE,
        status=_status(errors),
        score=_score(errors),
        metrics=summary,
        evidence=[
            str(gold_set_path.relative_to(repo_root)),
            str(dimensions_path.relative_to(repo_root)),
        ],
        errors=errors,
    )


def _make_stage5_db(db_path: Path, rows: list[dict[str, Any]]) -> None:
    con = sqlite3.connect(db_path)
    con.execute(
        """CREATE TABLE discovered_items(
            url_canonica TEXT PRIMARY KEY,
            referente_id TEXT NOT NULL,
            referente_nombre TEXT NOT NULL,
            canal TEXT NOT NULL,
            titulo TEXT,
            publicado_en TEXT,
            primera_vez_visto TEXT NOT NULL,
            promovido_a_candidato_at TEXT,
            notion_page_id TEXT,
            contenido_html TEXT,
            contenido_extraido_at TEXT
        )"""
    )
    for row in rows:
        con.execute(
            "INSERT INTO discovered_items(url_canonica, referente_id, referente_nombre, "
            "canal, titulo, publicado_en, primera_vez_visto, promovido_a_candidato_at, "
            "contenido_html) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                row["url"],
                row.get("ref_id", "ref_x"),
                row.get("ref_nombre", "Ref X"),
                row.get("canal", "rss"),
                row.get("titulo"),
                row.get("publicado_en"),
                "2026-05-01T00:00:00Z",
                "2026-05-02T00:00:00Z",
                row.get("contenido_html"),
            ),
        )
    con.commit()
    con.close()


def _load_stage5_rows(dataset_path: Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
    rows: list[dict[str, Any]] = []
    bucket_by_id: dict[str, str] = {}
    with dataset_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            example = json.loads(line)
            pub_dt = STAGE5_FIXED_NOW - timedelta(
                days=example["publicado_en_offset_days"]
            )
            rows.append(
                {
                    "url": example["id"],
                    "titulo": example["titulo"],
                    "contenido_html": example.get("contenido_html"),
                    "publicado_en": pub_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "canal": example["canal"],
                    "ref_nombre": example["id"],
                }
            )
            bucket_by_id[example["id"]] = example["expected_rank_bucket"]
    return rows, bucket_by_id


def run_stage5_ranking(repo_root: Path = REPO_ROOT) -> SuiteResult:
    """Run deterministic precision@5 for Stage 5 editorial ranking."""
    dataset_path = _repo_path(repo_root, "evals", "stage5_ranking", "dataset.jsonl")
    config_path = _repo_path(repo_root, "config", "aec_keywords.yaml")
    errors: list[str] = []
    metrics: dict[str, Any] = {
        "dataset_cases": 0,
        "precision_at_5": 0.0,
        "threshold": STAGE5_PRECISION_AT_5_THRESHOLD,
        "top5_ids": [],
    }

    try:
        cfg = stage5.load_config(config_path)
        rows, bucket_by_id = _load_stage5_rows(dataset_path)
        metrics["dataset_cases"] = len(rows)
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "state.sqlite"
            _make_stage5_db(db_path, rows)
            con = sqlite3.connect(db_path)
            ranked = stage5.rank(
                stage5.fetch_candidates(con, rerank=False),
                cfg,
                now=STAGE5_FIXED_NOW,
            )
            con.close()
        top5_ids = [row["url_canonica"] for row in ranked[:5]]
        correct = sum(1 for uid in top5_ids if bucket_by_id[uid] == "top")
        precision = correct / 5 if len(top5_ids) == 5 else 0.0
        metrics.update(
            {
                "precision_at_5": round(precision, 4),
                "threshold": STAGE5_PRECISION_AT_5_THRESHOLD,
                "top5_ids": top5_ids,
                "top_bucket_hits": correct,
            }
        )
        if precision < STAGE5_PRECISION_AT_5_THRESHOLD:
            errors.append(
                "precision_at_5 "
                f"{precision:.4f} below threshold {STAGE5_PRECISION_AT_5_THRESHOLD:.4f}"
            )
    except (FileNotFoundError, ValueError, KeyError, json.JSONDecodeError) as exc:
        errors.append(str(exc))

    return SuiteResult(
        name=STAGE5_SUITE,
        status=_status(errors),
        score=_score(errors, float(metrics["precision_at_5"])),
        metrics=metrics,
        evidence=[
            str(dataset_path.relative_to(repo_root)),
            str(config_path.relative_to(repo_root)),
        ],
        errors=errors,
    )


def _load_agent_output_cases(path: Path) -> list[dict[str, Any]]:
    _require_yaml()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "cases" not in data:
        raise ValueError(f"Agent output gold set must have a 'cases' key: {path}")
    cases = data["cases"]
    if not isinstance(cases, list):
        raise ValueError(f"'cases' must be a list: {path}")
    return cases


def _validate_agent_output_cases(cases: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if len(cases) < 5:
        errors.append("Agent output gold set must contain at least 5 cases")

    ids_seen: set[str] = set()
    dimensions_used: set[str] = set()
    for case in cases:
        case_id = case.get("id", "MISSING")
        if not isinstance(case_id, str) or not case_id.startswith("AO-GOLD-"):
            errors.append(f"Case '{case_id}' id must start with 'AO-GOLD-'")
        if case_id in ids_seen:
            errors.append(f"Duplicate case id: {case_id}")
        ids_seen.add(case_id)

        for field in AGENT_OUTPUT_REQUIRED_FIELDS:
            if field not in case:
                errors.append(f"Case '{case_id}' missing required field '{field}'")

        if not isinstance(case.get("input", {}), dict):
            errors.append(f"Case '{case_id}' input must be an object")

        for list_field in (
            "expected_behavior",
            "must_include",
            "must_avoid",
            "evaluation_dimensions",
        ):
            value = case.get(list_field, [])
            if not isinstance(value, list) or not value:
                errors.append(f"Case '{case_id}' {list_field} must be a non-empty list")

        for dim in case.get("evaluation_dimensions", []):
            if isinstance(dim, str):
                dimensions_used.add(dim)

        score = case.get("minimum_score")
        if not isinstance(score, (int, float)) or not 0 <= score <= 1:
            errors.append(f"Case '{case_id}' minimum_score must be between 0 and 1")

        if case.get("live_allowed_by_default") is not False:
            errors.append(f"Case '{case_id}' must be offline by default")

    if len(dimensions_used) < 4:
        errors.append("Agent output gold set must cover at least 4 dimensions")
    return errors


def run_agent_output_gold_set(repo_root: Path = REPO_ROOT) -> SuiteResult:
    """Validate the minimum agent-output gold set for future live evals."""
    gold_set_path = _repo_path(repo_root, "evals", "agent_output", "gold-set-v0.yaml")
    errors: list[str] = []
    metrics: dict[str, Any] = {
        "total_cases": 0,
        "tasks_covered": [],
        "dimensions_used": [],
        "offline_by_default": False,
    }

    try:
        cases = _load_agent_output_cases(gold_set_path)
        errors.extend(_validate_agent_output_cases(cases))
        tasks = sorted({case.get("task", "") for case in cases})
        dimensions = sorted(
            {
                dim
                for case in cases
                for dim in case.get("evaluation_dimensions", [])
                if isinstance(dim, str)
            }
        )
        metrics.update(
            {
                "total_cases": len(cases),
                "tasks_covered": tasks,
                "dimensions_used": dimensions,
                "offline_by_default": all(
                    case.get("live_allowed_by_default") is False for case in cases
                ),
            }
        )
    except (FileNotFoundError, ValueError, ImportError) as exc:
        errors.append(str(exc))

    return SuiteResult(
        name=AGENT_OUTPUT_SUITE,
        status=_status(errors),
        score=_score(errors),
        metrics=metrics,
        evidence=[str(gold_set_path.relative_to(repo_root))],
        errors=errors,
    )


def expand_suites(suites: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    if not suites or "all" in suites:
        return ALL_SUITES
    unknown = sorted(set(suites) - set(ALL_SUITES))
    if unknown:
        raise ValueError(f"Unknown suite(s): {', '.join(unknown)}")
    return tuple(suites)


def run_suites(
    suites: list[str] | tuple[str, ...] = ("all",),
    *,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    selected = expand_suites(suites)
    runners = {
        EDITORIAL_SUITE: run_editorial_gold_set,
        STAGE5_SUITE: run_stage5_ranking,
        AGENT_OUTPUT_SUITE: run_agent_output_gold_set,
    }
    results = [runners[name](repo_root) for name in selected]
    passed = sum(1 for result in results if result.status == "pass")
    failed = len(results) - passed
    overall_status = "pass" if failed == 0 else "fail"
    average_score = (
        round(sum(result.score for result in results) / len(results), 4)
        if results
        else 0.0
    )
    return {
        "harness_version": HARNESS_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "read_only": True,
        "network": "none",
        "llm_calls": 0,
        "overall_status": overall_status,
        "summary": {
            "suites_total": len(results),
            "suites_passed": passed,
            "suites_failed": failed,
            "average_score": average_score,
        },
        "suites": [result.to_dict() for result in results],
    }


def format_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Core Eval Harness Report",
        "",
        f"- Overall: `{report['overall_status']}`",
        f"- Generated: `{report['generated_at']}`",
        f"- Harness: `{report['harness_version']}`",
        f"- Network: `{report['network']}`",
        f"- LLM calls: `{report['llm_calls']}`",
        "",
        "| Suite | Status | Score | Key metric |",
        "|---|---:|---:|---|",
    ]
    for suite in report["suites"]:
        metrics = suite["metrics"]
        if "precision_at_5" in metrics:
            key_metric = f"precision@5={metrics['precision_at_5']}"
        elif "total_cases" in metrics:
            key_metric = f"cases={metrics['total_cases']}"
        else:
            key_metric = "-"
        lines.append(
            f"| `{suite['name']}` | `{suite['status']}` | "
            f"{suite['score']:.4f} | {key_metric} |"
        )

    failures = [suite for suite in report["suites"] if suite["errors"]]
    if failures:
        lines.extend(["", "## Failures"])
        for suite in failures:
            lines.append(f"- `{suite['name']}`: {'; '.join(suite['errors'])}")

    return "\n".join(lines) + "\n"


def write_report_files(
    report: dict[str, Any],
    output_dir: Path = DEFAULT_REPORT_DIR,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json = output_dir / "core-eval-harness-latest.json"
    latest_md = output_dir / "core-eval-harness-latest.md"
    latest_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    latest_md.write_text(format_markdown_report(report), encoding="utf-8")
    return {"json": latest_json, "markdown": latest_md}
