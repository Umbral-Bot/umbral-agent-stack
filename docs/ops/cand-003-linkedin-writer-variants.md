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

## Estado

- Dry-run: sí.
- Notion editado: no (pending).
- Publicado: no.
- Gates: intactos.
- Fuente set: sin cambios.
- CAND-002: no tocado.
