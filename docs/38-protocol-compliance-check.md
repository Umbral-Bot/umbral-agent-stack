# 38 — Verificación de cumplimiento de protocolos

Checklist para comprobar que el stack cumple con los protocolos definidos: dashboard, Linear, Notion, board de agentes, etc. Revisar periódicamente (o cuando Cursor integre trabajo de otros agentes).

---

## Script de verificación (antes de n8n u otros cambios)

Para comprobar que todo funciona **como está ahora** (env, Worker, Redis, Linear, tareas del Worker).

**Regla VPS:** En la VPS no hay `python` global; usar siempre **`.venv`** (`source .venv/bin/activate`). Scripts nuevos requieren **`git pull origin main`** antes de ejecutarlos (si no, "No such file or directory").

**En la VPS (verificación completa — env, Redis, Linear, tareas):**
```bash
cd ~/umbral-agent-stack && git pull origin main
source .venv/bin/activate
export $(grep -v '^#' ~/.config/openclaw/env | xargs)
PYTHONPATH=. python scripts/verify_stack_vps.py
```

**Alternativa en la VPS (sin git pull):** Verificación rápida (solo OpenClaw, Tailscale, Worker health; no comprueba Redis/Notion/Linear):
```bash
cd ~/umbral-agent-stack
export $(grep -v '^#' ~/.config/openclaw/env | xargs)
bash scripts/vps/verify-openclaw.sh
```

**En local (Windows, leyendo `.env`):**
```powershell
cd C:\GitHub\umbral-agent-stack
python scripts/verify_stack_vps.py
```

El script Python comprueba: variables de entorno necesarias, Worker `/health`, Redis, que el Worker tenga `notion.update_dashboard` y `linear.list_teams`, y prueba Linear llamando al Worker. No escribe en Notion. Tras ver que todo da OK, probar el dashboard real con `scripts/dashboard_report_vps.py` (sección 5 del output).

---

## Estado de verificación (2026-03-03)

Verificación desde repo (código y config). Lo que requiere VPS o Notion/Linear solo se puede confirmar en el entorno real.

