# Tarea Claude — Test VPS + Fix (incorpora PR 108 y auditoría)

---
id: "2026-03-07-100"
title: "Test en VPS + fix según resultados (incorpora PR 108 Rick)"
status: assigned
assigned_to: claude-code
created_by: cursor
priority: high
sprint: R21
created_at: "2026-03-07"
updated_at: "2026-03-07"
---

## Objetivo

1. **Testear en la VPS** que lo documentado/declarado existe y está configurado como se describe.
2. **Incorporar antecedentes del PR 108** (Rick): modelo Linear-first, identity/, .rick/, linear_create_issue mejorado.
3. **Con los resultados del test**, solucionar discrepancias y bloqueos (token mismatch, n8n, etc.).

---

## Antecedentes — PR 108 (Rick)

Rick consolidó en el PR 108 (rama `rick/vps`):

- **Modelo operativo Linear-first:** `docs/34-linear-first-operating-model.md`
- **Identity:** `identity/01-perfil.md`, `02-servicios-actuales.md`, `03-servicios-potencia.md`, `05-modelo-propuesto.md`, `06-estrategia-marketing.md`
- **Carpeta .rick/:** `README.md`, `LOG.md` (bitácora de Rick)
- **Script linear_create_issue.py:** nuevos flags `--trace-id`, `--umbral-team`, `--owner-agent`, `--objective`, `--dod`, `--artifacts-path`
- **Runbook:** actualización en `docs/62-operational-runbook.md`
- **setup-ssh-vm.ps1**, **vm-ssh-key-diagnostic.ps1**

Mergear o incorporar PR 108 antes/durante esta tarea para tener el contexto completo.

---

## Fase 1 — Test en VPS (verificar realidad vs docs)

Conectarte a la VPS vía SSH (`rick@100.113.249.25` o `rick@srv1431451`) y ejecutar checks. Documentar resultados en `docs/audits/vps-test-results-YYYY-MM-DD.md`.

### 1.1 Infraestructura básica

| Check | Comando | Qué verificar |
|-------|---------|---------------|
| Redis | `redis-cli ping` | PONG |
| Worker VPS | `curl -s http://127.0.0.1:8088/health` | ok, version, tasks_registered |
| Dispatcher | `ps aux | grep dispatcher` | proceso activo |
| Notion Poller | `ps aux | grep notion_poller` | proceso activo |
| OpenClaw | `systemctl --user status openclaw` | active (running) |
| Crons | `crontab -l` | 11–12 crons según runbook |
| Git branch | `cd ~/umbral-agent-stack && git branch -v` | main vs rick/vps, HEAD |
| Env | `grep -E 'WORKER_TOKEN|WORKER_URL|REDIS_URL' ~/.config/openclaw/env | cut -c1-50` | keys presentes (no valores) |

### 1.2 n8n — instalación y configuración

La documentación afirma que n8n está instalado en la VPS (Rick confirmó 2026-03-03). **Verificar en vivo:**

| Check | Comando | Qué verificar |
|-------|---------|---------------|
| n8n en PATH | `which n8n` o `~/.npm-global/bin/n8n --version` | binario existe |
| Servicio n8n | `systemctl --user status n8n` | active o inactive |
| Puerto 5678 | `ss -tlnp | grep 5678` o `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5678` | escucha o responde |
| PATH en .bashrc | `grep -n "npm-global\|n8n" ~/.bashrc` | PATH configurado |
| Unit systemd | `cat ~/.config/systemd/user/n8n.service` (si existe) | ExecStart correcto |
| Script de setup | `test -f ~/umbral-agent-stack/scripts/vps/n8n-path-and-service.sh && echo OK` | script existe en repo |

Referencias: `docs/37-n8n-vps-automation.md`, `scripts/vps/n8n-path-and-service.sh`, `docs/38-protocol-compliance-check.md` (n8n confirmado por Rick 2026-03-03).

### 1.3 E2E y token

| Check | Comando | Qué verificar |
|-------|---------|---------------|
| Token en env | `source ~/.config/openclaw/env && echo ${#WORKER_TOKEN}` | longitud (no valor) |
| Worker acepta token | `source ~/.config/openclaw/env && curl -s -X POST http://127.0.0.1:8088/run -H "Authorization: Bearer $WORKER_TOKEN" -H "Content-Type: application/json" -d '{"task":"ping","input":{}}'` | 200 o 401 |
| OpsLog | `tail -5 ~/.config/umbral/ops_log.jsonl` | task_failed 401 vs task_completed |
| Cola Redis | `redis-cli LLEN umbral:queue` | pendientes |

### 1.4 Otros servicios declarados

| Check | Referencia | Comando sugerido |
|-------|------------|------------------|
| Kimi/Azure | `docs/kimi-recurso-n8n.md` | `grep KIMI ~/.config/openclaw/env \| cut -c1-20` |
| Make.com webhook | SIM pipeline | `grep MAKE_WEBHOOK ~/.config/openclaw/env \| cut -c1-30` |
| Tailscale | IPs VPS/VM | `tailscale status` |

---

## Fase 2 — Documentar resultados

Crear `docs/audits/vps-test-results-YYYY-MM-DD.md` con:

- Scorecard: OK / WARN / FAIL por cada check.
- Evidencia (salidas truncadas, sin secretos).
- Discrepancias: "doc dice X, realidad es Y".
- Lista de fixes necesarios (P0, P1, P2).

---

## Fase 3 — Solucionar según resultados

Con el scorecard de Fase 2:

1. **P0 — Token mismatch**  
   Si Dispatcher → Worker da 401: identificar por qué el token difiere (parsing de env, export prefix, etc.) y corregir. Criterio: encolar `ping` vía Redis → `task_completed` en OpsLog.

2. **P1 — n8n**  
   Si n8n no está instalado/configurado como doc 37:
   - Ejecutar `scripts/vps/n8n-path-and-service.sh`
   - Activar servicio: `systemctl --user enable --now n8n`
   - Documentar URL de acceso (Tailscale) y credenciales (fuera del repo)

3. **P2 — Branch y sync**  
   Si VPS está en `rick/vps`: coordinar con Rick para `git pull origin main` tras merge de PR 108 y PR 106; actualizar docs si hace falta.

4. **P3 — VM**  
   Si aplica: SSH a VM (Rick puede hacerlo desde VPS), verificar Worker en Windows nativo, token alineado. Referencia: `docs/audits/audit-results-2026-03-07.md`, `docs/62-operational-runbook.md` §7.2.1.

---

## Criterios de aceptación

- [ ] Test ejecutado en VPS y resultados en `docs/audits/vps-test-results-*.md`
- [ ] n8n verificado: instalado, PATH, servicio, puerto 5678 (o documentado qué falta)
- [ ] Token mismatch resuelto (P0) o diagnóstico claro de causa
- [ ] Fixes aplicados según prioridad (P0 → P1 → P2)
- [ ] PR con cambios + doc de resultados

---

## Referencias

- PR 108: `feat: standard operating model and linear issue creation improvements` (rama `rick/vps`)
- PR 106: auditoría 2026-03-07, tarea 099 (token mismatch)
- `docs/audits/audit-results-2026-03-07.md`
- `docs/37-n8n-vps-automation.md`
- `docs/62-operational-runbook.md`
- `docs/34-linear-first-operating-model.md`
- `scripts/vps/n8n-path-and-service.sh`
