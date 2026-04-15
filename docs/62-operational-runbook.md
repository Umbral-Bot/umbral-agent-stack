# 62 — Runbook Operacional y Checklist de Gobernanza

> Documento maestro para mantenimiento, gobernanza y troubleshooting de Umbral Agent Stack.
> Complementa [08-operations-runbook.md](08-operations-runbook.md) (OpenClaw) y [09-troubleshooting.md](09-troubleshooting.md).

**VPS/Linux:** En Debian/Ubuntu no existe el comando `python`; usar siempre `python3` para scripts y módulos.

---

## 1. Procedimientos de mantenimiento

### 1.1 Diario

| Procedimiento | Comando / Script | Qué verificar | Notas |
|---------------|------------------|---------------|-------|
| Verificar salud de servicios | `bash scripts/vps/supervisor.sh` | Redis, Worker y Dispatcher UP; auto-restart si caídos | Cron `*/5 min` ya lo ejecuta |
| Dashboard Rick técnico | `PYTHONPATH=. python3 scripts/dashboard_report_vps.py --trigger manual` | Salud del stack, Redis, cuotas y tracking de paneles | Cron horario; usar `--force` para forzar actualización |
| OpenClaw humano | `PYTHONPATH=. python3 scripts/openclaw_panel_vps.py --trigger manual` | Resumen ejecutivo humano, entregables, proyectos y bandeja viva | Event-driven por cambios reales + fallback cada 6 h |
| E2E validation | `PYTHONPATH=. python3 scripts/e2e_validation.py` | health, ping, research.web, llm.generate, enqueue, task history, Notion, Redis, quota, routing | Cron diario a las 06:00; `--notion` para postear resultados |
| Smoke test rápido | `PYTHONPATH=. python3 scripts/smoke_test.py` | Worker /health, ping, Redis, quota status | Para verificación rápida ad-hoc (VPS: usar `python3`) |
| Smoke research.web | `PYTHONPATH=. python3 scripts/research_web_smoke.py --query "BIM trends 2026"` | Gemini grounded search en runtime real y fallback Tavily; distingue cuota, auth/config, timeout y fallo upstream | Útil cuando `research.web` falle y quieras ver la causa exacta sin correr la suite E2E completa |
| Health check infraestructura | `bash scripts/vps/health-check.sh` | Redis, Worker, Dispatcher, ops_log | Cron `*/30 min` |

### 1.2 Semanal

| Procedimiento | Comando / Script | Qué verificar | Notas |
|---------------|------------------|---------------|-------|
| Quota report | `PYTHONPATH=. python3 scripts/quota_usage_report.py --notion` | Uso vs límites por provider, subutilización | `--hours 168 --all` para semana completa |
| OODA report | `PYTHONPATH=. python3 scripts/ooda_report.py --format markdown` | Resumen semanal: tareas, éxito/fallo, tokens, costo Langfuse | `--week-ago 1` para semana anterior |
| Stack verification | `PYTHONPATH=. python3 scripts/verify_stack_vps.py` | Env vars, Worker, Redis, Linear, dashboard | Verificación integral del stack (VPS: usar `python3`) |

### 1.3 Mensual

| Procedimiento | Comando / Script | Qué verificar | Notas |
|---------------|------------------|---------------|-------|
| Secrets audit | `python3 scripts/secrets_audit.py` | Sin secretos expuestos en código fuente | `--ci` para integración continua (exit 1 si hay hallazgos); VPS: usar `python3` |
| Secrets management | `python3 scripts/manage_secrets.py audit` | Estado de secretos cifrados y gestión de claves | Subcomandos: `genkey`, `encrypt`, `audit`, `list` |
| Revisar quota_policy.yaml | Editar `config/quota_policy.yaml` | Límites alineados con uso real, routing óptimo | Ajustar `warn` y `restrict` según tendencias |
| Revisar teams.yaml | Editar `config/teams.yaml` | Equipos y routing por equipo vigentes | — |

### 1.4 Variables de entorno requeridas

