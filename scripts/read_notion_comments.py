"""Read recent Notion Control Room comments."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client.worker_client import WorkerClient

wc = WorkerClient(
    base_url=os.environ.get("WORKER_URL", "http://127.0.0.1:8088"),
    token=os.environ.get("WORKER_TOKEN", ""),
)
limit = int(sys.argv[1]) if len(sys.argv) > 1 else 5
result = wc.notion_poll_comments(limit=limit)
for c in result.get("comments", []):
    ts = c.get("created_time", "?")[:19]
    text = (c.get("text") or "").strip()[:120]
    print(f"[{ts}] {text}")
