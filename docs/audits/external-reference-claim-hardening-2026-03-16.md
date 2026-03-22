# External Reference Claim Hardening - 2026-03-16

## Objetivo

Cerrar la desviacion observada en el caso `Kris Wojslaw`, donde Rick:
- eligio bien el proyecto;
- mejoro el benchmark;
- pero uso lenguaje de cierre fuerte (`verificado`) sin traza operativa suficiente de adquisicion real;
- y no dejo `deliverable` ni `task` nueva proporcional al caso.

## Hallazgo operativo

Evidencia revisada:
- `ops_log.jsonl` de la VPS y VM
- bases Notion de `Projects`, `Deliverables` y `Tasks`
- archivo persistido en `G:\Mi unidad\Rick-David\Proyecto-Embudo-Ventas\informes\benchmark-kris-wojslaw-contexto-antes-que-sintaxis.md`

Hallazgo:
- Rick si reescribio el benchmark y actualizo el proyecto.
- No quedo rastro observable de `browser.*` ni `research.web` sobre el caso Kris.
- No aparecio `notion.upsert_deliverable`.
- No aparecio nueva `task` ligada al caso.

## Medida aplicada

Se endurecio el sistema en tres capas:

1. `openclaw/workspace-templates/AGENTS.md`
   - nueva regla 26:
     - `verificado`, `confirmado`, `auditado` o equivalentes exigen traza observable y, si impactan un proyecto, update o entregable proporcional.

2. `openclaw/workspace-templates/SOUL.md`
   - nueva regla 18:
     - Rick debe degradar el lenguaje si no puede sostener el cierre fuerte con tools o artefactos verificables.

3. `external-reference-intelligence`
   - se agrego regla explicita de lenguaje de certeza
   - se agrego matriz de lenguaje permitido por nivel de evidencia
   - se agrego check de trazabilidad para claims fuertes

## Despliegue

Sincronizado a:
- `/home/rick/umbral-agent-stack/openclaw/workspace-templates/`
- `/home/rick/.openclaw/workspaces/rick-orchestrator/`

Validacion:
- `python scripts/validate_skills.py`

## Comunicacion directa con Rick

Se dejo comentario en Control Room via `notion.add_comment`:
- `comment_id`: `3255f443-fb5c-816f-9390-001d67492aa4`

Mensaje operativo:
- o sostiene `verificado` con traza real y entregable/update;
- o baja el lenguaje del benchmark a `lectura aplicada` / `senal fuerte` y explicita el limite.

## Criterio de cierre

Este hardening se considera exitoso cuando el caso Kris quede en uno de estos dos estados:

1. `verificado` sostenido con:
   - adquisicion real observable;
   - `deliverable` o update trazable;
   - cierre consistente en Notion/ops log.

2. `lectura aplicada` o equivalente, sin claims mas fuertes que la evidencia disponible.
