"""
Tests for Granola pipeline: handlers + watcher parser.
"""

import os
from datetime import datetime
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Watcher parser tests (no Worker dependency)
# ---------------------------------------------------------------------------

from scripts.vm.granola_watcher import parse_granola_markdown


class TestParseGranolaMarkdown:

    def test_full_format(self):
        md = """# Reunión con Cliente X

**Date:** 2026-03-04
**Attendees:** David, Cliente X, Partner Y

## Notes

Se revisó el avance del proyecto BIM.
Se acordó enviar propuesta la próxima semana.

## Transcript

David: Buenos días, gracias por venir.
Cliente X: Gracias, veamos el avance.

## Action Items

- [ ] Enviar propuesta a Cliente X (David, 2026-03-07)
- [ ] Revisar presupuesto (Partner Y, 2026-03-10)
- [ ] Agendar siguiente reunión (David)
"""
        result = parse_granola_markdown(md, "test.md")

        assert result["title"] == "Reunión con Cliente X"
        assert result["date"] == "2026-03-04"
        assert result["attendees"] == ["David", "Cliente X", "Partner Y"]
        assert len(result["action_items"]) == 3
        assert result["action_items"][0]["text"] == "Enviar propuesta a Cliente X"
        assert result["action_items"][0]["assignee"] == "David"
        assert result["action_items"][0]["due"] == "2026-03-07"
        assert result["action_items"][2]["assignee"] == "David"
        assert result["action_items"][2]["due"] == ""
        assert result["source"] == "granola"
        assert "Se revisó el avance" in result["content"]
        assert "Buenos días" in result["content"]

    def test_minimal_format(self):
        md = "Just some meeting notes without any structure."
        result = parse_granola_markdown(md, "quick-note.md")

        assert result["title"] == "quick-note"
        assert result["content"] == "Just some meeting notes without any structure."
        assert result["attendees"] == []
        assert result["action_items"] == []

    def test_spanish_metadata(self):
        md = """# Junta de equipo

**Fecha:** 2026-03-04
**Participantes:** Ana, Carlos

## Notas

Se discutieron temas varios.
"""
        result = parse_granola_markdown(md, "junta.md")

        assert result["title"] == "Junta de equipo"
        assert result["date"] == "2026-03-04"
        assert result["attendees"] == ["Ana", "Carlos"]
        assert "Se discutieron temas varios" in result["content"]

    def test_action_items_without_dates(self):
        md = """# Planning

## Action Items

- [ ] Research competitors
- [ ] Update roadmap
"""
        result = parse_granola_markdown(md, "planning.md")

        assert len(result["action_items"]) == 2
        assert result["action_items"][0]["text"] == "Research competitors"
        assert result["action_items"][0]["assignee"] == ""
        assert result["action_items"][0]["due"] == ""

    def test_empty_content_fallback(self):
        md = ""
        result = parse_granola_markdown(md, "empty.md")

        assert result["title"] == "empty"
        assert result["content"] == "(sin contenido)"

    def test_title_from_filename(self):
        md = "Some content without a heading."
        result = parse_granola_markdown(md, "2026-03-04-client-meeting.md")

        assert result["title"] == "2026-03-04-client-meeting"

    def test_shared_folder_export_format_is_preserved_exactly(self):
        md = (
            "Meeting Title: Konstruedu\n"
            "Date: Mar 30\n"
            "Meeting participants: David, Konstruedu\n"
            "\n"
            "Transcript:\n"
            " \n"
            "Me: Revisemos el piloto.  \n"
            "Them: Perfecto, partamos por el alcance.  \n"
        )

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 4, 1)

        with patch("scripts.vm.granola_watcher.datetime", FixedDateTime):
            result = parse_granola_markdown(md, "konstruedu.md")

        assert result["title"] == "Konstruedu"
        assert result["date"] == "2026-03-30"
        assert result["attendees"] == ["David", "Konstruedu"]
        assert result["content"] == md.strip()
        assert result["action_items"] == []


# ---------------------------------------------------------------------------
# Handler tests
# ---------------------------------------------------------------------------

os.environ.setdefault("WORKER_TOKEN", "test-token-12345")

