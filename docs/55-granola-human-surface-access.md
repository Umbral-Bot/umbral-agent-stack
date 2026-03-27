# 55 - Granola human surface access

> Evidencia operativa sobre qué superficies humanas de Notion ve hoy la integración `Rick` después del sharing ejecutado el 2026-03-27.

## 1. Objetivo

Dejar explícito el estado real de acceso antes de ejecutar promoción `raw -> curado -> destino` sobre superficies humanas gobernadas en Notion.

## 2. IDs exactos confirmados

- `Registro de Sesiones y Transcripciones` -> `7eca76a8d9f3403b9de11eb24229ac8c`
- `Registro de Tareas y Proximas Acciones` -> `517bfeb967584d33bf6f6ba1b853bb4a`
- `Asesorías & Proyectos` -> `3c1112c327cd445f848f041c4f8449c2`

## 3. Verificación repo-side con Rick

Probado el 2026-03-27 cargando `.env` del repo y ejecutando:

```powershell
python scripts/verify_notion_surface_access.py --json
```

Resultado:

- `granola_raw` -> `reachable`
- `technical_tasks` -> `reachable`
- `technical_projects` -> `reachable`
- `bridge` -> `reachable`
- `deliverables` -> `reachable`
- `curated_sessions` -> `reachable`
- `human_tasks` -> `reachable`
- `commercial_projects` -> `reachable`

Conclusión:

- la frontera de permisos ya no bloquea el pipeline
- Rick ya puede leer la capa raw, la capa curada humana, la DB humana de tareas y la DB comercial humana

## 4. Schemas observados

### 4.1 Capa curada humana

`Registro de Sesiones y Transcripciones`:

- `Nombre` -> `title`
- `Dominio` -> `select`
- `Tipo` -> `select`
- `Fecha` -> `date`
- `Proyecto` -> `relation`
- `Estado` -> `status`
- `Fuente` -> `select`
- `URL fuente` -> `url`
- `Notas` -> `rich_text`
- `Transcripción disponible` -> `checkbox`

### 4.2 Tareas humanas

`Registro de Tareas y Proximas Acciones`:

- `Nombre` -> `title`
- `Dominio` -> `select`
- `Proyecto` -> `relation`
- `Sesion relacionada` -> `relation`
- `Tipo` -> `select`
- `Estado` -> `status`
- `Prioridad` -> `select`
- `Responsable` -> `people`
- `Fecha objetivo` -> `date`
- `Origen` -> `select`
- `URL fuente` -> `url`
- `Notas` -> `rich_text`

### 4.3 Proyectos humanos

`Asesorías & Proyectos`:

- `Nombre` -> `title`
- `Estado` -> `status`
- `Cliente` -> `select`
- `Fecha` -> `date`
- `Monto` -> `number`
- `Plazo` -> `date`
- `Tipo` -> `select`
- `Acción Requerida` -> `select`

## 5. Consecuencia para implementación

La separación de contratos sigue siendo válida:

- `NOTION_GRANOLA_DB_ID`
  - raw intake
- `NOTION_TASKS_DB_ID`
  - Kanban técnico del stack
- `NOTION_PROJECTS_DB_ID`
  - registry técnico del stack
- `NOTION_CURATED_SESSIONS_DB_ID`
  - DB humana curada de sesiones
- `NOTION_HUMAN_TASKS_DB_ID`
  - DB humana de tareas
- `NOTION_COMMERCIAL_PROJECTS_DB_ID`
  - DB humana comercial

Pero el bloqueo principal ya cambió:

- antes: sharing/permisos
- ahora: definir y ejecutar el primer slice live `raw -> curado`

## 6. Siguiente paso exacto

1. ejecutar un piloto live de `granola.promote_curated_session`
2. usar una reunión ya validada en raw, idealmente `Konstruedu`
3. crear o actualizar una sesión curada con:
   - `Nombre`
   - `Dominio`
   - `Tipo`
   - `Fecha`
   - `Fuente`
   - `URL fuente`
   - `Notas`
   - `Proyecto` si el page id comercial ya está identificado
4. dejar comentarios de trazabilidad entre raw y curado
5. revisar el resultado en Notion antes de avanzar a `curado -> destino`
