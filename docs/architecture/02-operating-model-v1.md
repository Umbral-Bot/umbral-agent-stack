# 02 - Operating Model V1

> Contrato V1 para gobernar el workspace de David Moreira sin reemplazar desde este repo el contenido vivo de Notion.

## 1. Alcance

- Notion es la capa principal de operacion humana.
- Rick coordina el runtime del sistema y solo debe escribir en superficies permitidas.
- Notion AI interpreta y capitaliza dentro del workspace, pero no redefine el canon estructural.
- Este repo define contrato, taxonomias, permisos, placeholders y bindings de runtime.
- Este repo no sustituye contenido live, no inventa IDs y no decide por encima de la fuente canonica humana.

## 2. Principios de diseno

1. Una base canonica por tipo de objeto.
2. El flujo oficial V1 es `raw -> sesion capitalizable -> capitalizacion`.
3. Si hay ambiguedad, no se actualiza; se deja comentario para revision.
4. El error mas grave es duplicar o tocar la fuente canonica equivocada.
5. `raw` es append-only y nunca se usa como objeto operativo final.
6. La interpretacion ocurre en la sesion capitalizable, no sobre la base canonica final.
7. Recursos e investigacion quedan deliberadamente livianos en V1.
8. IDs y `data_source_id` no verificados permanecen como placeholders hasta que Cursor los confirme live.

## 3. Roles operativos

| Actor | Rol | Decide canon | Puede escribir live |
| --- | --- | --- | --- |
| David | owner humano del workspace | Si | Si |
| Rick | coordinador operativo del runtime | No por defecto; ejecuta reglas | Si, solo en superficies y campos permitidos |
| Notion AI | interpretacion dentro del workspace | No por defecto; asiste capitalizacion | Si, con las mismas restricciones del contrato |
| Cursor | implementacion live del contrato V1 | Si, durante setup/migracion supervisada | Si, para crear schema, relaciones, vistas y shares |
| umbral-agent-stack | bridge runtime | No | Solo via handlers ya existentes y surfaces verificadas |

## 4. Modelo canonico V1

| Tipo de objeto | Superficie canonica esperada | Funcion | Politica de escritura | Estado runtime |
| --- | --- | --- | --- | --- |
| `raw_session` | `<RAW_SESSIONS_DB_NAME>` | intake bruto desde Granola u otra fuente | append-only | ligado hoy a `NOTION_GRANOLA_DB_ID` |
| `capitalizable_session` | `<CAPITALIZABLE_SESSIONS_DB_NAME>` | staging de interpretacion y destino | editable mientras este en revision | ligado hoy a `NOTION_CURATED_SESSIONS_DB_ID` |
| `task` | `<HUMAN_TASKS_DB_NAME>` | proximas acciones humanas | crear/actualizar con target verificado | ligado hoy a `NOTION_HUMAN_TASKS_DB_ID` |
| `deliverable` | `<DELIVERABLES_DB_NAME>` | artefactos revisables | Rick libre en artefactos propios; resto por target verificado | ligado hoy a `NOTION_DELIVERABLES_DB_ID` |
| `client_opportunity` | `<CRM_CLIENTS_OPPORTUNITIES_DB_NAME>` | CRM y pipeline comercial | protegido; solo update con target verificado | transicion: hoy el runtime solo conoce `NOTION_COMMERCIAL_PROJECTS_DB_ID` |
| `project` | `<PROJECTS_DB_NAME>` | proyectos canonicos humanos | protegido; crear o editar solo con target verificado | no existe binding humano canonico en runtime V1 |
| `program_course` | `<PROGRAMS_COURSES_DB_NAME>` | programas, cursos, cohortes | protegido; no auto-crear por ambiguedad | sin binding runtime V1 |
| `resource` | `<RESOURCES_DB_NAME>` | biblioteca utilitaria y casos | flexible pero con dedupe por fuente | sin binding runtime V1 |
| `research` | `<RESEARCH_DB_NAME>` | evidencias, hipotesis, insights | flexible pero con trazabilidad a fuente | sin binding runtime V1 |

## 5. Flujo oficial V1

### 5.1 Raw

- Toda captura externa entra a `raw`.
- Campos minimos: `source_system`, `source_external_id`, `source_url`, `captured_at`, `content_hash`, `raw_title`.
- `raw` no actualiza directamente una base canonica humana compartida.
- Si existe una excepcion tecnica, debe quedar trazada y no reemplaza el flujo oficial V1.

### 5.2 Sesion capitalizable

- Existe una sola fila de sesion capitalizable por evento fuente relevante.
- La sesion capitalizable es la unica superficie donde se permite:
  - interpretar el raw
  - clasificar dominio y tipo
  - relacionar candidatos de destino
  - dejar notas de revision
- Estados minimos V1:
  - `Nueva`
  - `En revision`
  - `Lista para capitalizar`
  - `Capitalizada parcial`
  - `Capitalizada`
  - `Bloqueada por ambiguedad`
  - `Descartada`

### 5.3 Capitalizacion

- La capitalizacion crea o actualiza objetos canonicos desde la sesion capitalizable.
- Cada write debe tener:
  - target verificado o permiso explicito de creacion
  - trazabilidad hacia la sesion capitalizable
  - comentario de contexto o comentario de bloqueo
- Si un mismo caso impacta multiples superficies, la sesion capitalizable fan-out a varios objetos; nunca se duplican interpretaciones en varias bases.

## 6. Regla de canon y transicion

- El contrato V1 objetivo es una base canonica por tipo de objeto.
- Si el workspace live todavia mezcla tipos en una sola base, Cursor puede usar una transicion controlada solo para la migracion.
- Esa transicion debe cumplir tres condiciones:
  - vistas tipadas separadas por objeto
  - claves canonicas que eviten colisiones
  - plan explicito para separar la base si el costo de error sigue siendo alto

## 7. Taxonomias minimas V1

- El detalle operativo queda en [registry/taxonomies-v1.yaml](/C:/GitHub/umbral-agent-stack-codex/registry/taxonomies-v1.yaml).
- Las taxonomias son minimas y estables para:
  - sesiones
  - tareas
  - proyectos
  - entregables
  - clientes y oportunidades
  - programas y cursos
  - recursos
  - investigacion
- Recursos e investigacion conservan menor rigidez en V1: menos selects obligatorios, mas foco en fuente y trazabilidad.

## 8. Reglas de implementacion live para Cursor

1. Verificar si la superficie ya existe antes de crear una nueva.
2. Confirmar `database_id` y `data_source_id` reales antes de escribirlos en runtime o en docs operativos.
3. Compartir con Rick solo las superficies que el runtime necesita.
4. No migrar en lote `Mi Perfil`, `OpenClaw`, `Referencias`, `Docencia y Contenido`, dashboards, CRM ni proyectos sensibles sin plan de revision.
5. Crear relaciones y vistas antes de habilitar writes del runtime.
6. Mantener placeholders en este repo hasta que la verificacion live sea explicita.

## 9. Reglas de runtime para umbral-agent-stack

- El hilo stack solo usa handlers y env vars que ya existen.
- Si falta un binding verificado, el fallback seguro es comentario via `notion.add_comment`.
- `granola.promote_curated_session` encaja con la etapa `raw -> sesion capitalizable`.
- `granola.create_human_task_from_curated_session` y `granola.update_commercial_project_from_curated_session` encajan con capitalizacion de superficies ya ligadas.
- `granola.capitalize_raw` queda como slice legado o tecnico; no es la ruta canonica V1 para superficies humanas compartidas.
