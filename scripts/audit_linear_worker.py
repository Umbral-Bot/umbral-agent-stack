#!/usr/bin/env python3
"""Audit: call Worker linear.list_teams and show full response."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
env_file = Path(os.environ.get("HOME", "")) / ".config/openclaw/env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'").replace("\r", "")
        if k.startswith("export "):
            k = k[7:].strip()
        if k:
            os.environ[k] = v

import httpx
tok = os.environ.get("WORKER_TOKEN", "")
url = os.environ.get("WORKER_URL", "http://127.0.0.1:8088").rstrip("/") + "/run"
r = httpx.post(
    url,
    json={"task": "linear.list_teams", "input": {}},
    headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
    timeout=15,
)
print("Worker URL:", url)
print("WORKER_TOKEN length:", len(tok))
print("Response status:", r.status_code)
print("Response body:", r.text[:800])
