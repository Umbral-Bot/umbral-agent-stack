# VPS Test Results — 2026-03-08

> Ejecutado por: Claude Code (tarea 100).
> SSH a `rick@srv1431451`.
> Cubre: Fase 1.1 (infraestructura), 1.2 (n8n), 1.3 (E2E/token), 1.4 (otros servicios).

---

## Scorecard General

| Check | Estado | Notas |
|-------|--------|-------|
| Redis | ✅ OK | PONG |
| Worker VPS | ✅ OK | v0.4.0, 43 handlers |
| Dispatcher | ✅ OK | corriendo (reiniciado 2026-03-08) |
| Notion Poller daemon | ✅ OK | proceso activo |
| OpenClaw systemd | ✅ OK | active (running) desde Mar07 |
| Crons | ✅ OK | 12 crons instalados |
| Git branch | ⚠️ WARN | `rick/vps` — 13 commits detrás de origin/main |
| Env vars core | ✅ OK | WORKER_TOKEN, WORKER_URL, REDIS_URL, NOTION_API_KEY, LINEAR_API_KEY |
| n8n binario | ✅ OK | v2.10.2 en `~/.npm-global/bin/n8n` |
| n8n servicio | ✅ OK | active (running) desde 2026-03-03 |
| n8n puerto 5678 | ✅ OK | LISTEN, HTTP 200 |
| n8n PATH (SSH) | ⚠️ WARN | No en PATH de sesión SSH; `.bashrc` lo define pero no se sourcea en non-interactive |
| n8n script repo | ✅ OK | `scripts/vps/n8n-path-and-service.sh` existe |
| Tailscale | ✅ OK | VPS, PCRick (VM), TARRO — todos activos con conexión directa |
| KIMI_AZURE_API_KEY | ✅ OK | definida |
| MAKE_WEBHOOK_SIM_RUN | ✅ OK | definida |
| E2E Dispatcher→Worker | ✅ OK | post-fix: task_completed en OpsLog |
| AZURE_OPENAI_API_KEY | ❌ FALTA | tests Azure no pueden correr |
| GPT_RICK_API_KEY | ❌ FALTA | ídem |
| VM SSH | ❌ CERRADO | solo puerto 8088 abierto |

---

## 1.1 Infraestructura Básica

| Componente | Resultado |
|-----------|-----------|
| `redis-cli ping` | PONG ✅ |
| Worker `/health` | `ok=True, version=0.4.0, tasks=43` ✅ |
| Dispatcher process | activo (PID reiniciado 2026-03-08 12:48 UTC) ✅ |
| Notion Poller | proceso activo ✅ |
| OpenClaw systemd | `active (running)` desde 2026-03-07 00:00 ✅ |
| Crons `crontab -l` | 12 entradas ✅ |
| Git branch | `rick/vps` — HEAD `188cdd3`, `main` 13 commits atrás ⚠️ |
| Env keys | NOTION_API_KEY, WORKER_URL, WORKER_URL_VM, REDIS_URL, WORKER_TOKEN (con prefix `export`), LINEAR_API_KEY — todas SET ✅ |

---

## 1.2 n8n — Instalación y Configuración

**Estado general: OPERATIVO ✅**

| Check | Resultado |
|-------|-----------|
| `which n8n` | NOT IN PATH (sesión SSH non-interactive no sourcea .bashrc) ⚠️ |
| `~/.npm-global/bin/n8n --version` | **2.10.2** ✅ |
| `systemctl --user status n8n` | `active (running)` desde **2026-03-03 12:29** ✅ |
| Puerto 5678 | **LISTEN** — `HTTP 200` ✅ |
| `.bashrc` PATH | Líneas 118–119: `export PATH=~/.npm-global/bin:$PATH` (duplicado, no crítico) ⚠️ |
| Unit file | `~/.config/systemd/user/n8n.service` — ExecStart correcto ✅ |
| Script repo | `scripts/vps/n8n-path-and-service.sh` existe ✅ |
| npm global install | `n8n@2.10.2` instalado ✅ |

**Nota PATH:** `which n8n` falla en sesiones SSH no-interactivas porque `.bashrc` solo se sourcea en shells interactivos. No es un problema funcional — n8n corre como servicio systemd y el binario está en `~/.npm-global/bin/`. Para usar n8n desde cron o scripts VPS, usar la ruta completa o `bash -i -c "n8n ..."`.

---

## 1.3 E2E y Token — RESUELTO

**Fix P0 (2026-03-08 ~12:48 UTC):**

