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

from dispatcher.smart_reply import (
    handle_smart_reply,
    _do_research,
    _do_llm_generate,
    _post_comment,
    _post_fallback,
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
        handle_smart_reply(COMMENT_TEXT_QUESTION, COMMENT_ID, "question", "improvement", wc, queue)

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
        handle_smart_reply(COMMENT_TEXT_QUESTION, COMMENT_ID, "question", "system", wc, queue)

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
        handle_smart_reply(COMMENT_TEXT_QUESTION, COMMENT_ID, "question", "system", wc, queue)

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
        handle_smart_reply(COMMENT_TEXT_QUESTION, COMMENT_ID, "question", "system", wc, queue)

        posted_text = wc.run.call_args_list[-1][0][1]["text"]
        assert "Investigando" in posted_text


# ── Test handle_smart_reply: task intent ───────────────────────

class TestTaskFlow:
    def test_task_generates_plan_and_enqueues(self, wc, queue):
        """task → LLM plan + post + enqueue."""
        wc.run.side_effect = [
            _llm_result("1. Recopilar datos\n2. Generar gráficas\n3. Publicar"),  # llm
            _empty_result(),  # notion.add_comment
        ]
        handle_smart_reply(COMMENT_TEXT_TASK, COMMENT_ID, "task", "marketing", wc, queue)

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

    def test_task_llm_fails_posts_fallback(self, wc, queue):
        """task but LLM fails → fallback."""
        wc.run.side_effect = [
            Exception("llm down"),
            _empty_result(),  # fallback post
        ]
        handle_smart_reply(COMMENT_TEXT_TASK, COMMENT_ID, "task", "marketing", wc, queue)

        posted_text = wc.run.call_args_list[-1][0][1]["text"]
        assert "Tarea registrada" in posted_text
        queue.enqueue.assert_not_called()


# ── Test handle_smart_reply: instruction intent ────────────────

class TestInstructionFlow:
    def test_instruction_posts_confirmation(self, wc, queue):
        wc.run.return_value = _empty_result()
        handle_smart_reply(COMMENT_TEXT_INSTRUCTION, COMMENT_ID, "instruction", "system", wc, queue)

        wc.run.assert_called_once_with("notion.add_comment", {
            "text": f"{ECHO_PREFIX} Instrucción registrada. Procesando configuración. (comment_id={COMMENT_ID[:8]}...)",
        })
        queue.enqueue.assert_not_called()


# ── Test handle_smart_reply: echo intent ───────────────────────

class TestEchoFlow:
    def test_echo_posts_acknowledgment(self, wc, queue):
        wc.run.return_value = _empty_result()
        handle_smart_reply(COMMENT_TEXT_ECHO, COMMENT_ID, "echo", "system", wc, queue)

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
        handle_smart_reply(COMMENT_TEXT_QUESTION, COMMENT_ID, "question", "system", wc, queue)
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
            _do_poll(wc, queue, r)

        mock_smart.assert_called_once()
        args = mock_smart.call_args[0]
        assert args[0] == COMMENT_TEXT_QUESTION  # comment_text
        assert args[1] == COMMENT_ID             # comment_id
        assert args[2] == "question"             # intent
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
            _do_poll(wc, queue, r)

        mock_smart.assert_not_called()
