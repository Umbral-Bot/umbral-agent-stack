"""Tests for scripts/pit/pit_vault_check.py (umbral-pit-vault structure)."""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.pit.pit_vault_check import (
    REQUIRED_FOLDERS,
    WRITABLE_ROOTS,
    check_pit_vault,
)


def _make_valid_vault(root: Path) -> Path:
    vault = root / "umbral-pit-vault"
    for folder in ("pit", "templates", "archive"):
        (vault / folder).mkdir(parents=True)
    (vault / "README.md").write_text("# umbral-pit-vault\n", encoding="utf-8")
    return vault


def test_valid_vault_passes(tmp_path, monkeypatch):
    monkeypatch.delenv("PIT_VAULT_WRITE_SCOPE", raising=False)
    vault = _make_valid_vault(tmp_path)
    result = check_pit_vault(vault)
    assert result["status"] == "pass", result["errors"]
    assert result["read_only"] is True
    assert result["writable_roots"] == ["pit"]
    assert result["required_folders"] == list(REQUIRED_FOLDERS)


def test_missing_required_folders_fail(tmp_path):
    vault = tmp_path / "vault"
    (vault / "pit").mkdir(parents=True)
    result = check_pit_vault(vault)
    assert result["status"] == "fail"
    missing = {e for e in result["errors"] if e.startswith("missing required folder")}
    assert {"missing required folder: templates", "missing required folder: archive"} == missing


def test_vault_path_not_found_fails(tmp_path):
    result = check_pit_vault(tmp_path / "nope")
    assert result["status"] == "fail"
    assert any("not found" in e for e in result["errors"])


def test_secret_like_file_inside_pit_fails(tmp_path):
    vault = _make_valid_vault(tmp_path)
    lane_dir = vault / "pit" / "pit-demo" / "lanes" / "lane-a"
    lane_dir.mkdir(parents=True)
    (lane_dir / ".env").write_text("TOKEN=nope\n", encoding="utf-8")
    result = check_pit_vault(vault)
    assert result["status"] == "fail"
    assert any("secret-like" in e for e in result["errors"])


def test_nested_obsidian_vault_fails(tmp_path):
    vault = _make_valid_vault(tmp_path)
    (vault / "pit" / "pit-demo" / ".obsidian").mkdir(parents=True)
    result = check_pit_vault(vault)
    assert result["status"] == "fail"
    assert any("nested Obsidian vault" in e for e in result["errors"])


def test_stray_root_file_fails(tmp_path):
    vault = _make_valid_vault(tmp_path)
    (vault / "notas-sueltas.md").write_text("x\n", encoding="utf-8")
    result = check_pit_vault(vault)
    assert result["status"] == "fail"
    assert any("unexpected file at vault root" in e for e in result["errors"])
    assert "notas-sueltas.md" in result["stray_root_files"]


def test_root_allowlist_files_ok(tmp_path):
    vault = _make_valid_vault(tmp_path)
    (vault / ".gitignore").write_text(".obsidian/workspace.json\n", encoding="utf-8")
    result = check_pit_vault(vault)
    assert result["status"] == "pass", result["errors"]


def test_require_write_scope_fails_without_env(tmp_path, monkeypatch):
    monkeypatch.delenv("PIT_VAULT_WRITE_SCOPE", raising=False)
    vault = _make_valid_vault(tmp_path)
    result = check_pit_vault(vault, require_write_scope=True)
    assert result["status"] == "fail"
    assert any("PIT_VAULT_WRITE_SCOPE" in e for e in result["errors"])


def test_require_write_scope_passes_with_pit_env(tmp_path, monkeypatch):
    monkeypatch.setenv("PIT_VAULT_WRITE_SCOPE", "pit")
    vault = _make_valid_vault(tmp_path)
    result = check_pit_vault(vault, require_write_scope=True)
    assert result["status"] == "pass", result["errors"]
    assert result["write_scope"] == "pit"


def test_wrong_write_scope_warns_when_not_required(tmp_path, monkeypatch):
    monkeypatch.setenv("PIT_VAULT_WRITE_SCOPE", "everything")
    vault = _make_valid_vault(tmp_path)
    result = check_pit_vault(vault, require_write_scope=False)
    assert result["status"] == "pass"
    assert any("PIT_VAULT_WRITE_SCOPE" in w for w in result["warnings"])


def test_tournament_without_spec_warns(tmp_path, monkeypatch):
    monkeypatch.delenv("PIT_VAULT_WRITE_SCOPE", raising=False)
    vault = _make_valid_vault(tmp_path)
    (vault / "pit" / "pit-sin-spec").mkdir()
    result = check_pit_vault(vault)
    assert result["status"] == "pass"
    assert any("without spec" in w for w in result["warnings"])
    assert result["tournaments"] == ["pit-sin-spec"]


def test_tournament_with_spec_no_warning(tmp_path, monkeypatch):
    monkeypatch.delenv("PIT_VAULT_WRITE_SCOPE", raising=False)
    vault = _make_valid_vault(tmp_path)
    spec_dir = vault / "pit" / "pit-ok" / "spec"
    spec_dir.mkdir(parents=True)
    (spec_dir / "pit_spec.yaml").write_text("pit_id: pit-ok\n", encoding="utf-8")
    result = check_pit_vault(vault)
    assert result["status"] == "pass"
    assert not any("without spec" in w for w in result["warnings"])
    assert result["tournaments"] == ["pit-ok"]


def test_writable_roots_constant_is_pit_only():
    assert WRITABLE_ROOTS == ("pit",)
