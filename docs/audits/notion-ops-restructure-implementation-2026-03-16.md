# Implementacion — Reestructura operativa de Notion

Fecha: 2026-03-16
Autor: Codex

## Objetivo

Cerrar la reestructura operativa de Notion sin botar la arquitectura util, separando:

- dashboard tecnico,
- panel operativo humano,
- inbox vivo,
- y bases operativas vinculadas.

## Cambios aplicados

### 1. `Dashboard Rick` queda como dashboard tecnico

Se reforzo el rol tecnico de la pagina:

- estado del stack,
- workers,
- cuotas,
- errores recientes,
- ruido tecnico,
- y nueva seccion `Operacion Notion`.

Archivos:

- [scripts/dashboard_report_vps.py](C:/GitHub/umbral-agent-stack-codex/scripts/dashboard_report_vps.py)
- [worker/notion_client.py](C:/GitHub/umbral-agent-stack-codex/worker/notion_client.py)
- [tests/test_dashboard.py](C:/GitHub/umbral-agent-stack-codex/tests/test_dashboard.py)

### 2. `OpenClaw` pasa a ser panel operativo humano

Se creo un renderer dedicado para `OpenClaw` con secciones utiles para decision:

- entregables pendientes de revision,
- proyectos con bloqueo o drift,
- bandeja viva,
- proximos vencimientos,
- recursos,
- bases operativas.

Archivo:

- [scripts/openclaw_panel_vps.py](C:/GitHub/umbral-agent-stack-codex/scripts/openclaw_panel_vps.py)

### 3. `Tareas` deja de absorber telemetria inutil

Se mejoro la persistencia de tareas para guardar mejor procedencia:

- `Source`
- `Source Kind`
- `Trace ID`
- `selected_model`

Ademas se creo una curacion incremental que archiva ruido viejo no vinculado.

Archivos:

- [worker/tasks/notion.py](C:/GitHub/umbral-agent-stack-codex/worker/tasks/notion.py)
- [worker/notion_client.py](C:/GitHub/umbral-agent-stack-codex/worker/notion_client.py)
- [dispatcher/service.py](C:/GitHub/umbral-agent-stack-codex/dispatcher/service.py)
- [scripts/notion_curate_ops_vps.py](C:/GitHub/umbral-agent-stack-codex/scripts/notion_curate_ops_vps.py)
- [tests/test_notion_tasks_registry.py](C:/GitHub/umbral-agent-stack-codex/tests/test_notion_tasks_registry.py)
- [tests/test_notion_ops_curation.py](C:/GitHub/umbral-agent-stack-codex/tests/test_notion_ops_curation.py)

### 4. `Bandeja Puente` vuelve a comportarse como inbox vivo

No se creo una base nueva. En vez de eso:

- se archivaron entradas resueltas viejas,
- se bajo el volumen visible,
- y `OpenClaw` ahora muestra solo items vivos.

### 5. Automatizacion de mantenimiento

Se agrego un cron especifico para curacion Notion diaria en la VPS.

Archivos:

- [scripts/vps/notion-curate-cron.sh](C:/GitHub/umbral-agent-stack-codex/scripts/vps/notion-curate-cron.sh)
- [scripts/vps/dashboard-cron.sh](C:/GitHub/umbral-agent-stack-codex/scripts/vps/dashboard-cron.sh)

Cron validado en VPS:

```text
20 5 * * * bash /home/rick/umbral-agent-stack/scripts/vps/notion-curate-cron.sh >> /tmp/notion_curate.log 2>&1
```

## Resultado medible

Snapshot de curacion:

- `projects_total`: `8`
- `tasks_total`: `13 -> 9`
- `tasks_unlinked`: `10 -> 4`
- `deliverables_total`: `21`
- `deliverables_pending_review`: `3`
- `deliverables_without_task_origin`: `16`
- `deliverables_live_without_task_origin`: `0`
- `deliverables_historical_without_task_origin`: `16`
- `bridge_total`: `12`
- `bridge_live`: `2`

Fuente:

- `/home/rick/umbral-agent-stack/docs/audits/notion-curation-snapshot-2026-03-16.json`

## Estado final por capa

### Bien resuelto

- `OpenClaw` como panel humano
- `Dashboard Rick` como panel tecnico
- `Entregables` como gate humano
- `Projects -> Task -> Deliverable -> Review` como flujo principal
- ruido tecnico viejo reducido
- entregables vivos sin `Tareas origen`: `0`

### Deuda residual

- muchos entregables historicos siguen sin `Tareas origen`, pero ya quedaron reclasificados como deuda historica y no como deuda operativa viva
- quedan `4` tareas no vinculadas, mantenidas como colchon reciente de diagnostico
- `Bandeja Puente` sigue siendo util, pero necesita disciplina de uso para no volver a degradarse

## Validacion

Local:

```text
python -m pytest tests/test_dashboard.py tests/test_notion_tasks_registry.py tests/test_notion_ops_curation.py tests/test_notion_project_registry.py tests/test_notion_deliverables_registry.py -q
42 passed

python scripts/validate_skills.py
OK
```

VPS:

- refresh forzado de `Dashboard Rick`: OK
- refresh forzado de `OpenClaw`: OK
- worker saludable en `127.0.0.1:8088`: OK

## Conclusión

No fue necesario rehacer todo Notion.

La solucion correcta fue separar capas y curar ruido:

- `Dashboard Rick` = observabilidad tecnica
- `OpenClaw` = decision operativa humana
- `Tareas` = ejecucion significativa, no log bruto
- `Entregables` = revision
- `Bandeja Puente` = inbox vivo, no historico horario

El sistema queda util para operar. La deuda que sigue abierta ya no es de arquitectura base, sino de normalizacion historica.
