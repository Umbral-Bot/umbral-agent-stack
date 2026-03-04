#!/usr/bin/env python3
"""
Umbral E2E Validation Suite — verify the entire system works end-to-end.

Connects to the live Worker VPS and runs tests against every major subsystem:
health checks, ping, research.web, llm.generate, composite research,
/enqueue, /task/history, Notion, and Redis queue stats.

Usage:
    # Basic run (prints results to stdout)
    PYTHONPATH=. python3 scripts/e2e_validation.py

    # Post results to Notion Control Room
    PYTHONPATH=. python3 scripts/e2e_validation.py --notion

    # Quiet mode (summary only)
    PYTHONPATH=. python3 scripts/e2e_validation.py --quiet

Requires env vars: WORKER_URL, WORKER_TOKEN, REDIS_URL (for queue stats).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Repo root on PATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("e2e_validation")


# ── Data structures ─────────────────────────────────────────────

@dataclass
class TestResult:
    name: str
    passed: bool
    elapsed_ms: float
    detail: str = ""
    error: str = ""


@dataclass
class SuiteResult:
    results: List[TestResult] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def total_pass(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def total_fail(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def total_time_s(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return sum(r.elapsed_ms for r in self.results) / 1000.0


# ── Test runner infrastructure ──────────────────────────────────

def _run_test(name: str, fn, timeout: float = 30.0) -> TestResult:
    """Execute a test function with timing and error capture."""
    start = time.monotonic()
    try:
        detail = fn()
        elapsed = (time.monotonic() - start) * 1000
        return TestResult(name=name, passed=True, elapsed_ms=elapsed, detail=str(detail or ""))
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        error_msg = f"{type(e).__name__}: {e}"
        logger.warning("Test '%s' failed: %s", name, error_msg)
        return TestResult(name=name, passed=False, elapsed_ms=elapsed, error=error_msg)


# ── Individual tests ────────────────────────────────────────────

def _make_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def test_worker_vps_health(base_url: str) -> str:
    """1. GET /health on Worker VPS."""
    with httpx.Client(timeout=10.0) as c:
        resp = c.get(f"{base_url}/health")
        resp.raise_for_status()
        data = resp.json()
        version = data.get("version", "?")
        handlers = data.get("handlers", "?")
        return f"v{version}, {handlers} handlers"


def test_ping(base_url: str, token: str) -> str:
    """2. POST /run ping task."""
    with httpx.Client(timeout=10.0) as c:
        resp = c.post(
            f"{base_url}/run",
            headers=_make_headers(token),
            json={"task": "ping", "input": {}},
        )
        resp.raise_for_status()
        data = resp.json()
        return f"echo={data.get('result', {}).get('echo', '?')}"


def test_research_web(base_url: str, token: str) -> str:
    """3. POST /run research.web with a real query."""
    with httpx.Client(timeout=20.0) as c:
        resp = c.post(
            f"{base_url}/run",
            headers=_make_headers(token),
            json={
                "task": "research.web",
                "input": {"query": "BIM trends 2026", "count": 3},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("result", {}).get("results", [])
        return f"{len(results)} resultados"


def test_llm_generate(base_url: str, token: str) -> str:
    """4. POST /run llm.generate with a simple prompt."""
    with httpx.Client(timeout=25.0) as c:
        resp = c.post(
            f"{base_url}/run",
            headers=_make_headers(token),
            json={
                "task": "llm.generate",
                "input": {
                    "prompt": "Responde en una oración: ¿qué es BIM?",
                    "max_tokens": 100,
                    "temperature": 0.3,
                },
            },
        )
        resp.raise_for_status()
        data = resp.json()
        text = data.get("result", {}).get("text", "")
        return f"{len(text)} chars generados"


def test_composite_research(base_url: str, token: str) -> str:
    """5. POST /run composite.research_report — full pipeline."""
    with httpx.Client(timeout=45.0) as c:
        resp = c.post(
            f"{base_url}/run",
            headers=_make_headers(token),
            json={
                "task": "composite.research_report",
                "input": {
                    "query": "tendencias proptech 2026",
                    "count": 3,
                },
            },
        )
        resp.raise_for_status()
        data = resp.json()
        report = data.get("result", {}).get("report", "")
        return f"reporte {len(report)} chars"


def test_enqueue(base_url: str, token: str) -> str:
    """6. POST /enqueue a test task and check its status."""
    task_id = None
    with httpx.Client(timeout=15.0) as c:
        # Enqueue
        resp = c.post(
            f"{base_url}/enqueue",
            headers=_make_headers(token),
            json={
                "task": "ping",
                "team": "system",
                "input": {"echo": "e2e_validation_test"},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        task_id = data.get("task_id", "?")
        if not data.get("ok"):
            raise ValueError(f"enqueue returned ok=false: {data}")

        # Check status
        resp2 = c.get(
            f"{base_url}/task/{task_id}/status",
            headers=_make_headers(token),
        )
        resp2.raise_for_status()
        status_data = resp2.json()
        status = status_data.get("status", "?")
        return f"task_id={task_id[:8]}..., status={status}"


def test_task_history(base_url: str, token: str) -> str:
    """7. GET /task/history — check endpoint works."""
    with httpx.Client(timeout=15.0) as c:
        resp = c.get(
            f"{base_url}/task/history",
            headers=_make_headers(token),
            params={"hours": 24, "limit": 10},
        )
        resp.raise_for_status()
        data = resp.json()
        total = data.get("stats", {}).get("total", data.get("total", "?"))
        return f"{total} tareas en 24h"


def test_notion_add_comment(base_url: str, token: str) -> str:
    """8. POST /run notion.add_comment — post a validation ping."""
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    text = f"Rick: [E2E Validation] Sistema OK — {ts}"
    with httpx.Client(timeout=15.0) as c:
        resp = c.post(
            f"{base_url}/run",
            headers=_make_headers(token),
            json={"task": "notion.add_comment", "input": {"text": text}},
        )
        resp.raise_for_status()
        data = resp.json()
        ok = data.get("ok", False)
        comment_id = data.get("result", {}).get("comment_id", "?")
        if not ok:
            raise ValueError(f"notion.add_comment ok=false: {data}")
        return f"comment_id={str(comment_id)[:8]}..."


def test_redis_queue_stats(redis_url: str) -> str:
    """9. Redis queue stats — connectivity + queue state."""
    import redis as redis_lib
    r = redis_lib.from_url(redis_url, decode_responses=True)
    r.ping()

    # Read queue lengths directly
    pending = r.llen("umbral:tasks:pending")
    blocked = r.llen("umbral:tasks:blocked")
    return f"pending={pending}, blocked={blocked}"


def test_worker_vm_health(vm_url: str) -> str:
    """10. GET /health on Worker VM (if reachable)."""
    with httpx.Client(timeout=8.0) as c:
        resp = c.get(f"{vm_url}/health")
        resp.raise_for_status()
        data = resp.json()
        version = data.get("version", "?")
        handlers = data.get("handlers", "?")
        return f"v{version}, {handlers} handlers"


# ── Suite runner ────────────────────────────────────────────────

def run_e2e_suite(
    base_url: str,
    token: str,
    redis_url: str,
    vm_url: Optional[str] = None,
) -> SuiteResult:
    """Execute the full E2E validation suite."""
    suite = SuiteResult(start_time=datetime.now(timezone.utc))

    tests = [
        ("Worker VPS health", lambda: test_worker_vps_health(base_url)),
        ("Ping", lambda: test_ping(base_url, token)),
        ("research.web", lambda: test_research_web(base_url, token)),
        ("llm.generate", lambda: test_llm_generate(base_url, token)),
        ("composite.research", lambda: test_composite_research(base_url, token)),
        ("POST /enqueue + status", lambda: test_enqueue(base_url, token)),
        ("GET /task/history", lambda: test_task_history(base_url, token)),
        ("notion.add_comment", lambda: test_notion_add_comment(base_url, token)),
        ("Redis queue stats", lambda: test_redis_queue_stats(redis_url)),
    ]

    # Optionally test Worker VM if URL provided
    if vm_url:
        tests.append(("Worker VM health", lambda: test_worker_vm_health(vm_url)))

    for i, (name, fn) in enumerate(tests, 1):
        label = f"{i}. {name}"
        result = _run_test(label, fn)
        suite.results.append(result)

    suite.end_time = datetime.now(timezone.utc)
    return suite


# ── Output formatting ──────────────────────────────────────────

def format_results(suite: SuiteResult, quiet: bool = False) -> str:
    """Format suite results for display."""
    lines = []
    ts = suite.start_time.strftime("%Y-%m-%d %H:%M UTC") if suite.start_time else "?"

    lines.append("=== Umbral E2E Validation ===")
    lines.append(f"Date: {ts}")
    lines.append("")

    for r in suite.results:
        status = "[PASS]" if r.passed else "[FAIL]"
        elapsed = _format_elapsed(r.elapsed_ms)

        if r.passed:
            detail = r.detail[:50] if r.detail else ""
            lines.append(f"{status} {r.name:<30s} ({elapsed})  {detail}")
        else:
            if quiet:
                lines.append(f"{status} {r.name:<30s} ({elapsed})  {r.error[:60]}")
            else:
                lines.append(f"{status} {r.name:<30s} ({elapsed})")
                lines.append(f"       Error: {r.error}")

    lines.append("")
    total = len(suite.results)
    lines.append(f"=== Results: {suite.total_pass}/{total} PASS ===")
    if suite.total_fail > 0:
        lines.append(f"    FAILURES: {suite.total_fail}")
    lines.append(f"Total time: {suite.total_time_s:.1f}s")

    return "\n".join(lines)


def _format_elapsed(ms: float) -> str:
    if ms >= 1000:
        return f"{ms / 1000:.1f}s"
    return f"{ms:.0f}ms"


# ── Notion posting ──────────────────────────────────────────────

def post_to_notion(base_url: str, token: str, text: str) -> None:
    """Post validation results as a Notion comment."""
    try:
        with httpx.Client(timeout=15.0) as c:
            resp = c.post(
                f"{base_url}/run",
                headers=_make_headers(token),
                json={"task": "notion.add_comment", "input": {"text": text}},
            )
            resp.raise_for_status()
            logger.info("Results posted to Notion Control Room")
    except Exception as e:
        logger.error("Failed to post to Notion: %s", e)


# ── Main ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Umbral E2E Validation Suite")
    parser.add_argument("--notion", action="store_true", help="Post results to Notion Control Room")
    parser.add_argument("--quiet", action="store_true", help="Print summary only")
    parser.add_argument("--vm-url", default=None, help="Worker VM URL (optional)")
    args = parser.parse_args()

    base_url = os.environ.get("WORKER_URL", "").rstrip("/")
    token = os.environ.get("WORKER_TOKEN", "")
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    if not base_url or not token:
        print("ERROR: WORKER_URL and WORKER_TOKEN must be set.", file=sys.stderr)
        sys.exit(1)

    print(f"Running E2E validation against {base_url}...")
    print()

    suite = run_e2e_suite(
        base_url=base_url,
        token=token,
        redis_url=redis_url,
        vm_url=args.vm_url,
    )

    output = format_results(suite, quiet=args.quiet)
    print(output)

    # Post to Notion if requested
    if args.notion:
        notion_text = f"Rick: [E2E Validation Report]\n\n{output}"
        post_to_notion(base_url, token, notion_text)

    # Exit code reflects pass/fail
    sys.exit(0 if suite.total_fail == 0 else 1)


if __name__ == "__main__":
    main()
