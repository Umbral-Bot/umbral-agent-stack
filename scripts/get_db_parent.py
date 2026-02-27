#!/usr/bin/env python3
"""Obtiene el parent de una DB de Notion para usar como página padre."""
import os
import sys
import httpx

db_id = sys.argv[1] if len(sys.argv) > 1 else "3145f443fb5c80e189b1da79122feeb0"
api_key = os.environ.get("NOTION_API_KEY", "")
if not api_key:
    print("NOTION_API_KEY required", file=sys.stderr)
    sys.exit(1)

H = {"Authorization": f"Bearer {api_key}", "Notion-Version": "2022-06-28"}

r = httpx.get(f"https://api.notion.com/v1/databases/{db_id}", headers=H, timeout=10)
print(f"DB Status: {r.status_code}")
if r.status_code != 200:
    print(r.text[:500])
    sys.exit(1)

p = r.json().get("parent", {})
print(f"DB Parent: {p}")

if p.get("type") == "block_id":
    block_id = p["block_id"]
    r2 = httpx.get(f"https://api.notion.com/v1/blocks/{block_id}", headers=H, timeout=10)
    if r2.status_code == 200:
        bp = r2.json().get("parent", {})
        print(f"Block Parent: {bp}")
        if bp.get("type") == "page_id":
            page_id = bp["page_id"]
            print(f"Page ID (usar como NOTION_TASKS_PARENT_PAGE_ID): {page_id}")
