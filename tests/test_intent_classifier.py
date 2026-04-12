"""
Tests for dispatcher/intent_classifier.py

All tests are pure — no Redis, no mocks, no I/O.
Run with:
    python -m pytest tests/test_intent_classifier.py -v
"""

import pytest

from dispatcher.intent_classifier import (
    IntentResult,
    classify_intent,
    route_to_team,
    build_envelope,
)


# ---------------------------------------------------------------------------
# classify_intent
# ---------------------------------------------------------------------------


class TestClassifyIntent:
    """Tests for intent classification heuristics."""

    # -- Questions --

    def test_question_with_question_mark(self):
        r = classify_intent("¿Cuál es el estado del proyecto?")
        assert r.intent == "question"
        assert r.confidence == "high"

    def test_question_english(self):
        r = classify_intent("What is the current status?")
        assert r.intent == "question"

    def test_question_mark_midsentence(self):
        r = classify_intent("No sé, ¿qué opinas?")
        assert r.intent == "question"

    # -- Tasks --

    def test_task_verb_first_crea(self):
        r = classify_intent("Crea un post para LinkedIn")
        assert r.intent == "task"
        assert r.confidence == "high"

    def test_task_verb_first_busca(self):
        r = classify_intent("Busca información sobre BIM ")
        assert r.intent == "task"
        assert r.confidence == "high"

    def test_task_verb_first_english(self):
        r = classify_intent("Create a marketing report")
        assert r.intent == "task"
        assert r.confidence == "high"

    def test_task_verb_anywhere(self):
        r = classify_intent("Necesito que alguien revisa el pipeline")
        assert r.intent == "task"
        assert r.confidence == "medium"

    def test_task_genera(self):
        r = classify_intent("Genera un reporte de SEO")
        assert r.intent == "task"

    # -- Instructions --

    def test_instruction_verb_first(self):
        r = classify_intent("Configura el dashboard cada 5 min")
        assert r.intent == "instruction"
        assert r.confidence == "high"

    def test_instruction_cambia(self):
        r = classify_intent("Cambia el intervalo del poller")
        assert r.intent == "instruction"

    def test_instruction_verb_anywhere(self):
        r = classify_intent("Hay que actualiza la frecuencia del cron")
        assert r.intent == "instruction"
        assert r.confidence == "medium"

    def test_instruction_english(self):
        r = classify_intent("Enable the LiteLLM proxy")
        assert r.intent == "instruction"

    def test_instruction_correction_language(self):
        r = classify_intent(
            "Rick, el caso Kris sigue abierto: baja el lenguaje a lectura aplicada"
        )
        assert r.intent == "instruction"

    def test_instruction_short_review_feedback_no_se_entiende(self):
        r = classify_intent("no se entiende")
        assert r.intent == "instruction"
        assert r.confidence == "medium"

    def test_instruction_short_review_feedback_trabajo_incompleto(self):
        r = classify_intent("trabajo incompleto")
        assert r.intent == "instruction"
        assert r.confidence == "medium"

    # -- Echo (fallback) --

    def test_echo_unrecognized_text(self):
        r = classify_intent("xyz abc 123 qwerty")
        assert r.intent == "echo"
        assert r.confidence == "low"

    def test_echo_empty_string(self):
        r = classify_intent("")
        assert r.intent == "echo"

    def test_echo_only_whitespace(self):
        r = classify_intent("   \n\t  ")
        assert r.intent == "echo"

    # -- Priority: question wins over task verbs --

    def test_question_beats_task_verb(self):
        """If text has both '?' and task verb, question wins."""
        r = classify_intent("¿Puedes buscar información?")
        assert r.intent == "question"

    def test_mojibake_question_marks_inside_words_do_not_force_question(self):
        r = classify_intent(
            "regularizaci?n del embudo: corrige esto y d?jalo trazable"
        )
        assert r.intent == "instruction"


# ---------------------------------------------------------------------------
# route_to_team
# ---------------------------------------------------------------------------


class TestRouteToTeam:
    """Tests for team routing."""

    # -- Direct @mentions --

    def test_mention_marketing(self):
        assert route_to_team("@marketing crea un post") == "marketing"

    def test_mention_advisory(self):
        assert route_to_team("@advisory revisa finanzas") == "advisory"

    def test_mention_lab(self):
        assert route_to_team("@lab experimenta con esto") == "lab"

    def test_mention_case_insensitive(self):
        assert route_to_team("@MARKETING plan de contenido") == "marketing"

    # -- Keyword scoring --

    def test_keywords_marketing(self):
        assert route_to_team("Crea un post para Instagram con copywriting") == "marketing"

    def test_keywords_advisory(self):
        assert route_to_team("Revisa el presupuesto y las finanzas") == "advisory"

    def test_keywords_system(self):
        assert route_to_team("Haz deploy del worker en el pipeline CI") == "system"

    def test_keywords_improvement(self):
        assert route_to_team("Optimizar el benchmark del ciclo OODA") == "improvement"

    def test_keywords_lab(self):
        assert route_to_team("Lanza un experimento en el sandbox") == "lab"

    # -- Fallback --

    def test_fallback_system(self):
        assert route_to_team("xyz abc 123 qwerty") == "system"

    def test_empty_text_fallback(self):
        assert route_to_team("") == "system"


# ---------------------------------------------------------------------------
# build_envelope
# ---------------------------------------------------------------------------


class TestBuildEnvelope:
    """Tests for TaskEnvelope construction."""

    def test_envelope_has_required_fields(self):
        intent = IntentResult(intent="task", confidence="high")
        env = build_envelope("Crea algo", "comment-abc-123", intent, "marketing")

        assert "schema_version" in env
        assert "task_id" in env
        assert "team" in env
        assert "task" in env
        assert "input" in env
        assert env["schema_version"] == "0.1"

    def test_question_envelope(self):
        intent = IntentResult(intent="question", confidence="high")
        env = build_envelope("¿Qué pasa?", "cmt-123", intent, "system")

        assert env["task_type"] == "research"
        assert env["task"] == "notion.add_comment"
        assert "Investigando tu pregunta" in env["input"]["text"]

    def test_task_envelope(self):
        intent = IntentResult(intent="task", confidence="high")
        env = build_envelope("Crea un post", "cmt-456", intent, "marketing")

        assert env["team"] == "marketing"
        assert env["task_type"] == "general"
        assert "equipo [marketing]" in env["input"]["text"]
        assert env["input"]["original_request"] == "Crea un post"

    def test_instruction_envelope_forces_system_team(self):
        intent = IntentResult(intent="instruction", confidence="high")
        env = build_envelope("Configura X", "cmt-789", intent, "marketing")

        # Instructions always go to system team regardless of routing
        assert env["team"] == "system"
        assert env["task_type"] == "instruction"

    def test_echo_envelope_backward_compat(self):
        intent = IntentResult(intent="echo", confidence="low")
        env = build_envelope("xyz", "cmt-000", intent, "system")

        # Echo envelopes now carry empty text — no acknowledgment needed
        assert env["input"]["text"] == ""
        assert env["task"] == "notion.add_comment"

    def test_source_metadata(self):
        intent = IntentResult(intent="task", confidence="high")
        env = build_envelope("Haz algo", "comment-full-id", intent, "lab")

        assert env["source"] == "notion_poller"
        assert env["source_comment_id"] == "comment-full-id"
