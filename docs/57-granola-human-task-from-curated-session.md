# 57 - Granola create_human_task_from_curated_session

> Slice conservador para derivar una tarea humana desde una sesion curada sin escribir todavia en la DB comercial humana.

## 1. Objetivo

`granola.create_human_task_from_curated_session` cubre el primer tramo real de:

- `Transcripciones Granola` como capa raw
- `Registro de Sesiones y Transcripciones` como capa curada
- `Registro de Tareas y Proximas Acciones` como primer destino humano operativo

No intenta actualizar proyectos comerciales por inferencia.
No reemplaza la clasificacion humana.

## 2. Qué hace

Parte desde una sesion curada existente y:

- lee la pagina real como evidencia
- requiere `NOTION_HUMAN_TASKS_DB_ID`
- inspecciona el schema vivo de la DB humana de tareas antes de escribir
- exige `task_name` explicito
- crea o actualiza la tarea humana por titulo exacto
- hereda la relacion `Proyecto` desde la sesion curada cuando existe
- enlaza `Sesion relacionada`
- deja comentarios de trazabilidad entre sesion curada y tarea humana cuando `add_trace_comments=true`

## 3. Qué no hace

- no decide por si sola si hay que crear una tarea humana
- no inventa el nombre de la tarea si no se lo pasas
- no asigna responsable humano por defecto
- no escribe todavia en `Asesorías & Proyectos`
- no infiere fechas objetivo si no se le entregan

## 4. Payload mínimo

```json
{
  "curated_session_page_id": "<curated-session-page-id>",
  "task_name": "Revisar contrato Konstruedu"
}
```

Con eso:

- hereda `Dominio` desde la sesion curada si existe
- hereda `Proyecto` desde la sesion curada si existe
- enlaza `Sesion relacionada`
- usa defaults conservadores:
  - `Tipo = Follow-up`
  - `Estado = Pendiente`
  - `Origen = Sesion`

## 5. Payload recomendado

```json
{
  "curated_session_page_id": "<curated-session-page-id>",
  "task_name": "Revisar contrato Konstruedu",
  "task_type": "Follow-up",
  "estado": "Pendiente",
  "priority": "Alta",
  "due_date": "2026-03-31",
  "notes": "Siguiente paso observado en la sesion curada: revisar contrato con Konstruedu y coordinar la bajada con diseno instruccional.",
  "add_trace_comments": true
}
```

## 6. Campos que intenta mapear

Solo si el schema vivo los soporta:

- `Nombre`
- `Dominio`
- `Proyecto`
- `Sesion relacionada`
- `Tipo`
- `Estado`
- `Prioridad`
- `Fecha objetivo`
- `Origen`
- `URL fuente`
- `Notas`

## 7. Estado operativo actual

Al 2026-03-27:

- `NOTION_HUMAN_TASKS_DB_ID` ya es reachable con Rick
- la tarea puede crearse o actualizarse por titulo exacto
- la relacion `Sesion relacionada` ya quedo validada en vivo
- la relacion `Proyecto` heredada desde la sesion curada ya quedo validada en vivo

## 8. Piloto live validado

Validacion ejecutada el 2026-03-27 con:

- sesion curada:
  - `Konstruedu - propuesta 6 cursos`
  - page id: `3305f443-fb5c-81cd-ba63-c6d06624f6a2`
- tarea humana creada:
  - `Revisar contrato Konstruedu`
  - page id: `3305f443-fb5c-81a0-8239-fd9ec0600ae3`

Propiedades verificadas:

- `Dominio = Operacion`
- `Proyecto` relacionado a `Especialización IA + Automatización AECO — 6 Cursos Konstruedu`
- `Sesion relacionada` enlazada a la sesion curada
- `Tipo = Follow-up`
- `Estado = Pendiente`
- `Prioridad = Alta`
- `Origen = Sesion`
- `URL fuente` apuntando a la sesion curada

## 9. Siguiente frente recomendado

Si se desea continuar el pipeline, el siguiente slice deberia ser explícito y separado:

- actualizar `Asesorías & Proyectos` desde una sesion curada solo cuando el payload indique exactamente qué campo comercial tocar

No conviene mezclar ese comportamiento con la creacion de tareas humanas.

## 10. Referencias

- `worker/tasks/granola.py`
- `tests/test_granola.py`
- `docs/50-granola-notion-pipeline.md`
- `docs/53-granola-raw-curated-promotion-plan.md`
- `docs/56-granola-promote-curated-session.md`
