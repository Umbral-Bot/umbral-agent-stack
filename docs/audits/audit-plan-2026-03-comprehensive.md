# Plan de Auditoría Comprensiva — 2026-03-07

> Complementa: auditoría codebase 2026-03 (quick wins, 6 fixes), hackathon diagnóstico 2026-03-04.
> Foco: estado REAL del sistema vivo — VPS + VM + flujos funcionales + objetivos.

---

## Contexto: Qué se auditó antes vs qué falta

| Auditoría previa | Cobertura | Qué falta |
|-----------------|-----------|-----------|
| Codebase audit 2026-03 (quick wins) | Código estático — bugs, seguridad, dead code | Verificar que fixes llegaron a producción |
| Hackathon diagnóstico 2026-03-04 | Snapshot en vivo: VPS/VM alive, Redis OK, Dispatcher loop, 21 tareas/día | 3 días pasaron: ¿qué cambió? ¿crons corriendo? ¿flujos reales? |
| VM audit 2026-02-27 | Worker corriendo, NSSM, Tailscale | Estado actual de VM, LangGraph, Langfuse, granola_watcher |

---

## Dimensiones de Auditoría

### A — Infraestructura Viva (VPS)
**Objetivo:** ¿Los servicios críticos siguen corriendo? ¿El sistema se levantó solo tras posible reinicio?

Checks en VPS (SSH `rick@srv1431451` o Tailscale):
```bash
# 1. Servicios systemd
systemctl status openclaw --no-pager
systemctl status n8n --no-pager

# 2. Procesos activos
ps aux | grep -E "python|uvicorn|dispatcher|redis" | grep -v grep

# 3. Redis vivo y con datos
redis-cli ping
redis-cli llen umbral:tasks:pending
redis-cli llen umbral:tasks:blocked
redis-cli keys "umbral:*" | wc -l
redis-cli keys "quota:*"

# 4. Worker VPS health
curl -s http://localhost:8000/health | python3 -m json.tool

# 5. Git status (¿tiene los quick wins del 2026-03-05?)
cd ~/umbral-agent-stack && git log --oneline -5
git status -s

# 6. Crontab real instalado
crontab -l

# 7. Logs recientes de crons clave
tail -20 /tmp/dashboard_cron.log 2>/dev/null || echo "Sin log dashboard"
tail -20 /tmp/sim_report.log 2>/dev/null || echo "Sin log SIM"
tail -20 /tmp/supervisor.log 2>/dev/null || echo "Sin log supervisor"
tail -20 /tmp/health_check.log 2>/dev/null || echo "Sin log health"
tail -20 /tmp/notion_poller_cron.log 2>/dev/null || echo "Sin log poller"
tail -20 /tmp/scheduled_tasks.log 2>/dev/null || echo "Sin log scheduled"
tail -20 /tmp/quota_guard.log 2>/dev/null || echo "Sin log quota_guard"
tail -20 /tmp/e2e_validation.log 2>/dev/null || echo "Sin log e2e"
tail -20 /tmp/ooda_report.log 2>/dev/null || echo "Sin log ooda"
tail -20 /tmp/daily_digest.log 2>/dev/null || echo "Sin log daily_digest"

# 8. Dispatcher corriendo
ps aux | grep dispatcher
# Revisar log del dispatcher
journalctl -u openclaw -n 50 --no-pager
```

**Preguntas clave:**
- ¿El Dispatcher sigue en loop de health check failures o se resolvió la IP de VM?
- ¿Cuántos crons están realmente instalados vs los 11 definidos en install-cron.sh?
- ¿El git pull del 2026-03-05 (quick wins) llegó a VPS?

---

### B — Infraestructura Viva (VM Windows / PCRick)
**Objetivo:** ¿El Worker está corriendo? ¿Con la versión actualizada? ¿NSSM estable?

