#!/usr/bin/env python3
"""
SIM → Make.com Pipeline.

Encola un composite.research_report, espera resultado vía polling, y envía
los datos al webhook de Make.com configurado para análisis de mercado SIM.

Uso:
    python scripts/sim_to_make.py                           # topic por defecto
    python scripts/sim_to_make.py --topic "IA generativa en real estate"
    python scripts/sim_to_make.py --dry-run                 # no envía a Make
    python scripts/sim_to_make.py --timeout 180             # 3 min polling
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Repo root in sys.path
# ---------------------------------------------------------------------------
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from client.worker_client import WorkerClient  # noqa: E402

logger = logging.getLogger("sim_to_make")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

DEFAULT_TOPIC = "mercado inmobiliario BIM"
DEFAULT_POLL_INTERVAL = 10  # seconds
DEFAULT_TIMEOUT = 120  # seconds


# ======================================================================
# Step 1: Enqueue research report
# ======================================================================

def enqueue_research(
    client: WorkerClient,
    topic: str,
    depth: str = "standard",
    language: str = "es",
) -> str:
    """
    Enqueue a composite.research_report via POST /enqueue.
    Returns the task_id.
    """
    import httpx

    payload = {
        "task": "composite.research_report",
        "team": "marketing",
        "task_type": "research",
        "input": {
            "topic": topic,
            "depth": depth,
            "language": language,
        },
    }

    logger.info("Enqueueing research report: topic=%r, depth=%s", topic, depth)

    with httpx.Client(timeout=client.timeout) as http:
        resp = http.post(
            f"{client.base_url}/enqueue",
            headers=client._headers(),
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    task_id = data.get("task_id", "")
    if not task_id:
        raise RuntimeError(f"Enqueue failed: no task_id in response: {data}")

    logger.info("Enqueued task_id=%s", task_id)
    return task_id


# ======================================================================
# Step 2: Poll for result
# ======================================================================

def poll_task_status(
    client: WorkerClient,
    task_id: str,
    timeout: int = DEFAULT_TIMEOUT,
    interval: int = DEFAULT_POLL_INTERVAL,
) -> Dict[str, Any]:
    """
    Poll GET /task/{task_id}/status until done/failed or timeout.
    Returns the task status response dict.
    """
    import httpx

    deadline = time.time() + timeout
    logger.info("Polling task %s (timeout=%ds, interval=%ds)", task_id, timeout, interval)

    while time.time() < deadline:
        try:
            with httpx.Client(timeout=client.timeout) as http:
                resp = http.get(
                    f"{client.base_url}/task/{task_id}/status",
                    headers=client._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("Poll error: %s", exc)
            time.sleep(interval)
            continue

        status = data.get("status", "unknown")
        logger.info("Task %s status: %s", task_id, status)

        if status in ("done", "failed"):
            return data

        time.sleep(interval)

    raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")


# ======================================================================
# Step 3: Send to Make.com
# ======================================================================

def send_to_make(
    client: WorkerClient,
    webhook_url: str,
    payload: Dict[str, Any],
    timeout: int = 30,
) -> Dict[str, Any]:
    """
    Send payload to Make.com webhook via worker task make.post_webhook.
    """
    logger.info("Sending result to Make.com webhook: %s", webhook_url[:60])
    return client.run("make.post_webhook", {
        "webhook_url": webhook_url,
        "payload": payload,
        "timeout": timeout,
    })


# ======================================================================
# CLI
# ======================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="SIM → Make.com Pipeline: encola research, espera resultado, envía a Make."
    )
    parser.add_argument("--topic", default=DEFAULT_TOPIC, help=f"Tema de investigación (default: '{DEFAULT_TOPIC}')")
    parser.add_argument("--depth", default="standard", choices=["quick", "standard", "deep"], help="Profundidad del research")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help=f"Timeout de polling en segundos (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--interval", type=int, default=DEFAULT_POLL_INTERVAL, help=f"Intervalo de polling (default: {DEFAULT_POLL_INTERVAL}s)")
    parser.add_argument("--dry-run", action="store_true", help="No envía a Make.com; imprime resultado")
    parser.add_argument("--language", default="es", help="Idioma del reporte (default: es)")
    args = parser.parse_args()

    # --- Validate env ---
    webhook_url = os.environ.get("MAKE_WEBHOOK_SIM_URL", "").strip()
    if not webhook_url and not args.dry_run:
        print("ERROR: MAKE_WEBHOOK_SIM_URL not set. Use --dry-run or set the env var.", file=sys.stderr)
        return 1

    # --- WorkerClient ---
    try:
        wc = WorkerClient()
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # --- Step 1: Enqueue ---
    try:
        task_id = enqueue_research(wc, topic=args.topic, depth=args.depth, language=args.language)
    except Exception as exc:
        logger.error("Failed to enqueue research: %s", exc)
        return 2

    # --- Step 2: Poll ---
    try:
        result = poll_task_status(wc, task_id, timeout=args.timeout, interval=args.interval)
    except TimeoutError as exc:
        logger.error("Polling timeout: %s", exc)
        return 3
    except Exception as exc:
        logger.error("Polling error: %s", exc)
        return 3

    status = result.get("status", "unknown")
    if status == "failed":
        error = result.get("error", "unknown error")
        logger.error("Research task failed: %s", error)
        print(f"Research task failed: {error}", file=sys.stderr)
        return 4

    # --- Extract result ---
    task_result = result.get("result", {})
    make_payload = {
        "task_id": task_id,
        "topic": args.topic,
        "depth": args.depth,
        "status": status,
        "report": task_result.get("report", ""),
        "sources_count": len(task_result.get("sources", [])),
        "sources": task_result.get("sources", [])[:20],
        "queries": task_result.get("queries", []),
        "execution_time_s": task_result.get("execution_time_s", 0),
    }

    if args.dry_run:
        import json
        print("=== DRY RUN — Would send to Make.com ===")
        print(f"Webhook: {webhook_url or '(not set)'}")
        print(f"Task ID: {task_id}")
        print(f"Status:  {status}")
        print(f"Report length: {len(make_payload.get('report', ''))} chars")
        print(f"Sources: {make_payload['sources_count']}")
        print("--- Payload preview ---")
        print(json.dumps(make_payload, indent=2, ensure_ascii=False)[:2000])
        return 0

    # --- Step 3: Send to Make.com ---
    try:
        resp = send_to_make(wc, webhook_url, make_payload)
        ok = resp.get("result", {}).get("ok", False)
        sc = resp.get("result", {}).get("status_code", "?")
        logger.info("Make.com response: ok=%s, status_code=%s", ok, sc)
        print(f"Sent to Make.com: ok={ok}, status_code={sc}")
        return 0 if ok else 5
    except Exception as exc:
        logger.error("Failed to send to Make.com: %s", exc)
        return 5


if __name__ == "__main__":
    sys.exit(main())
