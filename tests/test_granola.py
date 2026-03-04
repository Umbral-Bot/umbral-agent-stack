"""
Tests for Granola pipeline: handlers + watcher parser.
"""

import os
import pytest
from unittest.mock import patch, MagicMock, call

os.environ.setdefault("WORKER_TOKEN", "test-token-12345")

from worker.tasks.granola import (
    handle_granola_process_transcript,
    handle_granola_create_followup,
    _extract_action_items,
)

# Also test the watcher's parser (it's a standalone script, import its function)
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "vm"))
from granola_watcher import parse_markdown_transcript


# ---------------------------------------------------------------------------
# Watcher parser tests
# ---------------------------------------------------------------------------

class TestParseMarkdownTranscript:
    SAMPLE_MD = """# Reunión con Cliente ABC

**Fecha:** 2026-03-04

## Participantes
- David
- María García
- Juan López

## Resumen

Se discutió la propuesta técnica para el proyecto BIM.
El cliente solicitó una demo para la próxima semana.

## Action Items
- [ ] Enviar cotización antes del viernes
- [ ] Agendar demo para el lunes
- [x] Revisar documento de alcance
"""

    def test_parse_title(self):
        result = parse_markdown_transcript(self.SAMPLE_MD)
        assert result["title"] == "Reunión con Cliente ABC"

    def test_parse_date(self):
        result = parse_markdown_transcript(self.SAMPLE_MD)
        assert result["date"] == "2026-03-04"

    def test_parse_attendees(self):
        result = parse_markdown_transcript(self.SAMPLE_MD)
        assert "David" in result["attendees"]
        assert "María García" in result["attendees"]
        assert "Juan López" in result["attendees"]
        assert len(result["attendees"]) == 3

    def test_parse_action_items(self):
        result = parse_markdown_transcript(self.SAMPLE_MD)
        assert len(result["action_items"]) == 3
        assert "Enviar cotización antes del viernes" in result["action_items"]
        assert "Agendar demo para el lunes" in result["action_items"]
        assert "Revisar documento de alcance" in result["action_items"]

    def test_parse_content_preserved(self):
        result = parse_markdown_transcript(self.SAMPLE_MD)
        assert "Se discutió la propuesta técnica" in result["content"]

    def test_parse_no_title_fallback(self):
        md = "Some random text without heading"
        result = parse_markdown_transcript(md)
        assert result["title"] == "Some random text without heading"

    def test_parse_no_date_defaults_today(self):
        md = "# Meeting\nNo date here"
        result = parse_markdown_transcript(md)
        assert len(result["date"]) == 10  # YYYY-MM-DD format

    def test_parse_empty_content(self):
        result = parse_markdown_transcript("")
        assert result["title"] == ""
        assert result["attendees"] == []
        assert result["action_items"] == []

    def test_parse_english_attendees(self):
        md = "# Meeting\n## Attendees\n- Alice\n- Bob\n\n## Notes\nSome notes."
        result = parse_markdown_transcript(md)
        assert result["attendees"] == ["Alice", "Bob"]

    def test_parse_compromisos_section(self):
        md = "# Reunión\n## Compromisos\n- Hacer X\n- Hacer Y\n\n## Otro"
        result = parse_markdown_transcript(md)
        assert len(result["action_items"]) == 2
        assert "Hacer X" in result["action_items"]

    def test_parse_next_steps_section(self):
        md = "# Meeting\n## Next Steps\n- Step 1\n- Step 2"
        result = parse_markdown_transcript(md)
        assert len(result["action_items"]) == 2

    def test_parse_checkbox_outside_section(self):
        md = "# Meeting\nSome text\n- [ ] Task anywhere\n- [ ] Another task"
        result = parse_markdown_transcript(md)
        assert len(result["action_items"]) == 2
        assert "Task anywhere" in result["action_items"]


# ---------------------------------------------------------------------------
# _extract_action_items (handler-side parser)
# ---------------------------------------------------------------------------

