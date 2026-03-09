---
name: agent-handoff-governance
description: gobernar handoffs entre agentes y subagentes para que el trabajo delegado
  conserve contexto mÃ­nimo suficiente, owner explÃ­cito, criterio de aceptaciÃ³n,
  eta y trazabilidad hasta volver al solicitante. usar cuando un agente detecta bloqueo,
  necesita experiencia especializada, debe decidir entre subagente vs issue vs update,
  registrar el traspaso en linear y/o notion, evitar `no_reply` o cierres prematuros,
  auditar delegaciones, integrar resultados de subagentes o distinguir progreso real
  de fake progress.
metadata:
  openclaw:
    emoji: 🤝
    requires:
      env: []
---

# Agent Handoff Governance

## Overview

Aplicar esta skill para delegar trabajo sin perder contexto, ownership ni trazabilidad.
Mantener una regla central: el agente solicitante sigue siendo responsable del resultado final hasta integrar la respuesta del experto y cerrar el loop con quien abriÃ³ el caso.

## Mantener ownership correcto

- Mantener al agente solicitante como owner del resultado final ante el caso, proyecto o usuario original.
- Transferir al agente experto solo el ownership del trabajo delegado, no del caso completo, salvo instrucciÃ³n explÃ­cita.
- Evitar handoffs implÃ­citos. Hacer explÃ­cito quiÃ©n pide, quiÃ©n resuelve, quiÃ©n integra y quiÃ©n cierra.
- Mantener siempre un camino de regreso al solicitante original.

## Elegir el mecanismo correcto

### Usar subagente

Usar subagente cuando la tarea sea especializada, acotada y todavÃ­a forme parte del mismo caso activo.
Elegir esta vÃ­a cuando el agente solicitante vaya a seguir integrando la respuesta y necesite paralelizar o aislar contexto sin transferir el ownership final.

Usar subagente solo si:

- el entregable esperado es claro y verificable;
- la tarea puede devolverse a la sesiÃ³n solicitante para integraciÃ³n;
- el trabajo no debe quedar suelto sin seguimiento persistente.

### Usar issue o subtarea

Usar issue o subtarea cuando el trabajo deba sobrevivir a cambios de contexto, sesiÃ³n, turno o agente.
Preferir esta vÃ­a cuando haya bloqueo real, dependencia entre equipos, necesidad de visibilidad, prioridad, SLA, ETA, o riesgo de que la respuesta tarde o se pierda.

Preferir subtarea o sub-issue cuando el trabajo cuelgue de un caso padre.
Preferir relaciÃ³n blocked/blocking cuando el trabajo experto desbloquee otro frente.

### Usar update

Usar update solo para informar progreso, registrar una decisiÃ³n ya tomada o dejar constancia de algo que ya tiene owner y tracking.
No usar update como sustituto de un handoff cuando exista transferencia de trabajo, bloqueo, dependencia o necesidad de aceptaciÃ³n formal.

## Aplicar lÃ³gica de integraciÃ³n de subagentes

- Formular la tarea del subagente con problema, entregable esperado, criterio de aceptaciÃ³n y formato de retorno.
- Asumir que el subagente trabaja con contexto aislado. Incluir solo contexto mÃ­nimo suficiente y enlazar fuentes.
- Tratar `subagent accepted`, `issue creada`, `ping enviado` o `voy a revisarlo` como coordinaciÃ³n, no como resoluciÃ³n.
- Esperar un resultado concreto antes de actualizar a `done`, `closed` o equivalente.
- Registrar el resultado del subagente en el sistema de tracking si afecta roadmap, proyecto, dependencia o estado compartido.
- Integrar el resultado en el caso original antes de responder que el trabajo quedÃ³ resuelto.

## Ejecutar el flujo obligatorio

### 1. Detectar bloqueo o trabajo especializado

Explicitar por quÃ© el agente actual no debe seguir en solitario.
Nombrar la especialidad faltante, el riesgo del bloqueo y el impacto si no se delega.

### 2. Crear un item trazable

Crear issue, sub-issue, subtarea o registro equivalente.
En Linear, enlazar al padre o marcar relaciones blocked/blocking cuando corresponda.
En Notion, crear o actualizar una pÃ¡gina o tarea enlazada al caso origen.

