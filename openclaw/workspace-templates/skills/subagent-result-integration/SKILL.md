---
name: subagent-result-integration
description: ensenar a usar sessions_spawn en openclaw sin confundir accepted con
  resultado final. usar cuando el agente quiera delegar una tarea pesada, lenta o
  paralelizable a un subagente y deba decidir entre flujo asincrono, orquestador con
  fan-out o respuesta integrada en el mismo turno. cubre cuando delegar, como redactar
  el task, como esperar e integrar resultados, como dejar trazabilidad con label,
  runid y childsessionkey, y como evitar cierres prematuros, no_reply, announce_skip
  o respuestas desfasadas.
metadata:
  openclaw:
    emoji: 🔗
    requires:
      env: []
---

# Subagent Result Integration

## Objetivo
Usar `sessions_spawn` solo cuando el flujo soporte asincronia o cuando exista un orquestador que integrara resultados antes de anunciar. Tratar `status: "accepted"` como confirmacion de arranque, nunca como evidencia de que el trabajo ya termino.

## Reglas duras
1. No dar una respuesta final al usuario justo despues de `sessions_spawn`.
2. No decir `listo`, `ya revise` o `ya confirme` hasta integrar el resultado real del hijo.
3. No usar `NO_REPLY` como salida facil despues de spawnear.
4. No usar `ANNOUNCE_SKIP` si ese announce es la via esperada para entregar el resultado.
5. No integrar un resultado por coincidencia de tema o label; verificar `label`, `runId`, `childSessionKey` y, si hace falta, `sessionId`.
6. No reciclar el ultimo resultado visible si existe riesgo de que pertenezca a un run previo, a otra sesion o a otro usuario.
7. No pedir al hijo una respuesta final bonita para el usuario si luego el padre debe sintetizar. Pedir un payload integrable.

## Arbol de decision
- Delegar con `sessions_spawn` si la tarea es lenta, pesada, paralelizable, aislable o conviene moverla a otro agente o modelo.
- No delegar con `sessions_spawn` si la respuesta debe quedar integrada en este mismo turno y no hay plan explicito de espera o integracion.
- Si se necesita respuesta integrada en el mismo turno, resolver inline o usar otro patron sincrono.
- Si se necesita fan-out y sintesis, spawnear un orquestador de nivel 1; ese orquestador spawnea workers, integra y solo entonces anuncia al padre.

## Flujo recomendado
1. decidir modo
2. spawnear con contrato claro
3. registrar trazabilidad: `label`, `runId`, `childSessionKey`
4. esperar sin cerrar en falso
5. integrar el resultado correcto
6. responder

## Frases guia
- `accepted significa arranco, no que termino`
- `si necesito respuesta integrada en este turno, no dependo de bare sessions_spawn`
- `si el resultado importa, verifico el hijo correcto antes de sintetizar`

