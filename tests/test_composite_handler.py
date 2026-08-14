"""
Tests for composite.research_report handler.
"""

import pytest
from unittest.mock import patch, MagicMock

# We patch at the composite module level since it imports from sibling modules
RESEARCH_PATCH = "worker.tasks.composite.handle_research_web"
LLM_PATCH = "worker.tasks.composite.handle_llm_generate"


def _make_research_result(query: str, n: int = 3):
    """Helper: fake research.web response."""
    return {
        "results": [
            {"title": f"Result {i} for {query}", "url": f"https://example.com/{i}", "snippet": f"Snippet {i}"}
            for i in range(1, n + 1)
        ],
        "count": n,
        "engine": "tavily",
    }


def _make_llm_result(text: str = "Generated report"):
    """Helper: fake llm.generate response."""
    return {
        "text": text,
        "model": "gemini-2.5-flash",
        "usage": {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
    }


def _make_query_gen_result(queries: list):
    """Helper: fake LLM response for query generation."""
    text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(queries))
    return _make_llm_result(text)


class TestCompositeResearchReport:
    """Tests for handle_composite_research_report."""

    @patch(LLM_PATCH)
    @patch(RESEARCH_PATCH)
    def test_topic_generates_queries_and_report(self, mock_research, mock_llm):
        """Topic without explicit queries → LLM generates queries → research → report."""
        from worker.tasks.composite import handle_composite_research_report

        generated_queries = ["AI market size 2026", "AI enterprise adoption", "AI competitive landscape",
                             "AI regulation trends", "AI investment opportunities"]

        # First LLM call: query generation. Subsequent: report generation.
        mock_llm.side_effect = [
            _make_query_gen_result(generated_queries),
            _make_llm_result("# Market Report\n\n## Resumen Ejecutivo\nGreat findings."),
        ]
        mock_research.return_value = _make_research_result("test", 3)

        result = handle_composite_research_report({"topic": "AI market trends 2026"})

        assert "report" in result
        assert "Market Report" in result["report"]
        assert "sources" in result
        assert len(result["sources"]) > 0
        assert "queries_used" in result
        assert len(result["queries_used"]) == 5  # standard depth
        assert result["stats"]["total_sources"] > 0
        assert result["stats"]["research_time_ms"] >= 0
        assert result["stats"]["generation_time_ms"] >= 0

        # LLM called twice: once for query gen, once for report
        assert mock_llm.call_count == 2
        # Research called once per query
        assert mock_research.call_count == 5

    @patch(LLM_PATCH)
    @patch(RESEARCH_PATCH)
    def test_explicit_queries_used_directly(self, mock_research, mock_llm):
        """When queries are provided, skip LLM query generation."""
        from worker.tasks.composite import handle_composite_research_report

        explicit = ["query A", "query B"]
        mock_research.return_value = _make_research_result("test", 2)
        mock_llm.return_value = _make_llm_result("# Report with explicit queries")

        result = handle_composite_research_report({
            "topic": "Test topic",
            "queries": explicit,
        })

        assert result["queries_used"] == explicit
        # LLM called only once (for report, no query generation)
        assert mock_llm.call_count == 1
        assert mock_research.call_count == 2

    @patch(LLM_PATCH)
    @patch(RESEARCH_PATCH)
    def test_depth_controls_query_count(self, mock_research, mock_llm):
        """Depth parameter controls number of generated queries."""
        from worker.tasks.composite import handle_composite_research_report

        for depth, expected_n in [("quick", 3), ("standard", 5), ("deep", 10)]:
            mock_research.reset_mock()
            mock_llm.reset_mock()

            queries = [f"q{i}" for i in range(expected_n)]
            mock_llm.side_effect = [
                _make_query_gen_result(queries),
                _make_llm_result(f"Report for {depth}"),
            ]
            mock_research.return_value = _make_research_result("test", 2)

            result = handle_composite_research_report({"topic": "Test", "depth": depth})

            assert len(result["queries_used"]) == expected_n, f"depth={depth} expected {expected_n} queries"
            assert mock_research.call_count == expected_n

    @patch(LLM_PATCH)
    @patch(RESEARCH_PATCH)
    def test_research_error_does_not_crash(self, mock_research, mock_llm):
        """If some research queries fail, the handler continues with the rest."""
        from worker.tasks.composite import handle_composite_research_report

        # Alternate: success, failure, success
        mock_research.side_effect = [
            _make_research_result("q1", 3),
            RuntimeError("Tavily API down"),
            _make_research_result("q3", 2),
        ]
        mock_llm.side_effect = [
            _make_query_gen_result(["q1", "q2", "q3"]),
            _make_llm_result("# Report with partial data"),
        ]

        result = handle_composite_research_report({"topic": "Test resilience", "depth": "quick"})

        assert "report" in result
        # Sources from q1 (3) + q3 (2) = 5, q2 failed
        assert result["stats"]["total_sources"] == 5
        assert mock_research.call_count == 3

    @patch(LLM_PATCH)
    @patch(RESEARCH_PATCH)
    def test_llm_error_returns_raw_results(self, mock_research, mock_llm):
        """If LLM report generation fails, return raw research data as fallback."""
        from worker.tasks.composite import handle_composite_research_report

        mock_research.return_value = _make_research_result("test", 2)
        # First call (query gen) succeeds, second (report) fails
        mock_llm.side_effect = [
            _make_query_gen_result(["q1", "q2", "q3"]),
            RuntimeError("Gemini API quota exceeded"),
        ]

        result = handle_composite_research_report({"topic": "Test LLM failure", "depth": "quick"})

        assert "report" in result
        assert "LLM generation failed" in result["report"]
        assert "Raw research data" in result["report"]
        assert result["stats"]["total_sources"] > 0

    @patch("worker.tasks.composite.time.sleep")
    @patch(LLM_PATCH)
    @patch(RESEARCH_PATCH)
    def test_report_generation_does_not_retry_transient_error(self, mock_research, mock_llm, mock_sleep):
        """PKG-MACRO-P5-L2-T9 (SHRINK): un solo intento, incluso ante un error
        que antes se consideraba transitorio.

        Antes reintentaba hasta 3 veces. Con un turno de agente de >119s por
        intento, ese reintento era el multiplicador que apiló corridas hasta
        matar al gateway por OOM (acta §12.4). Con el turno ya achicado, si
        falla que falle rápido y visible."""
        from worker.tasks.composite import handle_composite_research_report

        mock_research.return_value = _make_research_result("test", 2)
        mock_llm.side_effect = [
            _make_query_gen_result(["q1", "q2", "q3"]),
            RuntimeError("OpenClaw proxy request failed: timed out"),
        ]

        result = handle_composite_research_report({"topic": "No retry test", "depth": "quick"})

        # Cae al reporte degradado con los datos crudos, sin reintentar.
        assert "LLM generation failed" in result["report"]
        assert result["stats"]["report_generation_attempts"] == 1
        # 1 llamada de queries + 1 sola de reporte. Nada más.
        assert mock_llm.call_count == 2
        mock_sleep.assert_not_called()

    def test_report_generation_max_attempts_is_one(self):
        """Guardia sobre la constante: si alguien la vuelve a subir, que sea
        una decisión consciente — con turnos de ~1 min por intento, reintentar
        es lo que tiró el gateway."""
        from worker.tasks import composite
        assert composite.REPORT_GENERATION_MAX_ATTEMPTS == 1

    @patch(LLM_PATCH)
    @patch(RESEARCH_PATCH)
    def test_empty_topic_raises(self, mock_research, mock_llm):
        """Empty topic raises ValueError."""
        from worker.tasks.composite import handle_composite_research_report

        with pytest.raises(ValueError, match="topic"):
            handle_composite_research_report({"topic": ""})

    @patch(LLM_PATCH)
    @patch(RESEARCH_PATCH)
    def test_language_passed_to_llm(self, mock_research, mock_llm):
        """Language parameter is passed to the report generation prompt."""
        from worker.tasks.composite import handle_composite_research_report

        mock_research.return_value = _make_research_result("test", 1)
        mock_llm.side_effect = [
            _make_query_gen_result(["q1", "q2", "q3"]),
            _make_llm_result("# English Report"),
        ]

        handle_composite_research_report({"topic": "Test", "depth": "quick", "language": "en"})

        # The report generation call (second LLM call) should have "en" in system prompt
        report_call = mock_llm.call_args_list[1]
        system_prompt = report_call[0][0].get("system", "") if report_call[0] else report_call[1].get("system", "")
        # Access via the dict passed to handle_llm_generate
        call_input = mock_llm.call_args_list[1][0][0]
        assert "en" in call_input["system"]

    @patch(LLM_PATCH)
    @patch(RESEARCH_PATCH)
    def test_composite_passes_usage_metadata_to_nested_llm_calls(self, mock_research, mock_llm):
        from worker.tasks.composite import handle_composite_research_report

        mock_research.return_value = _make_research_result("test", 1)
        mock_llm.side_effect = [
            _make_query_gen_result(["q1", "q2", "q3"]),
            _make_llm_result("# Report"),
        ]

        handle_composite_research_report(
            {
                "topic": "Test",
                "depth": "quick",
                "_task_id": "task-xyz",
                "_task_type": "analysis",
                "_source": "openclaw_gateway",
                "_source_kind": "tool_enqueue",
            }
        )

        first_call = mock_llm.call_args_list[0][0][0]
        second_call = mock_llm.call_args_list[1][0][0]
        assert first_call["_task_id"] == "task-xyz"
        assert first_call["_usage_component"] == "composite.research_report.query_generation"
        assert second_call["_source"] == "openclaw_gateway"
        assert second_call["_usage_component"] == "composite.research_report.report_generation"


