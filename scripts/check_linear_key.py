#!/usr/bin/env python3
"""One-off: load env from ~/.config/openclaw/env and call Linear API to check key."""
import os
import sys
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo))

# Load env like verify_stack
env_file = Path(os.environ.get("HOME", "")) / ".config/openclaw/env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k.startswith("export "):
            k = k[7:].strip()
        if k and k not in os.environ:
            os.environ.setdefault(k, v)

import httpx
key = os.environ.get("LINEAR_API_KEY", "")
if not key:
    print("LINEAR_API_KEY not set")
    sys.exit(1)
r = httpx.post(
    "https://api.linear.app/graphql",
    headers={"Authorization": key, "Content-Type": "application/json"},
    json={"query": "query { viewer { id } }"},
    timeout=10,
)
print(f"Linear API status: {r.status_code}")
if r.status_code != 200:
    print("Body:", r.text[:400])
