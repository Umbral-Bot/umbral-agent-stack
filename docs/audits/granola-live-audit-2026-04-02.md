# Granola Live Audit - 2026-04-02

Generated: 2026-04-02 America/Santiago

## Scope

- Live worker health checked at `http://127.0.0.1:8088/health`: `ok=true`, version `0.4.0`, `39` tasks in memory.
- Live Notion DBs inspected:
  - raw `Transcripciones Granola`
  - curated `Registro de Sesiones y Transcripciones`
  - human tasks `Registro de Tareas y Proximas Acciones`
  - commercial projects `Asesorías & Proyectos`
- Live read-only controls executed:
  - `scripts/list_granola_raw_ingest_gap.py`
  - `scripts/list_granola_promotion_candidates.py`
  - direct cross-DB audit through `worker.notion_client`

## Executive Summary

- Accessible raw rows now: `45`.
- Raw rows already linked to a curated session by canonical raw URL: `44`.
- Raw rows still without curated match: `1`.
- Current planning script classification:
  - `43` promoted
  - `1` smoke_or_test
  - `1` candidate
- Important semantic note: in `scripts/list_granola_promotion_candidates.py`, `promoted` means "raw URL is present in curated `URL fuente`". It does not mean "already capitalized into task/project".
- Raw rows created on `2026-04-02`: `23`.
  - `16` belong to the stronger `granola_document_id` / private API cohort.
  - `7` belong to the weaker `source_sync=granola_shared_folder_sync` cohort.
- Consequences from those `23` raw rows:
  - `20` ended in a curated session created on `2026-04-02`.
  - `2` were attached to curated sessions that already existed.
  - `1` was blocked by ambiguity before curated creation.
- Human-task downstream remains constrained:
  - only `4` raw rows in the accessible corpus have related human tasks.
- Commercial-project downstream remains explicit:
  - only `2` raw rows in the accessible corpus resolve into linked commercial projects.
- No processed raw currently points its `URL artefacto` to an archived curated page.
- Backlog is not empty:
  - gap report still shows `1` recent ambiguous export and `2` historic unique exports still missing from raw.

## Global Control Findings

- Strong traceability now exists for page identity:
  - raw `45/45` expose `ID interno Notion`
  - curated `51/51` expose `ID interno Notion`
  - human tasks expose `ID interno Notion`
- Artifact linkage is clean:
  - processed raw rows missing `URL artefacto`: `0`
  - raw rows whose artifact URL does not match the current curated page URL: `0`
- Route traceability is still incomplete:
  - raw rows that already have a curated match but still do not stamp `promotion_path` in `Trazabilidad`: `42`
  - in those cases, promotion evidence survives through `URL artefacto` and `Log del agente`, but not through a normalized route marker.
- Date traceability is still cohort-dependent:
  - processed raws overall: `44`
  - processed raws missing `Fecha que Rick pasó a Notion`: `27`
  - processed raws missing `Fecha que el agente procesó`: `23`
  - today private API / doc-id cohort: `15/15` complete on both date fields
  - today shared-folder-sync cohort: `7/7` missing both date fields
- Curated source governance is mostly canonical but not fully cleaned:
  - curated pages still using external `notes.granola.ai` as `URL fuente`: `2`
  - one of those is the current blocker for `Revisión final de proyectos de módulo de inteligencia artificial generativa`
  - one is an archived temp validation page

## What Happened On 2026-04-02

### Shared-folder-sync cohort created on 2026-04-02

- `Reunión con N8n`
  - raw created `2026-04-02T00:53:00Z`
  - traceability style: shared folder sync only
  - curated created `2026-04-02T00:59:00Z`
  - downstream: no human task, no project
- `Embudo inteligente: estrategias de adquisición de clientes para empresas B2B`
  - raw created `2026-04-02T00:53:00Z`
  - traceability style: shared folder sync only
  - curated created `2026-04-02T00:59:00Z`
  - downstream: no human task, no project
