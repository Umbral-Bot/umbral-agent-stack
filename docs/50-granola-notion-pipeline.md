# Granola -> Notion Pipeline

> LEGACY V1 / SUPERSEDED: este documento conserva contexto historico. El contrato operativo vigente es el flujo V2 directo desde `Transcripciones Granola`; no usar `Registro de Sesiones y Transcripciones` como paso normal.

> Documento de diseño del pipeline de reuniones de Granola para Rick. Este flujo debe convivir con el modo manual actual de David y evolucionar hacia una arquitectura estable `raw -> curado -> destino`.

## 0. Resumen ejecutivo

Hoy coexisten dos modos:

1. **Modo actual manual**
   - David copia manualmente la nota desde Granola.
   - La pega a Notion AI.
   - Si la reunión impacta operación, capitaliza en `Asesorías & Proyectos`.

2. **Modo objetivo con Rick**
   - Rick lee el raw de Granola.
   - Lo guarda en una DB raw exclusiva (`NOTION_GRANOLA_DB_ID`).
   - Solo después promueve lo relevante a la capa curada humana y a los destinos operativos.

La decisión de arquitectura es:

- **Raw**: DB exclusiva de Rick en Notion (`NOTION_GRANOLA_DB_ID`)
- **Curado**: DB humana separada de sesiones/transcripciones clasificadas
- **Destino**: proyectos, tareas, recursos y follow-ups

Rick no debe escribir directamente a la DB curada humana como intake bruto.

## 1. Hallazgos actuales de Granola

### 1.1 Realidad observada en marzo 2026

- El cache observado en Windows fue `%APPDATA%\Granola\cache-v6.json`
- La estructura observada fue `cache.state.documents`
- En la muestra real actual, `cache.state.documents` llega como un `dict` indexado por `document_id`
- Para algunos documentos con transcript, los segmentos viven en `cache.state.transcripts[document_id]`
- Había 41 reuniones en el cache local
- El contenido principal estaba en **ProseMirror JSON**
- `notes_markdown` estaba vacío
- En la muestra real actual, varios `notes` eran `doc -> paragraph` vacíos; por eso el exporter debe usar transcript como fallback cuando exista
- Varias reuniones no tenían transcripción de audio; eran notas de reunión estructuradas
- En un smoke test real del exporter, el cache local actual reportó 36 documentos `metadata_only`; eso significa que `cache-v6.json` no siempre materializa la nota o transcript final aunque la reunión exista
- Se validó una segunda fuente local usable: la API privada autenticada del cliente de Granola
- `get-document-panels` y `get-document-transcript` sí devuelven contenido real si se llaman con el body crudo correcto (`{"document_id": ...}`)
- En un dry-run real con hidratación API, el exporter quedó capaz de preparar 38 de 41 reuniones; solo 3 quedaron fuera por `trashed_or_deleted`

Implicancia:

- Granola no debe modelarse solo como "pipeline de transcript"
- el intake real es **notas o transcripciones**, según disponibilidad
- hace falta un exportador previo a Markdown para reutilizar el watcher actual
- cuando el cache llegue solo con shells metadata-only, el exporter debe intentar hidratar desde la API privada local antes de declarar la reunión inutilizable

### 1.2 Capacidades relevantes

| Característica | Estado |
|---|---|
| Notas de reunión | Sí |
| Transcripción de audio | Parcial / depende del caso |
| Export automático nativo a carpeta | No |
| API pública estable | No |
| Cache local utilizable | Sí |
| API privada local autenticada | Sí, pero frágil |
| Formato raw listo para el watcher actual | Sí, mediante exporter |

## 2. Arquitectura recomendada

### 2.1 Tres capas

#### Capa raw

Owner: Rick  
Superficie: `NOTION_GRANOLA_DB_ID`

Debe almacenar:

- título
- cuerpo bruto de la nota/transcripción
- fecha
- fuente
- attendees si están disponibles
- action items detectados
- timestamps de importación/procesamiento

No necesita relaciones ricas.

#### Capa curada

