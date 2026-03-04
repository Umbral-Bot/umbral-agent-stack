# Hackathon: Notion Poller inteligente

**Assigned:** antigravity  
**Priority:** P0  
**Status:** assigned  
**Created:** 2026-03-04

## Contexto

El Notion Poller (`dispatcher/notion_poller.py`) actualmente solo hace eco: cuando David comenta en la Control Room, responde "Rick: Recibido." sin procesar el contenido. Esto hace que el flujo David → Rick → tareas no funcione.

La Control Room de Notion ya tiene acceso para la integración (verificado 2026-03-04).

## Tareas

1. **Clasificar la intención del comentario**:
   - Parsear el texto del comentario de David.
   - Clasificar en: `tarea` (algo que hacer), `pregunta` (algo que responder), `instrucción` (configuración/cambio).
   - Usar heurísticas simples primero (keywords como "haz", "crea", "revisa" → tarea; "?" → pregunta; "configura", "cambia" → instrucción).

2. **Encolar tarea al equipo correcto**:
   - Si es `tarea`: determinar equipo (marketing, advisory, system, improvement) según keywords del comentario.
   - Crear un TaskEnvelope con la clasificación y encolarlo en Redis vía `TaskQueue.enqueue()`.
   - Si es `pregunta`: responder con un comentario en Notion (usando el Worker `notion.add_comment`).

3. **Responder con contexto**:
   - En vez de "Rick: Recibido.", responder con algo como: "Rick: Entendido. Creé tarea [tipo] para equipo [X]. ID: [task_id]."

4. **Test**:
   - Escribir un comentario en la Control Room (Notion page `30c5f443fb5c80eeb721dc5727b20dca`).
   - Verificar que el Poller lo clasifica, encola y responde.

## Archivos relevantes

- `dispatcher/notion_poller.py` — Poller actual (modificar aquí)
- `dispatcher/queue.py` — TaskQueue para encolar
- `dispatcher/team_config.py` — Configuración de equipos
- `config/teams.yaml` — Definición de equipos

## Entrega

Responder en `.agents/board.md` con estado de la tarea y commit con los cambios.
