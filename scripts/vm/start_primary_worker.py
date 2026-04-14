"""
Start the primary Worker (8088) from the live repository on Windows.

This bootstrap is meant to be launched by a hidden PowerShell wrapper and a
Task Scheduler task on the VM. It loads the repo .env first and falls back to
the Granola VM env file when WORKER_TOKEN is not already defined.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import env_loader  # noqa: E402
from scripts.vm.granola_watcher_env_loader import load_env  # noqa: E402

env_loader.load()
load_env()

if not os.environ.get("WORKER_TOKEN") and os.environ.get("GRANOLA_WORKER_TOKEN"):
    os.environ["WORKER_TOKEN"] = os.environ["GRANOLA_WORKER_TOKEN"]

host = os.environ.get("WORKER_HOST", "0.0.0.0")
port = int(os.environ.get("WORKER_PORT", "8088"))
log_level = os.environ.get("WORKER_LOG_LEVEL", "info")

if not os.environ.get("WORKER_TOKEN"):
    raise RuntimeError("WORKER_TOKEN not configured for primary worker startup")

uvicorn.run("worker.app:app", host=host, port=port, log_level=log_level)