Owner: David / gobernanza humana  
Superficie: DB humana de sesiones y transcripciones

Debe almacenar solo lo relevante:

- dominio
- tipo de sesión
- programa o proyecto relacionado
- fecha
- URL fuente
- recurso relacionado
- si hay transcripción disponible
- notas de capitalización

Aquí sí convienen relaciones y clasificación.

#### Capa destino

Superficies:

- proyectos
- tareas
- recursos
- follow-ups

Un ítem raw o curado solo debe llegar a destino cuando haya señal suficiente.

## 3. Flujo objetivo

```text
Granola cache-v6.json
    -> hidratación API privada local (cuando el cache venga metadata-only)
    -> granola_cache_exporter.py
    -> archivos .md estructurados
    -> granola_watcher.py
    -> Worker
    -> DB raw de Rick en Notion
    -> promoción selectiva a capa curada
    -> proyectos / tareas / recursos / follow-up
```

## 4. Componentes

### 4.1 Exporter

- lee `cache-v6.json`
- detecta reuniones nuevas o modificadas
- convierte ProseMirror JSON a Markdown cuando haya notas utilizables
- usa `cache.state.transcripts` como fallback cuando existan segmentos de transcript
- cuando el cache local no trae contenido materializado, intenta hidratar:
  - paneles vía `get-document-panels`
  - transcript vía `get-document-transcript`
- marca en metadata si el contenido vino de `cache`, `private_api_panels` o `private_api_transcript`
- exporta `.md` a `GRANOLA_EXPORT_DIR`
- mantiene un manifest local para evitar reexportar el mismo `document_id` con la misma firma de contenido

Este componente es el puente entre la realidad actual de Granola y el watcher ya previsto en el repo.

Nota: esta hidratación usa endpoints privados y credenciales locales del cliente de Granola. Sirve para este entorno, pero debe tratarse como integración frágil, no como API pública contractual.

### 4.2 Watcher existente

`granola_watcher.py` sigue siendo válido si recibe `.md` bien formado.

### 4.3 Worker existente

Las tasks `granola.*` siguen siendo válidas para:

- crear página raw
- extraer action items
- capitalizar explicitamente una pagina raw hacia proyecto, entregable, puente o follow-up
- crear follow-ups
- notificar a Enlace

## 5. Variables de entorno relevantes

| Variable | Dónde | Uso |
|---|---|---|
| `GRANOLA_EXPORT_DIR` | VM | carpeta monitoreada por el watcher |
| `GRANOLA_PROCESSED_DIR` | VM | archivos ya procesados |
| `GRANOLA_ENABLE_PRIVATE_API_HYDRATION` | VM | activa fallback a API privada local (default: on si existe `supabase.json`) |
| `GRANOLA_SUPABASE_PATH` | VM | ruta a `supabase.json` local de Granola |
| `GRANOLA_WORKSPACE_ID` | VM | override opcional del workspace id para headers de API |
| `WORKER_URL` | VM | endpoint local del Worker |
| `WORKER_TOKEN` | VM + Worker | autenticación |
| `NOTION_GRANOLA_DB_ID` | Worker | DB raw de Granola Inbox |
| `NOTION_TASKS_DB_ID` | Worker | opcional; tareas derivadas |
| `NOTION_CURATED_SESSIONS_DB_ID` | Worker | DB humana curada para `granola.promote_curated_session` |
| `NOTION_HUMAN_TASKS_DB_ID` | Worker | DB humana de tareas/proximas acciones |
| `NOTION_COMMERCIAL_PROJECTS_DB_ID` | Worker | DB humana comercial (`Asesorías & Proyectos`) |
| `ENLACE_NOTION_USER_ID` | Worker | opcional; comentarios para Enlace |

## 6. Contrato del raw

### 6.1 Qué va al raw

- contenido bruto de la reunión
- metadata básica
- action items detectados
- señales para follow-up

### 6.2 Qué no va directo al curado

- notas sin clasificar
- reuniones ambiguas
- contenido aún no validado
- action items sin contexto suficiente

