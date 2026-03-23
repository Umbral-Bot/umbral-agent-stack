---
id: "012"
title: "Smart Notion Reply Pipeline"
assigned_to: claude-code
status: done
updated_at: "2026-03-22T19:04:21-03:00"
branch: feat/claude-smart-reply
priority: critical
round: 3
---

# Smart Notion Reply Pipeline

## Problema
Cuando David escribe una pregunta en Notion Control Room, el poller la detecta y responde
"Pregunta recibida. Investigando y responderé pronto." — pero NUNCA investiga ni responde.
Rick promete y no cumple. Este es el gap #1 del sistema.

## Tu tarea
Crear un módulo `dispatcher/smart_reply.py` que el Notion Poller invoque cuando detecta
una pregunta o tarea, para generar una respuesta inteligente usando research.web + llm.generate.

### A. Módulo smart_reply.py
```python
async def handle_smart_reply(comment_text, comment_id, intent, team, wc, queue):
    # 1. Si intent == "question":
    #    a) Ejecutar research.web via WorkerClient con el texto como query
    #    b) Tomar los top 3 resultados
    #    c) Construir prompt para llm.generate con contexto de los resultados
    #    d) Ejecutar llm.generate para generar respuesta
    #    e) Postear respuesta como notion.add_comment
    #
    # 2. Si intent == "task":
    #    a) Usar llm.generate para descomponer la tarea en pasos
    #    b) Postear plan como notion.add_comment
    #    c) Encolar los sub-pasos como tareas individuales
    #
    # 3. Si intent == "instruction":
    #    a) Confirmar qué se va a cambiar
    #    b) Postear confirmación
```

### B. Integrar en notion_poller.py
Modificar `_do_poll()` para que después de clasificar el intent, llame a `smart_reply`
en lugar de solo encolar un acknowledgment template.

### C. Manejo de errores
- Si research.web falla, responder solo con LLM (sin contexto web)
- Si llm.generate falla, responder con el acknowledgment template actual (fallback)
- Timeout máximo: 30 segundos por respuesta
- Loguear todo con OpsLogger

### D. Tests
Crear `tests/test_smart_reply.py`:
- Mock de WorkerClient para research.web y llm.generate
- Test: pregunta genera research + llm + comment
- Test: task genera plan + sub-tareas
- Test: fallback cuando research falla
- Test: fallback cuando llm falla

## Archivos relevantes
- `dispatcher/notion_poller.py` — _do_poll() (modificar)
- `dispatcher/intent_classifier.py` — classify_intent, build_envelope (referencia)
- `client/worker_client.py` — WorkerClient (usar para llamar al Worker)
- `worker/tasks/research.py` — handle_research_web (referencia)
- `worker/tasks/llm.py` — handle_llm_generate (referencia)

## Variables de entorno necesarias
Ya configuradas en VPS: WORKER_URL, WORKER_TOKEN, TAVILY_API_KEY, GOOGLE_API_KEY

## Log

### [codex] 2026-03-22 19:04 -03:00
Regularizacion administrativa por UMB-132. Esta tarea quedo como arrastre historico y ya no representa trabajo vivo; se cierra el archivo para alinearlo con el board y el estado real del repo.
