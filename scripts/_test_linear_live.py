"""
Script de prueba live para Linear client (corre local con .env).
Ejecutar: python scripts/_test_linear_live.py
"""
import sys
import os
from pathlib import Path

# Cargar .env
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip()
            # Descartar líneas con null bytes u otros caracteres de control
            if k and all(ord(c) >= 32 for c in k) and all(ord(c) >= 32 for c in v):
                os.environ.setdefault(k, v)

sys.path.insert(0, str(Path(__file__).parent.parent))
from worker import linear_client

api_key = os.environ.get("LINEAR_API_KEY", "")
if not api_key or "CHANGE_ME" in api_key:
    print("ERROR: LINEAR_API_KEY no configurada en .env")
    sys.exit(1)

print("=== 1. list_teams ===")
teams = linear_client.list_teams(api_key)
print("Teams:", teams)
assert teams, "No teams found"
team_id = teams[0]["id"]
team_name = teams[0]["name"]
print(f"Usando: {team_name} ({team_id})\n")

print("=== 2. create_issue ===")
issue = linear_client.create_issue(
    api_key=api_key,
    team_id=team_id,
    title="[Test P1] Issue equipo Marketing - routing automático",
    description="Issue de prueba para validar Phase 2 Linear routing.",
    priority=3,
)
print("Issue:", issue)
issue_id = issue["id"]
print(f"Identifier: {issue.get('identifier')} | URL: {issue.get('url')}\n")

print("=== 3. get_or_create_label ===")
lid1 = linear_client.get_or_create_label(api_key, team_id, "Marketing", "#F59E0B")
lid2 = linear_client.get_or_create_label(api_key, team_id, "Marketing Supervisor", "#EF4444")
print(f"Marketing label id: {lid1}")
print(f"Marketing Supervisor label id: {lid2}\n")

print("=== 4. update_issue (apply labels) ===")
label_ids = [l for l in [lid1, lid2] if l]
r = linear_client.update_issue(api_key, issue_id, label_ids=label_ids)
print("Update result:", r, "\n")

print("=== 5. get_state_id_by_name (Done) ===")
state_id = linear_client.get_state_id_by_name(api_key, team_id, "Done")
print(f"State 'Done' id: {state_id}\n")

print("=== 6. update_issue (state=Done + comment) ===")
r2 = linear_client.update_issue(
    api_key, issue_id,
    state_id=state_id,
    comment="Prueba P1 completada exitosamente. Labels y estado actualizados correctamente.",
)
print("Final update result:", r2)

print()
print("=== TODOS LOS TESTS PASARON ===")
print(f"Issue: {issue.get('identifier')} — {issue.get('url')}")
