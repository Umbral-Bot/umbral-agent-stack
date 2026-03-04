"""Post a message to Notion Control Room via Worker API."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client.worker_client import WorkerClient

msg = sys.argv[1] if len(sys.argv) > 1 else "Rick: ping"
wc = WorkerClient(
    base_url=os.environ.get("WORKER_URL", "http://127.0.0.1:8088"),
    token=os.environ.get("WORKER_TOKEN", ""),
)
result = wc.notion_add_comment(msg)
print(json.dumps(result, indent=2, ensure_ascii=False))
