"""Tests — scripts/pit/pit_dev_human_qa_gate.py (gate QA producto PIT-DEV).

Quality gate del postmortem ``pit-dev-ifc-viewer``: sin IFC real (>100 KB,
no fixture) + ≥3 screenshots reales + resultado registrado en el outcome, el
deliver no entrega. Los tests cubren skip/evidence/auto y el update del
outcome — el modo auto real (playwright + browser) queda fuera de CI y se
prueba vía el seam ``_import_playwright``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.pit import pit_dev_human_qa_gate as qa_mod
from tests.pit_qa_helpers import write_real_png

PIT_ID = "pit-qa-test"


def _make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    outcome_dir = vault / "pit" / PIT_ID / "outcome"
    outcome_dir.mkdir(parents=True)
    (outcome_dir / "pit_outcome_report.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "pit_id": PIT_ID}, allow_unicode=True),
        encoding="utf-8",
    )
    return vault


def _make_ifc(tmp_path: Path, name: str = "real-building.ifc", size: int = 200 * 1024) -> Path:
    path = tmp_path / name
    path.write_bytes(b"ISO-10303-21;" + b"0" * size)
    return path


def _make_evidence(
    vault: Path,
    *,
    shots: int = 3,
    results: dict | None = None,
    ifc_name: str = "real-building.ifc",
    ifc_size: int = 200 * 1024,
) -> Path:
    shots_dir = qa_mod.qa_screenshots_dir(vault, PIT_ID)
    shots_dir.mkdir(parents=True, exist_ok=True)
    for idx in range(shots):
        write_real_png(shots_dir / f"0{idx + 1}-shot.png")
    if results is None:
        results = {
            "ifc_file": ifc_name,
            "ifc_size_bytes": ifc_size,
            "elements_parsed": 42,
            "fatal_error": False,
        }
    (shots_dir / qa_mod.RESULTS_FILENAME).write_text(
        json.dumps(results), encoding="utf-8"
    )
    return shots_dir


def _outcome(vault: Path) -> dict:
    path = vault / "pit" / PIT_ID / "outcome" / "pit_outcome_report.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Checks unitarios
# ---------------------------------------------------------------------------


def test_check_ifc_rejects_small_file(tmp_path: Path) -> None:
    small = _make_ifc(tmp_path, size=4 * 1024)  # tamaño del fixture del incidente
    with pytest.raises(qa_mod.QaError, match="ifc_too_small"):
        qa_mod.check_ifc_source(small)


def test_check_ifc_rejects_denylisted_fixture(tmp_path: Path) -> None:
    fixture = _make_ifc(tmp_path, name="mini-site.ifc", size=200 * 1024)
    with pytest.raises(qa_mod.QaError, match="ifc_is_test_fixture"):
        qa_mod.check_ifc_source(fixture)


def test_check_ifc_accepts_real_file(tmp_path: Path) -> None:
    real = _make_ifc(tmp_path)
    meta = qa_mod.check_ifc_source(real)
    assert meta["ifc_file"] == "real-building.ifc"
    assert meta["ifc_size_bytes"] > qa_mod.MIN_IFC_BYTES


def test_check_ifc_recorded_metadata_without_file() -> None:
    meta = qa_mod.check_ifc_source(
        None, recorded_name="hospital.ifc", recorded_size=5_000_000
    )
    assert meta == {"ifc_file": "hospital.ifc", "ifc_size_bytes": 5_000_000}
    with pytest.raises(qa_mod.QaError, match="ifc_file_not_recorded"):
        qa_mod.check_ifc_source(None, recorded_name="", recorded_size=1)
    with pytest.raises(qa_mod.QaError, match="ifc_is_test_fixture"):
        qa_mod.check_ifc_source(None, recorded_name="MINI-SITE.ifc", recorded_size=5_000_000)


def test_check_screenshots_requires_three_real_pngs(tmp_path: Path) -> None:
    shots = tmp_path / "shots"
    shots.mkdir()
    write_real_png(shots / "01.png")
    write_real_png(shots / "02.png")
    # PNG falso (magic ok, tamaño trivial) NO cuenta
    (shots / "03.png").write_bytes(qa_mod.PNG_MAGIC + b"tiny")
    with pytest.raises(qa_mod.QaError, match="qa_screenshots_insufficient:2/3"):
        qa_mod.check_screenshots(shots)
    write_real_png(shots / "04.png")
    assert len(qa_mod.check_screenshots(shots)) == 3


def test_validate_results_needs_elements_and_no_fatal() -> None:
    assert qa_mod.validate_results({"elements_parsed": 7, "fatal_error": False}) == 7
    with pytest.raises(qa_mod.QaError, match="no_elements_parsed"):
        qa_mod.validate_results({"elements_parsed": 0})
    with pytest.raises(qa_mod.QaError, match="elements_parsed_not_recorded"):
        qa_mod.validate_results({})
    with pytest.raises(qa_mod.QaError, match="fatal_error_recorded"):
        qa_mod.validate_results({"elements_parsed": 3, "fatal_error": "Uncaught TypeError"})


# ---------------------------------------------------------------------------
# Modo skip
# ---------------------------------------------------------------------------


def test_skip_writes_block_and_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = _make_vault(tmp_path)
    rc = qa_mod.main([
        "--pit-id", PIT_ID, "--vault-path", str(vault),
        "--skip", "--reason", "deliverable es una CLI sin UI",
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert "PIT_DEV_QA_SKIPPED" in out
    block = _outcome(vault)["human_qa"]
    assert block["status"] == "QA_SKIPPED_WITH_REASON"
    assert block["reason"] == "deliverable es una CLI sin UI"
    assert block["real_ifc_upload"] == "skipped"


def test_skip_without_reason_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = _make_vault(tmp_path)
    rc = qa_mod.main(["--pit-id", PIT_ID, "--vault-path", str(vault), "--skip"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "skip_requires_reason" in out


# ---------------------------------------------------------------------------
# Modo evidence
# ---------------------------------------------------------------------------


def test_evidence_pass_updates_outcome(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = _make_vault(tmp_path)
    ifc = _make_ifc(tmp_path)
    _make_evidence(vault)
    rc = qa_mod.main([
        "--pit-id", PIT_ID, "--vault-path", str(vault),
        "--from-evidence", "--ifc-file", str(ifc),
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert "PIT_DEV_QA_PASS" in out
    assert "screenshots=3" in out
    assert "elements_parsed=42" in out
    block = _outcome(vault)["human_qa"]
    assert block["status"] == "QA_PASS"
    assert block["real_ifc_upload"] == "pass"
    assert block["ifc_file"] == "real-building.ifc"
    assert block["elements_parsed"] == 42
    assert len(block["screenshots"]) == 3
    assert block["screenshots_dir"] == f"pit/{PIT_ID}/deliverables/qa-screenshots"
    assert block["verified_at"]


def test_evidence_uses_recorded_ifc_metadata_when_no_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = _make_vault(tmp_path)
    _make_evidence(vault)  # qa_results.json registra el IFC real
    rc = qa_mod.main(["--pit-id", PIT_ID, "--vault-path", str(vault), "--from-evidence"])
    assert rc == 0
    assert "PIT_DEV_QA_PASS" in capsys.readouterr().out


def test_evidence_fail_records_qa_fail_in_outcome(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = _make_vault(tmp_path)
    _make_evidence(vault, shots=2)  # insuficiente
    rc = qa_mod.main(["--pit-id", PIT_ID, "--vault-path", str(vault), "--from-evidence"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "PIT_DEV_QA_FAIL" in out
    assert "qa_screenshots_insufficient" in out
    block = _outcome(vault)["human_qa"]
    assert block["status"] == "QA_FAIL"  # sin bypass silencioso
    assert "qa_screenshots_insufficient" in block["reason"]


def test_evidence_fail_when_fixture_ifc_recorded(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = _make_vault(tmp_path)
    _make_evidence(
        vault,
        results={
            "ifc_file": "mini-site.ifc",
            "ifc_size_bytes": 4508,
            "elements_parsed": 10,
            "fatal_error": False,
        },
    )
    rc = qa_mod.main(["--pit-id", PIT_ID, "--vault-path", str(vault), "--from-evidence"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "ifc_is_test_fixture" in out


def test_evidence_fail_when_results_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = _make_vault(tmp_path)
    shots_dir = qa_mod.qa_screenshots_dir(vault, PIT_ID)
    shots_dir.mkdir(parents=True)
    for idx in range(3):
        write_real_png(shots_dir / f"0{idx + 1}.png")
    rc = qa_mod.main(["--pit-id", PIT_ID, "--vault-path", str(vault), "--from-evidence"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "qa_results_missing" in out


def test_outcome_missing_is_fail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = tmp_path / "vault"  # sin outcome
    _make_evidence(vault)
    rc = qa_mod.main(["--pit-id", PIT_ID, "--vault-path", str(vault), "--from-evidence"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "outcome_missing" in out


# ---------------------------------------------------------------------------
# Modo auto (playwright)
# ---------------------------------------------------------------------------


def test_auto_requires_url_and_ifc(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = _make_vault(tmp_path)
    rc = qa_mod.main(["--pit-id", PIT_ID, "--vault-path", str(vault), "--auto"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "auto_requires_app_url_and_ifc_file" in out


def test_auto_requires_elements_probe(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = _make_vault(tmp_path)
    ifc = _make_ifc(tmp_path)
    rc = qa_mod.main([
        "--pit-id", PIT_ID, "--vault-path", str(vault), "--auto",
        "--app-url", "http://127.0.0.1:9", "--ifc-file", str(ifc),
    ])
    out = capsys.readouterr().out
    assert rc == 2
    assert "elements_probe_required" in out


def test_auto_without_playwright_is_clear_fail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    vault = _make_vault(tmp_path)
    ifc = _make_ifc(tmp_path)

    def _no_playwright():
        raise ImportError("No module named 'playwright'")

    monkeypatch.setattr(qa_mod, "_import_playwright", _no_playwright)
    rc = qa_mod.main([
        "--pit-id", PIT_ID, "--vault-path", str(vault), "--auto",
        "--app-url", "http://127.0.0.1:9", "--ifc-file", str(ifc),
        "--elements-js", "window.__elements",
    ])
    out = capsys.readouterr().out
    assert rc == 2
    assert "playwright_not_installed" in out
    # el FAIL queda registrado en el outcome (fail-closed, visible)
    assert _outcome(vault)["human_qa"]["status"] == "QA_FAIL"


def test_invalid_pit_id_fails(capsys: pytest.CaptureFixture[str]) -> None:
    rc = qa_mod.main(["--pit-id", "bad id!", "--skip", "--reason", "x"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "invalid_pit_id" in out
