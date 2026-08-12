# CAND-PROD-001 - STAGE3 variantes y benchmark repo

> Fecha: 2026-06-06  
> Rama: `codex/cand-prod001-stage2`  
> Base: `71ea7ad6`  
> Estado: interno. NO Notion. NO gates. NO publicar. NO commit en este stage.

## 1. Decision brief operativo

```yaml
publication_id: CAND-PROD-001
stage: STAGE3_VARIANTS_REPO_BENCHMARK
canal: LinkedIn
premisa: >
  En flujos BIM, muchas decisiones se toman pero nunca se cierran ni se vuelven
  reconstruibles: quedan en chats, reuniones y memorias individuales. Escalar IA
  sobre ese sustrato no resuelve el problema; lo hereda y lo amplifica, porque la
  IA actúa sobre decisiones abiertas, sin autor, sin fecha y sin fundamento recuperable.
claim_type: inferencia_con_fuentes
claim_principal: >
  El factor que limita el valor de escalar IA en flujos BIM puede no estar solo
  en la madurez del equipo o en la falta de criterios de aceptación, sino en que
  muchas decisiones de proyecto no son trazables ni están formalmente cerradas.
objetivo_comercial:
  etapa_embudo: awareness
  visibilidad: alta
  venta_directa: baja
  cta_tipo: diagnostico
fuentes_citables:
  - ISO 19650 como marco de gestión de información, CDE, estados y revisión/autorización.
  - buildingSMART BCF como marco abierto para incidencias, comentarios, autoría, fecha y estado.
  - DeepLearning.AI / The Batch como señal de provenance/auditabilidad de agentes, issue específico pendiente de verificación.
fuentes_discovery_no_citables:
  - Burcin Kaplanoglu
  - Ignasi Perez Arnal
limites_claim:
  - No afirmar estadísticas de adopción de CDE, BCF o IA.
  - No citar referentes discovery como autoridad pública.
  - Usar ISO 19650 y BCF como marco operativo, no como brochure normativo.
  - Mantener la tesis como inferencia modesta.
```

## 2. Nota editorial de dedup

| Candidata | Territorio | Diferencia frente a CAND-PROD-001 |
|---|---|---|
| CAND-002 | Preparación organizacional para absorber IA. | Habla de roles, procesos y capacidad de la organización. CAND-PROD-001 baja a una superficie más específica: decisiones reconstruibles y cerradas. |
| CAND-003 | Criterio antes que automatización. | Habla de criterios de revisión, aceptación y escalación. CAND-PROD-001 asume que puede existir criterio, pero pregunta si la decisión concreta quedó trazada, cerrada y auditable. |
| CAND-PROD-001 | Trazabilidad y cierre de decisiones BIM. | El foco es el decision audit trail: autor, fecha, fundamento, estado y evidencia de cierre antes de escalar IA sobre flujos BIM. |

Esta pieza no repite "más preparación" ni "definir criterio". La pregunta diferencial es: **si alguien revisa el proyecto dentro de seis meses, puede reconstruir quién decidió qué, cuándo, sobre qué base y si quedó cerrado.**

## 3. Variantes LinkedIn internas

### V1 - Clash detectado, decisión no registrada en BCF/CDE

**Status:** interna, needs ChatGPT benchmark.

```text
El clash ya estaba detectado.
La decisión nunca quedó registrada.

En una coordinación BIM, MEP y estructura acuerdan mover una bandeja. El modelo se ajusta, la reunión avanza y todos entienden que el punto quedó resuelto.

Semanas después, alguien abre el CDE y el BCF sigue abierto: sin autor del cierre, sin fecha y sin evidencia de qué se aceptó.

Al conectar IA para revisar incidencias, esa IA hereda el registro que existe, no la memoria del equipo.

Puede volver a levantar un problema resuelto.
Puede asumir como cerrado algo que nunca tuvo cierre.
Puede acelerar una coordinación que perdió su propia traza.

ISO 19650 y BCF ya dan marcos para estados, revisión, autorización y registro de incidencias. El uso práctico está en convertir eso en decisiones reconstruibles, no en una cita de norma.

Antes de escalar IA en BIM, revisaría una capa más básica:

qué decisiones del proyecto tienen autor,
fecha,
fundamento,
y estado real de cierre.
```

