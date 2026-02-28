---
id: "2026-02-27-003"
title: "VM: auditar OpenClaw instalado, proyectos y automatizaciones — regularizar"
status: assigned
assigned_to: codex
created_by: cursor
priority: high
sprint: S4
created_at: "2026-02-27"
updated_at: "2026-02-27T14:00:00-03:00"
---

## Objetivo

En la VM Windows (PCRick) donde corre el Worker: auditar qué hay instalado de OpenClaw más allá del Worker, qué proyectos y automatizaciones tenían lugar en esa máquina, y dejar un plan para regularizarlo según la arquitectura (Rick solo en VPS; VM = Execution Plane).

## Contexto

- La arquitectura oficial pone a Rick (OpenClaw Gateway) solo en la VPS. La VM es Execution Plane (Worker FastAPI, PAD/RPA, etc.).
- David indicó que OpenClaw en la VM tenía "algunos proyectos corriendo" y "automatizaciones". Hay que inventariar eso para decidir qué migrar, qué mantener y qué desactivar.
- Codex está en VS Code en la VM y puede ejecutar comandos y revisar archivos en esa máquina.

## Criterios de aceptación

1. **Inventario OpenClaw en la VM:**
   - ¿Existe OpenClaw Gateway (npm `openclaw` o `npx openclaw`)? Si sí: versión y ruta.
   - Ubicación de config/workspace: `%USERPROFILE%\.openclaw\` o similar; listar contenido.
   - Servicios: `openclaw-worker` (Worker) ya documentado; ¿hay otro servicio relacionado con OpenClaw (ej. gateway)?
   - Variables de entorno o config que apunten a OpenClaw (sin valores sensibles).

2. **Proyectos y automatizaciones:**
   - Qué proyectos/workspaces estaban asociados a OpenClaw en la VM (carpetas, nombres).
   - Qué automatizaciones había: scripts, triggers, cron-like, Power Automate, etc.
   - Rutas y descripción breve de cada uno.

3. **Plan de regularización:**
   - Qué debe quedar en la VM (solo Worker + PAD/RPA según arquitectura).
   - Qué debe migrarse a la VPS o desactivarse.
   - Pasos concretos para aplicar el plan (sin ejecutarlos aún si requieren decisión de David).

4. **Documentar en el repo:**
   - Crear o actualizar `docs/audits/vm-openclaw-audit-2026-02-27.md` con el inventario y el plan.
   - Actualizar `runbooks/runbook-vm-worker-setup.md` si hace falta reflejar qué NO debe correr (p. ej. gateway).

5. **Log:** Añadir entrada en el Log de este archivo con hallazgos, archivos tocados y recomendaciones.

## Entregables

- `docs/audits/vm-openclaw-audit-2026-02-27.md`: inventario de OpenClaw en VM, proyectos, automatizaciones, plan de regularización.
- Actualización de runbook si corresponde.
- Entrada en Log de esta tarea.

## Referencias

- Arquitectura: [docs/00-overview.md](../../docs/00-overview.md)
- ADR Rick en VPS: [docs/adr/ADR-001-rick-location.md](../../docs/adr/ADR-001-rick-location.md)
- VM audit previa: [docs/audits/vm-2026-02-27.md](../../docs/audits/vm-2026-02-27.md)
- Runbook VM: [runbooks/runbook-vm-worker-setup.md](../../runbooks/runbook-vm-worker-setup.md)
- Protocolo: [.agents/PROTOCOL.md](../../.agents/PROTOCOL.md)

## Log

### [cursor] 2026-02-27 14:00
Tarea creada. Asignada a Codex para ejecutar en la VM. David indicó que OpenClaw en la VM tenía proyectos y automatizaciones; se requiere inventario y plan de regularización según arquitectura.
