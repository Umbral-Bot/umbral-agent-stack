# Protocolo de Coordinación Inter-Agentes

> Este archivo define cómo los agentes AI que trabajan en este repositorio se coordinan entre sí.
> **Todos los agentes DEBEN leer este archivo al inicio de cada sesión.**

## Agentes participantes

| Agente | Herramienta | Rol | Fortalezas |
|--------|-------------|-----|------------|
| **Cursor** | Cursor IDE (Agent mode) | **Lead / Orquestador** | Edición precisa, contexto largo, planning, revisión |
| **Antigravity** | Antigravity | Ejecutor | Iteración rápida, multi-archivo, refactoring |
| **Codex** | Codex CLI / VS Code | Ejecutor | Terminal, tests, CI, tareas que necesitan ejecución |

## Reglas fundamentales

1. **Cursor es el lead.** Crea tareas, asigna, revisa resultados, y mantiene el `board.md`.
2. **Un solo agente trabaja a la vez.** David (el humano) cambia entre agentes manualmente.
3. **Toda coordinación pasa por archivos** en `.agents/`. No hay canal externo.
4. **Al iniciar sesión**, el agente lee `.agents/board.md` para entender el estado actual.
5. **Al terminar trabajo**, el agente actualiza el estado de la tarea y agrega una entrada al log.

## Estructura de archivos

```
.agents/
  PROTOCOL.md              ← Este archivo (reglas del juego)
  board.md                 ← Estado actual de todas las tareas activas
  tasks/
    YYYY-MM-DD-NNN-slug.md ← Una tarea = un archivo
```

## Ciclo de vida de una tarea

```
pending → assigned → in_progress → done
                  ↘ blocked (con explicación)
```

| Estado | Quién lo pone | Significado |
|--------|---------------|-------------|
| `pending` | Cursor (lead) | Tarea creada, sin asignar |
| `assigned` | Cursor (lead) | Asignada a un agente específico |
| `in_progress` | El agente asignado | El agente está trabajando en ella |
| `done` | El agente asignado | Completada con éxito |
| `blocked` | El agente asignado | No puede continuar, necesita input |

## Formato de tarea

Cada archivo en `tasks/` usa este formato:

```markdown
---
id: "YYYY-MM-DD-NNN"
title: "Descripción corta"
status: pending | assigned | in_progress | done | blocked
assigned_to: cursor | antigravity | codex
created_by: cursor | antigravity | codex
priority: high | medium | low
sprint: S0 | S1 | S2 | ...
created_at: ISO-8601
updated_at: ISO-8601
---

## Objetivo
Qué hay que hacer y por qué.

## Contexto
Archivos relevantes, dependencias, decisiones previas.

## Criterios de aceptación
- [ ] Criterio 1
- [ ] Criterio 2

## Log
### [agente] YYYY-MM-DD HH:MM
Qué hizo, qué archivos tocó, resultado de tests.
```

## Instrucciones por agente

### Para Cursor (lead)

1. Al iniciar sesión, lee `board.md` y revisa tareas `done` o `blocked`.
2. Integra el trabajo completado por otros agentes (review + merge mental).
3. Crea nuevas tareas según lo que David necesite.
4. Actualiza `board.md` después de crear/cerrar tareas.

### Para Antigravity

1. Al iniciar, David te dirá: "Lee `.agents/PROTOCOL.md` y trabaja en tus tareas".
2. Lee `board.md` para ver tus tareas asignadas (`assigned_to: antigravity`).
3. Para cada tarea asignada:
   - Cambia `status` a `in_progress` y `updated_at` al momento actual.
   - Trabaja en la tarea siguiendo los criterios de aceptación.
   - Al terminar, cambia `status` a `done` y agrega una entrada en `## Log`.
   - Si no podés completarla, cambia a `blocked` y explica por qué en el Log.
4. **No crees tareas nuevas.** Si detectás trabajo adicional, documentalo en el Log.

### Para Codex

1. Al iniciar, David te dirá: "Lee `.agents/PROTOCOL.md` y trabaja en tus tareas".
2. Mismo flujo que Antigravity (ver arriba).
3. Codex tiene ventaja en tareas que requieren ejecución en terminal (tests, builds, deploys).

## Convenciones

- **Nombres de archivo**: `YYYY-MM-DD-NNN-slug.md` donde NNN es secuencial por día.
- **Timestamps**: ISO-8601 en zona horaria local (America/Mexico_City).
- **Log entries**: Siempre incluir archivos modificados y resultado de tests si aplica.
- **board.md**: Lo mantiene el lead (Cursor). Los demás agentes no lo editan.

## Prompt de inicio para David

Cuando David abra Antigravity o Codex, puede pegar esto:

> Lee `.agents/PROTOCOL.md` para entender cómo trabajamos y después revisa `.agents/board.md` para ver tus tareas asignadas. Trabaja en las que tengan `assigned_to` con tu nombre.
