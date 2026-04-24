# CAND-003 — LinkedIn Writer Flow Variants

> **Date**: 2026-04-24
> **Agent**: rick-linkedin-writer (Run ID: 624f5a7c)
> **Model**: azure-openai-responses/gpt-5.4
> **Flow**: AEC/BIM context framing → linkedin-post-writer → rick-communication-director → rick-qa

## V-A Operativa

### LinkedIn

Automatizar una revision no sirve de mucho si el equipo todavia no definio que esta revisando.

En muchos equipos BIM, ese punto aparece antes de cualquier herramienta.

¿Que significa que un modelo esta listo para revision? ¿Que tipo de observacion obliga a rehacer? ¿Cuando un entregable puede pasar de etapa? ¿Que reporte ayuda de verdad a tomar una decision?

Si esas respuestas no estan explicitadas, la automatizacion no corrige el proceso.

Solo ejecuta mas rapido un criterio que sigue disperso entre personas, reuniones y costumbres del equipo.

La capacidad tecnologica ya existe, y cada vez mas empresas usan sistemas algoritmicos para gestionar trabajo.

Pero en la practica, el valor no aparece solo por incorporar IA.

Aparece cuando el equipo ya puso por escrito como revisar, como cerrar observaciones, como aceptar entregables y que umbrales usa para decidir.

Por eso, la preparacion real no empieza en la herramienta.

Empieza en definir criterios operativos explicitos para revision, cierre y aceptacion.

Si eso no esta claro, lo mas probable es que la automatizacion amplifique el desorden en vez de resolverlo.

En tu flujo actual, ¿que criterio sigue sin estar definido por escrito?

### X

En revision BIM, el problema no siempre es la herramienta. Suele aparecer antes: cuando nadie definio por escrito que significa "listo para revision", que observacion obliga a rehacer o que reporte sirve para decidir. Sin ese criterio, la IA acelera el desorden.

### Metrics

- LinkedIn words: 187
- X chars: 273
- Within target: yes

### Communication Director

- Naturalidad: 4/5
- Apertura: cumple (escena operativa)
- Cierre: correcto (pregunta accionable)
- Problemas: "criterios operativos explicitos" suena documental; "sistemas algoritmicos para gestionar trabajo" suena prestado de fuente

### QA

- Verdict: pass_with_changes
- Claims: ok
- Sources: ok
- Voice: minor issues
- Changes: suavizar "la capacidad tecnologica ya existe", reducir repeticion de "explicitos", ajustar "personas, reuniones y costumbres del equipo"

---

## V-B Estrategica

### LinkedIn

La conversacion sobre automatizacion suele empezar demasiado tarde.

Empieza en la herramienta, cuando deberia empezar en el criterio.

En muchos equipos, el punto critico no es si ya existe capacidad tecnologica.

El punto critico es si el equipo definio con claridad que significa que algo esta listo, que desvio obliga a intervenir, que umbral cambia una decision y que informacion realmente sirve para mover un proyecto.

Cuando eso no esta explicitado, la IA no ordena la operacion.

Puede ejecutarla mas rapido, pero no darle criterio.

Por eso, la preparacion real para automatizar no empieza en la compra, ni en la integracion, ni en el piloto.

Empieza antes.

Empieza en definir criterios operativos explicitos para revisar, cerrar observaciones, aceptar entregables y producir reportes que ayuden a decidir.

Cada vez mas empresas usan sistemas algoritmicos para gestionar trabajo.

Pero el impacto operativo no aparece solo por incorporar tecnologia.

Aparece cuando la automatizacion se apoya en reglas claras, umbrales compartidos y decisiones que el equipo ya sabe sostener.

Si eso todavia no existe, automatizar puede amplificar el desorden en lugar de resolverlo.

Antes de sumar otra capa de automatizacion, ¿que criterio clave sigue sin estar definido en tu operacion?

### X

