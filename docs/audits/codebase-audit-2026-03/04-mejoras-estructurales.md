# Mejoras Estructurales — Umbral Agent Stack

**Fecha:** 2026-03-05
**Fuentes:** `01-mapa.md`, `02-bugs.md`, `03-seguridad.md`

---

## Nivel 1 — Quick Wins (1 dia)

### QW-1: Corregir sanitize_input descartado + hacer _check_injection defensivo

**Objetivo:** Hacer que la cadena de sanitizacion realmente proteja los handlers.

**Impacto:** Cierra el bug P0 #3 de `02-bugs.md` y mitiga hallazgo Medio SEC-13 de `03-seguridad.md`. Cada request pasa por sanitizacion efectiva en vez de decorativa.

**Esfuerzo:** 1-2 horas, 3 archivos, <20 lineas.

**Plan:**
- Capturar el retorno de `sanitize_input()` en `app.py:237`: `envelope.input = sanitize_input(envelope.input)`
- Repetir en el endpoint `/enqueue` (linea ~358)
- En `sanitize.py`, hacer que `_check_injection()` lance `ValueError` en lugar de solo loguear
- Actualizar los tests existentes de sanitize para verificar que `ValueError` se propaga
- Verificar que el middleware de FastAPI convierte `ValueError` en HTTP 422

**Dependencias:** Ninguna.

---

### QW-2: Timing-safe token comparison

**Objetivo:** Eliminar vulnerabilidad de timing attack en autenticacion del Worker.

**Impacto:** Mitiga hallazgo Alto SEC-7 de `03-seguridad.md` y bug P1 #9 de `02-bugs.md`.

**Esfuerzo:** 15 minutos, 1 archivo, 2 lineas.

**Plan:**
- Importar `hmac` en `worker/app.py`
- Reemplazar `parts[1] != WORKER_TOKEN` por `not hmac.compare_digest(parts[1], WORKER_TOKEN)` en linea 183
- Verificar que los tests de auth existentes siguen pasando
- Confirmar consistencia: `linear_webhook.py` ya usa `hmac.compare_digest`

**Dependencias:** Ninguna.

---

### QW-3: Validacion de inputs en handlers de Windows

**Objetivo:** Proteger los 3 handlers de `windows.py` que reciben input de usuario y lo pasan a comandos del sistema.

**Impacto:** Mitiga hallazgos Critico SEC-10 y SEC-11, y Alto SEC-12 de `03-seguridad.md`.

**Esfuerzo:** 2-3 horas, 1 archivo (`worker/tasks/windows.py`).

**Plan:**
- Crear funcion helper `_validate_safe_name(value, max_len=64)` con regex `[A-Za-z0-9_.-]+`
- Aplicar a `name` en `handle_windows_firewall_allow_port` (SEC-11)
- Aplicar a `username` en `handle_windows_add_interactive_worker_to_startup` (SEC-12)
- Para `run_as_password` (SEC-10): eliminar el parametro del input HTTP; leer de env var `SCHTASKS_PASSWORD` en la VM
- Agregar tests unitarios para las validaciones

**Dependencias:** Ninguna.

---

### QW-4: Limpiar .env.example (IPs, secretos faltantes, DB IDs)

**Objetivo:** Eliminar informacion sensible del template de entorno y documentar variables faltantes.

**Impacto:** Mitiga hallazgos Alto SEC-2 y SEC-3, y Medio SEC-5 de `03-seguridad.md`.

**Esfuerzo:** 30 minutos, 3 archivos.

**Plan:**
- Reemplazar IPs Tailscale reales por `<VPS_TAILSCALE_IP>` y `<VM_TAILSCALE_IP>` en `.env.example`
- Agregar `LINEAR_WEBHOOK_SECRET=` con comentario `# required for webhook HMAC validation`
- Agregar `NOTION_BITACORA_DB_ID=` con comentario `# required for bitacora scripts`
- En `scripts/add_resumen_amigable.py` y `scripts/enrich_bitacora_pages.py`: eliminar el default hardcodeado del DB ID; hacer que falle con mensaje claro si no esta definido
- Verificar que los tests no dependan del DB ID hardcodeado

