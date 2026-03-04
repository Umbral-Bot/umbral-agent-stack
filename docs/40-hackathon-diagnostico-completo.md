# 40 — Hackathon: Diagnóstico Completo del Sistema

> **Fecha:** 2026-03-04  
> **Coordinador:** Cursor (Lead)  
> **Participantes:** Cursor, Codex, Antigravity, GitHub Copilot  
> **Objetivo:** Diagnóstico profundo, propuestas de mejora y plan de acción alineado a la visión de David

---

## 1. Análisis de la Idea Original de David

### Visión
David concibió **Umbral Agent Stack** como un sistema donde **equipos de agentes AI trabajan 24/7** como una organización real, aprovechando al máximo **5 suscripciones LLM** (Claude Pro, ChatGPT Plus, Gemini Pro, Copilot Pro, Notion Business).

### Principios Fundacionales
1. **Solo David manda** — Rick (meta-orquestador) recibe instrucciones exclusivamente de David
2. **Equipos especializados** — Marketing, Asesoría Personal, Mejora Continua
3. **Arquitectura split** — Control Plane (VPS 24/7) + Execution Plane (VM Windows)
4. **Multi-modelo inteligente** — Cada tarea usa el LLM óptimo según tipo y cuota
5. **Auditable** — Toda ejecución deja traza en Notion + Langfuse
6. **Máximo aprovechamiento** — Los créditos/cuotas de las 5 suscripciones se usan al máximo

### ¿Qué debería verse funcionando?
Según la visión, el sistema operativo debería:
- Recibir instrucciones de David vía Telegram/Notion
- Rick procesa y delega a equipos automáticamente
- Los equipos ejecutan tareas usando el modelo más adecuado
- Dashboard en Notion muestra estado gerencial en tiempo real
- Los agentes (Cursor, Codex, Antigravity, Copilot) mejoran el sistema continuamente
- Las cuotas de LLMs se aprovechan activamente (no se desperdician)

---

## 2. Diagnóstico Profundo del Sistema

### 2.1 Estado de los Tests
- **130 tests pasan**, 1 skipped (encrypt/decrypt necesita `cryptography`)
- Tests cubren: Worker, Dispatcher, Dashboard, Linear, ModelRouter, Observability, Hardening
- **Veredicto:** La base de código es sólida técnicamente

### 2.2 Worker (FastAPI)
| Aspecto | Estado | Detalle |
|---------|--------|---------|
| Código | ✅ Funcional | 22 task handlers registrados, auth, rate limiting, sanitización |
| Health endpoint | ✅ OK | `/health` responde correctamente |
| Ping | ✅ OK | Echo funciona perfecto |
| Notion tasks | ⚠️ Requiere config | Sin `NOTION_API_KEY` solo funciona `ping` |
| Linear tasks | ⚠️ Requiere config | Sin `LINEAR_API_KEY` no funciona |
| Windows tasks | ❌ Bloqueado | PAD no instalado en VM; `open_notepad` bloqueado por permisos |
| TaskEnvelope | ✅ Implementado | v0.1 con backward compat legacy |
| Store | ⚠️ In-memory | Se pierde al reiniciar (máx 1000 tareas) |

### 2.3 Dispatcher
| Aspecto | Estado | Detalle |
|---------|--------|---------|
| Service loop | ✅ Implementado | brpop + N workers en paralelo |
| ModelRouter | ✅ Implementado | Selección por task_type + cuotas |
| QuotaTracker | ✅ Implementado | Redis-backed con ventanas temporales |
| TeamRouter | ⚠️ Parcial | `dispatch()` no se usa en producción |
| HealthMonitor | ✅ Implementado | Vigila VM cada 10s |
| Notion Poller | ⚠️ Solo eco | Solo responde "Rick: Recibido." — no procesa contenido |
| Linear integration | ✅ Implementado | Actualiza issues al completar tareas |
| Notion upsert | ✅ Implementado | Kanban tracking en Notion |

