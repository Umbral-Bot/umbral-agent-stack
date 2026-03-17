"""
Tests for dispatcher.smart_reply — Smart Notion Reply Pipeline.

Covers:
- Question flow: research + LLM + comment
- Question flow: research fails → LLM-only answer
- Question flow: LLM fails → fallback acknowledgment
- Task flow: LLM plan + comment + enqueue
- Task flow: LLM fails → fallback
- Instruction flow: acknowledge
- Echo flow: acknowledge
- Integration: _do_poll calls smart_reply instead of old envelope
"""

import uuid
from unittest.mock import MagicMock, patch, call

import pytest

from dispatcher.intent_classifier import IntentResult
from dispatcher.smart_reply import (
    handle_smart_reply,
    _build_instruction_message,
    _do_research,
    _do_llm_generate,
    _handoff_instruction_to_rick,
    _instruction_task_id,
    _is_external_reference_instruction,
    _post_comment,
    _post_fallback,
    _resolve_rick_main_session_id,
    ECHO_PREFIX,
)


# ── Fixtures ────────────────────────────────────────────────────

@pytest.fixture
def wc():
    """Mock WorkerClient."""
    return MagicMock()


@pytest.fixture
def queue():
    """Mock TaskQueue."""
    return MagicMock()


COMMENT_ID = "abc12345-6789-0000-0000-000000000000"
COMMENT_TEXT_QUESTION = "¿Cuáles son las tendencias BIM 2026?"
COMMENT_TEXT_TASK = "Genera un reporte de marketing para esta semana"
COMMENT_TEXT_INSTRUCTION = "Configura el equipo advisory para responder en inglés"
COMMENT_TEXT_ECHO = "ok gracias"


def _research_result(n=3):
    """Build a mock research.web Worker response."""
    results = [
        {
            "title": f"Result {i}",
            "snippet": f"Snippet for result {i} about the query topic.",
            "url": f"https://example.com/{i}",
        }
        for i in range(1, n + 1)
    ]
    return {"ok": True, "result": {"results": results, "count": n, "engine": "tavily"}}


