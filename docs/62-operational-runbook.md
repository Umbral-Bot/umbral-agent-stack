# 62 — Runbook Operacional y Checklist de Gobernanza

> Documento maestro para mantenimiento, gobernanza y troubleshooting de Umbral Agent Stack.
> Complementa [08-operations-runbook.md](08-operations-runbook.md) (OpenClaw) y [09-troubleshooting.md](09-troubleshooting.md).

---

## 1. Procedimientos de mantenimiento

### 1.1 Diario

| Procedimiento | Comando / Script | Qué verificar | Notas |
|---------------|------------------|---------------|-------|
| Verificar salud de servicios | `bash scripts/vps/supervisor.sh` | Redis, Worker y Dispatcher UP; auto-restart si caídos | Cron `*/5 min` ya lo ejecuta |
| Dashboard Notion | `PYTHONPATH=. python scripts/dashboard_report_vps.py` | Tareas recientes, métricas de salud, estado de Redis | Cron `*/15 min`; usar `--force` para forzar actualización |
| E2E validation | `PYTHONPATH=. python scripts/e2e_validation.py` | health, ping, research.web, llm.generate, enqueue, task history, Notion, Redis, quota, routing | Cron diario a las 06:00; `--notion` para postear resultados |
| Smoke test rápido | `PYTHONPATH=. python scripts/smoke_test.py` | Worker /health, ping, Redis, quota status | Para verificación rápida ad-hoc |
| Health check infraestructura | `bash scripts/vps/health-check.sh` | Redis, Worker, Dispatcher, ops_log | Cron `*/30 min` |

### 1.2 Semanal

| Procedimiento | Comando / Script | Qué verificar | Notas |
|---------------|------------------|---------------|-------|
| Quota report | `PYTHONPATH=. python scripts/quota_usage_report.py --notion` | Uso vs límites por provider, subutilización | `--hours 168 --all` para semana completa |
| OODA report | `PYTHONPATH=. python scripts/ooda_report.py --format markdown` | Resumen semanal: tareas, éxito/fallo, tokens, costo Langfuse | `--week-ago 1` para semana anterior |
| Stack verification | `PYTHONPATH=. python scripts/verify_stack_vps.py` | Env vars, Worker, Redis, Linear, dashboard | Verificación integral del stack |

### 1.3 Mensual

| Procedimiento | Comando / Script | Qué verificar | Notas |
|---------------|------------------|---------------|-------|
| Secrets audit | `python scripts/secrets_audit.py` | Sin secretos expuestos en código fuente | `--ci` para integración continua (exit 1 si hay hallazgos) |
| Secrets management | `python scripts/manage_secrets.py audit` | Estado de secretos cifrados y gestión de claves | Subcomandos: `genkey`, `encrypt`, `audit`, `list` |
| Revisar quota_policy.yaml | Editar `config/quota_policy.yaml` | Límites alineados con uso real, routing óptimo | Ajustar `warn` y `restrict` según tendencias |
| Revisar teams.yaml | Editar `config/teams.yaml` | Equipos y routing por equipo vigentes | — |

### 1.4 Variables de entorno requeridas

Archivo de configuración en VPS: `~/.config/openclaw/env`

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `WORKER_TOKEN` | Sí | Token Bearer para autenticación API |
| `WORKER_URL` | Sí | URL del Worker (ej. `http://localhost:8088`) |
| `REDIS_URL` | Sí | URL de conexión a Redis |
| `WORKER_URL_VM` | No | URL del Worker en VM (Execution Plane) |
| `NOTION_API_KEY` | Sí* | API key de Notion |
| `NOTION_DASHBOARD_PAGE_ID` | Sí* | Page ID del dashboard en Notion |
| `NOTION_CONTROL_ROOM_PAGE_ID` | Sí* | Page ID de la **Control Room** (solo comunicación Rick/Enlace/David; no usar para alertas automáticas) |
| `NOTION_SUPERVISOR_ALERT_PAGE_ID` | Recomendado | Page ID donde el supervisor postea el aviso de reinicio. **Definir una página aparte** (ej. "Alertas supervisor") para no llenar la Control Room de comentarios automáticos; si no se define, los avisos van a NOTION_CONTROL_ROOM_PAGE_ID. |
| `NOTION_GRANOLA_DB_ID` | No | Database ID para Granola |
| `LANGFUSE_PUBLIC_KEY` | No | Clave pública de Langfuse (graceful degradation sin ella) |
| `LANGFUSE_SECRET_KEY` | No | Clave secreta de Langfuse |
| `LANGFUSE_HOST` | No | Host de Langfuse |
| `RATE_LIMIT_RPM` | No | Límite de requests por minuto (default: 60) |
| `GOOGLE_API_KEY` | No | API key de Google AI Studio |
| `OPENAI_API_KEY` | No | API key de OpenAI |
| `ANTHROPIC_API_KEY` | No | API key de Anthropic |