- `Automatización de flujos de trabajo y documentos en Umbral BIM`
  - raw created `2026-04-02T00:53:00Z`
  - traceability style: shared folder sync only
  - curated created `2026-04-02T00:59:00Z`
  - downstream: no human task, no project
- `Automatización de documentos técnicos para flujo de trabajo en DSO`
  - raw created `2026-04-02T00:53:00Z`
  - traceability style: shared folder sync only
  - curated created `2026-04-02T00:59:00Z`
  - downstream: no human task, no project
- `Asesoría Discurso`
  - raw created `2026-04-02T00:52:00Z`
  - traceability style: shared folder sync only
  - curated created `2026-04-02T01:03:00Z`
  - downstream: no human task, no project
- `Reunión Con Jorge de Boragó`
  - raw created `2026-04-02T00:52:00Z`
  - traceability style: shared folder sync only
  - no new curated page created on this run
  - raw was attached to existing curated session `3305f443-fb5c-81e8-941d-f1c36724b7a6`
  - downstream already existed:
    - human task `Enviar consolidado Boragó`
    - project `Implementación Odoo + Mantenimiento M365 — Boragó`
- `asesoría discurso`
  - raw created `2026-04-02T00:52:00Z`
  - traceability style: shared folder sync only
  - no new curated page created on this run
  - raw was attached to existing curated session `8da03f33-84e0-4db5-9d89-d5efea555ed0`
  - downstream: no human task, no project

### Private API / doc-id cohort created on 2026-04-02

- `Embudo inteligente: estrategias de adquisición de clientes para empresas B2B [2]`
  - raw `2026-04-02T13:34:00Z`
  - curated `2026-04-02T13:40:00Z`
  - downstream: no human task, no project
- `Automatización de documentos técnicos para flujo de trabajo en DSO [2]`
  - raw `2026-04-02T13:34:00Z`
  - curated `2026-04-02T13:40:00Z`
  - downstream: no human task, no project
- `Markdown y herramientas de IA para procesamiento de documentación técnica`
  - raw `2026-04-02T13:34:00Z`
  - curated `2026-04-02T13:40:00Z`
  - downstream: no human task, no project
- `Introducción a Power BI y modelado de datos con David Moreira`
  - raw `2026-04-02T13:34:00Z`
  - curated `2026-04-02T13:40:00Z`
  - downstream: no human task, no project
- `Asesoría discurso [2]`
  - raw `2026-04-02T13:35:00Z`
  - curated `2026-04-02T13:41:00Z`
  - downstream: no human task, no project
- `Planificación de sesiones para máster de inteligencia artificial y estrategia de marketing`
  - raw `2026-04-02T13:37:00Z`
  - curated `2026-04-02T13:43:00Z`
  - downstream: no human task, no project
- `Dalux Field y Power BI: Captura de datos e integración de incidencias BIM`
  - raw `2026-04-02T13:37:00Z`
  - curated `2026-04-02T13:43:00Z`
  - downstream: no human task, no project
- `Automatización de flujos de trabajo y documentos en Umbralbim`
  - raw `2026-04-02T13:39:00Z`
  - curated `2026-04-02T13:45:00Z`
  - downstream: no human task, no project
- `Configuración de plantillas de incidencias en Dalux para gestión BIM en construcción`
  - raw `2026-04-02T13:40:00Z`
  - curated `2026-04-02T13:46:00Z`
  - downstream: no human task, no project
- `Fundamentos de inteligencia artificial generativa para modelado BIM en Revit`
  - raw `2026-04-02T13:40:00Z`
  - curated `2026-04-02T13:46:00Z`
  - downstream: no human task, no project
- `Get started with Granola`
  - raw `2026-04-02T13:40:00Z`
  - curated `2026-04-02T13:47:00Z`
  - downstream: no human task, no project
