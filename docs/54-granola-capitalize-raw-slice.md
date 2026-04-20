# 54 - Granola capitalize_raw

> Slice operativo para capitalizar una pagina raw de Granola hacia objetos canonicos que el stack ya gobierna hoy.

## 1. Objetivo

`granola.capitalize_raw` existe para cubrir el hueco entre:

- el intake raw ya validado en `NOTION_GRANOLA_DB_ID`
- y la futura promocion completa `raw -> curado -> destino`

No clasifica automaticamente hacia la DB humana curada.
No crea proyectos tecnicos por reflejo.
No reemplaza la decision humana sobre el contenedor final.

## 2. Que hace

Parte desde una pagina raw ya existente y:

- lee la pagina real para mantener trazabilidad
- exige destinos explicitos en el payload
- hoy puede escribir a:
  - `notion.upsert_project`
  - `notion.upsert_deliverable`
  - `notion.upsert_bridge_item`
  - `granola.create_followup`
- agrega comentarios de trazabilidad entre raw y destino cuando `add_trace_comments=true`

## 3. Que no hace

- no promueve automaticamente a la DB humana curada
- no usa `NOTION_TASKS_DB_ID` como si fuera la DB humana de proximas acciones
- no decide por si solo si una reunion comercial debe vivir como proyecto tecnico del stack
- no deduplica follow-ups tipo propuesta; si repites el mismo payload, puedes crear otra pagina hija

## 4. Regla practica de uso

Usar `granola.capitalize_raw` cuando:

- la pagina raw ya existe en `Transcripciones Granola`
- el destino dentro del stack es claro
- quieres dejar trazabilidad operativa sin abrir paginas sueltas

Preferir `bridge_item` cuando:

- la reunion pertenece al sistema humano de proyectos/asesorias y no al registry tecnico del stack
- aun no hay un proyecto tecnico canonico del stack al cual asociarla
- el mejor cierre dentro del repo es dejar un handoff claro para revision humana

## 5. Ejecucion estandar

Usar `scripts/run_worker_task.py`:

```powershell
python scripts/run_worker_task.py granola.capitalize_raw "{\
  \"transcript_page_id\": \"3305f443-fb5c-81db-9162-fd70c8574938\",\
  \"bridge_item_name\": \"Seguimiento oportunidad Konstruedu desde Granola\",\
  \"bridge_priority\": \"Alta\",\
  \"bridge_source\": \"Control Room\",\
  \"bridge_notes\": \"Reunion comercial/documental capturada en raw. No pertenece al registry tecnico de proyectos del stack, asi que se deja en Bandeja Puente para coordinacion y handoff humano.\",\
  \"bridge_next_action\": \"Revisar contrato prometido, confirmar siguiente reunion con diseno instruccional y decidir handoff al sistema humano de proyectos/asesorias.\",\
  \"followup_type\": \"proposal\",\
  \"followup_notes\": \"Usar esta reunion como base para un seguimiento comercial/documental y no como proyecto tecnico del stack.\"\
}"
```

Si el cliente expira antes de terminar, subir el timeout:

```powershell
$env:WORKER_TIMEOUT = "120"
```

## 6. Caso validado en vivo

El 2026-03-27 se valido el slice con la pagina raw:

- `Konstruedu`
- raw page id: `3305f443-fb5c-81db-9162-fd70c8574938`

Resultado:

- se creo el item puente:
  - `Seguimiento oportunidad Konstruedu desde Granola`
  - page id: `3305f443-fb5c-81a2-b59c-c91885f97c91`
- se creo el follow-up tipo propuesta:
  - `Propuesta: Konstruedu`
  - page id: `3305f443-fb5c-8186-8663-c20d3c558b34`
- se dejaron comentarios de trazabilidad entre la pagina raw y el item puente
- tambien se valido la ruta HTTP estandar del repo via `scripts/run_worker_task.py`
  - la segunda corrida actualizo el mismo item puente (`created: false`)
  - con `add_trace_comments=false` para evitar ruido de comentarios

## 6.1 Guardrails de capitalizacion (normativos)

Estas reglas son **normativas** y aplican a cualquier corrida de
`granola.capitalize_raw` (con o sin `allow_legacy_raw_to_canonical`) y a
cualquier skill o agente que decida cerrar una pagina raw Granola.

Referencia viva del contrato: `openclaw/workspace-templates/skills/granola-pipeline/SKILL.md`
(seccion "Guardrails de capitalizacion").

### 6.1.1 Preservacion de trazabilidad de ingest

