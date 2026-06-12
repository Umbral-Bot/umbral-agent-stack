"""Tests del adapter read-only mission_control/adapters/pit_vault.py (PIT-5 P5.1)."""

from __future__ import annotations

import builtins
import io
from pathlib import Path

import pytest

from mission_control.adapters import pit_vault
from tests.mission_control._pit_fixtures import (
    ARCHIVED_PIT_ID,
    DEMO_PIT_ID,
    build_demo_vault,
    build_evidence,
    make_kpi_pack,
    write_announce,
    write_iteration,
)


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    return build_demo_vault(tmp_path / "vault")


@pytest.fixture
def evidence(tmp_path: Path) -> Path:
    return build_evidence(tmp_path / "evidence")


# ---------------------------------------------------------------------------
# Validación de inputs (antes de tocar filesystem)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_pit_id",
    ["..", "PIT-UPPER", "pit_underscore", "ab", "-leading", "a" * 65, "p/it"],
)
def test_validate_pit_id_rejects(bad_pit_id: str) -> None:
    with pytest.raises(ValueError):
        pit_vault.validate_pit_id(bad_pit_id)


@pytest.mark.parametrize(
    "bad_lane_id", ["alpha", "lane-", "lane-UPPER", "lane-..", "lane-a/b", ".."]
)
def test_validate_lane_id_rejects(bad_lane_id: str) -> None:
    with pytest.raises(ValueError):
        pit_vault.validate_lane_id(bad_lane_id)


@pytest.mark.parametrize("bad_iteration", [0, 11, -1, "3", 2.5, True])
def test_validate_iteration_rejects(bad_iteration) -> None:
    with pytest.raises(ValueError):
        pit_vault.validate_iteration(bad_iteration)


def test_validators_accept_known_good() -> None:
    assert pit_vault.validate_pit_id(DEMO_PIT_ID) == DEMO_PIT_ID
    assert pit_vault.validate_lane_id("lane-alpha") == "lane-alpha"
    assert pit_vault.validate_iteration(5) == 5


def test_invalid_ids_raise_before_filesystem(tmp_path: Path) -> None:
    """ValueError debe saltar incluso con un vault path inexistente."""
    ghost = tmp_path / "no-vault"
    with pytest.raises(ValueError):
        pit_vault.read_tournament(ghost, ghost, "..")
    with pytest.raises(ValueError):
        pit_vault.read_kpi_pack(ghost, DEMO_PIT_ID, "..", 1)
    with pytest.raises(ValueError):
        pit_vault.read_kpi_pack(ghost, DEMO_PIT_ID, "lane-alpha", 99)


# ---------------------------------------------------------------------------
# derive_status (matriz pura)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("archived", "has_winner", "announces", "lane_dirs", "expected"),
    [
        (True, True, 3, 3, "archived"),
        (False, True, 0, 1, "closed"),
        (False, False, 2, 3, "judge_pending"),
        (False, False, 1, 2, "running"),
        (False, False, 0, 1, "running"),
        (False, False, 0, 0, "spec_only"),
    ],
)
def test_derive_status_matrix(
    archived: bool, has_winner: bool, announces: int, lane_dirs: int, expected: str
) -> None:
    assert (
        pit_vault.derive_status(
            archived=archived,
            has_winner=has_winner,
            lanes_with_announce=announces,
            lane_dir_count=lane_dirs,
        )
        == expected
    )


# ---------------------------------------------------------------------------
# list_tournaments
# ---------------------------------------------------------------------------


def test_list_tournaments_happy(vault: Path, evidence: Path) -> None:
    payload = pit_vault.list_tournaments(vault, evidence)
    assert payload["read_only"] is True
    assert payload["vault"] == {"path": str(vault), "available": True}
    by_id = {t["pit_id"]: t for t in payload["tournaments"]}
    assert set(by_id) == {DEMO_PIT_ID, ARCHIVED_PIT_ID}

    demo = by_id[DEMO_PIT_ID]
    assert demo["title"] == "Demo tournament"
    assert demo["mode"] == "sintetico"
    assert demo["lane_count"] == 3
    assert demo["iteration_count"] == 5
    assert demo["budget_usd"] == 25
    assert demo["status"] == "judge_pending"
    assert demo["lanes_complete"] == 2
    assert demo["has_outcome"] is False
    assert demo["archived"] is False
    assert demo["run_verdict"] == "PIT_RUN_PASS"
    assert demo["spec_source"] == "vault"

    old = by_id[ARCHIVED_PIT_ID]
    assert old["status"] == "archived"
    assert old["archived"] is True
    assert old["has_outcome"] is True
    assert old["run_verdict"] is None


