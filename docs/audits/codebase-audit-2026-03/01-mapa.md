# Mapa del Codebase — Umbral Agent Stack
> Auditoría: 2026-03-05 | Revisor: claude-sonnet-4-6 | Branch: `claude/090-implementar-notion-bitacora`

---

## 1. Módulos principales

### `worker/` — Execution Plane (FastAPI HTTP)
| Archivo | Rol |
|---------|-----|
| `app.py` | App FastAPI v0.4.0: 10 endpoints, middleware rate-limit, task dispatch |
| `config.py` | Centraliza todas las env vars; carga `~/.config/openclaw/env` en Linux |
| `rate_limiter.py` | `RateLimiter` clase — sliding window por IP, 60 RPM default (usado en `app.py`) |
| `rate_limit.py` | Módulo alternativo — sliding window con Lock global, 120 RPM default (usado en tests) |
| `sanitize.py` | Valida `task_name` y `input` (tamaño, caracteres) |
| `tracing.py` | Integración Langfuse (graceful degradation sin keys) |
| `tool_policy.py` | Política YAML de herramientas permitidas por equipo |
| `notion_client.py` | Cliente Notion API (httpx) — add_comment, poll_comments, upsert_task, dashboard, etc. |
| `linear_client.py` | Cliente Linear GraphQL |
| `linear_team_router.py` | Resuelve equipo Umbral → team/labels Linear desde `config/teams.yaml` |
| `models/` | Pydantic models: `TaskEnvelope`, `LegacyRunRequest`, `TaskResult`, `TaskStatus` |
| `tasks/` | 43 handlers agrupados por dominio (ver tabla abajo) |

**Handlers registrados en `worker/tasks/__init__.py` (43 total):**

| Prefijo | Tasks |
|---------|-------|
| `ping` | ping |
| `notion.*` | write_transcript, add_comment, poll_comments, upsert_task, update_dashboard, create_report_page, enrich_bitacora_page |
| `windows.*` | pad.run_flow, open_notepad, write_worker_token, firewall_allow_port, start_interactive_worker, add_interactive_worker_to_startup |
| `windows.fs.*` | ensure_dirs, list, read_text, write_text, write_bytes_b64 |
| `system.*` | ooda_report, self_eval |
| `linear.*` | create_issue, list_teams, update_issue_status |
| `research.*` | web |
| `llm.*` | generate |
| `composite.*` | research_report |
| `make.*` | post_webhook |
| `azure.*` | audio.generate |
| `figma.*` | get_file, get_node, export_image, add_comment, list_comments |
| `document.*` | create_word, create_pdf, create_presentation |
| `granola.*` | process_transcript, create_followup |
| `google.calendar.*` | create_event, list_events |
| `gmail.*` | create_draft, list_drafts |

---

### `dispatcher/` — Control Plane (VPS)
| Archivo | Rol |
|---------|-----|
| `service.py` | Loop principal: N threads (default 2), dequeue Redis → dispatch Worker local o VM |
| `queue.py` | `TaskQueue` — abstracción Redis LPUSH/RPOP (FIFO), sorted sets para tareas bloqueadas |
| `model_router.py` | `ModelRouter` — selección de LLM por `task_type` + estado de cuotas |
| `quota_tracker.py` | `QuotaTracker` — uso de cuotas en Redis (warn/restrict/exceeded) |
| `router.py` | `TeamRouter` — determina si tarea va a VPS worker o VM worker según `requires_vm` |
| `health.py` | `HealthMonitor` — hilo que verifica /health del Worker VM cada 10s |
| `alert_manager.py` | Envía alertas a Notion Control Room (rate-limited, cooldown 300s) |
| `notion_poller.py` | Lee comentarios Notion Control Room → encola tareas (cron XX:10 o intervalo) |
| `intent_classifier.py` | Clasifica intención de texto para routing |
| `smart_reply.py` | Generación de respuestas automáticas |
| `scheduler.py` | `TaskScheduler` — tareas futuras en Redis sorted set |
| `task_history.py` | `TaskHistory` — query y stats sobre `umbral:task:*` keys |
| `workflow_engine.py` | Motor de workflows multi-step |
| `team_config.py` | Carga `config/teams.yaml` |
| `linear_webhook.py` | Convierte webhooks Linear → `TaskEnvelope` |

---

### `client/` — SDK Python
| Archivo | Rol |
|---------|-----|
| `worker_client.py` | `WorkerClient` — httpx wrapper para `/run`, `/enqueue`, `/health`, shortcuts Notion |

---

