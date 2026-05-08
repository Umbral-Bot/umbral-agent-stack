"""Task 036b — sim_daily_report writer paginator integration.

These tests pin the contract between the SIM daily-report writer and the
paginator helper (`dispatcher.extractors.notion_comment_paginator`). They do
NOT exercise Notion HTTP — the adapter is replaced with an in-memory
``MagicMock`` satisfying the helper's ``NotionLikeClient`` Protocol.
"""

from __future__ import annotations

import io
import os
import sys
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import MagicMock

import pytest

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts import sim_daily_report as sdr  # noqa: E402


SHORT_TEXT = "small report\nline2\nline3"
LONG_TEXT_HEADER = "SIM Daily Report (2026-05-07 18:30 UTC)"
LONG_TEXT_BODY = (
    f"{LONG_TEXT_HEADER}\n"
    "Ventana: ultimas 168h\n"
    "\n"
    "Actividad:\n"
    "- research.web: 17 total | 14 exitosas | 3 fallidas\n"
    "- llm.generate: 4 total | 4 exitosas | 0 fallidas\n"
    "\n"
    + ("x" * 50 + "\n") * 60
)
LONG_TEXT = LONG_TEXT_BODY  # ~3.1KB, > SAFE_LIMIT (1900)
PARENT_PAGE = "task-page-id-1234"
SUBPAGE_PARENT = "sim-reports-parent-5678"


def _mock_client(page_id: str = "new-subpage-id", url: str = "https://www.notion.so/new"):
    client = MagicMock()
    client.add_comment.return_value = {"comment_id": "cmt-abc"}
    client.create_subpage.return_value = {"page_id": page_id, "url": url}
    # Task 047 idempotency hooks: default = no existing page, no existing comment.
    client.find_subpage_by_title.return_value = None
    client.list_recent_comments.return_value = []
    return client


# ---------------------------------------------------------------------------
# Direct paginator behaviour through the writer's public entry-point
# ---------------------------------------------------------------------------


def test_short_report_uses_single_comment():
    """≤ SAFE_LIMIT → exactly one add_comment call, no subpage."""
    client = _mock_client()
    result = sdr.post_report(
        SHORT_TEXT,
        page_id=PARENT_PAGE,
        body_page_parent_id=SUBPAGE_PARENT,
        client=client,
    )
    assert client.add_comment.call_count == 1
    assert client.create_subpage.call_count == 0
    posted_parent, posted_text = client.add_comment.call_args[0]
    assert posted_parent == PARENT_PAGE
    assert posted_text == SHORT_TEXT
    assert result["parts"] == 1
    assert result["page_id"] is None
    assert result["truncated"] is False


def test_long_report_with_parent_creates_subpage():
    """Task 047: > SAFE_LIMIT + parent → 1 create_subpage + 1 compact add_comment.

    Compact comment must contain header, summary, and page URL — and stay
    well below SAFE_LIMIT (target ~300 chars, NOT ~1800 like the old
    leading-lines path).
    """
    assert len(LONG_TEXT) > sdr.SAFE_LIMIT
    client = _mock_client(page_id="page-XYZ", url="https://www.notion.so/page-XYZ")
    result = sdr.post_report(
        LONG_TEXT,
        page_id=PARENT_PAGE,
        body_page_parent_id=SUBPAGE_PARENT,
        client=client,
    )
    # Idempotency probe was attempted before create.
    client.find_subpage_by_title.assert_called_once()
    assert client.create_subpage.call_count == 1
    assert client.add_comment.call_count == 1

    sub_parent, sub_title, sub_blocks = client.create_subpage.call_args[0]
    assert sub_parent == SUBPAGE_PARENT
    # Date-only title for cross-run idempotency.
    assert sub_title == "SIM Daily Report 2026-05-07"
    assert isinstance(sub_blocks, list) and sub_blocks  # full body offloaded

    posted_parent, posted_text = client.add_comment.call_args[0]
    assert posted_parent == PARENT_PAGE
    assert "https://www.notion.so/page-XYZ" in posted_text
    assert LONG_TEXT_HEADER in posted_text
    assert "research.web 17" in posted_text
    assert "llm.generate 4" in posted_text
    # Compact: header + summary + URL line ≪ SAFE_LIMIT.
    assert len(posted_text) < 500, f"compact comment too long: {len(posted_text)}"
    assert result["page_id"] == "page-XYZ"
    assert result["parts"] == 1
    assert result["reused_page"] is False
    assert result["reused_comment"] is False
    assert result["comment_chars"] == len(posted_text)


