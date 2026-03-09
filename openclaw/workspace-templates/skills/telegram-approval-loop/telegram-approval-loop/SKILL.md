---
name: telegram-approval-loop
description: gestionar un flujo de revision editorial por telegram con shortlist, seleccion, ajustes y aprobacion explicita por etapa. usar cuando chatgpt deba enviar 5 alternativas numeradas, interpretar respuestas como "1", "1 - ajusta tal cosa", "elige 2 y 4" o "rechaza todas", mantener estado por item y version, registrar decisiones en notion o linear y evitar confundir comentarios intermedios con aprobacion final de publicacion. util para aprobacion de idea, estrategia, borrador, imagen y publicacion final.
---

Gestionar la aprobacion editorial por Telegram como una cadena de decisiones separadas. Tratar cada etapa como un contrato distinto y registrar evidencia antes de mover estado.

## Flujo canonico

Seguir este orden salvo instruccion explicita en contra:

1. Seleccionar idea.
2. Seleccionar estrategia.
3. Aprobar borrador.
4. Aprobar imagen.
5. Obtener aprobacion final de publicacion.

No colapsar etapas. Un comentario sobre una etapa posterior no aprueba automaticamente las anteriores.

## Reglas duras

- Enviar exactamente 5 alternativas numeradas para `idea` y `strategy`.
- Mantener numeracion estable dentro de la misma ronda.
- Abrir una nueva ronda si cambia el set de opciones; incrementar `round_index` y regenerar opciones `1..5`.
- Anclar cada mensaje del loop a un `item_id`, una `stage` y, si aplica, una `version`.
- Tratar un numero solo como `selection`, nunca como `approval` final.
- Tratar `1 - ajusta ...` como seleccion mas solicitud de cambios.
- Tratar `elige 2 y 4` como shortlist o multi-seleccion temporal.
- Tratar `rechaza todas` como rechazo del lote actual y generar un lote nuevo.
- Exigir aprobacion explicita y localizada para `draft`, `image` y `final-publication`.
- No inferir aprobacion final desde `ok`, `👍`, `va`, `me gusta`, `si`, `dale` o comentarios positivos equivalentes.

## Modelo de estado minimo

Mantener estado por `item_id` y por version. Usar como minimo:

- `item_id`
- `stage`: `idea`, `strategy`, `draft`, `image`, `final-publication`
- `stage_status`: `awaiting-selection`, `shortlisted`, `selected`, `changes-requested`, `approved`, `rejected`, `blocked`, `ambiguous`
- `round_index`: entero para rondas de idea o estrategia
- `active_options`: opciones vigentes para la ronda activa
- `selected_options`: una o varias opciones elegidas en la etapa actual
- `draft_version`: `v1`, `v2`, `v3`
- `image_version`: `v1`, `v2`
- `approval_scope`: `none`, `idea only`, `strategy only`, `draft vN`, `image vN`, `publication final`
- `last_user_reply_raw`: texto exacto recibido
- `last_interpreted_action`: `selection`, `adjustment`, `rejection`, `approval`, `ambiguous`
- `approval_evidence`: cita corta del mensaje, fecha y referencia
- `source_message_id`: mensaje del bot al que respondio el usuario
- `reply_message_id`: mensaje del usuario
- `next_action`

Si borrador o imagen no tienen version estable, no registrar aprobacion; fijar version primero.

## Regla de oro de aprobacion

Registrar el cambio mas conservador posible.

Interpretar por defecto asi:

- `1` => seleccion de una opcion de la etapa actual.
- `1 - ajusta tal cosa` => seleccion mas ajuste; no es aprobacion final.
- `elige 2 y 4` => shortlist o comparativa; no es aprobacion final.
- `rechaza todas` => rechazo del lote actual.
- `ok`, `dale`, `👍`, `va`, `me gusta` => senal positiva insuficiente; no marcar aprobacion final.

Registrar aprobacion solo cuando la respuesta nombra de forma clara la etapa o el artefacto:

- `apruebo la estrategia 2`
- `aprobado borrador v3`
- `aprobada imagen v2`
- `aprobado para publicar`
- `publica`