Archivo de configuración en VPS: `~/.config/openclaw/env`

**Notion (Rick + Supervisor):** Resumen de variables y roles: [auditoría Notion](auditoria-notion-env-vars.md).

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `WORKER_TOKEN` | Sí | Token Bearer para autenticación API |
| `WORKER_URL` | Sí | URL del Worker (ej. `http://localhost:8088`) |
| `REDIS_URL` | Sí | URL de conexión a Redis |
| `WORKER_URL_VM` | No | URL del Worker en VM (Execution Plane) |
| `NOTION_API_KEY` | Sí* | API key de Notion |
| `NOTION_DASHBOARD_PAGE_ID` | Sí* | Page ID del dashboard en Notion |
| `NOTION_CONTROL_ROOM_PAGE_ID` | Sí* | Page ID de la **Control Room** (solo comunicación Rick/Enlace/David; no usar para alertas automáticas) |
| `NOTION_SUPERVISOR_ALERT_PAGE_ID` | Recomendado | Page ID donde el supervisor postea el aviso (ej. `Alertas del Supervisor`: `0fd13978b220498e9465b4fb2efc5f4a`). Si no se define, el fallback usa el Worker y NOTION_CONTROL_ROOM_PAGE_ID. |
| `NOTION_SUPERVISOR_API_KEY` | No* | Token de la integración Notion **"Supervisor"** (nombre/avatar distintos a Rick). Si está definido junto con NOTION_SUPERVISOR_ALERT_PAGE_ID, el supervisor postea **directo a Notion** y el comentario aparece como Supervisor en esa página. Si no, usa el Worker (identidad Rick). *Requerido solo para identidad Supervisor en la página de alertas. |
| `NOTION_GRANOLA_DB_ID` | No | ID de la DB de transcripciones Granola (usa `NOTION_API_KEY` de Rick) |
| `LANGFUSE_PUBLIC_KEY` | No | Clave pública de Langfuse (graceful degradation sin ella) |
| `LANGFUSE_SECRET_KEY` | No | Clave secreta de Langfuse |
| `LANGFUSE_HOST` | No | Host de Langfuse |
| `RATE_LIMIT_RPM` | No | Límite externo por cliente/IP (default: 60) |
| `RATE_LIMIT_INTERNAL_RPM` | No | Límite para trafico interno autenticado, particionado por ruta/tarea (default: 600) |
| `GOOGLE_API_KEY` | No | API key de Google AI Studio |
| `OPENAI_API_KEY` | No | API key de OpenAI |
| `ANTHROPIC_API_KEY` | No | API key de Anthropic |
| `GITHUB_TOKEN` | No | Fine-grained PAT de GitHub (para `gh` CLI y handlers `github.*`). Las operaciones git usan SSH deploy key, no este token |

*Requeridas para funcionalidades de Notion; sin ellas solo `ping` funciona completamente. Para que el aviso a Notion del supervisor funcione, el Worker debe tener `NOTION_API_KEY` y `NOTION_CONTROL_ROOM_PAGE_ID` (o `NOTION_SUPERVISOR_ALERT_PAGE_ID` si el script lo soporta) en su entorno al arrancar.

**Supervisor con identidad propia (recomendado):** Para que los avisos de reinicio aparezcan como **"Supervisor"** (no como Rick) y vayan a **Alertas del Supervisor**: (1) En Notion, crear una integración (nombre ej. "Supervisor", avatar distinto). (2) En la página `Alertas del Supervisor`, **••• → Add connections** y conectar esa integración. (3) En la VPS, en `~/.config/openclaw/env`, definir `NOTION_SUPERVISOR_API_KEY` (token de esa integración) y `NOTION_SUPERVISOR_ALERT_PAGE_ID=0fd13978b220498e9465b4fb2efc5f4a`. El script del supervisor postea entonces directo a la API de Notion y el comentario sale como Supervisor en la página dedicada de alertas.

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
| `0 * * * *` | `dashboard-rick-cron.sh` | Dashboard Rick técnico (métricas + tracking) |
| `0 */6 * * *` | `openclaw-panel-cron.sh` | Fallback lento para OpenClaw humano |
| `*/15 min` | `quota-guard-cron.sh` | Guard de cuota Claude (fallback si excedida) |
| `*/30 min` | `health-check.sh` | Health check Redis/Worker/Dispatcher |
| `* * * * *` | `scheduled-tasks-cron.sh` | Procesar tareas programadas (Redis sorted set) |
| `0 8,14,20` | `sim-daily-cron.sh` | SIM research (Gemini grounded primario + Tavily fallback) |
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

