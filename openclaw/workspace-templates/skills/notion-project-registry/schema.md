# Schema and View Guide

## 1) Model the registry around one row per project

Treat each project as one page inside one master data source.
Use page properties for the current operational state.
Use the page body for chronology, secondary links, and handoff context.

Use this modeling split:
- **Notion row** = current truth for cross-tool portfolio tracking.
- **Page body** = update log and operational notes.
- **Linear** = issue-level execution.
- **Drive** = source of truth for files and deliverables.

## 2) Prefer the api-stable property set

Use this property set when operating with low-level Notion tools or raw property payloads.

| Property | Recommended type | Richer UI alternative | Required | Purpose |
|---|---|---|---|---|
| `Proyecto` | `title` | none | yes | Canonical project name. One row per project. |
| `Estado` | `select` | `status` if it already exists and is stable | yes | Canonical state for dashboard and board grouping. |
| `Responsable` | `rich_text` | `people` | yes | Single owner or orchestrator. Prefer text if user-id resolution is unreliable. |
| `Agentes asignados` | `multi_select` | `people` | yes | Agents or copilots working on the project. |
| `Drive` | `url` | none | yes | Canonical shared folder or drive location. |
| `Linear` | `url` | relation to a separate projects db only if already modeled | yes | Canonical Linear project URL. |
| `Links relevantes` | `rich_text` | body section with linked bullets | yes | Short index of key docs, specs, deliverables, and dashboards. |
| `Siguiente hito` | `rich_text` | none | yes | Next milestone or concrete checkpoint. |
| `Bloqueos` | `rich_text` | none | yes | Current blockers with action owner. Leave empty when unblocked. |
| `Fecha inicio` | `date` | none | yes | Project start date. |
| `Fecha objetivo` | `date` | none | yes | Target date or target end date. |
| `Ultimo update` | `date` | none | yes | Date of the latest explicit project update. |
| `Issues abiertas o sin respuesta` | `rich_text` | none | yes | Short list of critical open issues or unanswered questions. |
| `Notas de handoff` | `rich_text` | body section only | yes | Transfer notes, closeout, and context for the next owner. |

## 3) Use these canonical state values

Use these values exactly for `Estado`:
- `activo`
- `bloqueado`
- `en espera`
- `cerrado`

Allow extra values only if there is a real operating need and the team defines them precisely.
Do not create vague states such as `pending`, `moving`, `almost done`, or `parked?`.

## 4) Normalize how to store links

Use this hierarchy:
1. `Drive` = one canonical folder link.
2. `Linear` = one canonical project link.
3. `Links relevantes` = short, newline-delimited index for the most important secondary links.
4. Page body `links operativos` section = fuller list of docs, specs, decks, deliverables, dashboards.

Recommended `Links relevantes` format:
```text
spec — https://...
dashboard — https://...
entregable v1 — https://...
```

## 5) Create these views

### `master`
- layout: table
- scope: all projects
- visible properties:
  - `Proyecto`
  - `Estado`
  - `Responsable`
  - `Agentes asignados`
  - `Drive`
  - `Linear`
  - `Siguiente hito`
  - `Bloqueos`
  - `Fecha inicio`
  - `Fecha objetivo`
  - `Ultimo update`
- sort:
  1. `Estado` ascending or manual group order
  2. `Fecha objetivo` ascending
  3. `Ultimo update` descending

### `seguimiento`
- layout: board
- group by: `Estado`
- group order:
  1. `activo`
  2. `bloqueado`
  3. `en espera`
  4. `cerrado`
- show on cards:
  - `Responsable`
  - `Siguiente hito`
  - `Fecha objetivo`
  - `Ultimo update`

### `roadmap`
- layout: timeline
- plot by:
  - `Fecha inicio` + `Fecha objetivo` as start/end when configured separately, or
  - `Fecha objetivo` when only one date is practical
- default filter: `Estado` is not `cerrado`
- show table: yes
- visible properties:
  - `Responsable`
  - `Estado`
  - `Siguiente hito`

### `atencion`
- layout: table or list
- filter:
  - `Bloqueos` is not empty
  - or `Issues abiertas o sin respuesta` is not empty
- sort:
  1. `Fecha objetivo` ascending
  2. `Ultimo update` ascending

### `backlog` (optional)
Use only when the team really separates intake from active delivery.
Otherwise keep a single active portfolio and do not duplicate views.

## 6) Use this page template

```markdown
# links operativos
- drive:
- linear:
- specs:
- entregables:
- otros:

# updates
## [yyyy-mm-dd]
estado:
hecho desde el ultimo update:
siguiente hito:
bloqueos:
issues sin respuesta:
links o entregables actualizados:
siguiente accion / owner:

# handoff
- contexto vigente:
- riesgos pendientes:
- siguientes pasos:
- owner recomendado:
```

## 7) Apply weekly rules

