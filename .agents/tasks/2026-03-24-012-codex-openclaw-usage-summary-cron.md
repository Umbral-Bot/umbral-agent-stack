---
id: "2026-03-24-012"
title: "OpenClaw: automatizar runtime snapshot y resumir uso en Dashboard Rick"
status: done
assigned_to: codex
created_by: codex
priority: medium
sprint: R23
created_at: 2026-03-24T09:02:01-03:00
updated_at: 2026-03-24T09:21:00-03:00
---

## Objetivo
Cerrar el diferido operativo que quedo abierto tras el saneamiento de OpenClaw:

1. automatizar el export repo-side del runtime snapshot en la VPS;
2. mostrar un resumen compacto de uso/research en `Dashboard Rick`;
3. dejar trazado el bloqueo real del fallback VPS -> VM sin inventar mas cambios de red.

## Contexto
- `scripts/openclaw_runtime_snapshot.py` ya consolida paneles, runtime OpenClaw, `llm_usage`, `research_usage` y snapshots de sesiones.
- `scripts/dashboard_report_vps.py` ya publica `Dashboard Rick` y muestra `panel_tracking`, pero aun no resume uso/costo/research en el panel.
- `scripts/vps/install-cron.sh` aun deja el exporter de snapshot como oportunidad futura.
- El fallback VM no invasivo quedo listo en `scripts/vm/ensure_vm_reverse_tunnel.ps1`, pero el host sigue sin ninguna direccion alcanzable a `8088/8089`.

## Criterios de aceptacion
- [ ] Existe un cron wrapper para actualizar `reports/runtime/openclaw-runtime-snapshot-latest.json` y un markdown latest dentro del repo en VPS.
- [ ] `Dashboard Rick` recibe un bloque compacto de uso OpenClaw con LLM/research y costo proxy.
- [ ] Tests dirigidos cubren el nuevo payload/render.
- [ ] El bloqueo VPS -> VM queda documentado con precision operativa, incluyendo que falta una direccion host->VM alcanzable y no otro cambio de router virtual.

## Log
### [codex] 2026-03-24 09:13
Abri la rama `codex/openclaw-usage-summary-cron` y avance el slice repo-side:

- agregue `scripts/vps/openclaw-runtime-snapshot-cron.sh` para refrescar `reports/runtime/openclaw-runtime-snapshot-latest.{json,md}` cada 6h en VPS;
- extendi `scripts/vps/install-cron.sh` para instalar ese cron;
- agregue `usage_summary` en `scripts/dashboard_report_vps.py`, reutilizando `openclaw_runtime_snapshot.py` para resumir LLM/research/sesiones en 24h;
- renderice el bloque `Uso OpenClaw` en `worker/notion_client.py`;
- actualice docs en `docs/03-setup-vps-openclaw.md`, `docs/22-notion-dashboard-gerencial.md` y `docs/audits/openclaw-deferreds-followup-2026-03-24.md`.

Validacion local:

- `python -m pytest tests/test_dashboard.py tests/test_openclaw_runtime_snapshot.py tests/test_ops_logger.py -q` -> `51 passed`
- `python scripts/openclaw_runtime_snapshot.py --days 1 --format json > $null` -> OK
- `_usage_summary()` local devuelve payload valido aunque sin datos en este clon.
- ajuste adicional: el cron escribe en `reports/runtime/generated/` para no dejar el checkout de la VPS sucio sobre archivos versionados.

### [codex] 2026-03-24 09:21
Validacion real en VPS sobre la rama `codex/openclaw-usage-summary-cron`:

- `bash scripts/vps/install-cron.sh` agrego `openclaw-runtime-snapshot-cron.sh` cada 6h;
- `bash scripts/vps/openclaw-runtime-snapshot-cron.sh` genero:
  - `reports/runtime/generated/openclaw-runtime-snapshot-latest.json`
  - `reports/runtime/generated/openclaw-runtime-snapshot-latest.md`
- `bash scripts/vps/restart-worker.sh` + `python3 scripts/dashboard_report_vps.py --trigger manual --force` actualizaron `Dashboard Rick` con `31` bloques;
- lectura viva via `worker.notion_client.read_page(...)` confirmo `USO_OPENCLAW_PRESENT=True`.

Hallazgo operativo corregido durante la validacion:

- el primer wrapper escribia sobre `reports/runtime/openclaw-runtime-snapshot-latest.json`, dejando el checkout VPS sucio;
- se corrigio para escribir en `reports/runtime/generated/`, que queda dentro del repo pero fuera de archivos versionados.

Bloqueo VPS -> VM dejado documentado con precision en `docs/audits/vm-tailnet-operational-recovery-2026-03-15.md`:

- no falta mas script ni mas router virtual;
- falta una direccion host->VM realmente alcanzable a `8088/8089` para fijarla en el fallback no invasivo.
