#!/usr/bin/env python3
"""
publish_tracking_demo.py — Generate demo publish tracking events.

Default mode is dry-run (prints JSON to stdout, no log writes).

Usage:
  python scripts/publish_tracking_demo.py
  python scripts/publish_tracking_demo.py --json
  python scripts/publish_tracking_demo.py --write-ops-log

This script never publishes anything.  It only generates sample
publish_attempt / publish_success / publish_failed events for
validating dashboards and log pipelines.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from infra.publish_tracking import (
    PublishEvent,
    build_publish_record,
    compute_content_hash,
)
from infra.ops_logger import OpsLogger


def _demo_records() -> list[dict[str, Any]]:
    """Build a set of representative demo events."""
    records: list[dict[str, Any]] = []

    # 1. Ghost attempt
    ghost_hash = compute_content_hash({"title": "Demo post", "body": "Hello world"})
    records.append(build_publish_record(
        event=PublishEvent.ATTEMPT.value,
        channel="ghost",
        content_hash=ghost_hash,
        notion_page_id="demo-notion-page-001",
        publication_id="pub-demo-001",
        attempt=1,
        source="publish_tracking_demo",
        source_kind="script",
    ))

    # 2. Ghost success
    records.append(build_publish_record(
        event=PublishEvent.SUCCESS.value,
        channel="ghost",
        content_hash=ghost_hash,
        notion_page_id="demo-notion-page-001",
        publication_id="pub-demo-001",
        platform_post_id="ghost-post-abc123",
        publication_url="https://example.ghost.io/demo-post/",
        attempt=1,
        source="publish_tracking_demo",
        source_kind="script",
    ))

    # 3. LinkedIn attempt
    li_hash = compute_content_hash("LinkedIn post about editorial automation")
    records.append(build_publish_record(
        event=PublishEvent.ATTEMPT.value,
        channel="linkedin",
        content_hash=li_hash,
        notion_page_id="demo-notion-page-002",
        attempt=1,
        source="publish_tracking_demo",
        source_kind="script",
    ))

    # 4. LinkedIn failed (auth expired)
    records.append(build_publish_record(
        event=PublishEvent.FAILED.value,
        channel="linkedin",
        content_hash=li_hash,
        notion_page_id="demo-notion-page-002",
        attempt=1,
        error_kind="auth_expired",
        error_code="401",
        retryable=False,
        source="publish_tracking_demo",
        source_kind="script",
    ))

    # 5. Manual publish success
    records.append(build_publish_record(
        event=PublishEvent.SUCCESS.value,
        channel="manual",
        content_hash=compute_content_hash("Manual post by David"),
        notion_page_id="demo-notion-page-003",
        platform_post_id="manual-confirmation",
        attempt=1,
        source="publish_tracking_demo",
        source_kind="script",
    ))

    # 6. Unknown channel attempt
    records.append(build_publish_record(
        event=PublishEvent.ATTEMPT.value,
        channel="tiktok",
        content_hash=compute_content_hash("future channel test"),
        attempt=1,
        source="publish_tracking_demo",
        source_kind="script",
    ))

    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate demo publish tracking events.",
    )
    parser.add_argument(
        "--write-ops-log",
        action="store_true",
        default=False,
        help="Write events to OpsLogger (default: dry-run).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output results as JSON array.",
    )
    args = parser.parse_args(argv)

    records = _demo_records()

    if args.write_ops_log:
        ops = OpsLogger()
        for record in records:
            event_name = record.get("event", "publish_attempt")
            method = getattr(ops, event_name, ops.publish_attempt)
            # Remove 'event' and 'status' since OpsLogger sets those
            kwargs = {k: v for k, v in record.items() if k not in ("event", "status")}
            method(**kwargs)
        print(f"Wrote {len(records)} publish tracking events to {ops.path}")
    else:
        if args.json:
            print(json.dumps(records, indent=2, default=str))
        else:
            for r in records:
                event = r["event"]
                channel = r["channel"]
                marker = {
                    "publish_attempt": "->",
                    "publish_success": "OK",
                    "publish_failed": "XX",
                }
                icon = marker.get(event, "??")
                hash_short = r.get("content_hash", "?")[:8]
                err = r.get("error_kind", "")
                suffix = f" error={err}" if err else ""
                print(f"  [{icon}] {channel}: {event} (hash={hash_short}){suffix}")
            print(f"\n{len(records)} demo events generated (dry-run, no log written).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
