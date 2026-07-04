"""Tests PIT-DEV — pit_traceability_check (cadena completa y con gaps).

Verifican el script de trazabilidad post-torneo contra un vault fabricado en
tmpdir: cadena completa ⇒ TRACE_COMPLETE (exit 0, report.md escrito); eslabones
faltantes ⇒ TRACE_GAPS con la lista (exit 1); artefactos corruptos ⇒
UNVERIFIABLE. Sin red, sin Docker, sin binario openclaw.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

from scripts.pit.pit_traceability_check import (
    MISSING,
    PRESENT,
    TRACE_COMPLETE,
    UNVERIFIABLE,
    check_traceability,
    main,
    write_report,
)

PIT_ID = "pit-dev-trace"
LANE_IDS = ["lane-alpha", "lane-beta"]


def _make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    for folder in ("pit", "templates", "archive"):
        (vault / folder).mkdir(parents=True)
    (vault / "README.md").write_text("# v\n", encoding="utf-8")
    return vault


def _full_chain(vault: Path) -> Path:
    """Fabrica la cadena COMPLETA de un torneo dev en el vault."""
    pit_root = vault / "pit" / PIT_ID
    spec_dir = pit_root / "spec"
    spec_dir.mkdir(parents=True)
    (spec_dir / "pit_spec.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 3,
                "mode": "dev",
                "pit_id": PIT_ID,
                "title": "t",
                "problem_statement": "p",
                "deliverable_spec": "d",
                "repo_ref": "HEAD",
                "lane_count": 2,
                "iteration_count": 2,
                "budget_usd": 10,
                "security_monitor": "required",
                "traceability": "required",
            }
        ),
        encoding="utf-8",
    )
    (spec_dir / "lanes.yaml").write_text(
        yaml.safe_dump(
            {"lanes": [{"lane_id": lane_id, "lane_focus": "f"} for lane_id in LANE_IDS]}
        ),
        encoding="utf-8",
    )
    (spec_dir / "agents.yaml").write_text(
        yaml.safe_dump(
            {
                "pit_id": PIT_ID,
                "agents": [
                    {"lane_id": lane_id, "agent_id": f"{PIT_ID}-{lane_id}"}
                    for lane_id in LANE_IDS
                ],
            }
        ),
        encoding="utf-8",
    )
    for lane_id in LANE_IDS:
        lane_root = pit_root / "lanes" / lane_id
        workspace = lane_root / "workspace"
        (workspace / "snapshot").mkdir(parents=True)
        (workspace / "snapshot" / "README.md").write_text("# snap\n", encoding="utf-8")
        (workspace / "CONTEXT_INDEX.md").write_text("# índice\n", encoding="utf-8")
        iteration = lane_root / "iterations" / "1"
        iteration.mkdir(parents=True)
        (iteration / "egress.jsonl").write_text(
            json.dumps(
                {
                    "lane_id": lane_id,
                    "iteration": 1,
                    "url_or_query": "https://example.org",
                    "purpose": "docs",
                    "timestamp": "2026-07-03T00:00:00Z",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (iteration / "test_report.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "pit_id": PIT_ID,
                    "lane_id": lane_id,
                    "iteration": 1,
                    "command": [sys.executable, "-c", "pass"],
                    "workdir": "deliverable",
                    "exit_code": 0,
                    "total": 1,
                    "passed": 1,
                    "failed": 0,
                }
            ),
            encoding="utf-8",
        )
        (lane_root / "announce.md").write_text(
            "\n".join(
                [
                    f"DELIVERABLE_PATH=pit/{PIT_ID}/lanes/{lane_id}/deliverable/",
                    f"TEST_REPORT=pit/{PIT_ID}/lanes/{lane_id}/iterations/1/test_report.json",
                    "SELF_ASSESSMENT=0.8",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
    scorecards = pit_root / "judge" / "scorecards"
    scorecards.mkdir(parents=True)
    for judge_id in ("judge-1", "judge-2"):
        for lane_id in LANE_IDS:
            (scorecards / f"{judge_id}--{lane_id}.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "pit_id": PIT_ID,
                        "lane_id": lane_id,
                        "judge_id": judge_id,
                        "installed_clean": True,
                        "ran": True,
                        "own_tests_passed": True,
                        "meets_functional_spec": True,
                        # Hardening post pit-dev-ifc-viewer: true exige
                        # evidencia de input real en el scorecard.
                        "functional_evidence": {
                            "real_input_used": True,
                            "input_description": "input real 2MB verificado end-to-end",
                        },
                        "criteria": {
                            "funcionalidad": 0.9,
                            "robustez": 0.8,
                            "dx": 0.7,
                            "docs": 0.8,
                            "testabilidad": 0.9,
                        },
                    }
                ),
                encoding="utf-8",
            )
    outcome = pit_root / "outcome"
    outcome.mkdir(parents=True)
    (outcome / "pit_outcome_report.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "pit_id": PIT_ID, "title": "t"}),
        encoding="utf-8",
    )
    deliverables = pit_root / "deliverables"
    deliverables.mkdir(parents=True)
    (deliverables / f"{PIT_ID}-outcome-deck.pptx").write_bytes(b"PK\x03\x04fake")
    return pit_root


class TestFullChain:
    def test_complete_chain_is_trace_complete(self, tmp_path):
        vault = _make_vault(tmp_path)
        _full_chain(vault)
        result = check_traceability(vault, PIT_ID)
        assert result["verdict"] == TRACE_COMPLETE, result["links"]
        assert result["complete"] and result["gaps"] == []
        assert all(link["status"] == PRESENT for link in result["links"])
        # los 9 eslabones de la cadena, en orden
        assert [link["link"] for link in result["links"]] == [
            "spec",
            "lanes.yaml",
            "agents.yaml",
            "workspace_init",
            "iterations",
            "announce.md",
            "judge_scorecards",
            "outcome_report",
            "deck_deliverables",
        ]

    def test_report_md_is_written_into_the_vault(self, tmp_path):
        vault = _make_vault(tmp_path)
        _full_chain(vault)
        result = check_traceability(vault, PIT_ID)
        report_path = write_report(vault, result)
        assert report_path == vault / "pit" / PIT_ID / "traceability" / "report.md"
        text = report_path.read_text(encoding="utf-8")
        assert TRACE_COMPLETE in text and "| spec | PRESENT |" in text

    def test_cli_exit_zero_and_writes_report(self, tmp_path, capsys):
        vault = _make_vault(tmp_path)
        _full_chain(vault)
        rc = main(["--pit-id", PIT_ID, "--vault-path", str(vault)])
        assert rc == 0
        assert (vault / "pit" / PIT_ID / "traceability" / "report.md").is_file()
        assert TRACE_COMPLETE in capsys.readouterr().out

    def test_telegram_pack_counts_as_deck_deliverable(self, tmp_path):
        vault = _make_vault(tmp_path)
        pit_root = _full_chain(vault)
        (pit_root / "deliverables" / f"{PIT_ID}-outcome-deck.pptx").unlink()
        (pit_root / "deliverables" / "telegram_pack.json").write_text(
            "{}", encoding="utf-8"
        )
        result = check_traceability(vault, PIT_ID)
        assert result["verdict"] == TRACE_COMPLETE


class TestGaps:
    def test_missing_links_produce_trace_gaps_with_list(self, tmp_path):
        vault = _make_vault(tmp_path)
        pit_root = _full_chain(vault)
        # Rompe DOS eslabones: judge scorecards y outcome.
        for path in (pit_root / "judge" / "scorecards").glob("*.json"):
            path.unlink()
        (pit_root / "outcome" / "pit_outcome_report.yaml").unlink()
        result = check_traceability(vault, PIT_ID)
        assert not result["complete"]
        assert result["verdict"].startswith("TRACE_GAPS(")
        assert set(result["gaps"]) == {"judge_scorecards", "outcome_report"}
        statuses = {link["link"]: link["status"] for link in result["links"]}
        assert statuses["judge_scorecards"] == MISSING
        assert statuses["outcome_report"] == MISSING

    def test_gap_report_tells_rick_not_to_fix(self, tmp_path):
        vault = _make_vault(tmp_path)
        pit_root = _full_chain(vault)
        (pit_root / "outcome" / "pit_outcome_report.yaml").unlink()
        result = check_traceability(vault, PIT_ID)
        report_path = write_report(vault, result)
        text = report_path.read_text(encoding="utf-8")
        assert "NO arregla nada" in text
        assert "mejora continua" in text

    def test_cli_exit_one_on_gaps(self, tmp_path):
        vault = _make_vault(tmp_path)
        pit_root = _full_chain(vault)
        (pit_root / "outcome" / "pit_outcome_report.yaml").unlink()
        rc = main(["--pit-id", PIT_ID, "--vault-path", str(vault)])
        assert rc == 1

    def test_corrupt_egress_marks_iterations_unverifiable(self, tmp_path):
        vault = _make_vault(tmp_path)
        pit_root = _full_chain(vault)
        (pit_root / "lanes" / "lane-alpha" / "iterations" / "1" / "egress.jsonl").write_text(
            "{not json\n", encoding="utf-8"
        )
        result = check_traceability(vault, PIT_ID)
        statuses = {link["link"]: link["status"] for link in result["links"]}
        assert statuses["iterations"] == UNVERIFIABLE
        assert "iterations" in result["gaps"]

    def test_announce_without_literal_lines_is_unverifiable(self, tmp_path):
        vault = _make_vault(tmp_path)
        pit_root = _full_chain(vault)
        (pit_root / "lanes" / "lane-beta" / "announce.md").write_text(
            "terminé, todo ok\n", encoding="utf-8"
        )
        result = check_traceability(vault, PIT_ID)
        statuses = {link["link"]: link["status"] for link in result["links"]}
        assert statuses["announce.md"] == UNVERIFIABLE

    def test_missing_workspace_is_a_gap(self, tmp_path):
        vault = _make_vault(tmp_path)
        pit_root = _full_chain(vault)
        import shutil

        shutil.rmtree(pit_root / "lanes" / "lane-alpha" / "workspace")
        result = check_traceability(vault, PIT_ID)
        statuses = {link["link"]: link["status"] for link in result["links"]}
        assert statuses["workspace_init"] == MISSING


class TestInputErrors:
    def test_unknown_tournament_exits_two(self, tmp_path, capsys):
        vault = _make_vault(tmp_path)
        rc = main(["--pit-id", "pit-no-existe", "--vault-path", str(vault)])
        assert rc == 2
        assert "not found" in capsys.readouterr().err

    def test_bad_pit_id_raises(self, tmp_path):
        vault = _make_vault(tmp_path)
        with pytest.raises(ValueError, match="pit_id"):
            check_traceability(vault, "NOT VALID")
