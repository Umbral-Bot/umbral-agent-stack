# CAND-003 V-E Architect Review Packet

> **Para**: Agente "Arquitecto de Agentes OpenClaw" (ChatGPT) con conocimiento consultivo de voz David y acceso a Notion.
> **De**: rick-linkedin-writer + rick-communication-director + rick-qa (vía Codex / Copilot CLI).
> **Date**: 2026-04-26
> **Branch**: `rick/editorial-linkedin-writer-flow` @ commit base `ee8ce34`
> **PR**: https://github.com/Umbral-Bot/umbral-agent-stack/pull/268

## Recordatorio de seguridad editorial

- **No publicar.**
- **No marcar gates.**
- **No tocar Notion en nombre de Codex/runtime.**
- **No alterar CAND-002.**
- **No agregar fuentes ni claims nuevos.**
- **No persistir benchmark humano privado.**
- **No afirmar aprobación humana.**

## Contexto mínimo

CAND-003 es la candidata editorial source-driven sobre "criterio antes que automatización en AEC/BIM". Se itero V-A → V-D3 según evidencia previa. V-D3 fue la primera con `pass` limpio en QA y se recomendó solo como base para revisión humana, no como pieza final aprobada.

Se generaron 10 alternativas nuevas (V-E01..V-E10) con direcciones diferentes, todas a partir de V-D3 como referencia (no copia). 4 necesitaron una sola corrección R1 (límite `automatizacion`). Las 10 finales pasan validación automática.

ComDir filtró Top 3 (V-E01, V-E04, V-E08). QA confirmó Top 1 técnica: **V-E01** (único `pass` limpio).

## V-D3 base (referencia)

**LinkedIn (V-D3, ~170 palabras):**

```
Si un equipo todavia no dejo claro como revisa, que acepta y que devuelve, automatizar no le va a ordenar el trabajo.

El problema aparece antes.

Aparece cuando un entregable pasa de etapa sin acuerdo claro.
Aparece cuando una observacion se cierra y despues vuelve.
Aparece cuando un reporte circula, pero no ayuda a decidir.

Eso en BIM se ve rapido.

Un modelo BIM que para una persona ya esta listo y para otra no.
Un cierre que depende de quien revise.
Una entrega que avanza aunque nadie haya dejado por escrito que se estaba aceptando.

Cada vez mas empresas ya usan este tipo de software.

Pero si esas reglas siguen repartidas entre conversaciones, costumbre y criterio de cada uno, la automatizacion solo acelera el mismo problema.

El orden no sale del software.

Sale de acordar como se revisa, cuando algo vuelve y que tiene que estar resuelto para seguir.

En tu flujo de hoy, ¿que se sigue cerrando o aprobando segun quien lo mire?
```

**X (V-D3, 245 chars):**

```
Si un equipo no dejo claro como revisa, que acepta y que devuelve, la automatizacion solo acelera el mismo problema.

Se ve cuando un modelo BIM, una observacion o un entregable cambian segun quien los revise.

¿Donde te pasa hoy?
```

## Tabla comparativa de las 10 alternativas

| ID | Direccion | LinkedIn words | X chars | automatiz | criterio | fuente |
|----|-----------|----------------|---------|-----------|----------|--------|
| V-E01 | Operativa directa | 153 | 243 | 2 | 1 | original |
| V-E02 | Pregunta central | 152 | 233 | 2 | 1 | R1 |
| V-E03 | Reflexion sobria | 166 | 238 | 2 | 1 | original |
| V-E04 | AEC/BIM mas concreto | 177 | 217 | 2 | 1 | R1 |
| V-E05 | Datos y flujo | 169 | 239 | 2 | 0 | original |
| V-E06 | Conversacional con par tecnico | 163 | 228 | 2 | 0 | original |
| V-E07 | Lider de equipo / decision | 177 | 217 | 2 | 0 | original |
| V-E08 | Anti-herramienta aislada | 175 | 241 | 1 | 0 | original |
| V-E09 | Mas breve y seca | 157 | 210 | 2 | 1 | R1 |
| V-E10 | Mas calida y humana | 170 | 240 | 2 | 0 | R1 |

