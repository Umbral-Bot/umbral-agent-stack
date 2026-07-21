# Ola 3 — Editorial × Rick: 5 pitches de blog seleccionables (2026-07-20)

> Estado: **`OLA3_EDITORIAL_PITCHES_READY` (candidato)** — entregable docs-only.
> **No** amplía a borradores completos, **no** publica, **no** abre gates humanos,
> **no** escribe en Notion ni Azure, **no** activa runtime.
> Base en `main`: **`136a1a47`** (PR #544 — Ola 2, contención stage9c/stage8
> fail-closed; esos guards **no** se tocan).
> Gate de cierre de la ola: `OLA3_EDITORIAL_PITCHES_READY` → luego **GO humano**
> de ampliación (David elige; solo entonces se amplían las elegidas).

## Alcance y reglas aplicadas

- Canal sugerido para los 5: **blog** (pieza de autoridad evergreen conectada a
  pain-points reales — `docs/68-editorial-phase-1-manual.md` §2 y §7).
- Formato: shortlist humana §6 de `docs/68-editorial-phase-1-manual.md`, ampliado
  con los campos 1–8 del GO de Ola 3.
- Contenido: **tesis única** por pitch, sin hype, sin pitch comercial. Se prefieren
  claims verificables; lo demás va marcado **"opinión / pendiente de fuente
  primaria"**. **No** se inventan URLs, cifras ni datos de clientes.
- Estos son **pitches**, no copy: no hay draft de blog ni de LinkedIn/X.
- Smoke del pipeline (FASE A): **PASS** — ver `docs/ops/ola3-editorial-smoke-note-2026-07-20.md`.

## Tabla corta — los 5 ids

| id | Título tentativo | Fuente / señal | ¿Verificable? | Riesgo | Decisión sugerida |
|---|---|---|---|---|---|
| PITCH-OLA3-01 | IDS: el criterio de aceptación se vuelve verificable por máquina | buildingSMART **IDS v1.0** | Sí (ancla) | bajo | **usar ahora** |
| PITCH-OLA3-02 | IFC 4.3 en infraestructura lineal: el hueco ya no es el formato, es el proceso | **IFC 4.3 = ISO 16739-1:2024** | Sí (ancla) | medio | usar ahora / esperar |
| PITCH-OLA3-03 | La IA no sube la productividad de una revisión que nadie definió | **McKinsey** (tema) | Parcial (tema; cifras pendientes) | medio | **usar ahora** |
| PITCH-OLA3-04 | Un entregable en verde no es un entregable aceptado | Opinión + McKinsey (contexto) | No (opinión marcada) | medio | **usar ahora** |
| PITCH-OLA3-05 | Antes de automatizar la revisión, define la puerta: qué se acepta, qué vuelve y qué avanza | Opinión / pendiente de fuente primaria (referente ISO 19650) | No (opinión marcada) | bajo | **usar ahora** |

> Cobertura de fuentes piloto (§3): buildingSMART (2 pitches) · McKinsey (1 + 1
> como contexto) · opinión operativa de David (2). Balance verificable/opinión: 2
> ancladas, 1 parcial, 2 opinión — honestidad de fuente explícita en cada una.
> Los pitches 04 y 05 son **complementarios, no redundantes**: 05 es la decisión
> *antes* de automatizar (definir el requisito); 04 es la decisión *después* de que
> la comprobación automática pasa (aceptar y responder).

---

## PITCH-OLA3-01 — IDS: el criterio de aceptación se vuelve verificable por máquina

