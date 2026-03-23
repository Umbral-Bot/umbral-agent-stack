---
id: "2026-03-23-012"
title: "Cleanup de directorios pytest temporales con permisos rotos"
status: done
assigned_to: codex
created_by: codex
priority: medium
sprint: R23
created_at: 2026-03-23T14:42:54-03:00
updated_at: 2026-03-23T14:56:00-03:00
---

## Objetivo
Eliminar el ruido residual del checkout local por directorios `pytest` temporales con permisos rotos y evitar que reaparezcan como warnings en `git status`.

## Contexto
- El repo ya quedó alineado a `main` tras cerrar Fase 2.
- Persisten warnings locales por `.pytest_tmp`, `.pytest_tmp_run2` y `pytest_tmp_run3`.
- El punto tiene dos frentes:
  1. Ignorar estos artefactos en el repo para que no vuelvan a ensuciar futuros checkouts.
  2. Limpiar los directorios ya existentes en este workspace si técnicamente es posible.

## Criterios de aceptación
- [x] `.gitignore` cubre los patrones `pytest` temporales relevantes.
- [x] Los directorios bloqueados se eliminan del workspace o queda evidencia concreta del impedimento técnico.
- [x] `git status` deja de mostrar warnings por `.pytest_tmp*`.
- [x] Tarea y `board.md` quedan actualizados con el resultado real.

## Log
### [codex] 2026-03-23 14:42
Inicio de tarea. Branch creada: `codex/pytest-temp-cleanup`. Estado inicial: `git status` muestra warnings por `.pytest_tmp`, `.pytest_tmp_run2` y `pytest_tmp_run3`. Voy a cubrir ignore repo-side y cleanup local con ACL/ownership si hace falta.

### [codex] 2026-03-23 14:56
Reescribí [`.gitignore`](C:/GitHub/umbral-agent-stack-codex/.gitignore) en ASCII limpio y agregué `/.pytest_tmp*/` y `/pytest_tmp*/`. Resultado: `git status --short --branch` dejó de mostrar warnings y ahora queda limpio salvo los archivos modificados reales.

Intenté cleanup físico de `C:\GitHub\umbral-agent-stack-codex\.pytest_tmp`, `.pytest_tmp_run2` y `pytest_tmp_run3` con `rd /s /q`, variantes `\\?\`, `icacls`, `takeown` y fallback WSL. Evidencia:
- `rd` e `icacls`: `Acceso denegado`
- `takeown`: la sesión actual corre con token medio, sin privilegios de administrador
- `wsl.exe`: no está instalado en este host

Conclusión: el problema de repo/workspace quedó resuelto del lado práctico (Git ya no emite ruido), y la persistencia física de esos tres directorios es una cuestión local de ACL/elevación del host, no una deuda del stack.
