---
name: linear
description: >-
  Manage issues in Linear with automatic team routing, labels, and status updates.
  Use when "create issue", "linear ticket", "create task in linear",
  "update issue status", "list teams", "project management", "track issue".
metadata:
  openclaw:
    emoji: "\U0001F4CB"
    requires:
      env:
        - LINEAR_API_KEY
---

# Linear Skill

Rick puede gestionar issues en Linear con routing automático de equipos Umbral, labels por equipo y actualizaciones de estado.

## Requisitos

- `LINEAR_API_KEY`: API key de Linear (Settings → API → Personal API keys).

## Tasks disponibles

### 1. Crear issue

Task: `linear.create_issue`

```json
{
  "title": "Diseñar nueva landing page",
  "description": "Crear mockup para la campaña Q2",
  "team_key": "marketing",
  "priority": 2
}
```

Parámetros:

| Parámetro | Tipo | Requerido | Default | Descripción |
|---|---|---|---|---|
| `title` | str | ✅ | — | Título del issue |
| `description` | str | — | — | Descripción del issue |
| `team_key` | str | — | auto-inferido | Clave del equipo Umbral (ej. `"marketing"`, `"advisory"`) |
| `team_id` | str | — | — | UUID del equipo en Linear |
| `team_name` | str | — | `"Umbral"` | Nombre del equipo en Linear |
| `priority` | int | — | — | 0=Sin prioridad, 1=Urgente, 2=Alta, 3=Media, 4=Baja |
| `add_team_labels` | bool | — | `true` | Adjuntar labels del equipo al issue |

Devuelve:

```json
{
  "ok": true,
  "id": "uuid",
  "identifier": "UMB-5",
  "title": "Diseñar nueva landing page",
  "url": "https://linear.app/umbral/issue/UMB-5",
  "routing": {
    "team_key": "marketing",
    "labels_applied": ["Marketing", "Marketing Supervisor"],
    "supervisor": "Marketing Supervisor",
    "inferred": false,
    "linear_team_id": "uuid"
  }
}
```

Si no se pasa `team_key`, se infiere automáticamente del título y descripción usando la configuración de equipos.

### 2. Listar equipos

Task: `linear.list_teams`

```json
{}
```

Devuelve la lista de equipos configurados en Linear con `id` y `name`.

### 3. Actualizar estado de issue

Task: `linear.update_issue_status`

```json
{
  "issue_id": "uuid-del-issue",
  "state_name": "Done",
  "comment": "Tarea completada exitosamente.",
  "team_id": "uuid-del-team"
}
```

Parámetros:

| Parámetro | Tipo | Requerido | Default | Descripción |
|---|---|---|---|---|
| `issue_id` | str | ✅ | — | UUID del issue en Linear |
| `state_name` | str | — | — | Nombre del workflow state (ej. `"Done"`, `"Cancelled"`, `"In Progress"`) |
| `comment` | str | — | — | Comentario a agregar al issue |
| `team_id` | str | — | — | Necesario para resolver `state_name` → `state_id` |

## Notas

- Todas las tasks se encolan vía el Dispatcher a Redis y las ejecuta el Worker.
- El routing de equipos usa `config/teams.yaml` para mapear `team_key` a labels y supervisores.
- Si `team_name` no se encuentra en Linear, se usa el primer equipo disponible.
- `state_name` requiere `team_id` para resolver el ID del workflow state en Linear.
