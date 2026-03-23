---
id: "030"
title: "E2E Integration Final — Validación completa del stack multi-modelo + Langfuse"
assigned_to: claude-code
branch: feat/claude-final-e2e
round: 7
status: done
updated_at: "2026-03-22T19:04:21-03:00"
created: 2026-03-04
---

## Objetivo

Validación final de integración que cubre todo el stack: multi-modelo, Langfuse tracing, rate limiting, scheduled tasks, y quota tracking. El "acceptance test" definitivo.

## Contexto

- `scripts/e2e_validation.py` — actualizado en tarea 026 con tests multi-modelo
- `scripts/smoke_test.py` — creado en tarea 026
- Todo el stack post-Ronda 6 y 7

## Requisitos

### 1. Integration Test Script: `scripts/integration_test.py`

Crear un script de integración que valide el flujo completo end-to-end:

```python
# Test 1: Full pipeline - Notion comment → smart reply con model routing
#   - Simular un comentario de pregunta
#   - Verificar que ModelRouter selecciona el modelo correcto
#   - Verificar que el Worker usa el provider correcto
#   - Verificar que la respuesta se postea en Notion

# Test 2: Quota pressure test
#   - Enviar múltiples llm.generate con distintos task_types
#   - Verificar que quota_tracker se incrementa
#   - Verificar que GET /quota/status refleja el uso

# Test 3: Rate limiting
#   - Enviar 70 requests rápidos al Worker
#   - Verificar que se recibe 429 después del límite

# Test 4: Langfuse tracing (si configurado)
#   - Enviar llm.generate
#   - Verificar que trace_llm_call no falla
#   - (No se puede validar en Langfuse directamente desde test)

# Test 5: Scheduled task lifecycle
#   - Programar tarea +2min via POST /enqueue con run_at
#   - Verificar aparece en GET /scheduled
#   - Cancelar via API
#   - Verificar desaparece de /scheduled

# Test 6: Composite pipeline con model routing
#   - composite.research_report con topic
#   - Verificar que usa el modelo seleccionado por ModelRouter
#   - Verificar resultado completo

# Test 7: Error handling resilience
#   - Enviar llm.generate con modelo inexistente
#   - Verificar error graceful, no crash
#   - Verificar AlertManager registra el fallo
```

### 2. GitHub Actions workflow (opcional, si hay Actions configurado)

Crear `.github/workflows/e2e-test.yml`:
- Trigger: manual (workflow_dispatch) + después de merge a main
- Ejecuta `smoke_test.py` contra producción
- Notifica resultado en Notion

### 3. Reporte final en Notion

Al final de todos los tests, generar un reporte "Hackathon Closure" en Notion:

```
🏁 Hackathon Final Report — 2026-03-04

Stack Status: PRODUCTION READY
E2E: X/Y PASS
Multi-Model: Gemini ✅ | OpenAI ✅/SKIP | Anthropic ✅/SKIP
Langfuse: ✅ Connected / ⚠️ Not configured
Scheduled Tasks: ✅ Operational
Rate Limiting: ✅ Active
Quota Tracking: ✅ Active

PRs: 30 merged across 7 rounds
Agents: Cursor, Codex, Copilot, Antigravity, Claude Code
```

### 4. Actualizar docs

- `docs/07-worker-api-contract.md` — versión final completa
- `docs/40-hackathon-diagnostico-completo.md` — agregar sección de cierre
- `README.md` — actualizar con estado actual del sistema

## Entregable

PR a `main` desde `feat/claude-final-e2e` con todos los tests pasando.

## Log

### [codex] 2026-03-22 19:04 -03:00
Regularizacion administrativa por UMB-132. Esta tarea quedo como arrastre historico y ya no representa trabajo vivo; se cierra el archivo para alinearlo con el board y el estado real del repo.