La aprobacion final de publicacion requiere una senal explicita de publicacion final. Nunca deducirla desde aprobacion de idea, estrategia, borrador o imagen.

## Reglas de transporte para Telegram

Ajustar el loop al medio, no al reves.

- Mantener cada mensaje por debajo del limite de texto de Telegram. Si el contenido excede el espacio razonable, resumir y enlazar al artefacto completo.
- Hacer una sola pregunta operativa por mensaje.
- Incluir `ITEM`, `ETAPA` y, si aplica, `VERSION` al principio.
- Anclar la respuesta al mensaje del bot usando reply context cuando exista implementacion (`reply_parameters` o equivalente). Usar `ForceReply` cuando se necesite dirigir una respuesta a un mensaje concreto.
- Permitir siempre texto libre ademas de botones. Los botones ayudan a seleccionar rapido, pero el ajuste y la aprobacion contextual deben poder escribirse en texto.
- Si se usan botones, limitar su funcion a picks rapidos como `1`, `2`, `3`, `4`, `5` y `rechaza todas`. No meter instrucciones largas en `callback_data`.
- No depender solo de inline keyboard para la aprobacion final; exigir respuesta textual o confirmacion inequívoca de `final-publication`.
- Mantener formato robusto. Preferir texto simple o markdown estable y evitar adornos que dificulten copiar o responder.

## Formato recomendado del mensaje

Usar mensajes cortos, numerados y con instruccion de respuesta concreta.

### 1) Seleccion de idea

Usar exactamente 5 alternativas numeradas.

```text
ITEM: POST-142
ETAPA: seleccion de idea
RONDA: 1
OBJETIVO: elegir el angulo del post

1. [idea 1 en una linea]
2. [idea 2 en una linea]
3. [idea 3 en una linea]
4. [idea 4 en una linea]
5. [idea 5 en una linea]

Responde con uno de estos formatos:
- `1`
- `1 - ajusta [detalle]`
- `elige 2 y 4`
- `rechaza todas`
```

### 2) Seleccion de estrategia

```text
ITEM: POST-142
ETAPA: seleccion de estrategia
RONDA: 1
IDEA ELEGIDA: 2

1. [estrategia 1]
2. [estrategia 2]
3. [estrategia 3]
4. [estrategia 4]
5. [estrategia 5]

Responde con:
- `1`
- `1 - ajusta [detalle]`
- `elige 2 y 4`
- `rechaza todas`
```

### 3) Aprobacion de borrador

Referenciar siempre version.

```text
ITEM: POST-142
ETAPA: aprobacion de borrador
BORRADOR: v3

[borrador o resumen corto]

Responde con:
- `aprobado borrador v3`
- `v3 - ajusta [detalle]`
- `rechaza borrador v3`
```

### 4) Aprobacion de imagen

```text
ITEM: POST-142
ETAPA: aprobacion de imagen
IMAGEN: v2

[link o descripcion breve]

Responde con:
- `aprobada imagen v2`
- `v2 - ajusta [detalle]`
- `rechaza imagen v2`
```

### 5) Aprobacion final de publicacion

Usar una pregunta binaria y explicita.

```text
ITEM: POST-142
ETAPA: aprobacion final de publicacion
BORRADOR APROBADO: v3
IMAGEN APROBADA: v2
CANAL: LinkedIn

¿Autorizas la publicacion final?

Responde con:
- `aprobado para publicar`
- `publica`
- `no publicar - ajusta [detalle]`
```

## Algoritmo de interpretacion

Resolver siempre en este orden:

1. Identificar la etapa activa del loop.
2. Identificar si la respuesta expresa `selection`, `adjustment`, `rejection`, `approval` o `ambiguous`.
3. Identificar si menciona opcion, objeto o version.
4. Aplicar el cambio de estado mas conservador posible.
5. Registrar evidencia.
6. Confirmar la interpretacion si hay ambiguedad.

Aplicar estas reglas:

