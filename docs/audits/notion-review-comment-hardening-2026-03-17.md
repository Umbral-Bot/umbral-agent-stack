# Notion review comment hardening - 2026-03-17

## Objetivo
Endurecer el flujo de comentarios de revisión en Notion para que Rick pueda reaccionar de forma más consistente a feedback corto sobre proyectos y entregables, evitando ambigüedades, colisiones de tareas y errores de encoding.

## Problemas reales detectados
1. El poller de Notion solo vigilaba `Control Room`, no comentarios de revisión puestos directamente sobre páginas de `Proyectos` o `Entregables`.
2. El clasificador de intención trataba cualquier `?` como pregunta, incluso cuando el carácter venía de mojibake dentro de palabras como `regularización?`.
3. Las tareas creadas por `_handle_instruction()` usaban solo los primeros 8 caracteres del `comment_id`, lo que generaba colisiones entre comentarios distintos con el mismo prefijo.
4. El canal para postear mensajes desde scripts podía degradar UTF-8 si el texto viajaba por PowerShell y SSH sin codificación explícita.
5. Aunque el poller ya detectaba comentarios sobre `Proyectos` y `Entregables`, las tareas creadas desde esos comentarios no heredaban automáticamente la relación al proyecto o entregable de origen.
6. `_handle_instruction()` enviaba la segunda actualización con `status = in_progress`, pero la base `Tareas` solo acepta `queued`, `running`, `done`, `blocked` y `failed`.

## Cambios aplicados
### `dispatcher/intent_classifier.py`
- se añadieron patrones de feedback corto de revisión:
  - `no se entiende`
  - `trabajo incompleto`
  - `aprobado con ajustes`
  - `regulariza`
  - variantes similares
- se añadió `_looks_like_question()` para ignorar `?` incrustados dentro de palabras y no tratarlos como preguntas reales

### `dispatcher/notion_poller.py`
- se añadió ventana de solape (`NOTION_POLL_OVERLAP_SEC`) para reducir pérdida de eventos en bordes temporales
- se añadieron `review targets`:
  - páginas relevantes de `Entregables`
  - páginas de `Proyectos`
  - además de `Control Room`
- se añadió deduplicación por `comment_id`
- si el filtro de deliverables por `Estado revisión` falla, el poller reintenta sin filtro
- los comentarios relevantes ahora preservan contexto de origen:
  - `page_id`
  - `page_kind = project | deliverable`

### `dispatcher/smart_reply.py`
- se añadió `_instruction_task_id(comment_id)` para crear ids únicos a partir del comentario completo, no solo de su prefijo corto
- `_handle_instruction()` y `_build_instruction_message()` quedaron alineados con ese id nuevo
- `_handle_instruction()` ahora hereda:
  - `project_page_id` cuando el comentario viene de una página de proyecto
  - `deliverable_page_id` cuando viene de una página de entregable
- el segundo estado de seguimiento se corrigió a `running` en vez de `in_progress`

### `worker/tasks/notion.py`
- `notion.upsert_task` ahora puede inferir `project_page_id` desde la relación `Proyecto` del entregable cuando se recibe `deliverable_page_id` pero no proyecto explícito

### `scripts/post_notion_message.py`
- se añadió soporte `--base64` para enviar texto UTF-8 robustamente por SSH

## Verificación remota
### Caso Kris
- `Benchmark parcial de Kris Wojslaw para el embudo`
  - `Estado revisión = Rechazado`
  - conserva un solo comentario de revisión:
    - `trabajo incompleto`
  - eso es correcto: no necesitaba comentario nuevo
- tarea asociada:
  - `Task ID = notion-instruction-3265f443`
  - `Status = done`
  - `Proyecto` y `Entregable` ligados correctamente
- conclusión:
  - el frente Kris quedó semánticamente cerrado como benchmark parcial rechazado
  - el error estaba en la interpretación de la auditoría, no en la ausencia de comentario nuevo

### Caso embudo derivado
- `Ingeniería inversa del sistema de Ruben Hassid para el embudo`
  - `Procedencia = Tarea`
  - `Task ID origen` y `Tareas origen` presentes
  - tarea de regularización: `done`
- `Definición operativa del CTA y captura del embudo`
  - `Procedencia = Tarea`
  - `Task ID origen` y `Tareas origen` presentes
  - tarea de regularización: `done`

## Resultado
El sistema ya no depende solo de `Control Room` para captar comentarios relevantes y dejó de confundir mojibake con preguntas reales. Además, las instrucciones desde Notion ya no deberían pisarse entre sí cuando comparten prefijos similares de `comment_id`, y si nacen desde una página de proyecto o entregable quedan mejor contextualizadas.

## Residual honesto
- siguen existiendo tareas históricas con ids cortos como `notion-instruction-3265f443` porque fueron creadas antes del hardening; no conviene reescribirlas retroactivamente si ya quedaron funcionalmente cerradas
- el filtro remoto por deliverables seguía siendo frágil; el poller ya hace fallback sin romper el flujo
