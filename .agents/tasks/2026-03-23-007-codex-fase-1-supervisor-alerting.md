---
id: "2026-03-23-007"
title: "Fase 1: supervisor VPS y alerting Notion robusto"
status: done
assigned_to: codex
created_by: codex
priority: high
sprint: R24
created_at: 2026-03-23T12:24:00-03:00
updated_at: 2026-03-23T12:31:00-03:00
---

## Objetivo
Cerrar el frente supervisor/alerting abierto en el super diagnostico: validar que la VPS ya no entre en falso drift, verificar en vivo que `NOTION_SUPERVISOR_ALERT_PAGE_ID` apunte a una pagina activa y endurecer el tooling para detectar o degradar limpiamente paginas archivadas o destinos de alerta invalidos.

## Contexto
- Fase 0 ya dejo alineados `main`, VPS y VM.
- El bug `USER` / `systemd --user` en `scripts/vps/dispatcher-service.sh` ya fue desplegado y el loop falso del supervisor desaparecio.
- Sigue pendiente cerrar de forma robusta el canal de alertas Notion:
  - validar la pagina actual en vivo;
  - evitar que el supervisor trate una pagina archivada como destino valido;
  - mejorar `scripts/verify_stack_vps.py` o el tooling cercano para que detecte esta clase de drift.

## Criterios de aceptacion
- [x] La pagina configurada en `NOTION_SUPERVISOR_ALERT_PAGE_ID` queda validada en vivo o se documenta/corrige el drift real.
- [x] El supervisor maneja de forma clara paginas archivadas o destinos invalidos de Notion sin volver al estado de ruido opaco previo.
- [x] Existe una verificacion reproducible en repo para detectar este problema sin esperar a un fallo de cron.
- [x] Log y board actualizados con resultado real.

## Log
### [codex] 2026-03-23 12:24
- Inicio de Fase 1. Se parte desde `main` ya alineado tras merge de Fase 0 (PR #138) y se enfoca el slice en supervisor VPS + alerting Notion robusto.

### [codex] 2026-03-23 12:31
- Validacion viva en VPS:
  - `NOTION_SUPERVISOR_ALERT_PAGE_ID=0fd13978-b220-498e-9465-b4fb2efc5f4a` esta realmente archivada / `in_trash=true`.
  - La `Control Room` (`NOTION_CONTROL_ROOM_PAGE_ID=30c5f443-fb5c-80ee-b721-dc5727b20dca`) esta activa para el token de Rick/Worker.
  - La integracion `Supervisor` no tiene acceso a la `Control Room` (`404 object_not_found`), por lo que la ruta dedicada sigue degradada aunque ya no rompe el canal de alertas.
- Implementacion:
  - nuevo helper `scripts/notion_alert_target.py` para resolver el destino efectivo de alertas Notion;
  - `scripts/vps/supervisor.sh` ahora detecta paginas archivadas y hace fallback limpio a `Worker -> Control Room`;
  - `scripts/vps/supervisor.sh test-alert "..."` agrega smoke reproducible del canal de alertas;
  - `scripts/verify_stack_vps.py` ahora valida el target de alertas Notion e informa si la ruta dedicada esta degradada o rota.
- Validacion:
  - tests locales: `25 passed` en `tests/test_notion_alert_target.py`, `tests/test_env_loader.py`, `tests/test_run_worker_task.py`, `tests/test_provider_status.py`, `tests/test_quota_endpoint.py`;
  - VPS: `python3 scripts/verify_stack_vps.py` -> `plano base verificado con alerting degradado`;
  - VPS: `bash scripts/vps/supervisor.sh test-alert 'Supervisor alert smoke from phase 1'` -> fallback efectivo y comentario publicado en `Control Room`.
- Resultado:
  - el loop falso del supervisor ya no reaparecio desde Fase 0;
  - la pagina archivada ya no vuelve a producir ruido opaco ni pierde alertas;
  - queda deuda operativa menor: si se quiere identidad `Supervisor` sobre pagina dedicada, David debe crear/compartir una pagina activa nueva con esa integracion y actualizar `NOTION_SUPERVISOR_ALERT_PAGE_ID`.
