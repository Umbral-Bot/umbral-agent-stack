"""Read raw comments from Notion API directly."""
import os, sys, httpx, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

page_id = os.environ.get("NOTION_CONTROL_ROOM_PAGE_ID", "")
token = os.environ.get("NOTION_API_KEY", "")

url = f"https://api.notion.com/v1/comments?block_id={page_id}&page_size=100"
headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"}
r = httpx.get(url, headers=headers, timeout=10)
data = r.json()

if r.status_code != 200:
    print(f"Error {r.status_code}: {data}")
    sys.exit(1)

results = data.get("results", [])
print(f"Total comments: {len(results)}")
for c in results[-10:]:
    text_parts = c.get("rich_text", [])
    text = "".join(p.get("plain_text", "") for p in text_parts)
    ts = c.get("created_time", "?")[:19]
    print(f"[{ts}] {text[:200]}")