## 7. Promoción a curado

Promover a la capa curada cuando:

- la sesión tiene valor de trazabilidad
- el dominio es claro
- el programa o proyecto es identificable
- hay una razón humana para consultarla después

No promover automáticamente todo el raw.

### 7.1 Slices hoy implementados en el stack

Hoy existen dos tasks explicitas y reversibles:

- `granola.capitalize_raw`
- `granola.promote_curated_session`
- `granola.create_human_task_from_curated_session`
- `granola.update_commercial_project_from_curated_session`
- `granola.promote_operational_slice`

`granola.capitalize_raw`:

- parte desde una pagina raw ya existente en `NOTION_GRANOLA_DB_ID`
- lee la pagina real para mantener trazabilidad
- escribe solo en destinos pedidos de forma explicita
- hoy opera solo sobre superficies que el stack ya gobierna:
  - `notion.upsert_project`
  - `notion.upsert_deliverable`
  - `notion.upsert_bridge_item`
  - `granola.create_followup`
- deja comentarios de trazabilidad entre raw y destino cuando se usa con `add_trace_comments=true`

`granola.promote_curated_session`:

- parte desde una pagina raw ya existente en `NOTION_GRANOLA_DB_ID`
- requiere `NOTION_CURATED_SESSIONS_DB_ID`
- inspecciona el schema vivo de la DB curada antes de escribir
- solo llena campos soportados por esa DB
- solo crea relaciones si se pasan `page_id` explicitos
- puede crear o actualizar la sesion curada por titulo exacto

No reemplaza una futura clasificacion mas rica `raw -> curado -> destino`. Es el primer slice conservador para promocion controlada desde Rick.

`granola.create_human_task_from_curated_session`:

- parte desde una sesion curada ya existente
- requiere `NOTION_HUMAN_TASKS_DB_ID`
- inspecciona el schema vivo de la DB humana de tareas antes de escribir
- exige `task_name` explicito
- crea o actualiza la tarea humana por titulo exacto
- hereda la relacion `Proyecto` desde la sesion curada cuando existe
- enlaza `Sesion relacionada`
- deja trazabilidad cruzada entre sesion curada y tarea humana

Con esto el stack ya tiene un primer slice real `curado -> destino` sin tocar todavia la DB comercial humana.

`granola.update_commercial_project_from_curated_session`:

- parte desde una sesion curada ya existente
- requiere `NOTION_COMMERCIAL_PROJECTS_DB_ID`
- usa `project_page_id` explicito o hereda `Proyecto` desde la sesion curada
- solo actualiza campos comerciales realmente soportados por el schema vivo
- hoy el contrato cubre:
  - `Estado`
  - `Acción Requerida`
  - `Fecha`
  - `Plazo`
  - `Monto`
  - `Tipo`
  - `Cliente`
- deja trazabilidad por comentario entre sesion curada y proyecto comercial

Con esto el stack ya puede recorrer `raw -> curado -> tarea humana` y `raw -> curado -> proyecto comercial`, siempre por payload explicito.

`granola.promote_operational_slice`:

- parte desde una pagina raw ya existente
- exige un `curated_payload`
- exige al menos un destino explicito:
  - `human_task_payload`
  - `commercial_project_payload`
- encadena los handlers conservadores ya validados
- no agrega inferencias nuevas; solo pasa payloads explicitos

Con esto el stack ya tiene una orquestacion segura para:

`raw -> curado -> destino(s)`

Además soporta `dry_run=true` para previsualizar el payload real de cada tramo antes de escribir en Notion.

Repo-side también existe un runner batch explícito:

- `scripts/run_granola_operational_batch.py`
- template:
  - `scripts/templates/granola_operational_batch.plan.template.json`

## 8. Compatibilidad con el modo manual actual

Mientras el pipeline automático no exista, el modo manual sigue siendo válido:

1. David copia desde Granola
2. pega a Notion AI
3. capitaliza en proyectos o sesiones según corresponda

El pipeline de Rick no reemplaza ese flujo de un día para otro. Debe coexistir con él.