**Dependencias:** Ninguna.

---

### QW-5: Emitir evento task_queued en ops_log

**Objetivo:** Completar el ciclo de vida observable de las tareas.

**Impacto:** Corrige bug P1 #5 de `02-bugs.md`. Habilita calculo de latencia en cola y deteccion de tareas huerfanas.

**Esfuerzo:** 1 hora, 2 archivos.

**Plan:**
- Agregar `ops_log.task_queued(task_id, task, team, task_type, trace_id)` en `worker/app.py` despues de `queue.enqueue()` (endpoint `/enqueue`)
- Agregar lo mismo en `dispatcher/service.py` si hay enqueue directo
- Verificar que `scripts/audit_traceability_check.py` ahora detecta el evento
- Agregar test unitario que verifique que el evento se escribe al log

**Dependencias:** Ninguna.

---

### QW-6: Unificar rate limiter duplicado

**Objetivo:** Eliminar la confision entre dos implementaciones y dos env vars de rate limiting.

**Impacto:** Corrige bug P2 #13 de `02-bugs.md`. Simplifica mantenimiento.

**Esfuerzo:** 1-2 horas, 3-4 archivos.

**Plan:**
- Unificar en una sola env var: `RATE_LIMIT_RPM` (ya usada por `app.py`)
- Eliminar `WORKER_RATE_LIMIT_PER_MIN` de `config.py`
- Mantener `rate_limiter.py` (la implementacion activa); deprecar `rate_limit.py`
- Migrar tests que importan `rate_limit` a usar `rate_limiter`
- Si `rate_limit.py` no tiene callers reales, eliminarlo

**Dependencias:** Ninguna.

---

## Nivel 2 — Mediano plazo (1-2 semanas)

### M-1: Ejecutar handlers en thread pool (run_in_executor)

**Objetivo:** Evitar que handlers sincronos bloqueen el event loop de FastAPI/uvicorn.

**Impacto:** Corrige bugs P0 #1 y #2 de `02-bugs.md` (los mas criticos del inventario). Permite servir multiples requests concurrentes sin que un handler lento (llm.generate, document.create_pdf) bloquee todo el servidor.

**Esfuerzo:** 3-5 dias. Requiere testing cuidadoso de concurrencia.

**Plan:**
- En `worker/app.py`, endpoint `/run`: envolver la llamada al handler con `await asyncio.get_event_loop().run_in_executor(None, handler, envelope.input)`
- Hacer lo mismo para las llamadas Redis sincronas en `/enqueue`
- Configurar el threadpool de uvicorn (default: 40 threads) o usar un ThreadPoolExecutor explicito con limite configurable
- Agregar timeout por handler: `asyncio.wait_for(executor_call, timeout=handler_timeout)` con timeout configurable por task_type
- Test de carga: verificar que 5 requests `llm.generate` concurrentes no bloquean un `ping` simultaneo

**Dependencias:** Ninguna. Es autocontenido en `app.py`.

---

### M-2: Desacoplar worker de dispatcher (paquete comun)

**Objetivo:** Eliminar la dependencia circular `worker → dispatcher` que causa ImportError en deploys minimos.

**Impacto:** Corrige bug P1 #6 de `02-bugs.md`. Permite desplegar el Worker en la VM sin instalar el paquete `dispatcher`.

**Esfuerzo:** 3-5 dias. Refactoring estructural.

**Plan:**
- Crear paquete `shared/` (o `common/`) con las clases/funciones compartidas: `TaskQueue`, `TaskHistory`, `TaskScheduler`, `QuotaTracker`, modelos Pydantic
- Mover las dependencias Redis de los endpoints `/enqueue`, `/task/history`, `/scheduled`, `/quota/status`, `/providers/status` a este paquete
- En `worker/app.py`, importar desde `shared/` en vez de `dispatcher/`
- En los endpoints que requieren Redis, envolver imports en `try/except ImportError` y devolver `503 Service Unavailable` si Redis no esta disponible
- Actualizar `dispatcher/service.py` para importar desde `shared/` tambien
- Actualizar CI y requirements para instalar `shared/` como dependencia