- En `idea` o `strategy`, un numero solo significa seleccion.
- Numero mas instruccion de cambio => `changes-requested`.
- Varios numeros => `shortlisted`; pedir cierre a una sola opcion o devolver una ronda refinada.
- `rechaza todas` => `rejected`; devolver 5 alternativas nuevas.
- `aprobado borrador vN` => aprobar solo ese borrador.
- `aprobada imagen vN` => aprobar solo esa imagen.
- `publica` o `aprobado para publicar` => aprobar solo `final-publication`, y solo si el flujo anterior esta cerrado o si el item no requiere imagen por definicion.

Para patrones mas finos, consultar `references/reply-parsing.md`.

## Manejo de respuestas ambiguas

Si la respuesta no identifica con claridad la accion o el alcance, no avanzar de etapa. Registrar `ambiguous` y responder con una reformulacion minima.

Ejemplos tipicos:

- `ok`
- `me gusta mas`
- `si`
- `vamos con esa`
- `bien, pero cambia el cierre`
- emojis sin texto

Respuesta sugerida:

```text
Interpreto que quieres seguir con la opcion 2, pero no lo tomo como aprobacion final. Si quieres aprobar esta etapa responde `aprobado [etapa/objeto]`. Si quieres ajustes, responde `2 - ajusta [detalle]`.
```

Si existen dos lecturas razonables, exponer ambas y pedir confirmacion en una sola linea.

## Registrar el estado en Notion

Usar una fila por `item_id` en una data source editorial. Mantener el estado actual en propiedades y el historial en comentarios o en una tabla hija de log.

Propiedades recomendadas:

- `Item ID`
- `Working title`
- `Current stage`
- `Stage status`
- `Round index`
- `Selected idea`
- `Selected strategy`
- `Approved draft version`
- `Approved image version`
- `Final publication approval`
- `Approval scope`
- `Last Telegram reply`
- `Interpretation`
- `Approval evidence`
- `Owner`
- `Next action`

Reglas de implementacion:

- Preferir propiedades de tipo `status` o `select` para estado visible.
- Preferir IDs de propiedad en codigo de integracion si el esquema puede renombrarse.
- Guardar el texto bruto y la interpretacion de cada respuesta en comentario o log separado.
- Si la integracion no tiene capacidad de comentarios, registrar el audit trail en una tabla hija o campo de log.
- Dividir payloads largos en entradas pequenas; no intentar meter un historial enorme en una sola actualizacion.

## Registrar el estado en Linear

Usar un issue por `item_id` o por pieza editorial. Mantener el issue vivo durante todo el loop.

Recomendar:

- Usar `State` del issue para estado macro del trabajo, no para cada microdecision del loop.
- Usar labels o custom fields para `idea-approved`, `strategy-approved`, `draft-approved`, `image-approved`, `final-approved`.
- Usar comentario por cada respuesta relevante de Telegram con texto bruto, interpretacion y evidencia.
- Usar checklist o custom fields para version aprobada de borrador e imagen.
- Bloquear `ready-to-publish` hasta tener aprobacion final explicita.

Si se usa checklist, separarlo asi:

- Idea seleccionada
- Estrategia seleccionada
- Borrador aprobado
- Imagen aprobada
- Publicacion final aprobada

No marcar el ultimo punto por inferencia.

## Anti-patrones del loop por Telegram

Evitar siempre estos errores:

- Mezclar idea, estrategia y aprobacion final en un mismo mensaje.
- Enviar alternativas sin numeracion estable.
- Cambiar la numeracion en una nueva ronda sin indicar cambio de ronda.
- Reusar una aprobacion vieja para una version nueva.
- Marcar `final-approved` por un emoji, un `ok` o una reaccion.
- Perder el mensaje bruto original al registrar el estado.
- Guardar solo la interpretacion y no la evidencia.
- Mover el issue o la fila a estado final sin comentario o prueba.
- Usar botones como unica via para cambios complejos.
- Confundir `elige 2 y 4` con aprobacion de dos publicaciones.
- Tomar feedback intermedio de imagen como permiso de publicacion.

## Salida esperada al operar el loop

Al responder sobre un evento o al proponer la siguiente accion, devolver de forma explicita:

- lectura de la respuesta
- estado actualizado
- alcance aprobado real
- siguiente mensaje sugerido al usuario
- registro sugerido para notion o linear