### 3. Asignar owner experto o responsable

Asignar una persona o agente concreto.
No dejar owners vagos como â€œbackendâ€, â€œequipoâ€, â€œalguienâ€ o â€œpor asignarâ€ salvo triage explÃ­cito y temporal.

### 4. Dejar contexto mÃ­nimo suficiente

Incluir Ãºnicamente:

- estado actual;
- problema exacto;
- intento ya realizado;
- restricciones, riesgos y supuestos;
- enlaces a fuente de verdad;
- entregable esperado.

No copiar transcriptos largos ni contexto redundante.
Resumir en 3 a 8 bullets y enlazar material extenso.

### 5. Esperar y revisar la respuesta del experto

No cerrar por mera delegaciÃ³n.
Esperar diagnÃ³stico, decisiÃ³n, artefacto, cambio aplicado o recomendaciÃ³n accionable.
Si el retorno del subagente no llega o es ambiguo, tratar el handoff como pendiente.

### 6. Integrar el resultado

Actualizar el caso padre, proyecto o plan original.
Quitar bloqueos solo si el criterio de aceptaciÃ³n se cumpliÃ³.
Registrar quÃ© cambiÃ³, quÃ© sigue pendiente y quÃ© riesgo residual queda.

### 7. Responder al solicitante original

Devolver un resumen corto con:

- resultado;
- evidencia o link;
- impacto sobre el caso original;
- siguiente paso o criterio de cierre.

## Usar el formato obligatorio del handoff

Copiar y completar siempre este formato. No omitir owner, criterio de aceptaciÃ³n ni ETA.
Si la ETA no es segura, escribir `eta: unknown` y aÃ±adir un `checkpoint` explÃ­cito.

```md
## Handoff
- tipo: subagent | issue | sub-issue | update
- solicitante original:
- owner del handoff:
- caso padre / proyecto:
- motivo del handoff:
- problema a resolver:
- contexto mÃ­nimo suficiente:
  - estado actual:
  - intento previo:
  - restricciones / riesgos:
  - links fuente:
- entregable esperado:
- criterio de aceptaciÃ³n:
- eta:
- checkpoint si no hay eta cerrada:
- registro:
  - linear:
  - notion:
- plan de retorno al solicitante:
- condiciÃ³n exacta de cierre:
```

## Registrar en Linear y/o Notion

### En Linear

- Crear issue o sub-issue cuando el trabajo necesite seguimiento operativo.
- Asignar assignee explÃ­cito.
- AÃ±adir due date o ETA si existe.
- Conectar con parent, blocked/blocking o related segÃºn el tipo de dependencia.
- Dejar el handoff como comentario o en la descripciÃ³n si define el trabajo.
- AÃ±adir comentario de resoluciÃ³n del experto y comentario de integraciÃ³n del solicitante.

### En Notion

- Crear o actualizar tarea o pÃ¡gina cuando haga falta contexto largo, decision log o relaciÃ³n con documentaciÃ³n.
- Registrar owner en una propiedad `Person`.
- Registrar ETA o checkpoint en una propiedad `Date`.
- Conectar el caso con una propiedad `Relation` o con backlinks a la pÃ¡gina padre.
- Usar @menciones o comentarios para notificar a owner y solicitante.
- Registrar resoluciÃ³n e integraciÃ³n en la misma pÃ¡gina para mantener trazabilidad.

### Cuando existan ambos sistemas

Usar Linear como fuente operativa del estado de ejecuciÃ³n.
Usar Notion como contexto largo, resumen de decisiÃ³n o documentaciÃ³n complementaria.
Mantener enlaces cruzados entre ambos.

## Evitar `NO_REPLY` y cierres prematuros

- Usar `NO_REPLY` solo para housekeeping silencioso o pasos internos que no deban producir una respuesta visible.
- No usar `NO_REPLY` para ocultar un bloqueo, un handoff, una escalaciÃ³n o un resultado que el solicitante necesita ver.
- No cerrar el caso cuando solo exista coordinaciÃ³n: issue creada, subagente lanzado, comentario dejado o ping enviado.
- No marcar `done` hasta recibir respuesta Ãºtil, verificar criterio de aceptaciÃ³n, integrar el resultado y responder al solicitante original.
- Si el handoff quedÃ³ pendiente, responder con estado real: `waiting`, `blocked`, `escalated` o equivalente; nunca simular resoluciÃ³n.

