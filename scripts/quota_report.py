#!/usr/bin/env python3
"""
Reporte de uso multi-modelo en Notion (Quota Dashboard).

Uso:
    python scripts/quota_report.py                 # imprime reporte sin publicar
    python scripts/quota_report.py --notion        # publica en Notion
"""

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

# Repo root in sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from client.worker_client import WorkerClient

logger = logging.getLogger("quota_report")
logging.basicConfig(level=logging.INFO, format="%(message)s")


def build_visual_report(quota_data: Dict[str, Any]) -> str:
    """Construye un reporte visual de cuotas con barras ASCII."""
    timestamp = quota_data.get("timestamp", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    providers = quota_data.get("providers", {})

    lines = [f"📊 Quota Report — {timestamp}", ""]

    if not providers:
        lines.append("No providers configured or Redis unavailable.")
        return "\n".join(lines)

    for provider, data in providers.items():
        used = data.get("used", 0)
        limit = data.get("limit", 100)
        fraction = data.get("fraction", 0.0)
        status = data.get("status", "ok")

        pct = int(fraction * 100)
        bars = int(min(1.0, fraction) * 10)
        visual = "█" * bars + "░" * (10 - bars)

        if status == "ok":
            icon = "✅ OK"
        elif status == "warn":
            icon = "⚠️ WARN"
        elif status == "restrict":
            icon = "🚫 RESTRICT"
        else:
            icon = "⛔ EXCEEDED"

        line = f"{provider:<15} {visual} {pct:3d}% ({used}/{limit}) {icon}"
        lines.append(line)

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera y publica reporte de cuotas.")
    parser.add_argument("--notion", action="store_true", help="Publica el reporte en Notion Control Room")
    parser.add_argument("--page-id", default=None, help="Page ID override para Notion")
    args = parser.parse_args()

    try:
        wc = WorkerClient()
    except ValueError as exc:
        logger.error("WorkerClient not available: %s", exc)
        return 1

    try:
        quota_data = wc.quota_status()
    except Exception as exc:
        logger.error("Failed to fetch quota status: %s", exc)
        return 1

    report = build_visual_report(quota_data)
    print(report)

    if args.notion:
        try:
            print("\nPublicando en Notion...")
            res = wc.notion_add_comment(text=report, page_id=args.page_id)
            print(f"Éxito: {res}")
        except Exception as exc:
            logger.error("Failed to post to Notion: %s", exc)
            return 2
    else:
        print("\n(Usa --notion para publicar)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