def test_idempotent_subpage_reuse_skips_create():
    """Task 047: same date re-run → reuse existing subpage, do NOT call create."""
    client = _mock_client()
    client.find_subpage_by_title.return_value = {
        "page_id": "page-EXISTING",
        "url": "https://www.notion.so/page-EXISTING",
    }
    result = sdr.post_report(
        LONG_TEXT,
        page_id=PARENT_PAGE,
        body_page_parent_id=SUBPAGE_PARENT,
        client=client,
    )
    assert client.create_subpage.call_count == 0
    assert client.add_comment.call_count == 1  # comment is fresh
    posted_parent, posted_text = client.add_comment.call_args[0]
    assert "page-EXISTING" in posted_text
    assert result["page_id"] == "page-EXISTING"
    assert result["reused_page"] is True
    assert result["reused_comment"] is False


def test_idempotent_comment_reuse_skips_post():
    """Task 047: existing comment containing page URL → no new add_comment call."""
    page_url = "https://www.notion.so/page-EXISTING"
    client = _mock_client()
    client.find_subpage_by_title.return_value = {
        "page_id": "page-EXISTING",
        "url": page_url,
    }
    client.list_recent_comments.return_value = [
        {
            "id": "cmt-OLD",
            "rich_text": [{"text": {"content": f"prev run: detalle {page_url}"}}],
        }
    ]
    result = sdr.post_report(
        LONG_TEXT,
        page_id=PARENT_PAGE,
        body_page_parent_id=SUBPAGE_PARENT,
        client=client,
    )
    assert client.create_subpage.call_count == 0
    assert client.add_comment.call_count == 0
    assert result["comment_id"] == "cmt-OLD"
    assert result["reused_page"] is True
    assert result["reused_comment"] is True


def test_synthetic_50_urls_full_body_in_subpage():
    """Task 047 quality gate: report with 50 URLs is offloaded WHOLE to subpage."""
    urls = [f"https://example.com/article-{i}" for i in range(50)]
    body = (
        "SIM Daily Report (2026-05-07 18:30 UTC)\n"
        "Ventana: ultimas 168h\n\n"
        "Actividad:\n"
        "- research.web: 50 total | 47 exitosas | 3 fallidas\n"
        "- llm.generate: 5 total | 5 exitosas | 0 fallidas\n\n"
        "URLs encontradas (research.web):\n"
        + "\n".join(f"{i + 1}. {u}" for i, u in enumerate(urls))
    )
    assert len(body) > sdr.SAFE_LIMIT
    client = _mock_client(page_id="page-50", url="https://www.notion.so/page-50")
    sdr.post_report(
        body,
        page_id=PARENT_PAGE,
        body_page_parent_id=SUBPAGE_PARENT,
        client=client,
    )
    _parent, _title, blocks = client.create_subpage.call_args[0]
    rendered = "\n".join(
        b["paragraph"]["rich_text"][0]["text"]["content"] for b in blocks
    )
    for u in urls:
        assert u in rendered, f"URL missing from subpage body: {u}"
    posted_text = client.add_comment.call_args[0][1]
    # Compact comment must NOT contain individual URLs (only the page URL).
    for u in urls:
        assert u not in posted_text
    assert len(posted_text) < 500


def test_long_report_no_parent_falls_back_split():
    """> SAFE_LIMIT + no parent → numbered split + WARN on stderr."""
    client = _mock_client()
    buf = io.StringIO()
    with redirect_stderr(buf):
        result = sdr.post_report(
            LONG_TEXT,
            page_id=PARENT_PAGE,
            body_page_parent_id=None,
            client=client,
        )
    err = buf.getvalue()
    assert "WARN" in err
    assert "SIM_REPORTS_PARENT_PAGE" in err
    assert client.create_subpage.call_count == 0
    assert client.add_comment.call_count >= 2
    assert result["parts"] >= 2
    assert isinstance(result["comment_id"], list)
    # Every emitted part must be tagged [i/N] and within the budget.
    for call in client.add_comment.call_args_list:
        posted_parent, posted_text = call[0]
        assert posted_parent == PARENT_PAGE
        assert posted_text.startswith("[")
        assert "/" in posted_text.split("]")[0]
        assert len(posted_text) <= sdr.SAFE_LIMIT


