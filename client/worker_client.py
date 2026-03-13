"""
Umbral Worker Client SDK

Python client for calling the Worker HTTP API from the VPS or other services.
Handles Bearer auth, timeouts, and retries.

Usage:
    from client.worker_client import WorkerClient

    wc = WorkerClient()  # reads WORKER_URL and WORKER_TOKEN from env
    result = wc.ping()
    result = wc.run("notion.add_comment", {"text": "Hello from VPS"})
"""

import logging
import os
import time
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("worker_client")


class WorkerClient:
    """Client for the Umbral Worker HTTP API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: float = 30.0,
        retries: int = 2,
        retry_delay: float = 1.0,
    ):
        """
        Args:
            base_url: Worker URL (default: env WORKER_URL).
            token: Bearer token (default: env WORKER_TOKEN).
            timeout: HTTP timeout in seconds.
            retries: Number of retries on transient errors.
            retry_delay: Seconds between retries.
        """
        self.base_url = (base_url or os.environ.get("WORKER_URL", "")).rstrip("/")
        self.token = token or os.environ.get("WORKER_TOKEN", "")
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay

        if not self.base_url:
            raise ValueError(
                "WORKER_URL not set. Pass base_url or set WORKER_URL env var."
            )
        if not self.token:
            raise ValueError(
                "WORKER_TOKEN not set. Pass token or set WORKER_TOKEN env var."
            )

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }

    def health(self) -> Dict[str, Any]:
        """GET /health — no auth required."""
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.base_url}/health")
            resp.raise_for_status()
            return resp.json()

    def run(
        self,
        task: str,
        input_data: Optional[Dict[str, Any]] = None,
        envelope: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        POST /run — execute a task on the worker.

        Args:
            task: Task name (e.g., "ping", "notion.add_comment").
            input_data: Task input payload.
            envelope: Full task envelope. When provided, merges task_id, team,
                      task_type, and trace_id into the payload for end-to-end tracing.

        Returns:
            Response dict with "ok", "task", "result" keys.

        Raises:
            httpx.HTTPStatusError: On 4xx/5xx after all retries.
        """
        payload: Dict[str, Any] = {"task": task, "input": input_data or {}}
        if envelope:
            for field in ("task_id", "team", "task_type", "trace_id"):
                if field in envelope:
                    payload[field] = envelope[field]
        last_exc: Optional[Exception] = None

        for attempt in range(1, self.retries + 2):  # retries + 1 initial attempt
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(
                        f"{self.base_url}/run",
                        headers=self._headers(),
                        json=payload,
                    )
                    resp.raise_for_status()
                    return resp.json()
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
                last_exc = exc
                if attempt <= self.retries:
                    logger.warning(
                        "Attempt %d/%d failed (%s), retrying in %.1fs...",
                        attempt,
                        self.retries + 1,
                        type(exc).__name__,
                        self.retry_delay,
                    )
                    time.sleep(self.retry_delay)
                continue
            except httpx.HTTPStatusError:
                raise  # Don't retry on 4xx/5xx

        raise last_exc  # type: ignore

    def ping(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Convenience: run the ping task."""
        return self.run("ping", extra or {})

    def notion_write_transcript(
        self, title: str, content: str, source: str = "granola", date: str | None = None
    ) -> Dict[str, Any]:
        """Convenience: write a transcript to Notion Granola Inbox."""
        input_data: Dict[str, Any] = {"title": title, "content": content, "source": source}
        if date:
            input_data["date"] = date
        return self.run("notion.write_transcript", input_data)

    def notion_add_comment(self, text: str, page_id: str | None = None) -> Dict[str, Any]:
        """Convenience: add a comment to Notion Control Room."""
        input_data: Dict[str, Any] = {"text": text}
        if page_id:
            input_data["page_id"] = page_id
        return self.run("notion.add_comment", input_data)

    def notion_poll_comments(
        self, since: str | None = None, limit: int = 20, page_id: str | None = None
    ) -> Dict[str, Any]:
        """Convenience: poll comments from Notion page."""
        input_data: Dict[str, Any] = {"limit": limit}
        if since:
            input_data["since"] = since
        if page_id:
            input_data["page_id"] = page_id
        return self.run("notion.poll_comments", input_data)

    def task_history(
        self,
        hours: int = 24,
        team: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """GET /task/history — Redis-backed task history with pagination/stats."""
        params: Dict[str, Any] = {
            "hours": hours,
            "limit": limit,
            "offset": offset,
        }
        if team:
            params["team"] = team
        if status:
            params["status"] = status

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(
                f"{self.base_url}/task/history",
                headers=self._headers(),
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    def quota_status(self) -> Dict[str, Any]:
        """GET /quota/status — Returns current configured quotas and usage."""
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(
                f"{self.base_url}/quota/status",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()