El limite de muchas iniciativas de automatizacion no suele estar en la herramienta. Suele estar en el criterio: que significa "listo", que umbral cambia una decision y que informacion realmente sirve para actuar. Sin eso, la IA acelera la operacion, pero no la ordena.

### Metrics

- LinkedIn words: 185
- X chars: 271
- Within target: yes

### Communication Director

- Naturalidad: 2.5/5
- Apertura: floja (abstracta, no escena operativa)
- Cierre: formulado
- Problemas: "conversacion sobre automatizacion" no suena a David; "capacidad tecnologica", "impacto operativo", "umbrales compartidos" enfrían; menos AEC visible

### QA

- Verdict: blocked
- Claims: ok
- Sources: ok
- Voice: issues
- Anti-slop: issues
- Changes: bajar tono consultoria, eliminar abstraccion, rehacer apertura, reducir "Empieza... Empieza..."

---

## V-C Conversacional

### LinkedIn

Antes de automatizar algo en tu equipo, hay una pregunta más útil que "qué herramienta usamos".

La pregunta es otra: ¿ya tenemos claro qué significa que algo está suficientemente bien?

En muchos equipos, el problema no aparece por falta de tecnología.

Aparece cuando nadie definió con precisión qué revisar, cuándo una observación obliga a rehacer, cuándo un entregable puede pasar de etapa o qué reporte realmente ayuda a tomar una decisión.

La capacidad tecnológica ya existe, sí.

Pero si esos criterios siguen implícitos, la automatización no ordena el proceso. Solo ejecuta más rápido un desorden que ya estaba ahí.

Por eso, para mí, la preparación real no empieza en la herramienta.

Empieza en poner por escrito el criterio operativo que el equipo ya debería estar usando para revisar, cerrar observaciones y aceptar entregables.

Ahí suele estar la diferencia entre automatizar una mejora o amplificar la confusión.

¿Qué criterio sigue todavía "en la cabeza" de alguien en tu equipo?

### X

Antes de automatizar, conviene definir algo más básico: qué significa que un modelo, una observación o un entregable está suficientemente bien. Si ese criterio sigue implícito, la IA no ordena el proceso. Solo lo acelera. ¿Qué regla sigue todavía "en la cabeza" de alguien en tu equipo?

### Metrics

- LinkedIn words: 152
- X chars: 275
- Within target: yes (short variant, 120-200 target)

### Communication Director

- Naturalidad: 4.5/5
- Apertura: cumple (pregunta concreta)
- Cierre: muy bueno ("en la cabeza" de alguien)
- Problemas: "suficientemente bien" algo genérico; "criterio operativo" algo técnico; falta gota de BIM explícito en apertura

### QA

- Verdict: pass
- Claims: ok
- Sources: ok
- Voice: ok
- Changes: opcionalmente subir longitud a 180-260 si el rango es obligatorio; mantener claims tal cual

---

## Source trace (all versions)

| Claim | Source | Confidence |
|-------|--------|------------|
| Cada vez mas empresas usan sistemas algoritmicos para gestionar trabajo | OECD 2025 | evidencia |
| La IA no ordena el proceso. Lo puede ejecutar mas rapido | inferencia editorial | inferencia |
| El cuello de botella no es la herramienta. Es el criterio | tesis editorial | hipotesis |

## Summary

| Version | ComDir score | QA verdict | Recommended |
|---------|-------------|------------|-------------|
| V-A Operativa | 4/5 | pass_with_changes | Alternativa conservadora |
| V-B Estratégica | 2.5/5 | blocked | Necesita otra iteración |
| V-C Conversacional | 4.5/5 | pass | **Base recomendada** |

---

## Iteracion 2 — Variantes refinadas

> **Date**: 2026-04-24
> **Trigger**: V-B blocked by QA, V-C too short (152 words < 180 min), V-A minor voice issues
> **Changes**: V-B2 reescrita desde cero, V-C2 extendida con escenas BIM, V-A2 polish de naturalidad

