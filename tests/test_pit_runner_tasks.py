"""Tests for PIT-2 runner: core (scripts/pit/pit_runner_core) + Worker tasks pit.*."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.pit import pit_runner_core as core
from scripts.pit.pit_spec_validate import compute_fulfillment
from worker.tasks import TASK_HANDLERS
from worker.tasks.pit_runner import (
    handle_pit_iteration_close,
    handle_pit_lane_announce,
    handle_pit_lane_init,
    handle_pit_preflight,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_SPEC = REPO_ROOT / "examples" / "pit-salud-mental-pilot.yaml"

PIT_ID = "pit-salud-mental-pilot"
LANE_ID = "lane-friccion"


def _make_vault(tmp_path: Path) -> Path:
    """Vault scratch válido para pit_vault_check (README + pit/templates/archive)."""
    vault = tmp_path / "vault"
    for folder in ("pit", "templates", "archive"):
        (vault / folder).mkdir(parents=True)
    (vault / "README.md").write_text("# scratch pit vault\n", encoding="utf-8")
    (vault / ".gitignore").write_text(".obsidian/workspace.json\n", encoding="utf-8")
    for template in core.TEMPLATES_DIR.iterdir():
        if template.is_file():
            shutil.copyfile(template, vault / "templates" / template.name)
    return vault


def _hypothesis(**overrides) -> dict:
    base = {
        "variable": "taps hasta completar el check-in",
        "statement": "Si bajo los taps de 5 a 2, sube checkin_completion",
        "kpi_id": "checkin_completion",
        "validated": True,
    }
    base.update(overrides)
    return base


def _kpis() -> list[dict]:
    return [
        {
            "kpi_id": "checkin_completion",
            "unit": "%",
            "kpi_expected": 60,
            "kpi_achieved": 30,
            "direction": "increase",
            "weight": 2.0,
            "synthetic": True,
        },
        {
            "kpi_id": "time_to_checkin",
            "unit": "segundos",
            "kpi_expected": 30,
            "kpi_achieved": 30,
            "direction": "decrease",
        },
    ]


def _init_lane(vault: Path) -> dict:
    return core.lane_init(vault, PIT_ID, LANE_ID, research_profile="mixed")


# ---------------------------------------------------------------------------
# pit.preflight
# ---------------------------------------------------------------------------


class TestPreflight:
    def test_pass_with_example_spec_and_valid_vault(self, tmp_path):
        vault = _make_vault(tmp_path)
        result = core.preflight(EXAMPLE_SPEC, vault)

        assert result["ok"] is True
        assert result["verdict"] == "PIT_PREFLIGHT_PASS"
        assert result["spec"]["status"] == "pass"
        assert result["vault"]["status"] == "pass"
        assert result["errors"] == []

    def test_budget_block_is_kill_switch_stub(self, tmp_path):
        vault = _make_vault(tmp_path)
        budget = core.preflight(EXAMPLE_SPEC, vault)["budget"]

        assert budget["budget_usd"] == 200
        assert budget["budget_per_lane_usd"] == round(200 / 3, 2)
        # Stub PIT-2: budget = max cost estimate; corte duro documentado, no aplicado.
        assert budget["max_cost_estimate_usd"] == 200
        assert budget["kill_switch"] == {
            "threshold_pct": 100,
            "enforced": False,
            "enforcement_milestone": "PIT-3",
        }

    def test_fails_on_invalid_spec(self, tmp_path):
        vault = _make_vault(tmp_path)
        bad_spec = tmp_path / "bad.yaml"
        bad_spec.write_text("pit_id: pit-bad\ntitle: x\n", encoding="utf-8")

        result = core.preflight(bad_spec, vault)

        assert result["ok"] is False
        assert result["verdict"] == "PIT_PREFLIGHT_FAIL"
        assert result["budget"] is None

    def test_fails_on_missing_vault(self, tmp_path):
        result = core.preflight(EXAMPLE_SPEC, tmp_path / "nope")

        assert result["ok"] is False
        assert any("vault_path" in error for error in result["errors"])

    def test_handler_requires_vault_path(self, monkeypatch):
        monkeypatch.delenv("PIT_VAULT_PATH", raising=False)
        result = handle_pit_preflight({"spec_path": str(EXAMPLE_SPEC)})

        assert result["ok"] is False
        assert "vault_path" in result["error"]

    def test_handler_takes_vault_from_env(self, tmp_path, monkeypatch):
        vault = _make_vault(tmp_path)
        monkeypatch.setenv("PIT_VAULT_PATH", str(vault))
        result = handle_pit_preflight({"spec_path": str(EXAMPLE_SPEC)})

        assert result["ok"] is True


# ---------------------------------------------------------------------------
# pit.lane_init
# ---------------------------------------------------------------------------


class TestLaneInit:
    def test_creates_board_and_first_iteration(self, tmp_path):
        vault = _make_vault(tmp_path)
        result = _init_lane(vault)

        board = Path(result["board_path"])
        assert result["board_created"] is True
        assert board.is_file()
        # Placeholders de la plantilla rellenados.
        content = board.read_text(encoding="utf-8")
        assert f'pit_id: "{PIT_ID}"' in content
        assert f'lane_id: "{LANE_ID}"' in content
        assert "{{" not in content
        # kpi-pack es 1-based: la primera iteración es iterations/1 (no 0).
        assert Path(result["first_iteration_dir"]).name == "1"
        assert Path(result["first_iteration_dir"]).is_dir()

    def test_writes_only_under_lane_subtree(self, tmp_path):
        vault = _make_vault(tmp_path)
        before = {p for p in vault.rglob("*")}
        result = _init_lane(vault)

        lane_root = Path(result["lane_root"])
        assert lane_root == vault / "pit" / PIT_ID / "lanes" / LANE_ID
        created = {p for p in vault.rglob("*")} - before
        # Permitido: el subárbol de la lane + sus directorios ancestros (mkdir -p).
        allowed_ancestors = {lane_root, *lane_root.parents}
        outside = [
            p for p in created
            if p not in allowed_ancestors and lane_root not in p.parents
        ]
        assert outside == [], f"lane_init wrote outside its write scope: {outside}"

    def test_idempotent_never_clobbers_board(self, tmp_path):
        vault = _make_vault(tmp_path)
        first = _init_lane(vault)
        board = Path(first["board_path"])
        board.write_text("## Backlog\n\n- [ ] edicion manual\n", encoding="utf-8")

        second = _init_lane(vault)

        assert second["board_created"] is False
        assert "edicion manual" in board.read_text(encoding="utf-8")

    @pytest.mark.parametrize("lane_id", ["lane_x", "qa", "lane-", "lane-../evil", "lane-UP"])
    def test_rejects_invalid_lane_id(self, tmp_path, lane_id):
        vault = _make_vault(tmp_path)
        with pytest.raises(ValueError):
            core.lane_init(vault, PIT_ID, lane_id)

    @pytest.mark.parametrize("pit_id", ["ab", "PIT-X", "pit/../etc", "pit x"])
    def test_rejects_invalid_pit_id(self, tmp_path, pit_id):
        vault = _make_vault(tmp_path)
        with pytest.raises(ValueError):
            core.lane_init(vault, pit_id, LANE_ID)

    def test_rejects_unknown_research_profile(self, tmp_path):
        vault = _make_vault(tmp_path)
        with pytest.raises(ValueError):
            core.lane_init(vault, PIT_ID, LANE_ID, research_profile="vibes")

    def test_handler_wraps_errors(self, tmp_path):
        vault = _make_vault(tmp_path)
        result = handle_pit_lane_init(
            {"vault_path": str(vault), "pit_id": PIT_ID, "lane_id": "nope"}
        )

        assert result["ok"] is False
        assert "lane_id" in result["error"]


# ---------------------------------------------------------------------------
# pit.iteration_close
# ---------------------------------------------------------------------------


class TestIterationClose:
    def test_writes_kpi_pack_and_updates_kanban(self, tmp_path):
        vault = _make_vault(tmp_path)
        _init_lane(vault)

        result = core.iteration_close(
            vault, PIT_ID, LANE_ID, 1, _hypothesis(), _kpis(),
            prototype_url="https://dry-run.invalid/mc/x",
            synthetic_personas={"used": True, "count": 6},
        )

        pack = json.loads(Path(result["kpi_pack_path"]).read_text(encoding="utf-8"))
        assert pack["schema_version"] == 1
        assert pack["pit_id"] == PIT_ID
        assert pack["lane_id"] == LANE_ID
        assert pack["iteration"] == 1
        # (2*0.5 + 1*1.0) / 3 = 0.67
        assert pack["fulfillment_score"] == compute_fulfillment(_kpis())
        assert pack["fulfillment_score"] == result["fulfillment_score"]
        assert pack["synthetic_personas"] == {"used": True, "labeled": True, "count": 6}
        assert result["kpi_pack_rel"] == (
            f"pit/{PIT_ID}/lanes/{LANE_ID}/iterations/1/kpi_pack.json"
        )

        board = (vault / "pit" / PIT_ID / "lanes" / LANE_ID / "kanban" / "board.md").read_text(
            encoding="utf-8"
        )
        fulfillment_idx = board.index("## Fulfillment")
        review_idx = board.index("## Review")
        card_idx = board.index("- [x] iter-1 · taps hasta completar el check-in")
        assert fulfillment_idx < card_idx < review_idx
        assert "fulfillment 0.67 #iter1" in board

    def test_kpi_pack_validates_against_schema(self, tmp_path):
        jsonschema = pytest.importorskip("jsonschema")
        vault = _make_vault(tmp_path)
        _init_lane(vault)

        result = core.iteration_close(
            vault, PIT_ID, LANE_ID, 1, _hypothesis(), _kpis(),
            prototype_url="https://dry-run.invalid/mc/x",
        )

        assert result["schema_validation"] == "jsonschema"
        schema = json.loads(
            (core.TEMPLATES_DIR / "kpi-pack.schema.json").read_text(encoding="utf-8")
        )
        pack = json.loads(Path(result["kpi_pack_path"]).read_text(encoding="utf-8"))
        jsonschema.validate(instance=pack, schema=schema)

    def test_custom_kanban_column(self, tmp_path):
        vault = _make_vault(tmp_path)
        _init_lane(vault)

        core.iteration_close(
            vault, PIT_ID, LANE_ID, 2, _hypothesis(), _kpis(), kanban_column="Review"
        )

        board = (vault / "pit" / PIT_ID / "lanes" / LANE_ID / "kanban" / "board.md").read_text(
            encoding="utf-8"
        )
        review_idx = board.index("## Review")
        done_idx = board.index("## Done")
        assert review_idx < board.index("#iter2") < done_idx

    def test_rejects_unknown_column(self, tmp_path):
        vault = _make_vault(tmp_path)
        _init_lane(vault)
        with pytest.raises(ValueError, match="kanban_column"):
            core.iteration_close(
                vault, PIT_ID, LANE_ID, 1, _hypothesis(), _kpis(), kanban_column="WIP"
            )

    def test_rejects_hypothesis_kpi_not_in_kpis(self, tmp_path):
        vault = _make_vault(tmp_path)
        _init_lane(vault)
        with pytest.raises(ValueError, match="hypothesis.kpi_id"):
            core.iteration_close(
                vault, PIT_ID, LANE_ID, 1, _hypothesis(kpi_id="otro_kpi"), _kpis()
            )

    @pytest.mark.parametrize("iteration", [0, 11, "1", None, 1.5])
    def test_rejects_out_of_contract_iteration(self, tmp_path, iteration):
        vault = _make_vault(tmp_path)
        _init_lane(vault)
        with pytest.raises(ValueError, match="iteration"):
            core.iteration_close(
                vault, PIT_ID, LANE_ID, iteration, _hypothesis(), _kpis()
            )

    def test_requires_lane_init_first(self, tmp_path):
        vault = _make_vault(tmp_path)
        with pytest.raises(ValueError, match="pit.lane_init"):
            core.iteration_close(vault, PIT_ID, LANE_ID, 1, _hypothesis(), _kpis())

    def test_handler_roundtrip(self, tmp_path):
        vault = _make_vault(tmp_path)
        _init_lane(vault)

        result = handle_pit_iteration_close(
            {
                "vault_path": str(vault),
                "pit_id": PIT_ID,
                "lane_id": LANE_ID,
                "iteration": 1,
                "hypothesis": _hypothesis(),
                "kpis": _kpis(),
                "prototype_url": "https://dry-run.invalid/mc/x",
            }
        )

        assert result["ok"] is True
        assert Path(result["kpi_pack_path"]).is_file()


# ---------------------------------------------------------------------------
# pit.lane_announce
# ---------------------------------------------------------------------------


class TestLaneAnnounce:
    def _close(self, vault: Path, iteration: int = 1, **kwargs) -> dict:
        return core.iteration_close(
            vault, PIT_ID, LANE_ID, iteration, _hypothesis(), _kpis(), **kwargs
        )

    def test_emits_three_literal_lines(self, tmp_path):
        vault = _make_vault(tmp_path)
        _init_lane(vault)
        self._close(vault, prototype_url="https://dry-run.invalid/mc/lane")

        result = core.lane_announce(vault, PIT_ID, LANE_ID)

        expected_pack = f"pit/{PIT_ID}/lanes/{LANE_ID}/iterations/1/kpi_pack.json"
        lines = result["announce"].splitlines()
        assert lines == [
            "PROTOTYPE_URL=https://dry-run.invalid/mc/lane",
            f"KPI_PACK={expected_pack}",
            f"FULFILLMENT={result['fulfillment']}",
        ]
        assert result["lane_complete"] is True
        assert result["reproducible"] is True
        assert result["incomplete_reasons"] == []

    def test_picks_latest_iteration(self, tmp_path):
        vault = _make_vault(tmp_path)
        _init_lane(vault)
        self._close(vault, iteration=1, prototype_url="https://dry-run.invalid/1")
        self._close(vault, iteration=3, prototype_url="https://dry-run.invalid/3")

        result = core.lane_announce(vault, PIT_ID, LANE_ID)

        assert result["iteration"] == 3
        assert "iterations/3/" in result["kpi_pack"]

    def test_missing_prototype_url_is_incomplete(self, tmp_path):
        vault = _make_vault(tmp_path)
        _init_lane(vault)
        self._close(vault)  # sin prototype_url

        result = core.lane_announce(vault, PIT_ID, LANE_ID)

        assert result["lane_complete"] is False
        assert any("PROTOTYPE_URL" in reason for reason in result["incomplete_reasons"])

    def test_tampered_fulfillment_not_reproducible(self, tmp_path):
        vault = _make_vault(tmp_path)
        _init_lane(vault)
        closed = self._close(vault, prototype_url="https://dry-run.invalid/mc")
        pack_path = Path(closed["kpi_pack_path"])
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        pack["fulfillment_score"] = 0.99  # finalStatus=success trucho
        pack_path.write_text(json.dumps(pack), encoding="utf-8")

        result = core.lane_announce(vault, PIT_ID, LANE_ID)

        assert result["reproducible"] is False
        assert result["lane_complete"] is False
        assert any("not reproducible" in reason for reason in result["incomplete_reasons"])

    def test_errors_when_no_iterations(self, tmp_path):
        vault = _make_vault(tmp_path)
        _init_lane(vault)
        with pytest.raises(ValueError, match="no iterations"):
            core.lane_announce(vault, PIT_ID, LANE_ID)

    def test_handler_roundtrip(self, tmp_path):
        vault = _make_vault(tmp_path)
        _init_lane(vault)
        self._close(vault, prototype_url="https://dry-run.invalid/mc")

        result = handle_pit_lane_announce(
            {"vault_path": str(vault), "pit_id": PIT_ID, "lane_id": LANE_ID}
        )

        assert result["ok"] is True
        assert result["lane_complete"] is True


# ---------------------------------------------------------------------------
# Registry — pit.* registradas y D3 tournament_lane.* intacto
# ---------------------------------------------------------------------------


class TestTaskRegistry:
    def test_pit_tasks_registered(self):
        assert TASK_HANDLERS["pit.preflight"] is handle_pit_preflight
        assert TASK_HANDLERS["pit.lane_init"] is handle_pit_lane_init
        assert TASK_HANDLERS["pit.iteration_close"] is handle_pit_iteration_close
        assert TASK_HANDLERS["pit.lane_announce"] is handle_pit_lane_announce

    def test_d3_tournament_lane_tasks_untouched(self):
        # Guardrail PIT-2: el protocolo D3 (docs/79) no se rompe.
        for task in (
            "tournament_lane.preflight",
            "tournament_lane.create_branch",
            "tournament_lane.commit_and_push",
            "tournament_lane.open_pr",
            "tournament_lane.verify_pr",
            "tournament.run",
            "github.orchestrate_tournament",
        ):
            assert task in TASK_HANDLERS, f"D3 task missing: {task}"
