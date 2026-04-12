"""
Tests for Granola pipeline: handlers + watcher parser.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


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


# ---------------------------------------------------------------------------
# Handler tests
# ---------------------------------------------------------------------------

os.environ.setdefault("WORKER_TOKEN", "test-token-12345")

from worker.tasks.granola import (
    _build_action_item_task_id,
    handle_granola_process_transcript,
    handle_granola_capitalize_raw,
    handle_granola_create_human_task_from_curated_session,
    handle_granola_promote_operational_slice,
    handle_granola_update_commercial_project_from_curated_session,
    handle_granola_promote_curated_session,
    handle_granola_create_followup,
    _extract_action_items_from_content,
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

    @patch("worker.tasks.granola.handle_notion_upsert_task")
    @patch("worker.tasks.granola.notion_client")
    def test_success(self, mock_nc, mock_upsert_task):
        mock_nc.create_transcript_page.return_value = {
            "page_id": "page-123",
            "url": "https://notion.so/page-123",
        }
        mock_upsert_task.return_value = {"page_id": "task-1", "created": True}
        mock_nc.add_comment.return_value = {"comment_id": "c-1"}

        result = handle_granola_process_transcript({
            "title": "Reunión con Cliente",
            "content": "## Notes\n\nDiscusión de proyecto.\n\n## Action Items\n\n- [ ] Enviar propuesta (David, 2026-03-07)",
            "date": "2026-03-04",
            "attendees": ["David", "Cliente X"],
            "source": "granola",
        })

        assert result["page_id"] == "page-123"
        assert result["url"] == "https://notion.so/page-123"
        assert result["action_items_detected"] == 1
        assert result["action_items_created"] == 0
        assert result["legacy_raw_task_writes_enabled"] is False
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
        mock_upsert_task.assert_not_called()
        return
        mock_upsert_task.assert_called_once()
        task_payload = mock_upsert_task.call_args.args[0]
        assert task_payload["task"] == "granola.action_item"
        assert task_payload["task_name"] == "[Granola] Enviar propuesta"
        assert task_payload["project_name"] == "Proyecto Granola"
        assert task_payload["source"] == "granola_process_transcript"
        assert task_payload["source_kind"] == "action_item"
        assert task_payload["task_id"] == _build_action_item_task_id(
            "Reunión con Cliente",
            "2026-03-04",
            {"text": "Enviar propuesta", "assignee": "David", "due": "2026-03-07"},
        )

    @patch("worker.tasks.granola.handle_notion_upsert_task")
    @patch("worker.tasks.granola.notion_client")
    def test_with_pre_parsed_action_items(self, mock_nc, mock_upsert_task):
        mock_nc.create_transcript_page.return_value = {"page_id": "p1", "url": ""}
        mock_upsert_task.return_value = {"page_id": "t1", "created": True}
        mock_nc.add_comment.return_value = {"comment_id": "c1"}

        result = handle_granola_process_transcript({
            "title": "Meeting",
            "content": "Content",
            "action_items": [
                {"text": "Task 1", "assignee": "David", "due": "2026-03-10"},
                {"text": "Task 2", "assignee": "Ana", "due": ""},
            ],
        })

        assert result["action_items_detected"] == 2
        assert result["action_items_created"] == 0
        assert result["legacy_raw_task_writes_enabled"] is False
        mock_upsert_task.assert_not_called()

    @patch("worker.tasks.granola.handle_notion_upsert_task")
    @patch("worker.tasks.granola.notion_client")
    def test_legacy_raw_task_writes_can_be_enabled_explicitly(self, mock_nc, mock_upsert_task):
        mock_nc.create_transcript_page.return_value = {"page_id": "p1", "url": ""}
        mock_upsert_task.return_value = {"page_id": "t1", "created": True}
        mock_nc.add_comment.return_value = {"comment_id": "c1"}

        result = handle_granola_process_transcript({
            "title": "Meeting",
            "content": "Content",
            "action_items": [
                {"text": "Task 1", "assignee": "David", "due": "2026-03-10"},
                {"text": "Task 2", "assignee": "Ana", "due": ""},
            ],
            "allow_legacy_raw_task_writes": True,
        })

        assert result["action_items_detected"] == 2
        assert result["action_items_created"] == 2
        assert result["legacy_raw_task_writes_enabled"] is True
        assert mock_upsert_task.call_count == 2

    @patch("worker.tasks.granola.notion_client")
    def test_no_enlace_notification(self, mock_nc):
        mock_nc.create_transcript_page.return_value = {"page_id": "p1", "url": ""}

        result = handle_granola_process_transcript({
            "title": "Quick note",
            "content": "Just notes",
            "notify_enlace": False,
        })

        assert result["notification_sent"] is False
        mock_nc.add_comment.assert_not_called()

    def test_missing_title(self):
        with pytest.raises(ValueError, match="'title' is required"):
            handle_granola_process_transcript({"content": "text"})

    def test_missing_content(self):
        with pytest.raises(ValueError, match="'content' is required"):
            handle_granola_process_transcript({"title": "Test"})


class TestHandleGranolaCapitalizeRaw:

    def test_requires_transcript_page_id(self):
        with pytest.raises(ValueError, match="'transcript_page_id' is required"):
            handle_granola_capitalize_raw({"project_name": "Proyecto X"})

    def test_requires_explicit_destination(self):
        with patch("worker.tasks.granola.notion_client") as mock_nc:
            mock_nc.read_page.return_value = {
                "page_id": "raw-1",
                "url": "https://www.notion.so/raw-1",
                "title": "Reunion",
                "plain_text": "Resumen",
            }
            mock_nc.get_page.return_value = {
                "url": "https://www.notion.so/raw-1",
                "properties": {},
            }
            with pytest.raises(ValueError, match="At least one explicit destination is required"):
                handle_granola_capitalize_raw(
                    {
                        "transcript_page_id": "raw-1",
                        "allow_legacy_raw_to_canonical": True,
                    }
                )

    @patch("worker.tasks.granola.notion_client")
    def test_capitalize_raw_is_blocked_by_v1_policy_by_default(self, mock_nc):
        mock_nc.read_page.return_value = {
            "page_id": "raw-1",
            "url": "https://www.notion.so/raw-1",
            "title": "Reunion",
            "plain_text": "Resumen",
        }
        mock_nc.get_page.return_value = {
            "url": "https://www.notion.so/raw-1",
            "properties": {
                "Fecha": {"type": "date", "date": {"start": "2026-03-23"}},
                "Fuente": {"type": "select", "select": {"name": "granola"}},
            },
        }
        mock_nc.add_comment.return_value = {"comment_id": "comment-1"}

        result = handle_granola_capitalize_raw(
            {
                "transcript_page_id": "raw-1",
                "project_name": "Konstruedu",
            }
        )

        assert result["ok"] is False
        assert result["blocked_by_policy"] is True
        assert result["policy"] == "raw_to_canonical_disabled_in_v1"
        assert result["review_comment_added"] is True
        assert result["trace_comments_added"] == 1
        mock_nc.add_comment.assert_called_once()

    @patch("worker.tasks.granola.notion_client")
    def test_capitalize_raw_blocked_policy_handles_review_comment_failures(self, mock_nc):
        mock_nc.read_page.return_value = {
            "page_id": "raw-1",
            "url": "https://www.notion.so/raw-1",
            "title": "Reunion",
            "plain_text": "Resumen",
        }
        mock_nc.get_page.return_value = {
            "url": "https://www.notion.so/raw-1",
            "properties": {
                "Fecha": {"type": "date", "date": {"start": "2026-03-23"}},
                "Fuente": {"type": "select", "select": {"name": "granola"}},
            },
        }
        mock_nc.add_comment.side_effect = RuntimeError("notion unavailable")

        result = handle_granola_capitalize_raw(
            {
                "transcript_page_id": "raw-1",
                "project_name": "Konstruedu",
            }
        )

        assert result["ok"] is False
        assert result["blocked_by_policy"] is True
        assert result["review_comment_added"] is False
        assert result["trace_comments_added"] == 0
        mock_nc.add_comment.assert_called_once()

    @patch("worker.tasks.granola.handle_granola_create_followup")
    @patch("worker.tasks.granola.handle_notion_upsert_bridge_item")
    @patch("worker.tasks.granola.handle_notion_upsert_deliverable")
    @patch("worker.tasks.granola.handle_notion_upsert_project")
    @patch("worker.tasks.granola.notion_client")
    def test_capitalize_raw_writes_targets_and_trace_comments(
        self,
        mock_nc,
        mock_project,
        mock_deliverable,
        mock_bridge,
        mock_followup,
    ):
        mock_nc.read_page.return_value = {
            "page_id": "raw-1",
            "url": "https://www.notion.so/raw-1",
            "title": "Konstruedu",
            "plain_text": "Decision: avanzar piloto. Siguiente paso: enviar propuesta.",
        }
        mock_nc.get_page.return_value = {
            "url": "https://www.notion.so/raw-1",
            "properties": {
                "Fecha": {"type": "date", "date": {"start": "2026-03-23"}},
                "Fuente": {"type": "select", "select": {"name": "granola"}},
                "Estado": {"type": "select", "select": {"name": "Pendiente"}},
                "Fecha que el agente procesó": {"type": "date", "date": None},
            },
        }
        mock_project.return_value = {"ok": True, "page_id": "proj-1", "created": False}
        mock_deliverable.return_value = {"ok": True, "page_id": "deliv-1", "created": True}
        mock_bridge.return_value = {"ok": True, "page_id": "bridge-1", "created": True}
        mock_followup.return_value = {"followup_type": "proposal", "result": {"page_id": "report-1"}}
        mock_nc.add_comment.return_value = {"comment_id": "comment-1"}

        result = handle_granola_capitalize_raw(
            {
                "transcript_page_id": "raw-1",
                "project_name": "Konstruedu",
                "project_next_action": "Enviar propuesta actualizada",
                "deliverable_name": "Propuesta Konstruedu",
                "deliverable_type": "Plan",
                "bridge_item_name": "Validar alcance reunion Konstruedu",
                "bridge_next_action": "Confirmar si pasa a proyecto o queda como seguimiento.",
                "followup_type": "proposal",
                "allow_legacy_raw_to_canonical": True,
            }
        )

        assert result["title"] == "Konstruedu"
        assert result["date"] == "2026-03-23"
        assert result["source"] == "granola"
        assert result["trace_comments_added"] == 4

        project_payload = mock_project.call_args.args[0]
        assert project_payload["name"] == "Konstruedu"
        assert project_payload["next_action"] == "Enviar propuesta actualizada"
        assert project_payload["last_update_date"] == "2026-03-23"

        deliverable_payload = mock_deliverable.call_args.args[0]
        assert deliverable_payload["project_name"] == "Konstruedu"
        assert deliverable_payload["summary"] == "Derivado de reunion raw: Konstruedu"
        assert "Origen raw: Konstruedu (2026-03-23)" in deliverable_payload["notes"]

        bridge_payload = mock_bridge.call_args.args[0]
        assert bridge_payload["project_name"] == "Konstruedu"
        assert bridge_payload["link"] == "https://www.notion.so/raw-1"
        assert bridge_payload["source"] == "Rick"

        followup_payload = mock_followup.call_args.args[0]
        assert followup_payload["transcript_page_id"] == "raw-1"
        assert followup_payload["title"] == "Konstruedu"
        assert followup_payload["date"] == "2026-03-23"

        assert mock_nc.add_comment.call_count == 4
        raw_comment = mock_nc.add_comment.call_args_list[0].kwargs
        assert raw_comment["page_id"] == "raw-1"
        assert "Destino(s): Proyecto: Konstruedu, Entregable: Propuesta Konstruedu" in raw_comment["text"]

    @patch("worker.tasks.granola.handle_notion_upsert_project")
    @patch("worker.tasks.granola.notion_client")
    def test_capitalize_raw_can_skip_trace_comments(self, mock_nc, mock_project):
        mock_nc.read_page.return_value = {
            "page_id": "raw-1",
            "url": "https://www.notion.so/raw-1",
            "title": "Konstruedu",
            "plain_text": "Resumen breve.",
        }
        mock_nc.get_page.return_value = {"url": "https://www.notion.so/raw-1", "properties": {}}
        mock_project.return_value = {"ok": True, "page_id": "proj-1", "created": False}

        result = handle_granola_capitalize_raw(
            {
                "transcript_page_id": "raw-1",
                "project_name": "Konstruedu",
                "add_trace_comments": False,
                "allow_legacy_raw_to_canonical": True,
            }
        )

        assert result["trace_comments_added"] == 0
        mock_nc.add_comment.assert_not_called()


class TestHandleGranolaPromoteCuratedSession:

    def test_requires_transcript_page_id(self):
        with pytest.raises(ValueError, match="'transcript_page_id' is required"):
            handle_granola_promote_curated_session({})

    @patch("worker.tasks.granola.config.NOTION_CURATED_SESSIONS_DB_ID", None)
    def test_requires_curated_sessions_env(self):
        with pytest.raises(RuntimeError, match="NOTION_CURATED_SESSIONS_DB_ID not configured"):
            handle_granola_promote_curated_session({"transcript_page_id": "raw-1"})

    @patch("worker.tasks.granola.config.NOTION_CURATED_SESSIONS_DB_ID", "curated-db-1")
    @patch("worker.tasks.granola.notion_client")
    def test_creates_curated_session_with_supported_schema(self, mock_nc):
        mock_nc.read_page.return_value = {
            "page_id": "raw-1",
            "url": "https://www.notion.so/raw-1",
            "title": "Sesion Borago",
            "plain_text": "Revision comercial y proximos pasos.",
        }
        mock_nc.get_page.return_value = {
            "url": "https://www.notion.so/raw-1",
            "properties": {
                "Fecha": {"type": "date", "date": {"start": "2026-03-24"}},
                "Fuente": {"type": "select", "select": {"name": "granola"}},
                "Estado": {"type": "select", "select": {"name": "Pendiente"}},
                "Fecha que el agente procesó": {"type": "date", "date": None},
                "URL artefacto": {"type": "url", "url": None},
            },
        }
        mock_nc.read_database.return_value = {
            "schema": {
                "Nombre": "title",
                "Fecha": "date",
                "Dominio": "select",
                "Tipo": "select",
                "Proyecto": "relation",
                "Programa": "relation",
                "Recurso relacionado": "relation",
                "Estado": "status",
                "Fuente": "select",
                "URL fuente": "url",
                "Resumen": "rich_text",
                "Notas": "rich_text",
                "Transcripción disponible": "checkbox",
            }
        }
        mock_nc.query_database.side_effect = [[], []]
        mock_nc.create_database_page.return_value = {
            "page_id": "curated-1",
            "url": "https://www.notion.so/curated-1",
            "created": True,
        }
        mock_nc.update_page_properties.return_value = {
            "page_id": "raw-1",
            "url": "https://www.notion.so/raw-1",
            "updated": True,
        }
        mock_nc.add_comment.return_value = {"comment_id": "comment-1"}

        result = handle_granola_promote_curated_session(
            {
                "transcript_page_id": "raw-1",
                "session_name": "Sesion Borago - Curada",
                "domain": "Operacion",
                "session_type": "Asesoria",
                "estado": "Pendiente",
                "summary": "Sesion comercial curada para seguimiento.",
                "project_page_id": "proj-123",
                "program_page_id": "prog-123",
                "resource_page_id": "res-123",
            }
        )

        assert result["matched_existing"] is False
        assert result["trace_comments_added"] == 2
        assert result["session_name"] == "Sesion Borago - Curada"
        assert "Nombre" in result["schema_fields_used"]
        assert "Proyecto" in result["schema_fields_used"]

        assert mock_nc.query_database.call_args_list[0].kwargs == {
            "database_id": "curated-db-1",
            "filter": {"property": "URL fuente", "url": {"equals": "https://www.notion.so/raw-1"}},
        }
        assert mock_nc.query_database.call_args_list[1].kwargs == {
            "database_id": "curated-db-1",
            "filter": {"property": "Nombre", "title": {"equals": "Sesion Borago - Curada"}},
        }
        create_args = mock_nc.create_database_page.call_args.args
        assert create_args[0] == "curated-db-1"
        props = mock_nc.create_database_page.call_args.kwargs["properties"]
        assert props["Nombre"]["title"][0]["text"]["content"] == "Sesion Borago - Curada"
        assert props["Fecha"]["date"]["start"] == "2026-03-24"
        assert props["Dominio"]["select"]["name"] == "Operacion"
        assert props["Tipo"]["select"]["name"] == "Asesoria"
        assert props["Estado"]["status"]["name"] == "Pendiente"
        assert props["Fuente"]["select"]["name"] == "granola"
        assert props["URL fuente"]["url"] == "https://www.notion.so/raw-1"
        assert props["Transcripción disponible"]["checkbox"] is True
        assert props["Proyecto"]["relation"] == [{"id": "proj-123"}]
        assert props["Programa"]["relation"] == [{"id": "prog-123"}]
        assert props["Recurso relacionado"]["relation"] == [{"id": "res-123"}]
        assert "Origen raw: Sesion Borago (2026-03-24)" in props["Notas"]["rich_text"][0]["text"]["content"]
        assert result["raw_status_update"]["ok"] is True
        raw_update_args = mock_nc.update_page_properties.call_args.args
        assert raw_update_args[0] == "raw-1"
        raw_props = mock_nc.update_page_properties.call_args.kwargs["properties"]
        assert raw_props["Estado"]["select"]["name"] == "Procesada"
        assert raw_props["Fecha que el agente procesó"]["date"]["start"]
        assert raw_props["URL artefacto"]["url"] == "https://www.notion.so/curated-1"

    @patch("worker.tasks.granola.config.NOTION_CURATED_SESSIONS_DB_ID", "curated-db-1")
    @patch("worker.tasks.granola.notion_client")
    def test_updates_existing_curated_session_without_comments(self, mock_nc):
        mock_nc.read_page.return_value = {
            "page_id": "raw-1",
            "url": "https://www.notion.so/raw-1",
            "title": "Konstruedu",
            "plain_text": "Resumen breve.",
        }
        mock_nc.get_page.return_value = {
            "url": "https://www.notion.so/raw-1",
            "properties": {
                "Fecha": {"type": "date", "date": {"start": "2026-03-23"}},
                "Fuente": {"type": "select", "select": {"name": "granola"}},
                "Estado": {"type": "select", "select": {"name": "Pendiente"}},
                "Fecha que el agente procesó": {"type": "date", "date": None},
                "URL artefacto": {"type": "url", "url": None},
            },
        }
        mock_nc.read_database.return_value = {
            "schema": {
                "Nombre": "title",
                "Fecha": "date",
                "Fuente": "select",
                "URL fuente": "url",
                "Resumen": "rich_text",
                "Notas": "rich_text",
                "Transcripción disponible": "checkbox",
            }
        }
        mock_nc.query_database.side_effect = [[
            {
                "id": "curated-existing-1",
                "url": "https://www.notion.so/curated-existing-1",
                "properties": {
                    "Nombre": {"type": "title", "title": [{"plain_text": "Konstruedu - propuesta 6 cursos"}]},
                    "Fecha": {"type": "date", "date": {"start": "2026-03-23"}},
                    "URL fuente": {"type": "url", "url": "https://www.notion.so/raw-1"},
                },
            }
        ]]
        mock_nc.update_page_properties.return_value = {
            "page_id": "curated-existing-1",
            "url": "https://www.notion.so/curated-existing-1",
            "updated": True,
        }

        result = handle_granola_promote_curated_session(
            {
                "transcript_page_id": "raw-1",
                "summary": "Resumen curado corto.",
                "add_trace_comments": False,
            }
        )

        assert result["matched_existing"] is True
        assert result["match_strategy"] == "source_url"
        assert result["trace_comments_added"] == 0
        update_args = mock_nc.update_page_properties.call_args_list[0].args
        assert update_args[0] == "curated-existing-1"
        props = mock_nc.update_page_properties.call_args_list[0].kwargs["properties"]
        assert props["Nombre"]["title"][0]["text"]["content"] == "Konstruedu"
        assert props["Resumen"]["rich_text"][0]["text"]["content"] == "Resumen curado corto."
        raw_update_args = mock_nc.update_page_properties.call_args_list[1].args
        assert raw_update_args[0] == "raw-1"
        raw_props = mock_nc.update_page_properties.call_args_list[1].kwargs["properties"]
        assert raw_props["Estado"]["select"]["name"] == "Procesada"
        assert result["raw_status_update"]["ok"] is True
        mock_nc.add_comment.assert_not_called()

    @patch("worker.tasks.granola.config.NOTION_CURATED_SESSIONS_DB_ID", "curated-db-1")
    @patch("worker.tasks.granola.notion_client")
    def test_curated_session_dry_run_skips_writes_and_comments(self, mock_nc):
        mock_nc.read_page.return_value = {
            "page_id": "raw-1",
            "url": "https://www.notion.so/raw-1",
            "title": "Konstruedu",
            "plain_text": "Resumen breve.",
        }
        mock_nc.get_page.return_value = {
            "url": "https://www.notion.so/raw-1",
            "properties": {
                "Fecha": {"type": "date", "date": {"start": "2026-03-23"}},
                "Fuente": {"type": "select", "select": {"name": "granola"}},
                "Estado": {"type": "select", "select": {"name": "Pendiente"}},
                "Fecha que el agente procesó": {"type": "date", "date": None},
            },
        }
        mock_nc.read_database.return_value = {
            "schema": {
                "Nombre": "title",
                "Fecha": "date",
                "Fuente": "select",
                "Notas": "rich_text",
            }
        }
        mock_nc.query_database.side_effect = [[
            {
                "id": "curated-existing-1",
                "url": "https://www.notion.so/curated-existing-1",
                "properties": {
                    "Nombre": {"type": "title", "title": [{"plain_text": "Konstruedu"}]},
                    "Fecha": {"type": "date", "date": {"start": "2026-03-23"}},
                },
            }
        ]]

        result = handle_granola_promote_curated_session(
            {
                "transcript_page_id": "raw-1",
                "dry_run": True,
            }
        )

        assert result["dry_run"] is True
        assert result["matched_existing"] is True
        assert result["match_strategy"] == "exact_title"
        assert result["trace_comments_added"] == 0
        assert result["curated_session"]["dry_run"] is True
        assert result["raw_status_update"]["dry_run"] is True
        assert result["raw_status_update"]["properties"]["Estado"]["select"]["name"] == "Procesada"
        mock_nc.create_database_page.assert_not_called()
        mock_nc.update_page_properties.assert_not_called()
        mock_nc.add_comment.assert_not_called()

    @patch("worker.tasks.granola.config.NOTION_CURATED_SESSIONS_DB_ID", "curated-db-1")
    @patch("worker.tasks.granola.notion_client")
    def test_prefers_existing_session_by_source_url_even_if_title_is_mangled(self, mock_nc):
        mock_nc.read_page.return_value = {
            "page_id": "raw-1",
            "url": "https://www.notion.so/raw-1",
            "title": "Reunión Con Jorge de Boragó",
            "plain_text": "Resumen breve.",
        }
        mock_nc.get_page.return_value = {
            "url": "https://www.notion.so/raw-1",
            "properties": {
                "Fecha": {"type": "date", "date": {"start": "2026-03-24"}},
                "Fuente": {"type": "select", "select": {"name": "granola"}},
                "Estado": {"type": "select", "select": {"name": "Pendiente"}},
                "Fecha que el agente procesó": {"type": "date", "date": None},
            },
        }
        mock_nc.read_database.return_value = {
            "schema": {
                "Nombre": "title",
                "Fecha": "date",
                "URL fuente": "url",
                "Notas": "rich_text",
            },
            "items": [],
        }
        mock_nc.query_database.side_effect = [[
            {
                "id": "curated-good-1",
                "url": "https://www.notion.so/curated-good-1",
                "properties": {
                    "Nombre": {"type": "title", "title": [{"plain_text": "Boragó - propuesta Odoo y M365"}]},
                    "Fecha": {"type": "date", "date": {"start": "2026-03-24"}},
                    "URL fuente": {"type": "url", "url": "https://www.notion.so/raw-1"},
                },
            },
            {
                "id": "curated-bad-1",
                "url": "https://www.notion.so/curated-bad-1",
                "properties": {
                    "Nombre": {"type": "title", "title": [{"plain_text": "Borag? - propuesta Odoo y M365"}]},
                    "Fecha": {"type": "date", "date": {"start": "2026-03-24"}},
                    "URL fuente": {"type": "url", "url": "https://www.notion.so/raw-1"},
                },
            },
        ]]
        mock_nc.update_page_properties.return_value = {
            "page_id": "curated-good-1",
            "url": "https://www.notion.so/curated-good-1",
            "updated": True,
        }

        result = handle_granola_promote_curated_session(
            {
                "transcript_page_id": "raw-1",
                "session_name": "Boragó - propuesta Odoo y M365",
                "add_trace_comments": False,
            }
        )

        assert result["matched_existing"] is True
        assert result["match_strategy"] == "source_url"
        assert result["curated_session"]["page_id"] == "curated-good-1"
        update_args = mock_nc.update_page_properties.call_args_list[0].args
        assert update_args[0] == "curated-good-1"

    @patch("worker.tasks.granola.config.NOTION_CURATED_SESSIONS_DB_ID", "curated-db-1")
    @patch("worker.tasks.granola.notion_client")
    def test_preserves_existing_title_when_payload_title_is_mangled(self, mock_nc):
        mock_nc.read_page.return_value = {
            "page_id": "raw-1",
            "url": "https://www.notion.so/raw-1",
            "title": "Reunión Con Jorge de Boragó",
            "plain_text": "Resumen breve.",
        }
        mock_nc.get_page.return_value = {
            "url": "https://www.notion.so/raw-1",
            "properties": {
                "Fecha": {"type": "date", "date": {"start": "2026-03-24"}},
                "Fuente": {"type": "select", "select": {"name": "granola"}},
            },
        }
        mock_nc.read_database.return_value = {
            "schema": {
                "Nombre": "title",
                "Fecha": "date",
                "URL fuente": "url",
                "Notas": "rich_text",
            },
            "items": [],
        }
        mock_nc.query_database.side_effect = [[
            {
                "id": "curated-good-1",
                "url": "https://www.notion.so/curated-good-1",
                "properties": {
                    "Nombre": {"type": "title", "title": [{"plain_text": "Boragó - propuesta Odoo y M365"}]},
                    "Fecha": {"type": "date", "date": {"start": "2026-03-24"}},
                    "URL fuente": {"type": "url", "url": "https://www.notion.so/raw-1"},
                },
            },
            {
                "id": "curated-bad-1",
                "url": "https://www.notion.so/curated-bad-1",
                "properties": {
                    "Nombre": {"type": "title", "title": [{"plain_text": "Borag? - propuesta Odoo y M365"}]},
                    "Fecha": {"type": "date", "date": {"start": "2026-03-24"}},
                    "URL fuente": {"type": "url", "url": "https://www.notion.so/raw-1"},
                },
            },
        ]]
        mock_nc.update_page_properties.return_value = {
            "page_id": "curated-good-1",
            "url": "https://www.notion.so/curated-good-1",
            "updated": True,
        }

        result = handle_granola_promote_curated_session(
            {
                "transcript_page_id": "raw-1",
                "session_name": "Borag? - propuesta Odoo y M365",
                "add_trace_comments": False,
            }
        )

        assert result["matched_existing"] is True
        assert result["match_strategy"] == "source_url"
        assert result["session_name"] == "Boragó - propuesta Odoo y M365"
        props = mock_nc.update_page_properties.call_args_list[0].kwargs["properties"]
        assert props["Nombre"]["title"][0]["text"]["content"] == "Boragó - propuesta Odoo y M365"


class TestHandleGranolaCreateHumanTaskFromCuratedSession:

    def test_requires_curated_session_page_id(self):
        with pytest.raises(ValueError, match="'curated_session_page_id' is required"):
            handle_granola_create_human_task_from_curated_session({})

    @patch("worker.tasks.granola.config.NOTION_HUMAN_TASKS_DB_ID", None)
    def test_requires_human_tasks_env(self):
        with pytest.raises(RuntimeError, match="NOTION_HUMAN_TASKS_DB_ID not configured"):
            handle_granola_create_human_task_from_curated_session(
                {
                    "curated_session_page_id": "curated-1",
                    "task_name": "Revisar contrato Konstruedu",
                }
            )

    @patch("worker.tasks.granola.config.NOTION_HUMAN_TASKS_DB_ID", "human-tasks-db-1")
    @patch("worker.tasks.granola.notion_client")
    def test_creates_human_task_with_supported_schema(self, mock_nc):
        mock_nc.read_page.return_value = {
            "page_id": "curated-1",
            "url": "https://www.notion.so/curated-1",
            "title": "Konstruedu - propuesta 6 cursos",
            "plain_text": "Presupuesto aprobado. Siguiente paso: revisar contrato.",
        }
        mock_nc.get_page.return_value = {
            "url": "https://www.notion.so/curated-1",
            "properties": {
                "Fecha": {"type": "date", "date": {"start": "2026-03-23"}},
                "Dominio": {"type": "select", "select": {"name": "Operacion"}},
                "Proyecto": {"type": "relation", "relation": [{"id": "proj-123"}]},
            },
        }
        mock_nc.read_database.return_value = {
            "schema": {
                "Nombre": "title",
                "Dominio": "select",
                "Proyecto": "relation",
                "Sesion relacionada": "relation",
                "Tipo": "select",
                "Estado": "status",
                "Prioridad": "select",
                "Fecha objetivo": "date",
                "Origen": "select",
                "URL fuente": "url",
                "Notas": "rich_text",
            }
        }
        mock_nc.query_database.return_value = []
        mock_nc.create_database_page.return_value = {
            "page_id": "task-1",
            "url": "https://www.notion.so/task-1",
            "created": True,
        }
        mock_nc.add_comment.return_value = {"comment_id": "comment-1"}

        result = handle_granola_create_human_task_from_curated_session(
            {
                "curated_session_page_id": "curated-1",
                "task_name": "Revisar contrato Konstruedu",
                "task_type": "Follow-up",
                "estado": "Pendiente",
                "priority": "Alta",
                "due_date": "2026-03-31",
            }
        )

        assert result["matched_existing"] is False
        assert result["trace_comments_added"] == 2
        assert result["task_name"] == "Revisar contrato Konstruedu"
        assert "Sesion relacionada" in result["schema_fields_used"]
        assert "Proyecto" in result["schema_fields_used"]

        mock_nc.query_database.assert_called_once_with(
            database_id="human-tasks-db-1",
            filter={"property": "Nombre", "title": {"equals": "Revisar contrato Konstruedu"}},
        )
        create_args = mock_nc.create_database_page.call_args.args
        assert create_args[0] == "human-tasks-db-1"
        props = mock_nc.create_database_page.call_args.kwargs["properties"]
        assert props["Nombre"]["title"][0]["text"]["content"] == "Revisar contrato Konstruedu"
        assert props["Dominio"]["select"]["name"] == "Operacion"
        assert props["Proyecto"]["relation"] == [{"id": "proj-123"}]
        assert props["Sesion relacionada"]["relation"] == [{"id": "curated-1"}]
        assert props["Tipo"]["select"]["name"] == "Follow-up"
        assert props["Estado"]["status"]["name"] == "Pendiente"
        assert props["Prioridad"]["select"]["name"] == "Alta"
        assert props["Fecha objetivo"]["date"]["start"] == "2026-03-31"
        assert props["Origen"]["select"]["name"] == "Sesion"
        assert props["URL fuente"]["url"] == "https://www.notion.so/curated-1"
        assert "Derivada de sesion curada" in props["Notas"]["rich_text"][0]["text"]["content"]

    @patch("worker.tasks.granola.config.NOTION_HUMAN_TASKS_DB_ID", "human-tasks-db-1")
    @patch("worker.tasks.granola.notion_client")
    def test_updates_existing_human_task_without_comments(self, mock_nc):
        mock_nc.read_page.return_value = {
            "page_id": "curated-1",
            "url": "https://www.notion.so/curated-1",
            "title": "Konstruedu - propuesta 6 cursos",
            "plain_text": "Resumen breve.",
        }
        mock_nc.get_page.return_value = {
            "url": "https://www.notion.so/curated-1",
            "properties": {
                "Fecha": {"type": "date", "date": {"start": "2026-03-23"}},
                "Dominio": {"type": "select", "select": {"name": "Operacion"}},
            },
        }
        mock_nc.read_database.return_value = {
            "schema": {
                "Nombre": "title",
                "Dominio": "select",
                "Sesion relacionada": "relation",
                "Tipo": "select",
                "Estado": "status",
                "Origen": "select",
                "URL fuente": "url",
                "Notas": "rich_text",
            }
        }
        mock_nc.query_database.return_value = [{"id": "task-existing-1"}]
        mock_nc.update_page_properties.return_value = {
            "page_id": "task-existing-1",
            "url": "https://www.notion.so/task-existing-1",
            "updated": True,
        }

        result = handle_granola_create_human_task_from_curated_session(
            {
                "curated_session_page_id": "curated-1",
                "task_name": "Revisar contrato Konstruedu",
                "notes": "Follow-up manual confirmado.",
                "add_trace_comments": False,
            }
        )

        assert result["matched_existing"] is True
        assert result["trace_comments_added"] == 0
        update_args = mock_nc.update_page_properties.call_args.args
        assert update_args[0] == "task-existing-1"
        props = mock_nc.update_page_properties.call_args.kwargs["properties"]
        assert props["Nombre"]["title"][0]["text"]["content"] == "Revisar contrato Konstruedu"
        assert props["Notas"]["rich_text"][0]["text"]["content"] == "Follow-up manual confirmado."
        mock_nc.add_comment.assert_not_called()

    @patch("worker.tasks.granola.config.NOTION_HUMAN_TASKS_DB_ID", "human-tasks-db-1")
    @patch("worker.tasks.granola.notion_client")
    def test_human_task_dry_run_skips_writes_and_comments(self, mock_nc):
        mock_nc.read_page.return_value = {
            "page_id": "curated-1",
            "url": "https://www.notion.so/curated-1",
            "title": "Konstruedu - propuesta 6 cursos",
            "plain_text": "Resumen breve.",
        }
        mock_nc.get_page.return_value = {
            "url": "https://www.notion.so/curated-1",
            "properties": {
                "Fecha": {"type": "date", "date": {"start": "2026-03-23"}},
                "Dominio": {"type": "select", "select": {"name": "Operacion"}},
            },
        }
        mock_nc.read_database.return_value = {
            "schema": {
                "Nombre": "title",
                "Dominio": "select",
                "Sesion relacionada": "relation",
                "Tipo": "select",
                "Estado": "status",
                "Origen": "select",
                "URL fuente": "url",
                "Notas": "rich_text",
            }
        }
        mock_nc.query_database.return_value = [{"id": "task-existing-1", "url": "https://www.notion.so/task-existing-1"}]

        result = handle_granola_create_human_task_from_curated_session(
            {
                "curated_session_page_id": "curated-1",
                "task_name": "Revisar contrato Konstruedu",
                "dry_run": True,
            }
        )

        assert result["dry_run"] is True
        assert result["matched_existing"] is True
        assert result["trace_comments_added"] == 0
        assert result["human_task"]["dry_run"] is True
        mock_nc.create_database_page.assert_not_called()
        mock_nc.update_page_properties.assert_not_called()
        mock_nc.add_comment.assert_not_called()


class TestHandleGranolaUpdateCommercialProjectFromCuratedSession:

    def test_requires_curated_session_page_id(self):
        with pytest.raises(ValueError, match="'curated_session_page_id' is required"):
            handle_granola_update_commercial_project_from_curated_session({})

    @patch("worker.tasks.granola.config.NOTION_COMMERCIAL_PROJECTS_DB_ID", None)
    def test_requires_commercial_projects_env(self):
        with pytest.raises(RuntimeError, match="NOTION_COMMERCIAL_PROJECTS_DB_ID not configured"):
            handle_granola_update_commercial_project_from_curated_session(
                {
                    "curated_session_page_id": "curated-1",
                    "estado": "Propuesta enviada",
                }
            )

    @patch("worker.tasks.granola.config.NOTION_COMMERCIAL_PROJECTS_DB_ID", "commercial-db-1")
    @patch("worker.tasks.granola.notion_client")
    def test_requires_project_target(self, mock_nc):
        mock_nc.read_page.return_value = {
            "page_id": "curated-1",
            "url": "https://www.notion.so/curated-1",
            "title": "Konstruedu - propuesta 6 cursos",
            "plain_text": "Resumen breve.",
        }
        mock_nc.get_page.return_value = {
            "url": "https://www.notion.so/curated-1",
            "properties": {"Fecha": {"type": "date", "date": {"start": "2026-03-23"}}},
        }
        mock_nc.add_comment.return_value = {"comment_id": "comment-1"}

        result = handle_granola_update_commercial_project_from_curated_session(
            {
                "curated_session_page_id": "curated-1",
                "estado": "Propuesta enviada",
            }
        )

        assert result["ok"] is False
        assert result["blocked_by_ambiguity"] is True
        assert result["review_comment_added"] is True
        assert result["trace_comments_added"] == 1
        mock_nc.add_comment.assert_called_once()

    @patch("worker.tasks.granola.config.NOTION_COMMERCIAL_PROJECTS_DB_ID", "commercial-db-1")
    @patch("worker.tasks.granola.notion_client")
    def test_updates_commercial_project_with_supported_schema(self, mock_nc):
        mock_nc.read_page.return_value = {
            "page_id": "curated-1",
            "url": "https://www.notion.so/curated-1",
            "title": "Konstruedu - propuesta 6 cursos",
            "plain_text": "Presupuesto aprobado. Siguiente paso: revisar contrato.",
        }
        mock_nc.get_page.side_effect = [
            {
                "url": "https://www.notion.so/curated-1",
                "properties": {
                    "Fecha": {"type": "date", "date": {"start": "2026-03-23"}},
                    "Proyecto": {"type": "relation", "relation": [{"id": "proj-123"}]},
                },
            },
            {
                "url": "https://www.notion.so/proj-123",
                "properties": {
                    "Nombre": {
                        "type": "title",
                        "title": [{"plain_text": "Especializacion IA + Automatizacion AECO - 6 Cursos Konstruedu"}],
                    }
                },
            },
        ]
        mock_nc.read_database.return_value = {
            "schema": {
                "Nombre": "title",
                "Estado": "status",
                "Acción Requerida": "select",
                "Fecha": "date",
                "Plazo": "date",
                "Monto": "number",
                "Tipo": "select",
                "Cliente": "select",
            }
        }
        mock_nc.update_page_properties.return_value = {
            "page_id": "proj-123",
            "url": "https://www.notion.so/proj-123",
            "updated": True,
        }
        mock_nc.add_comment.return_value = {"comment_id": "comment-1"}

        result = handle_granola_update_commercial_project_from_curated_session(
            {
                "curated_session_page_id": "curated-1",
                "estado": "Propuesta enviada",
                "accion_requerida": "Revisar contrato",
            }
        )

        assert result["project_page_id"] == "proj-123"
        assert result["project_title"] == "Especializacion IA + Automatizacion AECO - 6 Cursos Konstruedu"
        assert result["trace_comments_added"] == 2
        assert "Estado" in result["schema_fields_used"]
        assert "Acción Requerida" in result["schema_fields_used"]

        update_args = mock_nc.update_page_properties.call_args.args
        assert update_args[0] == "proj-123"
        props = mock_nc.update_page_properties.call_args.kwargs["properties"]
        assert props["Estado"]["status"]["name"] == "Propuesta enviada"
        assert props["Acción Requerida"]["select"]["name"] == "Revisar contrato"

    @patch("worker.tasks.granola.config.NOTION_COMMERCIAL_PROJECTS_DB_ID", "commercial-db-1")
    @patch("worker.tasks.granola.notion_client")
    def test_requires_explicit_commercial_fields(self, mock_nc):
        mock_nc.read_page.return_value = {
            "page_id": "curated-1",
            "url": "https://www.notion.so/curated-1",
            "title": "Konstruedu - propuesta 6 cursos",
            "plain_text": "Resumen breve.",
        }
        mock_nc.get_page.return_value = {
            "url": "https://www.notion.so/curated-1",
            "properties": {
                "Fecha": {"type": "date", "date": {"start": "2026-03-23"}},
                "Proyecto": {"type": "relation", "relation": [{"id": "proj-123"}]},
            },
        }

        with pytest.raises(ValueError, match="At least one explicit commercial field is required"):
            handle_granola_update_commercial_project_from_curated_session(
                {"curated_session_page_id": "curated-1"}
            )

    @patch("worker.tasks.granola.config.NOTION_COMMERCIAL_PROJECTS_DB_ID", "commercial-db-1")
    @patch("worker.tasks.granola.notion_client")
    def test_commercial_project_dry_run_skips_write_and_comments(self, mock_nc):
        mock_nc.read_page.return_value = {
            "page_id": "curated-1",
            "url": "https://www.notion.so/curated-1",
            "title": "Konstruedu - propuesta 6 cursos",
            "plain_text": "Resumen breve.",
        }
        mock_nc.get_page.side_effect = [
            {
                "url": "https://www.notion.so/curated-1",
                "properties": {
                    "Fecha": {"type": "date", "date": {"start": "2026-03-23"}},
                    "Proyecto": {"type": "relation", "relation": [{"id": "proj-123"}]},
                },
            },
            {
                "url": "https://www.notion.so/proj-123",
                "properties": {
                    "Nombre": {"type": "title", "title": [{"plain_text": "Proyecto X"}]},
                },
            },
        ]
        mock_nc.read_database.return_value = {
            "schema": {
                "Estado": "status",
                "Acción Requerida": "select",
            }
        }

        result = handle_granola_update_commercial_project_from_curated_session(
            {
                "curated_session_page_id": "curated-1",
                "estado": "Propuesta enviada",
                "dry_run": True,
            }
        )

        assert result["dry_run"] is True
        assert result["trace_comments_added"] == 0
        assert result["commercial_project"]["dry_run"] is True
        mock_nc.update_page_properties.assert_not_called()
        mock_nc.add_comment.assert_not_called()


class TestHandleGranolaPromoteOperationalSlice:

    def test_requires_transcript_page_id(self):
        with pytest.raises(ValueError, match="'transcript_page_id' is required"):
            handle_granola_promote_operational_slice({})

    def test_requires_curated_payload(self):
        with pytest.raises(ValueError, match="'curated_payload' is required"):
            handle_granola_promote_operational_slice({"transcript_page_id": "raw-1"})

    def test_requires_at_least_one_destination_payload(self):
        with pytest.raises(ValueError, match="At least one destination payload is required"):
            handle_granola_promote_operational_slice(
                {
                    "transcript_page_id": "raw-1",
                    "curated_payload": {"session_name": "Sesion X"},
                }
            )

    @patch("worker.tasks.granola.handle_granola_update_commercial_project_from_curated_session")
    @patch("worker.tasks.granola.handle_granola_create_human_task_from_curated_session")
    @patch("worker.tasks.granola.handle_granola_promote_curated_session")
    def test_composes_explicit_slices(
        self,
        mock_promote_curated,
        mock_create_human_task,
        mock_update_commercial_project,
    ):
        mock_promote_curated.return_value = {
            "curated_session": {"page_id": "curated-1", "created": True},
            "session_name": "Sesion X",
        }
        mock_create_human_task.return_value = {"human_task": {"page_id": "task-1", "created": True}}
        mock_update_commercial_project.return_value = {
            "commercial_project": {"page_id": "proj-1", "updated": True}
        }

        result = handle_granola_promote_operational_slice(
            {
                "transcript_page_id": "raw-1",
                "curated_payload": {"session_name": "Sesion X"},
                "human_task_payload": {"task_name": "Follow-up X"},
                "commercial_project_payload": {"estado": "Propuesta enviada"},
            }
        )

        assert result["transcript_page_id"] == "raw-1"
        assert result["curated_session_page_id"] == "curated-1"
        assert "curated" in result["results"]
        assert "human_task" in result["results"]
        assert "commercial_project" in result["results"]

        mock_promote_curated.assert_called_once_with(
            {"session_name": "Sesion X", "transcript_page_id": "raw-1"}
        )
        mock_create_human_task.assert_called_once_with(
            {"task_name": "Follow-up X", "curated_session_page_id": "curated-1"}
        )
        mock_update_commercial_project.assert_called_once_with(
            {"estado": "Propuesta enviada", "curated_session_page_id": "curated-1"}
        )

    @patch("worker.tasks.granola.handle_granola_update_commercial_project_from_curated_session")
    @patch("worker.tasks.granola.handle_granola_create_human_task_from_curated_session")
    @patch("worker.tasks.granola.handle_granola_promote_curated_session")
    def test_dry_run_propagates_to_subpayloads(
        self,
        mock_promote_curated,
        mock_create_human_task,
        mock_update_commercial_project,
    ):
        mock_promote_curated.return_value = {
            "curated_session": {"page_id": "curated-1", "dry_run": True},
        }
        mock_create_human_task.return_value = {"human_task": {"dry_run": True}}
        mock_update_commercial_project.return_value = {"commercial_project": {"dry_run": True}}

        result = handle_granola_promote_operational_slice(
            {
                "transcript_page_id": "raw-1",
                "dry_run": True,
                "curated_payload": {"session_name": "Sesion X"},
                "human_task_payload": {"task_name": "Follow-up X"},
                "commercial_project_payload": {"estado": "Propuesta enviada"},
            }
        )

        assert result["dry_run"] is True
        mock_promote_curated.assert_called_once_with(
            {"session_name": "Sesion X", "transcript_page_id": "raw-1", "dry_run": True}
        )
        mock_create_human_task.assert_called_once_with(
            {"task_name": "Follow-up X", "curated_session_page_id": "curated-1", "dry_run": True}
        )
        mock_update_commercial_project.assert_called_once_with(
            {"estado": "Propuesta enviada", "curated_session_page_id": "curated-1", "dry_run": True}
        )

    @patch("worker.tasks.granola.handle_granola_update_commercial_project_from_curated_session")
    @patch("worker.tasks.granola.handle_granola_create_human_task_from_curated_session")
    @patch("worker.tasks.granola.handle_granola_promote_curated_session")
    def test_dry_run_skips_downstream_when_new_curated_has_no_page_id(
        self,
        mock_promote_curated,
        mock_create_human_task,
        mock_update_commercial_project,
    ):
        mock_promote_curated.return_value = {
            "curated_session": {
                "created": True,
                "dry_run": True,
                "properties": {"Nombre": {"title": [{"text": {"content": "Sesion nueva"}}]}},
            },
        }

        result = handle_granola_promote_operational_slice(
            {
                "transcript_page_id": "raw-1",
                "dry_run": True,
                "curated_payload": {"session_name": "Sesion nueva"},
                "human_task_payload": {"task_name": "Follow-up X"},
                "commercial_project_payload": {"estado": "En conversación"},
            }
        )

        assert result["dry_run"] is True
        assert result["curated_session_page_id"] == ""
        assert result["results"]["human_task"]["skipped"] is True
        assert result["results"]["commercial_project"]["skipped"] is True
        assert (
            result["results"]["human_task"]["reason"]
            == "curated_session_page_id_unavailable_in_dry_run_for_new_session"
        )
        mock_create_human_task.assert_not_called()
        mock_update_commercial_project.assert_not_called()


class TestHandleGranolaCreateFollowup:

    @patch("worker.tasks.granola.notion_client")
    def test_reminder(self, mock_nc):
        mock_nc.upsert_task.return_value = {"page_id": "t-1", "created": True}

        result = handle_granola_create_followup({
            "transcript_page_id": "page-123",
            "followup_type": "reminder",
            "title": "Client Meeting",
            "date": "2026-03-04",
            "due_date": "2026-03-11",
        })

        assert result["followup_type"] == "reminder"
        assert result["result"]["due_date"] == "2026-03-11"
        mock_nc.upsert_task.assert_called_once()
        call_kwargs = mock_nc.upsert_task.call_args.kwargs
        assert "Client Meeting" in call_kwargs["task"]

    @patch("worker.tasks.granola.notion_client")
    def test_email_draft(self, mock_nc):
        mock_nc.add_comment.return_value = {"comment_id": "c-1"}

        result = handle_granola_create_followup({
            "transcript_page_id": "page-123",
            "followup_type": "email_draft",
            "title": "Sprint Review",
            "date": "2026-03-04",
            "action_items": [{"text": "Deploy v2", "assignee": "DevOps", "due": "2026-03-06"}],
        })

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

        result = handle_granola_create_followup({
            "transcript_page_id": "page-123",
            "followup_type": "proposal",
            "title": "Kickoff",
            "date": "2026-03-04",
            "attendees": ["David", "Client"],
            "action_items": [{"text": "Start phase 1", "assignee": "David", "due": "2026-03-15"}],
        })

        assert result["followup_type"] == "proposal"
        assert result["result"]["ok"] is True
        mock_nc.create_report_page.assert_called_once()

    def test_missing_page_id(self):
        with pytest.raises(ValueError, match="'transcript_page_id' is required"):
            handle_granola_create_followup({"followup_type": "reminder"})

    def test_invalid_followup_type(self):
        with pytest.raises(ValueError, match="'followup_type' must be one of"):
            handle_granola_create_followup({
                "transcript_page_id": "p-1",
                "followup_type": "invalid",
            })

    @patch("worker.tasks.granola.notion_client")
    def test_reminder_default_due_date(self, mock_nc):
        mock_nc.upsert_task.return_value = {"page_id": "t-1", "created": True}

        result = handle_granola_create_followup({
            "transcript_page_id": "page-123",
            "followup_type": "reminder",
            "title": "Meeting",
        })

        assert result["result"]["due_date"]  # Should have a default
        assert len(result["result"]["due_date"]) == 10  # YYYY-MM-DD format


def test_build_action_item_task_id_is_stable():
    item = {"text": "Verify watcher works", "assignee": "Test User", "due": "2026-03-22"}

    task_id_1 = _build_action_item_task_id("Smoke Test Meeting", "2026-03-22", item)
    task_id_2 = _build_action_item_task_id("Smoke Test Meeting", "2026-03-22", dict(item))

    assert task_id_1 == task_id_2
    assert task_id_1.startswith("granola-action-item-")


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
        # Hidden file should be skipped
        (tmp_path / ".hidden.md").write_text("# Hidden\n\nShould be skipped.", encoding="utf-8")

        processed_dir = tmp_path / "processed"
        mock_send.return_value = {"status": "ok"}

        count = scan_and_process(tmp_path, "http://localhost:8088", "test-token", processed_dir)

        assert count == 3
        assert mock_send.call_count == 3