class TestExtractActionItems:
    def test_extract_checkbox_items(self):
        content = "# Meeting\n- [ ] Do this\n- [x] Done that\n- [ ] Also this"
        items = _extract_action_items(content)
        assert len(items) == 3
        assert "Do this" in items

    def test_extract_from_action_items_heading(self):
        content = "# Meeting\n## Action Items\n- First\n- Second\n\n## Other"
        items = _extract_action_items(content)
        assert len(items) == 2

    def test_extract_from_compromisos_heading(self):
        content = "# Reunión\n### Compromisos\n- Tarea 1\n- Tarea 2"
        items = _extract_action_items(content)
        assert len(items) == 2

    def test_extract_empty(self):
        content = "# Meeting\nJust some notes, no tasks."
        items = _extract_action_items(content)
        assert items == []

    def test_extract_proximos_pasos(self):
        content = "# R\n## Próximos Pasos\n- Paso 1\n- Paso 2\n\n## Fin"
        items = _extract_action_items(content)
        assert len(items) == 2


# ---------------------------------------------------------------------------
# handle_granola_process_transcript
# ---------------------------------------------------------------------------

class TestHandleProcessTranscript:
    @patch("worker.tasks.granola.notion_client")
    def test_success_full(self, mock_nc):
        mock_nc.create_transcript_page.return_value = {
            "page_id": "page-123",
            "url": "https://notion.so/page-123",
        }
        mock_nc.add_comment.return_value = {"comment_id": "comment-1"}
        mock_nc.upsert_task.return_value = {"page_id": "task-1", "created": True}

        result = handle_granola_process_transcript({
            "title": "Test Meeting",
            "content": "# Test\n\n- [ ] Action 1\n- [ ] Action 2",
            "date": "2026-03-04",
            "attendees": ["Alice", "Bob"],
            "action_items": ["Action 1", "Action 2"],
        })

        assert result["page_id"] == "page-123"
        assert result["page_url"] == "https://notion.so/page-123"
        assert result["tasks_created"] == 2
        assert result["action_items_found"] == 2
        assert result["comment_added"] is True

        mock_nc.create_transcript_page.assert_called_once()
        assert mock_nc.upsert_task.call_count == 2

    @patch("worker.tasks.granola.notion_client")
    def test_auto_extract_action_items(self, mock_nc):
        mock_nc.create_transcript_page.return_value = {
            "page_id": "page-456",
            "url": "https://notion.so/page-456",
        }
        mock_nc.add_comment.return_value = {"comment_id": "c1"}
        mock_nc.upsert_task.return_value = {"page_id": "t1", "created": True}

        result = handle_granola_process_transcript({
            "title": "Auto Extract",
            "content": "# Meeting\n\n- [ ] Do X\n- [ ] Do Y\n\nNotes here.",
        })

        assert result["action_items_found"] == 2
        assert result["tasks_created"] == 2

    @patch("worker.tasks.granola.notion_client")
    def test_no_action_items(self, mock_nc):
        mock_nc.create_transcript_page.return_value = {
            "page_id": "page-789",
            "url": "https://notion.so/page-789",
        }
        mock_nc.add_comment.return_value = {"comment_id": "c1"}

        result = handle_granola_process_transcript({
            "title": "Simple Meeting",
            "content": "# Meeting\nJust some notes.",
        })

        assert result["tasks_created"] == 0
        assert result["action_items_found"] == 0
        mock_nc.upsert_task.assert_not_called()

    def test_missing_title(self):
        with pytest.raises(ValueError, match="'title' and 'content' are required"):
            handle_granola_process_transcript({"content": "hello"})

    def test_missing_content(self):
        with pytest.raises(ValueError, match="'title' and 'content' are required"):
            handle_granola_process_transcript({"title": "hello"})

    @patch("worker.tasks.granola.notion_client")
    def test_comment_failure_does_not_break(self, mock_nc):
        mock_nc.create_transcript_page.return_value = {
            "page_id": "page-err",
            "url": "",
        }
        mock_nc.add_comment.side_effect = RuntimeError("Notion API error")

        result = handle_granola_process_transcript({
            "title": "Error Test",
            "content": "# Test\nContent",
        })

        assert result["page_id"] == "page-err"
        assert result["comment_added"] is False

    @patch("worker.tasks.granola.notion_client")
    def test_upsert_task_failure_partial(self, mock_nc):
        mock_nc.create_transcript_page.return_value = {"page_id": "p1", "url": ""}
        mock_nc.add_comment.return_value = {"comment_id": "c1"}
        mock_nc.upsert_task.side_effect = [
            {"page_id": "t1", "created": True},
            RuntimeError("Notion error"),
        ]

        result = handle_granola_process_transcript({
            "title": "Partial",
            "content": "# M\n- [ ] A\n- [ ] B",
            "action_items": ["A", "B"],
        })

        assert result["tasks_created"] == 1


