---
id: "2026-03-23-005"
title: "Super diagnostico exhaustivo de interconectividad y gobernanza operativa"
status: done
assigned_to: codex
created_by: codex
priority: high
sprint: R24
created_at: 2026-03-23T04:10:00-03:00
updated_at: 2026-03-23T07:45:00-03:00
---

## Objetivo
Hacer un barrido exhaustivo del sistema completo, apoyado en el super diagnostico del 2026-03-22 pero ampliado a interconectividad real entre repo, VPS, VM, Notion, Linear, OpenClaw, Google, busqueda, GitHub, skills y flujos de coordinacion, con pruebas reales, propuestas multinivel y documentacion final.

## Contexto
- El super diagnostico del 2026-03-22 ya detecto drift operativo y abrio/capitalizo follow-ups relevantes.
- David pidio una nueva pasada profunda, no necesariamente desde cero, pero si con foco fuerte en conexiones entre sistemas y apps.
- El `Control Room`/`OpenClaw` seguia mostrando un resumen visual pobre; este barrido tenia que confirmar si era drift de despliegue o problema real de diseño/publicacion.
- Tambien quedaba pendiente responder de forma explicita si faltaban skills nuevas y, si aplicaba, dejar prompts listos para crearlas o actualizar skills existentes.

## Criterios de aceptacion
- [x] Existe inventario de integraciones y caminos criticos entre sistemas.
- [x] Se ejecutan pruebas y smokes reales por integracion clave donde habia acceso operativo.
- [x] Se documentan fallos reales, drift, hipotesis validadas y oportunidades de mejora multinivel.
- [x] Se revisa necesidad de skills nuevas y se dejan prompts completos listos para crear o actualizar skills.
- [x] Se entrega documento final de diagnostico y actualizacion de board/tarea con log honesto.

## Log

### [codex] 2026-03-23 04:10
- Arranque R24 desde `main` actualizado y abri la rama `codex/super-diagnostico-interconectividad-r24`.
- Confirmacion inicial: `NOTION_CONTROL_ROOM_PAGE_ID` apunta a `OpenClaw` y la pagina viva seguia mostrando el resumen visual malo. Esto ya no era solo hipotesis de cache.

### [codex] 2026-03-23 06:30
- Ejecute barrido real por repo, VPS, Worker local VPS, VM, Notion y Linear.
- Hallazgos operativos principales:
  - loop falso del supervisor cada 5 min por `scripts/vps/dispatcher-service.sh` (`USER` no definido + `systemd --user` no disponible);
  - `NOTION_SUPERVISOR_ALERT_PAGE_ID` apunta a una pagina archivada y rompe alertas Notion;
  - `research.web` sigue fallando en runtime vivo;
  - Calendar y Gmail si funcionan en el Worker local VPS;
  - la telemetria ya muestra `task_completed` y `task_failed`, pero `source` y `source_kind` siguen en 4.1%.

### [codex] 2026-03-23 07:10
- Corregi y probe localmente fixes que atacan drift de interconectividad sin mentir sobre deploy:
  - `scripts/env_loader.py` ahora carga `~/.config/openclaw/env`;
  - `scripts/run_worker_task.py` deja de enrutar tareas genericas a la VM interactive por defecto;
  - `worker/app.py` devuelve snapshots utiles en `/providers/status` y `/quota/status` aunque no haya Redis local;
  - `scripts/vps/dispatcher-service.sh` tolera falta de `USER` y ausencia de `systemd --user`;
  - `scripts/verify_stack_vps.py` deja de declarar "stack listo" solo por conectividad base.

### [codex] 2026-03-23 07:45
- Documente el barrido completo en `docs/audits/super-diagnostico-interconectividad-2026-03-23.md`.
- Actualice `scripts/skills_coverage_report.py` y el reporte resultante:
  - coverage real corregido: `71/80` tasks con skill (`89%`);
  - faltantes autenticos: `gui.*`, `windows.open_url`, `google.audio.generate` y una skill dedicada de diagnostico cross-system.
- Deje prompts completos para skills en el propio diagnostico:
  - nueva `system-interconnectivity-diagnostics`;
  - actualizar `browser-automation-vm`;
  - actualizar `notion-project-registry`;
  - nueva `google-audio-generation`.
- Validacion final:
  - `python scripts/audit_traceability_check.py --format json`
  - `python scripts/governance_metrics_report.py --days 7 --format json`
  - `python scripts/skills_coverage_report.py`
  - `python scripts/secrets_audit.py`
  - `$env:WORKER_TOKEN='test'; python -m pytest tests -q` -> `1198 passed, 4 skipped, 1 warning`
  - `git diff --check` -> sin errores de diff; solo warnings CRLF del checkout Windows
