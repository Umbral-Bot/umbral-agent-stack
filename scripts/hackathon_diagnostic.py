#!/usr/bin/env python3
"""
Hackathon Diagnostic — Diagnóstico automatizado completo del sistema Umbral.

Verifica todos los componentes, genera reporte de estado y métricas.
Diseñado para ejecutarse periódicamente como health check del sistema.

Uso:
  cd ~/umbral-agent-stack && source .venv/bin/activate
  PYTHONPATH=. python scripts/hackathon_diagnostic.py [--json] [--markdown]

Salida:
  Por defecto: stdout con colores
  --json: salida JSON para integración
  --markdown: salida Markdown para documentación
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


def _load_env() -> None:
    for p in [
        Path(os.environ.get("HOME", "")) / ".config/openclaw/env",
        repo_root / ".env",
    ]:
        if p.exists():
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip('"').strip("'")
                os.environ.setdefault(k, v)
            break


_load_env()


class DiagnosticResult:
    def __init__(self):
        self.checks: list[dict[str, Any]] = []
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.overall = "unknown"

    def add(self, category: str, name: str, status: str, detail: str = "", data: Any = None):
        self.checks.append({
            "category": category,
            "name": name,
            "status": status,
            "detail": detail,
            "data": data,
        })

    def compute_overall(self):
        statuses = [c["status"] for c in self.checks]
        if all(s == "ok" for s in statuses):
            self.overall = "healthy"
        elif any(s == "critical" for s in statuses):
            self.overall = "critical"
        elif any(s == "error" for s in statuses):
            self.overall = "degraded"
        elif any(s == "warning" for s in statuses):
            self.overall = "warning"
        else:
            self.overall = "unknown"

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "overall": self.overall,
            "checks": self.checks,
            "summary": {
                "total": len(self.checks),
                "ok": sum(1 for c in self.checks if c["status"] == "ok"),
                "warning": sum(1 for c in self.checks if c["status"] == "warning"),
                "error": sum(1 for c in self.checks if c["status"] == "error"),
                "critical": sum(1 for c in self.checks if c["status"] == "critical"),
            },
        }


def check_env_vars(result: DiagnosticResult):
    required = {
        "WORKER_URL": "Worker base URL",
        "WORKER_TOKEN": "Worker auth token",
        "REDIS_URL": "Redis connection URL",
        "NOTION_API_KEY": "Notion API integration key",
        "NOTION_CONTROL_ROOM_PAGE_ID": "Notion Control Room page",
        "NOTION_DASHBOARD_PAGE_ID": "Notion Dashboard page",
    }
    optional = {
        "WORKER_URL_VM": "Worker VM URL",
        "LINEAR_API_KEY": "Linear API key",
        "NOTION_TASKS_DB_ID": "Notion tasks DB",
        "NOTION_GRANOLA_DB_ID": "Notion Granola DB",
        "TAVILY_API_KEY": "Tavily search API",
    }

    missing = []
    for key, desc in required.items():
        val = os.environ.get(key)
        if val:
            result.add("env", key, "ok", f"Configured ({len(val)} chars)")
        else:
            missing.append(key)
            result.add("env", key, "error", f"MISSING — {desc}")

    for key, desc in optional.items():
        val = os.environ.get(key)
        if val:
            result.add("env", key, "ok", f"Configured ({len(val)} chars)")
        else:
            result.add("env", key, "warning", f"Optional not set — {desc}")


def check_worker(result: DiagnosticResult, url: str, name: str):
    try:
        import httpx
        r = httpx.get(f"{url}/health", timeout=10)
        if r.status_code == 200:
            data = r.json()
            tasks = data.get("tasks_registered", [])
            result.add("worker", name, "ok", f"{len(tasks)} tasks registered", data)
        else:
            result.add("worker", name, "error", f"HTTP {r.status_code}")
    except Exception as e:
        result.add("worker", name, "error", f"Offline ({type(e).__name__})")


def check_redis(result: DiagnosticResult):
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    try:
        import redis
        r = redis.from_url(redis_url, decode_responses=True)
        r.ping()
        pending = r.llen("umbral:tasks:pending")
        blocked = r.llen("umbral:tasks:blocked")
        result.add("redis", "connection", "ok", f"Connected (pending={pending}, blocked={blocked})")

        task_count = 0
        cursor = 0
        while True:
            cursor, keys = r.scan(cursor, match="umbral:task:*", count=200)
            task_count += len(keys)
            if cursor == 0:
                break
        result.add("redis", "task_history", "ok" if task_count > 0 else "warning",
                    f"{task_count} task records in Redis")

        quota_keys = []
        cursor = 0
        while True:
            cursor, keys = r.scan(cursor, match="umbral:quota:*", count=100)
            quota_keys.extend(keys)
            if cursor == 0:
                break
        result.add("redis", "quotas", "ok" if quota_keys else "warning",
                    f"{len(quota_keys)} quota keys")

    except Exception as e:
        result.add("redis", "connection", "error", f"Failed ({type(e).__name__}: {e})")


def check_ops_log(result: DiagnosticResult):
    try:
        from infra.ops_logger import OpsLogger
        ol = OpsLogger()
        if not ol.path.exists():
            result.add("ops", "ops_log", "warning", "File does not exist (no operations recorded)")
            return

        events = ol.read_events(limit=10000)
        if not events:
            result.add("ops", "ops_log", "critical", "EMPTY — Zero operations recorded. System is inactive.")
            return

        completed = sum(1 for e in events if e.get("event") == "task_completed")
        failed = sum(1 for e in events if e.get("event") == "task_failed")
        blocked = sum(1 for e in events if e.get("event") == "task_blocked")

        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        completed_today = sum(
            1 for e in events
            if e.get("event") == "task_completed" and e.get("ts", "").startswith(today)
        )
        completed_yesterday = sum(
            1 for e in events
            if e.get("event") == "task_completed" and e.get("ts", "").startswith(yesterday)
        )

        models_used = set()
        for e in events:
            if e.get("model"):
                models_used.add(e["model"])

        first_ts = events[0].get("ts", "")
        last_ts = events[-1].get("ts", "")

        result.add("ops", "ops_log", "ok",
                    f"{len(events)} events, {completed} completed, {failed} failed, {blocked} blocked",
                    {
                        "total": len(events),
                        "completed": completed,
                        "failed": failed,
                        "blocked": blocked,
                        "completed_today": completed_today,
                        "completed_yesterday": completed_yesterday,
                        "models_used": list(models_used),
                        "first_event": first_ts,
                        "last_event": last_ts,
                    })

        if completed_today == 0 and completed_yesterday == 0:
            result.add("ops", "activity", "critical",
                        "No tasks completed in last 48h — system appears inactive")
        elif completed_today == 0:
            result.add("ops", "activity", "warning",
                        f"No tasks today (yesterday: {completed_yesterday})")
        else:
            result.add("ops", "activity", "ok",
                        f"Today: {completed_today}, Yesterday: {completed_yesterday}")

    except Exception as e:
        result.add("ops", "ops_log", "error", f"Failed to read ops log: {e}")


def check_quota_utilization(result: DiagnosticResult):
    try:
        import yaml
        policy_path = repo_root / "config" / "quota_policy.yaml"
        if not policy_path.exists():
            result.add("quotas", "policy", "warning", "quota_policy.yaml not found")
            return

        with open(policy_path) as f:
            policy = yaml.safe_load(f)
        providers = policy.get("providers", {})

        try:
            import redis as redis_lib
            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
            r = redis_lib.from_url(redis_url, decode_responses=True)
            r.ping()

            for name, cfg in providers.items():
                limit = int(cfg.get("limit_requests", 100))
                used = int(r.get(f"umbral:quota:{name}:used") or 0)
                pct = round((used / limit * 100) if limit > 0 else 0, 1)
                status = "ok" if pct < 70 else ("warning" if pct < 90 else "critical")

                if used == 0:
                    result.add("quotas", name, "warning",
                               f"UNUSED — 0/{limit} requests (subscription idle)")
                else:
                    result.add("quotas", name, status,
                               f"{used}/{limit} ({pct}%)")
        except Exception:
            for name in providers:
                result.add("quotas", name, "warning", "Cannot check — Redis unavailable")

    except Exception as e:
        result.add("quotas", "policy", "error", f"Failed: {e}")


def check_agent_board(result: DiagnosticResult):
    board_path = repo_root / ".agents" / "board.md"
    if not board_path.exists():
        result.add("agents", "board", "error", "board.md not found")
        return

    content = board_path.read_text()
    tasks_dir = repo_root / ".agents" / "tasks"
    task_files = list(tasks_dir.glob("*.md")) if tasks_dir.exists() else []

    pending = sum(1 for f in task_files if "status: pending" in f.read_text())
    in_progress = sum(1 for f in task_files if "status: in_progress" in f.read_text())
    done = sum(1 for f in task_files if "status: done" in f.read_text())
    blocked = sum(1 for f in task_files if "status: blocked" in f.read_text())
    assigned = sum(1 for f in task_files if "status: assigned" in f.read_text())

    result.add("agents", "board", "ok",
               f"{len(task_files)} tasks total (pending={pending}, assigned={assigned}, "
               f"in_progress={in_progress}, done={done}, blocked={blocked})")


def check_tests(result: DiagnosticResult):
    import subprocess
    try:
        env = os.environ.copy()
        env["WORKER_TOKEN"] = env.get("WORKER_TOKEN", "test")
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"],
            capture_output=True, text=True, cwd=str(repo_root), timeout=60, env=env,
        )
        output = proc.stdout.strip().split("\n")[-1] if proc.stdout else ""
        if proc.returncode == 0:
            result.add("tests", "pytest", "ok", output)
        else:
            result.add("tests", "pytest", "error", f"Exit {proc.returncode}: {output}")
    except Exception as e:
        result.add("tests", "pytest", "error", f"Failed to run: {e}")


def check_services(result: DiagnosticResult):
    import subprocess

    for svc in ["openclaw", "openclaw-worker-vps", "openclaw-dispatcher"]:
        try:
            proc = subprocess.run(
                ["systemctl", "--user", "is-active", svc],
                capture_output=True, text=True, timeout=5,
            )
            status = proc.stdout.strip()
            if status == "active":
                result.add("services", svc, "ok", "Active")
            else:
                result.add("services", svc, "warning", f"Status: {status}")
        except Exception:
            result.add("services", svc, "warning", "systemctl not available (cloud env?)")


def format_terminal(diag: DiagnosticResult) -> str:
    icons = {"ok": "✅", "warning": "⚠️ ", "error": "❌", "critical": "🔴"}
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"  DIAGNÓSTICO UMBRAL AGENT STACK")
    lines.append(f"  {diag.timestamp}")
    overall_icon = {"healthy": "🟢", "warning": "🟡", "degraded": "🟠", "critical": "🔴"}.get(diag.overall, "⚪")
    lines.append(f"  Estado general: {overall_icon} {diag.overall.upper()}")
    lines.append(f"{'='*60}\n")

    current_cat = ""
    for c in diag.checks:
        if c["category"] != current_cat:
            current_cat = c["category"]
            lines.append(f"\n📋 {current_cat.upper()}")
            lines.append(f"{'─'*40}")
        icon = icons.get(c["status"], "❓")
        lines.append(f"  {icon} {c['name']}: {c['detail']}")

    summary = diag.to_dict()["summary"]
    lines.append(f"\n{'='*60}")
    lines.append(f"  RESUMEN: {summary['ok']} OK, {summary['warning']} warnings, "
                 f"{summary['error']} errors, {summary['critical']} critical")
    lines.append(f"{'='*60}\n")
    return "\n".join(lines)


def format_markdown(diag: DiagnosticResult) -> str:
    icons = {"ok": "✅", "warning": "⚠️", "error": "❌", "critical": "🔴"}
    lines = [f"# Diagnóstico Umbral — {diag.timestamp}", ""]

    overall_icon = {"healthy": "🟢", "warning": "🟡", "degraded": "🟠", "critical": "🔴"}.get(diag.overall, "⚪")
    lines.append(f"**Estado general:** {overall_icon} {diag.overall.upper()}")
    lines.append("")

    current_cat = ""
    for c in diag.checks:
        if c["category"] != current_cat:
            current_cat = c["category"]
            lines.append(f"\n## {current_cat.upper()}\n")
            lines.append("| Check | Estado | Detalle |")
            lines.append("|-------|--------|---------|")
        icon = icons.get(c["status"], "❓")
        lines.append(f"| {c['name']} | {icon} | {c['detail']} |")

    summary = diag.to_dict()["summary"]
    lines.append(f"\n---\n**Resumen:** {summary['ok']} OK, {summary['warning']} warnings, "
                 f"{summary['error']} errors, {summary['critical']} critical")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Hackathon Diagnostic")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--markdown", action="store_true", help="Output Markdown")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest run")
    args = parser.parse_args()

    diag = DiagnosticResult()

    check_env_vars(diag)

    worker_url = os.environ.get("WORKER_URL", "http://localhost:8088").rstrip("/")
    check_worker(diag, worker_url, "Worker VPS")

    worker_vm = os.environ.get("WORKER_URL_VM", "").strip()
    if worker_vm:
        check_worker(diag, worker_vm, "Worker VM")

    check_redis(diag)
    check_ops_log(diag)
    check_quota_utilization(diag)
    check_agent_board(diag)
    check_services(diag)

    if not args.skip_tests:
        check_tests(diag)

    diag.compute_overall()

    if args.json:
        print(json.dumps(diag.to_dict(), indent=2, default=str))
    elif args.markdown:
        print(format_markdown(diag))
    else:
        print(format_terminal(diag))

    return 0 if diag.overall in ("healthy", "warning") else 1


if __name__ == "__main__":
    sys.exit(main())