## Resultados de checks automáticos

| Check | Resultado |
|-------|-----------|
| YAML parseable (10/10) | ✓ |
| LinkedIn 150–220 palabras | ✓ (post-R1: 10/10) |
| X <280 caracteres | ✓ (10/10) |
| `automatiz*` ≤ 2 | ✓ (post-R1: 10/10) |
| `criterio` ≤ 2 | ✓ (10/10) |
| `modelo` siempre con `BIM` | ✓ (10/10) |
| Blacklist (7 términos) | ✓ (0 violaciones) |
| Anti-leak benchmark privado (10 patrones) | ✓ (0 matches) |
| `source_trace` presente | ✓ (10/10) |
| `ready_for_publication: false` | ✓ (10/10) |

## Las 10 alternativas

### V-E01 — Operativa directa _(fuente: original)_

**LinkedIn:**

```
Si un entregable pasa de etapa sin acuerdo claro, el problema aparece antes de cualquier herramienta.

El equipo primero necesita acordar como revisa, que acepta, que vuelve y que puede avanzar.

Eso se nota en la operacion diaria.
Una observacion se cierra y despues regresa.
Un reporte circula, pero no alcanza para decidir.
Una aprobacion cambia segun quien revise.

Despues se ve en BIM.
Un modelo BIM que para una persona ya esta listo y para otra no.
Un cierre que depende mas de habitos sueltos que de una regla compartida.
Una entrega que sigue adelante aunque nadie dejo claro que estaba aprobado.

Cada vez mas empresas ya trabajan con software de este tipo.

Pero si esas reglas siguen repartidas entre conversaciones, costumbre y criterio de cada uno, la automatizacion solo hace mas rapido el mismo problema.

En tu flujo de hoy, ¿que se sigue cerrando, devolviendo o aprobando segun quien lo mire?
```

**X:**

```
Si un equipo no acordo como revisa, que acepta y que vuelve, la automatizacion no corrige nada. Se nota cuando una observacion se reabre, un entregable cambia de etapa sin acuerdo o un modelo BIM depende de quien lo revise. ¿Donde te pasa hoy?
```

- length_check: linkedin_words=153, x_chars=243
- changed_vs_vd3: Mas seca y operativa, con apertura en problema concreto y menos fraseo editorial, manteniendo la misma tesis central.
- source_trace: ninguna fuente nueva; reusa contexto V-D3
- ready_for_publication: False

---

### V-E02 — Pregunta central _(fuente: R1)_

**LinkedIn:**

```
¿En que momento un entregable puede pasar de etapa de verdad?

Si el equipo no tiene eso claro, automatizar llega demasiado pronto.

Lo mismo pasa con el resto del flujo: que observacion vuelve, que reporte sirve para decidir, que aprobacion se sostiene cuando la revisa otra persona.

Ahi empieza el problema.
No cuando falta software.
Cuando falta acuerdo.

Despues se ve en BIM.
Un modelo BIM que para una persona ya esta listo y para otra no.
Un cierre que cambia segun quien revise.
Una entrega que sigue adelante aunque nadie dejo claro que se estaba aceptando.

Cada vez mas empresas ya trabajan con este tipo de software.

Pero si las reglas siguen repartidas entre conversaciones, costumbre y criterio de cada uno, la automatizacion solo acelera diferencias que ya estaban en el proceso.

Antes de sumar otra capa, conviene mirar el flujo.

¿Que parte de tu revision sigue dependiendo demasiado de interpretacion?
```

**X:**

```
¿En que momento un entregable puede pasar de etapa de verdad? Si eso no esta claro, sumar software llega demasiado pronto. Se nota cuando un modelo BIM, una observacion o una aprobacion cambian segun quien revise. ¿Donde te pasa hoy?
```

- length_check: linkedin_words=152, x_chars=233
- changed_vs_vd3: Se reemplazo la mencion de automatizar en X por sumar software para cumplir el maximo combinado sin tocar la estructura ni la tesis.
- source_trace: ninguna fuente nueva; reusa contexto V-D3
- ready_for_publication: False

