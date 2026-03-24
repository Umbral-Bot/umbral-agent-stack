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
