"""Tests for granola.process_transcript and granola.create_followup handlers."""

import os
import uuid
from unittest.mock import MagicMock, patch, call

import pytest

os.environ.setdefault("WORKER_TOKEN", "test")

from worker.tasks.granola import (
    handle_granola_process_transcript,
    handle_granola_create_followup,
    _extract_action_items,
)


# ---------------------------------------------------------------------------
# _extract_action_items
# ---------------------------------------------------------------------------

class TestExtractActionItems:
    def test_extracts_from_action_heading(self):
        md = (
            "# Meeting\n"
            "Discussion...\n"
            "## Action Items\n"
            "- Send proposal\n"
            "- Review contract\n"
            "## Next\n"
            "- Unrelated\n"
        )
        items = _extract_action_items(md)
        assert items == ["Send proposal", "Review contract"]

    def test_extracts_from_spanish_heading(self):
        md = (
            "# Reunión\n"
            "### Compromisos\n"
            "- Enviar propuesta\n"
            "- Revisar contrato\n"
        )
        items = _extract_action_items(md)
        assert items == ["Enviar propuesta", "Revisar contrato"]

    def test_extracts_checkboxes(self):
        md = (
            "# Meeting\n"
            "- [ ] Open task\n"
            "- [x] Done task\n"
            "Regular line\n"
        )
        items = _extract_action_items(md)
        assert items == ["Open task", "Done task"]

    def test_empty_content(self):
        assert _extract_action_items("") == []
        assert _extract_action_items("Just a paragraph.") == []

    def test_todo_heading(self):
        md = "## To-Do\n- Item A\n- Item B\n"
        items = _extract_action_items(md)
        assert items == ["Item A", "Item B"]

    def test_pendientes_heading(self):
        md = "### Pendientes\n* Tarea uno\n* Tarea dos\n"
        items = _extract_action_items(md)
        assert items == ["Tarea uno", "Tarea dos"]


# ---------------------------------------------------------------------------
# granola.process_transcript
# ---------------------------------------------------------------------------

class TestHandleGranolaProcessTranscript:
    @patch("worker.tasks.granola.notion_client")
    def test_success_full_pipeline(self, mock_nc):
        mock_nc.create_transcript_page.return_value = {
            "page_id": "page-123",
            "url": "https://notion.so/page-123",
        }
        mock_nc.add_comment.return_value = {"comment_id": "comm-456"}
        mock_nc.upsert_task.return_value = {"page_id": "task-789", "created": True}

        result = handle_granola_process_transcript({
            "title": "Reunión ABC",
            "content": "# Reunión ABC\n\n## Action Items\n- Enviar propuesta\n- Revisar planos\n",
            "date": "2026-03-04",
            "attendees": ["David", "Juan"],
        })

        assert result["page_id"] == "page-123"
        assert result["url"] == "https://notion.so/page-123"
        assert result["comment_id"] == "comm-456"
        assert result["action_items_created"] == 2
        assert result["action_items_total"] == 2

        mock_nc.create_transcript_page.assert_called_once()
        call_kwargs = mock_nc.create_transcript_page.call_args
        assert call_kwargs.kwargs["title"] == "Reunión ABC"
        assert call_kwargs.kwargs["source"] == "granola"
        assert "David" in call_kwargs.kwargs["content"]

        mock_nc.add_comment.assert_called_once_with(
            page_id="page-123",
            text="Transcripción lista para optimizar — procesada automáticamente por Granola Pipeline.",
        )

        assert mock_nc.upsert_task.call_count == 2

    @patch("worker.tasks.granola.notion_client")
    def test_success_with_explicit_action_items(self, mock_nc):
        mock_nc.create_transcript_page.return_value = {
            "page_id": "p1", "url": "",
        }
        mock_nc.add_comment.return_value = {"comment_id": "c1"}
        mock_nc.upsert_task.return_value = {"page_id": "t1", "created": True}

        result = handle_granola_process_transcript({
            "title": "Test",
            "content": "Just content.",
            "action_items": ["Do X", "Do Y", "Do Z"],
        })

        assert result["action_items_total"] == 3
        assert result["action_items_created"] == 3

    @patch("worker.tasks.granola.notion_client")
    def test_no_action_items(self, mock_nc):
        mock_nc.create_transcript_page.return_value = {"page_id": "p1", "url": ""}
        mock_nc.add_comment.return_value = {"comment_id": "c1"}

        result = handle_granola_process_transcript({
            "title": "Simple meeting",
            "content": "Nothing actionable here.",
        })

        assert result["action_items_created"] == 0
        assert result["action_items_total"] == 0
        mock_nc.upsert_task.assert_not_called()

    @patch("worker.tasks.granola.notion_client")
    def test_comment_failure_does_not_break_pipeline(self, mock_nc):
        mock_nc.create_transcript_page.return_value = {"page_id": "p1", "url": ""}
        mock_nc.add_comment.side_effect = RuntimeError("Notion error")

        result = handle_granola_process_transcript({
            "title": "Test",
            "content": "Content.",
        })

        assert result["page_id"] == "p1"
        assert result["comment_id"] is None

    @patch("worker.tasks.granola.notion_client")
    def test_upsert_task_failure_does_not_break(self, mock_nc):
        mock_nc.create_transcript_page.return_value = {"page_id": "p1", "url": ""}
        mock_nc.add_comment.return_value = {"comment_id": "c1"}
        mock_nc.upsert_task.side_effect = RuntimeError("DB error")

        result = handle_granola_process_transcript({
            "title": "Test",
            "content": "## Action Items\n- Item\n",
        })

        assert result["action_items_created"] == 0
        assert result["action_items_total"] == 1

    def test_missing_title_raises(self):
        with pytest.raises(ValueError, match="'title' and 'content' are required"):
            handle_granola_process_transcript({"content": "x"})

    def test_missing_content_raises(self):
        with pytest.raises(ValueError, match="'title' and 'content' are required"):
            handle_granola_process_transcript({"title": "x"})

    @patch("worker.tasks.granola.notion_client")
    def test_default_date_when_not_provided(self, mock_nc):
        mock_nc.create_transcript_page.return_value = {"page_id": "p1", "url": ""}
        mock_nc.add_comment.return_value = {"comment_id": "c1"}

        handle_granola_process_transcript({
            "title": "Test",
            "content": "Content",
        })

        call_kwargs = mock_nc.create_transcript_page.call_args.kwargs
        assert len(call_kwargs["date"]) == 10  # YYYY-MM-DD


