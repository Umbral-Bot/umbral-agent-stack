# Progreso — Auditoría Codebase 2026-03

| Paso | Descripción | Estado |
| ---- | ----------- | ------ |
| 1 | Mapa del codebase (módulos, entry points, deps, ejecución, tests, riesgos, trabajo perdido) | ✅ Completado |
| 2 | Bugs y edge cases por riesgo (tabla priorizada P0/P1/P2) | ✅ Completado |
| 3 | — | Siguiente |

## Paso 1 completado

Archivo: `docs/audits/codebase-audit-2026-03/01-mapa.md`

Secciones cubiertas:
1. Módulos principales (worker, dispatcher, client, infra, config, openclaw, scripts, tests)
2. Entry points (VPS systemd + crons, Windows NSSM, scripts standalone)
3. Dependencias críticas (runtime + test + dependencias no declaradas)
4. Cómo se ejecuta (flujo completo, env vars mínimas)
5. Cómo se testea (pytest 900 tests, CI GitHub Actions, scripts E2E/smoke/integration)
6. Top 10 riesgos técnicos priorizados
7. Ideas y trabajo parcial perdido (worker, dispatcher, scripts, docs, ramas/PRs)

## Paso 2 completado

Archivo: `docs/audits/codebase-audit-2026-03/02-bugs.md`

17 bugs/edge cases identificados y priorizados:

- 3 P0 (pérdida de datos / bloqueo total): sanitize descartado, event loop bloqueado, tarea perdida en TTL
- 8 P1 (comportamiento incorrecto silencioso): task_queued nunca emitido, imports sin fallback, hijos perdidos en prepend, timing attack, date comparison frágil, weasyprint sin CI, callback_url perdido, block_task TOCTOU
- 5 P2 (degradado / inconsistencia): dual rate limiter, quota race condition, child_database borrado, model IDs ficticios, filtro /tasks incorrecto

Top 3 a corregir primero: #3 sanitize (1 línea), #1/#2 event loop (run_in_executor), #4 tarea perdida en TTL.

## Siguiente: Paso 3

A definir con el usuario.