def test_list_tournaments_vault_absent(tmp_path: Path) -> None:
    payload = pit_vault.list_tournaments(tmp_path / "missing", tmp_path / "evidence")
    assert payload["read_only"] is True
    assert payload["vault"]["available"] is False
    assert payload["tournaments"] == []


def test_list_tournaments_vault_empty(tmp_path: Path) -> None:
    empty = tmp_path / "vault"
    empty.mkdir()
    payload = pit_vault.list_tournaments(empty, tmp_path / "evidence")
    assert payload["vault"]["available"] is True
    assert payload["tournaments"] == []


# ---------------------------------------------------------------------------
# read_tournament
# ---------------------------------------------------------------------------


def test_read_tournament_detail_happy(vault: Path, evidence: Path) -> None:
    payload = pit_vault.read_tournament(vault, evidence, DEMO_PIT_ID)
    assert payload is not None
    assert payload["read_only"] is True
    assert payload["pit_id"] == DEMO_PIT_ID
    assert payload["archived"] is False
    assert payload["status"] == "judge_pending"
    assert payload["spec_source"] == "vault"

    spec = payload["spec"]
    assert spec["title"] == "Demo tournament"
    assert spec["budget_usd"] == 25
    assert [d["kpi_id"] for d in spec["kpi_definitions"]] == [
        "kpi-activation",
        "kpi-retention",
    ]
    assert spec["kpi_definitions"][0]["direction"] == "up"

    lanes = {lane["lane_id"]: lane for lane in payload["lanes"]}
    assert list(lanes) == ["lane-alpha", "lane-beta", "lane-gamma"]

    alpha = lanes["lane-alpha"]
    assert alpha["announce_present"] is True
    assert alpha["lane_complete"] is True
    assert alpha["iterations_run"] == 2
    assert alpha["last_iteration"] == 2
    assert alpha["fulfillment_score"] == pytest.approx(0.82)
    assert alpha["hypothesis_final"] == {
        "variable": "onboarding copy",
        "kpi_id": "kpi-activation",
        "validated": True,
    }
    assert alpha["synthetic_share"] == pytest.approx(0.5)
    assert (
        alpha["kpi_pack_path"]
        == f"pit/{DEMO_PIT_ID}/lanes/lane-alpha/iterations/2/kpi_pack.json"
    )
    assert alpha["prototype"] == {
        "available": True,
        "entry": "index.html",
        "preview_path": f"/pit/preview/{DEMO_PIT_ID}/lane-alpha/2/",
    }
    assert alpha["announce"]["FULFILLMENT"] == "0.82"
    assert alpha["announce"]["PROTOTYPE_URL"]
    assert alpha["announce"]["KPI_PACK"]

    beta = lanes["lane-beta"]
    assert beta["lane_complete"] is True
    assert beta["synthetic_share"] == pytest.approx(1.0)
    assert beta["prototype"]["entry"] == "demo.html"
    assert beta["hypothesis_final"]["validated"] is False

    gamma = lanes["lane-gamma"]
    assert gamma["announce_present"] is False
    assert gamma["announce"] is None
    assert gamma["lane_complete"] is False

    assert payload["outcome"] == {
        "present": False,
        "winner_lane_id": None,
        "david_gate": None,
    }
    assert payload["evidence"] == {
        "run_metrics_present": True,
        "verdict": "PIT_RUN_PASS",
    }


def test_read_tournament_archived_outcome(vault: Path, evidence: Path) -> None:
    payload = pit_vault.read_tournament(vault, evidence, ARCHIVED_PIT_ID)
    assert payload is not None
    assert payload["archived"] is True
    assert payload["status"] == "archived"
    assert payload["outcome"] == {
        "present": True,
        "winner_lane_id": "lane-winner",
        "david_gate": "GO",
    }
    lane = payload["lanes"][0]
    assert (
        lane["kpi_pack_path"]
        == f"archive/{ARCHIVED_PIT_ID}/lanes/lane-winner/iterations/1/kpi_pack.json"
    )
    assert payload["evidence"] == {"run_metrics_present": False, "verdict": None}