### 2.4 Dashboard Rick
| Aspecto | Estado | Detalle |
|---------|--------|---------|
| Script generador | ✅ Implementado | `dashboard_report_vps.py` genera payload completo |
| Worker task | ✅ Implementado | `notion.update_dashboard` con bloques ricos v2 |
| Cron en VPS | ❓ Sin confirmar | `install-cron.sh` existe pero no confirmado que esté activo |
| Resultado actual | ❌ Degradado | Overall status: "Degradado", Workers offline, Redis no conectado |

### 2.5 Operaciones y Tracking
| Aspecto | Estado | Detalle |
|---------|--------|---------|
| OpsLogger | ✅ Implementado | JSONL append-only con eventos detallados |
| Eventos registrados | ❌ Vacío | 0 eventos — el sistema no ha procesado tareas reales |
| Uptime | ❌ null | No hay historial de operaciones |
| Cuotas utilizadas | ❌ 0% | Ningún modelo LLM ha sido usado por el sistema |

### 2.6 Infraestructura
| Componente | Estado | Detalle |
|-----------|--------|---------|
| VPS (Control Plane) | ❓ | No verificable desde aquí — cron, env, servicios |
| VM Windows | ❓ | Tareas bloqueadas por permisos admin |
| Tailscale | ❓ | Red mesh documentada pero no verificable |
| Redis | ⚠️ | Docker compose existe; conexión no confirmada en VPS |
| OpenClaw Gateway | ❓ | npm externo, no en este repo |
| LiteLLM | ❌ Comentado | Comentado en docker-compose |
| Langfuse | ❌ No activo | Docker compose existe pero no desplegado |
| n8n | ✅ Instalado | Confirmado por Rick el 2026-03-03 |

### 2.7 Agentes y Coordinación
| Agente | Tareas hechas | Tareas bloqueadas | Calidad |
|--------|--------------|-------------------|---------|
| Cursor | Lead/orquestador | — | Documentación extensa, planning sólido |
| Codex | 3 done | 2 blocked (permisos admin VM) | Parcial — bloqueado por permisos |
| Antigravity | 1 done (VPS setup) | 0 | OK |
| GitHub Copilot | 2 done (Tavily, Google CSE) | 0 | OK — resolvió búsqueda web |

---

## 3. Hallazgos Críticos

### 🔴 Problemas Graves

1. **El sistema NO está operando 24/7** — No hay evidencia de tareas procesadas. Los ops_logs están vacíos. Cero actividad real del sistema.

2. **Dashboard no funciona en producción** — El payload muestra "Degradado", workers offline. El cron probablemente no está instalado en la VPS.

3. **Cero aprovechamiento de cuotas LLM** — Las 5 suscripciones (Claude, ChatGPT, Gemini, Copilot, Notion) no están siendo usadas por el sistema. 0 requests registrados.

4. **Notion Poller es un eco vacío** — Solo responde "Rick: Recibido." sin procesar el contenido del comentario. No hay inteligencia en el flujo.

5. **No hay orquestación real de equipos** — Los equipos (Marketing, Asesoría, Mejora) están definidos en YAML pero no tienen agentes reales ejecutando. Son estructuras vacías.

6. **LiteLLM no está desplegado** — El proxy multi-modelo está comentado en docker-compose. Sin él, no hay selección real de modelo.

7. **Langfuse no está activo** — La observabilidad (trazas de LLM) no funciona.

### 🟡 Problemas Moderados

8. **Task store in-memory** — Se pierde al reiniciar. No hay persistencia de resultados.

9. **`linear_create_issue.py --enqueue` tiene bug** — `TaskQueue()` sin Redis client y firma incorrecta de `enqueue`.

10. **`install-cron.sh` sobrescribe crontab** — Puede borrar otros crons del usuario.

11. **Doc 00-overview.md desactualizado** — Muestra S2-S7 como "Planificado" cuando varios ya están implementados.

12. **Contrato API (doc 07) desactualizado** — No documenta TaskEnvelope ni endpoints actuales.

13. **Variables de entorno en VPS sin confirmar** — `NOTION_DASHBOARD_PAGE_ID`, `NOTION_CONTROL_ROOM_PAGE_ID`, `LINEAR_API_KEY`.

### 🟢 Lo que funciona bien