## 9. Recomendaciones de implementación

1. Mantener `NOTION_GRANOLA_DB_ID` como DB raw canónica de Rick.
2. No reutilizar la DB curada humana como intake bruto.
3. Implementar primero el exporter de `cache-v6.json`.
4. Mantener el watcher actual.
5. Configurar después la promoción explícita `raw -> curado -> destino` sobre el slice ya implementado.

### 9.1 Validación mínima del exporter

Comando recomendado para un lote pequeño:

```powershell
python scripts/vm/granola_cache_exporter.py --once --dry-run --limit 5
```

Comportamiento esperado:

- exporta solo reuniones con contenido utilizable
- escribe `.md` compatibles con `granola_watcher.py`
- deja trazabilidad local en `.granola-cache-export-manifest.json`
- si el cache está metadata-only, intenta hidratar desde la API privada local antes de descartar
- en el entorno real validado el dry-run completo quedó en `exported=38`, `skipped_unusable=3`, `skipped_reason_counts={'trashed_or_deleted': 3}`

### 9.2 Piloto E2E validado

Validación real ejecutada el 2026-03-27:

- Worker local levantado en `127.0.0.1:8088`
- exporter ejecutado con hidratación API privada local
- watcher procesó un lote piloto de 3 reuniones reales
- las 3 páginas quedaron creadas en `NOTION_GRANOLA_DB_ID`

Páginas verificadas:

- `Reunión Con Jorge de Boragó` — fecha `2026-03-24`
- `Asesoría discurso` — fecha `2026-03-23`
- `Konstruedu` — fecha `2026-03-23`

Conclusión:

- el tramo `Granola -> exporter -> watcher -> Worker -> Transcripciones Granola` ya quedó validado en vivo
- el siguiente frente ya no es el intake raw, sino la promoción controlada `raw -> curado -> destino`

### 9.3 Frontera de acceso observada el 2026-03-27

Con la integracion Rick cargada en el Worker:

- `Transcripciones Granola` responde y ya esta validada como raw.
- `Asesorías & Proyectos` tambien responde por busqueda y por `retrieve database`.
- `Registro de Sesiones y Transcripciones`, `Registro de Tareas y Proximas Acciones`, `Programas y Cursos` y `Recursos y Casos` no aparecen en `search`.
- intentos de `retrieve database` sobre IDs candidatos de las superficies humanas devolvieron `404 object_not_found` con el mensaje de compartir la base con la integracion `Rick`.

Implicancia:

- el bloqueo de permisos ya quedó resuelto para `Registro de Sesiones y Transcripciones`, `Registro de Tareas y Proximas Acciones` y `Asesorías & Proyectos`.
- `granola.promote_curated_session` ya puede ejecutarse live porque `NOTION_CURATED_SESSIONS_DB_ID` quedó compartido con Rick.
- la separación de contratos sigue vigente: `NOTION_TASKS_DB_ID` no reemplaza la DB humana de tareas.
- el siguiente frente ya no es reachability, sino el primer piloto live `raw -> curado`.

### 9.4 Piloto live `raw -> curado` validado

Validación ejecutada el 2026-03-27:

- raw page: `Konstruedu`
- raw page id: `3305f443-fb5c-81db-9162-fd70c8574938`
- sesión curada creada:
  - `Konstruedu - propuesta 6 cursos`
  - page id: `3305f443-fb5c-81cd-ba63-c6d06624f6a2`
- proyecto humano relacionado:
  - `Especialización IA + Automatización AECO — 6 Cursos Konstruedu`
  - page id: `dcd955f0-28e5-432a-a7ed-9be1ea091a74`

Resultado:

- `granola.promote_curated_session` ya quedó validada en vivo
- la relación `Proyecto` también quedó validada en vivo
- el siguiente frente técnico ya pasa a ser el primer slice `curado -> destino`

### 9.5 Piloto live `curado -> destino` validado

Validación ejecutada el 2026-03-27:

