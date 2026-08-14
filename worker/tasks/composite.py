"""
Tasks: Composite Research Report.

- composite.research_report: orchestrates multiple research.web + llm.generate
  to produce a complete market research report from a single topic.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from .research import handle_research_web
from .llm import (
    PROXY_COMPOSITE_TIMEOUT_S,
    PROXY_MIN_TIMEOUT_S,
    PROXY_QUERYGEN_TIMEOUT_S,
    handle_llm_generate,
)

logger = logging.getLogger("worker.tasks.composite")
_ACTIVE_CONTEXT: Dict[str, str] = {}

DEPTH_MAP = {
    "quick": 3,
    "standard": 5,
    "deep": 10,
}

QUERY_GEN_PROMPT = (
    "Generate exactly {n} distinct web search queries to research the following topic. "
    "Return ONLY a numbered list (1. query\\n2. query\\n...) with no extra text.\n\n"
    "Topic: {topic}"
)

REPORT_SYSTEM_PROMPT = (
    "You are a senior market research analyst. Produce a structured report in {language}. "
    "Use markdown formatting. Cite sources inline as [Source Title](URL)."
)

REPORT_USER_PROMPT = (
    "Write a comprehensive research report on: **{topic}**\n\n"
    "Use the following research data to support your analysis. "
    "The report MUST include these sections:\n"
    "1. **Resumen Ejecutivo** — 2-3 paragraph executive summary\n"
    "2. **Hallazgos Principales** — key findings with source citations\n"
    "3. **Tendencias Identificadas** — trends and patterns observed\n"
    "4. **Recomendaciones** — actionable recommendations\n\n"
    "---\n\nResearch Data:\n\n{research_data}"
)

# ── PKG-MACRO-P5-L2-T9 (SHRINK, autorizado por David 2026-08-14) ────────
# Objetivo: que la llamada de generación de reporte termine en <90s, por
# debajo del urlopen del proxy (105s) y de la ventana de redespacho del
# dispatcher (~2 min). Antes tardaba >119s, agotaba el timeout, reintentaba,
# y el redespacho apilaba corridas hasta matar el gateway por OOM (acta §12.4).
#
# De dónde salen los números (medidos, no estimados):
#   - Turno de agente vía openclaw_proxy con salida mínima: ~35s con
#     max_tokens=100 → 34 tokens generados (T8 live). O sea que ~35s es
#     casi todo overhead fijo (setup del turno + ~27k tokens de prompt del
#     propio agente), no generación.
#   - Con max_tokens=4096 la generación agregaba ~4000 tokens y empujaba el
#     turno por encima de 119s. Con 1000 se esperaba ~50-70s.
#   - research_data real a depth=quick: 9.945 chars (15 fuentes, snippets de
#     500 chars). standard ≈ 16.5k, deep ≈ 33k.
#
# CORRECCIÓN T10 (FASE 0, medición sin corte): esa expectativa de 50-70s era
# optimista. El turno de reporte con max_tokens=1000 tarda **158.2s** reales,
# y el task completo 205.6s. O sea: el SHRINK bajó el costo pero el objetivo
# de <90s nunca se alcanzó, y por eso T10 ensancha la ventana en vez de seguir
# achicando el pedido (GO de David: WINDOW). Ver acta §14.
REPORT_MAX_TOKENS = 1000
# 12.000 chars ≈ 3.000 tokens. Elegido para que `quick` (9.945) entre COMPLETO
# —es la forma que corre el e2e— y para acotar `deep` (33k → 12k), que es el
# que hacía crecer el prompt ~8k tokens sobre la línea base del agente.
REPORT_RESEARCH_DATA_MAX_CHARS = 12_000
REPORT_TRUNCATION_NOTICE = "\n\n[... research data truncado por límite de tamaño ...]"

# T9: 3 → 1. El reintento tras timeout era el multiplicador que llevó al OOM:
# cada intento abría un turno nuevo de >119s en el gateway, y encima el
# dispatcher redespachaba la tarea entera. Con el turno ya achicado no hace
# falta reintentar: si falla, que falle rápido y visible.
REPORT_GENERATION_MAX_ATTEMPTS = 1
REPORT_GENERATION_BACKOFF_SECONDS = 1.0


class ReportGenerationError(RuntimeError):
    def __init__(self, message: str, *, attempts: int):
        super().__init__(message)
        self.attempts = attempts


def _is_retryable_report_generation_error(exc: Exception) -> bool:
    text = str(exc or "").lower()
    retry_markers = (
        "503",
        "unavailable",
        "timeout",
        "timed out",
        "deadline exceeded",
        "temporarily unavailable",
        "connection reset",
        "connection aborted",
    )
    return any(marker in text for marker in retry_markers)


def _truncate_research_data(research_data: str) -> str:
    """Acota el research_data que se le manda al modelo (T9).

    Corta en el último salto de línea antes del límite cuando hay uno cerca,
    para no partir una fuente por la mitad y dejar una URL colgada.

    OJO — esto descarta fuentes que el modelo nunca va a ver. Quién llega acá:
    `quick` (~9.9k chars) entra completo, pero `standard` —que es el **default**
    del task— se recorta (≈20 de 25 fuentes) y `deep` bastante más (≈20 de 50).
    Por eso el resultado expone `sources_sent_to_model`: sin ese dato el sobre
    diría `total_sources: 25` al lado de un reporte escrito con 20."""
    if len(research_data) <= REPORT_RESEARCH_DATA_MAX_CHARS:
        return research_data
    cut = research_data[:REPORT_RESEARCH_DATA_MAX_CHARS]
    last_newline = cut.rfind("\n")
    # Sólo respetamos el corte por línea si no nos hace perder demasiado.
    if last_newline > REPORT_RESEARCH_DATA_MAX_CHARS * 0.8:
        cut = cut[:last_newline]
    logger.info(
        "research_data truncado: %d → %d chars (límite %d)",
        len(research_data), len(cut), REPORT_RESEARCH_DATA_MAX_CHARS,
    )
    return cut + REPORT_TRUNCATION_NOTICE


def _count_source_lines(research_data: str) -> int:
    """Cuántas líneas de fuente hay en un bloque de research_data.

    `_format_research_data` emite una línea por fuente con el prefijo `- **[`."""
    return research_data.count("- **[")


# Presupuesto de tiempo del task, en monotonic. Lo setea el handler al entrar.
_BUDGET: Dict[str, float] = {}

# Margen que se le deja al dispatcher para recibir la respuesta y cerrar.
BUDGET_SAFETY_MARGIN_S = 20.0


def _remaining_budget_s() -> Optional[float]:
    """Cuánto tiempo queda del presupuesto que dio el dispatcher, o None.

    T10: sin esto, el timeout del reporte era un techo fijo que se comparaba
    contra la ventana del dispatcher como si el reporte arrancara en t=0. No
    arranca: viene después de query-gen + research (~47s medidos). Con techos
    fijos la suma se pasaba de la ventana y dejaba turnos huérfanos corriendo
    en el gateway. Acá se reparte lo que QUEDA, así que la invariante
    `preámbulo + reporte < ventana` se cumple por construcción."""
    total = _BUDGET.get("task_timeout_s")
    started = _BUDGET.get("started_at")
    if not total or started is None:
        return None
    return total - (time.monotonic() - started) - BUDGET_SAFETY_MARGIN_S


def _proxy_timeout_for(ceiling_s: float) -> float:
    """Techo, acotado por lo que quede del presupuesto.

    OJO con el piso: NO se usa `max(PISO, restante)` a ciegas. Si ya queda
    menos que el piso, devolver el piso volvería a desbordar la ventana — el
    turno arrancaría condenado a quedar huérfano, que es justo lo que este
    pack elimina. Quien llama tiene que chequear `_has_budget_for_a_call()`
    antes y no llamar si no alcanza."""
    remaining = _remaining_budget_s()
    if remaining is None:
        return ceiling_s
    return max(0.0, min(ceiling_s, remaining))


def _has_budget_for_a_call() -> bool:
    """¿Queda tiempo suficiente como para que valga la pena intentar?"""
    remaining = _remaining_budget_s()
    return remaining is None or remaining >= PROXY_MIN_TIMEOUT_S


def _build_report_generation_payload(
    *,
    topic: str,
    research_data: str,
    language: str,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "prompt": REPORT_USER_PROMPT.format(
            topic=topic,
            research_data=_truncate_research_data(research_data),
        ),
        "system": REPORT_SYSTEM_PROMPT.format(language=language),
        "max_tokens": REPORT_MAX_TOKENS,
        "temperature": 0.5,
        "_task_id": _ACTIVE_CONTEXT.get("task_id"),
        "_task_type": _ACTIVE_CONTEXT.get("task_type"),
        "_source": _ACTIVE_CONTEXT.get("source"),
        "_source_kind": _ACTIVE_CONTEXT.get("source_kind"),
        "_usage_component": "composite.research_report.report_generation",
        # T10 (WINDOW): ~158s medidos (FASE 0), muy por encima del default de
        # 105s del proxy. Techo propio, PERO acotado por lo que quede de la
        # ventana del dispatcher — el reporte arranca después del preámbulo.
        "_proxy_timeout_s": _proxy_timeout_for(PROXY_COMPOSITE_TIMEOUT_S),
    }
    payload.update(_routed_model_fields())
    return payload


def _routed_model_fields() -> Dict[str, str]:
    """Modelo elegido por el ModelRouter del dispatcher, si lo hay.

    T8: antes se descartaba y las sub-llamadas caían siempre en el default.
    Si el dispatcher no inyectó nada (llamada directa, sin encolar), devuelve
    {} y `handle_llm_generate` aplica su propio default."""
    return {
        key: _ACTIVE_CONTEXT[key]
        for key in ("model", "selected_model")
        if _ACTIVE_CONTEXT.get(key)
    }


def _generate_report_with_retry(
    *,
    topic: str,
    research_data: str,
    language: str,
) -> Tuple[str, int]:
    payload = _build_report_generation_payload(
        topic=topic,
        research_data=research_data,
        language=language,
    )
    last_error: Optional[Exception] = None

    if not _has_budget_for_a_call():
        # T10: sin presupuesto, NO se arranca el turno. Arrancarlo dejaría un
        # turno huérfano corriendo en el gateway después de que el dispatcher
        # ya se rindió. Se falla acá y el handler cae al reporte degradado.
        raise ReportGenerationError(
            "sin presupuesto de tiempo para generar el reporte "
            f"(quedan {_remaining_budget_s():.0f}s, mínimo {PROXY_MIN_TIMEOUT_S:.0f}s)",
            attempts=0,
        )

    for attempt in range(1, REPORT_GENERATION_MAX_ATTEMPTS + 1):
        try:
            llm_result = handle_llm_generate(payload)
            return llm_result.get("text", ""), attempt
        except Exception as exc:
            last_error = exc
            if attempt >= REPORT_GENERATION_MAX_ATTEMPTS or not _is_retryable_report_generation_error(exc):
                raise ReportGenerationError(str(exc), attempts=attempt) from exc
            sleep_seconds = REPORT_GENERATION_BACKOFF_SECONDS * attempt
            logger.warning(
                "LLM report generation transient failure on attempt %d/%d for topic %r: %s. Retrying in %.1fs",
                attempt,
                REPORT_GENERATION_MAX_ATTEMPTS,
                topic,
                exc,
                sleep_seconds,
            )
            time.sleep(sleep_seconds)

    if last_error is not None:
        raise ReportGenerationError(str(last_error), attempts=REPORT_GENERATION_MAX_ATTEMPTS) from last_error
    raise RuntimeError("LLM report generation failed without explicit error")


def _generate_queries(topic: str, n: int) -> List[str]:
    """Use LLM to generate search queries for a topic."""
    try:
        result = handle_llm_generate({
            "prompt": QUERY_GEN_PROMPT.format(n=n, topic=topic),
            "max_tokens": 512,
            "temperature": 0.4,
            "_task_id": _ACTIVE_CONTEXT.get("task_id"),
            "_task_type": _ACTIVE_CONTEXT.get("task_type"),
            "_source": _ACTIVE_CONTEXT.get("source"),
            "_source_kind": _ACTIVE_CONTEXT.get("source_kind"),
            "_usage_component": "composite.research_report.query_generation",
            # T10: antes esta llamada no tenía override y se quedaba con los
            # 105s del default — el peor caso que hacía desbordar la ventana.
            "_proxy_timeout_s": _proxy_timeout_for(PROXY_QUERYGEN_TIMEOUT_S),
            **_routed_model_fields(),
        })
    except Exception as exc:
        raise RuntimeError(f"Query generation LLM call failed: {exc}") from exc
    text = result.get("text", "")
    # Parse numbered list: "1. query\n2. query\n..."
    queries = []
    for line in text.strip().splitlines():
        line = line.strip()
        # Remove numbering: "1. ", "1) ", "- ", etc.
        for prefix_len in range(1, 5):
            if line[prefix_len:prefix_len + 2] in (". ", ") "):
                line = line[prefix_len + 2:]
                break
            elif line[prefix_len:prefix_len + 1] == " " and line[:prefix_len].replace("-", "").strip() == "":
                line = line[prefix_len + 1:]
                break
        if line:
            queries.append(line)
    return queries[:n]


def _do_research(queries: List[str]) -> tuple:
    """Execute research.web for each query, tolerating individual failures."""
    all_results = []
    sources = []
    for query in queries:
        try:
            res = handle_research_web({"query": query, "count": 5, "search_depth": "basic"})
            items = res.get("results", [])
            all_results.append({"query": query, "results": items})
            for item in items:
                sources.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "query": query,
                })
        except Exception as e:
            logger.warning("Research failed for query %r: %s", query, e)
            all_results.append({"query": query, "results": [], "error": str(e)})
    return all_results, sources


def _format_research_data(research_results: List[dict]) -> str:
    """Format research results into a text block for the LLM."""
    parts = []
    for entry in research_results:
        query = entry["query"]
        results = entry.get("results", [])
        if not results:
            continue
        parts.append(f"### Query: {query}")
        for r in results:
            title = r.get("title", "Sin título")
            url = r.get("url", "")
            snippet = r.get("snippet", "")
            parts.append(f"- **[{title}]({url})**: {snippet}")
        parts.append("")
    return "\n".join(parts) if parts else "(No research data available)"


def handle_composite_research_report(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Orchestrates multiple research.web + llm.generate to produce a complete
    market research report.

    Input:
        topic (str, required): Subject to research.
        queries (list[str], optional): Specific search queries. Auto-generated if omitted.
        depth (str, optional): "quick" (3 queries) | "standard" (5) | "deep" (10). Default: "standard".
        language (str, optional): Report language. Default: "es".

    Returns:
        report (str): Complete markdown report.
        sources (list[dict]): Sources used ({title, url, query}).
        queries_used (list[str]): Queries executed.
        stats (dict): {total_sources, research_time_ms, generation_time_ms}.
    """
    topic = input_data.get("topic", "").strip()
    if not topic:
        raise ValueError("'topic' is required and cannot be empty")

    _ACTIVE_CONTEXT.clear()
    for key, target in (
        ("_task_id", "task_id"),
        ("_task_type", "task_type"),
        ("_source", "source"),
        ("_source_kind", "source_kind"),
        # PKG-MACRO-P5-L2-T8: `composite.` está en LLM_TASK_PREFIXES, así que
        # el dispatcher YA inyecta model/selected_model para esta tarea — pero
        # hasta ahora se descartaban acá y las sub-llamadas caían en el default.
        # Se propagan por _ACTIVE_CONTEXT igual que la metadata de tracing.
        ("model", "model"),
        ("selected_model", "selected_model"),
    ):
        value = str(input_data.get(key, "") or "").strip()
        if value:
            _ACTIVE_CONTEXT[target] = value

    # T10 (WINDOW): arranca el reloj del presupuesto. `_task_timeout_s` lo
    # inyecta el dispatcher; si no está (llamada directa al worker), las
    # sub-llamadas usan sus techos fijos.
    _BUDGET.clear()
    _BUDGET["started_at"] = time.monotonic()
    try:
        budget = float(input_data.get("_task_timeout_s") or 0)
    except (TypeError, ValueError):
        budget = 0.0
    if budget > 0:
        _BUDGET["task_timeout_s"] = budget

    depth = input_data.get("depth", "standard")
    language = input_data.get("language", "es")
    explicit_queries: Optional[List[str]] = input_data.get("queries")

    n_queries = DEPTH_MAP.get(depth, DEPTH_MAP["standard"])

    # Step 1: Determine queries
    if explicit_queries and len(explicit_queries) > 0:
        queries = explicit_queries[:n_queries * 2]  # allow more if user provides them
        logger.info("Using %d explicit queries for topic: %s", len(queries), topic)
    else:
        logger.info("Generating %d queries for topic: %s (depth=%s)", n_queries, topic, depth)
        queries = _generate_queries(topic, n_queries)
        if not queries:
            raise RuntimeError("Failed to generate search queries from LLM")

    # Step 2: Research
    t0 = time.monotonic()
    research_results, sources = _do_research(queries)
    research_time_ms = int((time.monotonic() - t0) * 1000)

    successful_queries = [r["query"] for r in research_results if r.get("results")]
    logger.info(
        "Research done: %d/%d queries returned results, %d total sources",
        len(successful_queries), len(queries), len(sources),
    )

    # Step 3: Generate report
    research_data = _format_research_data(research_results)

    t1 = time.monotonic()
    report_generation_attempts = 0
    try:
        report, report_generation_attempts = _generate_report_with_retry(
            topic=topic,
            research_data=research_data,
            language=language,
        )
    except Exception as e:
        if isinstance(e, ReportGenerationError):
            report_generation_attempts = e.attempts
        else:
            report_generation_attempts = max(report_generation_attempts, 1)
        logger.error("LLM report generation failed: %s", e)
        # Fallback: return raw research data as report
        report = (
            f"# Research Report: {topic}\n\n"
            f"⚠️ LLM generation failed ({e}). Raw research data below.\n\n"
            f"{research_data}"
        )
    generation_time_ms = int((time.monotonic() - t1) * 1000)

    return {
        "report": report,
        "sources": sources,
        "queries_used": queries,
        "stats": {
            "total_sources": len(sources),
            # T9: cuántas de esas fuentes le llegaron REALMENTE al modelo. Con
            # el cap de research_data pueden no ser todas (`standard`, que es
            # el default, ya recorta). Sin este dato el sobre afirmaría
            # `total_sources: 25` junto a un reporte escrito con 20.
            "sources_sent_to_model": _count_source_lines(
                _truncate_research_data(research_data)
            ),
            "research_time_ms": research_time_ms,
            "generation_time_ms": generation_time_ms,
            "report_generation_attempts": max(report_generation_attempts, 1),
        },
    }