1. **id:** PITCH-OLA3-01
2. **Título tentativo:** *IDS no revisa tu modelo: convierte en artefacto verificable qué aceptas, qué vuelve y qué avanza.*
3. **Tesis única:** con IDS v1.0 los requisitos de entrega pasan a ser legibles por máquina y validables automáticamente; el cambio operativo no es "ahora la máquina revisa", sino que *definir* qué se acepta deja de ser una convención implícita y se vuelve un artefacto explícito. Si esa definición no existe o está mal planteada, IDS solo automatiza —más rápido— una aceptación equivocada.
4. **Ángulo editorial:** proceso-primero. La automatización de la validación se apoya en una decisión previa (qué exigir) que IDS **no toma por ti**: solo la codifica y la comprueba. La pieza no celebra el estándar; muestra que mueve el trabajo difícil de "revisar el modelo" a "definir el requisito" (esa lectura del cuello de botella se presenta explícitamente como análisis, no como dato).
5. **Por qué ahora:** IDS alcanzó estatus de estándar final de buildingSMART en **junio de 2024**; hoy es adoptable, y el momento de riesgo es justo este —automatizar la comprobación antes de haber definido el requisito—. (La existencia de una "ola de flujos de auto-validación" se enuncia como observación, no como dato de adopción.)
6. **Alineación (narrativa/propuesta/audiencia):** encaja directo con "IA sin criterio no resuelve procesos". IDS es la expresión legible por máquina de exactamente las tres compuertas —qué se acepta, qué vuelve, qué avanza—. Audiencia: coordinación / revisión de modelos / entrega en equipos AECO-BIM.
7. **Fuente o señal:** verificable — buildingSMART, IDS v1.0 (estándar final, jun 2024): <https://www.buildingsmart.org/standards/bsi-standards/information-delivery-specification-ids/>. Tipo: estándar oficial (fuente primaria citable).
8. **Riesgo editorial:** **bajo.** El claim central (IDS = requisitos legibles por máquina, validables automáticamente) está anclado. Límite: IDS cubre la **capa de requisitos de información**, no todo el juicio de revisión (interferencias, adecuación al uso); no citar cifras de adopción/madurez sin fuente primaria.
9. **Decisión sugerida para David:** **usar ahora.** (Es la pieza-ancla del set: tesis nítida, fuente primaria, "por qué ahora" fuerte.)

---

## PITCH-OLA3-02 — IFC 4.3 en infraestructura lineal: el hueco ya no es el formato, es el proceso

1. **id:** PITCH-OLA3-02
2. **Título tentativo:** *En infraestructura lineal, IFC 4.3 cierra el hueco del formato: el que queda es de proceso.*
3. **Tesis única:** con IFC 4.3 aprobado como ISO 16739-1:2024, por primera vez la infraestructura **lineal** (rail, carretera, puente, túnel, puerto, `IfcAlignment`) entra al esquema IFC. Al desaparecer la explicación histórica de las entregas fragmentadas en obra lineal —"no había estándar abierto para esto"— queda al descubierto una pregunta de proceso: qué información del modelo intercambiado necesita cada decisión de coordinación, definida antes de automatizar cualquier comprobación.
4. **Ángulo editorial:** proceso-primero aplicado a obra lineal. El estándar es **precondición** del intercambio trazable, no sustituto de definir qué debe sobrevivir al handover y para qué decisión sirve. No celebra el estándar: muestra que el bloqueo se ve ahora donde siempre estuvo.
5. **Por qué ahora:** la aprobación como estándar final ISO es de **enero de 2024** y la infraestructura entra al esquema por primera vez. Como el canal es blog evergreen, el "ahora" se ancla en la **maduración/especificación** por equipos de obra lineal (enunciada como observación), no en fingir urgencia por la fecha.
6. **Alineación:** refuerza "IA sin criterio no resuelve procesos" desde el lado opuesto: cuando el estándar deja de faltar, se ve que el bloqueo nunca fue la herramienta sino la falta de definición del proceso. Audiencia: infraestructura / coordinación / handover openBIM.
7. **Fuente o señal:** verificable — buildingSMART / ISO 16739-1:2024 (IFC 4.3): <https://www.buildingsmart.org/ifc-4-3-approved-as-a-final-standard/>. Tipo: estándar oficial (fuente primaria citable).
8. **Riesgo editorial:** **medio.** Verificable: IFC 4.3 = ISO 16739-1:2024 y la entrada de infraestructura lineal por primera vez. Tratar como **contexto** (no dato duro) "antes no había estándar abierto"; cualquier mención a mandatos de licitación o ROI va como opinión / pendiente de fuente primaria; sin cifras de adopción.
9. **Decisión sugerida para David:** **usar ahora / esperar.** Sólida como autoridad evergreen; si se busca "por qué ahora" fuerte, esperar/atar a una señal de adopción concreta y fechada la subiría.

---

## PITCH-OLA3-03 — La IA no sube la productividad de una revisión que nadie definió

