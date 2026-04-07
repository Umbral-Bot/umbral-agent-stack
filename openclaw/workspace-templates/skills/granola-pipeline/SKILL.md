---
name: granola-pipeline
description: >-
  Process Granola meeting notes or transcripts into the active raw Notion
  surface, classify them in-place, capitalize directly to supported V2 targets,
  and leave review in raw when the destination is ambiguous or read-only. Use
  when "subir transcripcion", "procesar granola", "reunion terminada",
  "compromisos reunion", or "propuesta de seguimiento".
metadata:
  openclaw:
    emoji: "\U0001F399"
    requires:
      env:
        - NOTION_API_KEY
        - NOTION_GRANOLA_DB_ID
---

# Granola Pipeline Skill

Rick puede procesar notas o transcripciones de Granola y trabajar directamente sobre la superficie raw activa en Notion.

## Estado vigente

- El flujo vigente es V2 directo: `raw -> raw_review_or_direct_capitalization -> capitalization | review_required_in_raw`.
- La superficie activa es `Transcripciones Granola`.
- `Registro de Sesiones y Transcripciones` es solo residuo legacy V1; no es paso operativo normal ni artefacto final valido en este flujo.

## Regla principal

Trabajar siempre primero sobre `raw`.

No asumir que:

- toda reunion debe capitalizarse con exito
- `Programa` o `Recurso` son destinos escribibles desde raw
- `curated` o `session_capitalizable` siguen siendo el puente vigente
- un request con varios destinos explicitos debe ejecutarse sin revision

## Superficies activas

1. **Raw**: `NOTION_GRANOLA_DB_ID` -> `Transcripciones Granola`
2. **Targets directos soportados desde raw**:
   - `NOTION_HUMAN_TASKS_DB_ID` -> `Registro de Tareas y Proximas Acciones`
   - `NOTION_COMMERCIAL_PROJECTS_DB_ID` -> `Asesorias y Proyectos`
   - `NOTION_DELIVERABLES_DB_ID` -> `Entregables`
3. **Targets de solo lectura / clasificacion en este flujo**:
   - `Programas y Cursos`
   - `Recursos y Casos`

## Contrato raw que importa

En `Transcripciones Granola`, el runtime debe dejar como minimo:

- `Estado`
- `Estado agente`
- `Accion agente`
- `Dominio propuesto`
- `Tipo propuesto`
- `Destino canonico`
- `Resumen agente`
- `Log del agente`
- `URL artefacto`
- `Trazabilidad`
- campos de review cuando corresponda

Notas clave:

- `URL artefacto` debe apuntar solo al objeto canonico final.
- `Trazabilidad` debe quedar como bloque limpio `clave=valor`.
- Si el target clasificado es `Programa` o `Recurso`, no hay capitalizacion exitosa: la fila debe quedar en raw con review requerida.

## Requisitos

- `NOTION_API_KEY`: token de integracion Notion Rick.
- `NOTION_GRANOLA_DB_ID`: ID de la DB raw activa.
- `NOTION_HUMAN_TASKS_DB_ID` (recomendado): superficie humana activa de tareas.
- `NOTION_COMMERCIAL_PROJECTS_DB_ID` (recomendado): superficie comercial activa.
- `NOTION_DELIVERABLES_DB_ID` (opcional segun uso): superficie activa de entregables.
- `NOTION_CURATED_SESSIONS_DB_ID` es legacy-only; no asumirlo para el flujo actual.

## Tasks disponibles

### 1. Procesar intake raw

Task: `granola.process_transcript`

Pipeline raw:

1. crea pagina raw en Notion
2. extrae action items
3. notifica a Enlace

### 2. Evaluar capitalizacion directa desde raw

Task: `granola.capitalize_raw`

Usar esta task cuando:

- la pagina raw ya existe
- el destino canonico soportado es claro
- quieres escribir directo a tarea, proyecto o entregable

Comportamiento esperado:

- escribe directo al target soportado cuando hay un unico destino valido
- actualiza el contrato raw V2 completo
- deja review en raw cuando el destino es ambiguo o read-only
- ignora el viejo gate `allow_legacy_raw_to_canonical` como requisito normal

### 3. Crear follow-up

Task: `granola.create_followup`

Sigue disponible para follow-ups proactivos, pero no reemplaza la capitalizacion canonica del flujo V2.

## Tasks legacy

Estas tasks existen solo para residuo V1 o validacion defensiva:

- `granola.promote_curated_session`
- `granola.create_human_task_from_curated_session`
- `granola.update_commercial_project_from_curated_session`
- `granola.promote_operational_slice`

Usarlas solo cuando:

- estas tratando con historico V1
- necesitas validar o mantener un artefacto legacy
- el contrato vigente no se puede cumplir con el flujo directo

No usarlas como camino normal para sesiones nuevas.

## Procedimientos

### Pipeline automatico

1. Granola deja la reunion en cache local
2. un exporter o copy/paste genera `.md` en `GRANOLA_EXPORT_DIR`
3. `granola_watcher.py` detecta el archivo y llama al Worker
4. Worker crea pagina raw y deja lista la fila para revision o capitalizacion directa

### Pipeline manual

1. David copia la nota o transcript desde Granola
2. Rick o una herramienta intermedia la guarda como `.md`
3. el Worker procesa ese material en la capa raw activa

## Referencias

- `docs/50-granola-notion-pipeline.md`
- `docs/54-granola-capitalize-raw-slice.md`
- `worker/notion_client.py`
- `worker/tasks/granola.py`
- `scripts/vm/granola_watcher.py`

Los docs `50`, `53`, `54`, `56`, `57`, `58`, `59` y `60` pueden seguir existiendo como historico, pero no deben leerse como contrato operativo vigente si contradicen el flujo V2 directo.