from worker.tasks.granola import (  # noqa: E402
    _build_action_item_task_id,
    _build_traceability_block,
    _extract_action_items_from_content,
    handle_granola_capitalize_raw,
    handle_granola_create_followup,
    handle_granola_process_transcript,
)


class TestExtractActionItems:

    def test_extracts_from_section(self):
        content = """## Notes

Meeting went well.

## Action Items

- [ ] Send proposal (David, 2026-03-07)
- [ ] Review budget (Ana)
- [x] Already done item

## Other Section

Unrelated text.
"""
        items = _extract_action_items_from_content(content)
        assert len(items) == 3
        assert items[0]["text"] == "Send proposal"
        assert items[0]["assignee"] == "David"
        assert items[0]["due"] == "2026-03-07"
        assert items[1]["text"] == "Review budget"
        assert items[1]["assignee"] == "Ana"

    def test_no_action_items_section(self):
        content = "Just regular notes without action items."
        items = _extract_action_items_from_content(content)
        assert items == []

    def test_spanish_section_header(self):
        content = """## Compromisos

- [ ] Enviar cotización (David, 2026-03-10)
"""
        items = _extract_action_items_from_content(content)
        assert len(items) == 1
        assert items[0]["text"] == "Enviar cotización"


class TestHandleGranolaProcessTranscript:

    @patch("worker.tasks.granola.notion_client")
    def test_success(self, mock_nc):
        mock_nc.create_transcript_page.return_value = {
            "page_id": "page-123",
            "url": "https://notion.so/page-123",
        }
        mock_nc.add_comment.return_value = {"comment_id": "c-1"}

        result = handle_granola_process_transcript(
            {
                "title": "Reunión con Cliente",
                "content": "## Notes\n\nDiscusión de proyecto.\n\n## Action Items\n\n- [ ] Enviar propuesta (David, 2026-03-07)",
                "date": "2026-03-04",
                "attendees": ["David", "Cliente X"],
                "source": "granola",
            }
        )

        assert result["page_id"] == "page-123"
        assert result["url"] == "https://notion.so/page-123"
        assert result["action_items_detected"] == 1
        assert result["action_items_created"] == 0
        assert result["notification_sent"] is True

        mock_nc.create_transcript_page.assert_called_once_with(
            title="Reunión con Cliente",
            content="## Notes\n\nDiscusión de proyecto.\n\n## Action Items\n\n- [ ] Enviar propuesta (David, 2026-03-07)",
            source="granola",
            date="2026-03-04",
        )
        mock_nc.add_comment.assert_called_once()
        assert mock_nc.add_comment.call_args.kwargs["page_id"] is None
        assert "Hola @Enlace" in mock_nc.add_comment.call_args.kwargs["text"]

    @patch("worker.tasks.granola.notion_client")
    def test_with_pre_parsed_action_items(self, mock_nc):
        mock_nc.create_transcript_page.return_value = {"page_id": "p1", "url": ""}
        mock_nc.add_comment.return_value = {"comment_id": "c1"}

        result = handle_granola_process_transcript(
            {
                "title": "Meeting",
                "content": "Content",
                "action_items": [
                    {"text": "Task 1", "assignee": "David", "due": "2026-03-10"},
                    {"text": "Task 2", "assignee": "Ana", "due": ""},
                ],
            }
        )

        assert result["action_items_detected"] == 2
        assert result["action_items_created"] == 0

    @patch("worker.tasks.granola.notion_client")
    def test_no_enlace_notification(self, mock_nc):
        mock_nc.create_transcript_page.return_value = {"page_id": "p1", "url": ""}

        result = handle_granola_process_transcript(
            {
                "title": "Quick note",
                "content": "Just notes",
                "notify_enlace": False,
            }
        )

        assert result["notification_sent"] is False
        mock_nc.add_comment.assert_not_called()

    def test_missing_title(self):
        with pytest.raises(ValueError, match="'title' is required"):
            handle_granola_process_transcript({"content": "text"})

    def test_missing_content(self):
        with pytest.raises(ValueError, match="'content' is required"):
            handle_granola_process_transcript({"title": "Test"})


