"""Tests for scripts/discovery/audit_referentes_quality.py."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from scripts.discovery.audit_referentes_quality import (
    detect_empty_youtube,
    detect_fuzzy_duplicates,
    extract_row_fields,
    main,
    post_to_notion,
    render_report,
)


@pytest.fixture
def rows():
    return [
        {
            "id": "8bad9f1b-0000-0000-0000-000000000001",
            "nombre": "Pascal Bornet",
            "youtube_url": None,
            "plataformas": ["YouTube", "LinkedIn"],
            "is_youtube_creator": True,
            "url": "https://notion.so/p1",
        },
        {
            "id": "b0f28af3-0000-0000-0000-000000000002",
            "nombre": "Pascal Bornet",
            "youtube_url": "https://youtube.com/@pbornet",
            "plataformas": ["YouTube"],
            "is_youtube_creator": True,
            "url": "https://notion.so/p2",
        },
        {
            "id": "id-3",
            "nombre": "Andrew Ng",
            "youtube_url": "https://youtube.com/@andrewng",
            "plataformas": ["YouTube"],
            "is_youtube_creator": True,
            "url": "https://notion.so/p3",
        },
        {
            "id": "id-4",
            "nombre": "Some Org",
            "youtube_url": None,
            "plataformas": ["LinkedIn"],
            "is_youtube_creator": False,
            "url": "https://notion.so/p4",
        },
    ]


def test_detect_empty_youtube_creator_only(rows):
    out = detect_empty_youtube(rows)
    ids = {r["id"] for r in out}
    assert "8bad9f1b-0000-0000-0000-000000000001" in ids
    # Non-YouTube creator must NOT be flagged even if youtube_url empty.
    assert "id-4" not in ids


def test_detect_empty_youtube_full_skipped(rows):
    out = detect_empty_youtube(rows)
    ids = {r["id"] for r in out}
    assert "id-3" not in ids
    assert "b0f28af3-0000-0000-0000-000000000002" not in ids


def test_fuzzy_dedup_pascal_bornet_case(rows):
    dups = detect_fuzzy_duplicates(rows, threshold=90)
    pairs = [(d["id_a"], d["id_b"], d["score"]) for d in dups]
    assert any(
        a == "8bad9f1b-0000-0000-0000-000000000001"
        and b == "b0f28af3-0000-0000-0000-000000000002"
        and score == 100
        for a, b, score in pairs
    )


def test_fuzzy_threshold_respects_cutoff():
    rows_local = [
        {"id": "x1", "nombre": "AlphaBeta"},
        {"id": "x2", "nombre": "GammaDelta"},
    ]
    assert detect_fuzzy_duplicates(rows_local, threshold=90) == []


def test_render_report_schema(rows):
    empty = detect_empty_youtube(rows)
    dups = detect_fuzzy_duplicates(rows, threshold=90)
    report = render_report(empty, dups, total_referentes=len(rows))
    assert set(report.keys()) == {"empty_youtube", "fuzzy_duplicates", "summary"}
    s = report["summary"]
    assert set(s.keys()) == {"n_empty", "n_dups", "total_referentes", "timestamp"}
    assert s["n_empty"] == len(empty)
    assert s["n_dups"] == len(dups)
    assert s["total_referentes"] == len(rows)
    assert isinstance(s["timestamp"], str) and "T" in s["timestamp"]


def test_extract_row_fields_real_shape():
    """Smoke that extract_row_fields handles the real Notion property shapes."""
    page = {
        "id": "page-1",
        "url": "https://notion.so/page-1",
        "properties": {
            "Nombre": {"type": "title", "title": [{"plain_text": "Pascal Bornet"}]},
            "YouTube channel": {"type": "url", "url": None},
            "Plataformas": {
                "type": "multi_select",
                "multi_select": [{"name": "YouTube"}, {"name": "LinkedIn"}],
            },
        },
    }
    row = extract_row_fields(page)
    assert row["nombre"] == "Pascal Bornet"
    assert row["youtube_url"] is None
    assert row["plataformas"] == ["YouTube", "LinkedIn"]
    assert row["is_youtube_creator"] is True


def test_dry_run_no_notion_post(monkeypatch, tmp_path, rows):
    """Dry-run with parent_page_id set must NOT call client.post for /comments."""
    fake_client = MagicMock()
    fake_client.post.return_value.status_code = 200
    fake_client.post.return_value.json.return_value = {"results": [], "has_more": False}

    import scripts.discovery.audit_referentes_quality as mod

    monkeypatch.setattr(mod, "NotionClient", lambda *a, **kw: fake_client)
    monkeypatch.setattr(mod, "fetch_all_referentes", lambda c, ds: rows)
    monkeypatch.setenv("NOTION_API_KEY", "test-key")

    out = tmp_path / "report.json"
    rc = main([
        "--output-json", str(out),
        "--notion-comment-parent-page-id", "page-xyz",
        "--dry-run",
    ])
    assert rc == 0
    assert out.exists()
    for call in fake_client.post.call_args_list:
        assert "/comments" not in call.args[0]


def test_post_to_notion_splits_long_text():
    """post_to_notion uses inline split (no paginator helper coupling)."""
    fake_client = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"id": "comment-id"}
    fake_client.post.return_value = resp

    long_report = {
        "summary": {
            "timestamp": "2026-05-07T00:00:00+00:00",
            "total_referentes": 1,
            "n_empty": 0,
            "n_dups": 0,
        },
        "empty_youtube": [{"nombre": "X" * 200, "id": f"id-{i}"} for i in range(20)],
        "fuzzy_duplicates": [],
    }
    ids = post_to_notion(fake_client, "page-xyz", long_report)
    assert len(ids) >= 1
    for call in fake_client.post.call_args_list:
        assert call.args[0] == "/comments"