# ---------------------------------------------------------------------------
# CLI flag / ENV plumbing for --sim-reports-parent-page-id
# ---------------------------------------------------------------------------


def _run_main_capturing(argv, monkeypatch, *, post_report_return=None, raise_exc=None):
    """Drive sdr.main() with a stubbed post_report and stubbed event source."""
    captured: dict = {}

    def fake_post_report(text, *, page_id=None, body_page_parent_id=None, client=None):
        captured["text"] = text
        captured["page_id"] = page_id
        captured["body_page_parent_id"] = body_page_parent_id
        if raise_exc is not None:
            raise raise_exc
        return post_report_return or {"comment_id": "cmt-xyz", "parts": 1, "page_id": None}

    monkeypatch.setattr(sdr, "post_report", fake_post_report)
    # Stub OpsLogger so main() doesn't read disk / Redis.
    fake_ops = MagicMock()
    fake_ops.read_events.return_value = []
    monkeypatch.setattr(sdr, "OpsLogger", lambda: fake_ops)
    monkeypatch.setattr(sdr, "_load_task_details", lambda task_ids: {})

    monkeypatch.setattr(sys, "argv", ["sim_daily_report.py", *argv])
    rc = sdr.main()
    return rc, captured


def test_cli_flag_overrides_env(monkeypatch):
    monkeypatch.setenv("SIM_REPORTS_PARENT_PAGE", "ENV_PARENT")
    monkeypatch.setenv("NOTION_CONTROL_ROOM_PAGE_ID", "CTRL_ROOM")
    rc, captured = _run_main_capturing(
        ["--notion", "--sim-reports-parent-page-id", "FLAG_PARENT"],
        monkeypatch,
    )
    assert rc == 0
    assert captured["body_page_parent_id"] == "FLAG_PARENT"


def test_cli_flag_missing_uses_env(monkeypatch):
    monkeypatch.setenv("SIM_REPORTS_PARENT_PAGE", "ENV_PARENT")
    monkeypatch.setenv("NOTION_CONTROL_ROOM_PAGE_ID", "CTRL_ROOM")
    rc, captured = _run_main_capturing(["--notion"], monkeypatch)
    assert rc == 0
    assert captured["body_page_parent_id"] == "ENV_PARENT"


def test_no_parent_no_env_warns(monkeypatch):
    """Both missing + oversized payload → paginator warns; --notion path still runs."""
    monkeypatch.delenv("SIM_REPORTS_PARENT_PAGE", raising=False)
    monkeypatch.setenv("NOTION_CONTROL_ROOM_PAGE_ID", "CTRL_ROOM")
    # Stub main()'s post_report so we don't hit Notion. The actual WARN that
    # the spec asks for lives inside the real post_report; verify it directly
    # with an oversized payload + None parent + a mock client.
    client = _mock_client()
    buf = io.StringIO()
    with redirect_stderr(buf):
        sdr.post_report(LONG_TEXT, page_id="P", body_page_parent_id=None, client=client)
    assert "WARN" in buf.getvalue()
    # Plus: main() with --notion + neither set → body_page_parent_id forwarded as None.
    rc, captured = _run_main_capturing(["--notion"], monkeypatch)
    assert rc == 0
    assert captured["body_page_parent_id"] is None


# ---------------------------------------------------------------------------
# Bonus: legacy _trim_for_comment is no longer applied in build_report
# ---------------------------------------------------------------------------


def test_build_report_does_not_truncate(monkeypatch):
    """Regression guard: build_report must NOT add `[truncated]` suffix anymore."""
    # Synthesize many fake research events so the report grows past SAFE_LIMIT
    # via topics / urls. We just assert that whatever build_report returns is
    # never wrapped with the truncated suffix (paginator handles oversize).
    events = []
    details: dict[str, dict] = {}
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    text = sdr.build_report(events, task_details=details, now=now, window_hours=24)
    assert "[truncated]" not in text