### `infra/` — Infraestructura
| Archivo | Rol |
|---------|-----|
| `ops_logger.py` | Logger estructurado (JSONL) — task_queued, completed, failed, blocked, model_selected |
| `secrets.py` | Gestión de secretos (carga desde env, validación) |
| `tailscale_acl.py` | Gestión de ACLs Tailscale |
| `docker/` | Docker Compose scaffolds: hostinger, langfuse, local, litellm_config.yaml |
| `diagrams/` | Diagrama arquitectura Mermaid |

---

### `config/` — Configuración YAML
| Archivo | Rol |
|---------|-----|
| `teams.yaml` | Equipos: supervisor, roles, `requires_vm`, `notion_page_id` |
| `quota_policy.yaml` | Límites de cuota por proveedor LLM + routing preferido/fallback |
| `tool_policy.yaml` | Política de herramientas permitidas por equipo |
| `team_workflows.yaml` | Definición de workflows multi-step por equipo |

---

### `openclaw/` — Templates y Skills
- `workspace-templates/`: AGENTS.md, IDENTITY.md, SOUL.md, TOOLS.md, USER.md
- `workspace-templates/skills/`: 48+ skills (SKILL.md frontmatter YAML) para Rick
- `systemd/`: templates de unidades systemd para VPS
- `bin/`: scripts wrapper `worker-call` y `worker-run`
- `env.template`: plantilla de variables de entorno

---

### `scripts/` — Utilidades (60+ scripts)
Agrupados por función:

| Grupo | Scripts representativos |
|-------|------------------------|
| Operacional VPS | `verify_stack_vps.py`, `dashboard_report_vps.py`, `smoke_test.py`, `e2e_validation.py`, `integration_test.py` |
| Notion | `enrich_bitacora_pages.py`, `add_resumen_amigable.py`, `post_notion_message.py`, `setup_notion_tasks_db.py` |
| Linear | `linear_create_issue.py`, `audit_linear_worker.py`, `check_linear_key.py` |
| Observabilidad | `ooda_report.py`, `governance_metrics_report.py`, `quota_report.py`, `audit_traceability_check.py` |
| Research | `web_discovery.py`, `bing_search.py`, `sim_daily_report.py` |
| Skills | `validate_skills.py`, `build_skill.py`, `sync_skills_to_vps.py`, `skills_coverage_report.py` |
| Limpieza/admin | `borrar_ramas_r16_dry_run.py`, `cleanup_kanban_residues.py`, `ops_log_rotate.py` |
| Dev/diagnóstico | `hackathon_diagnostic.py`, `diagnose_google_cloud_apis.py`, `list_pending_blocked_tasks.py` |

Sub-carpetas: `scripts/vps/` (11 cron scripts bash+py), `scripts/windows/` (3 PowerShell), `scripts/vm/` (granola_watcher.py)

---

### `tests/` — Suite de tests
53 archivos de test, 900 tests passed (pytest). Cubre worker, dispatcher, todos los handlers, skills, governance, observabilidad, tracing, webhooks, workflows.

---

## 2. Entry Points — Cómo se arranca cada servicio

### VPS (Control Plane)

```bash
# Worker local en VPS (FastAPI :8088)
python3 -m uvicorn worker.app:app --host 0.0.0.0 --port 8088 --log-level info

# Dispatcher (N workers threads, lee Redis, despacha al Worker)
python3 -m dispatcher.service

# Notion Poller (daemon — polling XX:10 de cada hora)
python3 -m dispatcher.notion_poller
# O con cron: scripts/vps/notion-poller-cron.sh

# Stack completo de una vez
bash scripts/vps/full-stack-up.sh

# Crons (instalar una sola vez)
bash scripts/vps/install-cron.sh
```

**Servicios systemd (VPS):**
- `openclaw.service` — OpenClaw gateway principal
- `openclaw-dispatcher.service` — Dispatcher loop
- `openclaw-worker-vps.service` — Worker FastAPI en VPS

**11 Crons activos en VPS:**
dashboard, health-check, supervisor, notion-poller, SIM diario, SIM→Make, daily-digest, e2e-validation, OODA report, quota-guard, scheduled-tasks

---

### Windows VM (Execution Plane)

```powershell
# Modo dev
$env:WORKER_TOKEN="..."
python -m uvicorn worker.app:app --host 0.0.0.0 --port 8088

# Deploy automático (NSSM + deps)
.\scripts\deploy-vm.ps1

# Worker interactivo (sesión 1, puerto 8089)
# Ver runbooks/runbook-vm-interactive-worker-setup.md
```

---

### Scripts standalone