1. **id:** PITCH-OLA3-03
2. **Título tentativo:** *La IA no sube la productividad de una revisión que nadie definió.*
3. **Tesis única:** McKinsey sostiene, a nivel de tema, que mejorar la productividad en construcción "ya no es opcional" y que la IA es su próxima frontera. Pero cualquier mejora de productividad al automatizar una revisión es **condicional**: depende de haber definido antes qué se acepta, qué vuelve y qué puede avanzar. Sobre un proceso sin definir, automatizar acelera el reproceso en lugar de producir retorno.
4. **Ángulo editorial:** tomar el titular fácil y moverlo de la herramienta a la decisión: la pregunta no es qué IA instalar, sino qué resuelve realmente tu revisión. Lenguaje condicional; el retorno aparece solo si el proceso ya decide antes de automatizar. La tesis del criterio es **interpretación de Umbral**, no un hallazgo de McKinsey.
5. **Por qué ahora:** la línea editorial de McKinsey ("la productividad ya no es opcional", "IA: la próxima frontera") presiona a los equipos AECO a adoptar rápido. Es el momento de separar el titular del mecanismo que de verdad genera la mejora. (Se puede reforzar el "ahora" atando a IDS v1.0 / IFC 4.3 como gatillo datado.)
6. **Alineación:** núcleo exacto de Umbral —IA sin criterio no resuelve procesos—, framing proceso-primero, sin entrar de golpe al "modelo BIM". Audiencia: decisión técnica / dirección que evalúa adoptar IA.
7. **Fuente o señal:** parcial — McKinsey, línea editorial citada **a nivel de tema**: <https://www.mckinsey.com/capabilities/operations/our-insights/artificial-intelligence-construction-technologys-next-frontier> y <https://www.mckinsey.com/capabilities/operations/our-insights/delivering-on-construction-productivity-is-no-longer-optional>. Tipo: análisis de referente (citable a nivel de tema).
8. **Riesgo editorial:** **medio.** Todo "X% de productividad" queda **pendiente de fuente primaria**; no citar cifras concretas de McKinsey. Mantener lenguaje condicional para que "la IA acelera el reproceso" no se lea como conclusión de la fuente.
9. **Decisión sugerida para David:** **usar ahora.** Título limpio y anti-hype; máxima resonancia con la narrativa. Cuidado principal: disciplina de cifras.

---

## PITCH-OLA3-04 — Un entregable en verde no es un entregable aceptado

