---
id: "2026-03-09-004"
title: "Claude: gobernanza de proyectos Rick con Linear project + registro Notion"
status: done
assigned_to: claude-code
created_by: codex
priority: high
sprint: R21
created_at: 2026-03-09T10:23:47-03:00
updated_at: 2026-03-09T10:23:47-03:00
---

## Objetivo

Implementar y/o dejar cerrada la gobernanza de proyectos reales de Rick para que, cuando David declare un proyecto, exista un lugar único y visible para seguir:

- el proyecto específico en Linear
- la carpeta compartida de Drive/VM
- el registro base del proyecto en Notion
- sus updates
- sus issues
- sus responsables
- sus tiempos/estados
- y los handoffs entre agentes/subagentes

La meta es dejar de depender de issues sueltas o archivos dispersos para entender el progreso de un proyecto.

## Contexto

Problema visible hoy:

- David no ve las issues de `Proyecto Embudo Ventas` en el overview del project de Linear.
- El detalle real del trabajo quedó principalmente en `G:\Mi unidad\Rick-David\Proyecto-Embudo-Ventas\...`.
- Rick sí crea/comenta issues (`UMB-27` a `UMB-33`), pero no hay evidencia de asociación explícita al Linear project correcto.
- Notion se usó como fuente/contexto, no como tablero operativo visible de seguimiento del proyecto.

Diagnóstico técnico confirmado en este repo:

- `worker/tasks/linear.py` hoy solo expone:
  - `linear.create_issue`
  - `linear.list_teams`
  - `linear.update_issue_status`
- `worker/linear_client.py` hoy no implementa operaciones de project:
  - crear/buscar project
  - asociar issue a project
  - listar issues por project
- `worker/tasks/notion.py` sí tiene lectura/escritura útil, pero no un handler específico para:
  - registro maestro de proyectos
  - sync de proyecto ↔ Linear ↔ Drive
  - panel de seguimiento con vistas tipo Kanban/Trello

Requisitos pedidos por David:

- si se está trabajando en **un proyecto**, las issues deben ir al **project específico de Linear**
- si el proyecto no existe en Linear, debe crearse
- el proyecto debe quedar anotado tanto en:
  - la carpeta compartida/Drive
  - el registro de Notion
- en Notion debe existir una capa base de seguimiento para ver proyectos, status e información básica:
  - nombre del proyecto
  - estado
  - carpeta compartida / GDrive
  - project en Linear
  - si tiene issues sin responder en Linear
  - updates
  - issues
  - responsables / designados
  - tiempos
- los proyectos deben tener separación clara entre:
  - **Updates**
  - **Issues**
- debe existir una vista tipo Kanban/Trello para seguimiento
- un agente debe poder abrir un issue/bloqueo para otro agente experto, y ese segundo agente debe:
  - tomar el caso
  - resolverlo
  - dejar registro
  - responder al agente original

Referencia de Notion señalada por David:

- `https://www.notion.so/umbralbim/85f89758684744fb9f14076e7ba0930e?v=66e505e1e5b94923aa9fafdf4a277dc1&source=copy_link`

## Enfoque pedido a Claude

Se necesita que Claude tome este problema desde el ángulo de diseño e implementación de gobernanza operativa, idealmente cubriendo:

1. **Linear project awareness**
   - cómo garantizar que Rick cree/use el project correcto
   - cómo asociar nuevas issues al project correcto
   - qué hacer si el project aún no existe
   - cómo distinguir `project updates` de `project issues`

2. **Registro maestro de proyectos en Notion**
   - reutilizar la DB/página ya existente si corresponde
   - o diagnosticar por qué no sirve y proponer/implementar la alternativa correcta
   - definir esquema mínimo y vistas útiles

3. **Visibilidad operativa**
   - una vista clara tipo Kanban/Trello
   - una ficha por proyecto con links a:
     - Linear project
     - carpeta compartida
     - artefactos principales
     - últimos updates
     - issues abiertas

4. **Subagentes y handoffs**
   - modelar cómo un agente deja un issue/tarea a otro agente
   - cómo queda registrado el owner original, el designado y la respuesta
   - cómo evitar que eso se pierda entre chats/sesiones

5. **Guardrails**
   - Rick no debe declarar progreso de proyecto sin:
     - Linear project/issue trazable
     - artefacto o update en Notion/Drive
   - si el proyecto oficial no existe en Linear/Notion, debe crearlo o registrar bloqueo explícito

## Criterios de aceptación

