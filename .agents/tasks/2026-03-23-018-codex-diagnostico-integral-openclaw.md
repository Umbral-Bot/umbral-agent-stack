---
id: "2026-03-23-018"
title: "Diagnostico integral OpenClaw: servicio, configuracion, agentes, modelos, cron y mejoras"
status: done
assigned_to: codex
created_by: codex
priority: high
sprint: R24
created_at: 2026-03-23T21:12:35-03:00
updated_at: 2026-03-23T23:35:00-03:00
---

## Objetivo
Ejecutar un diagnostico integral de OpenClaw en la VPS, apoyado en el trabajo de fases ya cerrado, para verificar si el gateway, dashboard, modelos, agentes, sesiones, tareas cron, plugins, skills, canales e integraciones cargan y operan como corresponde. El entregable debe dejar evidencia real, tests y chequeos corridos, hallazgos priorizados y un plan serio de mejoras, incluyendo pendientes diferidos ya detectados.

## Contexto
- El sistema ya paso por fases 0-5 y un update de OpenClaw a `2026.3.23`.
- Tras el update hubo que reparar la ruta del plugin `acpx` en `~/.openclaw/openclaw.json`.
- El usuario quiere una revision exhaustiva de OpenClaw y su interconectividad, no solo del dashboard.
- Pendientes diferidos previos:
  - snapshot repo-side del tracking de paneles/OpenClaw a partir de `ops_log`
  - atribucion mas fina de costo/tokens por componente dentro de OpenClaw

## Criterios de aceptacion
- [x] Queda auditado el estado real de OpenClaw en VPS: servicio, version, bind, channels, agents, sessions, cron, plugins, skills y config.
- [x] Se ejecutan pruebas reales de funcionamiento y se deja evidencia honesta de lo que pasa y lo que no.
- [x] Se valida el wiring entre OpenClaw y el stack Umbral (worker, dispatcher, Notion, cron, skills/runtime).
- [x] Se documentan hallazgos priorizados con propuesta de acciones concretas.
- [x] Queda trazabilidad en el task log y board.

## Log
### [codex] 2026-03-23 21:12
Tarea creada y marcada `in_progress`. Inicio de diagnostico integral de OpenClaw desde rama `codex/diagnostico-openclaw-integral-r24`.

### [codex] 2026-03-23 23:35
Diagnostico integral completado y documentado en `docs/audits/diagnostico-integral-openclaw-2026-03-23.md`.

Resumen de hallazgos:

- OpenClaw `2026.3.23` esta operativo y el dashboard vuelve a abrir tras reparar `acpx`.
- Gateway, Telegram, cron, `main`, `rick-ops` y `rick-tracker` quedaron verificados en vivo.
- Wiring real OpenClaw -> Worker -> provider status / Linear / Calendar funciona.
- `research.web` sigue degradado por quota Tavily agotada.
- Se detecto drift de topologia (`openclaw.service` duplicado), drift de workspace (skills/AGENTS desalineados), deuda de sesiones/transcripts y deuda de hardening.

Pendientes anotados para siguiente ronda:

- regularizar gateway unico en VPS
- sincronizar workspace compartido con el repo
- resolver Tavily/quota y cron degradados
- snapshot repo-side del tracking de paneles/OpenClaw
- atribucion fina de costo/tokens por componente