- sesion curada origen:
  - `Konstruedu - propuesta 6 cursos`
  - page id: `3305f443-fb5c-81cd-ba63-c6d06624f6a2`
- tarea humana creada:
  - `Revisar contrato Konstruedu`
  - page id: `3305f443-fb5c-81a0-8239-fd9ec0600ae3`

Propiedades verificadas en `Registro de Tareas y Proximas Acciones`:

- `Dominio = Operacion`
- `Proyecto` relacionado al proyecto humano de Konstruedu
- `Sesion relacionada` enlazada a la sesion curada
- `Tipo = Follow-up`
- `Estado = Pendiente`
- `Prioridad = Alta`
- `Origen = Sesion`
- `URL fuente` apuntando a la sesion curada

Conclusión operativa:

- `granola.create_human_task_from_curated_session` ya quedó validada en vivo
- el stack ya puede recorrer `raw -> curado -> tarea humana`
- el siguiente frente, si se desea, es un slice explícito para actualizar la DB comercial humana sin heurísticas

### 9.6 Piloto live `curado -> proyecto comercial` validado

Validación ejecutada el 2026-03-27:

- sesion curada origen:
  - `Konstruedu - propuesta 6 cursos`
  - page id: `3305f443-fb5c-81cd-ba63-c6d06624f6a2`
- proyecto comercial actualizado:
  - `Especialización IA + Automatización AECO — 6 Cursos Konstruedu`
  - page id: `dcd955f0-28e5-432a-a7ed-9be1ea091a74`

Payload explícito usado:

- `Estado = Propuesta enviada`
- `Acción Requerida = Revisar contrato`

Propiedades verificadas en `Asesorías & Proyectos`:

- `Estado = Propuesta enviada`
- `Acción Requerida = Revisar contrato`

Trazabilidad verificada:

- comentario en la sesion curada apuntando al proyecto comercial
- comentario en el proyecto comercial apuntando a la sesion curada

Conclusión operativa:

- `granola.update_commercial_project_from_curated_session` ya quedó validada en vivo
- el stack ya puede recorrer `raw -> curado -> proyecto comercial`
- los cambios comerciales deben seguir siendo explícitos; no conviene inferirlos desde texto libre

### 9.7 Bundle live `raw -> curado -> destino(s)` validado

Validación ejecutada el 2026-03-27 con `Konstruedu`:

- raw page:
  - `Konstruedu`
  - page id: `3305f443-fb5c-81db-9162-fd70c8574938`
- sesion curada existente:
  - `Konstruedu - propuesta 6 cursos`
  - page id: `3305f443-fb5c-81cd-ba63-c6d06624f6a2`
- tarea humana existente:
  - `Revisar contrato Konstruedu`
  - page id: `3305f443-fb5c-81a0-8239-fd9ec0600ae3`
- proyecto comercial existente:
  - `Especialización IA + Automatización AECO — 6 Cursos Konstruedu`
  - page id: `dcd955f0-28e5-432a-a7ed-9be1ea091a74`

Resultado:

- `granola.promote_operational_slice` resolvió los tres pasos en una sola ejecución
- `curated_session` quedó `matched_existing = true`
- `human_task` quedó `matched_existing = true`
- `commercial_project` quedó actualizado por `page_id`
- la corrida se hizo con `add_trace_comments = false` en subpayloads para evitar duplicar trazabilidad

Conclusión operativa:

- el stack ya tiene una ruta compuesta y segura para `raw -> curado -> destino(s)`
- cualquier automatización futura debería usar este patrón de composición explícita, no una clasificación opaca

## 10. Referencias

- `worker/notion_client.py`
- `worker/tasks/granola.py`
- `docs/56-granola-promote-curated-session.md`
- `docs/57-granola-human-task-from-curated-session.md`
- `docs/58-granola-commercial-project-from-curated-session.md`
- `docs/59-granola-promote-operational-slice.md`
- `scripts/vm/granola_watcher.py`
- `docs/18-notion-enlace-rick-convention.md`
- `openclaw/workspace-templates/skills/granola-pipeline/SKILL.md`
