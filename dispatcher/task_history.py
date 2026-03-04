"""
Task history queries over Redis-backed task envelopes.

Provides a SCAN-based API to query `umbral:task:*` entries without blocking Redis.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, Optional

from .queue import TaskQueue


class TaskHistory:
    """Query helper for task history stored in Redis."""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.key_prefix = TaskQueue.TASK_KEY_PREFIX

    def _iter_task_keys(self, scan_count: int = 300) -> Iterator[str]:
        cursor = 0
        pattern = f"{self.key_prefix}*"
        while True:
            cursor, keys = self.redis.scan(cursor=cursor, match=pattern, count=scan_count)
            for key in keys:
                yield key
            if cursor == 0:
                break

    @staticmethod
    def _parse_ts(raw: Any) -> Optional[float]:
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            return float(raw)
        if isinstance(raw, str):
            text = raw.strip()
            if not text:
                return None
            try:
                return float(text)
            except ValueError:
                pass
            try:
                dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.timestamp()
            except ValueError:
                return None
        return None

    @classmethod
    def _task_ts(cls, envelope: Dict[str, Any]) -> float:
        for field in ("completed_at", "failed_at", "started_at", "queued_at", "created_at"):
            ts = cls._parse_ts(envelope.get(field))
            if ts is not None:
                return ts
        return 0.0

    def _load_envelope(self, key: str) -> Optional[Dict[str, Any]]:
        raw = self.redis.get(key)
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
        if not isinstance(data, dict):
            return None
        return data

    def query(
        self,
        hours: int = 24,
        team: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Query tasks in Redis by time window and optional filters."""
        now_ts = time.time()
        cutoff = now_ts - (max(hours, 0) * 3600)

        matches: list[Dict[str, Any]] = []
        for key in self._iter_task_keys():
            env = self._load_envelope(key)
            if env is None:
                continue

            env_ts = self._task_ts(env)
            if env_ts < cutoff:
                continue
            if team and env.get("team") != team:
                continue
            if status and env.get("status") != status:
                continue

            item = dict(env)
            item["_history_ts"] = env_ts
            matches.append(item)

        matches.sort(key=lambda x: x.get("_history_ts", 0.0), reverse=True)
        total = len(matches)

        page_slice = matches[offset : offset + limit]
        tasks: list[Dict[str, Any]] = []
        for item in page_slice:
            obj = dict(item)
            obj.pop("_history_ts", None)
            tasks.append(obj)

        return {
            "tasks": tasks,
            "total": total,
            "page": {
                "offset": offset,
                "limit": limit,
                "has_more": (offset + limit) < total,
            },
        }

    def stats(self, hours: int = 24) -> Dict[str, Any]:
        """Aggregate stats by status and team for a time window."""
        now_ts = time.time()
        cutoff = now_ts - (max(hours, 0) * 3600)

        status_counter: Counter[str] = Counter()
        team_counter: Counter[str] = Counter()

        for key in self._iter_task_keys():
            env = self._load_envelope(key)
            if env is None:
                continue

            env_ts = self._task_ts(env)
            if env_ts < cutoff:
                continue

            st = str(env.get("status", "unknown")).strip() or "unknown"
            tm = str(env.get("team", "unknown")).strip() or "unknown"
            status_counter[st] += 1
            team_counter[tm] += 1

        return {
            "done": status_counter.get("done", 0),
            "failed": status_counter.get("failed", 0),
            "queued": status_counter.get("queued", 0),
            "running": status_counter.get("running", 0),
            "blocked": status_counter.get("blocked", 0),
            "degraded": status_counter.get("degraded", 0),
            "unknown": status_counter.get("unknown", 0),
            "teams": dict(sorted(team_counter.items())),
        }