- El campo `Trazabilidad` de una pagina raw **nunca** puede ser reemplazado
  por completo. La capitalizacion solo puede **anexar** claves.
- Claves de ingest que deben sobrevivir si ya existen:
  `granola_document_id`, `source_updated_at`, `source_url`, `ingest_path`,
  `content_hash`, `char_count`, `segment_count`, `truncation_detected`,
  `ingested_at`, `reconciled_at`.
- La capitalizacion si puede anexar: `capitalization_mode`,
  `canonical_target_type`, `canonical_target_name`, `canonical_target_url`,
  `processed_at`.
- Queda **prohibido** escribir frases tipo `Residuo legacy descartado`
  sobre trazabilidad que contiene claves de ingest. Eso borra la
  reconciliacion que garantiza `docs/78-granola-transcript-finality-reconciliation.md`.

### 6.1.2 Reuniones comerciales / oportunidades

Si la reunion funda o cambia una oportunidad comercial, una **tarea suelta
no cierra la capitalizacion**. El orden correcto es:

1. resolver cliente/partner;
2. resolver o crear proyecto/oportunidad en `Asesorias & Proyectos`, o un
   `bridge item` si no hay DB o permiso disponible;
3. crear tarea vinculada al proyecto o bridge;
4. crear o registrar entregable/propuesta si hay output revisable;
5. dejar comentarios/trazabilidad cruzada entre transcript y objetos
   creados.

Si alguno de los pasos 1-4 no se puede completar, la capitalizacion es
**parcial** o **revision requerida**. En ese caso:

- `Estado` de la pagina raw no puede quedar en `Procesada`;
- `Accion agente` no puede quedar en `Capitalizado`;
- debe dejarse un comentario explicando el bloqueo (falta sharing, falta
  dato del cliente, etc).

### 6.1.3 Tarea suelta vs capitalizacion completa

Una tarea sin proyecto/oportunidad ni bridge item asociado, para una
reunion con identidad comercial clara, cuenta como **capitalizacion
parcial** y no habilita cerrar la pagina raw.

### 6.1.4 Datos ambiguos del transcript

No convertir transcripcion fonetica ambigua en dato firme. Ejemplo real:
`beam beam arroba congress` no puede guardarse como `beam@comgrap` sin
confirmacion humana; debe registrarse como `correo mencionado
foneticamente; confirmar direccion, posiblemente bim@comgrap o
bim@comgrap.cl`.

### 6.1.5 Caso Comgrap Dynamo (test de regresion)

Resultado incorrecto observado sobre la raw `Comgrap Dynamo`:

- solo una tarea suelta
- `Destino canonico = Tarea`, `Estado = Procesada`,
  `Accion agente = Capitalizado`
- `URL artefacto` apuntando a la tarea suelta
- `Trazabilidad` reescrita, con `granola_document_id`, `ingest_path` y
  `source_updated_at` descartados
- Log del agente reconocia que habria que evaluar un proyecto comercial y
  cerro igual como capitalizado

Resultado correcto esperado:

- proyecto / oportunidad o bridge item:
  `COMGRAP — Demo Dynamo / prefabricados de hormigon`
- tarea vinculada:
  `Enviar propuesta/estimacion demo Dynamo a Comgrap`
- entregable/propuesta:
  `Propuesta demo Dynamo/Revit para particion de muros prefabricados +
  diseno generativo`
- la pagina raw queda como `capitalizada` solo si los tres objetos minimos
  estan creados y trazados; si falta alguno, queda como parcial o revision
  requerida
- la trazabilidad de ingest se preserva intacta

## 7. Implicancia arquitectonica

Esto confirma una regla util:

- cuando una reunion raw tiene valor operativo pero no pertenece limpiamente al registry tecnico `Proyectos — Umbral`, el destino correcto dentro de este repo es `Bandeja Puente`

La futura promocion a la capa humana curada ahora ya tiene un slice repo-side separado:

- `granola.promote_curated_session`

Ese contrato no reemplaza este slice puente. Lo complementa.

Ademas, al 2026-03-27 ese contrato sigue bloqueado por acceso:

- la integracion Rick no ve todavia la DB humana curada de sesiones
- tampoco ve la DB humana de tareas
- por eso `granola.capitalize_raw` debe seguir siendo conservadora y operar solo sobre superficies tecnicas o compartidas explicitamente

## 8. Referencias

- `worker/tasks/granola.py`
- `scripts/run_worker_task.py`
- `docs/50-granola-notion-pipeline.md`
- `docs/53-granola-raw-curated-promotion-plan.md`
- `docs/56-granola-promote-curated-session.md`