| Área | En repo / config | En VPS o externo (confirmar con Rick/David) |
|------|------------------|---------------------------------------------|
| **.agents/** | OK: PROTOCOL.md, board.md, tasks con formato; 2026-03-03-001 y 002 done. | — |
| **Dashboard** | OK: `notion.update_dashboard` en Worker; `dashboard_report_vps.py` y `dashboard-cron.sh` existen; `install-cron.sh` instala cron cada 15 min. | Cron instalado en VPS (`install-cron.sh` o crontab); `~/.config/openclaw/env` con `NOTION_DASHBOARD_PAGE_ID`, `NOTION_API_KEY`, `WORKER_URL`, `WORKER_TOKEN`, `REDIS_URL`; página Dashboard Rick actualizándose. |
| **Notion Control Room** | OK: Worker usa `NOTION_CONTROL_ROOM_PAGE_ID`; doc 18 y 22 referencian. | `NOTION_CONTROL_ROOM_PAGE_ID` en env VPS/Worker; poller programado (XX:10); Enlace y Rick siguen convención. |
| **Linear** | OK: `linear.create_issue`, `linear.list_teams` en Worker; AGENTS.md indica uso por Rick. | `LINEAR_API_KEY` en `~/.config/openclaw/env` (VPS); probar listar equipos / crear issue. |
| **n8n** | OK: doc 37; script `n8n-path-and-service.sh`. | **Confirmado por Rick:** instalado, servicio user systemd activo, PATH configurado (2026-03-03). |
| **Variables env** | `.env.example` tiene NOTION_DASHBOARD, WORKER_*, LINEAR, etc. Faltaba `NOTION_CONTROL_ROOM_PAGE_ID` en plantilla → añadido. | En VPS: `~/.config/openclaw/env` con todas las necesarias para Worker, dashboard y poller. |

**Acciones pendientes (en la VPS o por David):** (1) Confirmar que el cron del dashboard está instalado y que el Dashboard Rick en Notion se actualiza. (2) Confirmar que `NOTION_CONTROL_ROOM_PAGE_ID` y `NOTION_DASHBOARD_PAGE_ID` están en el env de la VPS. (3) Probar Linear (listar equipos o crear issue de prueba).

## 1. Protocolo inter-agentes (`.agents/`)

| Elemento | Qué comprobar | Referencia |
|----------|----------------|------------|
| **PROTOCOL.md** | Todos los agentes deben leerlo al inicio. Reglas: Cursor = lead; un agente a la vez; coordinación por archivos en `.agents/`. | `.agents/PROTOCOL.md` |
| **board.md** | Actualizado por Cursor tras crear/cerrar tareas. Tareas con estado correcto (assigned, done, blocked). | `.agents/board.md` |
| **tasks/** | Una tarea = un archivo `YYYY-MM-DD-NNN-slug.md` con frontmatter (status, assigned_to, etc.) y Log al terminar. | `.agents/tasks/` |
| **GitHub Copilot** | Si la tarea indica "para GitHub Copilot", usar credenciales desde `.env`; no commitear `.env`; actualizar Log al terminar. | PROTOCOL.md sección Copilot |

**Acción:** Al iniciar sesión, Cursor debe leer `board.md` y revisar tareas `done` o `blocked` para integrar trabajo. Antigravity/Codex leen `board.md` y trabajan solo en tareas con su `assigned_to`.

---

## 2. Dashboard Rick (Notion)

| Elemento | Qué comprobar | Referencia |
|----------|----------------|------------|
| **Página Dashboard Rick** | Existe en Notion; integración con acceso; ID en `NOTION_DASHBOARD_PAGE_ID` en env (VPS / Worker). | doc 22 |
| **Script dashboard_report_vps.py** | Se ejecuta en la VPS (cron o systemd timer cada 15–30 min). Requiere: `WORKER_URL`, `WORKER_TOKEN`, `REDIS_URL`, `NOTION_DASHBOARD_PAGE_ID`, `NOTION_API_KEY` (y opcional `WORKER_URL_VM`). | `scripts/dashboard_report_vps.py`, doc 22 |
| **Worker** | Tarea `notion.update_dashboard` registrada; Worker con env Notion correcto para poder escribir en la página del dashboard. | `worker/tasks/notion.py`, doc 22 |

**Acción:** Confirmar en la VPS que el cron/timer existe (ej. `scripts/vps/dashboard-cron.sh` o crontab) y que el dashboard en Notion se actualiza (última actualización reciente).

---

## 3. Notion — Control Room y Enlace

| Elemento | Qué comprobar | Referencia |
|----------|----------------|------------|
| **Control Room** | Página de Notion con ID en `NOTION_CONTROL_ROOM_PAGE_ID` (o equivalente en env). Poller de Rick lee comentarios a las XX:10. | doc 18, AGENTS.md |
| **Enlace Notion ↔ Rick** | Rick revisa comentarios a las XX:10; usa "Hola @Enlace," para dirigirse al agente; responde "Rick: Recibido." al procesar. | doc 18, AGENTS.md |
| **Poller** | Dispatcher/Notion poller ejecutable en la VPS; encola tareas según comentarios en Control Room. | doc 18 |

**Acción:** Verificar que el poller está programado y que Rick/Enlace siguen la convención de comentarios (sin bucles "Rick:").

---

## 4. Linear

| Elemento | Qué comprobar | Referencia |
|----------|----------------|------------|
| **LINEAR_API_KEY** | En `.env` (local) y en `~/.config/openclaw/env` (VPS); no en el repo. | doc 30 |
| **Rick → Linear** | Rick puede crear issues con `linear.create_issue` o `scripts/linear_create_issue.py`; conoce equipos con `linear.list_teams`. | AGENTS.md, doc 30 |
| **Cursor** | Linear MCP solo lectura (no crea/actualiza issues; eso lo hace Rick). | doc 30 |

**Acción:** Probar desde la VPS (o con script local) que la API key de Linear permite listar equipos y crear un issue de prueba en el workspace correcto.

---

## 5. Otros canales y servicios

| Elemento | Qué comprobar | Referencia |
|----------|----------------|------------|
| **Telegram** | Si se usa para instrucciones a Rick: token en env; Rick prioriza tareas vía Notion o Telegram según configuración. | AGENTS.md, overview |
| **Redis** | Cola `umbral:tasks:pending` / `blocked` en la VPS; Worker y Dispatcher usan la misma `REDIS_URL`. | doc 20, dashboard_report_vps |
| **Worker VM** | Si está en uso: `WORKER_URL_VM` (y opcional `WORKER_URL_VM_INTERACTIVE`) en env VPS; Worker en VM con NSSM y repo actualizado. | doc 32, runbook VM |
| **n8n (VPS)** | Si Rick instaló n8n: servicio activo, puerto 5678 (o el configurado), credenciales en n8n (no en repo). | doc 37 |

---

## 6. Resumen de acciones recomendadas

1. **Cursor (lead):** Revisar `board.md` y tareas en `.agents/tasks/`; cerrar o actualizar tareas completadas; asignar nuevas según prioridad.
2. **Dashboard:** Comprobar que el cron de `dashboard_report_vps.py` está activo en la VPS y que la página Dashboard Rick en Notion se actualiza.
3. **Linear:** Verificar que `LINEAR_API_KEY` está configurada donde Rick/scripts la usan y que crear issue / listar equipos funciona.
4. **Notion:** Confirmar IDs de Control Room y Dashboard en env del Worker/VPS; poller y Enlace operativos.
5. **n8n:** Tras instalación por Rick, documentar URL de acceso (Tailscale o interna) y que los flujos usen credenciales propias de n8n.

Si algún ítem no se cumple, crear tarea en `.agents/tasks/` o anotar en el board para asignar a quien corresponda (Cursor, Codex, Rick, o David).
