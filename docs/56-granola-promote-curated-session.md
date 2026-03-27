# 56 - Granola promote_curated_session

> Slice conservador para promover una pagina raw de Granola hacia la DB humana curada de sesiones sin mezclar intake bruto con capitalizacion operativa.

## 1. Objetivo

`granola.promote_curated_session` cubre el primer tramo real de:

- `Transcripciones Granola` como capa raw canonica
- `Registro de Sesiones y Transcripciones` como capa humana curada

No automatiza todavia la derivacion completa a proyectos, tareas o recursos.
No reemplaza la clasificacion humana.

## 2. Que hace

Parte desde una pagina raw existente y:

- lee la pagina real como evidencia
- requiere `NOTION_CURATED_SESSIONS_DB_ID`
- lee el schema vivo de la DB curada antes de escribir
- crea o actualiza la sesion curada con este orden de matching:
  - primero por `URL fuente` del raw
  - luego por titulo exacto
  - por ultimo por `titulo_normalizado + fecha`
- solo rellena campos realmente soportados por la DB
- solo crea relaciones cuando recibe `page_id` explicitos
- deja comentarios de trazabilidad entre raw y curado cuando `add_trace_comments=true`
- sincroniza el estado de la raw a `Procesada` cuando el schema raw lo soporta

## 3. Que no hace

- no intenta adivinar el hub humano correcto si la DB curada no esta compartida
- no convierte automaticamente sesiones en tareas humanas
- no resuelve por si sola `curado -> destino`
- no infiere relaciones a proyecto, programa o recurso sin `page_id`
- no asume que el schema humano es estable; se adapta al schema observado

## 4. Payload minimo

```json
{
  "transcript_page_id": "<raw-page-id>"
}
```

Con eso:

- usa el titulo raw como `session_name`
- usa la fecha raw
- usa el origen raw
- agrega `URL fuente`
- agrega notas de trazabilidad basicas

## 5. Payload recomendado

```json
{
  "transcript_page_id": "<raw-page-id>",
  "session_name": "Sesion Borago - Curada",
  "domain": "Operacion",
  "session_type": "Asesoria",
  "estado": "Pendiente",
  "summary": "Sesion comercial curada para seguimiento.",
  "notes": "Notas humanas adicionales.",
  "project_page_id": "<project-page-id>",
  "program_page_id": "<program-page-id>",
  "resource_page_id": "<resource-page-id>",
  "add_trace_comments": true
}
```

## 6. Campos que intenta mapear

Solo si el schema vivo los soporta:

- `Nombre`
- `Fecha`
- `Dominio`
- `Tipo`
- `Estado`
- `Origen`
- `URL fuente`
- `Resumen`
- `Notas`
- `Proyecto`
- `Programa`
- `Recurso relacionado`
- `Transcripcion disponible`

Si el campo no existe o no coincide en tipo, se omite sin fallar.

## 7. Estado operativo actual

Al 2026-03-27 el reachability ya quedo resuelto:

- `Registro de Sesiones y Transcripciones` esta reachable con Rick
- `Registro de Tareas y Proximas Acciones` esta reachable con Rick
- `Asesorias & Proyectos` esta reachable con Rick

Eso significa que `granola.promote_curated_session` ya puede ejecutarse live.

Secuencia correcta:

1. elegir una reunion raw ya validada
2. identificar si conviene enlazarla a un proyecto humano
3. ejecutar `granola.promote_curated_session`
4. revisar el resultado en la DB curada antes de avanzar a `curado -> destino`

## 8. Validacion repo-side

Validado con tests unitarios:

- requiere `transcript_page_id`
- falla si `NOTION_CURATED_SESSIONS_DB_ID` no esta configurado
- crea una sesion curada cuando no hay match previo
- actualiza una sesion existente por `URL fuente` cuando el raw ya fue promovido
- hace fallback a titulo exacto y despues a `titulo_normalizado + fecha`
- puede omitir comentarios de trazabilidad
- puede sincronizar el estado de la raw sin volver a crear la sesion curada

## 9. Piloto live validado

Validacion ejecutada el 2026-03-27 con:

- raw page id: `3305f443-fb5c-81db-9162-fd70c8574938`
- raw title: `Konstruedu`
- proyecto humano relacionado:
  - `Especializacion IA + Automatizacion AECO - 6 Cursos Konstruedu`
  - page id: `dcd955f0-28e5-432a-a7ed-9be1ea091a74`

Resultado:

- sesion curada creada:
  - `Konstruedu - propuesta 6 cursos`
  - page id: `3305f443-fb5c-81cd-ba63-c6d06624f6a2`
- relacion `Proyecto` enlazada al proyecto humano correcto
- `Fuente` quedo como `Granola`
- `Dominio` quedo como `Operacion`
- `Estado` quedo como `Capturada`
- `Transcripcion disponible` quedo en `true`
- se dejaron comentarios de trazabilidad entre raw y curado

## 10. Nota practica para payloads live

El handler soporta unicode, pero si el payload se pasa por consola PowerShell sin cuidar encoding, pueden degradarse caracteres a `?`.

Para ejecuciones live conviene:

- usar payload ASCII cuando sea suficiente
- o fijar UTF-8 explicito en la ruta de ejecucion
- o invocar la task desde Python dict o Worker client sin depender de stdin shell

La resolucion por `URL fuente` deja este riesgo mucho mas acotado: aunque `session_name` llegue mangled por consola, la task ya no deberia crear una sesion curada nueva si el raw ya estaba promovido.

## 11. Referencias

- `worker/tasks/granola.py`
- `tests/test_granola.py`
- `docs/50-granola-notion-pipeline.md`
- `docs/53-granola-raw-curated-promotion-plan.md`
- `docs/55-granola-human-surface-access.md`