14. **Base de código sólida** — 130 tests pasan, arquitectura bien pensada.
15. **Worker funcional** — 22 handlers, auth, rate limiting, sanitización.
16. **Dispatcher bien diseñado** — Queue, routing, health monitoring, cuotas.
17. **Dashboard v2 con layout rico** — Tablas, callouts, KPIs, columnas en Notion.
18. **OpsLogger diseñado** — Tracking JSONL listo para usar.
19. **Protocolo inter-agentes** — Bien documentado y funcional.

---

## 4. Diagnóstico por Equipo

### Equipo Marketing
- **Estado:** Sin actividad
- **Problema:** No hay agentes ejecutando tareas de marketing
- **Necesita:** LLM conectado, prompts definidos, tareas reales en cola

### Equipo Asesoría Personal
- **Estado:** Sin actividad
- **Problema:** No hay flujo de consultas
- **Necesita:** Canal de entrada (Telegram/Notion), agentes con prompts

### Equipo Mejora Continua
- **Estado:** Sin actividad
- **Problema:** Requiere VM (que está con problemas de permisos)
- **Necesita:** OODA loop implementado, self-eval real, Langfuse activo

---

## 5. Propuestas de Mejora

### 5.1 Mejoras Inmediatas (Sprint actual)

#### A. Activar el sistema end-to-end (P0)
1. Instalar Redis en la VPS (o confirmar que está corriendo)
2. Configurar todas las variables de entorno necesarias en VPS
3. Levantar Worker en VPS con todas las API keys
4. Instalar cron del dashboard
5. Activar Dispatcher service
6. Probar flujo completo: enqueue → dequeue → execute → dashboard

#### B. Hacer que el Notion Poller sea inteligente (P0)
- Actualmente solo hace eco. Debería:
  - Parsear el contenido del comentario de David
  - Clasificar la intención (tarea, pregunta, instrucción)
  - Encolar la tarea apropiada al equipo correcto
  - Responder con un resumen de lo que va a hacer

#### C. Conectar LiteLLM o equivalente (P1)
- Descomentarlo en docker-compose y configurar las 5 API keys
- O usar las API keys directamente en los handlers
- Que cada equipo use el modelo asignado por QuotaTracker

### 5.2 Mejoras de Tracking y Observabilidad

#### D. Script de diagnóstico automatizado (P0)
Crear `scripts/hackathon_diagnostic.py` que:
- Verifica todos los componentes del sistema
- Genera un reporte en formato markdown
- Se puede ejecutar como health check periódico
- Incluye métricas de uso de cuotas LLM
- Mide la "actividad real" del sistema (tareas/hora, modelos usados, etc.)

#### E. Métricas de aprovechamiento de cuotas (P1)
- Dashboard que muestre: "De las 5 suscripciones, ¿cuánto estamos usando?"
- Alerta si alguna suscripción lleva >24h sin usar
- Reporte semanal de utilización

#### F. Log de actividad de agentes (P1)
- Registrar cuándo cada agente (Cursor, Codex, Antigravity, Copilot) trabaja
- Medir tiempo productivo vs tiempo idle
- Dashboard de contribución por agente

### 5.3 Mejoras Arquitectónicas

#### G. Persistencia de tareas (P2)
- Mover task store de in-memory a Redis o SQLite
- Historial completo de ejecuciones

#### H. Modo proactivo para Rick (P2)
- Rick no solo reacciona a comentarios, sino que:
  - Revisa cuotas disponibles y sugiere tareas
  - Ejecuta OODA loop diario automáticamente
  - Genera reportes de progreso sin que David los pida

---

## 6. Plan de Acción por Agente

### Cursor (Lead) — Coordinación y Documentación
1. ✅ Crear este documento de diagnóstico
2. Crear script de diagnóstico automatizado (`scripts/hackathon_diagnostic.py`)
3. Mejorar el Notion Poller para que sea inteligente
4. Corregir bugs encontrados (linear_create_issue, install-cron, doc 00)
5. Actualizar board.md y crear tareas para los demás agentes

### Codex — Infraestructura VPS/VM
1. Verificar y configurar Redis en VPS
2. Configurar variables de entorno en VPS (`~/.config/openclaw/env`)
3. Instalar cron del dashboard (sin sobrescribir)
4. Levantar Dispatcher service en VPS
5. Probar flujo end-to-end en VPS

