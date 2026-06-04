from __future__ import annotations

from scripts.obsidian_context_check import (
    DEFAULT_REQUIRED_FOLDER_ALIASES,
    DEFAULT_REQUIRED_FOLDERS,
    check_vault,
    main,
)


def _make_vault(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    for folder in DEFAULT_REQUIRED_FOLDERS:
        (vault / folder).mkdir()
    return vault


def test_obsidian_context_check_passes_for_expected_vault(tmp_path, monkeypatch):
    vault = _make_vault(tmp_path)
    monkeypatch.setenv("OBSIDIAN_SYNC_MODE", "pull-only")

    result = check_vault(vault, require_pull_only=True)

    assert result["status"] == "pass"
    assert result["read_only"] is True
    assert result["errors"] == []


def test_obsidian_context_check_passes_for_legacy_english_names(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    for aliases in DEFAULT_REQUIRED_FOLDER_ALIASES:
        (vault / aliases[-1]).mkdir()
    monkeypatch.setenv("OBSIDIAN_SYNC_MODE", "pull-only")

    result = check_vault(vault, require_pull_only=True)

    assert result["status"] == "pass"
    assert result["errors"] == []


def test_obsidian_context_check_fails_missing_folder(tmp_path, monkeypatch):
    vault = _make_vault(tmp_path)
    (vault / "90_evals").rmdir()
    monkeypatch.setenv("OBSIDIAN_SYNC_MODE", "pull-only")

    result = check_vault(vault, require_pull_only=True)

    assert result["status"] == "fail"
    assert any("90_evals" in error for error in result["errors"])


def test_obsidian_context_check_fails_secret_like_file(tmp_path, monkeypatch):
    vault = _make_vault(tmp_path)
    (vault / "00_inbox" / ".env").write_text("SECRET=value", encoding="utf-8")
    monkeypatch.setenv("OBSIDIAN_SYNC_MODE", "pull-only")

    result = check_vault(vault, require_pull_only=True)

    assert result["status"] == "fail"
    assert any("secret-like file" in error for error in result["errors"])


def test_obsidian_context_check_fails_non_pull_only_when_required(tmp_path, monkeypatch):
    vault = _make_vault(tmp_path)
    monkeypatch.setenv("OBSIDIAN_SYNC_MODE", "bidirectional")

    result = check_vault(vault, require_pull_only=True)

    assert result["status"] == "fail"
    assert any("pull-only" in error for error in result["errors"])


def test_obsidian_context_cli_requires_path(monkeypatch):
    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)

    assert main([]) == 2