**Dependencias:** Coordinar con QW-5 (ops_log) si se mueve logica de enqueue.

---

### M-3: Proteger tarea ante TTL expiry en Redis

**Objetivo:** Evitar perdida silenciosa de tareas cuando el key Redis expira antes del dequeue.

**Impacto:** Corrige bug P0 #4 de `02-bugs.md` y complementa bug P1 #12 (callback_url perdido).

**Esfuerzo:** 2-3 dias.

**Plan:**
- En `queue.py:dequeue()`, cuando `full_raw is None` tras BRPOP exitoso: loguear como `task_lost` en ops_log, NO retornar `None` silenciosamente
- Incluir campos criticos (`callback_url`, `trace_id`, `input` resumido) en el item de `QUEUE_PENDING`, no solo en el key completo
- Si el key expiro pero tenemos el meta del item, crear un `task_failed` sintetico con razon `key_expired` y disparar el callback si existe
- Agregar metrica/alerta para `task_lost` events
- Considerar aumentar TTL de 7 a 30 dias, o usar `PERSIST` (sin TTL) para tareas activas

**Dependencias:** QW-5 (ops_log task_queued) deberia ir primero para tener trazabilidad completa.

---

### M-4: Operaciones atomicas en Redis (Lua scripts)

**Objetivo:** Eliminar race conditions en quota tracker y block_task.

**Impacto:** Corrige bugs P2 #14 (quota window reset race) y P1 #8 (block_task TOCTOU) de `02-bugs.md`.

**Esfuerzo:** 2-3 dias.

**Plan:**
- Escribir Lua script para `_ensure_window()` en `quota_tracker.py`: GET + comparacion + SET como operacion atomica
- Escribir Lua script para `block_task()` en `queue.py`: LRANGE + LREM + actualizar key como operacion atomica
- Registrar los scripts con `redis.register_script()` para reutilizacion
- Agregar tests con `fakeredis` verificando atomicidad (simular concurrencia con threads)
- Documentar los scripts Lua en `config/` o `infra/`

**Dependencias:** Ninguna. Compatible con fakeredis en tests.

---

### M-5: Hardening de autenticacion y auth logging

**Objetivo:** Mejorar la postura de seguridad del mecanismo de autenticacion del Worker.

**Impacto:** Mitiga hallazgos Medio SEC-8 (token sin rotacion) y Bajo SEC-9 (sin rate limit en auth) de `03-seguridad.md`.

**Esfuerzo:** 3-4 dias.

