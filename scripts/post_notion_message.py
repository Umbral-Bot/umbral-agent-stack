"""Post a message to Notion Control Room via Worker API."""
import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client.worker_client import WorkerClient

argv = sys.argv[1:]
msg = "Rick: ping"

if len(argv) >= 2 and argv[0] == "--base64":
    msg = base64.b64decode(argv[1]).decode("utf-8")
elif argv:
    msg = " ".join(argv).strip() or msg
else:
    stdin_text = sys.stdin.read().strip()
    if stdin_text:
        msg = stdin_text
wc = WorkerClient(
    base_url=os.environ.get("WORKER_URL", "http://127.0.0.1:8088"),
    token=os.environ.get("WORKER_TOKEN", ""),
)
result = wc.notion_add_comment(msg)
print(json.dumps(result, indent=2, ensure_ascii=False))