---

### V-E03 — Reflexion sobria _(fuente: original)_

**LinkedIn:**

```
A veces un flujo se desordena mucho antes de que falte una herramienta.

Se desordena cuando el equipo no termino de acordar como revisa, que acepta, que vuelve y que puede avanzar.

Entonces pasan cosas conocidas: un entregable cambia de etapa sin acuerdo real, una observacion se cierra y despues regresa, un reporte circula pero no alcanza para decidir.

Eso despues se vuelve visible en BIM.

Un modelo BIM que para una persona ya esta listo y para otra no.
Una revision que depende mas de quien la toma que de una regla compartida.

Cada vez mas empresas ya trabajan con este tipo de software.

Pero si esas reglas siguen repartidas entre conversaciones, costumbre y criterio de cada uno, automatizar solo mueve mas rapido la misma diferencia.

La herramienta ayuda.
El orden aparece cuando el equipo deja por escrito como revisa, cuando algo vuelve y que tiene que estar resuelto para seguir.

En tu flujo de hoy, ¿que parte sigue cambiando demasiado segun quien la revise?
```

**X:**

```
Antes de automatizar, el equipo tiene que acordar algo mas basico: como revisa, que acepta, que vuelve y que puede avanzar. Si no, un modelo BIM, una observacion o un entregable terminan cambiando segun quien los mire. ¿Donde te pasa hoy?
```

- length_check: linkedin_words=164, x_chars=241
- changed_vs_vd3: Mas pausada y observacional, con menos secuencia martillada y una idea de fondo mas sobria sobre por que el orden no sale solo de la herramienta.
- source_trace: ninguna fuente nueva; reusa contexto V-D3
- ready_for_publication: False

---

### V-E04 — AEC/BIM mas concreto _(fuente: R1)_

**LinkedIn:**

```
Si un equipo no termino de acordar como revisa, que acepta, que vuelve y que puede avanzar, automatizar no le va a resolver el flujo.

El problema aparece antes.

Aparece cuando una entrega pasa de etapa sin acuerdo claro.
Cuando una observacion se cierra y vuelve en la siguiente revision.
Cuando un reporte llega a tiempo, pero no alcanza para decidir.

Despues eso se vuelve mas visible en coordinacion BIM.

Una interferencia que alguien da por resuelta y otro vuelve a levantar.
Un modelo BIM que para una persona ya esta validado y para otra no.
Un ciclo de observaciones que se alarga porque nadie dejo claro cuando algo realmente queda cerrado.
Una aceptacion de entrega que cambia segun quien la revise.

Cada vez mas empresas ya trabajan con este tipo de software.

Pero si esas reglas siguen repartidas entre conversaciones, costumbre y criterio de cada uno, la automatizacion solo acelera la misma diferencia.

Antes de sumar mas capa encima, conviene cerrar eso primero.

En tu flujo de hoy, ¿que parte sigue dependiendo demasiado de quien revisa?
```

**X:**

```
Antes de sumar software, el equipo tiene que acordar como revisa, que acepta y que vuelve. Si no, una interferencia, un modelo BIM validado o una entrega aceptada pueden cambiar segun quien revise. ¿Donde te pasa hoy?
```

- length_check: linkedin_words=177, x_chars=217
- changed_vs_vd3: Se reemplazo la mencion de automatizar en X por sumar software para cumplir el maximo combinado sin tocar la estructura ni la tesis.
- source_trace: ninguna fuente nueva; reusa contexto V-D3
- ready_for_publication: False

---

### V-E05 — Datos y flujo _(fuente: original)_

**LinkedIn:**

