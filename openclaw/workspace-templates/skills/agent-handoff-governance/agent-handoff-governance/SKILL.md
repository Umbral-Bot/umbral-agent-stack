---
name: agent-handoff-governance
description: gobernar handoffs entre agentes y subagentes para que el trabajo delegado conserve contexto mínimo suficiente, owner explícito, criterio de aceptación, eta y trazabilidad hasta volver al solicitante. usar cuando un agente detecta bloqueo, necesita experiencia especializada, debe decidir entre subagente vs issue vs update, registrar el traspaso en linear y/o notion, evitar `no_reply` o cierres prematuros, auditar delegaciones, integrar resultados de subagentes o distinguir progreso real de fake progress.
---

# Agent Handoff Governance

## Overview

Aplicar esta skill para delegar trabajo sin perder contexto, ownership ni trazabilidad.
Mantener una regla central: el agente solicitante sigue siendo responsable del resultado final hasta integrar la respuesta del experto y cerrar el loop con quien abrió el caso.

## Mantener ownership correcto

- Mantener al agente solicitante como owner del resultado final ante el caso, proyecto o usuario original.
- Transferir al agente experto solo el ownership del trabajo delegado, no del caso completo, salvo instrucción explícita.
- Evitar handoffs implícitos. Hacer explícito quién pide, quién resuelve, quién integra y quién cierra.
- Mantener siempre un camino de regreso al solicitante original.

## Elegir el mecanismo correcto

### Usar subagente

Usar subagente cuando la tarea sea especializada, acotada y todavía forme parte del mismo caso activo.
Elegir esta vía cuando el agente solicitante vaya a seguir integrando la respuesta y necesite paralelizar o aislar contexto sin transferir el ownership final.

Usar subagente solo si:

- el entregable esperado es claro y verificable;
- la tarea puede devolverse a la sesión solicitante para integración;
- el trabajo no debe quedar suelto sin seguimiento persistente.

### Usar issue o subtarea

Usar issue o subtarea cuando el trabajo deba sobrevivir a cambios de contexto, sesión, turno o agente.
Preferir esta vía cuando haya bloqueo real, dependencia entre equipos, necesidad de visibilidad, prioridad, SLA, ETA, o riesgo de que la respuesta tarde o se pierda.

Preferir subtarea o sub-issue cuando el trabajo cuelgue de un caso padre.
Preferir relación blocked/blocking cuando el trabajo experto desbloquee otro frente.

### Usar update

Usar update solo para informar progreso, registrar una decisión ya tomada o dejar constancia de algo que ya tiene owner y tracking.
No usar update como sustituto de un handoff cuando exista transferencia de trabajo, bloqueo, dependencia o necesidad de aceptación formal.

## Aplicar lógica de integración de subagentes

- Formular la tarea del subagente con problema, entregable esperado, criterio de aceptación y formato de retorno.
- Asumir que el subagente trabaja con contexto aislado. Incluir solo contexto mínimo suficiente y enlazar fuentes.
- Tratar `subagent accepted`, `issue creada`, `ping enviado` o `voy a revisarlo` como coordinación, no como resolución.
- Esperar un resultado concreto antes de actualizar a `done`, `closed` o equivalente.
- Registrar el resultado del subagente en el sistema de tracking si afecta roadmap, proyecto, dependencia o estado compartido.
- Integrar el resultado en el caso original antes de responder que el trabajo quedó resuelto.

## Ejecutar el flujo obligatorio

### 1. Detectar bloqueo o trabajo especializado

Explicitar por qué el agente actual no debe seguir en solitario.
Nombrar la especialidad faltante, el riesgo del bloqueo y el impacto si no se delega.

### 2. Crear un item trazable

Crear issue, sub-issue, subtarea o registro equivalente.
En Linear, enlazar al padre o marcar relaciones blocked/blocking cuando corresponda.
En Notion, crear o actualizar una página o tarea enlazada al caso origen.

### 3. Asignar owner experto o responsable

Asignar una persona o agente concreto.
No dejar owners vagos como “backend”, “equipo”, “alguien” o “por asignar” salvo triage explícito y temporal.

### 4. Dejar contexto mínimo suficiente

Incluir únicamente:

- estado actual;
- problema exacto;
- intento ya realizado;
- restricciones, riesgos y supuestos;
- enlaces a fuente de verdad;
- entregable esperado.

No copiar transcriptos largos ni contexto redundante.
Resumir en 3 a 8 bullets y enlazar material extenso.

### 5. Esperar y revisar la respuesta del experto

No cerrar por mera delegación.
Esperar diagnóstico, decisión, artefacto, cambio aplicado o recomendación accionable.
Si el retorno del subagente no llega o es ambiguo, tratar el handoff como pendiente.

### 6. Integrar el resultado

Actualizar el caso padre, proyecto o plan original.
Quitar bloqueos solo si el criterio de aceptación se cumplió.
Registrar qué cambió, qué sigue pendiente y qué riesgo residual queda.

### 7. Responder al solicitante original

Devolver un resumen corto con:

- resultado;
- evidencia o link;
- impacto sobre el caso original;
- siguiente paso o criterio de cierre.

## Usar el formato obligatorio del handoff

Copiar y completar siempre este formato. No omitir owner, criterio de aceptación ni ETA.
Si la ETA no es segura, escribir `eta: unknown` y añadir un `checkpoint` explícito.