- [ ] Diagnosticar explícitamente si la página/DB de Notion indicada por David fue realmente actualizada o no, y por qué.
- [ ] Proponer e idealmente implementar soporte project-aware para Linear (crear/resolver project y asociar issues al project correcto).
- [ ] Proponer e idealmente implementar un registro maestro de proyectos en Notion con al menos una vista Kanban.
- [ ] Definir el esquema mínimo de proyecto en Notion: nombre, estado, carpeta, Linear project, owners, updates, issues, tiempos, bloqueos.
- [ ] Definir cómo se registran handoffs entre agentes/subagentes.
- [ ] Ajustar skills/prompts/guardrails para que Rick use esta gobernanza por defecto en proyectos oficiales.
- [ ] Dejar el resultado en el `## Log` con archivos tocados, tests y cualquier limitación real.

## Log

### [codex] 2026-03-09 10:23 -03:00
Tarea creada por pedido directo de David.

Hallazgo base ya confirmado por Codex:

- hoy Rick sí deja artefactos reales en la carpeta del proyecto
- hoy Rick sí crea/comenta issues en Linear
- pero la asociación explícita al project de Linear no está resuelta por las tools actuales
- y no hay evidencia de un tablero operativo visible de proyecto en Notion para `Proyecto Embudo Ventas`

Se pide a Claude atacar esta brecha de gobernanza/seguimiento en paralelo, sin bloquear el resto del flujo editorial/embudo.

### [claude-code] 2026-03-09

**Diagnóstico confirmado:**
- La URL `85f897...` que indicó David es la **Bitácora — Umbral Agent Stack** (log de actividad general), NO un registro de proyectos. Se dejó intacta.
- Codex (PR #113, branch `codex/rick-editorial-notion-hardening`) ya entregó las tools de bajo nivel: `list_projects`, `create_project`, `attach_issue_to_project`, `list_project_issues` (Linear) y `read_database`, `search_databases`, `create_database_page`, `update_page_properties` (Notion).

**Implementación completada — branch `claude/task-004-project-governance`:**

**1. Nueva DB de proyectos en Notion:**
- Nombre: `📁 Proyectos — Umbral`
- URL: `https://www.notion.so/d4098fa43280434a8ae4b11cab81246f`
- NOTION_PROJECTS_DB_ID: `d4098fa43280434a8ae4b11cab81246f`
- Schema: Nombre (TITLE), Estado (SELECT), Linear Project (URL), Ruta compartida (RICH_TEXT), Responsable (RICH_TEXT), Agentes (MULTI_SELECT), Sprint, Inicio (DATE), Objetivo (DATE), Issues abiertas (NUMBER), Bloqueos, Siguiente acción, Último update (DATE)

**2. Backfill Proyecto Embudo Ventas:**
- Entrada creada: `https://www.notion.so/31e5f443fb5c8125a21ce5333fb32a03`
- Linear: `https://linear.app/umbral/project/proyecto-embudo-ventas-6d4b3ed16eb2`
- 7 issues abiertas (UMB-27..UMB-33, todas Backlog)
- Siguiente acción: "Paso 5 en curso — arquitectura web v1 (UMB-32) + curación editorial (UMB-33)"

**3. Archivos tocados:**
- `worker/config.py` → `NOTION_PROJECTS_DB_ID`
- `worker/tasks/notion.py` → `handle_notion_upsert_project` + `_build_project_properties`
- `worker/linear_client.py` → `create_project_update` (GraphQL `projectUpdateCreate`)
- `worker/tasks/linear.py` → `handle_linear_create_project_update`
- `worker/tasks/__init__.py` → registra ambos handlers
- `openclaw/extensions/umbral-worker/index.ts` → `umbral_notion_upsert_project` + `umbral_linear_create_project_update`
- `openclaw/workspace-templates/SOUL.md` → Regla 4 (gobernanza) + Regla 5 (handoffs)
- `openclaw/workspace-templates/skills/notion/SKILL.md` → documenta `notion.upsert_project`
- `docs/07-worker-api-contract.md` → 2 tasks nuevos en tabla

**4. Tests:**
- `tests/test_notion_project_registry.py` → 4 tests (requires_name, no_db, creates_new, updates_existing)
- `tests/test_linear_project_update.py` → 5 tests (no_api_key, no_body, no_project, success, gql_call)
- Todos pasan: 9/9 nuevos + 17/17 regresión

**5. Limitaciones documentadas:**
- Handoffs: solo convención via título `[HANDOFF → <Agente>]` + descripción estructurada. Sin push — requiere poll con `linear.list_project_issues`. Los agentes no tienen user IDs de Linear (sin assignee explícito).
- `linear.create_project_update`: si el workspace Linear no tiene acceso a `projectUpdateCreate`, devolverá `{"ok": false, "error": "..."}` con mensaje claro.