### V-A2 Operativa pulida (185 words)

#### LinkedIn

Automatizar una revision no sirve de mucho si el equipo todavia no definio que esta revisando.

En muchos equipos BIM, ese punto aparece antes de cualquier herramienta.

¿Que significa que un modelo esta listo para revision? ¿Que tipo de observacion obliga a rehacer? ¿Cuando un entregable puede pasar de etapa? ¿Que reporte ayuda de verdad a tomar una decision?

Si esas respuestas no estan explicitadas, la automatizacion no corrige el proceso.

Solo ejecuta mas rapido un criterio que todavia cambia segun quien revise, como se converse o que practica siga cada equipo.

La capacidad tecnologica ya existe, y cada vez mas empresas incorporan sistemas para organizar y ejecutar trabajo.

Pero en la practica, el valor no aparece solo por incorporar IA.

Aparece cuando el equipo ya puso por escrito como revisar, como cerrar observaciones, como aceptar entregables y que umbrales usa para decidir.

Por eso, la preparacion real no empieza en la herramienta.

Empieza en dejar claro por escrito como se revisa, como se cierra y que se acepta.

Si eso no esta claro, lo mas probable es que la automatizacion amplifique el desorden en vez de resolverlo.

En tu flujo actual, ¿que criterio sigue sin estar definido por escrito?

#### X

En revision BIM, el problema no siempre es la herramienta. Suele aparecer antes: cuando nadie definio por escrito que significa "listo para revision", que observacion obliga a rehacer o que reporte sirve para decidir. Sin ese criterio, la IA acelera el desorden.

#### Communication Director (V-A2)

- Naturalidad: 4/5
- Mejoras vs original: mas limpia, mas consistente, flujo mas claro
- Problemas: "la capacidad tecnologica ya existe" enfria la voz; "que umbrales usa para decidir" suena analitico

#### QA (V-A2)

- Verdict: pass_with_changes
- Claims: ok
- Sources: ok (OECD claim reformulated more generically than original trace)
- Anti-slop: clean
- Lengths: LinkedIn 185 words ok, X 273 chars ok

---

### V-B2 Estrategica operativa (185 words)

#### LinkedIn

Un equipo puede tener una herramienta nueva y seguir atascado en lo mismo.

Pasa cuando nadie definio con precision si un modelo esta listo para revision, cuando una observacion obliga a rehacer, cuando un entregable puede pasar de etapa o cuando un reporte realmente sirve para decidir.

En ese punto, el problema ya no es tecnico. Es de criterio.

Por eso, la preparacion real para automatizar no empieza en la herramienta.

Empieza antes, en definir por escrito que revisa el equipo, que acepta, que devuelve y con que criterio toma una decision.

Cada vez mas empresas usan sistemas algoritmicos para gestionar trabajo.

Pero cuando esos criterios siguen implicitos, la automatizacion no corrige el proceso.

Solo ejecuta mas rapido una forma de trabajar que todavia depende de interpretaciones, conversaciones sueltas o criterio no documentado.

En equipos BIM, eso suele notarse muy rapido: revisiones que no cierran, observaciones que vuelven, entregables que avanzan sin acuerdo claro y reportes que informan, pero no ayudan a decidir.

Antes de sumar otra capa de automatizacion, conviene resolver una pregunta mas basica:

¿que tiene que estar claro para que el equipo pueda revisar, cerrar y avanzar sin ambiguedad?

#### X

Antes de automatizar, conviene cerrar algo mas basico: que significa que un modelo esta listo para revision, que observacion obliga a rehacer y que entregable puede pasar de etapa. Si ese criterio no esta escrito, la automatizacion acelera el desorden.

#### Communication Director (V-B2)

- Naturalidad: 3.5/5
- Mejoras vs original: apertura mucho mejor (situacion concreta, no marco abstracto), mas AEC/BIM visible, cierre menos consultivo
- Problemas: "sistemas algoritmicos para gestionar trabajo" suena importado de fuente; "conviene resolver una pregunta mas basica" algo distante