```
Un reporte puede estar completo y aun asi no ayudar a decidir.

Pasa cuando el equipo no termino de acordar como revisa, que acepta, que vuelve y que puede avanzar.

Ahi los datos empiezan a perder valor dentro del flujo.
Circula informacion, pero no cierra decisiones.
Se marca una observacion, pero no queda claro si obliga a rehacer.
Se libera un entregable, pero nadie sabe con la misma vara por que paso de etapa.

Despues eso se hace visible en BIM.
Un modelo BIM que para una persona ya esta listo y para otra no.
Un reporte de revision que enumera problemas, pero no deja claro que sigue.
Un cierre que cambia segun quien lo mire.

La herramienta suma, claro.
Tambien suma tener mas datos.

Pero si las reglas de revision no estan acordadas, la automatizacion solo mueve mas rapido la misma ambiguedad.

Cuando esa base existe, los reportes ayudan de verdad y decidir pesa menos.

En tu equipo, ¿que informacion circula mucho pero todavia ayuda poco a decidir?
```

**X:**

```
Mas datos no alcanzan si el equipo no acordo como revisa, que acepta y que vuelve. Si no, un reporte, una observacion o un modelo BIM pueden decir cosas distintas segun quien los lea. La automatizacion solo acelera eso. ¿Donde te pasa hoy?
```

- length_check: linkedin_words=154, x_chars=246
- changed_vs_vd3: Desplaza el foco hacia datos, reportes y flujo de informacion como apoyo real a la decision solo cuando la revision ya esta acordada.
- source_trace: ninguna fuente nueva; reusa contexto V-D3
- ready_for_publication: False

---

### V-E06 — Conversacional con par tecnico _(fuente: original)_

**LinkedIn:**

```
Che, esto pasa mas seguido de lo que parece: se suma una herramienta nueva y el flujo sigue igual de enredado.

No porque el software no sirva, sino porque el equipo todavia no acordo como revisa, que acepta, que vuelve y que puede avanzar.

Entonces empiezan las discusiones de siempre.
Un entregable que para uno ya puede pasar.
Una observacion que alguien cierra y otro devuelve.
Un reporte que llega, pero no alcanza para tomar la decision.

Y despues eso se ve clarisimo en BIM.
Un modelo BIM que para una persona ya esta listo y para otra no.
Un cierre que depende mas de quien revisa que de una regla compartida.
Una entrega que cambia de estado segun quien la mire.

Ahi la automatizacion no ordena por si sola.
Primero hay que dejar esa base acordada.

Con esa base, la herramienta suma de verdad.

Si te toca sostener esa revision en tu equipo, ¿que parte del flujo sigue demasiado abierta a interpretacion?
```

**X:**

```
Che, esto pasa seguido: si el equipo no acordo como revisa, que acepta y que vuelve, la automatizacion no ordena sola. Se nota cuando un modelo BIM, una observacion o una entrega cambian segun quien los mire. ¿Donde te pasa hoy?
```

- length_check: linkedin_words=162, x_chars=239
- changed_vs_vd3: Toma un tono mas de par tecnico, con una apertura conversacional moderada y foco en la conversacion real entre quienes sostienen la revision.
- source_trace: ninguna fuente nueva; reusa contexto V-D3
- ready_for_publication: False

---

### V-E07 — Lider de equipo / decision _(fuente: original)_

**LinkedIn:**

```
Cuando nadie tiene claro quien decide si algo avanza, vuelve o se acepta, el problema aparece antes de automatizar.

Primero el equipo tiene que acordar como revisa, que acepta y que vuelve.

Pasa en lo diario.
Un entregable queda en pausa porque nadie quiere cerrar la decision.
Una observacion vuelve aunque ya se habia dado por resuelta.
Un reporte llega, pero no alcanza para decidir el siguiente paso.

Despues eso se hace visible en BIM.
Un modelo BIM que para una persona ya esta listo y para otra no.
Una interferencia que alguien considera cerrada y otro devuelve.
Una entrega que cambia de estado segun quien la revise.

Cada vez mas empresas ya trabajan con este tipo de software.

Pero si esas reglas siguen dispersas, el flujo cambia segun quien tome la ultima decision.

La herramienta puede ayudar.
Lo que ordena de verdad es saber quien decide, con que base y en que momento.

Si hoy te toca tomar esa decision en tu equipo, ¿que parte del flujo te sigue llegando sin una base clara para decidir?
```

**X:**

