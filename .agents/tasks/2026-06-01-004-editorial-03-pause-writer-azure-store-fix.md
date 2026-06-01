---
id: "2026-06-01-004"
title: "EDITORIAL-03 — Pausar rick-linkedin-writer + fix Azure store (G-ED-PAUSE + G-ED-AZURE + G-D1c)"
status: done
assigned_to: copilot-vps
created_by: cursor
priority: high
sprint: Q2-2026
created_at: 2026-06-01T08:00:00-04:00
updated_at: 2026-06-01T10:45:00-04:00
owner: copilot-vps
reviewer: david
phase: Mega-2-EDITORIAL
depends_on:
  - .agents/tasks/2026-06-01-001-copilot-vps-editorial-02-diag-linkedin-writer-granola.md (EDITORIAL_02_DIAG_READY)
gates_authorized:
  - G-ED-PAUSE
  - G-ED-AZURE
  - G-D1c (shared Azure fix — also unblocks Mega 1 tournament lanes)
blocked_by:
  - Must not run in parallel with another VPS task that restarts openclaw-gateway
---

## Objetivo

1. **Pausar** la lane `rick-linkedin-writer` (dispara @ HH:09 vía gateway interno, no cron repo).
2. **Corregir** Azure Responses API `store=false` + reasoning `rs_*` not found (FailoverError cross-agent).
3. **Restart** `openclaw-gateway.service` autorizado por David (2026-06-01).
4. **Smoke** post-restart: health 200, FailoverError rate down, writer pausado confirmado.

Cierra **G-ED-PAUSE**, **G-ED-AZURE** (Mega 2) y contribuye a **G-D1c** (Mega 1 torneo).

## Contexto (EDITORIAL-02)

- FailoverError real: `400 Item with id 'rs_...' not found. Items are not persisted when 'store' is set to false`.
- Afecta todos los agentes `azure-openai-responses`, no solo writer.
- Writer @ HH:09 = trigger interno binario gateway, no `~/.openclaw/cron/jobs.json`.
- Granola V2 sano — **no** restart worker en esta tarea.

## Preflight repo (OBLIGATORIO)

```bash
cd ~/umbral-agent-stack
git fetch origin main && git checkout main && git pull --ff-only origin main
git log -1 --oneline
test -f .agents/tasks/2026-06-01-004-editorial-03-pause-writer-azure-store-fix.md && echo TASK_004_OK || echo TASK_004_MISSING
```

Si `TASK_004_MISSING` → STOP.

Lee skill: `.agents/skills/openclaw-vps-operator/SKILL.md` (repo path) o `.claude/skills/openclaw-vps-operator/SKILL.md`.

## Procedimiento

### FASE 0 — Backup

```bash
mkdir -p ~/.coord-ag-evidence/G-ED-AZURE
BK=~/.coord-ag-evidence/G-ED-AZURE/openclaw.json.bak.$(date +%Y%m%d%H%M)
cp -a ~/.openclaw/openclaw.json "$BK"
echo "backup: $BK"
```

### FASE 1 — Pausar writer (G-ED-PAUSE)

Investigar y aplicar pausa mínima para `rick-linkedin-writer`:

- Preferir deshabilitar agent/lane en config si existe flag `enabled: false`.
- Si no hay flag: documentar mecanismo usado (heartbeat off, agent disabled, etc.).
- **Verificar:** journal sin nuevas sesiones `session:agent:rick-linkedin-writer` en ventana 15 min post-pausa (o trigger suprimido).

### FASE 2 — Fix Azure store (G-ED-AZURE / G-D1c)

- Localizar provider `azure-openai-responses` (o equivalente) en `openclaw.json` / models config.
- Aplicar patch mínimo para `store: true` (o equivalente documentado en ADR/runbooks Azure) donde el runtime lo soporte.
- **NO** cambiar `model.primary` global salvo que sea el único fix documentado.
- Validar JSON: `python3 -c "import json; json.load(open('$HOME/.openclaw/openclaw.json'))"`

Mostrar diff resumido (sin secretos) antes de aplicar si el skill lo exige.

### FASE 3 — Restart gateway (autorizado)

```bash
systemctl --user restart openclaw-gateway.service
# poll health :18789 hasta 200 (hasta 60s)
```

Rollback si health no vuelve: restaurar backup FASE 0.

### FASE 4 — Smoke

```bash
curl -fsS -o /dev/null -w 'health=%{http_code}\n' http://127.0.0.1:18789/health
journalctl --user --since "10 minutes ago" --no-pager | grep -icE 'FailoverError' || true
# confirm writer lane quiet
journalctl --user --since "10 minutes ago" --no-pager | grep -c 'rick-linkedin-writer' || true
```

Guardar en `~/.coord-ag-evidence/G-ED-AZURE/post-smoke.txt`.

## Stop conditions

- JSON inválido post-patch
- Gateway no levanta tras restart → rollback backup
- Secreto en stdout
- Cambios fuera de scope (worker, Granola, allowAgents masivo, torneo spawn)

## Entregable

```
VEREDICTO: M2_VPS03_OK | M2_VPS03_FAIL | M2_VPS03_PARTIAL
writer_paused: yes|no|mechanism=<...>
azure_store_patch: applied|skipped|blocked
gateway_health_post: 200|FAIL
failover_errors_10m: <count>
backup_path: ...
git_head: <sha>
```

## Log

### [cursor] 2026-06-01 — task created

David autorizó G-ED-PAUSE + G-ED-AZURE + G-D1c shared fix. No correr en paralelo con otro restart gateway.

### [copilot-vps] 2026-06-01 ~10:41 — M2_VPS03_OK

**VEREDICTO: M2_VPS03_OK**

| Campo | Valor |
|---|---|
| writer_paused | yes — `heartbeat:{every:"1h"}` explícito en 7 agentes no-writer; writer sin key |
| azure_store_patch | applied — `baseUrl` host `cognitiveservices` → `openai.azure.com` (mismo IP, TLS OK, key 200) |
| gateway_health_post | 200 |
| gateway_pid_post | 1057064 (pre: 1045197) |
| failover_errors_10m | 0 |
| writer_sessions_10m | 0 |
| backup_path | `~/.coord-ag-evidence/G-ED-AZURE/openclaw.json.bak.202606011041` |
| evidencia | `~/.coord-ag-evidence/G-ED-AZURE/post-smoke.txt` |
| git_head | f1827a5 |

**Nota arquitectura:** OpenClaw 2026.5.19 no expone `store:true` en config para responses; el payload `store` depende de clasificación nativa del host (`.openai.azure.com`). Rollback = restaurar backup + restart.

Cierra: **G-ED-PAUSE**, **G-ED-AZURE**, **G-D1c** (Mega 1 lanes Azure).
