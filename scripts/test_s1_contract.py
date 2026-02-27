#!/usr/bin/env python3
"""S1 Contract Validation — run from VPS against VM worker."""
import json
import urllib.request
import urllib.error

URL = "http://100.109.16.40:8088"
TOKEN = "test-token-12345"
AUTH = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

def post(path, payload, headers=AUTH):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"{URL}{path}", data=data, headers=headers)
    try:
        r = urllib.request.urlopen(req, timeout=10)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

def get(path, headers=None):
    h = headers or {"Authorization": f"Bearer {TOKEN}"}
    req = urllib.request.Request(f"{URL}{path}", headers=h)
    try:
        r = urllib.request.urlopen(req, timeout=10)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

print("=" * 50)
print("S1 Contract Validation — VPS -> VM")
print("=" * 50)

# 1. Health
code, data = get("/health")
ok = code == 200 and data.get("version") == "0.3.0"
print(f"\n1. HEALTH: {'PASS' if ok else 'FAIL'} ({code})")
print(f"   {data}")

# 2. Legacy format
code, data = post("/run", {"task": "ping", "input": {"from": "vps-legacy"}})
ok = code == 200 and "task_id" in data
print(f"\n2. LEGACY: {'PASS' if ok else 'FAIL'} ({code})")
print(f"   {data}")

# 3. Envelope format
code, data = post("/run", {
    "schema_version": "0.1",
    "team": "system",
    "task_type": "health",
    "task": "ping",
    "input": {"e2e": True}
})
ok = code == 200 and "task_id" in data and data.get("team") == "system"
print(f"\n3. ENVELOPE: {'PASS' if ok else 'FAIL'} ({code})")
print(f"   {data}")

# 4. No auth (expect 401)
code, data = post("/run", {"task": "ping", "input": {}}, headers={"Content-Type": "application/json"})
ok = code == 401
print(f"\n4. NO AUTH: {'PASS' if ok else 'FAIL'} ({code} — expected 401)")
print(f"   {data}")

# 5. GET /tasks
code, data = get("/tasks")
ok = code == 200 and "tasks" in data
print(f"\n5. GET TASKS: {'PASS' if ok else 'FAIL'} ({code})")
print(f"   {data}")

# 6. GET /tasks/<id> for a task we created
if "task_id" in (post("/run", {"task":"ping","input":{"lookup":1}})[1]):
    tid = post("/run", {"task":"ping","input":{"lookup":1}})[1]["task_id"]
    code, data = get(f"/tasks/{tid}")
    ok = code == 200
    print(f"\n6. GET TASK BY ID: {'PASS' if ok else 'FAIL'} ({code})")
    print(f"   {data}")

print("\n" + "=" * 50)
print("DONE")
print("=" * 50)