**Plan:**
- Implementar log de auditoria para cada intento de autenticacion (exito y fallo) con IP, timestamp, user-agent
- Agregar contador de fallos de auth por IP con backoff exponencial (bloqueo temporal tras 10 fallos en 60s)
- Documentar procedimiento de rotacion de WORKER_TOKEN (cambiar en VPS + VM, reiniciar servicios)
- Agregar middleware de cabeceras de seguridad HTTP: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` (mitiga SEC-17)
- Evaluar viabilidad de tokens con scopes para fase posterior (preparar la interfaz pero no implementar el scope check)

**Dependencias:** QW-2 (timing-safe comparison) deberia ir primero.

---

### M-6: Integrar pip-audit en CI y fijar dependencias

**Objetivo:** Detectar dependencias vulnerables automaticamente y evitar drift silencioso de versiones.

**Impacto:** Mitiga hallazgos Bajo SEC-15 (sin lock files) y SEC-16 (weasyprint sin libs) de `03-seguridad.md`. Corrige bug P1 #11 (weasyprint no testeado en CI).

**Esfuerzo:** 1-2 dias.

**Plan:**
- Generar `worker/requirements.lock` y `dispatcher/requirements.lock` con versiones exactas (`pip freeze`)
- Agregar step `pip-audit` al workflow de GitHub Actions (`pip install pip-audit && pip-audit -r worker/requirements.txt`)
- Agregar `sudo apt-get install -y libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0` al CI para testear weasyprint
- Agregar smoke test que importe `weasyprint` en los tests de `document_generator`
- Configurar Dependabot o Renovate para PRs automaticos de actualizacion

**Dependencias:** Ninguna.

---

## Nivel 3 — Grande (1-2 meses)

### G-1: Arquitectura de auth multi-nivel (tokens con scopes + rotacion)

**Objetivo:** Reemplazar el token unico compartido por un sistema de autenticacion con scopes, rotacion automatica y revocacion.

**Impacto:** Aborda de raiz los hallazgos SEC-1 (token en plaintext), SEC-8 (sin rotacion/scoping), y SEC-10 (password via HTTP) de `03-seguridad.md`. Corresponde al Sprint S7 (hardening) del roadmap.

**Esfuerzo:** 3-4 semanas.

**Plan:**
- Disenar esquema de tokens con scopes: `read`, `execute`, `execute:windows`, `admin`
- Implementar `TokenManager` en `infra/`: generacion (secrets.token_urlsafe), almacenamiento cifrado (SecretStore/Fernet — mitiga SEC-6), validacion con scopes
- Los handlers de Windows (`windows.*`) requieren scope `execute:windows` adicional
- Rotacion automatica: script cron que genera nuevo token, lo distribuye via Tailscale SSH a VPS+VM, reinicia servicios
- Revocacion: lista negra en Redis con TTL
- Migrar `handle_windows_write_worker_token` para usar el nuevo flujo (eliminar envio de token por HTTP)
- Eliminar `run_as_password` como input HTTP; las credenciales de schtasks se leen de SecretStore en la VM
- Agregar audit trail completo en ops_log: `auth_success`, `auth_failed`, `token_rotated`, `token_revoked`
- Retrocompatibilidad: soportar el token unico legacy durante 2 sprints con deprecation warning

**Dependencias:** QW-2 (timing-safe), QW-3 (validacion windows), M-5 (auth logging).

---

### G-2: Worker async nativo + queue resiliente

**Objetivo:** Reescribir el Worker y la cola para eliminar de raiz el bloqueo del event loop y la perdida de tareas.

**Impacto:** Resuelve definitivamente bugs P0 #1, #2, #4 de `02-bugs.md`. Elimina el in-memory task store (riesgo R7) y la fragilidad del TTL de Redis.

**Esfuerzo:** 4-6 semanas.

**Plan:**
- Convertir los handlers criticos (`llm.generate`, `composite.research_report`, `document.create_pdf`, `azure.audio.generate`) a `async def` nativos con `httpx.AsyncClient`
- Para handlers que deben ser sincronos (subprocess, python-docx): usar `run_in_executor` con ThreadPoolExecutor dedicado y timeout configurable
- Reemplazar `_task_store` (OrderedDict en memoria) por estado en Redis: cada tarea tiene lifecycle completo en `umbral:task:{id}`
- Redisenar `queue.py`: usar Redis Streams (`XADD`/`XREADGROUP`) en vez de LPUSH/BRPOP para consumer groups, ack explicito, y re-delivery automatica de tareas no confirmadas
- El envelope completo va en el stream entry (no en key separado): elimina el problema de TTL expiry entre BRPOP y GET
- Implementar dead-letter queue: tareas que fallan N veces van a `umbral:tasks:dlq` con alerta
- Agregar metricas de latencia por fase: `queued_at`, `started_at`, `completed_at` con calculo automatico
- Mantener retrocompatibilidad de la API HTTP (mismos endpoints, mismos contratos)

**Dependencias:** M-1 (run_in_executor) es el paso intermedio. M-3 (proteger TTL) es el fix temporal hasta que esto se complete.

---

### G-3: Observabilidad end-to-end (Langfuse + metricas + alertas)

**Objetivo:** Implementar el sprint S6 del roadmap: observabilidad completa con tracing distribuido, metricas cuantitativas, y alertas proactivas.

**Impacto:** Cierra el gap de observabilidad documentado en riesgos R5 (task_queued no emitido) y R9 (S6 pendiente) de `01-mapa.md`. Complementa bug P1 #5 de `02-bugs.md`.

**Esfuerzo:** 3-4 semanas.

**Plan:**
- Integrar Langfuse traces en el ciclo de vida completo: `task_queued` → `model_selected` → handler execution (con spans por subtarea) → `task_completed`/`task_failed`
- Agregar `trace_id` propagado end-to-end desde el envelope original hasta Langfuse y ops_log
- Implementar dashboard de metricas en Notion o Grafana: tasks/hora por equipo, latencia p50/p95, tasa de fallos, cuota usage
- Configurar alertas automaticas: tasa de fallos > 10%, latencia p95 > 60s, quota > 90%, worker offline > 5 min
- Conectar alertas con Telegram/Notion (el roadmap lo menciona como pendiente para `quota_exceeded_approval_required`)
- Implementar evals de calidad en Langfuse para `llm.generate` y `composite.research_report` (S6)
- Agregar `scripts/governance_metrics_report.py` enriquecido con datos de Langfuse

**Dependencias:** QW-5 (task_queued event), M-1 (async handlers para spans correctos).

---

### G-4: Despliegue containerizado con CI/CD completo

**Objetivo:** Containerizar Worker y Dispatcher con imagenes Docker reproducibles, CI/CD automatico, y entorno de staging.

**Impacto:** Aborda riesgo R8 (weasyprint sin libs de sistema), SEC-15 (sin lock files), SEC-16 (weasyprint sin verificacion), y el acoplamiento R4 (imagenes separadas para worker y dispatcher). Hace viable el sprint S7 (hardening).

**Esfuerzo:** 4-6 semanas.

**Plan:**
- Crear `Dockerfile.worker` y `Dockerfile.dispatcher` con multi-stage builds (builder + runtime)
- Worker image incluye deps de sistema para weasyprint: `libcairo2`, `libpango-1.0-0`, `libpangocairo-1.0-0`, `libgdk-pixbuf2.0-0`
- Dispatcher image es minimal: solo Redis client + httpx + FastAPI
- Usar lock files (`pip-tools compile` o `uv lock`) como fuente de verdad para builds reproducibles
- Docker Compose para entorno local: worker + dispatcher + Redis + Langfuse (integrar con `infra/docker/` existente)
- CI/CD: GitHub Actions build + push a registry, deploy automatico a VPS via SSH o Tailscale
- Entorno de staging en VPS: docker compose con red aislada para validacion pre-produccion
- Health checks nativos de Docker (`HEALTHCHECK CMD curl -f http://localhost:8088/health`)
- Secrets via Docker secrets o env files con permisos restringidos (integrar con SecretStore)

