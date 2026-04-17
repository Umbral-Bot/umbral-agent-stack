"""
Tasks: Tournament multi-agent pattern.

- tournament.run: Divergent exploration → debate → consolidation.

Rick identifies N distinct approaches to a challenge, develops each fully
via separate LLM calls (optionally with different models), runs an optional
debate round where each contestant sees rival proposals, then a judge
consolidates into a comparison table with a recommendation.
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional, Set

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
    "5. Write items 1-4 in the same language as the challenge.\n\n"
    "FINAL LINE CONTRACT (strict, machine-parsed):\n"
    "After your recommendation, finish the ENTIRE output with EXACTLY ONE\n"
    "of these two lines, on its own line, with no other text after it:\n"
    "  Winner: Contestant #N     (where N is the id of the contestant you chose)\n"
    "  ESCALATE                  (only if trade-offs are genuine and close)\n"
    "This final line MUST be in English and match the format above exactly.\n"
    "Do not add quotes, bullets, punctuation, markdown, translations, emojis,\n"
    "or explanatory text after it. Do not wrap it in a code block.\n\n"
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


# ---------------------------------------------------------------------------
# Verdict parsing helpers
# ---------------------------------------------------------------------------
#
# `_extract_winner_id` separa "ganador explícito" de "veredicto ambiguo":
#   - Si el juez declara un ganador en inglés/español/portugués (o variantes
#     mixtas) con un id válido cerca, devolvemos ese id.
#   - Si el texto está negado ("no clear winner", "no hay ganador", "empate",
#     "tied", "não há vencedor", ...) o el id que aparece no pertenece al
#     conjunto real de propuestas, devolvemos None — nunca inventamos un
#     ganador. La rama ESCALATE se maneja antes en handle_tournament_run.

# Palabras que señalan un ganador o recomendación firme, en en/es/pt.
# Se mantienen como un OR plano para que sea trivial agregar variantes.
_WINNER_KEYWORD_RE = re.compile(
    r"\b("
    # English
    r"winner|winning|wins|won|"
    r"recommend|recommended|recommendation|"
    r"best (?:approach|option|choice|fit)|"
    # Spanish
    r"ganador(?:a)?|vencedor(?:a)?|campe[oó]n|"
    r"recomiendo|recomienda|recomendad[oa]|"
    r"elijo|elegid[oa]|escojo|"
    r"mejor (?:opci[oó]n|enfoque|propuesta)|"
    # Portuguese
    r"vencedor(?:a)?|campe[aã]o|"
    r"recomendo|recomendad[oa]|"
    r"escolho|escolhid[oa]|"
    r"melhor (?:abordagem|op[cç][aã]o|escolha)"
    r")\b",
    re.IGNORECASE,
)

# Frases de negación que invalidan un veredicto cercano.
_NEGATION_RE = re.compile(
    r"\b("
    r"no clear|no winner|no hay (?:ganador|vencedor|claro)|"
    r"ning[uú]n[oa]?|"
    r"n[ãa]o (?:h[aá]|consigo|temos|posso)|"
    r"sem (?:ganhador|vencedor|claro)|"
    r"cannot determine|unable to (?:determine|pick|decide)|"
    r"no se puede (?:determinar|elegir)|"
    r"empate|tie|tied|"
    r"too close to call|demasiado parejo"
    r")\b",
    re.IGNORECASE,
)

# Captura un id de contestant. Acepta sustantivos en en/es/pt como prefijo
# opcional ("contestant", "approach", "propuesta", "enfoque", "proposta",
# "opción", "opção"...) y `#` opcional.
# El lookbehind `(?<![A-Za-z])` evita capturar dígitos pegados a una palabra
# (p.ej. "OAuth2" no debe parsearse como id=2).
_CONTESTANT_NUM_RE = re.compile(
    r"(?:contestant|approach|proposal|option|"
    r"propuesta|enfoque|opci[oó]n|n[uú]mero|"
    r"proposta|op[cç][aã]o)?\s*"
    r"#?\s*(?<![A-Za-z])(\d+)",
    re.IGNORECASE,
)


def _extract_winner_id(
    verdict_text: str, proposals: List[Dict[str, Any]]
) -> Optional[int]:
    """
    Best-effort, multilingual extraction of the winner id from the judge's verdict.

    Maneja variantes en inglés, español y portugués, además de wording mixto
    (p.ej. "Contestant #2 is the winner", "El ganador es la propuesta 2",
    "Recomiendo el enfoque 3", "Vencedor: Contestant #1"). Devuelve None
    cuando el texto está negado/empatado o cuando ningún id válido aparece
    en una ventana razonable alrededor del keyword — nunca elige por defecto.
    """
    if not verdict_text or not proposals:
        return None

    valid_ids: Set[int] = {p["id"] for p in proposals}
    name_to_id = {
        p["approach_name"].strip().lower(): p["id"]
        for p in proposals
        if p.get("approach_name")
    }

    text_lc = verdict_text.lower()

    # Recorremos cada hit de keyword en orden. El primero que pase la guarda
    # de negación y aporte un id válido define el ganador.
    for m in _WINNER_KEYWORD_RE.finditer(text_lc):
        kw_start, kw_end = m.start(), m.end()

        # Negation guard: ~50 chars antes del keyword + el keyword mismo,
        # para que negaciones como "no hay ganador" o "sem vencedor" — que
        # incluyen el sustantivo — queden capturadas en la misma ventana.
        preface = text_lc[max(0, kw_start - 50): kw_end]
        if _NEGATION_RE.search(preface):
            continue

        # 1) Id explícito DESPUÉS del keyword (caso típico "Winner: #2").
        window_after = text_lc[kw_end: kw_end + 120]
        winner_id = _first_valid_contestant_id(window_after, valid_ids)
        if winner_id is not None:
            return winner_id

        # 2) Id explícito ANTES del keyword (caso "Contestant #2 wins").
        window_before = text_lc[max(0, kw_start - 80): kw_start]
        winner_id = _last_valid_contestant_id(window_before, valid_ids)
        if winner_id is not None:
            return winner_id

        # 3) Fallback por approach_name (con word-boundary y longitud ≥ 2,
        #    para no confundir nombres de una letra con caracteres sueltos
        #    del texto). Buscamos primero la ventana posterior y luego la
        #    anterior.
        for window in (window_after, window_before):
            for name_lc, pid in name_to_id.items():
                if len(name_lc) < 2:
                    continue
                if re.search(rf"\b{re.escape(name_lc)}\b", window):
                    return pid

    return None


def _first_valid_contestant_id(window: str, valid_ids: Set[int]) -> Optional[int]:
    """Devuelve el primer id que aparece en `window` y pertenece a valid_ids."""
    for m in _CONTESTANT_NUM_RE.finditer(window):
        try:
            n = int(m.group(1))
        except (TypeError, ValueError):
            continue
        if n in valid_ids:
            return n
    return None


def _last_valid_contestant_id(window: str, valid_ids: Set[int]) -> Optional[int]:
    """Devuelve el último id válido en `window` (útil cuando el keyword va al final)."""
    last: Optional[int] = None
    for m in _CONTESTANT_NUM_RE.finditer(window):
        try:
            n = int(m.group(1))
        except (TypeError, ValueError):
            continue
        if n in valid_ids:
            last = n
    return last