def test_read_tournament_unknown_returns_none(vault: Path, evidence: Path) -> None:
    assert pit_vault.read_tournament(vault, evidence, "pit-ghost") is None


def test_read_tournament_vault_absent_returns_none(tmp_path: Path) -> None:
    ghost = tmp_path / "missing"
    assert pit_vault.read_tournament(ghost, ghost, DEMO_PIT_ID) is None


# ---------------------------------------------------------------------------
# Spec fallback (hallazgo P5.0: vault piloto sin spec/pit_spec.yaml)
# ---------------------------------------------------------------------------


def _vault_without_spec(tmp_path: Path, pit_id: str = "pit-no-spec") -> Path:
    vault = tmp_path / "vault"
    lane = vault / "pit" / pit_id / "lanes" / "lane-solo"
    write_iteration(lane, 1, make_kpi_pack(pit_id, "lane-solo", 1, 0.7))
    write_announce(lane, fulfillment="0.7")
    return vault


def test_spec_fallback_used_when_vault_spec_missing(tmp_path: Path) -> None:
    vault = _vault_without_spec(tmp_path)
    fallback_dir = tmp_path / "examples"
    fallback_dir.mkdir()
    (fallback_dir / "pit-no-spec.yaml").write_text(
        "pit_id: pit-no-spec\ntitle: Fallback title\nbudget_usd: 10\n"
        "iteration_count: 3\nlane_count: 1\nmode: real\n",
        encoding="utf-8",
    )
    payload = pit_vault.read_tournament(
        vault, tmp_path / "evidence", "pit-no-spec", fallback_dir
    )
    assert payload is not None
    assert payload["spec_source"] == "fallback"
    assert payload["spec"]["title"] == "Fallback title"

    listing = pit_vault.list_tournaments(vault, tmp_path / "evidence", fallback_dir)
    assert listing["tournaments"][0]["spec_source"] == "fallback"
    assert listing["tournaments"][0]["title"] == "Fallback title"


def test_spec_fallback_rejected_on_pit_id_mismatch(tmp_path: Path) -> None:
    vault = _vault_without_spec(tmp_path)
    fallback_dir = tmp_path / "examples"
    fallback_dir.mkdir()
    (fallback_dir / "pit-no-spec.yaml").write_text(
        "pit_id: pit-otro\ntitle: Wrong spec\n", encoding="utf-8"
    )
    payload = pit_vault.read_tournament(
        vault, tmp_path / "evidence", "pit-no-spec", fallback_dir
    )
    assert payload is not None
    assert payload["spec_source"] is None
    assert payload["spec"] is None


def test_spec_missing_everywhere(tmp_path: Path) -> None:
    vault = _vault_without_spec(tmp_path)
    payload = pit_vault.read_tournament(vault, tmp_path / "evidence", "pit-no-spec")
    assert payload is not None
    assert payload["spec_source"] is None
    assert payload["spec"] is None
    assert payload["status"] == "running"


# ---------------------------------------------------------------------------
# Robustez: announce / kpi_pack corruptos
# ---------------------------------------------------------------------------


