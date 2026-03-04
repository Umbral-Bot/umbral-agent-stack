---
id: "2026-03-04-003"
title: "Hackathon: Mejoras de código — Notion Poller inteligente + docs actualizados"
status: assigned
assigned_to: antigravity
created_by: cursor
priority: high
sprint: S5
created_at: 2026-03-04T03:35:00-06:00
updated_at: 2026-03-04T03:35:00-06:00
---

## Objetivo
Mejorar el código del sistema según hallazgos del hackathon. Prioridad: hacer que el Notion Poller clasifique intenciones en lugar de solo hacer eco, y actualizar docs desactualizados.

## Contexto
- Diagnóstico completo: `docs/40-hackathon-diagnostico-completo.md`
- Notion Poller actual: `dispatcher/notion_poller.py` — solo responde "Rick: Recibido." sin procesar contenido
- Doc 00 desactualizado: muestra S2-S7 como "Planificado" cuando ya están implementados
- Doc 07 (API contract): no documenta TaskEnvelope ni endpoints actuales

## Tareas

### 1. Refactorizar Notion Poller (P0)
El poller actual en `dispatcher/notion_poller.py` línea 70-81 solo encola un eco. Debe:

```python
# ACTUAL (solo eco):
envelope = {
    "task": "notion.add_comment",
    "input": {"text": f"Rick: Recibido. (comment_id=...)"},
}
```

**Debe hacer:**
- Parsear el texto del comentario
- Clasificar la intención (tarea, pregunta, instrucción directa)
- Determinar el equipo más adecuado (usando `linear_team_router.py` como referencia)
- Encolar la tarea real al equipo correcto
- Responder con un resumen de la acción tomada

**Reglas:**
- Mantener backward compat: si no puede clasificar, hacer eco como ahora
- Si el comentario empieza con un equipo (@marketing, @advisory, etc.), enrutar directamente
- Si es una pregunta, encolar como `task_type: research`
- Si es una instrucción de tarea, encolar como tarea al equipo más relevante

### 2. Actualizar doc 00-overview.md (P1)
- Actualizar la tabla "Estado Actual" con el estado real de cada componente
- S1-S4: marcar como ✅ Implementado
- S5: ⚠️ Parcial
- S6-S7: ✅ Código implementado (no desplegado)

### 3. Actualizar doc 07-api-contract.md (P1)
- Documentar TaskEnvelope v0.1
- Documentar endpoint GET /tasks/{task_id}
- Documentar endpoint GET /tasks con filtros
- Documentar los 22 task handlers registrados

## Criterios de aceptación
- [ ] Notion Poller clasifica al menos 3 tipos de intención (tarea, pregunta, eco)
- [ ] Notion Poller enruta a equipo correcto basado en contenido
- [ ] Tests agregados para la clasificación de intención
- [ ] Doc 00 actualizado con estado real
- [ ] Doc 07 actualizado con TaskEnvelope y endpoints

## Log