```
Si nadie tiene claro quien decide si algo avanza, vuelve o se acepta, automatizar llega demasiado pronto. Se nota cuando un modelo BIM, una observacion o una entrega cambian segun quien los revise. ¿Donde te pasa hoy?
```

- length_check: linkedin_words=162, x_chars=226
- changed_vs_vd3: Mueve el foco desde la regla general hacia quien toma la decision de avance, devolucion o aceptacion, para abrir conversacion entre lideres de equipo.
- source_trace: ninguna fuente nueva; reusa contexto V-D3
- ready_for_publication: False

---

### V-E08 — Anti-herramienta aislada _(fuente: original)_

**LinkedIn:**

```
Una herramienta sola no ordena un flujo que el equipo todavia no termino de acordar.

Si no esta claro como se revisa, que se acepta, que vuelve y que puede avanzar, el problema sigue donde estaba.

Se nota en la operacion diaria.
Un entregable cambia de etapa sin acuerdo claro.
Una observacion se cierra y vuelve en la siguiente revision.
Un reporte llega, pero no alcanza para decidir.

Despues eso se vuelve mas visible en BIM.
Un modelo BIM que para una persona ya esta listo y para otra no.
Una interferencia que alguien da por resuelta y otro devuelve.
Una entrega que cambia de estado segun quien la revise.

Por eso no se trata de estar contra la tecnologia.
Cuando esas reglas existen, el software ayuda de verdad: ordena la revision, sostiene el cierre y hace mas consistente la decision.

Pero si el equipo no acordo esa base, la automatizacion solo acelera diferencias que ya estaban en el proceso.

En tu flujo de hoy, ¿que parte mejoraria de verdad si primero dejaran eso resuelto?
```

**X:**

```
Una herramienta sola no ordena nada si el equipo no acordo como revisa, que acepta y que vuelve. Se nota cuando un modelo BIM, una observacion o una entrega cambian segun quien revise. Con reglas claras, el software suma. ¿Donde te pasa hoy?
```

- length_check: linkedin_words=175, x_chars=249
- changed_vs_vd3: Hace explicita la tension herramienta aislada vs acuerdo del equipo, sin tono anti-tecnologia y con un mecanismo mas claro de por que el software sirve cuando ya hay reglas.
- source_trace: ninguna fuente nueva; reusa contexto V-D3
- ready_for_publication: False

---

### V-E09 — Mas breve y seca _(fuente: R1)_

**LinkedIn:**

```
Si el equipo no acordo como revisa, que acepta, que vuelve y que puede avanzar, automatizar no le va a ordenar nada.

El problema aparece antes.

Un entregable pasa de etapa sin acuerdo claro.
Una observacion se cierra y despues vuelve.
Un reporte circula, pero no alcanza para decidir.

Tambien aparece cuando nadie termina de definir que tiene que quedar resuelto para seguir.

Despues eso se ve en BIM.

Un modelo BIM que para una persona ya esta listo y para otra no.
Un cierre que cambia segun quien revise.
Una entrega que sigue adelante aunque nadie dejo claro que estaba aceptando.

La herramienta puede ayudar.

Pero si esas reglas siguen repartidas entre conversaciones, costumbre y criterio de cada uno, la automatizacion solo hace mas rapido el mismo desorden.

Primero hay que ordenar esa base.
Y dejar menos cosas libradas a interpretacion.

En tu flujo de hoy, ¿que se sigue cerrando o aprobando segun quien lo mire?
```

**X:**

```
Si el equipo no acordo como revisa, que acepta y que vuelve, eso solo acelera el mismo desorden. Se nota cuando un modelo BIM, una observacion o un entregable cambian segun quien los revise. ¿Donde te pasa hoy?
```

- length_check: linkedin_words=157, x_chars=210
- changed_vs_vd3: Se sumaron dos frases breves para llevar LinkedIn al rango pedido y se reemplazo la mencion de automatizacion en X para cumplir el maximo combinado sin cambiar la tesis.
- source_trace: ninguna fuente nueva; reusa contexto V-D3
- ready_for_publication: False

---