class TestHandleGranolaCapitalizeRaw:

    @patch("worker.tasks.granola.config.GRANOLA_CAPITALIZATION_MODE", "raw_direct_v2")
    @patch("worker.tasks.granola.handle_notion_upsert_task")
    @patch("worker.tasks.granola.notion_client")
    def test_task_dispatch_updates_raw_and_traceability(self, mock_nc, mock_upsert_task):
        mock_nc.get_page_snapshot.return_value = {
            "page_id": "raw-123",
            "url": "https://notion.so/raw-123",
            "title": "Reunión A",
            "properties": {
                "Fecha": "2026-04-03",
                "Log del agente": "ingest ok",
            },
            "plain_text": "Transcript completo",
        }
        mock_upsert_task.return_value = {
            "ok": True,
            "page_id": "task-123",
            "url": "https://notion.so/task-123",
            "created": True,
        }

        result = handle_granola_capitalize_raw(
            {
                "raw_page_id": "raw-123",
                "target_kind": "task",
                "target_name": "Llamar a cliente",
                "project_name": "Proyecto X",
                "summary": "Resumen corto",
                "notes": "Notas de soporte",
                "next_action": "Llamar mañana",
            }
        )

        assert result["ok"] is True
        assert result["url"] == "https://notion.so/task-123"
        task_payload = mock_upsert_task.call_args.args[0]
        assert task_payload["task_name"] == "Llamar a cliente"
        assert task_payload["project_name"] == "Proyecto X"
        assert task_payload["source"] == "granola.capitalize_raw"
        assert mock_nc.update_page_properties.call_count == 2
        final_properties = mock_nc.update_page_properties.call_args_list[-1].kwargs["properties"]
        assert final_properties["Estado agente"]["select"]["name"] == "Procesada"
        assert final_properties["Accion agente"]["select"]["name"] == "Listo para promocion"
        assert final_properties["Destino canonico"]["select"]["name"] == "Tarea"
        assert final_properties["URL artefacto"]["url"] == "https://notion.so/task-123"
        traceability = final_properties["Trazabilidad"]["rich_text"][0]["text"]["content"]
        assert "capitalization_mode=raw_direct_v2" in traceability
        assert "canonical_target_type=task" in traceability

    @patch("worker.tasks.granola.config.GRANOLA_CAPITALIZATION_MODE", "legacy_session")
    @patch("worker.tasks.granola.notion_client")
    def test_requires_raw_direct_mode_for_live_write(self, mock_nc):
        mock_nc.get_page_snapshot.return_value = {
            "page_id": "raw-legacy",
            "url": "https://notion.so/raw-legacy",
            "title": "Legacy raw",
            "properties": {"Fecha": "2026-04-03"},
            "plain_text": "Transcript completo",
        }

        result = handle_granola_capitalize_raw(
            {
                "raw_page_id": "raw-legacy",
                "target_kind": "task",
                "target_name": "Task en legacy",
            }
        )

        assert result["ok"] is False
        assert result["skipped"] is True
        mock_nc.update_page_properties.assert_not_called()

    @patch("worker.tasks.granola.config.GRANOLA_CAPITALIZATION_MODE", "raw_direct_v2")
    @patch("worker.tasks.granola.notion_client")
    def test_unsupported_target_marks_review_required(self, mock_nc):
        mock_nc.get_page_snapshot.return_value = {
            "page_id": "raw-unsupported",
            "url": "https://notion.so/raw-unsupported",
            "title": "Sesion ambigua",
            "properties": {"Fecha": "2026-04-03", "Log del agente": ""},
            "plain_text": "Transcript completo",
        }

        result = handle_granola_capitalize_raw(
            {
                "raw_page_id": "raw-unsupported",
                "target_kind": "program",
                "target_name": "Programa IA",
            }
        )

        assert result["ok"] is False
        assert result["blocked"] is True
        properties = mock_nc.update_page_properties.call_args.kwargs["properties"]
        assert properties["Estado agente"]["select"]["name"] == "Revision requerida"
        assert properties["Accion agente"]["select"]["name"] == "Bloqueado por ambiguedad"
        assert properties["Destino canonico"]["select"]["name"] == "Programa"

    @patch("worker.tasks.granola.config.GRANOLA_CAPITALIZATION_MODE", "raw_direct_v2")
    @patch("worker.tasks.granola.notion_client")
    def test_dry_run_returns_payload_without_writing(self, mock_nc):
        mock_nc.get_page_snapshot.return_value = {
            "page_id": "raw-dry",
            "url": "https://notion.so/raw-dry",
            "title": "Sesion dry",
            "properties": {"Fecha": "2026-04-03"},
            "plain_text": "Transcript completo",
        }

        result = handle_granola_capitalize_raw(
            {
                "raw_page_id": "raw-dry",
                "target_kind": "deliverable",
                "target_name": "Reporte final",
                "project_name": "Proyecto X",
                "dry_run": True,
            }
        )

        assert result["ok"] is True
        assert result["dry_run"] is True
        assert result["handler"] == "notion.upsert_deliverable"
        assert result["handler_payload"]["project_name"] == "Proyecto X"
        assert "capitalization_mode=raw_direct_v2" in result["traceability"]
        mock_nc.update_page_properties.assert_not_called()


