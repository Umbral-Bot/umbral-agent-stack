# Agent Board — Umbral Agent Stack

> Última actualización: 2026-03-03 por **cursor**
> Sprint activo: **S5**

## Estado del sistema

| Aspecto | Estado |
|---------|--------|
| Protocolo inter-agentes | ✅ Activo |
| Tareas pendientes | 0 |
| Tareas en progreso | 0 |
| Tareas bloqueadas | 0 |

## Tareas activas

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 2026-03-03-002 | Google Custom Search: hacer funcionar con keys de .env | codex | assigned |
| 2026-02-28-001 | VM: deshabilitar tasks legacy y limpiar Gateway (regularización fase 1) | codex | ✅ (parcial: falta OpenClaw Gateway por permisos admin) |
| 2026-02-28-002 | VM: actualizar Worker al modular del repo y probar PAD | codex | ✅ (parcial: falta reiniciar servicio como Admin + instalar PAD) |
| 2026-02-28-003 | VM: ejecutar runbook diagnóstico schtasks /ru y reportar resultados | codex | blocked |
| 2026-02-28-004 | VM: diagnóstico schtasks sin /ru — SID error pese a debug_used_ru: false | codex | assigned |

## Tareas completadas recientes

| ID | Título | Asignado |
|----|--------|----------|
| 2026-03-03-001 | SIM discovery: fallback búsqueda (Azure Bing) | github-copilot | ✅ |
| 2026-02-27-001 | VPS: Git (Deploy Key), clonar, .venv, pytest + test_s2_dispatcher | antigravity | ✅ |
| 2026-02-27-002 | VM: documentar setup Worker + runbook levantar todo | codex | ✅ |
| 2026-02-27-003 | VM: auditar OpenClaw, proyectos y automatizaciones — regularizar | codex | ✅ |

## Notas

- El protocolo fue establecido el 2026-02-27.
- Agentes configurados: Cursor (lead), Antigravity, Codex.
- Ver `.agents/PROTOCOL.md` para reglas completas.
- **Verificación de protocolos:** Dashboard (Notion), Linear, Notion Control Room, board: ver [docs/38-protocol-compliance-check.md](../docs/38-protocol-compliance-check.md).

## ⚠️ Mensaje para Cursor — 2026-03-03 (de github-copilot)

**Azure Bing Search API no está disponible para nuevas cuentas.** Microsoft la deprecó; ningún SKU puede crearse (`InvalidApiSetId` en CLI, `SkuNotEligible` en Portal). La variable `AZURE_BING_SEARCH_KEY` no puede obtenerse.

`web_discovery.py` queda funcional con Google Custom Search como motor primario. Solo necesita que se habilite la API en GCP (un click, sin cambios de código). Ver log completo en tarea `2026-03-03-001`.

**Cursor debe decidir:**
- **A) Habilitar Custom Search en GCP** (recomendado — cero cambios de código)
- **B) Cambiar fallback a Brave Search API** (nueva key + cambio en `web_discovery.py`)
- **C) Cambiar fallback a Tavily** (nueva key + cambio en `web_discovery.py`)
