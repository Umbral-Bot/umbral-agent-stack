---
name: linear
description: >-
  Manage Linear issues with automatic team routing, labels, and status updates.
  Use when "create issue", "create ticket", "Linear task", "update issue status",
  "list teams", "track task in Linear", "project management", "attach to project",
  or "create Linear project".
metadata:
  openclaw:
    emoji: "\U0001F4CB"
    requires:
      env:
        - LINEAR_API_KEY
---

# Linear Skill

Rick puede gestionar issues en Linear con routing automático de equipos Umbral, labels inteligentes y actualizaciones de estado.

## Requisitos

- `LINEAR_API_KEY`: API key de Linear (Settings → API → Personal API keys).

## Tasks disponibles

### 1. Crear issue

Task: `linear.create_issue`

```json
{
  "title": "Revisar landing page de Marketing",
  "description": "Actualizar copy y CTAs según brief Q2.",
  "team_key": "marketing",
  "priority": 2
}
```

#### Parámetros

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `title` | str | sí | Título del issue |
| `description` | str | no | Descripción detallada |
| `team_key` | str | no | Clave del equipo Umbral (ej. `"marketing"`, `"asesoria"`). Se infiere del título si se omite |
| `team_id` | str | no | UUID del equipo en Linear. Si no se pasa, se resuelve por `team_name` |
| `team_name` | str | no | Nombre del equipo en Linear (default: `"Umbral"`) |
| `priority` | int | no | `0` Sin prioridad, `1` Urgente, `2` Alta, `3` Media, `4` Baja |
| `add_team_labels` | bool | no | Adjuntar labels del equipo (default: `true`) |

#### Respuesta

```json
{
  "ok": true,
  "id": "uuid-123",
  "identifier": "UMB-5",
  "title": "Revisar landing page de Marketing",
  "url": "https://linear.app/umbral/issue/UMB-5",
  "routing": {
    "team_key": "marketing",
    "labels_applied": ["Marketing", "Marketing Supervisor"],
    "supervisor": "Marketing Supervisor",
    "inferred": false,
    "linear_team_id": "uuid-team"
  }
}
```

### 2. Listar equipos

Task: `linear.list_teams`

```json
{}
```

Devuelve la lista de equipos configurados en Linear.

#### Respuesta

```json
{
  "ok": true,
  "teams": [
    {"id": "uuid-team", "name": "Umbral"}
  ]
}
```

### 3. Actualizar estado de issue

Task: `linear.update_issue_status`

```json
{
  "issue_id": "uuid-123",
  "state_name": "Done",
  "comment": "Tarea completada correctamente.",
  "team_id": "uuid-team"
}
```

#### Parámetros

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `issue_id` | str | sí | UUID del issue en Linear |
| `state_name` | str | no | Nombre del workflow state (ej. `"Done"`, `"Cancelled"`, `"In Progress"`) |
| `comment` | str | no | Comentario a agregar al issue |
| `team_id` | str | no | Necesario para resolver `state_name` → `state_id` |

### 4. Listar proyectos

Task: `linear.list_projects`

```json
{
  "query": "Proyecto Embudo",
  "limit": 20
}
```

Devuelve proyectos de Linear filtrables por nombre.

### 5. Crear proyecto

Task: `linear.create_project`

```json
{
  "name": "Proyecto Embudo Ventas",
  "team_name": "Umbral",
  "description": "Proyecto operativo para el embudo de ventas."
}
```

Notas:

- Si `if_exists_return=true` (default), retorna el proyecto existente por nombre en vez de duplicarlo.
- Requiere un `team_id` o un `team_name` resoluble.

### 6. Asociar issue a proyecto

Task: `linear.attach_issue_to_project`

```json
{
  "issue_id": "uuid-del-issue",
  "project_name": "Proyecto Embudo Ventas",
  "create_project_if_missing": true,
  "team_name": "Umbral"
}
```

Notas:

- Permite corregir issues que existan pero hayan quedado fuera del project view.
- Si se usa `project_name` y no existe, puede crear el proyecto automáticamente.

### 7. Listar issues de un proyecto

Task: `linear.list_project_issues`

```json
{
  "project_name": "Proyecto Embudo Ventas",
  "limit": 50
}
```

Devuelve las issues actualmente asociadas a un proyecto.

## Notas

- El routing automático infiere el equipo Umbral a partir del título y descripción usando keyword scoring.
- Los labels del equipo se crean automáticamente en Linear si no existen.
- La config de equipos está en `config/teams.yaml`.
- Todas las tasks se encolan vía el Dispatcher a Redis y las ejecuta el Worker.
- Para proyectos oficiales, no basta con crear la issue: hay que dejarla asociada al project correcto en Linear.
