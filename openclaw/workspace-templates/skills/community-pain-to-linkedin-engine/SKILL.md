---
name: community-pain-to-linkedin-engine
description: convertir conversaciones publicas de comunidades en pain points, hooks, angulos y borradores de contenido para linkedin, newsletter, blog y embudo dentro de umbral. usar cuando david pida extraer lenguaje real del mercado desde reddit u otras comunidades, detectar dolores y objeciones, transformarlos en ideas editoriales con gate humano y conectarlos con el sistema editorial, la marca personal o el proyecto embudo sin depender de un modelo o proveedor especifico.
metadata:
  openclaw:
    emoji: "🧵"
    requires:
      env: []
---

# Community Pain to LinkedIn Engine

## Objetivo

Convertir conversaciones publicas en insumos editoriales accionables para Umbral.

La salida buena no es "una idea interesante", sino un paquete reusable con:
- pains observados
- lenguaje real del mercado
- hooks
- angulos
- borradores de pieza
- CTA sugerido
- siguiente paso del funnel

No depender de Grok, Claude o una plataforma concreta. La logica debe sobrevivir al proveedor.

## Cuándo usar esta skill

Usarla cuando David pida algo como:
- "mira que dolores aparecen en Reddit"
- "saca ideas desde foros"
- "encuentra el lenguaje real del mercado"
- "quiero hooks a partir de conversaciones publicas"
- "quiero convertir pains reales en posts de LinkedIn"
- "quiero usar este metodo estilo Ruben Hassid pero aterrizado a Umbral"

Combinarla con:
- `competitive-funnel-benchmark` cuando el punto de partida sea un referente o caso externo
- `editorial-source-curation` cuando haya que rankear temas o shortlist
- `editorial-voice-profile` cuando haya que adaptar salida a la voz de David
- `multichannel-content-packager` cuando una pieza ya deba expandirse a varios canales
- `telegram-approval-loop` cuando David deba aprobar antes de publicar o seguir

## Regla maestra

No convertir una sola conversacion en "verdad del mercado".

Trabajar por patrones, no por anecdotas sueltas.

Toda salida debe separar:
- `evidencia observada`
- `inferencia`
- `hipotesis`
- `propuesta editorial`

## Flujo obligatorio

Seguir este orden:

1. definir el tema o ICP
2. reunir conversaciones publicas relevantes
3. extraer pain points y lenguaje real
4. agrupar patrones repetidos
5. convertir patrones en hooks y angulos
6. convertir hooks en piezas
7. elegir CTA y activo propio
8. dejar trazabilidad si esto impacta un proyecto oficial

No saltar del paso 2 al 6.

## Fuentes permitidas

### Reddit

Reddit es una fuente util, pero no la unica.

Si el hilo es publico, se puede usar el patron:
- `URL del thread + /.json`

Ejemplo conceptual:
- `https://www.reddit.com/r/.../comments/.../.json`

Usar ese JSON para:
- title
- selftext
- comentarios
- replies
- metadatos del hilo

No prometer acceso detras de login, contenido borrado o superficies anti-bot.

### Otras comunidades publicas

Tambien pueden servir:
- foros publicos
- comentarios visibles en blogs
- comentarios publicos en LinkedIn cuando sean observables con tooling real
- comunidades de producto con lectura publica
- issue trackers publicos
- discusiones publicas especializadas

Si la comunidad no es realmente publica, marcarla como fuera de alcance.

## Extraccion de pains

Para cada hilo o conversacion capturada, extraer:
- dolor principal
- limitacion o bloqueo
- necesidad implicita
- objecion visible
- lenguaje exacto del usuario
- ICP probable
- severidad percibida
- frecuencia aparente

### Formato recomendado

Usar una tabla o lista como:

- `pain`
- `evidencia`
- `lenguaje_literal`
- `ICP_probable`
- `severidad`
- `confianza`

Consultar `references/painpoint-extraction-format.md`.

## Agrupacion y patrones

No generar contenido desde pains aislados.

Agrupar primero por:
- pain repetido
- friccion recurrente
- error caro
- creencia equivocada
- necesidad mal atendida

Priorizar patrones que cumplan al menos dos de estas tres:
- repeticion
- intensidad
- cercania con una oferta o tesis de Umbral

## Hooks y angulos

De cada patron fuerte sacar:
- 3 a 5 hooks
- 2 a 3 angulos
- 1 tesis central

Separar:
- `hook`: apertura breve que detiene
- `angulo`: desde donde se mira el tema
- `tesis`: idea o afirmacion principal
- `CTA`: siguiente paso sugerido

No copiar frases exactas de referentes. Tomar solo estructura o criterio.

Consultar:
- `references/hook-generation-guide.md`
- `references/umbral-adaptation-checklist.md`

## Conversion a piezas

Por defecto generar primero:
- 3 a 5 hooks
- 3 borradores de post de LinkedIn
- 1 recomendacion de newsletter
- 1 recomendacion de blog o recurso

Si David pidio solo hooks o solo pain points, respetar el alcance.

### Reglas para LinkedIn

Cada borrador debe:
- abrir con hook fuerte
- usar lenguaje concreto
- evitar abstraccion hueca
- incluir una sola idea central
- aterrizar a framework, mecanismo o consecuencia
- cerrar con CTA compatible con el embudo

No publicar automaticamente. Esta skill produce borradores y criterio, no autopublicacion.

Consultar `references/linkedin-post-conversion-format.md`.

## Integracion con Umbral

Antes de cerrar, decidir para que sirve la salida:
- proyecto embudo
- sistema editorial
- marca personal
- newsletter
- blog
- puente a oferta, checklist o diagnostico

Si impacta un proyecto activo:
1. dejar artefacto en carpeta compartida o repo del proyecto
2. dejar update o comentario trazable en Linear
3. actualizar Notion si ese proyecto ya usa registro alli

## Guardrails

- No asumir que Reddit representa todo el mercado.
- No depender de Grok o Claude como requisito obligatorio.
- No tratar un hilo aislado como insight definitivo.
- No presentar inferencias como hechos.
- No usar scraping detras de login o paywall.
- No convertir esta skill en una excusa para publicar sin gate humano.

## Salida minima esperada

La salida buena incluye, como minimo:
- pains observados
- patrones agrupados
- hooks
- 3 angulos
- 3 borradores de post
- CTA sugerido
- recomendacion de activo propio
- huecos o limites de evidencia

## Referencias

- `references/reddit-json-workflow.md`
- `references/painpoint-extraction-format.md`
- `references/hook-generation-guide.md`
- `references/linkedin-post-conversion-format.md`
- `references/umbral-adaptation-checklist.md`