1. **id:** PITCH-OLA3-04
2. **Título tentativo:** *Un entregable en verde no es un entregable aceptado: quién responde después.*
3. **Tesis única:** aunque toda la revisión pase de forma automática, **aceptar** el entregable —asumir la decisión de qué avanza— es un acto humano que no se delega en el agente. Comprobar no es aceptar; tratarlos como lo mismo es lo que sale caro.
4. **Ángulo editorial:** distingue comprobación de aceptación. Un agente puede reportar "todo cumple"; nadie automatiza quién sostiene esa aceptación después. El gate de aceptación es criterio de proceso, no una casilla de checklist. Encuadre proceso-primero (entregable / revisión / aceptación / decisión). Se mantiene en el plano de **criterio operativo**, no de responsabilidad jurídica/contractual.
5. **Por qué ahora:** la presión por "dejar que la herramienta cierre la revisión" crece —a nivel de tema en la línea McKinsey y con la validación automática ya disponible (IDS)—; es justo cuando confundir "comprobar" con "aceptar" se vuelve costoso.
6. **Alineación:** núcleo "sin criterio no resuelve procesos": automatizar sobre una decisión de aceptación no definida acelera el reproceso. Refleja el diseño de gates humanos del propio sistema editorial de Umbral (`docs/ops/editorial-agent-flow.md`, pasos 8–10). Audiencia: coordinación / responsables de entrega.
7. **Fuente o señal:** opinión marcada (tesis central = posición editorial). Contexto del "por qué ahora": McKinsey a nivel de tema (<https://www.mckinsey.com/capabilities/operations/our-insights/artificial-intelligence-construction-technologys-next-frontier>). Tipo: opinión operativa + análisis de referente como contexto.
8. **Riesgo editorial:** **medio.** La tesis es opinión y va marcada. Vigilar que "aceptar el entregable" **no** se lea como asesoría legal/contractual (quién firma, responsabilidad civil): mantenerlo en criterio operativo. Cualquier %/USD de McKinsey → fuente primaria, no afirmar en el post.
9. **Decisión sugerida para David:** **usar ahora.** Tesis memorable y propia; complementa a 05 (define antes ↔ acepta después).

---

## PITCH-OLA3-05 — Antes de automatizar la revisión, define la puerta

1. **id:** PITCH-OLA3-05
2. **Título tentativo:** *Antes de automatizar la revisión de modelos, define la puerta: qué se acepta, qué vuelve y qué avanza.*
3. **Tesis única:** automatizar una revisión de modelos que no tiene **escrita** su regla de aceptación no ahorra trabajo: solo reparte más rápido decisiones que nadie acordó. Lo que hace "automatizable" una revisión no es la herramienta de IA, sino haber definido antes la puerta de decisión —qué entra como aceptado, qué regresa a origen y qué puede seguir—.
4. **Ángulo editorial:** desde coordinación: la mayoría de las "automatizaciones de revisión" no fallan por el modelo ni por la IA, sino porque el equipo nunca puso por escrito qué distingue un entregable aceptado de uno que vuelve. Definir esa puerta es trabajo de **proceso**, no de software. El cierre aterriza en consecuencias concretas (reprocesos, entregables que vuelven a origen, decisiones sin dueño), evitando la muletilla abstracta.
5. **Por qué ahora:** crece la presión por "meterle IA a la revisión", pero la regla de aceptación/rechazo sigue viviendo implícita en la cabeza de una persona. Es el momento de fijarla y hacerla explícita antes de escalarla con automatización, cuando el error se multiplica. (Se puede anclar a nivel de marco en IDS v1.0 —requisitos legibles por máquina— como el "por qué ahora" concreto.)
6. **Alineación:** encaje de lleno con "IA sin criterio no resuelve procesos" y la lente proceso-primero. Pieza de autoridad evergreen: no vende herramienta, ordena la decisión previa. Audiencia: coordinación / revisión de modelos / dirección técnica.
7. **Fuente o señal:** **opinión / pendiente de fuente primaria.** Referente conceptual (sin cifras, solo marco): gestión de información **ISO 19650** (define los requisitos de información —OIR/AIR/PIR/EIR— *antes* de designar al equipo de entrega). Tipo: opinión operativa de David con referente de estándar.
8. **Riesgo editorial:** **bajo.** Tesis de opinión, sin cifras ni datos de clientes. Único cuidado: presentar "la puerta de decisión" como criterio de proceso, **no** como método propietario ni promesa de resultados; ISO 19650 se nombra como referente, no como fuente de números.
9. **Decisión sugerida para David:** **usar ahora.** Es la expresión más pura de la narrativa núcleo y el mejor candidato "evergreen" del set.

---

## Anclas verificables usadas (fuentes)

| # | Ancla | Qué sostiene | URL |
|---|---|---|---|
| 1 | IFC 4.3 = **ISO 16739-1:2024** (buildingSMART, ene 2024) | Infraestructura lineal (rail/road/bridge/tunnel/port, `IfcAlignment`) entra al esquema IFC por primera vez | <https://www.buildingsmart.org/ifc-4-3-approved-as-a-final-standard/> |
| 2 | **IDS v1.0** — estándar final buildingSMART (jun 2024) | Requisitos de entrega de información legibles por máquina (XML/JSON), validables automáticamente | <https://www.buildingsmart.org/standards/bsi-standards/information-delivery-specification-ids/> |
| 3 | **McKinsey** — línea editorial (nivel de tema) | "Productividad en construcción ya no es opcional" + "IA: próxima frontera"; cifras concretas → verificar en fuente primaria | <https://www.mckinsey.com/capabilities/operations/our-insights/artificial-intelligence-construction-technologys-next-frontier> |
| 4 | **ISO 19650** (referente conceptual) | Define requisitos de información (OIR/AIR/PIR/EIR) antes de designar al equipo de entrega — usado solo como marco, sin cifras | — |

> Regla de honestidad aplicada: solo las anclas 1–3 se usan como "verificable";
> cualquier cifra específica (%/USD, adopción, madurez) queda **pendiente de fuente
> primaria** para la etapa de ampliación. No se citó ninguna URL ni estadística
> fuera de esta lista.

## Checklist — ningún gate de publish quedó abierto

- [x] **Sin publish** blog/Azure/LinkedIn/X (ni real ni simulado con red).
- [x] Gates `aprobado_contenido` / `autorizar_publicacion` **no abiertos**.
- [x] `RICK_LINKEDIN_ORG_PUBLISH_ENABLED` / `RICK_STAGE8_GOOGLE_IMAGE_ENABLED`
      **no seteados** (default-off / fail-closed; guards Ola 2 `136a1a47` intactos).
- [x] Sin escritura a Notion `Publicaciones`; sin activar runtime de Rick.
- [x] Sin tocar `env.rick` / `vm_script` / token-map / auth store; sin rotar secretos.
- [x] Sin SSH / VPS / deploy. Entrega **docs-only** en worktree
      `claude/docs-ola3-editorial-5-pitches`.
- [x] Pitches: 5 propuestas, tesis única, sin hype, sin datos de clientes inventados,
      sin copy completo.

## Próximo paso (fuera de alcance de esta ola)

David selecciona 1+ pitches. **Solo entonces**, con GO humano, se amplía(n) la(s)
elegida(s) a candidato/borrador (payload de
`docs/ops/rick-editorial-candidate-payload-template.md`, campos completos; Notion
`Publicaciones` en `Borrador` si aplica). Ningún publish automático en Ola 3 ni en
la ampliación sin gates humanos abiertos por David.

---

`OLA3_EDITORIAL_PITCHES_READY`