## Distinguir progreso real de fake progress

### Tratar como progreso real

- existir un item trazable con owner explÃ­cito, criterio de aceptaciÃ³n y ETA o checkpoint;
- recibir un resultado concreto del experto;
- integrar ese resultado en el caso o proyecto original;
- actualizar el estado compartido y responder al solicitante original.

### Tratar como fake progress

- decir â€œya lo deleguÃ©â€ sin owner ni aceptaciÃ³n;
- crear una issue o lanzar un subagente y asumir que eso resuelve el trabajo;
- mover el estado a `done` sin artefacto, decisiÃ³n o integraciÃ³n;
- publicar updates cosmÃ©ticos que no cambian el riesgo ni el estado real;
- usar `NO_REPLY` o silencio para aparentar que no hay trabajo pendiente.

## Registrar respuesta y resoluciÃ³n

Registrar siempre dos momentos distintos:

### Respuesta del experto

Registrar:

- diagnÃ³stico o decisiÃ³n;
- artefacto, cambio o recomendaciÃ³n;
- evidencia o links;
- pendiente residual.

### IntegraciÃ³n del solicitante

Registrar:

- quÃ© cambiÃ³ en el caso original;
- estado actualizado;
- si el bloqueo se levantÃ³ o no;
- link o resumen de la respuesta final al agente o caso original.

## Escalar si el experto no responde

- Esperar hasta la ETA acordada o hasta el checkpoint comprometido.
- Si no hay acuse de recibo, pedir confirmaciÃ³n de recepciÃ³n y owner efectivo.
- Si vence la ETA, o si no hay ETA y pasa un dÃ­a hÃ¡bil sin acuse, escalar a owner alternativo, lead o responsable de proyecto.
- Reasignar o abrir un bloqueo explÃ­cito si el trabajo sigue detenido.
- Informar al solicitante original que el caso sigue abierto, quiÃ©n fue escalado y cuÃ¡l es la nueva ETA o checkpoint.
- No cerrar ni desaparecer del hilo mientras el caso siga bloqueado.

## Usar estos ejemplos cortos

### Handoff bueno

```md
## Handoff
- tipo: sub-issue
- solicitante original: ops-agent
- owner del handoff: billing-agent
- caso padre / proyecto: PAY-142
- motivo del handoff: bloqueo por investigaciÃ³n de pagos fallidos
- problema a resolver: identificar causa raÃ­z del rechazo 3DS y proponer fix
- contexto mÃ­nimo suficiente:
  - estado actual: 12 pagos fallaron desde ayer
  - intento previo: se revisÃ³ app y no hay error cliente
  - restricciones / riesgos: no tocar antifraude sin evidencia
  - links fuente: PAY-142, dashboard de pagos, log Sentry
- entregable esperado: causa raÃ­z + cambio recomendado + evidencia
- criterio de aceptaciÃ³n: explicar causa, indicar acciÃ³n exacta y dejar link a PR o pasos manuales
- eta: 2026-03-10 15:00 utc
- checkpoint si no hay eta cerrada: n/a
- registro:
  - linear: PAY-203
  - notion: pagos/incidentes/3ds-marzo
- plan de retorno al solicitante: comentar en PAY-142 y mencionar a ops-agent
- condiciÃ³n exacta de cierre: resultado integrado en PAY-142 y bloqueo levantado o replanificado
```

### Handoff malo

```md
@billing Â¿pueden ver esto? creo que es algo de pagos. abrÃ­ un ticket. avisen.
```

### Cierre prematuro malo

```md
LancÃ© un subagente y abrÃ­ una issue. Cierro por ahora.
```

## Consultar el recurso de apoyo

Revisar [references/handoff-checklist.md](references/handoff-checklist.md) antes de cerrar un caso delegado o auditar un handoff dudoso.

