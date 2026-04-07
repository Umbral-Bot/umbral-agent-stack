# 53 - Granola raw -> curado -> destino

> LEGACY V1 / SUPERSEDED: este plan describe el puente `raw -> curado -> destino`, hoy retirado del flujo operativo vigente. Mantener solo como referencia historica.

> Plan de implementación para llevar el intake real de Granola al stack de Rick sin mezclar la capa raw con la capa humana curada.

## 1. Objetivo

Implementar un flujo compatible con la realidad operativa actual:

- **hoy**: David copia manualmente notas desde Granola y las capitaliza con Notion AI
- **objetivo**: Rick automatiza el intake raw y luego promueve selectivamente a la capa curada y a los destinos operativos

## 2. Capas

### 2.1 Raw

Owner: Rick  
Superficie: `NOTION_GRANOLA_DB_ID`

Contenido esperado:

- título
- contenido bruto de la reunión
- fecha
- fuente
- attendees si existen
- action items si existen
- timestamps de importación/procesamiento

### 2.2 Curado

Owner: David  
Superficie: DB humana de sesiones/transcripciones

Contenido esperado:

- dominio
- tipo
- programa o proyecto relacionado
- fecha
- URL fuente
- recurso relacionado
- transcripción disponible
- notas

### 2.3 Destino

Superficies:

- proyectos
- tareas
- recursos
- follow-ups

## 3. Componentes a implementar

### 3.1 Exporter de cache

Entrada:

- `%APPDATA%\Granola\cache-v6.json`
- `supabase.json` local de Granola cuando haga falta hidratar desde la API privada

Responsabilidad:

- leer documentos nuevos o modificados
- convertir ProseMirror JSON a Markdown cuando haya notas utilizables
- usar `cache.state.transcripts` como fallback cuando el cache sí tenga segmentos de transcript
- cuando el cache llegue metadata-only, hidratar desde la API privada local:
  - `get-document-panels` para contenido tipo resumen/paneles
  - `get-document-transcript` para segmentos de transcript
- generar `.md` en `GRANOLA_EXPORT_DIR`
- registrar un manifest local para deduplicación mínima por `document_id` + firma de contenido
- reportar explícitamente cuando el cache local solo trae metadata y no contenido utilizable
- marcar en metadata si el contenido vino de cache o de hidratación API

No debe:

- escribir directo en la DB curada
- decidir por sí solo relaciones complejas
- asumir que la API privada de Granola es estable o pública

### 3.2 Watcher existente

Reutilizar `scripts/vm/granola_watcher.py`.

### 3.3 Worker existente

Reutilizar:

- `granola.process_transcript`
- `granola.capitalize_raw`
- `granola.promote_curated_session`
- `granola.create_followup`

## 4. Regla de promoción

Promover de raw a curado solo cuando:

- el dominio sea claro
- exista programa o proyecto identificable
- la reunión tenga valor de trazabilidad
- no sea duplicado obvio

Promover de curado a destino solo cuando:

- haya action items claros
- haya impacto operativo real
- exista una actualización concreta para proyecto, tarea o recurso

### 4.1 Slice ya implementado

Ya existe una pieza intermedia para capitalizacion controlada sin saltar directo a la DB humana curada:

- `granola.capitalize_raw`
- `granola.promote_curated_session`
- `granola.create_human_task_from_curated_session`
- `granola.update_commercial_project_from_curated_session`
- `granola.promote_operational_slice`

`granola.capitalize_raw`:

- parte desde una pagina raw ya creada
- exige destinos explicitos
- hoy solo opera sobre proyecto, entregable, item puente y follow-up
- deja trazabilidad por comentario entre raw y destino

`granola.promote_curated_session`:

- parte desde una pagina raw ya creada
- requiere `NOTION_CURATED_SESSIONS_DB_ID`
- inspecciona el schema vivo de la DB curada antes de escribir
- crea o actualiza por titulo exacto
- solo setea relaciones si se pasan `page_id` explicitos
- deja trazabilidad cruzada entre raw y capa curada

Todavia no resuelve una clasificacion automatica completa `raw -> curado -> destino`.

`granola.create_human_task_from_curated_session`:

- parte desde una sesion curada ya existente
- requiere `NOTION_HUMAN_TASKS_DB_ID`
- exige `task_name` explicito
- crea o actualiza por titulo exacto en la DB humana de tareas
- hereda `Proyecto` desde la sesion curada cuando esa relacion existe
- enlaza `Sesion relacionada`
- deja comentarios de trazabilidad entre sesion curada y tarea humana

