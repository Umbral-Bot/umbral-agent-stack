"""Post a message to Notion Control Room via Worker API."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client.worker_client import WorkerClient

msg = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else "Rick: ping"
if len(sys.argv) <= 1:
    stdin_text = sys.stdin.read().strip()
    if stdin_text:
        msg = stdin_text
wc = WorkerClient(
    base_url=os.environ.get("WORKER_URL", "http://127.0.0.1:8088"),
    token=os.environ.get("WORKER_TOKEN", ""),
)
result = wc.notion_add_comment(msg)
print(json.dumps(result, indent=2, ensure_ascii=False))
