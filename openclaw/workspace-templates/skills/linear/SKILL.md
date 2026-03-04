---
name: linear
description: >-
  Manage Linear issues with automatic team routing, labels, and status updates.
  Use when "create issue", "create ticket", "Linear task", "update issue status",
  "list teams", "track task in Linear", "project management".
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

## Notas

- El routing automático infiere el equipo Umbral a partir del título y descripción usando keyword scoring.
- Los labels del equipo se crean automáticamente en Linear si no existen.
- La config de equipos está en `config/teams.yaml`.
- Todas las tasks se encolan vía el Dispatcher a Redis y las ejecuta el Worker.