- [ ] Ejecutar OODA report: `PYTHONPATH=. python3 scripts/ooda_report.py --format markdown`
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

- [ ] Ejecutar quota report: `PYTHONPATH=. python3 scripts/quota_usage_report.py --hours 168 --all`
- [ ] ¿Algún provider supera el umbral `warn`? → evaluar redistribución de routing
- [ ] ¿Algún provider subutilizado? → evaluar reasignar tráfico
- [ ] Revisar `GET /quota/status`: `curl -H "Authorization: Bearer $WORKER_TOKEN" "$WORKER_URL/quota/status"`

### 3.5 Seguridad

- [ ] Ejecutar secrets audit: `python3 scripts/secrets_audit.py`
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
| 5 | Restart manual: `source .venv/bin/activate && WORKER_TOKEN=... python3 -m uvicorn worker.app:app --host 0.0.0.0 --port 8088` |

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
| 4 | Reconciliar Dispatcher: `bash scripts/vps/dispatcher-service.sh reconcile` |
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

### 5.5 API rate limit (OpenClaw / Rick)

Cuando aparece **"⚠️ API rate limit reached"** al usar Rick por Telegram/OpenClaw:

| Paso | Acción |
|------|--------|
| 1 | Esperar 1–2 minutos; los límites del proveedor suelen ser por minuto |
| 2 | Reintentar el mensaje (el siguiente intento puede usar un modelo de respaldo) |
| 3 | No repetir el mismo mensaje muchas veces seguidas |

**Runbook detallado:** [runbooks/runbook-rate-limit-api.md](../runbooks/runbook-rate-limit-api.md). En el workspace de Rick (`~/.openclaw/workspace/USER.md`) hay una nota para que responda al usuario con esa indicación.

### 5.6 Notion no actualiza

| Paso | Acción |
|------|--------|
| 1 | Verificar variables: `echo $NOTION_API_KEY` (debe tener valor) |
| 2 | Verificar page IDs: `NOTION_DASHBOARD_PAGE_ID`, `NOTION_CONTROL_ROOM_PAGE_ID` |
| 3 | Test de conexión: `PYTHONPATH=. python3 scripts/e2e_validation.py` (revisar sección Notion) |
| 4 | Verificar Notion Poller: `ps aux \| grep notion_poller` |
| 5 | Reiniciar Poller: el cron `notion-poller-cron.sh` lo hace automáticamente cada 5 min |

### 5.7 Langfuse sin traces

| Paso | Acción |
|------|--------|
| 1 | Verificar env: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` |
| 2 | Si no están configuradas: el sistema opera con graceful degradation (sin traces) |
| 3 | Si están configuradas pero no hay traces: verificar conectividad al host de Langfuse |
| 4 | Revisar OODA report: `PYTHONPATH=. python3 scripts/ooda_report.py` (sección Langfuse) |

### 5.8 Model routing inesperado

| Paso | Acción |
|------|--------|
| 1 | Consultar routing actual: `curl -H "Authorization: Bearer $T" $WORKER_URL/providers/status` |
| 2 | Revisar quota de providers: ¿alguno en estado `restrict`? |
| 3 | Revisar `config/quota_policy.yaml` — sección `routing` y `fallback_chain` |
| 4 | Verificar que las API keys de los providers están configuradas |
| 5 | Revisar ops_log para ver qué modelo se usó en tareas recientes |

### 5.9 Tareas programadas no se ejecutan

| Paso | Acción |
|------|--------|
| 1 | Verificar scheduled tasks: `curl -H "Authorization: Bearer $T" $WORKER_URL/scheduled` |
| 2 | Verificar que el cron `scheduled-tasks-cron.sh` está activo: `crontab -l \| grep scheduled` |
| 3 | Verificar Redis sorted set: `redis-cli ZRANGEBYSCORE umbral:scheduled 0 +inf` |
| 4 | Revisar logs: `tail -50 /tmp/scheduled-tasks.log` |

### 5.10 Puerto 8088 ocupado

```bash
# Encontrar el proceso
lsof -i :8088
# o en Windows:
netstat -ano | findstr :8088

