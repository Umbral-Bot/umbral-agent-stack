# Auditoria VM OpenClaw - 2026-02-27

> Ejecutada en la VM Windows (PCRick) el 2026-02-27 23:11 -03:00.
> Objetivo: inventariar OpenClaw/proyectos/automatizaciones fuera del Worker y proponer regularizacion segun arquitectura (Rick en VPS, VM = Execution Plane).

## 1) Inventario OpenClaw en la VM

OpenClaw CLI/Gateway:
- `openclaw` instalado globalmente por npm.
- Version detectada: `2026.2.25`.
- Ruta CLI: `C:\Users\Rick\AppData\Roaming\npm\openclaw.cmd` (`openclaw.ps1` en misma carpeta).
- Node/NPM presentes (`node v24.13.1`, `npm 11.8.0`).

Config/workspace OpenClaw:
- Config principal: `C:\Users\Rick\.openclaw\openclaw.json`.
- Workspace principal: `C:\Users\Rick\.openclaw\workspace`.
- Estructuras relevantes detectadas:
  - `C:\Users\Rick\.openclaw\cron\jobs.json` (actualmente `jobs: []`).
  - `C:\Users\Rick\.openclaw\workspace\multiagent\` (proyecto MVP shadow mode).
  - `C:\Users\Rick\.openclaw\workspace\rpa\pad\` (scripts PAD/RPA).
  - `C:\Users\Rick\.openclaw\workspace\scripts\` (automatizaciones).

Servicios Windows relacionados:
- `openclaw-worker` (NSSM) `Running`, `Automatic`, puerto `8088`.
- No se detectaron otros servicios Windows tipo `openclaw*` o `rick*`.

Tareas programadas (Scheduled Tasks) relacionadas:
- `OpenClaw Gateway`
- `OpenClaw-TelegramAudioAgent`
- `Rick-Granola-Sync-Daily`
- `Rick-Multiagent-Progress-30min`

Config/variables (sin valores sensibles):
- Variables de entorno en sesion detectadas: `WORKER_TOKEN`, `NOTION_TOKEN`.
- `.openclaw\workspace\.env`: al menos `NOTION_TOKEN`.
- `openclaw-worker` inyecta `WORKER_TOKEN` y `PYTHONPATH`.
- `openclaw.json` indica `gateway.mode=local`, `gateway.port=18789`, `channels.telegram.enabled=false`.

## 2) Proyectos y automatizaciones detectadas

### Proyectos/workspaces

1. OpenClaw runtime/config local:
- Ruta: `C:\Users\Rick\.openclaw\`
- Evidencia: sesiones, logs, memoria sqlite, browser profile, config y backups.

2. Workspace operativo local:
- Ruta: `C:\Users\Rick\.openclaw\workspace\`
- Contiene docs operativos, `.env`, scripts, `multiagent`, `rpa`, logs y artefactos de integraciones.

3. Proyecto multiagent (shadow mode):
- Ruta: `C:\Users\Rick\.openclaw\workspace\multiagent\`
- Evidencia: `README.md`, `config/`, `langgraph/`, `litellm/`, `runtime/`, scripts smoke/bootstrap.
- Estado declarado en README: "shadow mode", sin impacto productivo directo.

4. Proyecto Telegram Audio Agent (externo al repo principal):
- Ruta de ejecucion: `G:\Mi unidad\Rick-David\telegram-audio-agent\`
- Script: `run-agent.ps1` (procesa inbound media de OpenClaw).

### Automatizaciones

1. `OpenClaw Gateway` (Scheduled Task):
- Accion: ejecuta `C:\Users\Rick\.openclaw\gateway.cmd`.
- `gateway.cmd` inicia Node + OpenClaw Gateway en puerto `18789`.
- Ultimo resultado capturado: `3221225786` (terminacion anormal/interrumpida).

2. `OpenClaw-TelegramAudioAgent` (Scheduled Task):
- Accion: PowerShell a `G:\Mi unidad\Rick-David\telegram-audio-agent\run-agent.ps1`.
- Repite cada 2 minutos (segun trigger actual).
- Ultimo resultado capturado: `4294770688` (error en ejecucion).

3. `Rick-Granola-Sync-Daily` (Scheduled Task):
- Script: `C:\Users\Rick\.openclaw\workspace\scripts\granola-sync.ps1`.
- Integra Granola -> Notion (usa token de Notion desde `.env`).
- Evidencia en log: ejecuciones correctas y creacion de items en Notion.

4. `Rick-Multiagent-Progress-30min` (Scheduled Task):
- Script: `C:\Users\Rick\.openclaw\workspace\scripts\multiagent-progress-check.ps1`.
- Ejecuta cada 30 min (bootstrap + smoke de fase 1, con append a Notion).
- Evidencia en log: ejecuciones recurrentes exitosas.

## 3) Diagnostico vs arquitectura objetivo

Arquitectura aceptada (ADR-001):
- Rick/OpenClaw Gateway debe operar en VPS (Control Plane) 24/7.
- VM debe quedar como Execution Plane (Worker + PAD/RPA y componentes de ejecucion).

Desviaciones actuales en VM:
- Existe Gateway OpenClaw local con task de arranque (`OpenClaw Gateway`).
- Existen automatizaciones de negocio/integracion (Granola/Notion, Telegram audio, checks multiagent) ejecutando en VM.
- Hay un workspace OpenClaw "operativo" en VM que mezcla runtime de control + automatizaciones.

## 4) Plan de regularizacion (sin ejecutar cambios aun)

### Debe quedar en VM

- `openclaw-worker` (FastAPI en 8088) como servicio principal de ejecucion.
- Scripts y componentes de ejecucion que realmente dependan de Windows/PAD/RPA.
- Artefactos tecnicos de pruebas locales, solo si no impactan el Control Plane.

### Debe migrarse a VPS o desactivarse en VM

- Gateway OpenClaw local (`OpenClaw Gateway`) -> desactivar en VM, operar en VPS.
- Automatizaciones de control/integracion (Notion/Granola/Telegram agent) -> mover a VPS o redefinir como tareas del Dispatcher/Worker.
- Check periodico de multiagent ligado a Notion (`Rick-Multiagent-Progress-30min`) -> migrar a VPS o desactivar si era temporal.

### Pasos concretos propuestos

1. Confirmar con David que VM quedara solo como Execution Plane.
2. Exportar inventario de Scheduled Tasks y respaldar scripts actuales (`workspace/scripts` + ruta `G:\...telegram-audio-agent`).
3. En VM: deshabilitar (no borrar aun) tasks:
   - `OpenClaw Gateway`
   - `OpenClaw-TelegramAudioAgent`
   - `Rick-Granola-Sync-Daily`
   - `Rick-Multiagent-Progress-30min`
4. Mantener activo solo `openclaw-worker`; validar health `/health` y `/run`.
5. Migrar automatizaciones necesarias a VPS con runbooks dedicados y secrets fuera de repo.
6. Tras validacion en VPS, retirar definitvamente automatizaciones legacy de VM.

## 5) Riesgos y recomendaciones

Riesgos si no se regulariza:
- Doble plano de control (VPS + VM) con comportamiento no deterministico.
- Fallas silenciosas (ya hay tasks con codigos de error).
- Dependencias ocultas en rutas locales/Google Drive.

Recomendaciones inmediatas:
- Definir "owner" y destino por cada task programada actual.
- Tratar `workspace/.env` de VM como material sensible y rotar tokens usados por automatizaciones legacy una vez migradas.
- Mantener este documento como baseline para cleanup por etapas.

