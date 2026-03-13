from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts import audit_to_linear


def test_parse_unchecked_items_extracts_only_open_checkboxes():
    text = """
- [ ] First unchecked item
- [x] Completed item
- [ ] Second unchecked item
"""

    assert audit_to_linear.parse_unchecked_items(text) == [
        "First unchecked item",
        "Second unchecked item",
    ]


def test_get_existing_issue_titles_returns_titles():
    response = {
        "team": {
            "issues": {
                "nodes": [
                    {"title": "[Audit] One"},
                    {"title": "[Audit] Two"},
                ]
            }
        }
    }

    with patch.object(audit_to_linear.linear_client, "_gql", return_value=response):
        titles = audit_to_linear.get_existing_issue_titles("api", "team")

    assert titles == {"[Audit] One", "[Audit] Two"}


def test_get_existing_issue_titles_returns_empty_on_error(capsys):
    with patch.object(audit_to_linear.linear_client, "_gql", side_effect=RuntimeError("boom")):
        titles = audit_to_linear.get_existing_issue_titles("api", "team")

    captured = capsys.readouterr()
    assert titles == set()
    assert "Could not fetch existing issues" in captured.err


def test_main_dry_run_lists_items_without_env(tmp_path, capsys, monkeypatch):
    audit_file = tmp_path / "audit.md"
    audit_file.write_text("- [ ] Fix routing\n- [ ] Add tests\n", encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        ["audit_to_linear.py", "--dry-run", "--file", str(audit_file)],
    )

    audit_to_linear.main()

    captured = capsys.readouterr()
    assert "Found 2 unchecked item(s)" in captured.out
    assert "[DRY RUN] No issues created." in captured.out


def test_main_requires_linear_api_key(tmp_path, monkeypatch):
    audit_file = tmp_path / "audit.md"
    audit_file.write_text("- [ ] Fix routing\n", encoding="utf-8")

    monkeypatch.delenv("LINEAR_API_KEY", raising=False)
    monkeypatch.setenv("LINEAR_TEAM_ID", "team-123")
    monkeypatch.setattr(
        "sys.argv",
        ["audit_to_linear.py", "--file", str(audit_file)],
    )

    with pytest.raises(SystemExit) as excinfo:
        audit_to_linear.main()

    assert excinfo.value.code == 1


def test_main_creates_only_missing_issues(tmp_path, capsys, monkeypatch):
    audit_file = tmp_path / "audit.md"
    audit_file.write_text("- [ ] Fix routing\n- [ ] Add tests\n", encoding="utf-8")

    monkeypatch.setenv("LINEAR_API_KEY", "api-123")
    monkeypatch.setenv("LINEAR_TEAM_ID", "team-123")
    monkeypatch.setattr(
        "sys.argv",
        ["audit_to_linear.py", "--file", str(audit_file)],
    )

    existing = {"[Audit] Fix routing"}
    created_response = {"identifier": "UMB-123"}

    with (
        patch.object(audit_to_linear, "get_existing_issue_titles", return_value=existing),
        patch.object(audit_to_linear.linear_client, "create_issue", return_value=created_response) as mock_create,
    ):
        audit_to_linear.main()

    captured = capsys.readouterr()
    assert "SKIP (exists): [Audit] Fix routing" in captured.out
    assert "CREATED UMB-123: [Audit] Add tests" in captured.out
    mock_create.assert_called_once_with(
        api_key="api-123",
        team_id="team-123",
        title="[Audit] Add tests",
        description=(
            f"Checklist item from audit `{audit_file.name}`:\n\n"
            f"> Add tests\n\n"
            f"_Created automatically by `scripts/audit_to_linear.py`._"
        ),
        priority=3,
    )