# ---------------------------------------------------------------------------
# granola.create_followup
# ---------------------------------------------------------------------------

class TestHandleGranolaCreateFollowup:
    @patch("worker.tasks.granola.notion_client")
    def test_reminder_success(self, mock_nc):
        mock_nc.upsert_task.return_value = {"page_id": "t-1", "created": True}

        result = handle_granola_create_followup({
            "transcript_page_id": "page-abc",
            "followup_type": "reminder",
            "title": "Enviar propuesta",
            "due_date": "2026-03-10",
            "assignee": "David",
        })

        assert result["ok"] is True
        assert result["followup_type"] == "reminder"
        mock_nc.upsert_task.assert_called_once()
        call_kwargs = mock_nc.upsert_task.call_args.kwargs
        assert call_kwargs["task"] == "Enviar propuesta"
        assert "David" in call_kwargs["input_summary"]

    @patch("worker.tasks.granola.notion_client")
    def test_email_draft_success(self, mock_nc):
        mock_nc.create_report_page.return_value = {
            "page_id": "rp-1", "page_url": "https://notion.so/rp-1", "ok": True,
        }

        result = handle_granola_create_followup({
            "transcript_page_id": "page-abc",
            "followup_type": "email_draft",
            "title": "Seguimiento reunión",
            "body": "Estimado Juan,\n\nGracias...",
            "assignee": "Juan",
        })

        assert result["ok"] is True
        assert result["followup_type"] == "email_draft"
        mock_nc.create_report_page.assert_called_once()
        call_kwargs = mock_nc.create_report_page.call_args.kwargs
        assert call_kwargs["parent_page_id"] == "page-abc"
        assert "Email Draft" in call_kwargs["title"]
        assert call_kwargs["metadata"]["type"] == "email_draft"

    @patch("worker.tasks.granola.notion_client")
    def test_proposal_success(self, mock_nc):
        mock_nc.create_report_page.return_value = {
            "page_id": "rp-2", "page_url": "https://notion.so/rp-2", "ok": True,
        }

        result = handle_granola_create_followup({
            "transcript_page_id": "page-xyz",
            "followup_type": "proposal",
            "title": "Propuesta BIM",
            "body": "# Alcance\n...",
        })

        assert result["ok"] is True
        assert result["followup_type"] == "proposal"
        call_kwargs = mock_nc.create_report_page.call_args.kwargs
        assert "Propuesta" in call_kwargs["title"]
        assert call_kwargs["metadata"]["type"] == "proposal"

    def test_missing_transcript_page_id(self):
        with pytest.raises(ValueError, match="'transcript_page_id' is required"):
            handle_granola_create_followup({
                "followup_type": "reminder",
                "title": "Test",
            })

    def test_invalid_followup_type(self):
        with pytest.raises(ValueError, match="'followup_type' must be one of"):
            handle_granola_create_followup({
                "transcript_page_id": "page-1",
                "followup_type": "invalid",
                "title": "Test",
            })

    def test_missing_title(self):
        with pytest.raises(ValueError, match="'title' is required"):
            handle_granola_create_followup({
                "transcript_page_id": "page-1",
                "followup_type": "reminder",
            })

    @patch("worker.tasks.granola.notion_client")
    def test_email_draft_without_body(self, mock_nc):
        mock_nc.create_report_page.return_value = {
            "page_id": "rp-3", "page_url": "", "ok": True,
        }

        result = handle_granola_create_followup({
            "transcript_page_id": "page-1",
            "followup_type": "email_draft",
            "title": "Follow up",
        })

        assert result["ok"] is True
        call_kwargs = mock_nc.create_report_page.call_args.kwargs
        assert len(call_kwargs["content_blocks"]) > 0


