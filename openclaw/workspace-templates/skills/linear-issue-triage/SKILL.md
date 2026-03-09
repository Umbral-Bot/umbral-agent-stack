---
name: linear-issue-triage
description: triage new or active linear issues into actionable recommendations project,
  priority, state, duplicates, next owner, missing context, and next steps. use when
  a user provides linear issue links or asks to review the latest active issues in
  linear and needs concrete updates they can apply in linear.
metadata:
  openclaw:
    emoji: 🚦
    requires:
      env: []
---

# Linear Issue Triage

## Objetivo
Convertir issues nuevas o activas de Linear en recomendaciones concretas y aplicables: proyecto correcto, prioridad, estado, duplicados, owner siguiente y contexto faltante.

## Inputs aceptados
1. lista de URLs de Linear
2. export de issues
3. pedido como `triage new issues in Linear`

Si el agente puede consultar Linear, partir por:
- team(s) indicados por el usuario
- por defecto `state in (New, Triage, Backlog)` y `created in last 14 days`
- si la muestra es pequena, ampliar a `updated in last 30 days`

## Salida obligatoria
1. tabla de acciones de triage
2. action cards por issue
3. follow-ups y owner pings

## Rubrica
- Elegir proyecto segun donde debe aterrizar la solucion, no donde se detecto.
- Definir prioridad P0-P3 por Impact x Urgencia x Confianza.
- Elegir estado entre Triage, Backlog, Planned, In Progress, Blocked, Done.
- Marcar probables duplicados cuando coincidan sintomas, componente, reproduccion o ventana temporal.
- Elegir next owner por la siguiente accion, no por implementador final.

## Calidad minima
- No devolver resumenes vagos.
- Cada issue debe terminar con una unica `Next action`.
- Si falta contexto, convertirlo en preguntas especificas y comentario sugerido.
- Mantener el razonamiento corto y accionable.

