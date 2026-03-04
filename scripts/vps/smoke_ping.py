#!/usr/bin/env python3
"""Smoke test rápido: ping + quota/status al Worker."""
import json
import os
import sys
import urllib.request

BASE = os.environ.get("WORKER_URL", "http://localhost:8088")
TOKEN = os.environ.get("WORKER_TOKEN", "")

def post(path, body):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + TOKEN},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def get(path):
    req = urllib.request.Request(
        BASE + path,
        headers={"Authorization": "Bearer " + TOKEN},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

ok = True

# 1. Ping (endpoint /run)
try:
    r = post("/run", {"task": "ping", "input": {}})
    print(f"[OK] ping → {r.get('result', r)}")
except Exception as e:
    print(f"[FAIL] ping: {e}")
    ok = False

# 2. Health
try:
    r = get("/health")
    print(f"[OK] health → version={r.get('version')} tasks={len(r.get('tasks_registered', []))}")
except Exception as e:
    print(f"[FAIL] health: {e}")
    ok = False

# 3. Quota status (si existe)
try:
    r = get("/quota/status")
    print(f"[OK] quota/status → {r}")
except Exception as e:
    print(f"[WARN] quota/status: {e}")

sys.exit(0 if ok else 1)