def test_announce_malformed_blocks_lane_complete(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    lane = vault / "pit" / "pit-demo-bad" / "lanes" / "lane-bad"
    write_iteration(lane, 1, make_kpi_pack("pit-demo-bad", "lane-bad", 1, 0.5))
    (lane / "announce.md").write_text(
        "PROTOTYPE_URL=http://x/\nKPI_PACK=kpi_pack.json\n", encoding="utf-8"
    )  # falta FULFILLMENT
    payload = pit_vault.read_tournament(vault, tmp_path / "evidence", "pit-demo-bad")
    lane_payload = payload["lanes"][0]
    assert lane_payload["announce_present"] is True
    assert lane_payload["announce"]["FULFILLMENT"] is None
    assert lane_payload["lane_complete"] is False


def test_announce_fulfillment_mismatch_blocks_lane_complete(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    lane = vault / "pit" / "pit-demo-drift" / "lanes" / "lane-drift"
    write_iteration(lane, 1, make_kpi_pack("pit-demo-drift", "lane-drift", 1, 0.5))
    write_announce(lane, fulfillment="0.99")
    payload = pit_vault.read_tournament(vault, tmp_path / "evidence", "pit-demo-drift")
    lane_payload = payload["lanes"][0]
    assert lane_payload["fulfillment_score"] == pytest.approx(0.5)
    assert lane_payload["lane_complete"] is False


def test_kpi_pack_invalid_json_degrades(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    lane = vault / "pit" / "pit-demo-corrupt" / "lanes" / "lane-corrupt"
    write_iteration(lane, 1, make_kpi_pack("pit-demo-corrupt", "lane-corrupt", 1, 0.4))
    write_iteration(lane, 2, "{not json")
    write_announce(lane, fulfillment="0.4")
    payload = pit_vault.read_tournament(
        vault, tmp_path / "evidence", "pit-demo-corrupt"
    )
    lane_payload = payload["lanes"][0]
    # Última iteración con kpi_pack.json es la 2 (corrupta) → degradar, no crashear.
    assert lane_payload["last_iteration"] == 2
    assert lane_payload["fulfillment_score"] is None
    assert lane_payload["hypothesis_final"] is None
    assert lane_payload["synthetic_share"] is None
    assert lane_payload["lane_complete"] is False


# ---------------------------------------------------------------------------
# read_kpi_pack
# ---------------------------------------------------------------------------


def test_read_kpi_pack_happy(vault: Path) -> None:
    payload = pit_vault.read_kpi_pack(vault, DEMO_PIT_ID, "lane-alpha", 2)
    assert payload is not None
    assert payload["read_only"] is True
    assert payload["pit_id"] == DEMO_PIT_ID
    assert payload["lane_id"] == "lane-alpha"
    assert payload["iteration"] == 2
    assert (
        payload["path"]
        == f"pit/{DEMO_PIT_ID}/lanes/lane-alpha/iterations/2/kpi_pack.json"
    )
    assert payload["kpi_pack"]["fulfillment_score"] == pytest.approx(0.82)
    assert payload["error"] is None


def test_read_kpi_pack_archived_path(vault: Path) -> None:
    payload = pit_vault.read_kpi_pack(vault, ARCHIVED_PIT_ID, "lane-winner", 1)
    assert payload is not None
    assert payload["path"].startswith("archive/")


def test_read_kpi_pack_missing_returns_none(vault: Path) -> None:
    assert pit_vault.read_kpi_pack(vault, DEMO_PIT_ID, "lane-alpha", 5) is None
    assert pit_vault.read_kpi_pack(vault, DEMO_PIT_ID, "lane-ghost", 1) is None
    assert pit_vault.read_kpi_pack(vault, "pit-ghost", "lane-alpha", 1) is None


def test_read_kpi_pack_invalid_json_reports_error(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    lane = vault / "pit" / "pit-demo-corrupt" / "lanes" / "lane-corrupt"
    write_iteration(lane, 1, "{not json")
    payload = pit_vault.read_kpi_pack(vault, "pit-demo-corrupt", "lane-corrupt", 1)
    assert payload is not None
    assert payload["kpi_pack"] is None
    assert "JSONDecodeError" in payload["error"]


# ---------------------------------------------------------------------------
# Garantía read-only: el adapter NUNCA escribe
# ---------------------------------------------------------------------------


def test_adapter_never_writes(
    vault: Path, evidence: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Toda la superficie pública del adapter con escrituras prohibidas."""
    real_open = builtins.open

    def guarded_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            raise AssertionError(f"write attempt: open({file!r}, {mode!r})")
        return real_open(file, mode, *args, **kwargs)

    def forbidden(name):
        def _fail(*args, **kwargs):
            raise AssertionError(f"write attempt: Path.{name}")

        return _fail

    # builtins.open e io.open son el mismo objeto pero bindings separados;
    # pathlib usa io.open a través de Path.open.
    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(io, "open", guarded_open)
    for method in (
        "write_text",
        "write_bytes",
        "mkdir",
        "touch",
        "unlink",
        "rename",
        "replace",
        "rmdir",
        "symlink_to",
        "chmod",
    ):
        monkeypatch.setattr(Path, method, forbidden(method))

    listing = pit_vault.list_tournaments(vault, evidence)
    assert listing["tournaments"]
    detail = pit_vault.read_tournament(vault, evidence, DEMO_PIT_ID)
    assert detail is not None
    pack = pit_vault.read_kpi_pack(vault, DEMO_PIT_ID, "lane-alpha", 2)
    assert pack is not None
    # Vault inexistente tampoco debe provocar creación de directorios.
    missing = vault.parent / "missing-vault"
    assert pit_vault.list_tournaments(missing, evidence)["vault"]["available"] is False
