# Copilot handoff prompts (Windows + VPS)

Copy-paste blocks for David. Cursor updates this file when creating VPS tasks.
**Rule:** Cursor must push `main` before you paste a VPS prompt.

Last push for prompts below: **`c8d5bc90`** (2026-06-01).

---

## Thread A — Copilot-VPS · D3.1 torneo real (#403)

**Cuándo:** nuevo hilo Copilot con acceso SSH VPS, o hilo VPS existente limpio.

```
Sos Copilot-VPS (rick@srv1431451.hstgr.cloud). Lee y ejecuta la tarea:

  ~/umbral-agent-stack/.agents/tasks/2026-06-01-008-d3.1-tournament-issue-403.md

Preflight obligatorio (PROTOCOL.md):
  cd ~/umbral-agent-stack && git pull --ff-only origin main && git log -1 --oneline
  test -f .agents/tasks/2026-06-01-008-d3.1-tournament-issue-403.md && echo TASK_FILE_OK

Skill: openclaw-vps-operator + publication-gatekeeper (merge solo con rubric + autorización en task).

David autorizó torneo real D3.1 y merge del winner si cumple rubric del spec YAML.
NO reinicies gateway salvo allowAgents roto. Evidencia en ~/.coord-ag-evidence/D3.1/

Al cerrar: VEREDICTO en el Log de la task + comentario en issue #403 con JSON métricas.
```

---

## Thread B — Copilot-VPS · O15 delegación smoke

**Cuándo:** hilo VPS separado (no mezclar con torneo activo si main está ocupado).

```
Sos Copilot-VPS. Ejecuta smoke de delegación O15 (read-only + traza):

  ~/umbral-agent-stack/.agents/tasks/2026-06-01-009-copilot-vps-o15-delegation-smoke.md

Preflight: git pull --ff-only origin main en ~/umbral-agent-stack.

Objetivo: una delegación orchestrator → rick-ops (health read-only), registro en
~/.openclaw/trace/delegations.jsonl, reporte a main. NO torneo, NO openclaw.json writes.

VEREDICTO esperado: O15_DELEGATION_SMOKE_OK o bloqueo honesto con evidencia.
```

---

## Thread C — Copilot Windows · D5.1 OAuth discovery (read-only)

**Cuándo:** Copilot Chat en VS Code / Windows, sin SSH.

```
Sos Copilot Windows (workstation David). Tarea read-only D5.1 prep:

  c:\GitHub\umbral-agent-stack\.agents\tasks\2026-06-01-010-copilot-windows-o15-gmail-calendar-discovery.md

NO toques VPS ni openclaw.json. Inventaria en Windows + repo qué falta para OAuth
rick.asistente@gmail.com (Gmail + Calendar + Notion guest): creds, env vars, docs ADR-16.

Entrega: tabla gaps + recomendación de siguiente gate para David. Sin prometer OAuth live.
```

---

## Thread D — Copilot Windows · Revisar spec torneo (opcional)

```
Revisá en repo umbral-agent-stack (main):

  openclaw/workspace-templates/skills/multi-agent-tournament-orchestrator/examples/d31-issue-403-tournament-spec.yaml

¿El scope de lanes sqlite-impl / sqlite-qa es acotado y mergeable? Sugerí ajustes al
winner_rubric o task_template sin ejecutar nada en VPS.
```
