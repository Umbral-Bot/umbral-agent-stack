#!/usr/bin/env python3
"""
Smoke directo para research.web contra el Worker configurado.

Objetivo:
- verificar rápidamente si Tavily responde bien en runtime real
- distinguir de inmediato entre éxito, cuota, auth/config, timeout o fallo upstream
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx

CALLER_ID = "script.research_web_smoke"


def _load_env() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    env_files = []
    if os.name != "nt":
        env_files.append(Path(os.environ.get("HOME", "")) / ".config/openclaw/env")
    env_files.append(repo_root / ".env")
    for p in env_files:
        if p.exists():
            raw = p.read_text(encoding="utf-8", errors="ignore").replace("\x00", "")
            for line in raw.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip().strip('"').strip("'").replace("\x00", "").replace("\r", "")
                if k.startswith("export "):
                    k = k[7:].strip()
                if k:
                    os.environ[k] = v
            break


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Umbral-Caller": CALLER_ID,
    }


def main() -> int:
    _load_env()

    parser = argparse.ArgumentParser(description="Smoke directo de research.web")
    parser.add_argument("--query", default="BIM trends 2026", help="Consulta a probar")
    parser.add_argument("--count", type=int, default=3, help="Cantidad de resultados")
    args = parser.parse_args()

    base_url = (os.environ.get("WORKER_URL") or "").rstrip("/")
    token = os.environ.get("WORKER_TOKEN") or ""

    if not base_url or not token:
        print("ERROR: faltan WORKER_URL y/o WORKER_TOKEN", file=sys.stderr)
        return 1

    with httpx.Client(timeout=40.0) as client:
        resp = client.post(
            f"{base_url}/run",
            headers=_headers(token),
            json={"task": "research.web", "input": {"query": args.query, "count": args.count}},
        )

    print(f"HTTP {resp.status_code}")
    try:
        data = resp.json()
    except Exception:
        print(resp.text[:1200])
        return 1

    print(json.dumps(data, ensure_ascii=False, indent=2)[:1600])

    if resp.status_code != 200:
        return 1

    result = data.get("result", {})
    print(f"OK: engine={result.get('engine')} count={result.get('count')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
