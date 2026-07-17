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
  - `notion.upsert_deliverable` (Bandeja de revision - Rick; solo para outputs internos de agentes, no propuestas comerciales)
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
  `ingested_at`, `reconciled_at`, `shared_folder_path`, `sha1`.
- La capitalizacion si puede anexar: `source`, `capitalization_mode`,
  `canonical_target_type`, `canonical_target_name`, `processed_at`.
- **`canonical_target_url` NO pertenece a `Trazabilidad` bajo ninguna
  circunstancia.** Corrige una inconsistencia previa de este documento: el
  prompt V2.1.1 del agente Notion (`notion-governance/prompts/agents/review-capitalizacion-v2.1.md`)
  prohibe explicitamente escribir URLs, mentions o links en cualquier valor de
  `Trazabilidad` porque Notion los convierte automaticamente en
  `<mention-page>` y rompe el formato `clave=valor`. La URL del canonico final
  vive **exclusivamente** en la propiedad `URL artefacto` (tipo `url`) de la
  pagina raw. Ningun handler ni skill debe emitir `canonical_target_url=` en
  `Trazabilidad`.
- Queda **prohibido** escribir frases tipo `Residuo legacy descartado`
  sobre trazabilidad que contiene claves de ingest. Eso borra la
  reconciliacion que garantiza `docs/78-granola-transcript-finality-reconciliation.md`.
- Helper determinista de referencia (P0, sin Notion, sin LLM):
  `worker/tasks/granola_capitalization.append_capitalization_traceability()`
  preserva las lineas de ingest existentes byte a byte y reconcilia
  (no duplica) el bloque de capitalizacion en reintentos. Ver
  `docs/plans/granola-capitalization-hybrid-plan-2026-07-16.md` (paquete P0).

### 6.1.1-bis Verify-after-write es bloqueante

Ninguna corrida futura de capitalizacion raw -> Tarea puede declarar exito a
partir de la respuesta de un `update_page_properties`/`create_database_page`.
El unico criterio valido es una **relectura real** posterior: releer la
pagina raw y la tarea creada/actualizada y comparar campo a campo (titulo,
`URL artefacto` == URL real de la tarea, `Destino canonico`, `Estado`,
`Estado agente`, `Accion agente`, `Procesar con agente`, propiedades V2
obligatorias, lineas de ingest de `Trazabilidad` intactas y en orden,
relaciones si fueron proporcionadas). Si la relectura no confirma cada punto,
no se declara `Capitalizado`; se repara y se relee, o se cierra como `Error`/
`Revision requerida`. Esto traduce a codigo la regla del prompt V2.1
"Prohibicion de declaracion falsa de exito", tras el patron "log miente"
observado en el piloto Notion (Haiku 4.5, 3/5 items). Helper determinista de
referencia (P0): `worker/tasks/granola_capitalization.verify_task_capitalization()`.

### 6.1.2 Reuniones comerciales / oportunidades (project-first)

Si la reunion funda o cambia una oportunidad comercial, una **tarea suelta
no cierra la capitalizacion**. La salida canonica es la **pagina del
proyecto**. El orden correcto es:

1. resolver cliente/partner;
2. resolver o crear proyecto/oportunidad en `Asesorias & Proyectos`, o un
   `bridge item` si no hay DB o permiso disponible;
3. si hay output revisable (propuesta, estimacion, demo, briefing), crearlo
   como **seccion o subpagina dentro del proyecto** — no como entregable
   separado en otra DB;
4. opcionalmente crear tarea operativa (seguimiento) vinculada al proyecto
   o bridge;
5. dejar comentarios/trazabilidad cruzada entre transcript y objetos
   creados.

**No usar** la DB humana "📦 Entregables" (eliminada por David, ID
`462adf65`) ni la "Bandeja de revision - Rick" (`NOTION_DELIVERABLES_DB_ID`)
para propuestas comerciales Granola. La Bandeja de revision queda reservada
para outputs internos de agentes.

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

Resultado correcto esperado (project-first):

- proyecto canonico:
  `COMGRAP — Demo Dynamo / prefabricados de hormigon`
  (pagina: `3485f443-fb5c-8198-9f54-fc5882302bf2`)
- subpagina propuesta dentro del proyecto:
  `Propuesta demo Dynamo/Revit para particion de muros prefabricados +
  diseno generativo`
  (pagina: `2de7b1e7-45c3-49b3-aec2-ea29ffd262d8`)
- tarea operativa vinculada:
  `Enviar propuesta/estimacion demo Dynamo a Comgrap`
  (pagina: `df938460-fdee-4752-b9d4-293bede5e541`)
- nada en "📦 Entregables" (DB eliminada) ni en "Bandeja de revision - Rick"
- la pagina raw queda como `capitalizada` solo si el proyecto y la
  subpagina propuesta estan creados y trazados; si falta alguno, queda como
  parcial o revision requerida
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

