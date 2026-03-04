# Agent Board — Umbral Agent Stack

> Última actualización: 2026-03-03 por **cursor**
> Sprint activo: **S5**

## Estado del sistema

| Aspecto | Estado |
|---------|--------|
| Protocolo inter-agentes | ✅ Activo |
| n8n en VPS | ✅ Instalado y en marcha (Rick 2026-03-03) |
| Verificación protocolos | Doc 38 actualizada con estado; pendiente confirmar en VPS: cron dashboard, env Notion/Linear |
| Tareas pendientes | 0 |
| Tareas en progreso | 0 |
| Tareas bloqueadas | 0 |

## Tareas activas

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 2026-02-28-001 | VM: deshabilitar tasks legacy y limpiar Gateway (regularización fase 1) | codex | ✅ (parcial: falta OpenClaw Gateway por permisos admin) |
| 2026-02-28-002 | VM: actualizar Worker al modular del repo y probar PAD | codex | ✅ (parcial: falta reiniciar servicio como Admin + instalar PAD) |
| 2026-02-28-003 | VM: ejecutar runbook diagnóstico schtasks /ru y reportar resultados | codex | blocked |
| 2026-02-28-004 | VM: diagnóstico schtasks sin /ru — SID error pese a debug_used_ru: false | codex | assigned |

## Tareas completadas recientes

| ID | Título | Asignado |
|----|--------|----------|
| 2026-03-03-002 | Google Custom Search: investigar 403 (no viable) | github-copilot | ✅ |
| 2026-03-03-001 | SIM discovery: fallback búsqueda (Tavily) | github-copilot | ✅ |
| 2026-02-27-001 | VPS: Git (Deploy Key), clonar, .venv, pytest + test_s2_dispatcher | antigravity | ✅ |
| 2026-02-27-002 | VM: documentar setup Worker + runbook levantar todo | codex | ✅ |
| 2026-02-27-003 | VM: auditar OpenClaw, proyectos y automatizaciones — regularizar | codex | ✅ |

## Notas

- El protocolo fue establecido el 2026-02-27.
- Agentes configurados: Cursor (lead), Antigravity, Codex, GitHub Copilot.
- Motor de búsqueda web para SIM: **Google Custom Search no viable** (403 conocido de Google desde ~2024). Motor activo: **Tavily** (`TAVILY_API_KEY`). Ver tareas 2026-03-03-001 y 002.
- **Verificación de protocolos:** Dashboard (Notion), Linear, Notion Control Room, board: ver [docs/38-protocol-compliance-check.md](../docs/38-protocol-compliance-check.md).