```md
## Handoff
- tipo: subagent | issue | sub-issue | update
- solicitante original:
- owner del handoff:
- caso padre / proyecto:
- motivo del handoff:
- problema a resolver:
- contexto mínimo suficiente:
  - estado actual:
  - intento previo:
  - restricciones / riesgos:
  - links fuente:
- entregable esperado:
- criterio de aceptación:
- eta:
- checkpoint si no hay eta cerrada:
- registro:
  - linear:
  - notion:
- plan de retorno al solicitante:
- condición exacta de cierre:
```

## Registrar en Linear y/o Notion

### En Linear

- Crear issue o sub-issue cuando el trabajo necesite seguimiento operativo.
- Asignar assignee explícito.
- Añadir due date o ETA si existe.
- Conectar con parent, blocked/blocking o related según el tipo de dependencia.
- Dejar el handoff como comentario o en la descripción si define el trabajo.
- Añadir comentario de resolución del experto y comentario de integración del solicitante.

### En Notion

- Crear o actualizar tarea o página cuando haga falta contexto largo, decision log o relación con documentación.
- Registrar owner en una propiedad `Person`.
- Registrar ETA o checkpoint en una propiedad `Date`.
- Conectar el caso con una propiedad `Relation` o con backlinks a la página padre.
- Usar @menciones o comentarios para notificar a owner y solicitante.
- Registrar resolución e integración en la misma página para mantener trazabilidad.

### Cuando existan ambos sistemas

Usar Linear como fuente operativa del estado de ejecución.
Usar Notion como contexto largo, resumen de decisión o documentación complementaria.
Mantener enlaces cruzados entre ambos.

## Evitar `NO_REPLY` y cierres prematuros

- Usar `NO_REPLY` solo para housekeeping silencioso o pasos internos que no deban producir una respuesta visible.
- No usar `NO_REPLY` para ocultar un bloqueo, un handoff, una escalación o un resultado que el solicitante necesita ver.
- No cerrar el caso cuando solo exista coordinación: issue creada, subagente lanzado, comentario dejado o ping enviado.
- No marcar `done` hasta recibir respuesta útil, verificar criterio de aceptación, integrar el resultado y responder al solicitante original.
- Si el handoff quedó pendiente, responder con estado real: `waiting`, `blocked`, `escalated` o equivalente; nunca simular resolución.

## Distinguir progreso real de fake progress

### Tratar como progreso real

- existir un item trazable con owner explícito, criterio de aceptación y ETA o checkpoint;
- recibir un resultado concreto del experto;
- integrar ese resultado en el caso o proyecto original;
- actualizar el estado compartido y responder al solicitante original.

### Tratar como fake progress

- decir “ya lo delegué” sin owner ni aceptación;
- crear una issue o lanzar un subagente y asumir que eso resuelve el trabajo;
- mover el estado a `done` sin artefacto, decisión o integración;
- publicar updates cosméticos que no cambian el riesgo ni el estado real;
- usar `NO_REPLY` o silencio para aparentar que no hay trabajo pendiente.

## Registrar respuesta y resolución

Registrar siempre dos momentos distintos:

### Respuesta del experto

Registrar:

- diagnóstico o decisión;
- artefacto, cambio o recomendación;
- evidencia o links;
- pendiente residual.

### Integración del solicitante

Registrar:

- qué cambió en el caso original;
- estado actualizado;
- si el bloqueo se levantó o no;
- link o resumen de la respuesta final al agente o caso original.

## Escalar si el experto no responde

- Esperar hasta la ETA acordada o hasta el checkpoint comprometido.
- Si no hay acuse de recibo, pedir confirmación de recepción y owner efectivo.
- Si vence la ETA, o si no hay ETA y pasa un día hábil sin acuse, escalar a owner alternativo, lead o responsable de proyecto.
- Reasignar o abrir un bloqueo explícito si el trabajo sigue detenido.
- Informar al solicitante original que el caso sigue abierto, quién fue escalado y cuál es la nueva ETA o checkpoint.
- No cerrar ni desaparecer del hilo mientras el caso siga bloqueado.

## Usar estos ejemplos cortos

### Handoff bueno

```md
## Handoff
- tipo: sub-issue
- solicitante original: ops-agent
- owner del handoff: billing-agent
- caso padre / proyecto: PAY-142
- motivo del handoff: bloqueo por investigación de pagos fallidos
- problema a resolver: identificar causa raíz del rechazo 3DS y proponer fix
- contexto mínimo suficiente:
  - estado actual: 12 pagos fallaron desde ayer
  - intento previo: se revisó app y no hay error cliente
  - restricciones / riesgos: no tocar antifraude sin evidencia
  - links fuente: PAY-142, dashboard de pagos, log Sentry
- entregable esperado: causa raíz + cambio recomendado + evidencia
- criterio de aceptación: explicar causa, indicar acción exacta y dejar link a PR o pasos manuales
- eta: 2026-03-10 15:00 utc
- checkpoint si no hay eta cerrada: n/a
- registro:
  - linear: PAY-203
  - notion: pagos/incidentes/3ds-marzo
- plan de retorno al solicitante: comentar en PAY-142 y mencionar a ops-agent
- condición exacta de cierre: resultado integrado en PAY-142 y bloqueo levantado o replanificado
```

### Handoff malo

```md
@billing ¿pueden ver esto? creo que es algo de pagos. abrí un ticket. avisen.
```

### Cierre prematuro malo

```md
Lancé un subagente y abrí una issue. Cierro por ahora.
```

## Consultar el recurso de apoyo

Revisar [references/handoff-checklist.md](references/handoff-checklist.md) antes de cerrar un caso delegado o auditar un handoff dudoso.