### V-E10 — Mas calida y humana _(fuente: R1)_

**LinkedIn:**

```
Cuando un flujo no esta claro, alguien del equipo siempre termina cargando con esa duda.

La persona que no sabe si un entregable ya puede avanzar.
La que cierra una observacion y despues la vuelve a ver abierta.
La que recibe un reporte y aun asi no tiene base suficiente para decidir.

Por eso, antes de automatizar, el equipo necesita acordar algo mas basico: como revisa, que acepta, que vuelve y que puede avanzar.

Despues eso se nota mucho en BIM.
Un modelo BIM que para una persona ya esta listo y para otra no.
Una entrega que cambia de estado segun quien la revise.
Un cierre que depende mas de habitos sueltos que de una regla compartida.

La herramienta puede ayudar, claro.
Pero si esa base no esta acordada, la automatizacion solo hace mas rapido el mismo desgaste.

Cuando el equipo deja eso claro, el software acompaña mejor la revision, el cierre y la decision.

En tu flujo de hoy, ¿donde sientes mas esa carga al revisar o aprobar?
```

**X:**

```
Cuando el flujo no esta claro, alguien del equipo siempre carga con esa duda. Si no acuerdan como revisan, que aceptan y que vuelve, eso solo acelera ese desgaste. Se nota en un modelo BIM, una observacion o una entrega. ¿Donde te pasa hoy?
```

- length_check: linkedin_words=170, x_chars=242
- changed_vs_vd3: Se reemplazo la mencion de automatizacion en X por una referencia mas breve para cumplir el maximo combinado sin tocar la estructura ni la tesis.
- source_trace: ninguna fuente nueva; reusa contexto V-D3
- ready_for_publication: False

---

## Communication Director — Top 5

```yaml
```yaml
evaluations:
  - variant_id: V-E01
    voz_david_score: 4
    naturalidad_score: 4
    subformato_apropiado: true
    ritmo_movil: 4
    aterrizaje_operativo: 5
    baja_abstraccion: 5
    claim_risk: medium
    benchmark_proximity: medium
    merece_arquitecto: true
    microedits_propuestos:
      - "Cambiar `que puede avanzar` por `que puede pasar de etapa` o `que puede seguir` para cerrar mejor la logica operativa."
      - "Revisar `Cada vez mas empresas ya trabajan con software de este tipo` porque suena algo injertado y baja naturalidad."
    veredicto: pass_with_microedits
    notas: "Es la mas estable en tesis y aterrizaje. Buena apertura, buen contexto antes de BIM y cierre conversacional. La unica friccion real es una linea de contexto externo algo fria y una formulacion operativa mejorable."
  - variant_id: V-E03
    voz_david_score: 3
    naturalidad_score: 3
    subformato_apropiado: true
    ritmo_movil: 4
    aterrizaje_operativo: 4
    baja_abstraccion: 3
    claim_risk: medium
    benchmark_proximity: medium
    merece_arquitecto: false
    microedits_propuestos:
      - "Revisar `A veces un flujo se desordena mucho antes de que falte una herramienta` porque abre mas abstracto y menos operativo."
      - "Revisar `automatizar solo mueve mas rapido la misma diferencia` porque suena raro y poco natural."
      - "Revisar `La herramienta ayuda. El orden aparece...` porque queda algo formulado y cercano a cierre doctrinal."
    veredicto: needs_rework
    notas: "Tiene sobriedad, pero se va mas a reflexion que a escena viva. La tesis se entiende, aunque pierde fuerza de voz y cae un poco en formulacion explicativa."
  - variant_id: V-E04
    voz_david_score: 4
    naturalidad_score: 4
    subformato_apropiado: true
    ritmo_movil: 4
    aterrizaje_operativo: 5
    baja_abstraccion: 5
    claim_risk: medium
    benchmark_proximity: medium
    merece_arquitecto: true
    microedits_propuestos:
      - "Cambiar `la automatizacion solo acelera la misma diferencia` por una formulacion mas natural, porque `misma diferencia` suena poco oral."
      - "Cambiar `Antes de sumar mas capa encima` por una frase mas limpia, porque esa construccion suena forzada."
    veredicto: pass_with_microedits
    notas: "Muy buen aterrizaje AEC/BIM y mejor uso de interferencia y coordinacion. La estructura funciona bien, pero hay dos giros de lenguaje que le quitan naturalidad."
  - variant_id: V-E07
    voz_david_score: 3
    naturalidad_score: 3
    subformato_apropiado: true
    ritmo_movil: 4
    aterrizaje_operativo: 4
    baja_abstraccion: 4
    claim_risk: medium
    benchmark_proximity: low
    merece_arquitecto: false
    microedits_propuestos:
      - "Revisar el eje `quien decide` porque mueve la premisa desde reglas de revision hacia autoridad y toma de decision."
      - "Revisar `Lo que ordena de verdad es saber quien decide, con que base y en que momento` porque se acerca a cierre de liderazgo, no al problema operativo base."
    veredicto: needs_rework
    notas: "Tiene escenas utiles, pero se desplaza de la tesis aprobada hacia gobierno de decision. No suena mal, pero ya es otra pieza."
  - variant_id: V-E08
    voz_david_score: 4
    naturalidad_score: 4
    subformato_apropiado: true
    ritmo_movil: 4
    aterrizaje_operativo: 4
    baja_abstraccion: 4
    claim_risk: medium
    benchmark_proximity: medium
    merece_arquitecto: true
    microedits_propuestos:
      - "Revisar `Por eso no se trata de estar contra la tecnologia` porque introduce una defensa innecesaria y algo consultiva."
      - "Revisar `ordena la revision, sostiene el cierre y hace mas consistente la decision` porque suena mas redactado que hablado."
    veredicto: pass_with_microedits
    notas: "Buena pieza, clara y util, con buen ritmo movil. Funciona mejor cuando habla de escenas concretas; pierde un poco de voz cuando entra a justificar que no esta contra la tecnologia."