# Matar por PID específico (NUNCA usar pkill -f)
kill <PID>
```

### 5.11 GitHub: token expirado, SSH o push protection

```bash
# Verificar token (debe devolver Logged in account UmbralBIM):
source ~/.config/openclaw/env && GH_TOKEN=$GITHUB_TOKEN gh auth status

# Verificar SSH deploy key:
ssh -T git@github.com   # Debe decir "successfully authenticated" (rc=1 es OK)

# Si el push falla por push protection (GH013):
# — El handler `github.commit_and_push` mostrará el error textual.
# — Revisar si algún archivo tocado está en GitHub push protection ruleset.
# — Archivos conocidos como protegidos: .claude/CLAUDE.md, .claude/settings.json, .agents/board.md

# Token expirado (PAT actual expira 2027-03-03):
# — Regenerar en GitHub → Settings → Developer settings → Fine-grained tokens
# — Actualizar GITHUB_TOKEN en ~/.config/openclaw/env
# — Reiniciar Worker para que recargue env
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
nohup python3 -m uvicorn worker.app:app --host 0.0.0.0 --port 8088 --log-level info &

# 3. Dispatcher
export WORKER_URL="http://localhost:8088"
export REDIS_URL="redis://localhost:6379/0"
bash scripts/vps/dispatcher-service.sh start