- `Clase final de máster: Herramientas de IA para escalado, generación de video y audio`
  - raw `2026-04-02T13:40:00Z`
  - curated `2026-04-02T13:47:00Z`
  - downstream: no human task, no project
- `Revisión de índice para guía de bases técnicas y procesos BIM`
  - raw `2026-04-02T13:40:00Z`
  - curated `2026-04-02T13:46:00Z`
  - downstream: no human task, no project
- `Planificación de módulo de construcción con Ricardo para máster de tecnologías 4.0`
  - raw `2026-04-02T13:40:00Z`
  - curated `2026-04-02T13:46:00Z`
  - downstream: no human task, no project
- `Reunión de prueba`
  - raw `2026-04-02T13:15:00Z`
  - curated `2026-04-02T13:21:00Z`
  - downstream created:
    - human task `Revisar resultado nocturno del test E2E Granola 2026-04-02`

### Blocked on 2026-04-02

- `Revisión final de proyectos de módulo de inteligencia artificial generativa`
  - raw created `2026-04-02T13:40:00Z`
  - raw status remained `Pendiente`
  - raw agent status `Revision requerida`
  - raw agent action `Bloqueado por ambiguedad`
  - no curated page was created from this raw
  - blocking evidence:
    - the raw log says search by canonical raw URL returned `0` matches
    - search by exact title + date returned `1` existing curated page
    - that existing curated page is `733fe941-bfbf-4435-8535-b87f9ec8329e`
    - its `URL fuente` is still an external `notes.granola.ai` URL, not the canonical raw Notion URL

## Non-trivial Downstream Cases

- `Konstruedu`
  - raw `3305f443-fb5c-81db-9162-fd70c8574938`
  - curated `3305f443-fb5c-81cd-ba63-c6d06624f6a2`
  - human task `3305f443-fb5c-81a0-8239-fd9ec0600ae3` (`Revisar contrato Konstruedu`)
  - linked commercial project `dcd955f0-28e5-432a-a7ed-9be1ea091a74`
- `Asesoría discurso`
  - raw `3305f443-fb5c-81e6-a1a5-cc0b2ebd1786`
  - curated `3305f443-fb5c-81f5-9911-c9be3fab3c42`
  - human task `3305f443-fb5c-81fc-9cab-cf00eb1030a8` (`Finalizar reordenamiento presentación discurso`)
  - no commercial project relation
- `Reunión Con Jorge de Boragó`
  - raw `3365f443-fb5c-819d-a55a-c79b15120e5e`
  - curated `3305f443-fb5c-81e8-941d-f1c36724b7a6`
  - human task `3305f443-fb5c-81e8-a67d-f4acfefb7b6a` (`Enviar consolidado Boragó`)
  - linked commercial project `b474364f-cfaf-4bf9-af7b-01abd64673aa`
- `Reunión de prueba`
  - raw `3365f443-fb5c-81aa-ae9e-ee5700563aba`
  - curated `0ed92d5f-ef5d-4687-b104-72c0563077be`
  - human task `3365f443-fb5c-814b-b67f-f335bfd8ccb1`
  - no commercial project relation

## Deep Dive: Konstruedu

### Observed Page Family

- Raw `3305f443-fb5c-81db-9162-fd70c8574938`
  - title: `Konstruedu`
  - meeting date: `2026-03-23`
  - created in Notion: `2026-03-27T18:06:00Z`
  - strongest traceability in family:
    - `promotion_path=granola.promote_curated_session`
    - `curated_session_page_id=3305f443-fb5c-81cd-ba63-c6d06624f6a2`
    - `granola_document_id=1d177374-2ff0-42a0-a032-189075f8b4c0`
  - current result:
    - raw `Estado=Procesada`
    - raw `Estado agente=Procesada`
    - raw `URL artefacto` points to the curated session
