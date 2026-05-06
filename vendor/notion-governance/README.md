# vendor/notion-governance

Snapshot pinneado del repo `Umbral-Bot/notion-governance` para usos read-only desde la VPS y desde scripts del stack que necesitan leer el registry de data sources Notion sin clonar el repo gobernanza.

## Contenido actual

- `registry/notion-data-sources.template.yaml` — copia de `notion-governance/registry/notion-data-sources.template.yaml` @ commit `1d1c3c6e5720f2995b43e43119512dec9f1f34b5` (2026-05-05).

## Reglas

1. **NO editar a mano.** El source of truth es `Umbral-Bot/notion-governance`.
2. **Refresh manual** cuando una task lo requiera. Procedimiento:
   ```bash
   # Desde Windows (donde está el clone notion-governance):
   Copy-Item C:\GitHub\notion-governance\registry\notion-data-sources.template.yaml \
     C:\GitHub\umbral-agent-stack\vendor\notion-governance\registry\notion-data-sources.template.yaml -Force
   cd C:\GitHub\notion-governance
   $sha = git rev-parse HEAD
   # Actualizar este README con el SHA nuevo
   cd C:\GitHub\umbral-agent-stack
   git add vendor/notion-governance/
   git commit -m "vendor(notion-governance): refresh registry snapshot @ <sha>"
   git push origin main
   ```
3. **Scripts en este repo** que necesiten el registry deben pasar `--registry vendor/notion-governance/registry/notion-data-sources.template.yaml` por defecto (o aceptar override por flag).

## Por qué vendoring y no clonar el repo en VPS

- VPS no tiene clonado `notion-governance` y agregar otro repo+sync introduce más superficie operativa.
- El registry cambia con baja frecuencia (días/semanas, no horas).
- El snapshot está pinneado a SHA en este README, así que es auditable.
- Cuando el registry cambie en `notion-governance` y la VPS necesite la versión nueva, se hace el refresh-and-push manual de arriba.