#### QA (V-B2)

- Verdict: pass
- Claims: ok
- Sources: ok
- Anti-slop: clean
- Voice: most balanced between thesis, operation, and claim control
- Lengths: LinkedIn 185 words ok, X 266 chars ok

---

### V-C2 Conversacional extendida (190 words)

#### LinkedIn

Antes de automatizar algo en tu equipo, hay una pregunta mas util que "que herramienta usamos".

La pregunta es otra: ¿ya tenemos claro que significa que algo esta suficientemente bien?

En muchos equipos, el problema no aparece por falta de tecnologia.

Aparece cuando nadie definio con precision que revisar, cuando una observacion obliga a rehacer, cuando un entregable puede pasar de etapa o que reporte realmente ayuda a tomar una decision.

Eso se nota rapido en lo cotidiano: un modelo que para una persona ya esta listo para revision y para otra no, observaciones que se cierran sin acuerdo real, o entregables que avanzan de etapa aunque el criterio de aceptacion siga siendo difuso.

La capacidad tecnologica ya existe, si.

Pero si esos criterios siguen implicitos, la automatizacion no ordena el proceso. Solo ejecuta mas rapido un desorden que ya estaba ahi.

Por eso, para mi, la preparacion real no empieza en la herramienta.

Empieza en poner por escrito el criterio operativo que el equipo ya deberia estar usando para revisar, cerrar observaciones y aceptar entregables.

Ahi suele estar la diferencia entre automatizar una mejora o amplificar la confusion.

¿Que criterio sigue todavia "en la cabeza" de alguien en tu equipo?

#### X

Antes de automatizar, conviene responder algo mas basico: ¿que significa que un modelo esta suficientemente bien, que una observacion obliga a rehacer y que un entregable puede pasar de etapa? Si ese criterio sigue implicito, la automatizacion acelera el desorden.

#### Communication Director (V-C2)

- Naturalidad: 4.5/5
- Mejoras vs original: mejor aterrizaje con escenas concretas, mejor ritmo visual, cierre fuerte y muy usable en voz David
- Problemas: "la capacidad tecnologica ya existe" y "criterio operativo" suenan algo documentales

#### QA (V-C2)

- Verdict: pass_with_changes
- Claims: ok
- Sources: ok
- Anti-slop: clean
- Lengths: LinkedIn 190 words ok, X 274 chars ok
- Note: "La capacidad tecnologica ya existe, si" sounds more absolute than source trace supports

---

### Iteracion 2 Summary

| Version | ComDir score | QA verdict | Status |
|---------|-------------|------------|--------|
| V-A2 Operativa pulida | 4/5 | pass_with_changes | Candidata |
| V-B2 Estrategica operativa | 3.5/5 | pass | Candidata (recuperada) |
| V-C2 Conversacional extendida | 4.5/5 | pass_with_changes | **Base recomendada** |

**Recomendacion**: V-C2 sigue siendo la mejor para David (mas natural, mejor ritmo, cierre fuerte). V-B2 recuperada tras reescritura completa. V-A2 solida como alternativa conservadora.

**Orden final QA**: V-B2 > V-A2 > V-C2 (por solidez de claims)
**Orden final ComDir**: V-C2 > V-A2 > V-B2 (por naturalidad y voz David)
**Recomendacion combinada**: V-C2 como base, V-A2 como alternativa

---

## Estado

- Dry-run: si.
- Notion editado: confirmado por run operativo 2026-04-24.
- Seccion creada: "Iteracion 2 — Variantes refinadas (2026-04-24)".
- Incluye: hardening de permisos, V-C2, V-A2, V-B2 y recomendacion.
- Publicado: no.
- Programado: no.
- Gates: intactos.
- Estado Notion: Borrador.
- Fuente set: sin cambios.
- CAND-002: no tocado.
