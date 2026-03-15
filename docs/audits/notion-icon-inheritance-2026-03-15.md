# Notion Icon Inheritance Validation — 2026-03-15

## Objetivo

Cerrar la deuda visual de Notion en `OpenClaw` y dejar consistente el uso de iconos para:

- `📁 Proyectos — Umbral`
- `🗂 Tareas — Umbral Agent Stack`
- `📬 Entregables Rick — Revisión`
- filas/paginas creadas por `notion.upsert_project`
- filas/paginas creadas por `notion.upsert_task`
- filas/paginas creadas por `notion.upsert_deliverable`
- paginas creadas por `notion.create_report_page`

## Cambios aplicados

### 1. Titulos visuales de databases top-level

Se restauraron los emojis en el titulo de las tres bases visibles en `OpenClaw`:

- `📁 Proyectos — Umbral`
- `🗂 Tareas — Umbral Agent Stack`
- `📬 Entregables Rick — Revisión`

Esto se hizo a nivel de data source en Notion para recuperar la lectura rapida del dashboard.

### 2. Herencia e inferencia de iconos en el Worker

Se endurecio el flujo de iconos en:

- `worker/tasks/notion.py`
- `worker/notion_client.py`

Reglas nuevas:

- `notion.upsert_project`
  - si no recibe `icon`, lo infiere desde el nombre del proyecto
- `notion.upsert_deliverable`
  - si el entregable esta ligado a un proyecto, hereda el icono del proyecto
  - si no, usa icono por tipo o por contenido
- `notion.upsert_task`
  - si la tarea esta ligada a un proyecto, hereda el icono del proyecto
  - si no, infiere por task/team/contenido
- `notion.create_report_page`
  - si no recibe `icon`, intenta heredar desde `metadata.project_name`
  - si no, infiere por titulo/contenido

### 3. Reglas de iconos por contexto

Se dejaron reglas de inferencia para estos casos:

- embudo / linkedin / youtube -> `🎯`
- laboral / postulacion / trabajo -> `💼`
- mejora continua / improvement / auditoria -> `🔄`
- editorial / contenido / newsletter / blog -> `✍️`
- granola / transcript -> `🎙️`
- browser / navegador -> `🌐`
- gui / rpa -> `🖱️`
- vm / windows -> `🖥️`
- freepik / figma -> `🎨`
- docencia / clase -> `🎓`
- ops -> `🛠️`
- system -> `⚙️`
- lab -> `🧪`
- advisory -> `🧠`

### 4. Skills sincronizadas para Rick

Se actualizaron las skills vivas de Rick en la VPS:

- `skills/notion/SKILL.md`
- `skills/notion-project-registry/SKILL.md`

Las reglas nuevas aclaran:

- usar el campo `icon` cuando exista
- heredar el icono del proyecto cuando corresponda
- mantener emoji en el titulo de las bases top-level cuando la API no gobierna bien el icono de database

## Backfill real aplicado

### Proyectos

Se actualizaron iconos reales en las filas de proyectos activos, por ejemplo:

- `🎯 Proyecto Embudo Ventas`
- `🔄 Auditoría Mejora Continua — Umbral Agent Stack`
- `💼 Sistema Automatizado de Búsqueda y Postulación Laboral`
- `✍️ Sistema Editorial Automatizado Umbral`
- `🎙️ Proyecto Granola`

### Entregables

Se actualizaron entregables existentes para que hereden el icono del proyecto cuando aplica, por ejemplo:

- `🎯 Benchmark Ruben Hassid - sistema contenido y funnel`
- `🎯 Framing tipo Veritasium aplicado al embudo`
- `🔄 Auditoria real - Mejora Continua Umbral Agent Stack - 2026-03-10`
- `💼 Shortlist inicial v1 - Sistema Automatizado de Búsqueda y Postulación Laboral`

### Tareas

Se verificaron tareas recientes y se confirmo iconado consistente, por ejemplo:

- `🎯 Governance smoke - task linked to embudo deliverable`
- `🖥️ windows.fs.list`

## Verificacion

### Tests locales

```powershell
python -m pytest tests/test_notion_project_registry.py tests/test_notion_deliverables_registry.py tests/test_notion_tasks_registry.py tests/test_notion_report_page.py -q
```

Resultado:

- `19 passed`

### Validacion de skills

```powershell
python scripts/validate_skills.py
```

Resultado:

- `OK`

### Smoke real por worker (VPS)

Se crearon por el endpoint real `/run` del Worker, sin pasar `icon` explicito:

- entregable:
  - `Smoke inherit project icon deliverable 2026-03-15`
  - resultado: icono real `🎯`
- tarea:
  - `Smoke inherit project icon task 2026-03-15`
  - resultado: icono real `🎯`

Esto valida el camino real que usaria Rick al ejecutar `notion.upsert_deliverable` y `notion.upsert_task`.

## Estado final

- Las tres bases del dashboard volvieron a mostrar emoji en el titulo.
- Las paginas nuevas creadas por el flujo `notion.upsert_*` quedan con icono real consistente.
- La relacion visual `Proyecto -> Tarea -> Entregable` ya puede compartir icono por proyecto.
- Rick ya no depende de meter emoji a mano en el titulo para conseguir lectura rapida.

## Limitacion residual

El icono real de las `database` top-level sigue sin estar gobernado limpiamente por nuestro camino de API. La solucion aplicada y estable es:

- titulo con emoji para la lectura visual
- iconos reales en las filas/paginas internas

Eso deja resuelto el problema practico del dashboard.