*Requeridas para funcionalidades de Notion; sin ellas solo `ping` funciona completamente. Para que el aviso a Notion del supervisor funcione, el Worker debe tener `NOTION_API_KEY` y `NOTION_CONTROL_ROOM_PAGE_ID` (o `NOTION_SUPERVISOR_ALERT_PAGE_ID` si el script lo soporta) en su entorno al arrancar.

**Control Room solo para comunicación:** Para no llenar la Control Room de avisos automáticos (reinicios del supervisor), crear en Notion una página dedicada (ej. "Alertas supervisor" u "Ops") y definir `NOTION_SUPERVISOR_ALERT_PAGE_ID` con su ID en `~/.config/openclaw/env` en la VPS. Conectar la misma integración a esa página (••• → Add connections). Los avisos de reinicio irán ahí y la Control Room queda solo para Rick/Enlace/David.

### 1.5 Notion: conectar la integración a la página

Para que la API de Notion pueda leer/escribir una página (p. ej. comentarios en Control Room o actualizar el Dashboard), **la integración debe estar conectada a esa página**. Si no, la API puede devolver 403 o el comentario no aparecerá.

Pasos (según [Add & manage integrations – Notion Help](https://www.notion.com/help/add-and-manage-connections-with-the-api)):

1. En Notion, abre la **página** donde debe actuar la integración (Control Room, Dashboard, etc.).
2. Clic en **•••** (arriba a la derecha).
3. Abajo del menú, **Add connections**.
4. Busca y selecciona la **conexión** correspondiente a tu integración (la que usa `NOTION_API_KEY`). Solo aparecen conexiones ya asociadas al workspace.
5. La conexión quedará activa en esa página; la API podrá crear comentarios, bloques, etc.

Si el aviso del supervisor sigue fallando con 200 desde el Worker pero no ves el comentario en Notion, comprueba que la integración esté conectada a la página cuyo ID es `NOTION_CONTROL_ROOM_PAGE_ID` (o `NOTION_SUPERVISOR_ALERT_PAGE_ID`).

---

## 2. Crons activos en VPS

| Frecuencia | Script | Función |
|------------|--------|---------|
| `*/5 min` | `supervisor.sh` | Auto-restart Worker/Dispatcher/Redis si caídos |
| `*/5 min` | `notion-poller-cron.sh` | Watchdog del daemon Notion Poller |
| `*/15 min` | `dashboard-cron.sh` | Dashboard Notion (métricas) |
| `*/15 min` | `quota-guard-cron.sh` | Guard de cuota Claude (fallback si excedida) |
| `*/30 min` | `health-check.sh` | Health check Redis/Worker/Dispatcher |
| `* * * * *` | `scheduled-tasks-cron.sh` | Procesar tareas programadas (Redis sorted set) |
| `0 8,14,20` | `sim-daily-cron.sh` | SIM research (Tavily) |
| `30 8,14,20` | `sim-report-cron.sh` | SIM report (LLM + Notion) |
| `0 9,15,21` | `sim-to-make-cron.sh` | SIM → Make.com pipeline |
| `0 22` | `daily-digest-cron.sh` | Digest diario (Redis → LLM → Notion) |
| `0 6` | `e2e-validation-cron.sh` | E2E validation + Notion |
| `0 7 lunes` | `ooda-report-cron.sh` | OODA weekly report |

Instalar/actualizar crons:

```bash
bash ~/umbral-agent-stack/scripts/vps/install-cron.sh
```

---

## 3. Checklist de gobernanza

Ejecutar semanalmente (o antes de cada revisión de estrategia) para evaluar la salud operativa y la efectividad de las decisiones.

### 3.1 Métricas de operación

- [ ] Ejecutar OODA report: `PYTHONPATH=. python scripts/ooda_report.py --format markdown`
- [ ] Revisar tasa de éxito global y por equipo (campo `status` en task history)
- [ ] Revisar uso de modelos: ¿el routing usa los providers esperados según `config/quota_policy.yaml`?
- [ ] Revisar distribución de tasks por tipo (research, llm, composite, notion, etc.)

### 3.2 Análisis de fallos

- [ ] Revisar tareas fallidas: `curl -H "Authorization: Bearer $WORKER_TOKEN" "$WORKER_URL/task/history?status=failed&hours=168"`
- [ ] Identificar causas recurrentes de fallo (timeout, quota, error de provider, error de input)
- [ ] Verificar que el sistema de alertas (Error Alert System) está notificando correctamente
- [ ] Revisar escalaciones a Linear: ¿se están creando issues para fallos críticos?

### 3.3 Observabilidad

- [ ] Revisar ops_log (`~/.config/umbral/ops_log.jsonl`): ¿`trace_id` presente? ¿eventos completos (start → end)?
- [ ] Verificar Langfuse (si configurado): traces, latencia, costo por modelo
- [ ] Revisar dashboard Notion: ¿la información es actual y coherente?

### 3.4 Cuotas y recursos

- [ ] Ejecutar quota report: `PYTHONPATH=. python scripts/quota_usage_report.py --hours 168 --all`
- [ ] ¿Algún provider supera el umbral `warn`? → evaluar redistribución de routing
- [ ] ¿Algún provider subutilizado? → evaluar reasignar tráfico
- [ ] Revisar `GET /quota/status`: `curl -H "Authorization: Bearer $WORKER_TOKEN" "$WORKER_URL/quota/status"`

### 3.5 Seguridad

- [ ] Ejecutar secrets audit: `python scripts/secrets_audit.py`
- [ ] Verificar que `.env` no está trackeado en git
- [ ] Revisar permisos de acceso a Notion, Linear, y APIs externas
- [ ] Verificar que `WORKER_TOKEN` no aparece en logs expuestos

### 3.6 Notion Control Room

- [ ] Revisar tareas pendientes en Notion Control Room
- [ ] Verificar que no hay tareas bloqueadas sin acción
- [ ] Confirmar que el Notion Poller daemon está activo y procesando

---

## 4. Rutas de API relevantes para gobernanza

Todas las rutas (excepto `/health`) requieren header `Authorization: Bearer <WORKER_TOKEN>`.

| Método | Endpoint | Descripción | Ejemplo |
|--------|----------|-------------|---------|
| GET | `/health` | Estado del Worker (sin auth) | `curl $WORKER_URL/health` |
| POST | `/run` | Ejecutar tarea (TaskEnvelope) | `curl -X POST -H "Authorization: Bearer $T" -H "Content-Type: application/json" -d '{"task_type":"ping"}' $WORKER_URL/run` |
| POST | `/enqueue` | Encolar tarea en Redis | `curl -X POST -H "Authorization: Bearer $T" -H "Content-Type: application/json" -d '{"task_type":"ping"}' $WORKER_URL/enqueue` |
| GET | `/tasks/{task_id}` | Estado de tarea (in-memory) | `curl -H "Authorization: Bearer $T" $WORKER_URL/tasks/<id>` |
| GET | `/task/{task_id}/status` | Estado de tarea (Redis) | `curl -H "Authorization: Bearer $T" $WORKER_URL/task/<id>/status` |
| GET | `/task/history` | Historial paginado | `curl -H "Authorization: Bearer $T" "$WORKER_URL/task/history?hours=24&limit=50"` |
| GET | `/tasks` | Tareas recientes | `curl -H "Authorization: Bearer $T" "$WORKER_URL/tasks?limit=10&team=default"` |
| GET | `/quota/status` | Uso de cuotas por provider | `curl -H "Authorization: Bearer $T" $WORKER_URL/quota/status` |
| GET | `/providers/status` | Estado de providers y routing | `curl -H "Authorization: Bearer $T" $WORKER_URL/providers/status` |
| GET | `/tools/inventory` | Inventario de tasks y skills | `curl -H "Authorization: Bearer $T" $WORKER_URL/tools/inventory` |
| GET | `/scheduled` | Tareas programadas | `curl -H "Authorization: Bearer $T" $WORKER_URL/scheduled` |

### Parámetros de query comunes

| Endpoint | Parámetro | Tipo | Descripción |
|----------|-----------|------|-------------|
| `/task/history` | `hours` | int | Ventana de tiempo (default: 24) |
| `/task/history` | `team` | str | Filtrar por equipo |
| `/task/history` | `status` | str | Filtrar por estado (`completed`, `failed`) |
| `/task/history` | `limit` | int | Máximo de resultados |
| `/task/history` | `offset` | int | Paginación |
| `/tasks` | `limit` | int | Máximo de resultados |
| `/tasks` | `team` | str | Filtrar por equipo |
| `/tasks` | `status` | str | Filtrar por estado |

---

## 5. Troubleshooting

### 5.1 Worker no responde

| Paso | Acción |
|------|--------|
| 1 | Verificar health: `curl -sf $WORKER_URL/health` |
| 2 | Verificar proceso: `ps aux \| grep uvicorn` |
| 3 | Revisar logs: `tail -100 /tmp/supervisor.log` |
| 4 | Restart vía supervisor: `bash scripts/vps/supervisor.sh` |
| 5 | Restart manual: `source .venv/bin/activate && WORKER_TOKEN=... python -m uvicorn worker.app:app --host 0.0.0.0 --port 8088` |

### 5.2 Redis down

| Paso | Acción |
|------|--------|
| 1 | Verificar: `redis-cli ping` (respuesta esperada: `PONG`) |
| 2 | Verificar proceso: `ps aux \| grep redis-server` |
| 3 | Reiniciar: `redis-server --daemonize yes` |
| 4 | Verificar conectividad: `redis-cli -u $REDIS_URL ping` |
| 5 | Si persiste: revisar logs en `/var/log/redis/` y espacio en disco (`df -h`) |

### 5.3 Dispatcher no despacha tareas

| Paso | Acción |
|------|--------|
| 1 | Verificar que Redis está UP: `redis-cli ping` |
| 2 | Verificar que el Worker está UP: `curl $WORKER_URL/health` |
| 3 | Verificar proceso Dispatcher: `ps aux \| grep dispatcher` |
| 4 | Restart Dispatcher: `source .venv/bin/activate && python -m dispatcher.service` |
| 5 | Revisar logs del Dispatcher para errores de conexión o routing |

### 5.4 Cuota excedida

| Paso | Acción |
|------|--------|
| 1 | Consultar estado: `curl -H "Authorization: Bearer $T" $WORKER_URL/quota/status` |
| 2 | Identificar provider saturado |
| 3 | Opción A: Esperar reset del window (ver `window_seconds` en `config/quota_policy.yaml`) |
| 4 | Opción B: Ajustar `config/quota_policy.yaml` — aumentar `limit_requests` o relajar `restrict` |
| 5 | Opción C: Redirigir tráfico a provider alternativo via routing config |
| 6 | Verificar fallback chain: el ModelRouter debería mover tráfico automáticamente al siguiente provider |

### 5.5 Notion no actualiza

| Paso | Acción |
|------|--------|
| 1 | Verificar variables: `echo $NOTION_API_KEY` (debe tener valor) |
| 2 | Verificar page IDs: `NOTION_DASHBOARD_PAGE_ID`, `NOTION_CONTROL_ROOM_PAGE_ID` |
| 3 | Test de conexión: `PYTHONPATH=. python scripts/e2e_validation.py` (revisar sección Notion) |
| 4 | Verificar Notion Poller: `ps aux \| grep notion_poller` |
| 5 | Reiniciar Poller: el cron `notion-poller-cron.sh` lo hace automáticamente cada 5 min |

### 5.6 Langfuse sin traces

| Paso | Acción |
|------|--------|
| 1 | Verificar env: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` |
| 2 | Si no están configuradas: el sistema opera con graceful degradation (sin traces) |
| 3 | Si están configuradas pero no hay traces: verificar conectividad al host de Langfuse |
| 4 | Revisar OODA report: `PYTHONPATH=. python scripts/ooda_report.py` (sección Langfuse) |

### 5.7 Model routing inesperado

| Paso | Acción |
|------|--------|
| 1 | Consultar routing actual: `curl -H "Authorization: Bearer $T" $WORKER_URL/providers/status` |
| 2 | Revisar quota de providers: ¿alguno en estado `restrict`? |
| 3 | Revisar `config/quota_policy.yaml` — sección `routing` y `fallback_chain` |
| 4 | Verificar que las API keys de los providers están configuradas |
| 5 | Revisar ops_log para ver qué modelo se usó en tareas recientes |

### 5.8 Tareas programadas no se ejecutan

| Paso | Acción |
|------|--------|
| 1 | Verificar scheduled tasks: `curl -H "Authorization: Bearer $T" $WORKER_URL/scheduled` |
| 2 | Verificar que el cron `scheduled-tasks-cron.sh` está activo: `crontab -l \| grep scheduled` |
| 3 | Verificar Redis sorted set: `redis-cli ZRANGEBYSCORE umbral:scheduled 0 +inf` |
| 4 | Revisar logs: `tail -50 /tmp/scheduled-tasks.log` |

### 5.9 Puerto 8088 ocupado

```bash
# Encontrar el proceso
lsof -i :8088
# o en Windows:
netstat -ano | findstr :8088

# Matar por PID específico (NUNCA usar pkill -f)
kill <PID>
```

---

## 6. Flujos de verificación rápida

### 6.1 Health check completo (copiar y pegar)

```bash
echo "=== Umbral Stack Health Check ==="

# Redis
redis-cli ping > /dev/null 2>&1 && echo "✅ Redis OK" || echo "❌ Redis DOWN"

# Worker
curl -sf ${WORKER_URL:-http://localhost:8088}/health > /dev/null 2>&1 && echo "✅ Worker OK" || echo "❌ Worker DOWN"

# Dispatcher
ps aux | grep -v grep | grep "dispatcher.service" > /dev/null 2>&1 && echo "✅ Dispatcher running" || echo "⚠️  Dispatcher not detected"

# Notion Poller
ps aux | grep -v grep | grep "notion_poller" > /dev/null 2>&1 && echo "✅ Notion Poller running" || echo "⚠️  Notion Poller not detected"

# Quota
curl -sf -H "Authorization: Bearer ${WORKER_TOKEN}" ${WORKER_URL:-http://localhost:8088}/quota/status > /dev/null 2>&1 && echo "✅ Quota API OK" || echo "⚠️  Quota API unreachable"

echo "=== Done ==="
```

### 6.2 Restart completo del stack

```bash
# 1. Redis
redis-server --daemonize yes

# 2. Worker (en background o en screen/tmux)
source .venv/bin/activate
export WORKER_TOKEN="<token>"
nohup python -m uvicorn worker.app:app --host 0.0.0.0 --port 8088 --log-level info &

# 3. Dispatcher
export WORKER_URL="http://localhost:8088"
export REDIS_URL="redis://localhost:6379/0"
nohup python -m dispatcher.service &

# 4. Verificar
sleep 3
curl -sf http://localhost:8088/health && echo "✅ Stack UP" || echo "❌ Stack DOWN"
```

---

## 7. Verificación VPS y VM (¿todo al día con el repo?)

Ejecutar periódicamente para comprobar que no falte `git pull` ni dependencias.

### 7.1 VPS

```bash
cd ~/umbral-agent-stack
git fetch origin
git status          # ¿Hay cambios locales sin commit?
git log -1 --oneline
git log origin/main -1 --oneline   # Si son distintos, hay que pull
git pull origin main
pip3 install -r worker/requirements.txt   # Por si se añadieron deps (ej. requests)
curl -s http://127.0.0.1:8088/health | head -1
bash scripts/vps/supervisor.sh     # Ver Redis, Worker, Dispatcher OK
```

Si después del pull el Worker falla al arrancar (ej. `ModuleNotFoundError`), instalar deps y reiniciar: `pip3 install -r worker/requirements.txt` y `bash scripts/vps/supervisor.sh` (o el método que uses para el Worker).

### 7.2 VM (Execution Plane, Windows)

En la VM donde corre el Worker (NSSM / servicio `openclaw-worker`):

```powershell
cd C:\GitHub\umbral-agent-stack
git fetch origin
git status
git log -1 --oneline
git log origin/main -1 --oneline
git pull origin main
python -m pip install -r worker/requirements.txt
# Reiniciar el servicio para cargar código nuevo:
nssm restart openclaw-worker
curl -s http://localhost:8088/health
```

Si el repo en la VM está en otra ruta, ajustar `cd`. La VPS usa `WORKER_URL_VM` para enviar tareas improvement/lab a esta VM cuando está online.

---

## 8. Archivos de configuración

| Archivo | Propósito | Ubicación VPS |
|---------|-----------|---------------|
| `config/quota_policy.yaml` | Límites de cuota por provider y reglas de routing | repo |
| `config/teams.yaml` | Definición de equipos y routing por equipo | repo |
| `~/.config/openclaw/env` | Variables de entorno (secretos) | VPS only |
| `~/.config/umbral/ops_log.jsonl` | Log de operaciones (append-only) | VPS only |

---

## 9. Contactos y escalación

| Nivel | Acción |
|-------|--------|
| L1 — Automatizado | Supervisor auto-restart, quota guard, health check crons |
| L2 — Operador | Ejecutar procedimientos de este runbook, revisar checklist de gobernanza |
| L3 — Escalación | Crear issue en Linear (automático si `ESCALATE_FAILURES_TO_LINEAR=true`), notificar al equipo |

---

## 10. Scripts y docs recuperados (R16)

> Contenido capitalizado desde ramas no mergeadas durante el cierre de R16.
> Ver [analisis-contenido-perdido-r16.md](analisis-contenido-perdido-r16.md) para el análisis completo.

### 10.1 Bitácora — Enriquecimiento de páginas Notion

Scripts recuperados desde `cursor/bit-cora-contenido-enriquecido-4099`.

| Script | Descripción | Uso |
|--------|-------------|-----|
| `scripts/enrich_bitacora_pages.py` | Enriquece páginas de Bitácora en Notion con métricas (commits, PRs, tests, archivos) | `PYTHONPATH=. python scripts/enrich_bitacora_pages.py` |
| `scripts/add_resumen_amigable.py` | Agrega resúmenes no técnicos ("En pocas palabras") a cada página de Bitácora | `PYTHONPATH=. python scripts/add_resumen_amigable.py` |

**Tests:** `tests/test_notion_enrich_bitacora.py`

**Variables de entorno adicionales:**

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `NOTION_BITACORA_DB_ID` | Sí* | Database ID de la Bitácora en Notion |

*Requerida solo para los scripts de enriquecimiento.

**Documentación relacionada:** Si existe `docs/bitacora-scripts.md`, contiene detalles de uso y configuración.

### 10.2 Browser Automation en VM

Investigación y plan recuperados desde `feat/browser-automation-vm-research` (PR #88).

| Documento | Descripción |
|-----------|-------------|
| [64-browser-automation-vm-plan.md](64-browser-automation-vm-plan.md) | Plan de arquitectura para browser automation en VM: matriz comparativa (Playwright vs Puppeteer vs Selenium), decisiones de diseño, requisitos de infraestructura |
| `openclaw/.../browser-automation-vm/SKILL.md` | Skill knowledge-only de browser automation: conceptos, herramientas, patrones de integración |

**Estado:** Investigación completada. Implementación diferida a sprint futuro.

### 9.3 Guía de limpieza de ramas

| Documento | Descripción |
|-----------|-------------|
| [guia-borrar-ramas-r16.md](guia-borrar-ramas-r16.md) | Comandos para borrar 25 ramas remotas obsoletas, categorizadas en 4 grupos (vacías, destructivas, recuperadas, evaluar) |
| [ramas-recomendadas-borrar-r16.md](ramas-recomendadas-borrar-r16.md) | Lista resumida de ramas candidatas a borrar |
| [r16-cierre-resumen.md](r16-cierre-resumen.md) | Resumen ejecutivo de cierre R16 (PRs #85–#90) |

---

## Referencias

- [08-operations-runbook.md](08-operations-runbook.md) — Runbook de OpenClaw (systemctl, reinicio, logs)
- [09-troubleshooting.md](09-troubleshooting.md) — Troubleshooting específico (UI auth, providers, curl, Telegram)
- [01-architecture-v2.3.md](01-architecture-v2.3.md) — Arquitectura del sistema
- [07-worker-api-contract.md](07-worker-api-contract.md) — Contrato API del Worker
- [analisis-contenido-perdido-r16.md](analisis-contenido-perdido-r16.md) — Análisis de ramas no mergeadas
- [64-browser-automation-vm-plan.md](64-browser-automation-vm-plan.md) — Plan de browser automation en VM