### V2 - Cambio de criterio sin autoría ni fecha reconstruible

**Status:** interna, needs ChatGPT benchmark.

```text
El criterio cambió en un chat.
El modelo siguió como si eso fuera trazabilidad.

En un proyecto BIM, alguien ajusta el criterio de modelado de instalaciones: qué nivel de detalle se espera, qué parámetros importan y qué se acepta en revisión.

La decisión sirve.
El problema aparece cuando queda repartida entre mensajes, memoria y costumbre.

Meses después, una validación automática compara el entregable contra el criterio anterior, porque ese es el único que quedó documentado.

La IA hereda la decisión abierta y la ejecuta a escala.

Ahí el riesgo no está en usar automatización. Está en pedirle que opere sobre criterios que cambiaron sin autor, sin fecha y sin fundamento recuperable.

ISO 19650 ayuda a pensar estados de información y autorización. BCF ayuda a registrar incidencias, comentarios y decisiones. En producción real, el valor aparece cuando esos marcos sostienen cambios de criterio que mañana alguien tendrá que auditar.

Antes de sumar otra capa de IA, miraría dónde vive cada cambio de criterio:

en el CDE,
en un BCF,
en una minuta trazable,
o solo en la memoria del equipo.
```

### V3 - Aprobación que nadie puede reconstruir meses después

**Status:** interna, needs ChatGPT benchmark.

```text
La aprobación existía.
La historia de la aprobación no.

Un entregable pasa de compartido a publicado en el CDE. En el momento parece normal: hubo revisión, hubo coordinación, hubo acuerdo.

Meses después, ante una orden de cambio o un reclamo, nadie puede reconstruir qué se revisó, qué quedó pendiente y quién aceptó el riesgo.

Si además se acelera el ciclo de aprobación con IA, la fragilidad cambia de escala.

Una IA puede ordenar documentos, sugerir cierres y detectar inconsistencias. Pero si el cierre humano no dejó evidencia mínima, el sistema solo acelera una aprobación opaca.

En BIM, el audit trail no debería sentirse como burocracia. Debería ser la forma de saber si una decisión está cerrada o solo fue asumida como cerrada.

ISO 19650 y BCF no son el argumento central de la pieza. Son marcos útiles para una exigencia más operativa:

cuando el proyecto avance y alguien tenga que reconstruir una decisión, el registro debería mostrar autor, fecha, fundamento y estado de cierre.

Si la respuesta depende de recordar quién estuvo en la reunión, la IA va a heredar una deuda que el proyecto todavía no resolvió.
```

## 4. Scorecard dimensions.yaml

Escala 0.00 a 1.00. Umbral operativo repo-side: promedio ponderado >= 0.70 y mínima dimensión >= 0.50.

| Dimensión | Peso | V1 | V2 | V3 |
|---|---:|---:|---:|---:|
| strategic_fit | 0.12 | 0.88 | 0.86 | 0.85 |
| audience_relevance | 0.12 | 0.92 | 0.89 | 0.87 |
| technical_accuracy | 0.10 | 0.84 | 0.86 | 0.84 |
| source_handling | 0.10 | 0.83 | 0.84 | 0.82 |
| primary_source_discipline | 0.08 | 0.84 | 0.84 | 0.82 |
| voice_fit | 0.10 | 0.86 | 0.84 | 0.85 |
| channel_fit | 0.08 | 0.86 | 0.84 | 0.84 |
| cta_quality | 0.08 | 0.78 | 0.76 | 0.78 |
| visual_brief_quality | 0.06 | 0.72 | 0.72 | 0.72 |
| anti_ai_slop | 0.08 | 0.88 | 0.86 | 0.87 |
| risk_control | 0.04 | 0.92 | 0.92 | 0.92 |
| human_gate_compliance | 0.04 | 1.00 | 1.00 | 1.00 |
| **Promedio ponderado** | **1.00** | **0.858** | **0.848** | **0.842** |
| **Mínima dimensión** |  | **0.72** | **0.72** | **0.72** |
| **Resultado repo-side** |  | **PASS** | **PASS** | **PASS** |

### Lectura de scorecard

