#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from infra.registry_backup_alert import evaluate_backup_alert


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Alert when registry backup logs show 2 consecutive daily failures.",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=None,
        help="Override the registry backup log directory. Defaults to %LOCALAPPDATA%\\umbral-registry-backup or the env override.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=60,
        help="Maximum number of recent log files to inspect (default: 60).",
    )
    args = parser.parse_args(argv)

    evaluation = evaluate_backup_alert(
        log_dir=args.log_dir,
        max_files=args.max_files,
    )
    print(evaluation.summary)
    return 1 if evaluation.alert else 0


if __name__ == "__main__":
    sys.exit(main())