Checks en VM (local PowerShell o via http://192.168.155.86:8088):
```powershell
# 1. Estado NSSM
nssm status openclaw-worker

# 2. Worker health (desde VM o desde TARRO)
Invoke-RestMethod http://localhost:8088/health
# O desde TARRO:
curl http://192.168.155.86:8088/health

# 3. Git status en VM
cd C:\GitHub\umbral-agent-stack
git log --oneline -5
git status -s

# 4. Granola Watcher
Get-Service -Name "GranolaWatcher" -ErrorAction SilentlyContinue
# O via Task Scheduler
Get-ScheduledTask -TaskName "*Granola*" -ErrorAction SilentlyContinue

# 5. Langfuse (Docker)
docker ps --filter name=langfuse
# O si no hay docker:
netstat -an | findstr 3000

# 6. Tailscale en VM (si está instalado)
tailscale status

# 7. Logs del Worker NSSM
Get-Content "C:\nssm-logs\openclaw-worker.log" -Tail 30 -ErrorAction SilentlyContinue
```

**Preguntas clave:**
- ¿La VM tiene los quick wins desplegados (sanitize_input, hmac, etc.)?
- ¿El Granola Watcher está corriendo y procesando reuniones?
- ¿Langfuse está desplegado y recibiendo traces?
- ¿La VM tiene conectividad Tailscale directa al VPS (IP 100.x)?

---

### C — Flujo Funcional End-to-End
**Objetivo:** ¿El sistema procesa tareas reales? ¿El flujo completo funciona?

Test desde VPS:
```bash
# C1. Encolar tarea ping → VM
cd ~/umbral-agent-stack && source .venv/bin/activate
python3 -c "
import redis, json, uuid, time
r = redis.from_url('redis://localhost:6379/0', decode_responses=True)
task_id = str(uuid.uuid4())
envelope = {
    'task_id': task_id, 'task': 'ping', 'input': {},
    'team': 'system', 'priority': 1, 'created_at': time.time()
}
r.rpush('umbral:tasks:pending', json.dumps(envelope))
print(f'Enqueued: {task_id}')
# Esperar 5s y chequear resultado
time.sleep(5)
result = r.get(f'umbral:task:{task_id}:result')
print(f'Result: {result}')
"

# C2. Llamar directamente al Worker VM
curl -s -X POST http://100.109.16.40:8088/run \
  -H "Authorization: Bearer $WORKER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task": "ping", "input": {}}' | python3 -m json.tool

# C3. Ejecutar verify_stack completo
PYTHONPATH=. python3 scripts/verify_stack_vps.py

# C4. Smoke test
PYTHONPATH=. python3 scripts/smoke_test.py
```

**Preguntas clave:**
- ¿El Dispatcher está procesando la cola o sigue bloqueado?
- ¿VPS puede llegar a VM por Tailscale (100.109.16.40)?
- ¿La respuesta es correcta y tiene trace_id?

---

### D — Flujo Notion → Rick → Sistema
**Objetivo:** ¿El loop bidireccional Notion ↔ Rick funciona?

```bash
# D1. Notion Poller: ¿está corriendo?
ps aux | grep notion_poller
# Log del poller
tail -30 /tmp/notion_poller_cron.log

# D2. Control Room: ¿la integración tiene acceso?
PYTHONPATH=. python3 -c "
from worker.tasks.notion import _notion_client
import os
page_id = os.environ.get('NOTION_CONTROL_ROOM_PAGE_ID')
if page_id:
    try:
        r = _notion_client().blocks.children.list(block_id=page_id)
        print(f'Control Room accesible: {len(r[\"results\"])} bloques')
    except Exception as e:
        print(f'ERROR: {e}')
else:
    print('NOTION_CONTROL_ROOM_PAGE_ID no definida')
"

# D3. ¿Dashboard Rick se actualiza?
tail -5 /tmp/dashboard_cron.log
```

**Preguntas clave:**
- ¿La integración Notion tiene acceso a Control Room (faltaba en hackathon)?
- ¿El Poller está clasificando instrucciones o solo haciendo eco?
- ¿El Dashboard muestra métricas reales (no solo ceros)?

---

### E — LLM Usage y Cuotas
**Objetivo:** ¿El sistema está usando los LLMs? ¿Las cuotas se trackean?

```bash
# E1. Cuotas en Redis
redis-cli keys "quota:*"
for key in $(redis-cli keys "quota:*"); do
    echo "$key: $(redis-cli get $key)"
done

# E2. OpsLog — ¿qué eventos hay?
ls -la ~/umbral-agent-stack/ops_log* 2>/dev/null || echo "Sin ops_log"

# E3. SIM Report — ¿está generando outputs?
tail -30 /tmp/sim_report.log
ls -la /tmp/sim_*.json 2>/dev/null

# E4. Probar llm.generate directo
curl -s -X POST http://localhost:8000/run \
  -H "Authorization: Bearer $WORKER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task": "llm.generate", "input": {"prompt": "Di hola en 5 palabras", "model": "gemini-2.5-flash"}}' \
  | python3 -m json.tool
```

**Preguntas clave:**
- ¿Gemini 2.5 Flash sigue funcionando (API key válida)?
- ¿Las cuotas Redis tienen datos (post-hackathon)?
- ¿El SIM report genera contenido real o está fallando?

---

### F — Seguridad: Quick Wins en Producción
**Objetivo:** Verificar que los 6 fixes del codebase audit llegaron a ambos entornos.

```bash
# F1. VPS: ¿tiene el commit 850790b?
cd ~/umbral-agent-stack && git log --oneline | grep -i "quick wins\|sanitize\|hmac" | head -3

# F2. Verificar que sanitize se aplica en app.py
grep -n "sanitize_input" ~/umbral-agent-stack/worker/app.py | head -10

# F3. Verificar hmac.compare_digest
grep -n "compare_digest" ~/umbral-agent-stack/worker/app.py

# F4. rate_limit.py eliminado (QW-6)
ls ~/umbral-agent-stack/worker/rate_limit.py 2>/dev/null && echo "PROBLEMA: rate_limit.py aún existe" || echo "OK: rate_limit.py eliminado"

# F5. IPs en .env.example son placeholders
grep -E "100\.[0-9]" ~/umbral-agent-stack/.env.example && echo "ATENCION: IPs reales en .env.example" || echo "OK: sin IPs reales"
```

---

### G — Observabilidad Real
**Objetivo:** ¿Qué vemos del sistema en runtime? ¿Langfuse activo? ¿OpsLogger tiene datos?

En VM:
```bash
# G1. Langfuse Docker
docker compose -f infra/docker/docker-compose.langfuse.yml ps 2>/dev/null

# G2. OpsLog en VM
ls -la C:\GitHub\umbral-agent-stack\ops_log* 2>/dev/null

# G3. OODA report — ¿se generó alguna vez?
tail -20 /tmp/ooda_report.log
```

En VPS:
```bash
# G4. Ops events en Redis
redis-cli keys "ops:*" | head -20
redis-cli llen "ops:events" 2>/dev/null

# G5. Task history
redis-cli keys "umbral:task:*:result" | wc -l
```

---

### H — Estado vs Objetivos del Sistema
**Objetivo:** Medir brecha entre arquitectura objetivo (doc 01) y realidad actual.

| Componente objetivo | Verificación |
|--------------------|-------------|
| Rick como meta-orquestador | ¿Rick clasifica instrucciones de Telegram? |
| Equipos Marketing/Asesoría/Mejora | ¿Hay tareas encoladas por equipo? |
| ModelRouter activo | ¿task_type → LLM correcto? |
| PAD/RPA | ¿`windows.pad.run_flow` funciona? |
| ChromaDB para RAG | ¿Está corriendo en VM? |
| LiteLLM Proxy | ¿Desplegado? |
| Health Monitor 60s | ¿Cron activo? |
| Modo degradado (ADR-003) | ¿Se activa cuando VM está off? |

```bash
# H1. ¿LiteLLM desplegado?
docker ps | grep litellm
curl -s http://localhost:4000/health 2>/dev/null

# H2. ChromaDB
docker ps | grep chroma
curl -s http://localhost:8000/api/v1/heartbeat 2>/dev/null

# H3. n8n workflows configurados
curl -s http://localhost:5678/api/v1/workflows \
  -H "X-N8N-API-KEY: $N8N_API_KEY" 2>/dev/null | python3 -m json.tool | head -40
```

---

### I — Linear: Tracking de Issues vs Realidad
**Objetivo:** ¿Los issues reflejan el estado real del sistema?

```bash
# I1. Listar issues activos
PYTHONPATH=. python3 -c "
from worker.tasks.linear import _linear_client_v2
c = _linear_client_v2()
issues = c.issues(filter={'team': {'key': {'eq': 'UMB'}}, 'state': {'type': {'in': ['backlog','unstarted','started']}}})
for i in issues.nodes:
    print(f'{i.identifier}: {i.title[:60]} [{i.state.name}]')
"

# I2. ¿Issues cerrados desde hackathon?
```

---

## Script de Auditoría Automática

Para ejecutar en VPS en un solo comando:

```bash
cd ~/umbral-agent-stack && source .venv/bin/activate && \
export $(grep -v '^#' ~/.config/openclaw/env | xargs -d '\n') && \
PYTHONPATH=. python3 scripts/verify_stack_vps.py && \
echo "=== CRONTAB ===" && crontab -l && \
echo "=== REDIS KEYS ===" && redis-cli keys "umbral:*" | head -20 && \
echo "=== QUOTA KEYS ===" && redis-cli keys "quota:*" && \
echo "=== DASHBOARD LOG ===" && tail -5 /tmp/dashboard_cron.log 2>/dev/null && \
echo "=== SIM REPORT LOG ===" && tail -5 /tmp/sim_report.log 2>/dev/null && \
echo "=== SUPERVISOR LOG ===" && tail -5 /tmp/supervisor.log 2>/dev/null && \
echo "=== GIT STATUS VPS ===" && git log --oneline -3
```

Para ejecutar en VM (PowerShell):
```powershell
# Estado general VM
nssm status openclaw-worker
Invoke-RestMethod http://localhost:8088/health | ConvertTo-Json -Depth 3
cd C:\GitHub\umbral-agent-stack; git log --oneline -3
```

---

## Resultado Esperado: Scorecard

| Dimensión | Indicador | OK | WARN | FAIL |
|-----------|-----------|----|----|-----|
| A. VPS servicios | openclaw + n8n running | | | |
| A. VPS crons | ≥8 crons instalados | | | |
| A. VPS git | Quick wins (850790b) presentes | | | |
| B. VM Worker | NSSM running + /health 200 | | | |
| B. VM git | Quick wins presentes en VM | | | |
| B. Granola | Watcher corriendo | | | |
| C. E2E flow | ping encolado → resultado OK | | | |
| C. VM alcanzable | VPS → VM Tailscale OK | | | |
| D. Notion loop | Control Room accesible | | | |
| D. Poller | Classifica comentarios | | | |
| E. LLM usage | llm.generate responde | | | |
| E. Cuotas | Redis quota keys con datos | | | |
| F. Security | 6 quick wins en producción | | | |
| G. Observabilidad | OpsLogger con eventos | | | |
| G. Langfuse | Docker corriendo en VM | | | |
| H. Objetivos | LiteLLM / ChromaDB desplegados | | | |
| H. n8n | ≥1 workflow configurado | | | |
| I. Linear | Issues actualizados | | | |

---

## Prioridades de Remediación (hipótesis pre-audit)

Basado en estado conocido al 2026-03-04:

| P | Problema hipotético | Acción |
|---|--------------------|----|
| P0 | VM no alcanzable desde VPS (Tailscale IP) | Actualizar WORKER_URL_VM en VPS env |
| P0 | Quick wins no desplegados en VPS/VM | git pull + reiniciar servicios |
| P1 | Dispatcher en loop de health check | Fijar IP VM o usar health check degradado |
| P1 | Crons no todos instalados | Ejecutar install-cron.sh |
| P1 | Control Room sin acceso Notion | David: compartir página con integración |
| P2 | Langfuse no desplegado | docker compose up en VM |
| P2 | LiteLLM no desplegado | docker compose up en VPS |
| P2 | Cuotas LLM en 0 (sistema no usa LLMs) | Verificar llm.generate handler activo |