- **V1** gana por aterrizaje AEC inmediato, claridad de escena y diferenciación frente a CAND-002/003.
- **V2** es fuerte si se quiere enfatizar "criterio que cambió", pero roza más CAND-003 y por eso queda segunda.
- **V3** tiene buen cierre narrativo y riesgo controlado, aunque tarda un poco más en mostrar el artefacto BIM concreto.

## 5. Smoke anti-patrones benchmark v1

| Check benchmark v1 / smoke LinkedIn | V1 | V2 | V3 |
|---|---|---|---|
| Sin "En el mundo actual" | PASS | PASS | PASS |
| Sin "No es solo X, es Y" | PASS | PASS | PASS |
| Sin "No es esto, es esto otro" | PASS | PASS | PASS |
| Sin "Aquí es donde entra" | PASS | PASS | PASS |
| Sin em dash en copy público | PASS | PASS | PASS |
| Escena AEC/BIM operativa en primer tercio | PASS | PASS | PASS |
| Una tesis central, sin mini-ensayo | PASS | PASS | PASS |
| Sin estadísticas inventadas | PASS | PASS | PASS |
| Sin discovery sources como autoridad pública | PASS | PASS | PASS |
| ISO 19650 / BCF como marco, no brochure normativo | PASS | PASS | PASS |
| Claim modesto, marcado como inferencia | PASS | PASS | PASS |
| CTA awareness tipo diagnóstico, sin venta directa | PASS | PASS | PASS |
| Dedup vs CAND-002 y CAND-003 explícito | PASS | PASS | PASS |

### Benchmark v1 estimado

| Variante | voice_fit /10 | aec_operativo /10 | anti_ai_slop /10 | Resultado |
|---|---:|---:|---:|---|
| V1 | 8.6 | 9.1 | 8.8 | PASS |
| V2 | 8.4 | 8.9 | 8.6 | PASS |
| V3 | 8.5 | 8.7 | 8.7 | PASS |

## 6. Recomendación repo-side

**Enviar V1 a benchmark ChatGPT.**

Motivo: cumple mejor el patrón validado por el benchmark v1: abre con escena concreta, no se vuelve mini-artículo, usa BCF/CDE sin tono normativo y mantiene la tesis diferencial de CAND-PROD-001. V2 y V3 quedan como material de fusión si ChatGPT pide más énfasis en cambio de criterio o aprobación reconstruible.

## 7. Handoff ChatGPT

Copiar este bloque para benchmark externo. No publicar desde ChatGPT.

