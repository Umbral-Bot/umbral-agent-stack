# Rick Veritasium Style Integration Validation (2026-03-14)

## Objetivo del test

Validar si Rick, ante un prompt natural y corto del tipo:

> `rick, me gusta el estilo comunicativo de veritasium. revisa si hay algo ahí que valga la pena adaptar para mí, para mi marca personal y mis proyectos, y si hace sentido intégralo donde corresponda.`

es capaz de:

1. investigar una referencia comunicativa externa sin microinstrucciones;
2. decidir por su cuenta dónde conviene integrarla;
3. aplicar cambios reales en el proyecto activo;
4. dejar trazabilidad persistida;
5. responder en clave de integración, no solo de inspiración abstracta.

## Sesión auditada

- Session id: `0e6b144c-e75d-4b6b-9f03-f2309cefa20a`
- Ruta: `/home/rick/.openclaw/agents/main/sessions/0e6b144c-e75d-4b6b-9f03-f2309cefa20a.jsonl`

## Evidencia observada

### Investigación real

Rick no respondió solo desde memoria.

Acciones observadas:

- `umbral_research_web`
  - query: `Veritasium Derek Muller communication style storytelling misconceptions curiosity interview explanation`
- `web_fetch`
  - `https://en.wikipedia.org/wiki/Veritasium`
- uso de memoria y docs del proyecto para cruzar la referencia con el sistema embudo ya existente.

### Integración real en proyecto

Rick editó estos archivos del workspace:

1. `proyectos/venta-servicios-embudo/landing-umbralbim-io.html`
2. `proyectos/venta-servicios-embudo/docs/perfil_estrategia/07-secuencia-linkedin-rescate-v2.md`

Además creó un artefacto nuevo:

3. `proyectos/venta-servicios-embudo/docs/41_veritasium_adaptacion_editorial_2026-03-14.md`

### Cambios concretos aplicados

#### Hub principal

Rick endureció el framing del hero y del CTA para mover el mensaje desde:

- “software / tiempo / BIM” en términos más descriptivos

hacia:

- creencia equivocada;
- síntoma vs causa;
- mecanismo real del problema.

#### Secuencia LinkedIn

Rick cambió el Post 1 de `07-secuencia-linkedin-rescate-v2.md` para abrir con:

- “Tu problema no es Revit.”
- “Tu problema es todo lo que sigue pasando fuera de Revit.”

Eso alinea el sistema con un patrón tipo Veritasium:

- contraste;
- creencia errónea;
- explicación de mecanismo;
- payoff rápido.

#### Documento de criterio

El artefacto `41_veritasium_adaptacion_editorial_2026-03-14.md` dejó explícito:

- qué sí tomar;
- qué no tomar;
- cómo adaptarlo a David;
- reglas por canal;
- integración concreta con el embudo.

## Trazabilidad persistida

Rick dejó trazabilidad real en:

- Notion:
  - `https://www.notion.so/Proyecto-Embudo-Ventas-adaptaci-n-editorial-desde-Veritasium-2026-03-14-3235f443fb5c81a88ba2defbc9178a7b`
- Linear:
  - comentario en `UMB-39`
  - comment id: `9e63381e-f0fe-4f6b-9662-2da727433744`

## Respuesta final de Rick

La respuesta visible al usuario fue coherente con lo que realmente hizo.

Rick declaró:

- qué rasgos valía la pena adaptar;
- qué no convenía copiar;
- dónde lo integró;
- y dejó un siguiente paso concreto.

Eso coincide con la traza observada.

## Evaluación

### Qué salió bien

1. Rick entendió que el pedido no era “copiar a Veritasium”.
2. Investigó una referencia externa real sin que se le detallara el procedimiento.
3. Decidió por sí solo dónde integrarla:
   - hub principal;
   - secuencia de LinkedIn;
   - documento de criterio.
4. No dejó el análisis en el chat: lo persistió.
5. La respuesta final estuvo alineada con la evidencia.

### Qué faltó o quedó parcial

1. La investigación externa fue suficiente para este test, pero no profunda al nivel de un teardown multifuente largo.
2. No hubo revisión explícita del perfil de David en esta misma iteración; la adaptación se apoyó más en docs existentes del proyecto.
3. La integración quedó bien en embudo + LinkedIn, pero todavía no aterriza de forma explícita:
   - docencia;
   - futuro canal de YouTube;
   - marco reusable para otros referentes.

## Veredicto

El test se considera **aprobado**.

Rick ya mostró el comportamiento que buscábamos en este tipo de prompt:

- inferir intención;
- investigar;
- decidir dónde integrar;
- aplicar cambios reales;
- persistir y dejar trazabilidad.

El siguiente paso natural ya no es corregir este caso puntual, sino generalizar este comportamiento con una skill reusable para prompts del tipo:

- “me gusta el estilo comunicativo de X”
- “me gusta cómo explica Y”
- “me gusta esta referencia para tal cosa”

## Iteración de continuidad dentro del embudo

Después del benchmark inicial, David pidió:

> `sí, aplícalo entonces dentro del proyecto embudo donde realmente haga sentido.`

### Qué hizo Rick

Rick aplicó el framing a piezas adicionales del embudo:

1. `proyectos/venta-servicios-embudo/blog-umbralbim-io.html`
2. `proyectos/venta-servicios-embudo/docs/perfil_estrategia/08-one-pager-rescate-digital-v2.md`
3. `proyectos/venta-servicios-embudo/docs/perfil_estrategia/09-template-propuesta-auditoria-v2.md`
4. `proyectos/venta-servicios-embudo/docs/42_integracion_veritasium_en_embudo_2026-03-14.md`

Los cambios fueron coherentes con el objetivo:

- apertura contraintuitiva;
- separación síntoma vs causa;
- mejora del diagnóstico antes de vender solución;
- sin empujar el tono hacia algo teatral o ajeno a David.

### Desviación observada

En esta subiteración, Rick primero:

- hizo los edits correctos;
- escribió el artefacto nuevo;

pero **no cerró inmediatamente la trazabilidad ni la respuesta al usuario**.

Necesitó un follow-up corto para:

- alinear esta vuelta con Linear / Notion;
- y responder con un cierre explícito de:
  - qué aplicó;
  - dónde;
  - qué cambió;
  - qué no conviene tocar.

### Resultado tras corrección

Después del empujón, Rick sí cerró correctamente:

- resumió los cambios reales;
- citó los archivos concretos;
- confirmó actualización en `UMB-39`;
- y entregó una nueva página de Notion:
  - `https://www.notion.so/Proyecto-Embudo-Ventas-integraci-n-aplicada-de-framing-tipo-Veritasium-2026-03-14-3235f443fb5c81ab99cbc01dffc86523`

### Lectura diagnóstica

Esto confirma un patrón ya conocido:

- Rick **ya sabe ejecutar e integrar bien**;
- el residual más frecuente no es de comprensión, sino de **cierre disciplinado**:
  - a veces edita y escribe el artefacto;
  - pero necesita una presión extra para cerrar la trazabilidad final y contestar con formato de cierre.

No hizo falta cambiar el runtime para este caso. Bastó una iteración correctiva corta.

## Próximo slice recomendado

Crear e integrar una skill general de:

- extracción de estilo / rasgos de referencia;
- adaptación a la voz de David;
- mapeo por canal;
- persistencia en proyecto;
- trazabilidad en Linear + Notion + carpeta compartida.