# ---------------------------------------------------------------------------
# handle_granola_create_followup
# ---------------------------------------------------------------------------

class TestHandleCreateFollowup:
    @patch("worker.tasks.granola.notion_client")
    def test_reminder(self, mock_nc):
        mock_nc.upsert_task.return_value = {"page_id": "task-1", "created": True}
        mock_nc.add_comment.return_value = {"comment_id": "c1"}

        result = handle_granola_create_followup({
            "transcript_page_id": "tp-123",
            "followup_type": "reminder",
            "title": "Enviar propuesta",
            "due_date": "2026-03-07",
        })

        assert result["followup_type"] == "reminder"
        assert result["due_date"] == "2026-03-07"
        mock_nc.upsert_task.assert_called_once()

    @patch("worker.tasks.granola.notion_client")
    def test_proposal(self, mock_nc):
        mock_nc.create_report_page.return_value = {
            "page_id": "prop-1",
            "page_url": "https://notion.so/prop-1",
            "ok": True,
        }
        mock_nc.add_comment.return_value = {"comment_id": "c1"}

        result = handle_granola_create_followup({
            "transcript_page_id": "tp-456",
            "followup_type": "proposal",
            "title": "Propuesta BIM",
            "notes": "Incluir estimados",
        })

        assert result["followup_type"] == "proposal"
        assert result["result"]["page_id"] == "prop-1"
        mock_nc.create_report_page.assert_called_once()
        kwargs = mock_nc.create_report_page.call_args.kwargs
        assert "Propuesta: Propuesta BIM" in kwargs["title"]

    @patch("worker.tasks.granola.notion_client")
    def test_email_draft(self, mock_nc):
        mock_nc.create_report_page.return_value = {
            "page_id": "email-1",
            "page_url": "https://notion.so/email-1",
            "ok": True,
        }
        mock_nc.add_comment.return_value = {"comment_id": "c1"}

        result = handle_granola_create_followup({
            "transcript_page_id": "tp-789",
            "followup_type": "email_draft",
            "title": "Seguimiento reunión",
            "assignee": "María",
            "notes": "confirmar presupuesto",
        })

        assert result["followup_type"] == "email_draft"
        mock_nc.create_report_page.assert_called_once()
        kwargs = mock_nc.create_report_page.call_args.kwargs
        assert "email" in kwargs["title"].lower()

    def test_missing_transcript_page_id(self):
        with pytest.raises(ValueError, match="'transcript_page_id' is required"):
            handle_granola_create_followup({
                "followup_type": "reminder",
            })

    def test_invalid_followup_type(self):
        with pytest.raises(ValueError, match="'followup_type' must be one of"):
            handle_granola_create_followup({
                "transcript_page_id": "tp-1",
                "followup_type": "invalid",
            })

    @patch("worker.tasks.granola.notion_client")
    def test_reminder_default_due_date(self, mock_nc):
        mock_nc.upsert_task.return_value = {"page_id": "t1", "created": True}
        mock_nc.add_comment.return_value = {"comment_id": "c1"}

        result = handle_granola_create_followup({
            "transcript_page_id": "tp-1",
            "followup_type": "reminder",
            "title": "Test",
        })

        assert result["due_date"]  # should have a default date
        assert len(result["due_date"]) == 10


# ---------------------------------------------------------------------------
# Handler registration test
# ---------------------------------------------------------------------------

class TestHandlerRegistration:
    def test_granola_handlers_registered(self):
        from worker.tasks import TASK_HANDLERS
        assert "granola.process_transcript" in TASK_HANDLERS
        assert "granola.create_followup" in TASK_HANDLERS

    def test_handler_callable(self):
        from worker.tasks import TASK_HANDLERS
        assert callable(TASK_HANDLERS["granola.process_transcript"])
        assert callable(TASK_HANDLERS["granola.create_followup"])