**Dependencias:** M-2 (desacople worker/dispatcher), M-6 (lock files + pip-audit).

---

## Mapa de dependencias entre mejoras

```
QW-1 (sanitize) ─────────────────────────────────────────────────┐
QW-2 (timing-safe) ──→ M-5 (auth hardening) ──→ G-1 (auth multi-nivel)
QW-3 (windows validation) ──────────────────────→ G-1
QW-4 (.env.example) ─────────────────────────────────────────────┘
QW-5 (task_queued) ──→ M-3 (TTL protection) ──→ G-2 (async + queue)
                   └──→ G-3 (observabilidad)
QW-6 (rate limiter) ──────────────────────────────────────────────┘

M-1 (run_in_executor) ──→ G-2 (async worker nativo)
M-2 (desacople paquetes) ──→ G-4 (containerizacion)
M-4 (Lua atomics) ──→ G-2 (Redis Streams)
M-6 (pip-audit + locks) ──→ G-4 (containerizacion)
```

## Orden de ejecucion recomendado

**Semana 1:** QW-1 a QW-6 (todos los quick wins, en paralelo o secuencialmente en 1 dia)

**Semanas 2-3:** M-1 (run_in_executor) + M-3 (TTL protection) — los dos P0 mas criticos

**Semanas 3-4:** M-2 (desacople) + M-4 (Lua atomics) + M-6 (pip-audit)

**Semana 5:** M-5 (auth hardening)

**Mes 2:** G-1 (auth multi-nivel) + G-3 (observabilidad) en paralelo

**Mes 3:** G-2 (async + queue resiliente) + G-4 (containerizacion)
