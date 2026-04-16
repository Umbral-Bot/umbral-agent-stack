"""
Tests for tournament.run handler.
"""

import pytest
from unittest.mock import patch, call

LLM_PATCH = "worker.tasks.tournament.handle_llm_generate"


def _make_llm_result(text: str = "Generated text", model: str = "gpt-5.4"):
    return {
        "text": text,
        "model": model,
        "usage": {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
    }


def _make_discovery_result(n: int = 3):
    lines = [f"{i+1}. Approach {chr(64+i)}: Description of approach {chr(64+i)}" for i in range(1, n + 1)]
    return _make_llm_result("\n".join(lines))


def _make_proposal(idx: int, approach: str):
    return _make_llm_result(
        f"Full proposal for {approach}: This approach involves..."
    )


def _make_debate(idx: int, approach: str):
    return _make_llm_result(
        f"Rebuttal from contestant #{idx} ({approach}): My approach is better because..."
    )


def _make_verdict(winner_id: int = 2):
    return _make_llm_result(
        f"| Approach | Strengths | Weaknesses | Risk | Fit |\n"
        f"|----------|-----------|------------|------|-----|\n"
        f"| A | Fast | Limited | Low | Good |\n"
        f"| B | Complete | Slow | Med | Best |\n"
        f"| C | Cheap | Fragile | High | OK |\n\n"
        f"**Winner: Contestant #{winner_id}** (confidence: high)\n"
        f"Recommendation: Go with approach B."
    )


def _make_escalate_verdict():
    return _make_llm_result(
        "| Approach | Strengths | Weaknesses | Risk | Fit |\n"
        "|----------|-----------|------------|------|-----|\n"
        "| A | Fast | Limited | Low | Good |\n"
        "| B | Complete | Slow | Med | Good |\n\n"
        "The trade-offs are genuine and close. ESCALATE to human decision-maker."
    )


class TestTournamentRun:
    """Tests for handle_tournament_run."""

    @patch(LLM_PATCH)
    def test_basic_tournament_with_auto_discovery(self, mock_llm):
        """Full tournament: discovery + 3 proposals + 3 debates + verdict."""
        from worker.tasks.tournament import handle_tournament_run

        mock_llm.side_effect = [
            _make_discovery_result(3),        # discovery
            _make_proposal(1, "A"),           # proposal 1
            _make_proposal(2, "B"),           # proposal 2
            _make_proposal(3, "C"),           # proposal 3
            _make_debate(1, "A"),             # debate 1
            _make_debate(2, "B"),             # debate 2
            _make_debate(3, "C"),             # debate 3
            _make_verdict(2),                 # judge
        ]

        result = handle_tournament_run({"challenge": "Best auth for BIM app?"})

        assert result["challenge"] == "Best auth for BIM app?"
        assert len(result["approaches"]) == 3
        assert len(result["debate"]) == 3
        assert result["verdict"]["winner_id"] == 2
        assert result["verdict"]["escalate"] is False
        assert result["meta"]["total_llm_calls"] == 8  # 1 discovery + 3 proposals + 3 debates + 1 judge
        assert mock_llm.call_count == 8

    @patch(LLM_PATCH)
    def test_predefined_approaches_skip_discovery(self, mock_llm):
        """Pre-defined approaches skip the discovery LLM call."""
        from worker.tasks.tournament import handle_tournament_run

        mock_llm.side_effect = [
            _make_proposal(1, "OAuth2"),
            _make_proposal(2, "SAML"),
            _make_debate(1, "OAuth2"),
            _make_debate(2, "SAML"),
            _make_verdict(1),
        ]

        result = handle_tournament_run({
            "challenge": "SSO for UmbralBIM",
            "approaches": ["OAuth2", "SAML"],
            "num_approaches": 2,
        })

        assert len(result["approaches"]) == 2
        assert result["approaches"][0]["approach_name"] == "OAuth2"
        assert result["approaches"][1]["approach_name"] == "SAML"
        assert result["meta"]["total_llm_calls"] == 5  # no discovery

    @patch(LLM_PATCH)
    def test_no_debate_rounds(self, mock_llm):
        """debate_rounds=0 skips debate entirely."""
        from worker.tasks.tournament import handle_tournament_run

        mock_llm.side_effect = [
            _make_discovery_result(2),
            _make_proposal(1, "A"),
            _make_proposal(2, "B"),
            _make_verdict(1),
        ]

        result = handle_tournament_run({
            "challenge": "Frontend framework choice",
            "num_approaches": 2,
            "debate_rounds": 0,
        })

        assert len(result["debate"]) == 0
        assert result["meta"]["total_llm_calls"] == 4  # discovery + 2 proposals + judge

    @patch(LLM_PATCH)
    def test_escalate_verdict(self, mock_llm):
        """Judge can escalate instead of picking a winner."""
        from worker.tasks.tournament import handle_tournament_run

        mock_llm.side_effect = [
            _make_proposal(1, "React"),
            _make_proposal(2, "Vue"),
            _make_debate(1, "React"),
            _make_debate(2, "Vue"),
            _make_escalate_verdict(),
        ]

        result = handle_tournament_run({
            "challenge": "Frontend for dashboard",
            "approaches": ["React", "Vue"],
            "num_approaches": 2,
        })

        assert result["verdict"]["escalate"] is True
        assert result["verdict"]["winner_id"] is None

    @patch(LLM_PATCH)
    def test_multi_model_tournament(self, mock_llm):
        """Different models for each contestant."""
        from worker.tasks.tournament import handle_tournament_run

        mock_llm.side_effect = [
            _make_llm_result("Proposal from GPT", model="gpt-5.4"),
            _make_llm_result("Proposal from Claude", model="claude-sonnet-4-6"),
            _make_llm_result("Debate GPT", model="gpt-5.4"),
            _make_llm_result("Debate Claude", model="claude-sonnet-4-6"),
            _make_verdict(1),
        ]

        result = handle_tournament_run({
            "challenge": "API design",
            "approaches": ["REST", "GraphQL"],
            "num_approaches": 2,
            "models": ["azure_foundry", "claude_pro"],
            "judge_model": "claude_opus",
        })

        assert len(result["approaches"]) == 2
        assert len(result["meta"]["models_used"]) >= 1

    def test_empty_challenge_raises(self):
        """Empty challenge must raise ValueError."""
        from worker.tasks.tournament import handle_tournament_run

        with pytest.raises(ValueError, match="challenge"):
            handle_tournament_run({"challenge": ""})

    def test_missing_challenge_raises(self):
        """Missing challenge must raise ValueError."""
        from worker.tasks.tournament import handle_tournament_run

        with pytest.raises(ValueError, match="challenge"):
            handle_tournament_run({})

    @patch(LLM_PATCH)
    def test_num_approaches_clamped(self, mock_llm):
        """num_approaches < 2 gets clamped to 2, > 5 gets clamped to 5."""
        from worker.tasks.tournament import handle_tournament_run

        # Test lower bound: 1 → 2
        mock_llm.side_effect = [
            _make_discovery_result(2),
            _make_proposal(1, "A"),
            _make_proposal(2, "B"),
            _make_debate(1, "A"),
            _make_debate(2, "B"),
            _make_verdict(1),
        ]

        result = handle_tournament_run({
            "challenge": "Test clamping",
            "num_approaches": 1,
        })
        assert len(result["approaches"]) == 2

    @patch(LLM_PATCH)
    def test_approach_names_in_proposals(self, mock_llm):
        """Each proposal carries its approach_name."""
        from worker.tasks.tournament import handle_tournament_run

        mock_llm.side_effect = [
            _make_proposal(1, "Microservices"),
            _make_proposal(2, "Monolith"),
            _make_proposal(3, "Serverless"),
            _make_debate(1, "Micro"),
            _make_debate(2, "Mono"),
            _make_debate(3, "Serverless"),
            _make_verdict(3),
        ]

        result = handle_tournament_run({
            "challenge": "Architecture for BIM platform",
            "approaches": ["Microservices", "Monolith", "Serverless"],
        })

        names = [a["approach_name"] for a in result["approaches"]]
        assert names == ["Microservices", "Monolith", "Serverless"]

    @patch(LLM_PATCH)
    def test_meta_tracks_duration_and_calls(self, mock_llm):
        """Meta section contains duration and call counts."""
        from worker.tasks.tournament import handle_tournament_run

        mock_llm.side_effect = [
            _make_proposal(1, "A"),
            _make_proposal(2, "B"),
            _make_verdict(1),
        ]

        result = handle_tournament_run({
            "challenge": "Quick test",
            "approaches": ["A", "B"],
            "num_approaches": 2,
            "debate_rounds": 0,
        })

        assert result["meta"]["total_llm_calls"] == 3
        assert result["meta"]["total_duration_ms"] >= 0
        assert isinstance(result["meta"]["models_used"], list)


class TestParseApproachList:
    """Tests for _parse_approach_list helper."""

    def test_numbered_list_with_descriptions(self):
        from worker.tasks.tournament import _parse_approach_list

        text = "1. OAuth2: Standard token-based\n2. SAML: Enterprise SSO\n3. Custom JWT: Lightweight"
        result = _parse_approach_list(text, 3)
        assert result == ["OAuth2", "SAML", "Custom JWT"]

    def test_fallback_for_empty_text(self):
        from worker.tasks.tournament import _parse_approach_list

        result = _parse_approach_list("", 3)
        assert result == ["Approach 1", "Approach 2", "Approach 3"]

    def test_partial_parse_fills_gaps(self):
        from worker.tasks.tournament import _parse_approach_list

        text = "1. React: Modern SPA"
        result = _parse_approach_list(text, 3)
        assert result[0] == "React"
        assert result[1] == "Approach 2"
        assert result[2] == "Approach 3"

    def test_extra_lines_truncated(self):
        from worker.tasks.tournament import _parse_approach_list

        text = "1. A: desc\n2. B: desc\n3. C: desc\n4. D: desc"
        result = _parse_approach_list(text, 2)
        assert len(result) == 2
        assert result == ["A", "B"]


class TestExtractWinnerId:
    """Tests for _extract_winner_id helper."""

    def test_extracts_from_winner_contestant(self):
        from worker.tasks.tournament import _extract_winner_id

        props = [{"id": 1, "approach_name": "A"}, {"id": 2, "approach_name": "B"}]
        text = "Analysis complete. **Winner: Contestant #2** with high confidence."
        assert _extract_winner_id(text, props) == 2

    def test_extracts_from_ganador(self):
        from worker.tasks.tournament import _extract_winner_id

        props = [{"id": 1, "approach_name": "React"}, {"id": 2, "approach_name": "Vue"}]
        text = "El ganador es Contestant #1 (React)."
        assert _extract_winner_id(text, props) == 1

    def test_returns_none_when_no_winner(self):
        from worker.tasks.tournament import _extract_winner_id

        props = [{"id": 1, "approach_name": "A"}]
        text = "No clear winner found."
        assert _extract_winner_id(text, props) is None

    # ------------------------------------------------------------------
    # Multilingual / loose-wording cases (regression for null winner_id
    # when the judge clearly chose a contestant).
    # ------------------------------------------------------------------

    def test_extracts_winner_before_keyword_english(self):
        """'Contestant #2 is the winner' — id appears BEFORE the keyword."""
        from worker.tasks.tournament import _extract_winner_id

        props = [{"id": 1, "approach_name": "A"}, {"id": 2, "approach_name": "B"}]
        text = "After review, Contestant #2 is the winner with high confidence."
        assert _extract_winner_id(text, props) == 2

    def test_extracts_with_winning_variant(self):
        """'The winning approach is #3' — variant 'winning' instead of 'winner'."""
        from worker.tasks.tournament import _extract_winner_id

        props = [
            {"id": 1, "approach_name": "X"},
            {"id": 2, "approach_name": "Y"},
            {"id": 3, "approach_name": "Z"},
        ]
        text = "The winning approach is #3 because of latency."
        assert _extract_winner_id(text, props) == 3

    def test_extracts_with_recommend(self):
        """'I recommend Contestant 2' — verb of recommendation, no '#'."""
        from worker.tasks.tournament import _extract_winner_id

        props = [{"id": 1, "approach_name": "A"}, {"id": 2, "approach_name": "B"}]
        text = "Both are solid, but I recommend Contestant 2 for production."
        assert _extract_winner_id(text, props) == 2

    def test_extracts_with_best_approach(self):
        """'The best approach is #1' — recommendation phrase."""
        from worker.tasks.tournament import _extract_winner_id

        props = [{"id": 1, "approach_name": "A"}, {"id": 2, "approach_name": "B"}]
        text = "The best approach is #1 by a clear margin."
        assert _extract_winner_id(text, props) == 1

    def test_extracts_with_recomiendo_es(self):
        """Spanish: 'Recomiendo la propuesta 2' (sin '#', sustantivo en español)."""
        from worker.tasks.tournament import _extract_winner_id

        props = [{"id": 1, "approach_name": "A"}, {"id": 2, "approach_name": "B"}]
        text = "Tras analizar todo, recomiendo la propuesta 2 por su robustez."
        assert _extract_winner_id(text, props) == 2

    def test_extracts_with_mejor_opcion_es(self):
        """Spanish: 'la mejor opción es el enfoque #3'."""
        from worker.tasks.tournament import _extract_winner_id

        props = [
            {"id": 1, "approach_name": "A"},
            {"id": 2, "approach_name": "B"},
            {"id": 3, "approach_name": "C"},
        ]
        text = "Considerando trade-offs, la mejor opción es el enfoque #3."
        assert _extract_winner_id(text, props) == 3

    def test_extracts_with_elijo_es(self):
        """Spanish verb: 'Elijo Contestant #1'."""
        from worker.tasks.tournament import _extract_winner_id

        props = [{"id": 1, "approach_name": "A"}, {"id": 2, "approach_name": "B"}]
        text = "Elijo Contestant #1 como ganadora."
        assert _extract_winner_id(text, props) == 1

    def test_extracts_with_vencedor_pt(self):
        """Portuguese: 'O vencedor é a proposta 2'."""
        from worker.tasks.tournament import _extract_winner_id

        props = [{"id": 1, "approach_name": "A"}, {"id": 2, "approach_name": "B"}]
        text = "Após o debate, o vencedor é a proposta 2."
        assert _extract_winner_id(text, props) == 2

    def test_extracts_with_recomendo_pt(self):
        """Portuguese: 'Recomendo a abordagem #3'."""
        from worker.tasks.tournament import _extract_winner_id

        props = [
            {"id": 1, "approach_name": "A"},
            {"id": 2, "approach_name": "B"},
            {"id": 3, "approach_name": "C"},
        ]
        text = "Recomendo a abordagem #3 para o caso de uso atual."
        assert _extract_winner_id(text, props) == 3

    def test_extracts_with_melhor_abordagem_pt(self):
        """Portuguese phrase: 'a melhor abordagem é a #2'."""
        from worker.tasks.tournament import _extract_winner_id

        props = [{"id": 1, "approach_name": "A"}, {"id": 2, "approach_name": "B"}]
        text = "Concluo que a melhor abordagem é a #2 pela escalabilidade."
        assert _extract_winner_id(text, props) == 2

    def test_extracts_with_escolho_pt(self):
        """Portuguese verb: 'Escolho Contestant #1'."""
        from worker.tasks.tournament import _extract_winner_id

        props = [{"id": 1, "approach_name": "A"}, {"id": 2, "approach_name": "B"}]
        text = "Escolho Contestant #1 como vencedor."
        assert _extract_winner_id(text, props) == 1

    def test_extracts_with_mixed_language(self):
        """Mixed wording (markdown + bilingual): 'Verdict: ganadora is Contestant #2'."""
        from worker.tasks.tournament import _extract_winner_id

        props = [{"id": 1, "approach_name": "A"}, {"id": 2, "approach_name": "B"}]
        text = "**Final Verdict:** la ganadora is Contestant #2 (confidence: high)."
        assert _extract_winner_id(text, props) == 2

    def test_extracts_by_approach_name_when_no_id(self):
        """Falls back to approach_name when no numeric id is present."""
        from worker.tasks.tournament import _extract_winner_id

        props = [
            {"id": 1, "approach_name": "OAuth2"},
            {"id": 2, "approach_name": "SAML"},
        ]
        text = "The winner is OAuth2 — better DX and ecosystem."
        assert _extract_winner_id(text, props) == 1

    # ------------------------------------------------------------------
    # Negation / ambiguous cases — must return None, never invent.
    # ------------------------------------------------------------------

    def test_returns_none_with_negation_then_id(self):
        """'No clear winner. Contestant #2 had merit.' → None (negation wins)."""
        from worker.tasks.tournament import _extract_winner_id

        props = [{"id": 1, "approach_name": "A"}, {"id": 2, "approach_name": "B"}]
        text = "No clear winner emerged. Contestant #2 had merit but so did #1."
        assert _extract_winner_id(text, props) is None

    def test_returns_none_with_no_hay_ganador_es(self):
        """Spanish negation: 'No hay ganador claro'."""
        from worker.tasks.tournament import _extract_winner_id

        props = [{"id": 1, "approach_name": "A"}, {"id": 2, "approach_name": "B"}]
        text = "No hay ganador claro; ambas propuestas son válidas. Contestant #1 destaca."
        assert _extract_winner_id(text, props) is None

    def test_returns_none_with_nao_ha_vencedor_pt(self):
        """Portuguese negation: 'Não há vencedor'."""
        from worker.tasks.tournament import _extract_winner_id

        props = [{"id": 1, "approach_name": "A"}, {"id": 2, "approach_name": "B"}]
        text = "Não há vencedor definido neste round. Contestant #1 ficou bom."
        assert _extract_winner_id(text, props) is None

    def test_returns_none_with_tied_verdict(self):
        """English: 'tied' / 'too close to call' → None."""
        from worker.tasks.tournament import _extract_winner_id

        props = [{"id": 1, "approach_name": "A"}, {"id": 2, "approach_name": "B"}]
        text = "The two approaches are tied — too close to call. Contestant #2 has slight edge."
        assert _extract_winner_id(text, props) is None

    def test_ignores_invalid_ids(self):
        """If only an out-of-range id appears near the keyword, return None."""
        from worker.tasks.tournament import _extract_winner_id

        props = [{"id": 1, "approach_name": "A"}, {"id": 2, "approach_name": "B"}]
        text = "Winner: Contestant #7 (typo) — please escalate."
        assert _extract_winner_id(text, props) is None

    def test_handles_empty_text(self):
        from worker.tasks.tournament import _extract_winner_id

        props = [{"id": 1, "approach_name": "A"}]
        assert _extract_winner_id("", props) is None
        assert _extract_winner_id("   ", props) is None