```bash
# E2E live (requiere WORKER_URL + WORKER_TOKEN)
PYTHONPATH=. python3 scripts/e2e_validation.py [--notion]

# Smoke test post-deploy
PYTHONPATH=. python3 scripts/smoke_test.py

# Integration test
PYTHONPATH=. python3 scripts/integration_test.py

# Enriquecer Bitácora Notion
python scripts/enrich_bitacora_pages.py [--dry-run] [--limit N]

# Dashboard Notion (ejecutar desde VPS via cron)
python3 scripts/dashboard_report_vps.py

# OODA report
python3 scripts/ooda_report.py
```

---

## 3. Dependencias críticas

### Runtime — Worker (`worker/requirements.txt`)
```
fastapi>=0.104.0,<1.0.0     # Framework HTTP
uvicorn[standard]>=0.24.0   # ASGI server
pydantic>=2.0.0             # Validación modelos
httpx>=0.25.0               # HTTP client (Notion, Figma, Linear, LLM)
requests>=2.28.0            # Usado en algunos handlers legacy
pyyaml>=6.0.0               # Config YAML
langfuse>=2.0.0             # Tracing observabilidad

# Document generation
python-docx>=1.1.0
docxtpl>=0.16.0
fpdf2>=2.7.0
weasyprint>=61.0            # PDF (requiere cairocffi/pango en Linux)
python-pptx>=0.6.23
openpyxl>=3.1.0
```

### Runtime — Dispatcher (`dispatcher/requirements.txt`)
```
redis>=5.0.0                # Cola + estado tareas
httpx>=0.25.0
PyYAML>=6.0
fastapi>=0.104.0            # (para enqueue API)
uvicorn[standard]>=0.24.0
```

### Tests
```
pytest>=7.0.0
fakeredis                   # Redis en memoria para unit tests
```

### No declaradas pero usadas (import dinámico / scripts)
- `redis` (en worker, importado lazy para `/enqueue`)
- `google-api-python-client`, `google-auth-*` (gmail, calendar tasks)
- `tavily` (research fallback)
- `azure-cognitiveservices-speech` (azure_audio task)
- `langfuse` (tracing — graceful si falta)
- `gh` CLI (GitHub CLI — usado por `enrich_bitacora_pages.py`)

---

## 4. Cómo se ejecuta

### Flujo principal (producción)

```
David → Telegram/Notion → OpenClaw (VPS)
                              ↓
                      POST /enqueue (Worker :8088)
                              ↓
                         Redis Queue
                              ↓
                    Dispatcher.service (N threads)
                         /              \
              WorkerClient(local:8088)  WorkerClient(VM:8088)
                         ↓                     ↓
               worker.app /run           worker.app /run
                         ↓
                    handler(input)
                         ↓
               Notion/Linear/LLM/etc.
```

### Variables de entorno mínimas

| Variable | Dónde | Descripción |
|----------|-------|-------------|
| `WORKER_TOKEN` | VPS + VM | Bearer token compartido |
| `WORKER_URL` | VPS | URL worker local (default `http://127.0.0.1:8088`) |
| `WORKER_URL_VM` | VPS (opt.) | URL worker VM vía Tailscale |
| `REDIS_URL` | VPS | Redis (default `redis://localhost:6379/0`) |
| `NOTION_API_KEY` | VPS + VM | Token integración Notion |
| `NOTION_CONTROL_ROOM_PAGE_ID` | VPS + VM | Página Control Room |
| `LINEAR_API_KEY` | VPS + VM (opt.) | API key Linear |
| `RATE_LIMIT_RPM` | VM | RPM rate limiter (default 60) |
| `DISPATCHER_WORKERS` | VPS | Threads del dispatcher (default 2) |

---

## 5. Cómo se testea