ranking_top3_para_qa: [V-E01, V-E04, V-E08]
recomendacion_general: "Llevar a QA primero V-E01. Es la mas cercana a la voz de David con mejor equilibrio entre apertura natural, operacion diaria, BIM como aterrizaje y cierre conversacional. V-E04 va segunda si quieren mas densidad AEC/BIM. V-E08 sirve como tercera opcion, pero conviene limpiarle la parte defensiva sobre tecnologia."
no_publicar: true
no_gates: true
no_notion: true
```
```

## QA — Top 3

```yaml
qa_results:
  - variant_id: V-E01
    claims_check: ok
    source_trace_check: ok
    blacklist_check: ok
    modelo_bim_check: ok
    length_linkedin: 153
    length_x: 243
    benchmark_proximity: low
    not_published: true
    gates_intact: true
    notion_unchanged: true
    ready_for_publication: false
    veredicto: pass
    notas: "No agrega claims nuevos, no cita referentes como autoridad y mantiene bien la tesis source-driven. La apertura es operativa, el contexto baja a escenas concretas y el cierre conversa sin moralizar. La frase OECD queda generalizada, pero sigue dentro del marco aprobado y no rompe trazabilidad."
  - variant_id: V-E04
    claims_check: ok
    source_trace_check: ok
    blacklist_check: ok
    modelo_bim_check: ok
    length_linkedin: 177
    length_x: 217
    benchmark_proximity: low
    not_published: true
    gates_intact: true
    notion_unchanged: true
    ready_for_publication: false
    veredicto: pass_with_changes
    notas: "Sigue trazabilidad y no mete fuentes nuevas, pero en voz queda un poco mas construida que V-E01. Frases como `mas visible en coordinacion BIM`, `la misma diferencia` y `sumar mas capa encima` suenan menos naturales y un poco mas de taller que de David. No rompe reglas, pero no es la mas fina."
  - variant_id: V-E08
    claims_check: issue
    source_trace_check: ok
    blacklist_check: ok
    modelo_bim_check: ok
    length_linkedin: 175
    length_x: 241
    benchmark_proximity: low
    not_published: true
    gates_intact: true
    notion_unchanged: true
    ready_for_publication: false
    veredicto: pass_with_changes
    notas: "No mete fuentes nuevas ni cita personas, pero introduce una formulacion mas afirmativa que el trace base: `cuando esas reglas existen, el software ayuda de verdad: ordena la revision, sostiene el cierre y hace mas consistente la decision`. Eso ya no es solo la tesis original, sino una promesa adicional. La voz es buena, pero el claim se ensancha."
recomendacion_para_arquitecto: [V-E01, V-E04, V-E08]
top1_tecnica: V-E01
no_publicar: true
no_gates: true
no_notion: true
```

