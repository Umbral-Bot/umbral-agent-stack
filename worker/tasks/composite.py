"""
Tasks: Composite Research Report.

- composite.research_report: orchestrates multiple research.web + llm.generate
  to produce a complete market research report from a single topic.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from .research import handle_research_web
from .llm import handle_llm_generate

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

REPORT_GENERATION_MAX_ATTEMPTS = 3
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


def _build_report_generation_payload(
    *,
    topic: str,
    research_data: str,
    language: str,
) -> Dict[str, Any]:
    return {
        "prompt": REPORT_USER_PROMPT.format(topic=topic, research_data=research_data),
        "system": REPORT_SYSTEM_PROMPT.format(language=language),
        "max_tokens": 4096,
        "temperature": 0.5,
        "_task_id": _ACTIVE_CONTEXT.get("task_id"),
        "_task_type": _ACTIVE_CONTEXT.get("task_type"),
        "_source": _ACTIVE_CONTEXT.get("source"),
        "_source_kind": _ACTIVE_CONTEXT.get("source_kind"),
        "_usage_component": "composite.research_report.report_generation",
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
    result = handle_llm_generate({
        "prompt": QUERY_GEN_PROMPT.format(n=n, topic=topic),
        "max_tokens": 512,
        "temperature": 0.4,
        "_task_id": _ACTIVE_CONTEXT.get("task_id"),
        "_task_type": _ACTIVE_CONTEXT.get("task_type"),
        "_source": _ACTIVE_CONTEXT.get("source"),
        "_source_kind": _ACTIVE_CONTEXT.get("source_kind"),
        "_usage_component": "composite.research_report.query_generation",
    })
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
    ):
        value = str(input_data.get(key, "") or "").strip()
        if value:
            _ACTIVE_CONTEXT[target] = value

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
            "research_time_ms": research_time_ms,
            "generation_time_ms": generation_time_ms,
            "report_generation_attempts": max(report_generation_attempts, 1),
        },
    }
