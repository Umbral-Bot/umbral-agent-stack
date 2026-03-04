# Agent Board — Umbral Agent Stack

> Última actualización: 2026-03-04 por **cursor**
> Sprint activo: **S5**
> **HACKATHON DIAGNÓSTICO EN CURSO**

## Estado del sistema

| Aspecto | Estado |
|---------|--------|
| Protocolo inter-agentes | ✅ Activo |
| n8n en VPS | ✅ Instalado y en marcha (Rick 2026-03-03) |
| Hackathon diagnóstico | 🔴 En curso — sistema operativamente inactivo |
| Verificación protocolos | Doc 38 y **Doc 40 (hackathon)** con diagnóstico completo |
| Tareas pendientes | 3 (hackathon) |
| Tareas en progreso | 1 (cursor - diagnóstico) |
| Tareas bloqueadas | 3 (de sprints anteriores) |

## Hackathon — Tareas Activas (2026-03-04)

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 2026-03-04-001 | Hackathon: Diagnóstico completo + script + fixes | cursor | 🔄 in_progress |
| 2026-03-04-002 | Hackathon: Verificar/activar infraestructura VPS | codex | 📋 assigned |
| 2026-03-04-003 | Hackathon: Mejoras de código — Poller inteligente + docs | antigravity | 📋 assigned |
| 2026-03-04-004 | Hackathon: Integraciones — LiteLLM, cuotas, Notion | github-copilot | 📋 assigned |

## Tareas anteriores (pre-hackathon)

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 2026-02-28-001 | VM: deshabilitar tasks legacy y limpiar Gateway | codex | ✅ (parcial) |
| 2026-02-28-002 | VM: actualizar Worker al modular + probar PAD | codex | ✅ (parcial) |
| 2026-02-28-003 | VM: diagnóstico schtasks /ru | codex | blocked |
| 2026-02-28-004 | VM: diagnóstico schtasks sin /ru | codex | assigned |

## Tareas completadas recientes

| ID | Título | Asignado |
|----|--------|----------|
| 2026-03-03-002 | Google Custom Search: investigar 403 (no viable) | github-copilot | ✅ |
| 2026-03-03-001 | SIM discovery: fallback búsqueda (Tavily) | github-copilot | ✅ |
| 2026-02-27-001 | VPS: Git (Deploy Key), clonar, .venv, pytest + test_s2_dispatcher | antigravity | ✅ |
| 2026-02-27-002 | VM: documentar setup Worker + runbook levantar todo | codex | ✅ |
| 2026-02-27-003 | VM: auditar OpenClaw, proyectos y automatizaciones — regularizar | codex | ✅ |

## Diagnóstico del Hackathon (resumen)

### Hallazgos críticos
1. **Sistema operativamente INACTIVO** — 0 tareas procesadas, 0 eventos en ops_log
2. **Dashboard no funciona** — muestra "Degradado", workers offline
3. **Cuotas LLM sin usar** — 0% de aprovechamiento de las 5 suscripciones
4. **Notion Poller es solo eco** — no procesa contenido de comentarios
5. **Equipos sin actividad** — Marketing, Asesoría, Mejora: 0 tareas

### Lo que funciona bien
- 130 tests pasan (base técnica sólida)
- Worker: 22 handlers, auth, rate limiting, sanitización
- Dispatcher: queue, routing, health monitor, cuotas
- Dashboard v2: layout rico para Notion
- Protocolo inter-agentes: funcional

### Documentación
- **Diagnóstico completo:** [docs/40-hackathon-diagnostico-completo.md](../docs/40-hackathon-diagnostico-completo.md)
- **Script diagnóstico:** `scripts/hackathon_diagnostic.py` (ejecutable como health check)

## Notas

- El protocolo fue establecido el 2026-02-27.
- Agentes configurados: Cursor (lead), Antigravity, Codex, GitHub Copilot.
- Motor de búsqueda web: **Tavily** (Google Custom Search no viable).
- **Prioridad absoluta:** Activar flujo end-to-end (Redis → Dispatcher → Worker → Dashboard).
