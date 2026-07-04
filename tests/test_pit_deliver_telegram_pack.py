"""Tests — scripts/pit/pit_deliver_telegram_pack.py (PIT-TG-DRIVE Fase 3).

``--dry-run`` no requiere Drive ni red; el path real se prueba mockeando el
handler ``google_drive.upload_file``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.pit import pit_deliver_telegram_pack as deliver_mod
from worker.tasks import google_drive as gd

PIT_ID = "pit-deliver-test"


def _outcome(closed: bool = True) -> dict:
    return {
        "schema_version": 1,
        "pit_id": PIT_ID,
        "title": "Torneo entrega",
        "dates": {"started_at": "2026-07-01", "closed_at": "2026-07-03"},
        "budget": {"budget_usd": 200, "usd_estimated_spent": 41},
        "lanes": [
            {"lane_id": "lane-a", "fulfillment_score": 0.9, "status": "complete"},
            {"lane_id": "lane-b", "fulfillment_score": 0.5, "status": "complete"},
        ],
        "winner": {
            "lane_id": "lane-a" if closed else "",
            "rationale": "- fulfillment\n- señal real\n- integrable",
            "david_gate": "ok, cierro" if closed else "pending",
        },
        "kpi_summary": [
            {"kpi_id": "adopcion", "unit": "%", "kpi_expected": 60, "kpi_achieved": 75,
             "synthetic_share": 1.0}
        ],
        "learnings": {"validated": ["fricción manda"], "refuted": [], "inconclusive": []},
        "fulfillment_decision": {"next_step": "fulfillment-track", "notes": "seguir"},
    }


def _make_vault(tmp_path: Path, outcome: dict) -> Path:
    vault = tmp_path / "vault"
    outcome_dir = vault / "pit" / PIT_ID / "outcome"
    outcome_dir.mkdir(parents=True)
    (outcome_dir / "pit_outcome_report.yaml").write_text(
        yaml.safe_dump(outcome, allow_unicode=True), encoding="utf-8"
    )
    return vault


@pytest.fixture(autouse=True)
def _no_drive_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "GOOGLE_DRIVE_PIT_FOLDER_ID",
        "GOOGLE_DRIVE_OAUTH_CLIENT_ID",
        "GOOGLE_DRIVE_OAUTH_CLIENT_SECRET",
        "GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN",
        "GOOGLE_DRIVE_SHARE_WITH",
    ):
        monkeypatch.delenv(name, raising=False)


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------


def test_fail_when_outcome_missing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = deliver_mod.main(["--pit-id", PIT_ID, "--vault-path", str(tmp_path / "vault"), "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "PIT_DELIVER_PACK_FAIL" in out
    assert "outcome_missing" in out


def test_fail_when_winner_pending(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    vault = _make_vault(tmp_path, _outcome(closed=False))
    rc = deliver_mod.main(["--pit-id", PIT_ID, "--vault-path", str(vault), "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "winner_pending" in out


@pytest.mark.parametrize(
    "gate",
    [
        "pending",
        "pending review de David",
        "PENDING — esperando gate",
        "pending_gate",
        "Pending(judge)",
        "null",
        "none",
        "",
        None,
    ],
)
def test_winner_is_closed_rejects_pending_prefix(gate) -> None:
    """Gate pending por PREFIJO (no igualdad exacta) — fix PIT post-torneo."""
    outcome = _outcome()
    outcome["winner"]["david_gate"] = gate
    assert deliver_mod.winner_is_closed(outcome) is False


@pytest.mark.parametrize("gate", ["ok, cierro", "aprobado, cerralo", "dale, cerrado"])
def test_winner_is_closed_accepts_real_gate(gate) -> None:
    outcome = _outcome()
    outcome["winner"]["david_gate"] = gate
    assert deliver_mod.winner_is_closed(outcome) is True


def test_fail_when_gate_is_pending_prefix(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    outcome = _outcome()
    outcome["winner"]["david_gate"] = "pending review de David"
    vault = _make_vault(tmp_path, outcome)
    rc = deliver_mod.main(["--pit-id", PIT_ID, "--vault-path", str(vault), "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "winner_pending" in out


def test_winner_is_closed_rejects_template_placeholder() -> None:
    outcome = _outcome()
    outcome["winner"]["david_gate"] = "<frase literal de David que autorizó el cierre, o pending>"
    assert deliver_mod.winner_is_closed(outcome) is False


def test_fail_when_drive_not_configured(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pytest.importorskip("pptx")
    vault = _make_vault(tmp_path, _outcome())
    rc = deliver_mod.main(["--pit-id", PIT_ID, "--vault-path", str(vault)])
    out = capsys.readouterr().out
    assert rc == 2
    assert "drive_not_configured" in out


# ---------------------------------------------------------------------------
# Dry-run: deck + pack sin Drive
# ---------------------------------------------------------------------------


def test_dry_run_builds_deck_and_pack(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pytest.importorskip("pptx")
    vault = _make_vault(tmp_path, _outcome())
    rc = deliver_mod.main(["--pit-id", PIT_ID, "--vault-path", str(vault), "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "PIT_DELIVER_PACK_DRY_OK" in out

    deck = vault / "pit" / PIT_ID / "deliverables" / f"{PIT_ID}-outcome-deck.pptx"
    assert deck.is_file()

    pack_path = vault / "pit" / PIT_ID / "deliverables" / "telegram_pack.json"
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    assert pack["pit_id"] == PIT_ID
    assert pack["drive_deck_url"] is None
    assert PIT_ID in pack["mc_judge_hint"]
    assert len(pack["summary_lines"]) <= 12
    assert pack["summary_lines"][0] == f"TORNEO PIT · {PIT_ID}"
    assert any("lane-a" in line for line in pack["summary_lines"])
    # nunca se filtra un pptx adjunto: el pack solo referencia links/paths
    assert "sendDocument" not in json.dumps(pack)


# ---------------------------------------------------------------------------
# Path real con upload mockeado
# ---------------------------------------------------------------------------


def test_real_run_uploads_and_writes_link(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pytest.importorskip("pptx")
    vault = _make_vault(tmp_path, _outcome())
    for name, value in (
        ("GOOGLE_DRIVE_PIT_FOLDER_ID", "folder-1"),
        ("GOOGLE_DRIVE_OAUTH_CLIENT_ID", "cid"),
        ("GOOGLE_DRIVE_OAUTH_CLIENT_SECRET", "csec"),
        ("GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN", "rtok"),
    ):
        monkeypatch.setenv(name, value)

    uploads: list[dict] = []

    def fake_upload(input_data: dict) -> dict:
        uploads.append(input_data)
        return {
            "ok": True,
            "file_id": "file-9",
            "web_view_link": "https://drive.google.com/file/d/file-9/view",
        }

    monkeypatch.setattr(gd, "handle_google_drive_upload_file", fake_upload)

    rc = deliver_mod.main(["--pit-id", PIT_ID, "--vault-path", str(vault)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "PIT_DELIVER_PACK_OK" in out
    assert "drive_url=https://drive.google.com/file/d/file-9/view" in out

    assert len(uploads) == 1
    assert uploads[0]["local_path"].endswith(f"{PIT_ID}-outcome-deck.pptx")

    pack = json.loads(
        (vault / "pit" / PIT_ID / "deliverables" / "telegram_pack.json").read_text(
            encoding="utf-8"
        )
    )
    assert pack["drive_deck_url"] == "https://drive.google.com/file/d/file-9/view"
    assert pack["drive_file_id"] == "file-9"
    assert any("drive.google.com" in line for line in pack["summary_lines"])


def test_real_run_upload_failure_is_fail_verdict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pytest.importorskip("pptx")
    vault = _make_vault(tmp_path, _outcome())
    for name, value in (
        ("GOOGLE_DRIVE_PIT_FOLDER_ID", "folder-1"),
        ("GOOGLE_DRIVE_OAUTH_CLIENT_ID", "cid"),
        ("GOOGLE_DRIVE_OAUTH_CLIENT_SECRET", "csec"),
        ("GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN", "rtok"),
    ):
        monkeypatch.setenv(name, value)

    monkeypatch.setattr(
        gd,
        "handle_google_drive_upload_file",
        lambda input_data: {"ok": False, "error": "403 scope"},
    )

    rc = deliver_mod.main(["--pit-id", PIT_ID, "--vault-path", str(vault)])
    out = capsys.readouterr().out
    assert rc == 2
    assert "PIT_DELIVER_PACK_FAIL" in out
    assert "drive_upload_failed" in out
    # sin link inventado
    assert "drive.google.com" not in out


# ---------------------------------------------------------------------------
# PIT-DEV — traceability gate + zip deliverable winner (orden canonico)
# ---------------------------------------------------------------------------


def _make_dev_vault(tmp_path: Path, outcome: dict, *, with_deliverable: bool = True) -> Path:
    """Vault dev: outcome + spec (mode: dev) + deliverable winner opcional."""
    vault = _make_vault(tmp_path, outcome)
    spec_dir = vault / "pit" / PIT_ID / "spec"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "pit_spec.yaml").write_text(
        yaml.safe_dump({"schema_version": 3, "mode": "dev", "pit_id": PIT_ID}),
        encoding="utf-8",
    )
    if with_deliverable:
        deliverable = vault / "pit" / PIT_ID / "lanes" / "lane-a" / "deliverable"
        deliverable.mkdir(parents=True, exist_ok=True)
        (deliverable / "README.md").write_text("producto", encoding="utf-8")
        (deliverable / "app.py").write_text("print('ok')", encoding="utf-8")
    return vault


def _trace_report(vault: Path) -> None:
    trace_dir = vault / "pit" / PIT_ID / "traceability"
    trace_dir.mkdir(parents=True, exist_ok=True)
    (trace_dir / "report.md").write_text("TRACE_COMPLETE", encoding="utf-8")


def _fake_trace_ok(vault_path, pit_id):  # firma de check_traceability
    return {"pit_id": pit_id, "complete": True, "gaps": [], "verdict": "TRACE_COMPLETE"}


def test_dev_fail_when_traceability_report_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pytest.importorskip("pptx")
    vault = _make_dev_vault(tmp_path, _outcome())
    rc = deliver_mod.main(["--pit-id", PIT_ID, "--vault-path", str(vault), "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "traceability_report_missing" in out


def test_dev_fail_when_traceability_gaps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pytest.importorskip("pptx")
    vault = _make_dev_vault(tmp_path, _outcome())
    _trace_report(vault)
    monkeypatch.setattr(
        deliver_mod,
        "check_traceability",
        lambda vp, pid: {"complete": False, "gaps": ["scorecards", "deck"], "verdict": "TRACE_GAPS"},
    )
    rc = deliver_mod.main(["--pit-id", PIT_ID, "--vault-path", str(vault), "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "traceability_gaps:scorecards,deck" in out


def test_dev_fail_when_winner_deliverable_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pytest.importorskip("pptx")
    vault = _make_dev_vault(tmp_path, _outcome(), with_deliverable=False)
    _trace_report(vault)
    monkeypatch.setattr(deliver_mod, "check_traceability", _fake_trace_ok)
    rc = deliver_mod.main(["--pit-id", PIT_ID, "--vault-path", str(vault), "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "winner_deliverable_missing" in out


def test_dev_dry_run_builds_zip_and_pack(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pytest.importorskip("pptx")
    vault = _make_dev_vault(tmp_path, _outcome())
    _trace_report(vault)
    monkeypatch.setattr(deliver_mod, "check_traceability", _fake_trace_ok)
    rc = deliver_mod.main(["--pit-id", PIT_ID, "--vault-path", str(vault), "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "PIT_DELIVER_PACK_DRY_OK" in out

    zip_path = vault / "pit" / PIT_ID / "deliverables" / f"{PIT_ID}-lane-a-deliverable.zip"
    assert zip_path.is_file()

    pack = json.loads(
        (vault / "pit" / PIT_ID / "deliverables" / "telegram_pack.json").read_text(
            encoding="utf-8"
        )
    )
    assert pack["deliverable_zip_path"].endswith(f"{PIT_ID}-lane-a-deliverable.zip")
    assert pack["drive_deliverable_zip_url"] is None
    assert pack["drive_deliverable_zip_file_id"] is None
    # hook Notion fase 2: reservado, no implementado
    assert "notion_page_url" in pack and pack["notion_page_url"] is None
    assert len(pack["summary_lines"]) <= 12
    assert any("Deliverable winner (zip" in line for line in pack["summary_lines"])


def test_dev_real_run_uploads_deck_and_zip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pytest.importorskip("pptx")
    vault = _make_dev_vault(tmp_path, _outcome())
    _trace_report(vault)
    monkeypatch.setattr(deliver_mod, "check_traceability", _fake_trace_ok)
    for name, value in (
        ("GOOGLE_DRIVE_PIT_FOLDER_ID", "folder-1"),
        ("GOOGLE_DRIVE_OAUTH_CLIENT_ID", "cid"),
        ("GOOGLE_DRIVE_OAUTH_CLIENT_SECRET", "csec"),
        ("GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN", "rtok"),
    ):
        monkeypatch.setenv(name, value)

    uploads: list[dict] = []

    def fake_upload(input_data: dict) -> dict:
        uploads.append(input_data)
        idx = len(uploads)
        return {
            "ok": True,
            "file_id": f"file-{idx}",
            "web_view_link": f"https://drive.google.com/file/d/file-{idx}/view",
        }

    monkeypatch.setattr(gd, "handle_google_drive_upload_file", fake_upload)

    rc = deliver_mod.main(["--pit-id", PIT_ID, "--vault-path", str(vault)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "PIT_DELIVER_PACK_OK" in out
    assert "drive_url=https://drive.google.com/file/d/file-1/view" in out
    assert "deliverable_zip_url=https://drive.google.com/file/d/file-2/view" in out

    assert len(uploads) == 2
    assert uploads[0]["local_path"].endswith(f"{PIT_ID}-outcome-deck.pptx")
    assert uploads[1]["local_path"].endswith(f"{PIT_ID}-lane-a-deliverable.zip")

    pack = json.loads(
        (vault / "pit" / PIT_ID / "deliverables" / "telegram_pack.json").read_text(
            encoding="utf-8"
        )
    )
    assert pack["drive_deliverable_zip_url"].endswith("file-2/view")
    assert pack["drive_deliverable_zip_file_id"] == "file-2"
    assert any("Deliverable winner (zip" in line for line in pack["summary_lines"])


def test_dev_zip_upload_failure_is_fail_verdict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pytest.importorskip("pptx")
    vault = _make_dev_vault(tmp_path, _outcome())
    _trace_report(vault)
    monkeypatch.setattr(deliver_mod, "check_traceability", _fake_trace_ok)
    for name, value in (
        ("GOOGLE_DRIVE_PIT_FOLDER_ID", "folder-1"),
        ("GOOGLE_DRIVE_OAUTH_CLIENT_ID", "cid"),
        ("GOOGLE_DRIVE_OAUTH_CLIENT_SECRET", "csec"),
        ("GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN", "rtok"),
    ):
        monkeypatch.setenv(name, value)

    calls: list[dict] = []

    def flaky_upload(input_data: dict) -> dict:
        calls.append(input_data)
        if len(calls) == 1:
            return {"ok": True, "file_id": "f1", "web_view_link": "https://drive.google.com/f1"}
        return {"ok": False, "error": "quota"}

    monkeypatch.setattr(gd, "handle_google_drive_upload_file", flaky_upload)

    rc = deliver_mod.main(["--pit-id", PIT_ID, "--vault-path", str(vault)])
    out = capsys.readouterr().out
    assert rc == 2
    assert "drive_zip_upload_failed" in out


def test_v1_pack_keeps_dev_fields_null_and_no_dev_gates(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """v1 producto intacto: sin spec dev no hay gates dev ni zip."""
    pytest.importorskip("pptx")
    vault = _make_vault(tmp_path, _outcome())  # sin spec => v1
    rc = deliver_mod.main(["--pit-id", PIT_ID, "--vault-path", str(vault), "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "PIT_DELIVER_PACK_DRY_OK" in out
    pack = json.loads(
        (vault / "pit" / PIT_ID / "deliverables" / "telegram_pack.json").read_text(
            encoding="utf-8"
        )
    )
    assert pack["deliverable_zip_path"] is None
    assert pack["drive_deliverable_zip_url"] is None
    assert pack["notion_page_url"] is None
    assert any("Preview prototipos" in line for line in pack["summary_lines"])