### Unit tests (suite principal)
```bash
# Windows
$env:WORKER_TOKEN="test"; python -m pytest tests/ -v

# Linux/VPS
WORKER_TOKEN=test python -m pytest tests/ -v --tb=short
```
- **866+ tests passed** (tras PR #96), 6 skipped, 0 failed
- Usa `fakeredis` — sin Redis real necesario
- Cubre todos los handlers, dispatcher, quota, skills, governance, workflows

### CI — GitHub Actions
- Trigger: push/PR a `main`
- Matrix: Python 3.11 + 3.12, ubuntu-latest
- Instala: `worker/requirements.txt` + `dispatcher/requirements.txt` + `fakeredis`
- Ejecuta: `pytest tests/ -v --tb=short` con `WORKER_TOKEN=test`
- Badge: `tests.yml`

### Scripts de validación (requieren entorno vivo)

| Script | Tests | Cuándo |
|--------|-------|--------|
| `scripts/e2e_validation.py` | 16 | Post-deploy, VPS con Worker online |
| `scripts/smoke_test.py` | 4 | Check rápido: ping + health |
| `scripts/integration_test.py` | 7 | Pipeline completo (Redis + Dispatcher + Worker) |
| `scripts/audit_traceability_check.py` | — | Trazabilidad de eventos ops_log |
| `scripts/validate_skills.py` | — | Valida frontmatter YAML de 48+ skills |

---

## 6. Top 10 Riesgos Técnicos (priorizados)

### R1 — `notion.enrich_bitacora_page` registrado pero parcialmente implementado ⚠️ CRÍTICO
El handler `handle_notion_enrich_bitacora_page` está en `worker/tasks/__init__.py` y en el registry, pero las 9 funciones soporte que necesita (`query_database`, `append_blocks_to_page`, `prepend_blocks_to_page`, `_block_code`, `_convert_block_for_write`, `_fetch_children_blocks`, `_sections_to_blocks`, `_raw_blocks_to_notion`, `_fetch_children_blocks`) **no existían en main hasta PR #96 en la rama actual**. Si PR #96 no se mergea, cualquier llamada a `notion.enrich_bitacora_page` fallará en producción silenciosamente. Los 34 tests de `test_notion_enrich_bitacora.py` también fallan sin esas funciones.

### R2 — Dos implementaciones de RateLimiter en paralelo ⚠️ ALTO
`worker/rate_limiter.py` (clase `RateLimiter`, 60 RPM, usada en `app.py` middleware) y `worker/rate_limit.py` (módulo global con Lock, 120 RPM, importado en tests) coexisten. La app usa `rate_limiter.py`; algunos tests importan `rate_limit.py`. Riesgo: limits inconsistentes, dead code, confusión en mantenimiento.

### R3 — Handlers síncronos bloquean threads FastAPI ⚠️ ALTO
Todos los `task_handlers` son funciones síncronas llamadas directamente desde `await` del endpoint `/run`. Tasks como `llm.generate`, `composite.research_report`, `document.create_pdf`, `azure.audio.generate` pueden tardar 30-120s. Con el pool de threads uvicorn por defecto, tareas largas concurrentes saturan el servidor. No hay async handlers ni timeout en la ejecución.

### R4 — Acoplamiento circular `worker.app` → `dispatcher.*` ⚠️ ALTO
`worker/app.py` importa dentro de funciones (`from dispatcher.queue import TaskQueue`, `from dispatcher.task_history import TaskHistory`, `from dispatcher.scheduler import TaskScheduler`, `from dispatcher.quota_tracker import QuotaTracker`, `from dispatcher.model_router import ...`). Esto acopla el Worker al Dispatcher: si el Worker corre sin el package `dispatcher` instalado (ej. imagen Docker mínima), falla en runtime al acceder a `/enqueue`, `/task/history`, `/scheduled`, `/quota/status`, `/providers/status`.

### R5 — `task_queued` nunca emitido en ops_log MEDIO
`scripts/audit_traceability_check.py` confirma que el evento `task_queued` **nunca se emite** en el ciclo de vida de una tarea. Los logs de observabilidad registran `model_selected`, `task_completed`, `task_failed`, `task_blocked`, pero el inicio del ciclo de vida queda ciego. Dificulta debugging y métricas de latencia end-to-end.

### R6 — Secretos en un único token compartido MEDIO
`WORKER_TOKEN` es un Bearer token único compartido entre VPS y VM. No hay rotación automatizada, scope por cliente, ni TTL. Una exposición del token compromete ambos planos. No hay mecanismo de revocación rápida en código.

### R7 — In-memory task store no persiste MEDIO
`_task_store` en `worker/app.py` es un `OrderedDict` en memoria (máx 1000 entries). Un restart del Worker borra todo el historial in-memory. El endpoint `GET /tasks/{task_id}` devolverá 404 tras reinicio incluso para tareas recientes. El historial Redis (`/task/{id}/status`) es el fallback, pero sólo si se usó `/enqueue`.

### R8 — `weasyprint` como dependencia de producción MEDIO
`weasyprint>=61.0` requiere `cairocffi`, `pango`, `fonttools` y otros paquetes de sistema que no están en `worker/requirements.txt`. En Linux (VPS), falla en runtime si no se instalan con `apt`. En el CI actual (ubuntu-latest), no se instalan paquetes de sistema, lo que significa que `document.create_pdf` no es testeado en CI y puede fallar en producción.

### R9 — Sprints S5, S6, S7 no implementados BAJO-MEDIO
El roadmap marca como pendientes:
- **S5**: Herramientas Windows PAD/RPA (handlers registrados como stubs)
- **S6**: Observabilidad completa (Langfuse evals, métricas reales)
- **S7**: Hardening transversal (autenticación multi-scope, rate limiting por token, mTLS)

Los handlers de PAD (`windows.pad.run_flow`) existen pero probablemente son stubs sin implementación real de RPA.

### R10 — Model IDs potencialmente ficticios BAJO
`PROVIDER_MODEL_MAP` en `dispatcher/service.py` y `app.py` mapea providers a strings como `"gpt-5.3-codex"`, `"gemini-3.1-pro-preview-customtools"`, `"gemini-flash-latest"`. Estos no corresponden a model IDs reales de ninguna API pública conocida a la fecha de auditoría. Las tareas `llm.generate` reciben estos strings como `model`, pero si el handler llama realmente a una API LLM, el string será rechazado. Sugiere que el routing de modelo es declarativo pero sin integración LLM real aún.

---

## 7. Ideas y Trabajo Parcial Perdido / No Integrado

### worker/ — No implementado / parcial
- **9 funciones `notion_client.py` + `tasks/notion.py`**: documentadas en `docs/bitacora-scripts.md` con firmas exactas. PR #96 en `claude/090-implementar-notion-bitacora` las implementa, pero no está mergeado a main aún.
- **`windows.pad.run_flow`**: handler registrado, pero la implementación real de PAD/RPA no existe (S5 pendiente).
- **`llm.generate`**: handler existe, pero no hay cliente LLM real integrado (router selecciona modelo pero el handler probablemente hace mock o llama a un endpoint local LiteLLM no siempre disponible).

### dispatcher/ — No implementado / pendiente
- **`task_queued` event**: nunca emitido (confirmado en `scripts/audit_traceability_check.py` línea 225: "task_queued nunca se emite — falta evento de inicio del ciclo de vida").
- **Notificación Telegram/Notion para `quota_exceeded_approval_required`**: `docs/11-roadmap-next-steps.md` lo menciona como "Telegram/Notion pendiente notificación" — el bloqueo ocurre pero no hay notificación proactiva al usuario.
- **WorkflowEngine**: `dispatcher/workflow_engine.py` existe con tests, pero no está integrado en `service.py`; se activa sólo si se invoca explícitamente.

### scripts/ — Scripts sin dependencias resueltas
- **`enrich_bitacora_pages.py`** y **`add_resumen_amigable.py`**: no ejecutables hasta que PR #96 se mergee (9 funciones faltantes en main).
- **`scripts/vm/granola_watcher.py`**: existe como script standalone de VM, pero no está integrado como tarea del Worker ni en ningún cron de VPS.
- **`scripts/vps/sim-daily-cron.sh`** y **`sim_daily_research.py`**: SIM (Sistema de Inteligencia de Mercado) tiene scripts de cron pero la integración con Make.com (`sim_to_make.py`) no está documentada como funcional.
- **`scripts/borrar_ramas_r16_dry_run.py`**: dry-run de borrado de 50+ ramas r16 — generado pero pendiente de ejecución real.

### docs/ — Planes no ejecutados
- **Browser automation VM** (`docs/64-browser-automation-vm-plan.md`): plan detallado + skill OpenClaw creado, pero sin implementación. Pendiente de S5.
- **n8n en VPS** (`docs/37-n8n-vps-automation.md`): referenciado como "Rick lo instala", sin evidencia de instalación real.
- **Migración Worker VM→VPS** (`docs/20-vm-to-vps-worker-migration.md`): plan documentado, la VPS tiene ahora un worker, pero la migración completa (dejar VM como opcional) está en progreso.
- **Drive Skills scan** (`reports/drive-skills-scan.md`): 4 carpetas META marcadas como `🔲 Pendiente` para evaluar.
- **S5-S7** del roadmap: PAD/RPA, evals Langfuse, hardening — todos sin iniciar según board.

### Ramas/PRs cerrados con trabajo útil (recuperado en R16)
- **`cursor/bit-cora-contenido-enriquecido-4099`** (PR #72 cerrado): contenido recuperado → `scripts/enrich_bitacora_pages.py`, `scripts/add_resumen_amigable.py`, `tests/test_notion_enrich_bitacora.py`
- **Rate limiter por provider** (rama cerrada recuperada en R16-084): recuperado → `worker/rate_limit.py`, `worker/rate_limiter.py`
- **11 PRs obsoletos** cerrados en R16-080: inventariados en `docs/branches-cerrados-inventario.md`
