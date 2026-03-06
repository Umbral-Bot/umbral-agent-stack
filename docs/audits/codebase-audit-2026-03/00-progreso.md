# Progreso — Auditoría Codebase 2026-03

| Paso | Descripción | Estado |
| ---- | ----------- | ------ |
| 1 | Mapa del codebase (módulos, entry points, deps, ejecución, tests, riesgos, trabajo perdido) | ✅ Completado |
| 2 | Bugs y edge cases por riesgo (tabla priorizada P0/P1/P2) | ✅ Completado |
| 3 | Revisión de seguridad (secretos, auth, inputs, deps) | ✅ Completado |
| 4 | — | Siguiente |

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

## Paso 3 completado

Archivo: `docs/audits/codebase-audit-2026-03/03-seguridad.md`

17 hallazgos priorizados (3 Critico, 5 Alto, 5 Medio, 4 Bajo):

- 3 Critico: command injection en windows.py (run_as_password→schtasks, name→netsh), WORKER_TOKEN en plaintext
- 5 Alto: timing attack en auth, os.environ sobreescrito desde archivo externo, path traversal por username, IPs Tailscale en .env.example, Notion DB ID hardcodeado
- 5 Medio: _check_injection() no bloquea, contenido Notion sin sanitizar, token sin rotacion, sin headers HTTP, LINEAR_WEBHOOK_SECRET ausente en .env.example
- 4 Bajo: SecretStore no integrado, sin rate limit en auth, sin lock files/pip-audit, weasyprint sin verificacion de libs

Quick wins identificados: SEC-7 (1 linea), SEC-11, SEC-13, SEC-3, SEC-2, SEC-5.

## Siguiente: Paso 4

A definir con el usuario.