# ---------------------------------------------------------------------------
# Watcher parse_markdown (imported from scripts)
# ---------------------------------------------------------------------------

class TestWatcherParseMarkdown:
    """Test the parse_markdown function from granola_watcher.py."""

    @pytest.fixture(autouse=True)
    def _import_watcher(self):
        import importlib
        import sys
        spec = importlib.util.spec_from_file_location(
            "granola_watcher",
            os.path.join(os.path.dirname(__file__), "..", "scripts", "vm", "granola_watcher.py"),
        )
        self.watcher = importlib.util.module_from_spec(spec)
        sys.modules["granola_watcher"] = self.watcher
        spec.loader.exec_module(self.watcher)

    def test_parse_with_title_and_date(self):
        md = "# Weekly Standup\n\nDate: 2026-03-04\n\nDiscussion points..."
        result = self.watcher.parse_markdown(md, "2026-03-04-standup.md")
        assert result["title"] == "Weekly Standup"
        assert result["date"] == "2026-03-04"

    def test_parse_extracts_attendees(self):
        md = "# Meeting\n\nParticipantes: David, Juan, Ana\n\nAgenda..."
        result = self.watcher.parse_markdown(md, "meeting.md")
        assert result["attendees"] == ["David", "Juan", "Ana"]

    def test_parse_extracts_action_items(self):
        md = "# Reunion\n\n## Compromisos\n- Enviar doc\n- Revisar plan\n\n## Notas\nOtro...\n"
        result = self.watcher.parse_markdown(md, "reunion.md")
        assert result["action_items"] == ["Enviar doc", "Revisar plan"]

    def test_parse_title_from_filename(self):
        md = "No heading here, just text."
        result = self.watcher.parse_markdown(md, "2026-03-04-client-call.md")
        assert "client call" in result["title"].lower()
        assert result["date"] == "2026-03-04"

    def test_parse_checkbox_action_items(self):
        md = "# M\n- [ ] Open\n- [x] Done\n"
        result = self.watcher.parse_markdown(md, "test.md")
        assert "Open" in result["action_items"]
        assert "Done" in result["action_items"]

    def test_parse_empty_content(self):
        result = self.watcher.parse_markdown("", "empty.md")
        assert result["title"] == "empty"
        assert result["content"] == ""


# ---------------------------------------------------------------------------
# Integration: handlers registered in TASK_HANDLERS
# ---------------------------------------------------------------------------

class TestRegistration:
    def test_granola_handlers_registered(self):
        from worker.tasks import TASK_HANDLERS

        assert "granola.process_transcript" in TASK_HANDLERS
        assert "granola.create_followup" in TASK_HANDLERS
        assert callable(TASK_HANDLERS["granola.process_transcript"])
        assert callable(TASK_HANDLERS["granola.create_followup"])