# 4. Verificar
sleep 3
curl -sf http://localhost:8088/health && echo "✅ Stack UP" || echo "❌ Stack DOWN"
```

---

## 7. Verificación VPS y VM (¿todo al día con el repo?)

Ejecutar periódicamente para comprobar que no falte `git pull` ni dependencias.

### 7.0 Política Git en la VPS: sin clonación de main para trabajar; rama + PR, merge lo hace David/Cursor

**No hay “clon de main” para editar.** En la VPS hay **un solo clone** del repo. La rama **`main`** se usa **solo para ejecutar** el stack (Worker, Dispatcher, crons) y **solo se actualiza con `git pull`** para recibir código ya mergeado. **Nunca** se hace commit ni push a `main` desde la VPS.

| Quién | Dónde | Acción |
|-------|--------|--------|
| **VPS (Rick)** | Rama `rick/vps` | Commit, push, abrir PR a `main` |
| **David / Cursor** | GitHub o local | Revisar PR, **mergear** a `main` |
| **VPS** | `main` | Tras el merge: `git checkout main && git pull origin main` (solo recibir) |

Cuando Rick o un script en la VPS necesite cambiar código o docs:

1. Crear rama: vía handler `github.create_branch` (que trabaja en `~/umbral-agent-stack`), o a mano:
   - `cd ~/umbral-agent-stack && git fetch origin && git checkout -b rick/<nombre> origin/main`
2. Hacer los cambios, staging explícito, commit, push: vía handler `github.commit_and_push` (requiere lista explícita de archivos), o a mano:
   - `git add -- <archivos> && git commit -m "..." && git push -u origin rick/<nombre>`
3. Abrir PR a `main`: vía handler `github.open_pr` (usa `GITHUB_TOKEN`), o: `GH_TOKEN=$GITHUB_TOKEN gh pr create --head rick/<nombre> --base main --title "..."`
4. **No** mergear desde la VPS; David (o Cursor) hace el merge
5. Después del merge: `cd ~/umbral-agent-stack && git checkout main && git pull origin main`

Los handlers `github.*` implementan guardrails: rechazan push a main, exigen prefijo `rick/` en todas las operaciones (crear rama, commit, PR), validan worktree limpio (archivos sin trackear se toleran, solo cambios staged/modified bloquean), validan nombres de rama base, y requieren lista explícita de archivos (nunca `git add -A`).

> **Nota:** Los scripts `scripts/vps/rick-branch-for-change.sh`, `scripts/vps/rick-ensure-not-pushing-main.sh` y `scripts/vps/ensure-main-for-run.sh` referenciados en versiones anteriores de este doc **no existen**. Los guardrails están ahora en los handlers `github.*` del Worker.

Referencia: [docs/34-rick-github-token-setup.md](34-rick-github-token-setup.md) y [docs/28-rick-github-workflow.md](28-rick-github-workflow.md).

### 7.0.1 Orquestación multi-rama (tournament over branches)

El handler `github.orchestrate_tournament` compone `tournament.run` con `github.create_branch` para comparar múltiples enfoques en ramas independientes:

1. Preflight → worktree limpio requerido.
2. Tournament LLM (discovery → develop → debate → judge).
3. Crea ramas `rick/t/{id}/{a,b,c,...}` por cada enfoque.
4. Si hay ganador, crea `rick/t/{id}/final`.
5. Retorna a la rama base.

Convención de ramas: `rick/t/{8-hex}/{label}` donde label es `a`-`e` o `final`.

El handler NO genera código en las ramas (Phase 1). Las ramas son contenedores nombrados para fases futuras. El resultado incluye `contestants`, `verdict`, `final_branch`, y `meta` con métricas del torneo.

Si el juez retorna `ESCALATE`, no se crea rama final — Rick debe escalar la decisión a David con la tabla comparativa.

### 7.0.2 Configuración VPS: repo único para runtime y cambios de Rick

En la VPS hay un solo repo: `~/umbral-agent-stack`. Es tanto el runtime como el working copy donde Rick crea ramas y trabaja. Los handlers `github.*` operan aquí por defecto (`config.GITHUB_REPO_PATH`).

**Sincronizar con origin antes de trabajar:**

```bash
cd ~/umbral-agent-stack
git checkout main && git pull origin main
```

Desde `main`, Rick crea ramas con prefijo `rick/` (vía handler o manual) y nunca pushea a `main` directamente.

### 7.0.3 Superficies locales de la VPS (no-canónicas)

Algunos archivos existen solo en la VPS y están excluidos del repo compartido vía `.gitignore`:

| Archivo | Propósito |
|---------|-----------|
| `.claude/CLAUDE.md` | Instrucciones de Claude Code específicas de la VPS (modelo single-repo) |
| `.claude/settings.json` | Configuración de sesión de Claude Code |
| `.claude/hooks/block-deployed-repo-writes.sh` | Hook PreToolUse que protege el repo contra escrituras accidentales |
| `.agents/board.md` | Tablero operativo del agente (estado interno de Rick) |
| `docs/audits/notion-curation-snapshot-2026-03-16.json` | Snapshot generado por la curación automática; se sobreescribe en cada ejecución |

Estos archivos **no se pushean** y **no deben bloquear** operaciones de Git de Rick. Al estar en `.gitignore`, `git status --porcelain --untracked-files=no` los ignora, lo que permite que `_ensure_clean_worktree()` los tolere automáticamente.

Si se pierden (por error, reinstalación, etc.), pueden regenerarse localmente sin afectar el repo compartido.

### 7.1 VPS (verificación: repo en rama correcta, worktree limpio)

En la VPS `~/umbral-agent-stack` es el único repo. Para **recibir** cambios mergeados: `git checkout main && git pull origin main`.

```bash
cd ~/umbral-agent-stack
git fetch origin
git status          # ¿En rama rick/vps con cambios sin commit? Commit y push a rick/vps, abre PR (§7.0)
git branch -v      # Por defecto deberías estar en rick/vps para trabajar
# Actualizar rick/vps con lo último de main (tras merges de David/Cursor):
git checkout main && git pull origin main
git checkout rick/vps && git merge main
pip3 install -r worker/requirements.txt   # Por si se añadieron deps (ej. requests)
curl -s http://127.0.0.1:8088/health | head -1
bash scripts/vps/supervisor.sh     # Ver Redis, Worker, Dispatcher OK (ellos usan main al correr)
# Verificación completa del stack (env, Worker, Redis, Linear, dashboard):
source ~/.config/openclaw/env && PYTHONPATH=. python3 scripts/verify_stack_vps.py
# Smoke test rápido:
source ~/.config/openclaw/env && PYTHONPATH=. python3 scripts/smoke_test.py
```

Si después de actualizar el Worker falla al arrancar (ej. `ModuleNotFoundError`), instalar deps y reiniciar: `pip3 install -r worker/requirements.txt` y `bash scripts/vps/supervisor.sh` (el supervisor pone el repo en main antes de arrancar).

### 7.2 VM (Execution Plane, Windows)

En la VM donde corre el Worker (NSSM / servicio `openclaw-worker`):

```powershell
cd C:\GitHub\umbral-agent-stack
git fetch origin
git status
git log -1 --oneline
git log origin/main -1 --oneline
git pull origin main
python3 -m pip install -r worker/requirements.txt
# Reiniciar el servicio para cargar código nuevo:
nssm restart openclaw-worker
curl -s http://localhost:8088/health
```

Si el repo en la VM está en otra ruta, ajustar `cd`. La VPS usa `WORKER_URL_VM` para enviar tareas improvement/lab a esta VM cuando está online.

#### 7.2.1 SSH a la VM (desde tu PC, no desde la VM)

Para conectarte por SSH a la VM (`rick@100.109.16.40` o la IP Tailscale de la VM) **hay que ejecutar `ssh` desde tu PC (TARRO)**, no desde la VM. La clave privada (id_rsa de David) está solo en tu PC; la VPS tiene su propia clave (vps-umbral) para Rick.

Si ejecutás `ssh rick@100.109.16.40` **desde la VM** (sesión de Rick), verás mensajes esperados:

- `Identity file C:\Users\Rick\.ssh\id_rsa not accessible: No such file or directory` — Rick en la VM no tiene esa clave.
- `hostkeys_foreach failed for C:\\Users\\Rick/.ssh/known_hosts: Permission denied` — permisos de la carpeta .ssh de Rick.
- `Failed to add the host to the list of known hosts` — no puede escribir known_hosts.
- `Connection reset by ... port 22` — la conexión se cierra.

**Acción:** usar SSH desde tu PC: `ssh -i $env:USERPROFILE\.ssh\id_rsa -o IdentitiesOnly=yes rick@100.109.16.40 "hostname"`. Diagnóstico profundo en la VM: `.\scripts\vm-ssh-key-diagnostic.ps1` (genera `docs/audits/vm-ssh-diagnostic-*.txt`).

#### 7.2.2 OpenClaw Node (VM → Gateway)

Si la VM tiene el nodo OpenClaw configurado (NSSM `openclaw-node`), verificar tras reinicio:

**En la VM:**
```powershell
nssm status openclaw-node
Get-Content C:\openclaw-worker\openclaw-node-stdout.log -Tail 20
```

**En la VPS:**
```bash
openclaw devices list
```

PCRick debe aparecer en Paired. Si aparece en Pending: `openclaw devices approve <requestId>`.

Runbook completo: [runbooks/runbook-vm-openclaw-node.md](../runbooks/runbook-vm-openclaw-node.md).

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
| `scripts/enrich_bitacora_pages.py` | Enriquece páginas de Bitácora en Notion con métricas (commits, PRs, tests, archivos) | `PYTHONPATH=. python3 scripts/enrich_bitacora_pages.py` |
| `scripts/add_resumen_amigable.py` | Agrega resúmenes no técnicos ("En pocas palabras") a cada página de Bitácora | `PYTHONPATH=. python3 scripts/add_resumen_amigable.py` |

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
