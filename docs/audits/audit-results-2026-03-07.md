# Resultados Auditoría Comprensiva — 2026-03-07

> Ejecutada en vivo: VPS (SSH), VM (HTTP API), TARRO (local).
> Auditor: Claude Code (Sonnet 4.6).

---

## Scorecard General

| Dim | Check | Estado | Detalle |
|-----|-------|--------|---------|
| A | VPS servicios | OK | redis, uvicorn worker, dispatcher, notion-poller corriendo |
| A | VPS crons | OK | 12/12 crons instalados |
| A | VPS git | WARN | Branch `rick/vps` (no `main`). Quick wins propios (#103/#104) |
| B | VM Worker health | OK | v0.4.0, 43 tasks, responde en :8088 (Tailscale + Hyper-V) |
| B | VM SSH/WinRM | FAIL | Puertos 22 y 5985 cerrados — solo :8088 abierto |
| B | VM git state | DESCONOCIDO | Sin acceso SSH/WinRM a PCRick |
| C | E2E Dispatcher→Worker | FAIL | Token mismatch (401): Dispatcher usa token diferente al Worker |
| C | VM alcanzable desde VPS | OK | Health checks HTTP 200 OK en 100.109.16.40:8088 |
| D | Notion Control Room | PENDIENTE | No verificado (sin debug extra hoy) |
| D | Notion Poller activo | OK | Proceso corriendo (PID 269682) desde 2026-03-04 |
| E | llm.generate Gemini | OK | Responde correctamente (`gemini-2.5-flash` activo) |
| E | Cuotas Redis | FAIL | Sin quota keys — Dispatcher no llega a despachar tareas |
| F | Quick wins en VPS | OK | PRs #103/#104 aplicados en branch rick/vps |
| G | OpsLogger | OK | 213 eventos en ~/.config/umbral/ops_log.jsonl |
| G | Langfuse/Docker | DESCONOCIDO | Sin acceso a VM para verificar |
| H | Dispatcher procesa tareas | FAIL | Despacha con 401 — colas no fluyen |
| H | LiteLLM desplegado | DESCONOCIDO | No verificado en VPS |

---

## Hallazgos Detallados

### A — VPS Infraestructura

**Procesos activos (PIDs estables desde días):**
```
redis-server     PID 28688  — desde Feb 27
notion-poller    PID 269682 — desde Mar 04
dispatcher       PID 287303 — desde Mar 04
uvicorn worker   PID 325733 — desde Mar 05
```

**12 crons instalados en crontab:**
- dashboard-cron.sh (*/15 min) — actualiza Notion, funciona bien (logs confirmados)
- health-check.sh (*/30 min) — OK (ops_log 213 eventos)
- supervisor.sh (*/5 min) — OK (Redis OK, Worker OK, Dispatcher OK)
- notion-poller-cron.sh (*/5 min) — logs vacíos (daemon ya corre)
- sim-report-cron.sh (30 8,14,20) — parcial ("Sin resumen disponible en llm.generate")
- sim-daily-cron.sh (0 8,14,20)
- daily-digest-cron.sh (0 22)
- sim-to-make-cron.sh (0 9,15,21)
- e2e-validation-cron.sh (0 6)
- ooda-report-cron.sh (0 7 lunes)
- scheduled-tasks-cron.sh (*/1 min)
- quota-guard-cron.sh (*/15 min) — activo

**Worker VPS (`http://127.0.0.1:8088`):** v0.4.0, 43 task handlers.
Mismo set que VM. Incluye: figma, document.create_*, granola, google.calendar, gmail, composite, azure.audio.

**Git:** Branch `rick/vps` (diverge de `main`). Commits propios de Rick con mejoras y quick wins (#103/#104). No está sincronizado con `main` ni con `audit-2026-03-quick-wins`.

---

### B — VM Windows (PCRick)

**Acceso:** Solo HTTP :8088. SSH (22) y WinRM (5985) cerrados. PowerShell Direct bloqueado (no Hyper-V admin en sesión actual).

**Worker VM vía HTTP:**
- URL desde TARRO: `http://172.31.10.195:8088/health` → 200 OK
- URL desde VPS: `http://100.109.16.40:8088/health` → 200 OK (Tailscale)
- Versión: 0.4.0
- Tasks registradas: 43 (mismo set que VPS)
- `tasks_in_memory: 0` — no ha procesado tareas recientemente

**No se pudo verificar:**
- Git state en VM (branch, commits, quick wins desplegados)
- Estado NSSM service
- Granola Watcher
- Langfuse Docker
- Logs del worker

---

### C — Flujo E2E: PROBLEMA CRÍTICO — Token Mismatch

**Problema identificado:** El Dispatcher usa `WORKER_TOKEN` del env para autenticarse contra ambos workers. El token en `~/.config/openclaw/env` (48 chars) **no coincide** con el token que tiene configurado el Worker.

Evidencia:
```
# Dispatcher → VPS Worker localhost:8088 → 401
OpsLog: task_failed, llm.generate, error: 401 Unauthorized for http://127.0.0.1:8088/run

# Dispatcher → VM Worker 100.109.16.40:8088 → 401
VPS test: curl http://100.109.16.40:8088/run -H "Bearer $WORKER_TOKEN" → {"detail":"Invalid or missing token"}
```

El Worker VPS SÍ funciona con el token correcto (cuando se hace `source ~/.config/openclaw/env` directamente, que expande el `export`). El Dispatcher posiblemente no lee el `export` prefix correctamente, o el worker fue reiniciado con un token diferente.

**Impacto:** NINGUNA tarea encolada en Redis llega a ejecutarse. El `scheduled-tasks-cron.sh` puede encolar tareas, pero el Dispatcher las expira o las falla con 401.

**OpsLog prueba el síntoma:** Las 213 entradas incluyen eventos de `task_failed` por 401. El último evento fue a las 17:00 UTC del 2026-03-07.

---

### E — LLM Usage

- `llm.generate` (`gemini-2.5-flash`) **funciona** cuando se invoca directamente al Worker con token correcto.
- Sin cuota keys en Redis (`redis-cli keys "quota:*"` → vacío) — el ModelRouter nunca completó dispatches exitosos.
- SIM report cron falla: "Sin resumen disponible en llm.generate para la ventana analizada" — porque el Dispatcher no despacha tareas exitosamente, no hay resultados que resumir.

---

### G — Observabilidad

- **OpsLogger activo:** `~/.config/umbral/ops_log.jsonl` con 213 eventos (en VPS).
- Último evento: 2026-03-07T17:00:02 (5+ horas antes de la auditoría).
- Eventos mayoritariamente: `task_failed` (401), `model_selected`.
- Langfuse: no verificado (VM inaccesible).

---

## Acciones Correctivas Prioritarias

### P0 — Fix token mismatch (desbloquea E2E)

El Dispatcher y el Worker deben usar el mismo token. Dos opciones:

**Opción A (recomendada):** Reiniciar Worker VPS cargando token desde env:
```bash
# En VPS:
source ~/.config/openclaw/env
# Matar y relanzar worker con el token que tiene el env actualmente
pkill -f "uvicorn worker.app"
cd ~/umbral-agent-stack && source .venv/bin/activate
WORKER_TOKEN="$WORKER_TOKEN" python3 -m uvicorn worker.app:app --host 127.0.0.1 --port 8088 &
```

**Opción B:** Actualizar el token en el env al valor que usa el Worker actualmente (requiere saber cuál es — puede verse en el proceso o en la config NSSM/systemd).

**Para VM:** El supervisor no puede reiniciar la VM worker porque no conoce el token. David debe entrar a la VM (GUI Hyper-V) y verificar/actualizar el token.

### P1 — Habilitar SSH en VM

Para poder auditar la VM remotamente y que los scripts de deploy funcionen, habilitar OpenSSH Server en PCRick:
```powershell
# En VM (con acceso GUI):
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'
New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

### P2 — Sincronizar branches

- VPS está en `rick/vps` — Rick hizo sus propios commits (identidad, Embudo V2, etc.)
- `main` tiene los quick wins de auditoría (`audit-2026-03-quick-wins`, PR #106 pendiente)
- Después de mergear PR #106, Rick debe hacer `git pull origin main` en VPS y VM

### P3 — VM_TOKEN en VPS env

Agregar el token correcto de la VM en `~/.config/openclaw/env` del VPS:
```
VM_TOKEN=<token-configurado-en-nssm-vm>
```
Y el Dispatcher debería usar ese token para las llamadas a la VM (actualmente usa el mismo WORKER_TOKEN para ambos).

---

## Métricas: Estado vs Objetivo

| Métrica | Objetivo | Estado Real |
|---------|----------|-------------|
| Tareas procesadas/día | >10 | ~0 (Dispatcher → 401) |
| LLM calls/día | >0 | ~0 (sin dispatches exitosos) |
| Dashboard actualizado | cada 15 min | OK (funciona vía cron directo) |
| OpsLog activo | Sí | OK (213 eventos, aunque mayormente errores) |
| E2E VPS → VM | OK | FAIL (token mismatch) |
| VM SSH accesible | Sí (runbooks) | NO (puerto 22 cerrado) |
| VM git actualizado | main | DESCONOCIDO |