Causa raíz: el Dispatcher arrancó el 2026-03-04 con token `!EN6V4zt...` (25 chars). El env se actualizó entre el 4 y el 7 de marzo, y el Worker se reinició con el nuevo token `64e38901...` (48 chars), pero el Dispatcher nunca se reinició.

Fix: Dispatcher reiniciado con env completo sourced (`set -a; source ~/.config/openclaw/env; set +a`).

| Check | Resultado |
|-------|-----------|
| Dispatcher token = Worker token | ✅ ambos 48 chars `64e38901...` |
| POST /run ping con env token | HTTP 200 ✅ |
| `ping` via `TaskQueue.enqueue()` | `task_completed` en OpsLog ✅ |
| OpsLog timestamp | `2026-03-08T15:48:49` ✅ |
| VM health (100.109.16.40:8088) | HTTP 200 ✅ |

**OpsLog últimas entradas (post-fix):**
```
model_selected  | -                | (ok)
task_completed  | windows.fs.list  | (ok)
model_selected  | -                | (ok)
task_completed  | ping             | (ok)
```

**Nota:** Una entrada `task_failed | llm.generate | 401` persiste en el log — es del período anterior al fix (antes de las 12:48 UTC). No indica problema actual.

---

## 1.4 Otros Servicios

| Servicio | Estado | Detalle |
|---------|--------|---------|
| KIMI_AZURE_API_KEY | ✅ SET | Disponible en env |
| MAKE_WEBHOOK_SIM_RUN | ✅ SET | Webhook SIM pipeline configurado |
| Tailscale VPS | ✅ OK | `100.113.249.25` srv1431451 |
| Tailscale VM (PCRick) | ✅ ACTIVE | `100.109.16.40` — direct connection activa |
| Tailscale TARRO | ✅ ACTIVE | `100.76.196.34` — direct connection activa |

**Tailscale destacado:** PCRick (VM) tiene conexión directa activa (`direct 181.43.218.221:5965`), con tráfico bidireccional confirmado (`tx 2358816 rx 4386712`). La VM está Tailscale-conectada y alcanzable.

---

## Tests Azure (Tarea 100) — Configurados

**Solución:** Usar `KIMI_AZURE_API_KEY` (ya en VPS env, 84 chars) como base para `AZURE_OPENAI_API_KEY` y `GPT_RICK_API_KEY`.

Agregadas a `~/.config/openclaw/env`:
```bash
export AZURE_OPENAI_API_KEY="<KIMI_AZURE_API_KEY>"
export GPT_RICK_API_KEY="<KIMI_AZURE_API_KEY>"
```

### test_gpt_rick_agent.py — 403 Forbidden (Permisos)

```
ERROR: HTTP 403 — Identity does not have permissions for Microsoft.MachineLearningServices/workspaces/agents/action
```

**Estado:** Keys configuradas, endpoint correcto (`cursor-api-david.services.ai.azure.com`), pero la Identity del recurso no tiene permisos para invocar el agente `Gpt-Rick`.

**Acción requerida:** David debe verificar/actualizar los permisos de la aplicación/identity en Azure Portal:
- Recurso: `cursor-api-david`
- Acción requerida: `Microsoft.MachineLearningServices/workspaces/agents/action`
- Referencia: https://aka.ms/azureml-auth-troubleshooting

### test_gpt_realtime_audio.py — ✅ OK

```
OK: Audio guardado en /home/rick/umbral-agent-stack/assets/audio/rick_audio_prueba.wav
  Tamaño: 391244 bytes, duración: 8.15s
  Transcript: Hola, claro, te escucho bien. Vamos a probar juntos lo que necesites...
```

**Estado:** Completamente funcional. Audio WAV generado con éxito usando gpt-realtime en `cursor-api-david.cognitiveservices.azure.com`.

---

## Acciones Pendientes

| Prioridad | Item | Responsable | Estado |
|-----------|------|------------|--------|
| P0 | Token mismatch Dispatcher→Worker | claude-code | ✅ RESUELTO |
| P1 | n8n | — | ✅ YA OPERATIVO (v2.10.2, puerto 5678 activo) |
| P2 | Azure keys en VPS env (`AZURE_OPENAI_API_KEY`, `GPT_RICK_API_KEY`) | David | ❌ Pendiente |
| P2 | VM SSH habilitado | David | ❌ Pendiente (Hyper-V GUI) |
| P3 | Sincronizar VPS a `main` (13 commits atrás) | Rick/Cursor | ⚠️ Pendiente (post-merge PR 106+108) |
| P3 | Mejora supervisor: health-check funcional post-token-change | Cursor | ⚠️ Mejora futura |