Con esto el stack ya dispone de un primer slice explícito `curado -> destino` sin inferir todavía escritura en la DB comercial humana.

`granola.update_commercial_project_from_curated_session`:

- parte desde una sesion curada ya existente
- requiere `NOTION_COMMERCIAL_PROJECTS_DB_ID`
- usa `project_page_id` explicito o la relacion `Proyecto` heredada desde la sesion curada
- solo actualiza campos comerciales soportados por el schema vivo
- deja trazabilidad por comentario entre sesion curada y proyecto comercial

Esto completa un segundo slice explícito `curado -> destino`, separado del flujo de tareas humanas.

`granola.promote_operational_slice`:

- compone `granola.promote_curated_session`
- compone opcionalmente `granola.create_human_task_from_curated_session`
- compone opcionalmente `granola.update_commercial_project_from_curated_session`
- exige payloads explícitos para cada tramo
- no introduce inferencias nuevas

Esto deja disponible una ruta repo-side segura para `raw -> curado -> destino(s)` manteniendo contratos separados.

Para ejecutar varios casos sin payloads manuales repetidos ya existe:

- `scripts/run_granola_operational_batch.py`
- template:
  - `scripts/templates/granola_operational_batch.plan.template.json`

## 5. Lotes sugeridos

### Lote 1

- 3 a 5 reuniones claras
- foco en baja ambigüedad
- validar exporter + watcher + DB raw
- correr primero `python scripts/vm/granola_cache_exporter.py --once --dry-run --limit 5`

### Lote 2

- promoción manual o semi-asistida a la capa curada

### Lote 3

- follow-ups y tareas derivadas

## 6. Riesgos

- asumir que toda nota de Granola es transcripción
- contaminar la DB curada con intake bruto
- crear tareas desde reuniones ambiguas
- perder trazabilidad entre raw y curado
- automatizar antes de tener codec ProseMirror -> Markdown estable
- asumir que `cache-v6.json` siempre trae el contenido final de la nota o transcript
- acoplar el pipeline a endpoints privados sin declarar explícitamente esa fragilidad

## 7. Siguiente paso recomendado

1. usar el exporter ya implementado con hidratación API privada controlada
2. lote piloto raw ya validado en vivo hacia `Transcripciones Granola`
3. `granola.promote_curated_session` ya validada en vivo con `Konstruedu`
4. `granola.create_human_task_from_curated_session` ya validada en vivo con `Konstruedu`
5. `granola.update_commercial_project_from_curated_session` ya validada en vivo con `Konstruedu`
6. `granola.promote_operational_slice` ya validada en vivo como bundle explícito sobre `Konstruedu`
7. mantener la automatización de follow-ups como fase posterior, no en el mismo cambio
8. cualquier automatización futura debe componer estos slices, no saltarse la evidencia intermedia

## 8. Bloqueo actual de acceso

Evidencia observada con la integración Rick del Worker:

- `Transcripciones Granola` visible y operativa.
- `Asesorías & Proyectos` visible por búsqueda y lectura directa.
- `Registro de Sesiones y Transcripciones` visible y operativa después del sharing.
- `Registro de Tareas y Proximas Acciones` visible y operativa después del sharing.

Conclusión operativa:

- el stack ya puede trabajar con raw y con ciertas superficies humanas compartidas.
- el slice de promoción a curado humano ya existe repo-side y ya quedó validado en vivo con una reunión real.
- el primer slice `curado -> destino` hacia la DB humana de tareas también quedó validado en vivo con una reunión real.
- el slice `curado -> destino` hacia la DB comercial humana también quedó validado en vivo con una reunión real.
- la composición explícita `raw -> curado -> destino(s)` también quedó validada en vivo con una reunión real.
- conviene dejar separados los contratos:
  - `NOTION_TASKS_DB_ID` = Kanban técnico
  - `NOTION_PROJECTS_DB_ID` = registry técnico
  - `NOTION_CURATED_SESSIONS_DB_ID` = capa humana curada
  - `NOTION_HUMAN_TASKS_DB_ID` = capa humana de tareas
  - `NOTION_COMMERCIAL_PROJECTS_DB_ID` = capa humana comercial