class TestHandleGranolaCreateFollowup:

    @patch("worker.tasks.granola.notion_client")
    def test_reminder(self, mock_nc):
        mock_nc.upsert_task.return_value = {"page_id": "t-1", "created": True}

        result = handle_granola_create_followup(
            {
                "transcript_page_id": "page-123",
                "followup_type": "reminder",
                "title": "Client Meeting",
                "date": "2026-03-04",
                "due_date": "2026-03-11",
            }
        )

        assert result["followup_type"] == "reminder"
        assert result["result"]["due_date"] == "2026-03-11"
        mock_nc.upsert_task.assert_called_once()
        call_kwargs = mock_nc.upsert_task.call_args.kwargs
        assert "Client Meeting" in call_kwargs["task"]

    @patch("worker.tasks.granola.notion_client")
    def test_email_draft(self, mock_nc):
        mock_nc.add_comment.return_value = {"comment_id": "c-1"}

        result = handle_granola_create_followup(
            {
                "transcript_page_id": "page-123",
                "followup_type": "email_draft",
                "title": "Sprint Review",
                "date": "2026-03-04",
                "action_items": [{"text": "Deploy v2", "assignee": "DevOps", "due": "2026-03-06"}],
            }
        )

        assert result["followup_type"] == "email_draft"
        assert "Sprint Review" in result["result"]["draft"]
        assert "Deploy v2" in result["result"]["draft"]
        assert result["result"]["posted_to_notion"] is True

    @patch("worker.tasks.granola.notion_client")
    def test_proposal(self, mock_nc):
        mock_nc.create_report_page.return_value = {
            "page_id": "report-1",
            "page_url": "https://notion.so/report-1",
            "ok": True,
        }

        result = handle_granola_create_followup(
            {
                "transcript_page_id": "page-123",
                "followup_type": "proposal",
                "title": "Kickoff",
                "date": "2026-03-04",
                "attendees": ["David", "Client"],
                "action_items": [{"text": "Start phase 1", "assignee": "David", "due": "2026-03-15"}],
            }
        )

        assert result["followup_type"] == "proposal"
        assert result["result"]["ok"] is True
        mock_nc.create_report_page.assert_called_once()

    def test_missing_page_id(self):
        with pytest.raises(ValueError, match="'transcript_page_id' is required"):
            handle_granola_create_followup({"followup_type": "reminder"})

    def test_invalid_followup_type(self):
        with pytest.raises(ValueError, match="'followup_type' must be one of"):
            handle_granola_create_followup(
                {
                    "transcript_page_id": "p-1",
                    "followup_type": "invalid",
                }
            )

    @patch("worker.tasks.granola.notion_client")
    def test_reminder_default_due_date(self, mock_nc):
        mock_nc.upsert_task.return_value = {"page_id": "t-1", "created": True}

        result = handle_granola_create_followup(
            {
                "transcript_page_id": "page-123",
                "followup_type": "reminder",
                "title": "Meeting",
            }
        )

        assert result["result"]["due_date"]
        assert len(result["result"]["due_date"]) == 10


