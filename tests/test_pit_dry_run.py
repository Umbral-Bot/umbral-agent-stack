"""Tests for the PIT-2 tournament dry run (smoke local, sin spawn OpenClaw)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.pit.pit_dry_run import DRY_RUN_PASS, main, run_dry_run

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_SPEC = REPO_ROOT / "examples" / "pit-salud-mental-pilot.yaml"
DRY_RUN_SH = REPO_ROOT / "scripts" / "pit" / "pit_tournament_dry_run.sh"

_BASH = shutil.which("bash")


class TestDryRunPython:
    def test_full_smoke_with_example_spec(self, tmp_path):
        evidence = tmp_path / "evidence"
        metrics = run_dry_run(EXAMPLE_SPEC, evidence_dir=evidence)

        assert metrics["verdict"] == DRY_RUN_PASS
        assert metrics["dry_run"] is True
        assert metrics["pit_id"] == "pit-salud-mental-pilot"
        assert metrics["preflight_verdict"] == "PIT_PREFLIGHT_PASS"
        assert metrics["lane_count"] == 3
        assert metrics["iterations_simulated"] == 1
        assert metrics["iteration_count_spec"] == 5
        # Hard constraints del smoke: sin internet, sin Magnific, sin spawn.
        assert metrics["constraints"] == {
            "internet": False,
            "magnific": False,
            "sessions_spawn": False,
        }

    def test_final_metrics_persisted_in_evidence_dir(self, tmp_path):
        evidence = tmp_path / "evidence"
        metrics = run_dry_run(EXAMPLE_SPEC, evidence_dir=evidence)

        metrics_path = evidence / "final-metrics.json"
        assert metrics_path.is_file()
        on_disk = json.loads(metrics_path.read_text(encoding="utf-8"))
        assert on_disk["verdict"] == metrics["verdict"]
        assert on_disk["kind"] == "pit_dry_run_final_metrics"

    def test_lanes_complete_with_deterministic_fulfillment(self, tmp_path):
        metrics = run_dry_run(EXAMPLE_SPEC, evidence_dir=tmp_path / "e")

        lanes = metrics["lanes"]
        assert [lane["lane_id"] for lane in lanes] == [
            "lane-dry-a",
            "lane-dry-b",
            "lane-dry-c",
        ]
        assert all(lane["lane_complete"] for lane in lanes)
        # Factores deterministas (0.6, 0.8, 1.0) ⇒ fulfillment == factor.
        assert [lane["fulfillment"] for lane in lanes] == [0.6, 0.8, 1.0]
        assert metrics["winner_candidate"] == {
            "lane_id": "lane-dry-c",
            "fulfillment": 1.0,
        }
        for lane in lanes:
            assert lane["prototype_url"].startswith("https://dry-run.invalid/")
            lines = lane["announce"].splitlines()
            assert lines[0].startswith("PROTOTYPE_URL=")
            assert lines[1].startswith("KPI_PACK=pit/pit-salud-mental-pilot/lanes/")
            assert lines[2].startswith("FULFILLMENT=")

    def test_budget_kill_switch_stub_in_metrics(self, tmp_path):
        metrics = run_dry_run(EXAMPLE_SPEC, evidence_dir=tmp_path / "e")

        budget = metrics["budget"]
        assert budget["budget_usd"] == 200
        assert budget["max_cost_estimate_usd"] == 200
        assert budget["estimated_spend_usd"] == 0.0
        assert budget["kill_switch"]["threshold_pct"] == 100
        assert budget["kill_switch"]["enforced"] is False
        assert budget["kill_switch"]["enforcement_milestone"] == "PIT-3"

    def test_scratch_vault_has_lane_artifacts_and_synthetic_labels(self, tmp_path):
        metrics = run_dry_run(EXAMPLE_SPEC, evidence_dir=tmp_path / "e")

        vault = Path(metrics["vault_path"])
        for lane in metrics["lanes"]:
            lane_root = vault / "pit" / metrics["pit_id"] / "lanes" / lane["lane_id"]
            assert (lane_root / "kanban" / "board.md").is_file()
            pack_path = lane_root / "iterations" / "1" / "kpi_pack.json"
            assert pack_path.is_file()
            pack = json.loads(pack_path.read_text(encoding="utf-8"))
            # Señales fake = sintéticas, SIEMPRE etiquetadas.
            assert all(kpi["synthetic"] is True for kpi in pack["kpis"])
            assert pack["synthetic_personas"]["labeled"] is True
            assert pack["hypothesis"]["validated"] is None

    def test_main_exit_codes(self, tmp_path):
        ok = main([str(EXAMPLE_SPEC), "--evidence-dir", str(tmp_path / "ok")])
        assert ok == 0

        bad_spec = tmp_path / "bad.yaml"
        bad_spec.write_text("pit_id: pit-bad\n", encoding="utf-8")
        assert main([str(bad_spec), "--evidence-dir", str(tmp_path / "bad")]) == 1

    def test_write_scope_env_restored(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PIT_VAULT_WRITE_SCOPE", "custom")
        run_dry_run(EXAMPLE_SPEC, evidence_dir=tmp_path / "e")

        assert os.environ["PIT_VAULT_WRITE_SCOPE"] == "custom"

    def test_broken_vault_path_raises(self, tmp_path):
        # Vault path forzado a un archivo (no dir) no puede bootstrappearse.
        not_a_dir = tmp_path / "file.txt"
        not_a_dir.write_text("x", encoding="utf-8")
        with pytest.raises(OSError):
            run_dry_run(EXAMPLE_SPEC, evidence_dir=tmp_path / "e", vault_path=not_a_dir)


@pytest.mark.skipif(_BASH is None, reason="bash not available")
class TestDryRunShellWrapper:
    def test_wrapper_runs_and_writes_metrics(self, tmp_path):
        evidence = tmp_path / "evidence"
        result = subprocess.run(
            [_BASH, str(DRY_RUN_SH), str(EXAMPLE_SPEC), str(evidence)],
            capture_output=True,
            text=True,
            timeout=120,
        )

        assert result.returncode == 0, result.stderr or result.stdout
        assert "PIT_DRY_RUN_PASS" in result.stdout
        assert (evidence / "final-metrics.json").is_file()