- Curated `3305f443-fb5c-81cd-ba63-c6d06624f6a2`
  - title: `Konstruedu - propuesta 6 cursos`
  - created in Notion: `2026-03-27T20:52:00Z`
  - current result:
    - `Estado=Procesada`
    - `Dominio=Operacion`
    - `Tipo=Sesión`
    - `URL fuente` points to the canonical raw URL
    - relation to commercial project `dcd955f0-28e5-432a-a7ed-9be1ea091a74`
- Human task `3305f443-fb5c-81a0-8239-fd9ec0600ae3`
  - title: `Revisar contrato Konstruedu`
  - created in Notion: `2026-03-27T21:01:00Z`
  - current result:
    - `Estado=Pendiente`
    - `Origen=Sesion`
    - `Prioridad=Alta`
    - related back to the curated session and the commercial project
- Commercial project `dcd955f0-28e5-432a-a7ed-9be1ea091a74`
  - title: `Especialización IA + Automatización AECO — 6 Cursos Konstruedu`
  - currently observed as:
    - `Estado=Propuesta enviada`
    - `Cliente=Konstruedu`
    - `Monto=3900`
    - `Tipo=Curso`
    - `Acción Requerida=Revisar contrato`

### Additional Konstruedu Pages In The Corpus

- Raw `3345f443-fb5c-8167-979b-f71cca933a60`
  - title: `Konstruedu`
  - meeting date: `2026-03-12`
  - created in Notion: `2026-03-31T13:41:00Z`
  - result:
    - linked to curated `15f113dd-c7b6-4c47-ba18-0bc9b555c873`
    - no human task
    - no commercial project relation
- Raw `3345f443-fb5c-81c6-9d09-d13599a4a736`
  - title: `Konstruedu`
  - meeting date: `2026-04-01`
  - created in Notion: `2026-03-31T13:40:00Z`
  - result:
    - linked to curated `1727da84-cb12-4ca2-99df-038ce3e46480`
    - no human task
    - no commercial project relation

### What Konstruedu Shows About The Current Rules

- The stack is not blindly creating a project for every Konstruedu raw:
  - only the proposal-like session (`2026-03-23`) flows into task + commercial project
  - the other Konstruedu sessions stop at the curated layer
- Human/commercial downstream is therefore not globally automatic:
  - it appears explicit and selective
- Traceability quality within the same family is uneven:
  - the `2026-03-23` raw has `promotion_path`
  - the `2026-03-12` and `2026-04-01` raws do not stamp `promotion_path`, even though they are linked cleanly by `URL artefacto` and curated `URL fuente`
- No deletion or archive was observed inside the Konstruedu family during this audit:
  - evidence shows creates and updates, not removals

## Archive / Cleanup Evidence

- Curated page `3365f443-fb5c-8160-b75c-de1e7aea78ba`
  - title: `Bim Forum Grupo Tecnico — legado incompleto`
  - state: `Archivada`
  - created: `2026-04-02T11:23:00Z`
  - notes explicitly say it was replaced by the canonical session and preserved only as historical trace
- This is the clearest live example in the current corpus of "something was not deleted, but intentionally archived as cleanup".

## Open Risks

- `scripts/list_granola_promotion_candidates.py` currently reports `43` promoted, but that metric is only raw-to-curated linkage. It should not be read as "full capitalization complete".
- `42` curated-linked raws still miss `promotion_path` in raw traceability.
- `7` raw pages created today through shared-folder sync still miss both:
  - `Fecha que Rick pasó a Notion`
  - `Fecha que el agente procesó`
- There is still one live ambiguous raw blocked by a legacy curated page whose `URL fuente` is external instead of canonical.
- Gap report is not closed:
  - `1` recent ambiguous export: `Asesoría Discurso` (`2026-04-01`)
  - `2` historic unique missing raws:
    - `Ejercicio doker Diplomado BIM + IA Butic`
    - `Técnicas de animación con IA para representación arquitectónica`