| Estado | Weekly rule |
|---|---|
| `activo` | Write one update every week. Refresh `Ultimo update`. |
| `bloqueado` | Write one update every week and every time the blocker changes. Keep `Bloqueos` explicit. |
| `en espera` | Write a brief weekly check-in that states whether the pause still stands and what reactivation trigger is expected. |
| `cerrado` | Write a final closeout update and complete `Notas de handoff` if another team or owner may inherit context. |

## 8) Sync with Linear and the shared folder using simple rules

- Use one canonical project name across Notion, Drive, and Linear where possible.
- Update the Notion row whenever one of these changes:
  - project URL in Linear
  - shared folder location
  - primary deliverable link
  - target milestone
  - blocker status
- Summarize only the critical open or unanswered issues from Linear in Notion.
- Do not replicate every issue, comment, or status transition from Linear into Notion.
- When there is no Linear project yet, keep `Linear` empty and record that gap in the latest update.
- When a deliverable moves to a new folder or doc, update the canonical link first, then append the update log entry.

## 9) Operate safely in raw mode

### API version mapping
Use this mapping to stay compatible with older or newer tools:
- **new mode**: `database` = container and `data source` = table-like rows/properties.
- **legacy mode**: `database` holds the rows and properties directly.

Keep the same business schema in either mode.
Do not let API naming changes change the portfolio model.

### Raw-mode rules
- Prefer property ids when available; names may change.
- Prefer property types that are easy to create and update in raw payloads.
- Treat views as UI-managed configuration.
- Treat page body sections as append-only logs, not derived state.
- Update properties first, then append the chronological update block.

## 10) Use these raw payload patterns

### Example property schema snippet
```json
{
  "Proyecto": { "title": {} },
  "Estado": {
    "select": {
      "options": [
        { "name": "activo", "color": "green" },
        { "name": "bloqueado", "color": "red" },
        { "name": "en espera", "color": "yellow" },
        { "name": "cerrado", "color": "gray" }
      ]
    }
  },
  "Responsable": { "rich_text": {} },
  "Agentes asignados": { "multi_select": { "options": [] } },
  "Drive": { "url": {} },
  "Linear": { "url": {} },
  "Links relevantes": { "rich_text": {} },
  "Siguiente hito": { "rich_text": {} },
  "Bloqueos": { "rich_text": {} },
  "Fecha inicio": { "date": {} },
  "Fecha objetivo": { "date": {} },
  "Ultimo update": { "date": {} },
  "Issues abiertas o sin respuesta": { "rich_text": {} },
  "Notas de handoff": { "rich_text": {} }
}
```

### Example page create or update payload
```json
{
  "properties": {
    "Proyecto": {
      "title": [{ "text": { "content": "Lanzamiento dashboard de revenue" } }]
    },
    "Estado": { "select": { "name": "activo" } },
    "Responsable": {
      "rich_text": [{ "text": { "content": "David" } }]
    },
    "Agentes asignados": {
      "multi_select": [{ "name": "research-agent" }, { "name": "ops-agent" }]
    },
    "Drive": { "url": "https://drive.google.com/..." },
    "Linear": { "url": "https://linear.app/..." },
    "Links relevantes": {
      "rich_text": [{ "text": { "content": "spec — https://...\ndashboard — https://..." } }]
    },
    "Siguiente hito": {
      "rich_text": [{ "text": { "content": "revisar mock final con finanzas" } }]
    },
    "Bloqueos": {
      "rich_text": [{ "text": { "content": "esperando definicion de metricas por finanzas" } }]
    },
    "Fecha inicio": { "date": { "start": "2026-03-03" } },
    "Fecha objetivo": { "date": { "start": "2026-03-21" } },
    "Ultimo update": { "date": { "start": "2026-03-09" } },
    "Issues abiertas o sin respuesta": {
      "rich_text": [{ "text": { "content": "LIN-231 — sin respuesta sobre definicion de churn" } }]
    },
    "Notas de handoff": {
      "rich_text": [{ "text": { "content": "vacío hasta cierre o transferencia" } }]
    }
  }
}
```

### Example attention query pattern
```json
{
  "filter": {
    "or": [
      {
        "property": "Bloqueos",
        "rich_text": { "is_not_empty": true }
      },
      {
        "property": "Issues abiertas o sin respuesta",
        "rich_text": { "is_not_empty": true }
      }
    ]
  },
  "sorts": [
    {
      "property": "Fecha objetivo",
      "direction": "ascending"
    },
    {
      "property": "Ultimo update",
      "direction": "ascending"
    }
  ]
}
```

## 11) Detect these anti-patterns

- project page exists, but there is no row in the registry
- multiple rows point to the same project
- `Estado` says `activo` while `Bloqueos` is filled and no next action exists
- `Estado` says `bloqueado` while `Bloqueos` is empty
- `Drive` or `Linear` link is missing even though the project is already underway
- last update lives only in Slack, comments, or Linear and never reaches the registry
- `Ultimo update` is older than the body log or the body log is newer than the properties
- handoff context is in a separate doc with no link from the project row