```text
Sos ChatGPT actuando como benchmark editorial externo para David.

Contexto:
- publication_id: CAND-PROD-001
- canal: LinkedIn
- estado: interno, no publicar
- objetivo comercial: awareness, visibilidad alta, venta directa baja
- claim_type: inferencia_con_fuentes
- premisa: En flujos BIM, muchas decisiones se toman pero nunca se cierran ni se vuelven reconstruibles: quedan en chats, reuniones y memorias individuales. Escalar IA sobre ese sustrato no resuelve el problema; lo hereda y lo amplifica, porque la IA actúa sobre decisiones abiertas, sin autor, sin fecha y sin fundamento recuperable.

Fuentes citables:
- ISO 19650: usar como marco de gestión de información, CDE, estados y revisión/autorización.
- buildingSMART BCF: usar como marco abierto para incidencias, comentarios, autoría, fecha y estado.
- DeepLearning.AI / The Batch: señal de provenance/auditabilidad de agentes; issue específico pendiente de verificación, no usar para afirmaciones concretas no verificadas.

Fuentes discovery no citables:
- Burcin Kaplanoglu.
- Ignasi Perez Arnal.

Límites del claim:
- No afirmar estadísticas de adopción de CDE, BCF o IA.
- No citar referentes discovery como autoridad pública.
- Mantener ISO 19650 y BCF como marco operativo, no como brochure normativo.
- Mantener la tesis como inferencia modesta.
- No usar "En el mundo actual".
- No usar "No es solo X, es Y".
- No usar "No es esto, es esto otro".
- No usar "Aquí es donde entra".
- No usar em dash.
- Evitar pregunta retórica con respuesta inmediata.
- Mantener una sola tesis central.

Dedup:
- CAND-002: preparación organizacional para absorber IA.
- CAND-003: criterio antes que automatización.
- CAND-PROD-001: trazabilidad y cierre de decisiones BIM, es decir autor, fecha, fundamento, estado y evidencia de cierre.

Tarea:
1. Puntúa V1, V2 y V3 de 0 a 10 en voice_fit, aec_operativo, anti_ai_slop, tesis_unica, linkedin_fit, atribucion_segura y diferenciacion_david.
2. Elige una ganadora o propone una fusión.
3. Si todas pasan, devuelve una sola variante final y termina con BENCHMARK_EDITORIAL_VALIDATED.
4. Si no pasan, termina con BENCHMARK_EDITORIAL_REJECTED y lista correcciones.

V1:
El clash ya estaba detectado.
La decisión nunca quedó registrada.

En una coordinación BIM, MEP y estructura acuerdan mover una bandeja. El modelo se ajusta, la reunión avanza y todos entienden que el punto quedó resuelto.

Semanas después, alguien abre el CDE y el BCF sigue abierto: sin autor del cierre, sin fecha y sin evidencia de qué se aceptó.

Al conectar IA para revisar incidencias, esa IA hereda el registro que existe, no la memoria del equipo.

Puede volver a levantar un problema resuelto.
Puede asumir como cerrado algo que nunca tuvo cierre.
Puede acelerar una coordinación que perdió su propia traza.

ISO 19650 y BCF ya dan marcos para estados, revisión, autorización y registro de incidencias. El uso práctico está en convertir eso en decisiones reconstruibles, no en una cita de norma.

Antes de escalar IA en BIM, revisaría una capa más básica:

qué decisiones del proyecto tienen autor,
fecha,
fundamento,
y estado real de cierre.

V2:
El criterio cambió en un chat.
El modelo siguió como si eso fuera trazabilidad.

En un proyecto BIM, alguien ajusta el criterio de modelado de instalaciones: qué nivel de detalle se espera, qué parámetros importan y qué se acepta en revisión.

La decisión sirve.
El problema aparece cuando queda repartida entre mensajes, memoria y costumbre.

Meses después, una validación automática compara el entregable contra el criterio anterior, porque ese es el único que quedó documentado.

La IA hereda la decisión abierta y la ejecuta a escala.

Ahí el riesgo no está en usar automatización. Está en pedirle que opere sobre criterios que cambiaron sin autor, sin fecha y sin fundamento recuperable.

ISO 19650 ayuda a pensar estados de información y autorización. BCF ayuda a registrar incidencias, comentarios y decisiones. En producción real, el valor aparece cuando esos marcos sostienen cambios de criterio que mañana alguien tendrá que auditar.

Antes de sumar otra capa de IA, miraría dónde vive cada cambio de criterio:

en el CDE,
en un BCF,
en una minuta trazable,
o solo en la memoria del equipo.

V3:
La aprobación existía.
La historia de la aprobación no.

Un entregable pasa de compartido a publicado en el CDE. En el momento parece normal: hubo revisión, hubo coordinación, hubo acuerdo.

Meses después, ante una orden de cambio o un reclamo, nadie puede reconstruir qué se revisó, qué quedó pendiente y quién aceptó el riesgo.

Si además se acelera el ciclo de aprobación con IA, la fragilidad cambia de escala.

Una IA puede ordenar documentos, sugerir cierres y detectar inconsistencias. Pero si el cierre humano no dejó evidencia mínima, el sistema solo acelera una aprobación opaca.

En BIM, el audit trail no debería sentirse como burocracia. Debería ser la forma de saber si una decisión está cerrada o solo fue asumida como cerrada.

ISO 19650 y BCF no son el argumento central de la pieza. Son marcos útiles para una exigencia más operativa:

cuando el proyecto avance y alguien tenga que reconstruir una decisión, el registro debería mostrar autor, fecha, fundamento y estado de cierre.

Si la respuesta depende de recordar quién estuvo en la reunión, la IA va a heredar una deuda que el proyecto todavía no resolvió.
```

## 8. Veredicto

`CAND_PROD001_REPO_BENCHMARK_READY`

Fases ejecutadas: variantes internas, benchmark repo-side, smoke anti-patrones y handoff ChatGPT.  
Fases no ejecutadas: Notion, gates, publicación, commit.
