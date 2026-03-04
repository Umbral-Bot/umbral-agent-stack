#!/usr/bin/env python3
"""Quick e2e test: call Worker VPS ping task."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

for line in open(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

import httpx

worker = os.environ.get("WORKER_URL", "http://127.0.0.1:8088")
token = os.environ.get("WORKER_TOKEN", "")

r = httpx.post(
    f"{worker}/run",
    json={"task": "ping", "input": {"echo": "hackathon-test-2026-03-04"}},
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    timeout=10,
)
print(f"Status: {r.status_code}")
print(f"Body: {r.text}")