def _llm_result(text="Respuesta generada por LLM."):
    """Build a mock llm.generate Worker response."""
    return {
        "ok": True,
        "result": {
            "text": text,
            "model": "gemini-2.5-flash",
            "usage": {"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80},
        },
    }


def _empty_result():
    return {"ok": True, "result": {}}


# ── Test _do_research ───────────────────────────────────────────

class TestDoResearch:
    def test_returns_formatted_context(self, wc):
        wc.run.return_value = _research_result(2)
        ctx = _do_research(wc, "tendencias BIM")
        assert ctx is not None
        assert "Result 1" in ctx
        assert "Result 2" in ctx
        assert "example.com/1" in ctx
        wc.run.assert_called_once_with(
            "research.web",
            {"query": "tendencias BIM", "count": 3, "search_depth": "basic"},
        )

    def test_returns_none_on_empty_results(self, wc):
        wc.run.return_value = {"ok": True, "result": {"results": [], "count": 0}}
        assert _do_research(wc, "xyz") is None

    def test_returns_none_on_exception(self, wc):
        wc.run.side_effect = Exception("network error")
        assert _do_research(wc, "xyz") is None


# ── Test _do_llm_generate ──────────────────────────────────────

class TestDoLlmGenerate:
    def test_returns_text(self, wc):
        wc.run.return_value = _llm_result("Hola mundo")
        text = _do_llm_generate(wc, "prompt", "system")
        assert text == "Hola mundo"

    def test_returns_none_on_empty(self, wc):
        wc.run.return_value = {"ok": True, "result": {"text": ""}}
        assert _do_llm_generate(wc, "prompt", "system") is None

    def test_returns_none_on_exception(self, wc):
        wc.run.side_effect = Exception("timeout")
        assert _do_llm_generate(wc, "prompt", "system") is None


# ── Test handle_smart_reply: question intent ───────────────────

class TestQuestionFlow:
    def test_question_with_research_and_llm(self, wc, queue):
        """Full pipeline: research.web → llm.generate → notion.add_comment."""
        wc.run.side_effect = [
            _research_result(3),   # research.web
            _llm_result("BIM 2026 se enfoca en gemelos digitales."),  # llm.generate
            _empty_result(),       # notion.add_comment
        ]
        handle_smart_reply(COMMENT_TEXT_QUESTION, COMMENT_ID, IntentResult("question", "high"), "improvement", wc, queue, MagicMock())

        assert wc.run.call_count == 3
        # First call: research
        assert wc.run.call_args_list[0][0][0] == "research.web"
        # Second call: LLM
        assert wc.run.call_args_list[1][0][0] == "llm.generate"
        # Third call: post comment
        assert wc.run.call_args_list[2][0][0] == "notion.add_comment"
        posted_text = wc.run.call_args_list[2][0][1]["text"]
        assert posted_text.startswith(ECHO_PREFIX)
        assert "gemelos digitales" in posted_text
        # No tasks enqueued for questions
        queue.enqueue.assert_not_called()

    def test_question_research_fails_llm_only(self, wc, queue):
        """research.web fails → still answers via LLM (no web context)."""
        wc.run.side_effect = [
            Exception("Tavily down"),      # research.web fails
            _llm_result("Respuesta sin contexto web."),  # llm.generate
            _empty_result(),               # notion.add_comment
        ]
        handle_smart_reply(COMMENT_TEXT_QUESTION, COMMENT_ID, IntentResult("question", "high"), "system", wc, queue, MagicMock())

        assert wc.run.call_count == 3
        posted_text = wc.run.call_args_list[2][0][1]["text"]
        assert "sin contexto web" in posted_text

    def test_question_llm_fails_posts_fallback(self, wc, queue):
        """Both research + LLM fail → fallback acknowledgment."""
        wc.run.side_effect = [
            _research_result(1),     # research OK
            Exception("Gemini down"),  # llm.generate fails
            _empty_result(),         # fallback notion.add_comment
        ]
        handle_smart_reply(COMMENT_TEXT_QUESTION, COMMENT_ID, IntentResult("question", "high"), "system", wc, queue, MagicMock())

        # The last call should be the fallback comment
        posted_text = wc.run.call_args_list[-1][0][1]["text"]
        assert "Investigando" in posted_text

    def test_question_both_fail_posts_fallback(self, wc, queue):
        """Research fails + LLM fails → fallback."""
        wc.run.side_effect = [
            Exception("research down"),
            Exception("llm down"),
            _empty_result(),  # fallback post
        ]
        handle_smart_reply(COMMENT_TEXT_QUESTION, COMMENT_ID, IntentResult("question", "high"), "system", wc, queue, MagicMock())

        posted_text = wc.run.call_args_list[-1][0][1]["text"]
        assert "Investigando" in posted_text


# ── Test handle_smart_reply: task intent ───────────────────────

class TestTaskFlow:
    @patch("dispatcher.smart_reply._get_workflow_engine")
    def test_task_generates_plan_and_enqueues(self, mock_get_engine, wc, queue):
        """task without workflow → LLM plan + post + enqueue."""
        # Force no-workflow path so we test the LLM plan fallback
        _mock_engine = MagicMock()
        _mock_engine.has_workflow.return_value = False
        mock_get_engine.return_value = _mock_engine

        wc.run.side_effect = [
            _llm_result("1. Recopilar datos\n2. Generar gráficas\n3. Publicar"),  # llm
            _empty_result(),  # notion.add_comment
        ]
        handle_smart_reply(COMMENT_TEXT_TASK, COMMENT_ID, IntentResult("task", "high"), "marketing", wc, queue, MagicMock())

        # LLM called for plan
        assert wc.run.call_args_list[0][0][0] == "llm.generate"
        # Comment posted with plan
        posted_text = wc.run.call_args_list[1][0][1]["text"]
        assert "Plan para equipo [marketing]" in posted_text
        assert "Recopilar datos" in posted_text
        # Task enqueued
        queue.enqueue.assert_called_once()
        envelope = queue.enqueue.call_args[0][0]
        assert envelope["team"] == "marketing"
        assert envelope["source"] == "smart_reply"
        assert envelope["input"]["original_request"] == COMMENT_TEXT_TASK

    @patch("dispatcher.smart_reply._get_workflow_engine")
    def test_task_llm_fails_posts_fallback(self, mock_get_engine, wc, queue):
        """task without workflow, LLM fails → fallback."""
        _mock_engine = MagicMock()
        _mock_engine.has_workflow.return_value = False
        mock_get_engine.return_value = _mock_engine

        wc.run.side_effect = [
            Exception("llm down"),
            _empty_result(),  # fallback post
        ]
        handle_smart_reply(COMMENT_TEXT_TASK, COMMENT_ID, IntentResult("task", "high"), "marketing", wc, queue, MagicMock())

        posted_text = wc.run.call_args_list[-1][0][1]["text"]
        assert "Tarea registrada" in posted_text
        queue.enqueue.assert_not_called()


# ── Test handle_smart_reply: instruction intent ────────────────

class TestInstructionFlow:
    @patch("dispatcher.smart_reply._handoff_instruction_to_rick")
    def test_instruction_posts_confirmation(self, mock_handoff, wc, queue):
        mock_handoff.return_value = True
        wc.run.return_value = _empty_result()
        handle_smart_reply(COMMENT_TEXT_INSTRUCTION, COMMENT_ID, IntentResult("instruction", "high"), "system", wc, queue, MagicMock())

        assert wc.run.call_count == 3
        assert wc.run.call_args_list[0][0][0] == "notion.add_comment"
        assert wc.run.call_args_list[0][0][1] == {
            "text": f"{ECHO_PREFIX} Instrucción registrada. Procesando configuración. (comment_id={COMMENT_ID[:8]}...)",
        }
        assert wc.run.call_args_list[1][0][0] == "notion.upsert_task"
        task_payload = wc.run.call_args_list[1][0][1]
        assert task_payload["task_id"] == _instruction_task_id(COMMENT_ID)
        assert task_payload["team"] == "system"
        assert task_payload["source_kind"] == "instruction_comment"
        assert wc.run.call_args_list[2][0][0] == "notion.upsert_task"
        assert wc.run.call_args_list[2][0][1]["status"] == "running"
        assert "Seguimiento inyectado" in wc.run.call_args_list[2][0][1]["result_summary"]
        mock_handoff.assert_called_once()
        queue.enqueue.assert_not_called()

    @patch("dispatcher.smart_reply._handoff_instruction_to_rick")
    def test_instruction_inherits_project_context_from_comment_page(self, mock_handoff, wc, queue):
        mock_handoff.return_value = False
        wc.run.return_value = _empty_result()

        handle_smart_reply(
            COMMENT_TEXT_INSTRUCTION,
            COMMENT_ID,
            IntentResult("instruction", "high"),
            "system",
            wc,
            queue,
            MagicMock(),
            page_id="project-page-1",
            page_kind="project",
        )

        task_payload = wc.run.call_args_list[1][0][1]
        assert task_payload["project_page_id"] == "project-page-1"
        assert task_payload["deliverable_page_id"] is None

    @patch("dispatcher.smart_reply._handoff_instruction_to_rick")
    def test_instruction_inherits_deliverable_context_from_comment_page(self, mock_handoff, wc, queue):
        mock_handoff.return_value = False
        wc.run.return_value = _empty_result()

        handle_smart_reply(
            COMMENT_TEXT_INSTRUCTION,
            COMMENT_ID,
            IntentResult("instruction", "high"),
            "system",
            wc,
            queue,
            MagicMock(),
            page_id="deliverable-page-1",
            page_kind="deliverable",
        )

        task_payload = wc.run.call_args_list[1][0][1]
        assert task_payload["project_page_id"] is None
        assert task_payload["deliverable_page_id"] == "deliverable-page-1"

    @patch("dispatcher.smart_reply._handoff_instruction_to_rick")
    def test_instruction_without_handoff_keeps_single_task_update(self, mock_handoff, wc, queue):
        mock_handoff.return_value = False
        wc.run.return_value = _empty_result()
        handle_smart_reply(COMMENT_TEXT_INSTRUCTION, COMMENT_ID, IntentResult("instruction", "high"), "system", wc, queue, MagicMock())

        assert wc.run.call_count == 2
        mock_handoff.assert_called_once()
        queue.enqueue.assert_not_called()


class TestInstructionMirroring:
    def test_detects_external_reference_instruction(self):
        assert _is_external_reference_instruction("Rick, mira esta publicación de LinkedIn https://www.linkedin.com/posts/x")
        assert not _is_external_reference_instruction("Rick, baja el tono del mensaje de bienvenida")

    def test_build_instruction_message_mentions_evidence_for_external_reference(self):
        msg = _build_instruction_message(
            "Rick, revisa esta publicación https://www.linkedin.com/posts/x y rehace el benchmark",
            COMMENT_ID,
        )
        assert _instruction_task_id(COMMENT_ID) in msg
        assert "evidencia real con tools" in msg
        assert "notion.upsert_deliverable" in msg
        assert "notion.create_report_page" in msg
        assert "archivala con notion.update_page_properties(archived=true)" in msg

    def test_instruction_task_id_uses_more_than_short_prefix(self):
        comment_a = "3265f443-fb5c-8155-b6a0-001dda1b1f9b"
        comment_b = "3265f443-fb5c-810d-afa0-001d56f14659"
        assert _instruction_task_id(comment_a) != _instruction_task_id(comment_b)


class TestInstructionHandoff:
    @patch("dispatcher.smart_reply._run_openclaw_agent")
    @patch("dispatcher.smart_reply._send_telegram_message")
    @patch("dispatcher.smart_reply._resolve_rick_main_session_id")
    def test_handoff_prefers_openclaw_agent(self, mock_session_id, mock_send_telegram, mock_run_agent):
        mock_session_id.return_value = "035bee42-a55e-4192-8a2e-1d11cdb85908"
        mock_run_agent.return_value = True

        assert _handoff_instruction_to_rick("reabre el caso", COMMENT_ID) is True
        mock_run_agent.assert_called_once()
        mock_send_telegram.assert_not_called()

    @patch("dispatcher.smart_reply._run_openclaw_agent")
    @patch("dispatcher.smart_reply._send_telegram_message")
    @patch("dispatcher.smart_reply._resolve_rick_main_session_id")
    def test_handoff_falls_back_to_telegram(self, mock_session_id, mock_send_telegram, mock_run_agent):
        mock_session_id.return_value = "035bee42-a55e-4192-8a2e-1d11cdb85908"
        mock_run_agent.return_value = False
        mock_send_telegram.return_value = True

        assert _handoff_instruction_to_rick("reabre el caso", COMMENT_ID) is True
        mock_run_agent.assert_called_once()
        mock_send_telegram.assert_called_once()

    def test_resolve_rick_main_session_id_prefers_exact_telegram_session(self, monkeypatch, tmp_path):
        store = tmp_path / "sessions.json"
        store.write_text(
            """
            {
              "agent:main:telegram:slash:1813248373": {
                "sessionId": "035bee42-a55e-4192-8a2e-1d11cdb85908",
                "updatedAt": 1773497886432,
                "origin": {
                  "provider": "telegram",
                  "from": "telegram:1813248373",
                  "to": "telegram:1813248373"
                }
              }
            }
            """.strip(),
            encoding="utf-8",
        )
        monkeypatch.setenv("OPENCLAW_MAIN_SESSION_STORE", str(store))
        monkeypatch.delenv("OPENCLAW_MAIN_TELEGRAM_SESSION_ID", raising=False)
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        monkeypatch.delenv("TELEGRAM_ALLOWLIST_ID", raising=False)

        assert _resolve_rick_main_session_id() == "035bee42-a55e-4192-8a2e-1d11cdb85908"


# ── Test handle_smart_reply: echo intent ───────────────────────

class TestEchoFlow:
    def test_echo_posts_acknowledgment(self, wc, queue):
        wc.run.return_value = _empty_result()
        handle_smart_reply(COMMENT_TEXT_ECHO, COMMENT_ID, IntentResult("echo", "high"), "system", wc, queue, MagicMock())

        wc.run.assert_called_once()
        posted_text = wc.run.call_args[0][1]["text"]
        assert posted_text.startswith(ECHO_PREFIX)
        assert "Recibido" in posted_text


# ── Test _post_fallback ────────────────────────────────────────

class TestPostFallback:
    def test_fallback_question(self, wc):
        _post_fallback(wc, COMMENT_ID, "question")
        text = wc.run.call_args[0][1]["text"]
        assert "Investigando" in text

    def test_fallback_task(self, wc):
        _post_fallback(wc, COMMENT_ID, "task")
        text = wc.run.call_args[0][1]["text"]
        assert "Tarea registrada" in text

    def test_fallback_unknown(self, wc):
        _post_fallback(wc, COMMENT_ID, "unknown_intent")
        text = wc.run.call_args[0][1]["text"]
        assert "Recibido" in text


# ── Test pipeline error resilience ─────────────────────────────

class TestPipelineResilience:
    def test_entire_pipeline_exception_posts_fallback(self, wc, queue):
        """If handle_smart_reply's internal logic throws, fallback is posted."""
        # Make _handle_question crash by having research return unexpected format
        wc.run.side_effect = [
            {"ok": True, "result": None},  # research returns None result
            Exception("boom"),              # LLM also fails
            _empty_result(),               # fallback comment
        ]
        # Should not raise
        handle_smart_reply(COMMENT_TEXT_QUESTION, COMMENT_ID, IntentResult("question", "high"), "system", wc, queue, MagicMock())
        # Fallback should have been posted
        assert wc.run.call_count >= 2


# ── Test integration: _do_poll uses smart_reply ────────────────

class TestPollerIntegration:
    """Verify that _do_poll now calls smart_reply instead of old envelope."""

    @patch("dispatcher.notion_poller.handle_smart_reply")
    def test_do_poll_calls_smart_reply(self, mock_smart, wc):
        import fakeredis
        r = fakeredis.FakeRedis(decode_responses=True)
        from dispatcher.queue import TaskQueue
        queue = TaskQueue(r)

        # Simulate a comment returned by poll
        wc.notion_poll_comments.return_value = {
            "comments": [
                {
                    "id": COMMENT_ID,
                    "text": COMMENT_TEXT_QUESTION,
                    "created_time": "2026-03-04T10:00:00Z",
                }
            ]
        }

        from dispatcher.notion_poller import _do_poll
        # Patch the import of smart_reply inside notion_poller
        with patch("dispatcher.notion_poller.handle_smart_reply", mock_smart):
            _do_poll(wc, queue, r, MagicMock())

        mock_smart.assert_called_once()
        args = mock_smart.call_args[0]
        assert args[0] == COMMENT_TEXT_QUESTION  # comment_text
        assert args[1] == COMMENT_ID             # comment_id
        assert args[2].intent == "question"             # intent
        assert args[4] is wc                     # wc

    @patch("dispatcher.notion_poller.handle_smart_reply")
    def test_do_poll_skips_rick_echo(self, mock_smart, wc):
        """Comments starting with 'Rick:' should be skipped."""
        import fakeredis
        r = fakeredis.FakeRedis(decode_responses=True)
        from dispatcher.queue import TaskQueue
        queue = TaskQueue(r)

        wc.notion_poll_comments.return_value = {
            "comments": [
                {
                    "id": "skip-this",
                    "text": "Rick: ya respondí",
                    "created_time": "2026-03-04T10:00:00Z",
                }
            ]
        }

        from dispatcher.notion_poller import _do_poll
        with patch("dispatcher.notion_poller.handle_smart_reply", mock_smart):
            _do_poll(wc, queue, r, MagicMock())

        mock_smart.assert_not_called()