### Antigravity — Mejora de Código
1. Refactorizar Notion Poller para clasificar intención
2. Mejorar task store (persistencia en Redis)
3. Actualizar doc 00-overview con estado real
4. Actualizar doc 07-api-contract con TaskEnvelope

### GitHub Copilot — Integraciones
1. Configurar LiteLLM con las 5 API keys
2. Implementar métricas de aprovechamiento de cuotas
3. Probar integración Linear end-to-end
4. Verificar integración Notion Control Room

---

## 7. Métricas de Éxito del Hackathon

| Métrica | Antes | Objetivo |
|---------|-------|----------|
| Tareas procesadas/día | 0 | >10 |
| Modelos LLM activos | 0 | ≥3 |
| Dashboard actualizado | No | Cada 15 min |
| Cuotas aprovechadas | 0% | >30% |
| Equipos con actividad | 0 | ≥2 |
| Flujo Notion→Rick funcional | No | Sí |
| Ops log con eventos | 0 | >50 |

---

## 8. Conclusión

El sistema tiene una **base técnica sólida** (130 tests, buena arquitectura, código limpio) pero está **operativamente inactivo**. La brecha entre lo documentado y lo que realmente funciona en producción es significativa.

El problema principal no es de código sino de **operacionalización**: los servicios no están corriendo 24/7, las API keys no están todas configuradas, y no hay flujo real de tareas. El dashboard muestra "Degradado" porque el sistema literal no está operando.

**La prioridad absoluta es activar el flujo end-to-end**: Redis → Dispatcher → Worker → Notion Dashboard, con al menos un equipo (Marketing o System) procesando tareas reales con al menos 2 modelos LLM.

---

## 9. Hackathon Closure — Claude Code (2026-03-04)

> **Agente:** Claude Code
> **Rondas completadas:** R6 + R7

### Entregables

| Entregable | Archivo | Estado |
|-----------|---------|--------|
| E2E Validation Suite ampliada | `scripts/e2e_validation.py` | ✅ 16 tests (10 original + 6 multi-modelo) |
| Smoke Test post-deploy | `scripts/smoke_test.py` | ✅ 4 checks (<5s) |
| Integration Tests | `scripts/integration_test.py` | ✅ 7 pipeline tests |
| Unit Tests (mock HTTP) | `tests/test_e2e_validation.py` | ✅ 14 tests, 100% pass |
| Cron wrapper VPS | `scripts/vps/e2e-validation-cron.sh` | ✅ Daily 06:00 UTC |
| API Contract actualizado | `docs/07-worker-api-contract.md` | ✅ `GET /scheduled` documentado |

### Tests Multi-Modelo (R6)

| Test | Modelo | Estado |
|------|--------|--------|
| `test_multi_model_openai` | gpt-4o-mini | ⏭️ SKIP (depende tarea 023) |
| `test_multi_model_anthropic` | claude-3-haiku | ⏭️ SKIP (depende tarea 023) |
| `test_model_routing` | routing endpoint | ⏭️ SKIP (depende tarea 024) |
| `test_scheduled_list` | GET /scheduled | ✅ Live |
| `test_scheduled_lifecycle` | enqueue → scheduled → status | ✅ Live |
| `test_quota_status` | GET /quota/status | ⏭️ SKIP (depende tarea 025) |

### Integration Tests (R7)

1. **Notion round-trip** — comment → poll → verify
2. **Quota pressure** — 3x llm.generate + quota status
3. **Rate limiting** — 70 rapid requests → expect 429
4. **Langfuse tracing** — verify trace_id in response
5. **Scheduled lifecycle** — enqueue with run_at → verify in /scheduled
6. **Composite pipeline** — research_report end-to-end
7. **Error resilience** — unknown task 400, oversized input 400, missing auth 401

### Estado del Stack

- **Worker:** v0.4.0, 25+ task handlers
- **Tests totales:** 380 passed, 1 skipped (pytest suite completa)
- **E2E suite:** 16 tests (6 SKIP conditional por dependencias no mergeadas)
- **Smoke test:** 4 checks post-deploy
- **Integration:** 7 pipeline tests end-to-end
- **Cron:** Daily validation con alerta a Notion en fallo