def test_build_action_item_task_id_is_stable():
    item = {"text": "Verify watcher works", "assignee": "Test User", "due": "2026-03-22"}

    task_id_1 = _build_action_item_task_id("Smoke Test Meeting", "2026-03-22", item)
    task_id_2 = _build_action_item_task_id("Smoke Test Meeting", "2026-03-22", dict(item))

    assert task_id_1 == task_id_2
    assert task_id_1.startswith("granola-action-item-")


def test_build_traceability_block_has_expected_shape():
    traceability = _build_traceability_block("raw-123", "task", "https://notion.so/task-123")

    assert "source=granola" in traceability
    assert "capitalization_mode=raw_direct_v2" in traceability
    assert "raw_page_id=raw-123" in traceability
    assert "canonical_target_type=task" in traceability
    assert "canonical_target_url=https://notion.so/task-123" in traceability
    assert "runtime_actor=granola.capitalize_raw" in traceability
    assert "processed_at=" in traceability


# ---------------------------------------------------------------------------
# Watcher integration tests
# ---------------------------------------------------------------------------


class TestWatcherProcessFile:

    @patch("scripts.vm.granola_watcher.send_to_worker")
    def test_process_file(self, mock_send, tmp_path):
        from scripts.vm.granola_watcher import process_file

        md_file = tmp_path / "meeting.md"
        md_file.write_text("# Test Meeting\n\n**Date:** 2026-03-04\n\nSome notes here.", encoding="utf-8")

        processed_dir = tmp_path / "processed"
        mock_send.return_value = {"status": "ok"}

        result = process_file(md_file, "http://localhost:8088", "test-token", processed_dir)

        assert result is True
        assert not md_file.exists()
        assert (processed_dir / "meeting.md").exists()
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[0][2] == "granola.process_transcript"
        parsed = call_args[0][3]
        assert parsed["title"] == "Test Meeting"

    @patch("scripts.vm.granola_watcher.send_to_worker")
    def test_skip_short_file(self, mock_send, tmp_path):
        from scripts.vm.granola_watcher import process_file

        md_file = tmp_path / "tiny.md"
        md_file.write_text("hi", encoding="utf-8")

        result = process_file(md_file, "http://localhost:8088", "test-token", tmp_path / "processed")

        assert result is False
        mock_send.assert_not_called()

    @patch("scripts.vm.granola_watcher.send_to_worker")
    def test_scan_and_process(self, mock_send, tmp_path):
        from scripts.vm.granola_watcher import scan_and_process

        for i in range(3):
            (tmp_path / f"meeting_{i}.md").write_text(
                f"# Meeting {i}\n\nSome notes for meeting {i}.", encoding="utf-8"
            )
        (tmp_path / ".hidden.md").write_text("# Hidden\n\nShould be skipped.", encoding="utf-8")

        processed_dir = tmp_path / "processed"
        mock_send.return_value = {"status": "ok"}

        count = scan_and_process(tmp_path, "http://localhost:8088", "test-token", processed_dir)

        assert count == 3
        assert mock_send.call_count == 3

    @patch("scripts.vm.granola_watcher.send_to_worker")
    def test_process_file_shared_folder_export_preserves_exact_content(self, mock_send, tmp_path):
        from scripts.vm.granola_watcher import process_file

        md_file = tmp_path / "shared-export.md"
        md_file.write_text(
            "Meeting Title: ACI Autodesk\n"
            "Date: Mar 17\n"
            "Meeting participants: David, Autodesk\n"
            "\n"
            "Transcript:\n"
            " \n"
            "Me: Hola.  \n"
            "Them: Buenas.  \n",
            encoding="utf-8",
        )

        processed_dir = tmp_path / "processed"
        mock_send.return_value = {"status": "ok"}

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 4, 1)

        with patch("scripts.vm.granola_watcher.datetime", FixedDateTime):
            result = process_file(md_file, "http://localhost:8088", "test-token", processed_dir)

        assert result is True
        parsed = mock_send.call_args[0][3]
        assert parsed["title"] == "ACI Autodesk"
        assert parsed["date"] == "2026-03-17"
        assert parsed["content"].startswith("Meeting Title: ACI Autodesk")
        assert parsed["content"].endswith("Them: Buenas.")