## Recomendación al Arquitecto

**Top 3 sugeridas para tu evaluación:**

1. **V-E01 (Operativa directa)** — top 1 técnica. `pass` limpio QA, ComDir 4/5 voz David. Microedits opcionales (línea OECD; "que puede avanzar" → "que puede pasar de etapa").
2. **V-E04 (AEC/BIM más concreto)** — más densidad BIM (interferencia, ciclo de observaciones). Microedits recomendados ("la misma diferencia"; "sumar mas capa encima").
3. **V-E08 (Anti-herramienta aislada)** — tensión herramienta vs proceso. Microedición necesaria si se selecciona (recortar promesa que ensancha el claim base).

**Descartadas por ComDir** (necesitan rework, no recomendadas para esta ronda): V-E03 (sobreexplica), V-E07 (desplaza tesis a "quién decide").

**No filtradas** (disponibles si quieres ampliar el set): V-E02, V-E05, V-E06, V-E09, V-E10. Todas pasan validación automática y tienen ángulo distintivo.

## Preguntas específicas para el Arquitecto

1. **Voz David**: ¿V-E01 es lo suficientemente cercana a la voz de David como para sostenerse sin microedición humana, o conviene aplicar las microedits de ComDir antes de mandar a David?
2. **Densidad BIM**: ¿V-E04 ofrece mejor servicio a la audiencia BIM coordinadora pese a su voz más construida que V-E01?
3. **Claim discipline**: ¿La línea de V-E08 sobre "el software ayuda de verdad: ordena la revisión, sostiene el cierre…" cruza la frontera de promesa que la pieza source-driven no debería hacer? ¿O es sostenible?
4. **Benchmark privado**: ¿Alguna de las 10 alternativas se acerca peligrosamente al benchmark humano privado de David, según tu conocimiento? (Anti-leak automático no detectó patrones, pero el benchmark abstracto solo puedes evaluarlo tú.)
5. **Estado en Notion**: V-D3 no estaba reflejada en Notion como draft activo según revisión externa, y los gates Notion seguían desmarcados. ¿Recomiendas que tú/Rick reflejes el set V-E como variantes candidatas en la página de CAND-003 antes de la decisión humana? ¿O esperar a que David elija primero?
6. **Más rondas**: ¿Necesitas que se genere una ronda V-F enfocada en algún ángulo específico (por ejemplo, mezcla operativa V-E01 + densidad BIM V-E04)?

## Recomendación de qué revisar en Notion

- Verificar que CAND-003 sigue en estado `Borrador` y que ningún gate de aprobación está marcado.
- Si quieres registrar este paquete como input al ciclo editorial, sugerimos:
  - Página: CAND-003 (Control Room → editorial pipeline).
  - Bloque: agregar entrada en historial con link a este archivo (`docs/ops/cand-003-ve-architect-review-packet.md`) y al PR #268.
  - **No** marcar `aprobado_contenido`.
  - **No** marcar `autorizar_publicacion`.
- Confirmar que el draft activo en Notion sigue siendo V-C2/V-D? como estaba antes — Codex no actualizó nada.

## Notas finales

- Benchmark humano privado: no usado, no copiado, no persistido. Solo señal de riesgo abstracta.
- Reglas persistentes: no modificadas (writer/ComDir/QA/CALIBRATION/skills/evals).
- Tests editoriales del repo: corridos como smoke estructural (ver evidence doc).
- Esta es entrega para revisión consultiva, no decisión final.
