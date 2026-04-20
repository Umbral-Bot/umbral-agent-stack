"""Tests for the Granola transcript finality + reconciliation flow.

Covers:

- truncation detector (the "Comgrap Dynamo" tail ending in a comma)
- partial -> complete reconciliation (same granola_document_id should update,
  not duplicate, the existing Notion page)
- dry-run / audit mode (no Notion writes)
- content hash unchanged -> noop
- repeated title with a different granola_document_id -> new page is created
- stability window defers first ingests of a freshly-updated Granola doc

These tests mock ``worker.tasks.granola.notion_client`` so they stay hermetic.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

os.environ.setdefault("WORKER_TOKEN", "test-token-12345")

from worker.tasks.granola import (  # noqa: E402
    _build_existing_raw_candidate,
    handle_granola_process_transcript,
)
from worker.tasks.granola_finality import (  # noqa: E402
    compute_transcript_metrics,
    decide_reconciliation,
    detect_truncation,
)


# ---------------------------------------------------------------------------
# Helper: a realistic schema + existing row factory
# ---------------------------------------------------------------------------


_BASE_SCHEMA = {
    "Título": "title",
    "Estado": "select",
    "Fecha de transcripción": "date",
    "Fecha que Rick pasó a Notion": "date",
    "Fecha que el agente procesó": "date",
    "Granola Document ID": "rich_text",
    "Source Updated At": "rich_text",
    "Source URL": "url",
    "Trazabilidad": "rich_text",
    "Tags": "multi_select",
}


def _mock_db(mock_nc, *, existing_pages=None, schema=None):
    mock_nc.read_database.return_value = {"schema": schema or dict(_BASE_SCHEMA)}
    mock_nc.query_database.return_value = existing_pages or []
    mock_nc.create_database_page.return_value = {
        "page_id": "page-new",
        "url": "https://notion.so/page-new",
        "created": True,
    }
    mock_nc.update_page_properties.return_value = {
        "page_id": "page-existing",
        "url": "https://notion.so/page-existing",
        "updated": True,
    }


def _mock_read_page_full_snapshot(mock_nc, content, page_id="page-new", page_url=""):
    blocks = []
    for i in range(0, len(content), 2000):
        blocks.append({"type": "paragraph", "text": content[i : i + 2000]})
    mock_nc.read_page_full.return_value = {
        "page_id": page_id,
        "url": page_url or f"https://notion.so/{page_id}",
        "title": "",
        "blocks": blocks,
        "plain_text": "\n".join(block["text"] for block in blocks),
        "block_count": len(blocks),
        "has_more": False,
    }


def _existing_page(
    *,
    page_id: str,
    title: str,
    date: str,
    granola_document_id: str,
    traceability_text: str,
    source_updated_at: str = "",
    url: str | None = None,
):
    return {
        "id": page_id,
        "url": url or f"https://notion.so/{page_id}",
        "last_edited_time": "2026-04-02T13:20:00Z",
        "properties": {
            "Título": {
                "type": "title",
                "title": [{"plain_text": title, "text": {"content": title}}],
            },
            # _extract_date_from_page reads "Fecha" / "Date" / ASCII variant
            # first, so expose both spellings to match what the real Granola
            # DB does in practice (legacy schema uses "Fecha de transcripción").
            "Fecha": {
                "type": "date",
                "date": {"start": date},
            },
            "Fecha de transcripción": {
                "type": "date",
                "date": {"start": date},
            },
            "Granola Document ID": {
                "type": "rich_text",
                "rich_text": [
                    {"plain_text": granola_document_id, "text": {"content": granola_document_id}}
                ],
            },
            "Trazabilidad": {
                "type": "rich_text",
                "rich_text": [
                    {"plain_text": traceability_text, "text": {"content": traceability_text}}
                ],
            },
            "Source Updated At": {
                "type": "rich_text",
                "rich_text": [
                    {"plain_text": source_updated_at, "text": {"content": source_updated_at}}
                ],
            },
        },
    }


# Content fixtures -----------------------------------------------------------

# Long enough to pass the `min_stable_chars` gate, ends mid-sentence on a comma
# — mimics the real Comgrap Dynamo truncation observed in production.
_TRUNCATED_TAIL = (
    "Entonces Me imagino, sí. Decía Lillo. De hecho, lo lo planteé a la señora,"
)
_PARTIAL_CONTENT = (
    "## Notes\n\nResumen breve de la reunión con padding adicional. " * 10
    + "\n\n## Transcript\n\n- **David:** [10:00:00] "
    + _TRUNCATED_TAIL
)
_FULL_CONTENT = (
    _PARTIAL_CONTENT
    + " y ella confirmó que avanzamos con la propuesta comercial."
    + " Siguiente reunión acordada para revisar contratos."
)


# ---------------------------------------------------------------------------
# Truncation detector
# ---------------------------------------------------------------------------


class TestDetectTruncation:
    def test_tail_ending_with_comma_is_truncated(self):
        report = detect_truncation(_PARTIAL_CONTENT)
        assert report.truncated is True
        assert report.tail_terminator == ","
        assert "tail_ends_with_marker" in report.reason

    def test_complete_sentence_is_not_truncated(self):
        report = detect_truncation(_FULL_CONTENT)
        assert report.truncated is False
        assert report.tail_terminator == "."

    def test_empty_content_is_truncated(self):
        report = detect_truncation("")
        assert report.truncated is True
        assert report.reason == "empty_content"

    def test_long_content_with_quote_close_is_not_truncated(self):
        text = (
            "Este es un texto claramente completo con muchas oraciones bien formadas. "
            * 10
            + "La cita final termina bien. "
            + "Y una cita final: 'todo ok.'"
        )
        report = detect_truncation(text.strip())
        assert report.truncated is False, report


# ---------------------------------------------------------------------------
# compute_transcript_metrics
# ---------------------------------------------------------------------------


class TestComputeTranscriptMetrics:
    def test_char_and_hash_stable(self):
        m1 = compute_transcript_metrics(_FULL_CONTENT)
        m2 = compute_transcript_metrics(_FULL_CONTENT)
        assert m1.content_hash == m2.content_hash
        assert m1.char_count == len(_FULL_CONTENT)
        assert m1.segment_count >= 1

    def test_partial_vs_full_differ(self):
        assert (
            compute_transcript_metrics(_PARTIAL_CONTENT).content_hash
            != compute_transcript_metrics(_FULL_CONTENT).content_hash
        )


# ---------------------------------------------------------------------------
# decide_reconciliation
# ---------------------------------------------------------------------------


class TestDecideReconciliation:
    def test_create_when_no_existing(self):
        decision = decide_reconciliation(
            existing=None,
            new_content=_FULL_CONTENT,
            source_updated_at="2026-04-01T12:00:00Z",
            now=datetime(2026, 4, 2, tzinfo=timezone.utc),
        )
        assert decision.action == "create"

    def test_defer_when_inside_stability_window(self):
        now = datetime(2026, 4, 2, 12, 0, tzinfo=timezone.utc)
        recent = (now - timedelta(minutes=2)).isoformat().replace("+00:00", "Z")
        decision = decide_reconciliation(
            existing=None,
            new_content=_FULL_CONTENT,
            source_updated_at=recent,
            now=now,
            stability_window=15 * 60,
        )
        assert decision.action == "defer"
        assert decision.stability_wait_seconds > 0

    def test_reconcile_when_hash_changes(self):
        existing = {
            "content_hash": "old-hash",
            "char_count": len(_PARTIAL_CONTENT),
            "segment_count": 3,
            "source_updated_at": "2026-04-01T11:00:00Z",
        }
        decision = decide_reconciliation(
            existing=existing,
            new_content=_FULL_CONTENT,
            source_updated_at="2026-04-01T12:30:00Z",
            now=datetime(2026, 4, 2, tzinfo=timezone.utc),
        )
        assert decision.action == "reconcile"
        # Either content_hash_changed or source_updated_at_newer is an acceptable
        # reason; both signal the content moved forward. We accept either.
        assert any(
            marker in decision.reason
            for marker in ("content_hash_changed", "source_updated_at_newer")
        ), decision.reason

    def test_noop_when_hash_and_char_count_match(self):
        metrics = compute_transcript_metrics(_FULL_CONTENT)
        existing = {
            "content_hash": metrics.content_hash,
            "char_count": metrics.char_count,
            "segment_count": metrics.segment_count,
            "source_updated_at": "2026-04-01T12:00:00Z",
        }
        decision = decide_reconciliation(
            existing=existing,
            new_content=_FULL_CONTENT,
            source_updated_at="2026-04-01T12:00:00Z",
            now=datetime(2026, 4, 2, tzinfo=timezone.utc),
        )
        assert decision.action == "noop"

    def test_force_reconcile_overrides_noop(self):
        metrics = compute_transcript_metrics(_FULL_CONTENT)
        existing = {
            "content_hash": metrics.content_hash,
            "char_count": metrics.char_count,
            "segment_count": metrics.segment_count,
            "source_updated_at": "2026-04-01T12:00:00Z",
        }
        decision = decide_reconciliation(
            existing=existing,
            new_content=_FULL_CONTENT,
            source_updated_at="2026-04-01T12:00:00Z",
            now=datetime(2026, 4, 2, tzinfo=timezone.utc),
            force_reconcile=True,
        )
        assert decision.action == "reconcile"

    def test_reconcile_when_source_newer_even_without_hash(self):
        existing = {
            "content_hash": "",
            "char_count": 0,
            "segment_count": 0,
            "source_updated_at": "2026-04-01T11:00:00Z",
        }
        decision = decide_reconciliation(
            existing=existing,
            new_content=_FULL_CONTENT,
            source_updated_at="2026-04-01T12:30:00Z",
            now=datetime(2026, 4, 2, tzinfo=timezone.utc),
        )
        assert decision.action == "reconcile"


# ---------------------------------------------------------------------------
# handle_granola_process_transcript integration
# ---------------------------------------------------------------------------


class TestProcessTranscriptReconciliation:
    @patch("worker.tasks.granola.notion_client")
    def test_partial_then_full_reconciles_same_page(self, mock_nc):
        # Existing raw page stores the partial transcript with Comgrap-like tail.
        partial_metrics = compute_transcript_metrics(_PARTIAL_CONTENT)
        traceability_partial = (
            "granola_document_id=doc-comgrap\n"
            "source_updated_at=2026-04-01T11:00:00Z\n"
            f"content_hash={partial_metrics.content_hash}\n"
            f"char_count={partial_metrics.char_count}\n"
            f"segment_count={partial_metrics.segment_count}\n"
            "truncation_detected=true\n"
            "truncation_reason=tail_ends_with_marker:','\n"
            "ingested_at=2026-04-01T11:05:00Z\n"
            "ingest_path=granola.process_transcript"
        )
        existing_page = _existing_page(
            page_id="page-comgrap",
            title="Comgrap Dynamo",
            date="2026-04-01",
            granola_document_id="doc-comgrap",
            traceability_text=traceability_partial,
            source_updated_at="2026-04-01T11:00:00Z",
        )
        _mock_db(mock_nc, existing_pages=[existing_page])
        _mock_read_page_full_snapshot(mock_nc, _FULL_CONTENT, page_id="page-comgrap")

        result = handle_granola_process_transcript(
            {
                "title": "Comgrap Dynamo",
                "content": _FULL_CONTENT,
                "date": "2026-04-01",
                "granola_document_id": "doc-comgrap",
                "source_updated_at": "2026-04-02T08:30:00Z",
                "notify_enlace": False,
                # Skip the stability window so the test is deterministic.
                "stability_window_seconds": 0,
            }
        )

        assert result["matched_existing"] is True
        assert result["match_strategy"] == "granola_document_id"
        assert result["page_id"] == "page-comgrap"
        assert result["reconciliation_action"] == "reconcile"
        mock_nc.create_database_page.assert_not_called()
        mock_nc.update_page_properties.assert_called_once()
        mock_nc.replace_blocks_in_page.assert_called_once()

        update_args = mock_nc.update_page_properties.call_args
        assert update_args.args[0] == "page-comgrap"
        traceability_written = update_args.kwargs["properties"]["Trazabilidad"][
            "rich_text"
        ][0]["text"]["content"]
        assert "content_hash=" in traceability_written
        assert "reconciled_at=" in traceability_written
        assert "truncation_detected=false" in traceability_written

    @patch("worker.tasks.granola.notion_client")
    def test_dry_run_does_not_write_to_notion(self, mock_nc):
        _mock_db(mock_nc, existing_pages=[])
        _mock_read_page_full_snapshot(mock_nc, _FULL_CONTENT, page_id="page-new")

        result = handle_granola_process_transcript(
            {
                "title": "Reunión X",
                "content": _FULL_CONTENT,
                "date": "2026-04-01",
                "granola_document_id": "doc-x",
                "source_updated_at": "2026-04-01T08:00:00Z",
                "notify_enlace": False,
                "dry_run": True,
                "stability_window_seconds": 0,
            }
        )

        assert result["dry_run"] is True
        assert result["reconciliation_action"] == "create"
        mock_nc.create_database_page.assert_not_called()
        mock_nc.update_page_properties.assert_not_called()
        mock_nc.replace_blocks_in_page.assert_not_called()
        mock_nc.add_comment.assert_not_called()

    @patch("worker.tasks.granola.notion_client")
    def test_identical_hash_is_noop_no_duplicate(self, mock_nc):
        metrics = compute_transcript_metrics(_FULL_CONTENT)
        traceability = (
            "granola_document_id=doc-same\n"
            "source_updated_at=2026-04-01T12:00:00Z\n"
            f"content_hash={metrics.content_hash}\n"
            f"char_count={metrics.char_count}\n"
            f"segment_count={metrics.segment_count}\n"
            "truncation_detected=false\n"
            "ingest_path=granola.process_transcript"
        )
        existing_page = _existing_page(
            page_id="page-same",
            title="Reunión estable",
            date="2026-04-01",
            granola_document_id="doc-same",
            traceability_text=traceability,
            source_updated_at="2026-04-01T12:00:00Z",
        )
        _mock_db(mock_nc, existing_pages=[existing_page])
        _mock_read_page_full_snapshot(mock_nc, _FULL_CONTENT, page_id="page-same")

        result = handle_granola_process_transcript(
            {
                "title": "Reunión estable",
                "content": _FULL_CONTENT,
                "date": "2026-04-01",
                "granola_document_id": "doc-same",
                "source_updated_at": "2026-04-01T12:00:00Z",
                "notify_enlace": False,
                "stability_window_seconds": 0,
            }
        )

        assert result["reconciliation_action"] == "noop"
        assert result["noop"] is True
        assert result["page_id"] == "page-same"
        mock_nc.create_database_page.assert_not_called()
        mock_nc.update_page_properties.assert_not_called()
        mock_nc.replace_blocks_in_page.assert_not_called()

    @patch("worker.tasks.granola.notion_client")
    def test_repeated_title_with_different_document_id_creates_new_page(self, mock_nc):
        existing_page = _existing_page(
            page_id="page-a",
            title="Comgrap Dynamo",
            date="2026-04-01",
            granola_document_id="doc-a",
            traceability_text=(
                "granola_document_id=doc-a\n"
                "source_updated_at=2026-04-01T11:00:00Z\n"
                "ingest_path=granola.process_transcript"
            ),
            source_updated_at="2026-04-01T11:00:00Z",
        )
        _mock_db(mock_nc, existing_pages=[existing_page])
        _mock_read_page_full_snapshot(mock_nc, _FULL_CONTENT, page_id="page-new")
        mock_nc.create_database_page.return_value = {
            "page_id": "page-new",
            "url": "https://notion.so/page-new",
            "created": True,
        }

        result = handle_granola_process_transcript(
            {
                "title": "Comgrap Dynamo",
                "content": _FULL_CONTENT,
                # Different date so title-date collision logic picks create.
                "date": "2026-04-15",
                "granola_document_id": "doc-b",
                "source_updated_at": "2026-04-15T09:00:00Z",
                "notify_enlace": False,
                "stability_window_seconds": 0,
            }
        )

        assert result["matched_existing"] is False
        assert result["reconciliation_action"] == "create"
        mock_nc.create_database_page.assert_called_once()
        # Title should be disambiguated via the canonical family suffix.
        create_args = mock_nc.create_database_page.call_args
        resolved_title = create_args.kwargs["properties"]["Título"]["title"][0][
            "text"
        ]["content"]
        assert resolved_title.startswith("Comgrap Dynamo")
        assert resolved_title != "Comgrap Dynamo" or result["page_id"] == "page-new"

    @patch("worker.tasks.granola.notion_client")
    def test_same_title_and_date_with_different_doc_id_does_not_update_existing(
        self, mock_nc
    ):
        """Blocker fix: the title/date fallback must NOT match a page whose
        granola_document_id is non-empty and different from the incoming one.

        Scenario:
            existing: title="Comgrap Dynamo", date="2026-04-20", doc_id="doc-a"
            incoming: title="Comgrap Dynamo", date="2026-04-20", doc_id="doc-b"

        Expected: a new raw page is created; the page bound to doc-a is left
        untouched. Otherwise two independent Granola meetings would collapse
        into the same raw row.
        """
        existing_page = _existing_page(
            page_id="page-a",
            title="Comgrap Dynamo",
            date="2026-04-20",
            granola_document_id="doc-a",
            traceability_text=(
                "granola_document_id=doc-a\n"
                "source_updated_at=2026-04-20T09:00:00Z\n"
                "ingest_path=granola.process_transcript"
            ),
            source_updated_at="2026-04-20T09:00:00Z",
        )
        _mock_db(mock_nc, existing_pages=[existing_page])
        _mock_read_page_full_snapshot(mock_nc, _FULL_CONTENT, page_id="page-b")
        mock_nc.create_database_page.return_value = {
            "page_id": "page-b",
            "url": "https://notion.so/page-b",
            "created": True,
        }

        result = handle_granola_process_transcript(
            {
                "title": "Comgrap Dynamo",
                "content": _FULL_CONTENT,
                "date": "2026-04-20",
                "granola_document_id": "doc-b",
                "source_updated_at": "2026-04-20T15:00:00Z",
                "notify_enlace": False,
                "stability_window_seconds": 0,
            }
        )

        assert result["matched_existing"] is False
        assert result["match_strategy"] == ""
        assert result["reconciliation_action"] == "create"
        mock_nc.create_database_page.assert_called_once()
        mock_nc.update_page_properties.assert_not_called()
        mock_nc.replace_blocks_in_page.assert_not_called()
        # Ensure we did not accidentally rewrite page-a.
        update_calls = [
            call
            for call in mock_nc.method_calls
            if call[0] in {"update_page_properties", "replace_blocks_in_page"}
            and call.args
            and call.args[0] == "page-a"
        ]
        assert update_calls == []

    @patch("worker.tasks.granola.notion_client")
    def test_legacy_page_without_document_id_can_still_match_by_title_date(
        self, mock_nc
    ):
        """Control test: the title/date fallback must keep working against
        legacy rows that have no granola_document_id stored yet, so those can
        be reconciled/backfilled rather than duplicated.
        """
        existing_page = _existing_page(
            page_id="page-legacy",
            title="Comgrap Dynamo",
            date="2026-04-20",
            granola_document_id="",
            traceability_text=(
                "source_updated_at=2026-04-20T09:00:00Z\n"
                "ingest_path=granola.process_transcript"
            ),
            source_updated_at="2026-04-20T09:00:00Z",
        )
        _mock_db(mock_nc, existing_pages=[existing_page])
        _mock_read_page_full_snapshot(
            mock_nc, _FULL_CONTENT, page_id="page-legacy"
        )

        result = handle_granola_process_transcript(
            {
                "title": "Comgrap Dynamo",
                "content": _FULL_CONTENT,
                "date": "2026-04-20",
                "granola_document_id": "doc-b",
                "source_updated_at": "2026-04-20T15:00:00Z",
                "notify_enlace": False,
                "stability_window_seconds": 0,
            }
        )

        assert result["matched_existing"] is True
        assert result["page_id"] == "page-legacy"
        assert result["match_strategy"] in {
            "exact_title_date",
            "normalized_title_date",
        }
        mock_nc.create_database_page.assert_not_called()
        mock_nc.update_page_properties.assert_called_once()

    @patch("worker.tasks.granola.notion_client")
    def test_stability_window_defers_fresh_documents(self, mock_nc):
        _mock_db(mock_nc, existing_pages=[])
        _mock_read_page_full_snapshot(mock_nc, _FULL_CONTENT, page_id="page-new")

        # Use a timestamp that is "now" relative to the default window — we pin
        # the window to 1 hour and hand the handler a source_updated_at that is
        # obviously recent enough to fall inside it.
        recent = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        result = handle_granola_process_transcript(
            {
                "title": "Reunión fresca",
                "content": _FULL_CONTENT,
                "date": "2026-04-01",
                "granola_document_id": "doc-fresh",
                "source_updated_at": recent,
                "stability_window_seconds": 3600,
                "notify_enlace": False,
            }
        )

        assert result["reconciliation_action"] == "defer"
        assert result["deferred"] is True
        mock_nc.create_database_page.assert_not_called()
        mock_nc.update_page_properties.assert_not_called()


# ---------------------------------------------------------------------------
# _build_existing_raw_candidate reads the new metrics from traceability
# ---------------------------------------------------------------------------


class TestExistingRawCandidateParsesFinalityFields:
    def test_traceability_metrics_are_surfaced(self):
        traceability = (
            "granola_document_id=doc-xyz\n"
            "source_updated_at=2026-04-01T11:00:00Z\n"
            "content_hash=abc123\n"
            "char_count=1234\n"
            "segment_count=17\n"
            "truncation_detected=true\n"
            "ingested_at=2026-04-01T11:05:00Z\n"
            "reconciled_at=2026-04-02T09:00:00Z\n"
            "ingest_path=granola.process_transcript"
        )
        page_data = _existing_page(
            page_id="p1",
            title="Reunión",
            date="2026-04-01",
            granola_document_id="doc-xyz",
            traceability_text=traceability,
            source_updated_at="2026-04-01T11:00:00Z",
        )
        candidate = _build_existing_raw_candidate(page_data)
        assert candidate["content_hash"] == "abc123"
        assert candidate["char_count"] == 1234
        assert candidate["segment_count"] == 17
        assert candidate["truncation_detected"] is True
        assert candidate["ingested_at"] == "2026-04-01T11:05:00Z"
        assert candidate["reconciled_at"] == "2026-04-02T09:00:00Z"


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
