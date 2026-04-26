# CAND-003 V-E Publication Options Run Evidence

> **Date**: 2026-04-26
> **Branch**: `rick/editorial-linkedin-writer-flow`
> **Commit base**: `ee8ce34` (V-D3 final microedit run)
> **Model**: azure-openai-responses/gpt-5.4 (default)
> **Writer**: rick-linkedin-writer (CAL-LW-001..009 hardened)
> **ComDir**: rick-communication-director (CAL-001..006)
> **QA**: rick-qa
> **Operator**: Codex / Copilot CLI

## Objective

Generar y validar 10 alternativas nuevas (V-E01..V-E10) de publicación LinkedIn/X para CAND-003 a partir de V-D3 como base técnica limpia, con trazabilidad suficiente para que después el agente "Arquitecto de Agentes OpenClaw" las evalúe.

**No publicación. No gates. No Notion. No merge. No alteración de CAND-002.**

## Constraints respected

- Notion: not changed
- Gates: not changed
- Publication: none
- CAND-002: not altered
- Sources: no new sources added
- Claims: no new claims added
- Human approval: not asserted
- Benchmark privado: no usado, no copiado, no persistido (señal de riesgo abstracta solamente)
- Persistent rules: not modified

## Runtime live verification

Verificado por diff repo-vs-live (silentes = idénticos):

- `~/.openclaw/openclaw.json` — present
- `~/.openclaw/workspaces/rick-linkedin-writer/{ROLE.md,skills/linkedin-post-writer/{SKILL.md,CALIBRATION.md,LINKEDIN_WRITING_RULES.md}}` — match repo
- `~/.openclaw/workspaces/rick-communication-director/skills/director-comunicacion-umbral/{SKILL.md,CALIBRATION.md}` — match repo
- `~/.openclaw/workspaces/rick-qa/` — present (skills directory mountado)

Sin desalineación detectada entre repo y runtime live.

## Evidence read

- `docs/ops/cand-003-vd3-final-microedit-run.md`
- `docs/ops/cand-003-vd2-benchmark-calibration-run.md`
- `docs/ops/cand-003-vd1-post-hardening-run.md`
- `docs/ops/cand-003-linkedin-writer-variants.md`
- `docs/ops/cand-003-payload.md`
- `docs/ops/cand-003-rick-qa-v6-1-result.md`
- `docs/ops/cand-003-notion-draft-result.md`
- `openclaw/workspace-templates/skills/linkedin-post-writer/{SKILL.md,CALIBRATION.md,LINKEDIN_WRITING_RULES.md}`
- `openclaw/workspace-agent-overrides/rick-linkedin-writer/ROLE.md`
- `openclaw/workspace-templates/skills/director-comunicacion-umbral/{SKILL.md,CALIBRATION.md}`
- `evals/editorial/gold-set-minimum.yaml`
- `tests/test_editorial_gold_set.py`

## Commands executed (resumen)

```
git status --short
git fetch origin main rick/editorial-linkedin-writer-flow
git checkout rick/editorial-linkedin-writer-flow
git pull --ff-only
git log --oneline -8
diff (6 live-vs-repo)
openclaw agent --agent rick-linkedin-writer  (10 alternativas + 4 R1)
openclaw agent --agent rick-communication-director  (Top 5)
openclaw agent --agent rick-qa  (Top 3)
python3 (validate.py + validate_r1.py + consolidate.py + render_*.py)
git diff --check HEAD
```

## Matriz de 10 alternativas (direcciones)

| ID | Direccion | Foco |
|----|-----------|------|
| V-E01 | Operativa directa | Más seca, sin frase editorial |
| V-E02 | Pregunta central | Pregunta como eje |
| V-E03 | Reflexión sobria | Pausada, sin moraleja |
| V-E04 | AEC/BIM más concreto | Más ejemplos coordinación BIM |
| V-E05 | Datos y flujo | Reportes, datos, decisión |
| V-E06 | Conversacional con par técnico | BIM manager / líder técnico |
| V-E07 | Líder de equipo / decisión | Quién decide si avanza |
| V-E08 | Anti-herramienta aislada | Tensión herramienta vs proceso |
| V-E09 | Más breve y seca | 145–175 palabras |
| V-E10 | Más cálida y humana | Personas detrás del flujo |

