"""
Tasks: Tournament multi-agent pattern.

- tournament.run: Divergent exploration → debate → consolidation.

Rick identifies N distinct approaches to a challenge, develops each fully
via separate LLM calls (optionally with different models), runs an optional
debate round where each contestant sees rival proposals, then a judge
consolidates into a comparison table with a recommendation.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from .llm import handle_llm_generate

logger = logging.getLogger("worker.tasks.tournament")

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

DIVERGE_SYSTEM = (
    "You are Contestant #{idx} in a tournament of ideas.\n"
    "Your assigned approach: **{approach_name}**\n\n"
    "Rules:\n"
    "- Develop this specific approach FULLY — not an outline, a complete proposal.\n"
    "- Be concrete: include implementation steps, trade-offs, and expected outcomes.\n"
    "- Do NOT mention other possible approaches. Focus only on yours.\n"
    "- Write in the same language as the challenge."
)

APPROACH_DISCOVERY_SYSTEM = (
    "You are an expert strategist. Given a challenge, identify exactly {n} "
    "FUNDAMENTALLY DIFFERENT approaches to solve it.\n\n"
    "Rules:\n"
    "- Each approach must be a genuinely distinct strategy, not a variation.\n"
    "- Return ONLY a numbered list: 1. Approach Name: one-line description\n"
    "- No preamble, no extra text.\n"
    "- Write in the same language as the challenge."
)

DEBATE_SYSTEM = (
    "You are Contestant #{idx} ({approach_name}).\n"
    "You previously proposed:\n---\n{own_proposal}\n---\n\n"
    "Here are rival proposals:\n{rival_proposals}\n\n"
    "Rules:\n"
    "- Argue why YOUR approach is superior with specific evidence.\n"
    "- Acknowledge any genuine advantages of rival proposals.\n"
    "- Identify risks or blind spots in rivals.\n"
    "- Be concise and evidence-based.\n"
    "- Write in the same language as the original challenge."
)

JUDGE_SYSTEM = (
    "You are the Tournament Judge.\n"
    "A challenge was explored through {n} distinct approaches"
    "{debate_note}.\n\n"
    "Your job:\n"
    "1. Build a comparison table with columns: Approach | Strengths | Weaknesses | Risk | Fit\n"
    "2. State the WINNER and confidence level (high/medium/low).\n"
    "3. If trade-offs are genuine and close, say \"ESCALATE\" instead of picking a winner.\n"
    "4. Provide a 2-3 sentence final recommendation.\n"
    "5. Write in the same language as the challenge.\n\n"
    "Proposals:\n{proposals}\n"
    "{debate_section}"
)


# ---------------------------------------------------------------------------
# Core handler
# ---------------------------------------------------------------------------


def handle_tournament_run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tournament: divergent exploration + debate + consolidation.

    Input:
        challenge (str, required): The problem/task to explore.
        num_approaches (int, optional): Number of distinct approaches (default: 3, max: 5).
        approaches (list[str], optional): Pre-defined approach names. If omitted,
            the LLM discovers them automatically.
        models (list[str], optional): LLM models for each contestant.
            Cycles if fewer than num_approaches. Default: ["azure_foundry"].
        judge_model (str, optional): Model for the consolidation step
            (default: same as first contestant model).
        temperature (float, optional): Sampling temp for contestants (default: 0.9).
        max_tokens (int, optional): Token budget per LLM call (default: 2048).
        debate_rounds (int, optional): Number of debate rounds (default: 1, 0 to skip).

    Returns:
        challenge: original challenge text
        approaches: list of {id, approach_name, proposal, model_used}
        debate: list of {id, rebuttal, model_used} (empty if debate_rounds=0)
        verdict: {comparison_table, recommendation, winner_id, confidence, escalate}
        meta: {total_llm_calls, total_duration_ms, models_used}
    """
    challenge = str(input_data.get("challenge", "")).strip()
    if not challenge:
        raise ValueError("'challenge' is required and cannot be empty")

    num_approaches = min(int(input_data.get("num_approaches", 3)), 5)
    if num_approaches < 2:
        num_approaches = 2

    predefined_approaches: Optional[List[str]] = input_data.get("approaches")
    models_raw: List[str] = input_data.get("models") or ["azure_foundry"]
    judge_model = str(input_data.get("judge_model", models_raw[0]))
    temperature = float(input_data.get("temperature", 0.9))
    max_tokens = int(input_data.get("max_tokens", 2048))
    debate_rounds = int(input_data.get("debate_rounds", 1))

    t0 = time.monotonic()
    llm_calls = 0

    # ------------------------------------------------------------------
    # Step 1: Discover approaches (or use predefined)
    # ------------------------------------------------------------------
    if predefined_approaches and len(predefined_approaches) >= num_approaches:
        approach_names = predefined_approaches[:num_approaches]
    else:
        logger.info("Discovering %d approaches for challenge", num_approaches)
        discovery = handle_llm_generate({
            "prompt": challenge,
            "system": APPROACH_DISCOVERY_SYSTEM.format(n=num_approaches),
            "model": judge_model,
            "max_tokens": 512,
            "temperature": 0.7,
        })
        llm_calls += 1
        approach_names = _parse_approach_list(discovery.get("text", ""), num_approaches)

    logger.info("Tournament approaches: %s", approach_names)

    # ------------------------------------------------------------------
    # Step 2: Develop each approach fully
    # ------------------------------------------------------------------
    proposals: List[Dict[str, Any]] = []
    for i, approach_name in enumerate(approach_names):
        model = models_raw[i % len(models_raw)]
        logger.info("Developing approach %d/%d: %s (model=%s)", i + 1, num_approaches, approach_name, model)

        result = handle_llm_generate({
            "prompt": challenge,
            "system": DIVERGE_SYSTEM.format(idx=i + 1, approach_name=approach_name),
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
        })
        llm_calls += 1

        proposals.append({
            "id": i + 1,
            "approach_name": approach_name,
            "proposal": result.get("text", ""),
            "model_used": result.get("model", model),
        })

    # ------------------------------------------------------------------
    # Step 3: Debate rounds (optional)
    # ------------------------------------------------------------------
    debate_log: List[Dict[str, Any]] = []
    if debate_rounds > 0:
        for round_num in range(debate_rounds):
            logger.info("Debate round %d/%d", round_num + 1, debate_rounds)
            for i, prop in enumerate(proposals):
                rivals = _format_rivals(proposals, exclude_id=prop["id"])
                model = models_raw[i % len(models_raw)]

                result = handle_llm_generate({
                    "prompt": challenge,
                    "system": DEBATE_SYSTEM.format(
                        idx=prop["id"],
                        approach_name=prop["approach_name"],
                        own_proposal=prop["proposal"],
                        rival_proposals=rivals,
                    ),
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                })
                llm_calls += 1

                debate_log.append({
                    "id": prop["id"],
                    "round": round_num + 1,
                    "approach_name": prop["approach_name"],
                    "rebuttal": result.get("text", ""),
                    "model_used": result.get("model", model),
                })

    # ------------------------------------------------------------------
    # Step 4: Judge consolidation
    # ------------------------------------------------------------------
    logger.info("Judge consolidating (model=%s)", judge_model)
    proposals_text = _format_all_proposals(proposals)
    debate_section = ""
    debate_note = ""
    if debate_log:
        debate_note = " followed by a debate"
        debate_section = "\nDebate rebuttals:\n" + _format_debate(debate_log)

    judge_result = handle_llm_generate({
        "prompt": challenge,
        "system": JUDGE_SYSTEM.format(
            n=num_approaches,
            debate_note=debate_note,
            proposals=proposals_text,
            debate_section=debate_section,
        ),
        "model": judge_model,
        "max_tokens": max_tokens,
        "temperature": 0.3,
    })
    llm_calls += 1

    verdict_text = judge_result.get("text", "")
    escalate = "ESCALATE" in verdict_text.upper()
    winner_id = _extract_winner_id(verdict_text, proposals) if not escalate else None

    duration_ms = (time.monotonic() - t0) * 1000.0

    models_used = list({p["model_used"] for p in proposals})
    models_used.append(judge_result.get("model", judge_model))
    models_used = list(set(models_used))

    return {
        "challenge": challenge,
        "approaches": proposals,
        "debate": debate_log,
        "verdict": {
            "text": verdict_text,
            "winner_id": winner_id,
            "escalate": escalate,
        },
        "meta": {
            "total_llm_calls": llm_calls,
            "total_duration_ms": round(duration_ms, 1),
            "models_used": models_used,
        },
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_approach_list(text: str, expected: int) -> List[str]:
    """Parse numbered list of approaches from LLM output."""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    approaches = []
    for line in lines:
        # Remove numbering: "1. Approach Name: desc" → "Approach Name"
        cleaned = line.lstrip("0123456789.-) ").strip()
        if ":" in cleaned:
            cleaned = cleaned.split(":", 1)[0].strip()
        if cleaned:
            approaches.append(cleaned)
    # Fallback: if parsing fails, generate generic names
    while len(approaches) < expected:
        approaches.append(f"Approach {len(approaches) + 1}")
    return approaches[:expected]


def _format_rivals(proposals: List[Dict[str, Any]], exclude_id: int) -> str:
    """Format rival proposals for debate context."""
    parts = []
    for p in proposals:
        if p["id"] == exclude_id:
            continue
        parts.append(
            f"### Contestant #{p['id']} — {p['approach_name']}\n{p['proposal']}"
        )
    return "\n\n".join(parts)


def _format_all_proposals(proposals: List[Dict[str, Any]]) -> str:
    """Format all proposals for judge context."""
    parts = []
    for p in proposals:
        parts.append(
            f"### Contestant #{p['id']} — {p['approach_name']}\n{p['proposal']}"
        )
    return "\n\n".join(parts)


def _format_debate(debate_log: List[Dict[str, Any]]) -> str:
    """Format debate rebuttals for judge context."""
    parts = []
    for d in debate_log:
        parts.append(
            f"### Contestant #{d['id']} ({d['approach_name']}) — Round {d['round']}\n"
            f"{d['rebuttal']}"
        )
    return "\n\n".join(parts)


def _extract_winner_id(
    verdict_text: str, proposals: List[Dict[str, Any]]
) -> Optional[int]:
    """Best-effort extraction of winner ID from verdict text."""
    text_lower = verdict_text.lower()
    # Look for "winner: contestant #N" or "winner: Approach Name"
    for p in proposals:
        marker = f"contestant #{p['id']}"
        if marker in text_lower:
            # Check if it's in a "winner" context
            idx = text_lower.find(marker)
            context = text_lower[max(0, idx - 40) : idx]
            if "winner" in context or "ganador" in context:
                return p["id"]
    # Fallback: first contestant mentioned after "winner"
    winner_pos = text_lower.find("winner")
    if winner_pos == -1:
        winner_pos = text_lower.find("ganador")
    if winner_pos >= 0:
        after = text_lower[winner_pos:]
        for p in proposals:
            if f"#{p['id']}" in after[:80]:
                return p["id"]
            if p["approach_name"].lower() in after[:120]:
                return p["id"]
    return None