> Nota 2026-07-16: la parte de acceso quedo obsoleta — la integracion Rick ya
> LEE la DB humana de tareas (`NOTION_HUMAN_TASKS_DB_ID`, verificado read-only
> en VPS; ver plan hibrido §1.2). El camino V2 raw -> Tarea es el del §7.1; la
> capa curada V1 sigue retirada.

## 7.1 Task determinista V2: `granola.capitalize_task_from_raw` (P1)

> Estado: **implementado en codigo, NO desplegado** (2026-07-17). Primer write
> live requiere un gate explicito de David (plan hibrido, paquete P1 fase
> piloto). El poller sigue pausado (`CAP_POLLER_PAUSED`) y no invoca esta task.

Motor B del plan hibrido (`docs/plans/granola-capitalization-hybrid-plan-2026-07-16.md`):
capitalizacion determinista raw -> Tarea, 0 LLM, con verify-after-write
bloqueante. Handler: `worker/tasks/granola_task_capitalize.py`.

### Contrato

- **`dry_run=true` por defecto.** Sin `dry_run=false` explicito la task solo
  lee y devuelve el plan exacto (accion propuesta create/update/review/error,
  propiedades exactas a escribir, dedup observado, cierre planificado del raw,
  preview de Trazabilidad). Un dry-run nunca declara capitalizacion.
- **Binding humano exclusivo.** Escribe solo en `NOTION_HUMAN_TASKS_DB_ID`
  (Registro de Tareas y Proximas Acciones). `NOTION_TASKS_DB_ID` (DB operativa
  del stack, distinta) esta prohibido en este flujo; si falta el binding
  humano la task falla cerrada sin ningun write.
- **Preflight fail-closed** (cualquier fallo = sin writes): el raw existe y
  pertenece a `Transcripciones Granola`; `Destino canonico=Tarea`;
  `Procesar con agente=true`; evidencia suficiente en el cuerpo;
  `Trazabilidad` valida segun el contrato P0 (formato `clave=valor` limpio).
- **Dedup seguro por titulo exacto:** 0 matches -> create; 1 match -> update
  **solo** si el caller pasa `expected_task_page_id` igual al match (prohibido
  actualizar por inferencia); 2+ matches -> Revision requerida. Nunca hay
  matching semantico.
- **Confirmacion anti-Comgrap:** si el raw trae senales comerciales
  estructuradas (`Cliente/Partner relacionado` presente + `Tipo propuesto`
  Reunion/Llamada + senal de proyecto en `Proyecto`/`Proyecto relacionado`),
  convertirlo en Tarea exige el input explicito `human_confirmed_task=true`;
  sin el, la salida es Revision requerida (`Duda de clasificación`). No se
  analizan keywords del transcript ni se reclasifica con LLM.
- **Relaciones solo propagadas:** la relacion `Proyecto` de la tarea sale de
  `Proyecto relacionado` del raw o de un `project_page_id` explicito. Nunca
  se infiere ni se hace matching CRM.
- **Verify-after-write obligatorio y bloqueante** (G1-bis): tras escribir, la
  task relee la tarea y el raw y verifica con
  `granola_capitalization.verify_task_capitalization()`. Exito solo con
  `verification.ok=true`. Si la verificacion falla: no se declara exito, el
  raw queda en `Revision requerida` + `Motivo revisión=Bloqueo técnico` +
  `Procesar con agente=false`, y el resultado lista los mismatches observados
  (no lo intentado).
- **Cierre de exito del raw:** `Estado=Procesada`, `Estado agente=Procesada`,
  `Accion agente=Capitalizado`, `Procesar con agente=false`,
  `Estado revisión=No aplica`, `URL artefacto` = URL real (releida) de la
  tarea, Trazabilidad = ingest intacto + bloque de capitalizacion anexado via
  P0 (`capitalization_mode=worker_task_from_raw_v1`, sin URL).
- Las salidas de revision pre-write **no escriben nada** (ni siquiera el
  estado de revision): devuelven el cierre propuesto en `planned_raw_close`
  para que un humano/orquestador lo aplique. El unico write en ruta de fallo
  es el cierre tecnico post-write cuando la verificacion falla.

## 8. Referencias

- `worker/tasks/granola.py`
- `worker/tasks/granola_task_capitalize.py` (P1 — `granola.capitalize_task_from_raw`)
- `worker/tasks/granola_capitalization.py` (P0 — helpers append/verify)
- `scripts/run_worker_task.py`
- `docs/plans/granola-capitalization-hybrid-plan-2026-07-16.md`
- `docs/50-granola-notion-pipeline.md`
- `docs/53-granola-raw-curated-promotion-plan.md`
- `docs/56-granola-promote-curated-session.md`