## Validación automática

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

**Resumen del primer pase**:

- 6 alternativas pass directo: V-E01, V-E03, V-E05, V-E06, V-E07, V-E08
- 4 alternativas necesitaron 1 corrección R1 por superar el límite de `automatizacion` o quedar fuera de rango de longitud:
  - V-E02 (aut=3 → R1: aut=2)
  - V-E04 (aut=3 → R1: aut=2)
  - V-E09 (aut=3, words=136 → R1: aut=2, words=157)
  - V-E10 (aut=3 → R1: aut=2)
- 0 alternativas rechazadas por blacklist o leak de benchmark

Checks aplicados (script `/tmp/cand003ve/validate.py`, no persistido):

- LinkedIn 150–220 palabras
- X <280 caracteres
- `automatiz*` ≤ 2
- `criterio` ≤ 2
- `modelo` siempre seguido de `BIM`
- Blacklist: `herramientas algoritmicas de gestion`, `sistemas algoritmicos para gestionar trabajo`, `capacidad tecnologica`, `criterio operativo`, `umbrales`, `amplificar la confusion`, `impacto operativo`
- Anti-leak: 10 patrones del benchmark privado
- YAML parseable
- `source_trace` presente
- `ready_for_publication: false`

## Prompt operativo (resumen)

Cada alternativa fue generada con:

```
openclaw agent --agent rick-linkedin-writer --message <prompt> --thinking medium --timeout 360
```

El prompt incluyó: instrucción de leer ROLE/CALIBRATION/SKILL/LINKEDIN_WRITING_RULES, V-D3 como referencia (no copiar), tesis central, dirección específica, restricciones de longitud y vocabulario, blacklist, prohibición de fuentes/claims nuevos, y formato YAML estructurado de salida.

Prompts persisten temporalmente en `/tmp/cand003ve/prompt_V-E*.txt` y se eliminan en Phase 12.

## Alternativas normalizadas (raw output procesado)

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

## Ranking técnico interno (10 dimensiones)

Evaluación abstracta sin uso de benchmark privado. Escala 1–5 por dimensión:

| ID | claridad tesis | naturalidad | baja abstracción | contexto antes BIM | ejemplos operativos | distancia V-D3 | voz David probable | claim discipline | ritmo móvil | cierre | total |
|----|----|----|----|----|----|----|----|----|----|----|------|
| V-E01 | 5 | 4 | 5 | 5 | 5 | 4 | 4 | 5 | 4 | 5 | 46 |
| V-E02 | 4 | 4 | 4 | 4 | 4 | 5 | 4 | 5 | 4 | 4 | 42 |
| V-E03 | 4 | 3 | 3 | 5 | 4 | 4 | 3 | 5 | 4 | 3 | 38 |
| V-E04 | 5 | 4 | 5 | 5 | 5 | 4 | 4 | 4 | 4 | 4 | 44 |
| V-E05 | 4 | 4 | 3 | 5 | 4 | 5 | 4 | 5 | 4 | 4 | 42 |
| V-E06 | 4 | 4 | 4 | 4 | 4 | 4 | 3 | 5 | 4 | 4 | 40 |
| V-E07 | 4 | 4 | 4 | 4 | 5 | 4 | 3 | 4 | 4 | 4 | 40 |
| V-E08 | 5 | 4 | 4 | 5 | 4 | 4 | 4 | 3 | 4 | 4 | 41 |
| V-E09 | 5 | 4 | 4 | 4 | 4 | 3 | 4 | 5 | 4 | 4 | 41 |
| V-E10 | 4 | 4 | 3 | 5 | 4 | 5 | 3 | 4 | 4 | 4 | 40 |

**Top 5 técnico** (pasa a ComDir): V-E01, V-E04, V-E08, V-E03, V-E07

(Se eligió diversidad de ángulos: operativa directa + concreción BIM + tensión herramienta vs proceso + reflexión sobria + decisión.)

## Communication Director — Top 5

Output completo del director-comunicacion-umbral (rick-communication-director):

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

