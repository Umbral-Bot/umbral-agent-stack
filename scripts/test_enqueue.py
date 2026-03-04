#!/usr/bin/env python3
"""Enqueue a test task via TaskQueue so Dispatcher picks it up."""
import os, sys, uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import redis
from dispatcher.queue import TaskQueue

redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(redis_url)
tq = TaskQueue(r)

tid = str(uuid.uuid4())
envelope = {
    "schema_version": "0.1",
    "task_id": tid,
    "team": "system",
    "task_type": "general",
    "task": "ping",
    "input": {"echo": "hackathon-dispatcher-e2e"},
}

result = tq.enqueue(envelope)
q_key = "umbral:tasks:pending"
q_len = r.llen(q_key)
print(f"Enqueued: {result}")
print(f"Queue len: {q_len}")