# ---------------------------------------------------------------------------
# PKG-MACRO-P5-L2-T9 — SHRINK del turno de reporte
# ---------------------------------------------------------------------------
class TestReportShrink:
    """El turno de generación de reporte tardaba >119s, agotaba el timeout del
    proxy y, con el redespacho del dispatcher, apiló corridas hasta matar el
    gateway por OOM (acta §12.4). SHRINK = una sola llamada, más barata:
    menos tokens de salida y research_data acotado."""

    def test_research_data_is_truncated_when_too_long(self):
        from worker.tasks import composite

        long_data = "x" * (composite.REPORT_RESEARCH_DATA_MAX_CHARS * 3)
        payload = composite._build_report_generation_payload(
            topic="t", research_data=long_data, language="es"
        )
        # El prompt lleva plantilla + datos; lo que importa es que los datos
        # no entren enteros y que quede constancia del recorte.
        assert len(payload["prompt"]) < len(long_data)
        assert composite.REPORT_TRUNCATION_NOTICE.strip() in payload["prompt"]

    def test_research_data_under_cap_is_untouched(self):
        """`quick` (medido: ~9.945 chars) entra completo — no se recorta la
        forma que corre el e2e."""
        from worker.tasks import composite

        short_data = "### Query: q\n- **[T](u)**: snippet\n"
        assert len(short_data) < composite.REPORT_RESEARCH_DATA_MAX_CHARS
        payload = composite._build_report_generation_payload(
            topic="t", research_data=short_data, language="es"
        )
        assert short_data in payload["prompt"]
        assert composite.REPORT_TRUNCATION_NOTICE.strip() not in payload["prompt"]

    def test_truncation_cuts_on_a_line_boundary(self):
        """Corta en el salto de línea previo para no dejar una fuente/URL a medias.

        Ojo con cómo se afirma esto: una primera versión de este test asertaba
        `body.endswith("\\n") or body.endswith("s")`, y con datos hechos de
        líneas de "s" eso pasaba **igual con la heurística desactivada** — o
        sea, no probaba nada (verificado mutando el código). Acá se afirma la
        propiedad de verdad: cada línea que sobrevive está entera."""
        from worker.tasks import composite

        line = "- **[Título](https://ejemplo.com/articulo)**: " + ("s" * 200) + "\n"
        many = line * 200  # bien por encima del cap
        truncated = composite._truncate_research_data(many)
        body = truncated.replace(composite.REPORT_TRUNCATION_NOTICE, "")

        # La propiedad real: nada quedó partido — TODAS las líneas que
        # sobreviven están completas, incluida la última. (El corte cae justo
        # antes del "\n", así que el texto no termina en salto de línea: eso
        # es correcto, lo que importa es que ninguna línea quede a medias.)
        kept_lines = body.splitlines()
        assert kept_lines, "no sobrevivió ninguna línea"
        for kept in kept_lines:
            assert kept == line.rstrip("\n"), f"línea partida: {kept[-40:]!r}"

    def test_truncation_without_newlines_still_respects_the_cap(self):
        """Si no hay ningún salto de línea cerca del corte, igual se acota:
        la heurística de línea es una mejora, no un requisito."""
        from worker.tasks import composite

        blob = "x" * (composite.REPORT_RESEARCH_DATA_MAX_CHARS * 2)
        truncated = composite._truncate_research_data(blob)
        body = truncated.replace(composite.REPORT_TRUNCATION_NOTICE, "")
        assert len(body) <= composite.REPORT_RESEARCH_DATA_MAX_CHARS

    def test_report_max_tokens_is_the_new_ceiling(self):
        from worker.tasks import composite

        payload = composite._build_report_generation_payload(
            topic="t", research_data="d", language="es"
        )
        assert payload["max_tokens"] == composite.REPORT_MAX_TOKENS
        # El techo viejo (4096) era lo que empujaba el turno por encima de 119s.
        assert composite.REPORT_MAX_TOKENS <= 1200
        assert composite.REPORT_MAX_TOKENS < 4096

    def test_stats_report_how_many_sources_reached_the_model(self):
        """El sobre no puede afirmar 25 fuentes al lado de un reporte escrito
        con 20. `standard` es el DEFAULT del task y ya recorta."""
        from worker.tasks import composite

        # 25 fuentes con snippets de 500 chars = la forma real de `standard`.
        research = [
            {"query": f"q{i}", "results": [
                {"title": f"Titulo largo de ejemplo {j}",
                 "url": f"https://ejemplo.com/articulo-{i}-{j}",
                 "snippet": "s" * 500}
                for j in range(5)]}
            for i in range(5)
        ]
        data = composite._format_research_data(research)
        assert len(data) > composite.REPORT_RESEARCH_DATA_MAX_CHARS, (
            "el fixture debería superar el cap para ejercitar el recorte"
        )
        sent = composite._count_source_lines(composite._truncate_research_data(data))
        assert sent < 25, "este fixture debe recortarse"
        assert sent > 0

    def test_budget_shrinks_the_report_window_as_time_passes(self):
        """T10: el reporte usa lo que QUEDA del presupuesto, no un techo fijo.
        Sin esto, preámbulo + techo se pasaba de la ventana del dispatcher y
        dejaba turnos huérfanos en el gateway."""
        import time as _t
        from worker.tasks import composite
        from worker.tasks.llm import PROXY_COMPOSITE_TIMEOUT_S

        try:
            # Recién arrancado: el techo manda.
            composite._BUDGET.clear()
            composite._BUDGET["task_timeout_s"] = 300.0
            composite._BUDGET["started_at"] = _t.monotonic()
            assert composite._proxy_timeout_for(PROXY_COMPOSITE_TIMEOUT_S) == PROXY_COMPOSITE_TIMEOUT_S

            # Ya consumido: manda lo que queda, y nunca se pasa de la ventana.
            composite._BUDGET["started_at"] = _t.monotonic() - 200.0
            got = composite._proxy_timeout_for(PROXY_COMPOSITE_TIMEOUT_S)
            assert got < PROXY_COMPOSITE_TIMEOUT_S
            assert 200.0 + got <= 300.0
        finally:
            composite._BUDGET.clear()

    def test_no_budget_left_means_no_call_at_all(self):
        """Si no queda presupuesto NO se arranca el turno: arrancarlo dejaría
        un huérfano corriendo después de que el dispatcher se rindió."""
        import time as _t
        from worker.tasks import composite

        try:
            composite._BUDGET.clear()
            composite._BUDGET["task_timeout_s"] = 300.0
            composite._BUDGET["started_at"] = _t.monotonic() - 295.0
            assert composite._has_budget_for_a_call() is False
            with pytest.raises(composite.ReportGenerationError, match="sin presupuesto"):
                composite._generate_report_with_retry(
                    topic="t", research_data="d", language="es"
                )
        finally:
            composite._BUDGET.clear()

    def test_direct_call_without_budget_uses_the_ceilings(self):
        """Llamada directa al worker (sin dispatcher): no hay presupuesto que
        repartir, así que valen los techos fijos."""
        from worker.tasks import composite
        from worker.tasks.llm import PROXY_COMPOSITE_TIMEOUT_S

        composite._BUDGET.clear()
        assert composite._has_budget_for_a_call() is True
        assert composite._proxy_timeout_for(PROXY_COMPOSITE_TIMEOUT_S) == PROXY_COMPOSITE_TIMEOUT_S
