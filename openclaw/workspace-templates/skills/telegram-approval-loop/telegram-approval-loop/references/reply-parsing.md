# Reply parsing

## Objetivo

Traducir respuestas breves de Telegram a una accion editorial sin inflar el alcance de la decision.

## Taxonomia de acciones

- `selection`: elegir una opcion vigente de la etapa actual.
- `adjustment`: pedir cambios sobre una opcion, borrador o imagen.
- `rejection`: rechazar una o varias opciones actuales.
- `approval`: aprobar explicitamente el objeto de la etapa actual.
- `ambiguous`: respuesta util pero insuficiente para mover etapa.

## Regla de conservadurismo

Si una respuesta admite dos lecturas, elegir la menos irreversible.

- Entre `selection` y `approval`, elegir `selection`.
- Entre `adjustment` y `approval`, elegir `adjustment`.
- Entre `approval de draft` y `approval final de publicacion`, elegir `approval de draft`.
- Entre `shortlist` y `multi-approval`, elegir `shortlist`.

## Prioridad de parseo

Aplicar este orden:

1. Detectar `rechaza todas` o rechazo explicito del objeto.
2. Detectar aprobacion explicita de etapa u objeto.
3. Detectar numero unico o multi-seleccion.
4. Detectar instruccion de ajuste.
5. Si no queda claro el alcance, marcar `ambiguous`.

## Patrones frecuentes

### 1) Numero unico

Entrada:

```text
1
```

Interpretacion:

- Si la etapa activa es `idea` o `strategy`: `selection`.
- Si la etapa activa es `draft` o `image`: preferir `ambiguous` y pedir confirmacion del formato de aprobacion.
- Nunca interpretar como aprobacion final de publicacion.

### 2) Numero + ajuste

Entrada:

```text
1 - ajusta el cierre
```

Interpretacion:

- `selection` + `adjustment`
- `stage_status`: `changes-requested`
- `approval_scope`: `none`

### 3) Multi-seleccion

Entrada:

```text
elige 2 y 4
```

Interpretacion:

- shortlist de candidatos
- `stage_status`: `shortlisted`
- siguiente accion: pedir cierre a una sola opcion o devolver una ronda refinada de 2 opciones

### 4) Rechazo total

Entrada:

```text
rechaza todas
```

Interpretacion:

- `rejection`
- `stage_status`: `rejected`
- siguiente accion: generar 5 alternativas nuevas

### 5) Aprobacion explicita de estrategia

Entrada:

```text
apruebo la estrategia 2
```

Interpretacion:

- `approval`
- etapa: `strategy`
- `approval_scope`: `strategy only`
- no implica aprobacion de borrador, imagen ni publicacion final

### 6) Aprobacion explicita de borrador

Entrada:

```text
aprobado borrador v3
```

Interpretacion:

- `approval`
- etapa: `draft`
- `approval_scope`: `draft v3`
- no implica aprobacion de imagen ni publicacion final

### 7) Aprobacion explicita de imagen

Entrada:

```text
aprobada imagen v2
```

Interpretacion:

- `approval`
- etapa: `image`
- `approval_scope`: `image v2`
- no implica publicacion final

### 8) Aprobacion final de publicacion

Entrada:

```text
publica
```

o

```text
aprobado para publicar
```

Interpretacion:

- `approval`
- etapa: `final-publication`
- `approval_scope`: `publication final`
- usar solo si el contexto activo es la solicitud de autorizacion final

## Respuestas ambiguas tipicas

Tratar como `ambiguous`:

- `ok`
- `si`
- `dale`
- `va`
- `me sirve`
- `me gusta`
- `bien`
- `👍`
- `🔥`
- `vamos con esa`

Respuesta sugerida:

```text
Para registrarlo bien: si quieres aprobar esta etapa responde `aprobado [etapa/objeto]`. Si quieres cambios, responde `[id o version] - ajusta [detalle]`.
```

## Heuristicas utiles

- Si el mensaje nombra una version (`v2`, `v3`) y contiene `ajusta`, parsear como `adjustment`.
- Si el mensaje nombra una version y contiene `aprobado` o `apruebo`, parsear como `approval` del objeto nombrado.
- Si el mensaje contiene dos o mas numeros en `idea` o `strategy`, no cerrar etapa; parsear como `shortlisted`.
- Si el mensaje llega fuera del contexto de la etapa activa, pedir re-confirmacion antes de mover estado.
- Si el mensaje responde a un mensaje viejo y ya hay una ronda nueva abierta, no sobreescribir el estado activo sin confirmacion.

## Plantilla de parseo

```text
item_id: [id]
stage: [idea|strategy|draft|image|final-publication]
round_index: [n o null]
incoming_reply: "[texto bruto]"
source_message_id: [id del mensaje del bot]
reply_message_id: [id del mensaje del usuario]
interpreted_action: [selection|adjustment|rejection|approval|ambiguous]
selected_options: [ids si aplica]
approval_scope: [none|idea only|strategy only|draft vN|image vN|publication final]
status_update: [estado]
confidence: [high|medium|low]
follow_up_needed: [si/no]
follow_up_message: "[texto]"
```