**ComDir Top 3 → QA**: V-E01, V-E04, V-E08
**ComDir descartó (needs_rework)**: V-E03, V-E07

## QA — Top 3

Output del rick-qa:

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

**QA Top 1 técnica**: V-E01 (único `pass` limpio)
**QA pass_with_changes**: V-E04, V-E08

## Recomendación para revisión del Arquitecto

Llevar las 3 finalistas a "Arquitecto de Agentes OpenClaw":

1. **V-E01 (Operativa directa)** — top 1 técnica. `pass` limpio en QA. Mejor equilibrio apertura operativa + escenas concretas + BIM como aterrizaje + cierre conversacional. ComDir: pass_with_microedits (línea OECD un poco fría; "que puede avanzar" → "que puede pasar de etapa").
2. **V-E04 (AEC/BIM más concreto)** — `pass_with_changes` en QA. Mejor densidad AEC/BIM (interferencia, ciclo de observaciones). ComDir señala "la misma diferencia" y "sumar mas capa encima" como giros poco orales.
3. **V-E08 (Anti-herramienta aislada)** — `pass_with_changes` en QA. Bien estructurada, pero introduce promesa adicional ("ordena la revisión, sostiene el cierre y hace más consistente la decisión") que ensancha levemente el claim base. Requiere microedición para no superar trazabilidad de V-D3.

## Alternativas descartadas y por qué

- **V-E03 (Reflexión sobria)**: ComDir `needs_rework` por exceso de reflexión sobre escena viva. Voz David 3/5.
- **V-E07 (Líder de equipo)**: ComDir `needs_rework` por desplazar la tesis hacia "quién decide" / autoridad, alejándose del marco aprobado de "reglas de revisión".
- **V-E02, V-E05, V-E06, V-E09, V-E10**: Quedaron fuera del Top 5 técnico por diversidad de ángulos elegida; todas son válidas y disponibles si el Arquitecto quiere otra ronda.

## ¿Requiere microedición humana?

- V-E01: microedición opcional ("que puede avanzar" → "que puede pasar de etapa"; suavizar línea OECD).
- V-E04: microedición recomendada ("la misma diferencia"; "sumar mas capa encima").
- V-E08: microedición necesaria si se selecciona ("ordena la revisión, sostiene el cierre…" recortar para no ensanchar claim).

## ¿Requiere nueva ronda técnica?

No. El problema en las finalistas es matiz de voz y micro-naturalidad, no claim/fuente/blacklist. Recomendado pasar a revisión del Arquitecto.

## Qué NO se hizo

- No se modificó Notion.
- No se cambiaron gates.
- No se publicó nada.
- No se alteró CAND-002.
- No se agregaron fuentes ni claims.
- No se persistió el benchmark humano privado.
- No se modificaron reglas persistentes (writer/ComDir/QA/CALIBRATION/skills/evals).
- No se hizo merge.
- No se afirmó aprobación humana.

## Anti-leak verification

Script anti-leak (`/tmp/cand003ve/validate.py`, no persistido) buscó **10 patrones distintivos del benchmark humano privado** en archivos nuevos/modificados. Las cadenas literales NO se reproducen en este documento por política (anti-leak self-reference).

**Resultado**: clean. Cero matches en las 10 alternativas y cero matches en los 2 archivos nuevos de evidencia, una vez aplicada la sanitización de self-reference.

## Temporales

Creados durante la ejecución (luego eliminados en Phase 12):

- `/tmp/cand-003-ve01..10-writer.txt` (raw outputs writer)
- `/tmp/cand-003-ve02_r1..ve10_r1-writer.txt` (R1 fixes)
- `/tmp/cand-003-ve-shortlist-comdir.txt` (ComDir Top 5)
- `/tmp/cand-003-ve-shortlist-qa.txt` (QA Top 3)
- `/tmp/cand003ve/` (prompts, validador, consolidador, renders)

## Qué quedó no verificado

- Benchmark humano privado de David: por política, no se usó ni se reconstruyó. Su match real sólo puede confirmarlo el Arquitecto + David.
- Posible apreciación humana de tono/calidez David sobre V-E04 / V-E08: no se asume, queda para revisión humana.
- Reacción de audiencia AEC/BIM real: fuera de scope técnico.
