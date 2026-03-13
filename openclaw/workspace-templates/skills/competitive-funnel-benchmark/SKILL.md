---
name: competitive-funnel-benchmark
description: estudiar en profundidad una persona, marca, perfil, post, landing, lead magnet, opt-in o funnel externo y convertirlo en un benchmark accionable para umbral. usar cuando david pida analizar un caso como referencia, benchmark o competencia, especialmente si involucra linkedin, perfil como landing, cta, lead capture, formularios, thank-you pages o continuidad de funnel. obligar cobertura minima de varias fuentes, separar evidencia de inferencia e hipotesis, evitar cerrar con una sola landing o una sola captura, y dejar una recomendacion util y trazable para el proyecto embudo.
metadata:
  openclaw:
    emoji: "🧭"
    requires:
      env: []
---

# Competitive Funnel Benchmark

## Objetivo
Convertir un caso externo en un benchmark profundo y util para Umbral, con cobertura minima real, teardown obligatorio y separacion estricta entre:
- evidencia observada
- inferencia
- hipotesis
- decision recomendada para Umbral

No tratar una sola landing, una sola captura o una sola pieza de copy como si fueran el sistema completo.

## Regla de oro
No cerrar un benchmark profundo con una sola fuente.

Como minimo trabajar con:
1. la fuente principal indicada por David
2. una segunda fuente independiente del mismo caso
3. una tercera senal si existe y es accesible

La tercera senal puede ser:
- perfil publico
- post relacionado
- comentarios
- primer comentario
- featured section
- landing secundaria
- home del sitio
- formulario
- thank-you page
- lead magnet accesible
- email de confirmacion visible
- otra pieza publica del mismo funnel

Si una fuente no es accesible:
- marcarla como `inaccesible` o `no verificada`
- no convertirla en hecho
- degradar el veredicto final si era critica para entender el funnel

## Veredicto de cobertura
Usar uno de estos veredictos y no inflarlo:

- `benchmark profundo`
  - fuente principal cubierta
  - segunda fuente independiente cubierta
  - tercera senal cubierta o explicitamente intentada y razonadamente clasificada como inaccesible
  - teardown completo
  - decision para Umbral con limites claros

- `benchmark parcial`
  - fuente principal cubierta
  - segunda fuente cubierta
  - tercera senal no encontrada o no verificable
  - teardown util pero con huecos materiales

- `senal inicial`
  - solo una fuente real cubierta
  - no afirmar aprendizaje de sistema
  - no recomendar imitacion fuerte

- `no verificable`
  - acceso insuficiente
  - restricciones de visibilidad
  - piezas clave no observables con tooling real

## Flujo obligatorio
Seguir este orden:

1. resolver el objeto del benchmark
2. resolver para que decision de Umbral sirve este benchmark
3. capturar la fuente principal
4. buscar una segunda fuente independiente del mismo caso
5. buscar una tercera senal si existe
6. clasificar lo visto en evidencia, inferencia e hipotesis
7. hacer teardown completo
8. traducir el hallazgo a decision para Umbral
9. dejar trazabilidad real si esto impacta un proyecto oficial

No saltar del punto 3 al 8.

## Persistencia obligatoria cuando impacta un proyecto
Si el benchmark se pide como parte de un proyecto activo, como insumo para un proyecto o como decision para Umbral:

1. No cerrar solo con respuesta de chat.
2. Persistir un artefacto en la carpeta compartida del proyecto.
3. Dejar issue o update trazable en Linear.
4. Si el proyecto usa registro en Notion, reflejar el avance alli.

### Contenido minimo del artefacto
El artefacto debe incluir estas secciones, en este orden:
- `objeto del benchmark`
- `evidencia observada`
- `inferencia`
- `hipotesis`
- `teardown`
- `adaptacion recomendada para Umbral`
- `huecos no verificados`
- `siguiente decision recomendada`

### Regla para benchmarks repetidos
Si David repite el mismo benchmark o uno muy cercano:
- se puede reutilizar contexto previo;
- pero antes de responder hay que hacer una de estas dos cosas:
  - refrescar al menos una fuente viva adicional; o
  - convertir el benchmark previo en artefacto persistido y trazable.

No reutilizar memoria sola como si fuera una nueva investigacion completa.

## Resolucion del objeto
Definir primero que se esta estudiando exactamente:

- persona
- marca
- perfil
- post
- landing
- lead magnet
- opt-in
- funnel
- combinacion de varias piezas

Nombrar tambien el recorte real del analisis:
- adquisicion
- captacion
- nurturance
- conversion
- posicionamiento
- perfil como landing
- post como entrada al funnel

## Criterio de herramientas
Usar herramientas reales y declarar el limite del metodo.

### Usar `web_fetch`
Usar `web_fetch` cuando baste con:
- html publico
- texto visible
- estructura basica de la pagina
- metadatos publicos
- lectura de landings estaticas
- comprobacion de una URL publica sin interaccion

### Escalar a browser real
Pasar a browser real cuando haga falta:
- ejecutar javascript
- hacer click
- abrir modales
- navegar tabs
- hacer scroll
- seguir CTAs
- inspeccionar formularios
- comprobar thank-you pages
- confirmar continuidad del funnel
- revisar piezas que no cargan en un fetch simple

### Login y acceso restringido
Si una pieza critica requiere login:
- usar browser real solo con login manual del usuario cuando exista ese flujo
- no pedir credenciales
- no aceptar credenciales en prompt
- no prometer scraping detras de login o paywall
- no asumir acceso a perfiles privados, comentarios privados, DMs o assets cerrados

Si no hay acceso real:
- marcar `observable solo con sesion iniciada`, `inaccesible` o `no verificado`
- no deducir el contenido no visto como si fuera hecho

## Matriz de observabilidad para LinkedIn
Clasificar cada pieza observada con una de estas etiquetas:

- `publico sin login`
- `observable solo con sesion iniciada`
- `no observable con tooling actual`
- `no verificado`

Regla critica:
la ausencia de comentarios, featured items, primer comentario, CTA extendido o continuidad del funnel en una vista publica no prueba ausencia real. Puede ser una restriccion de visibilidad, renderizado condicionado o limite del tooling.

## Reglas especificas para casos de LinkedIn

### 1. Post
Analizar como minimo:
- hook de apertura
- promesa
- framing
- CTA explicito o implicito
- tipo de audiencia implicita
- senales de continuidad hacia perfil, comentario, link, lead magnet o DM

No tratar el post como funnel completo si no se siguio el siguiente paso.

### 2. Perfil como landing
Analizar como minimo:
- headline
- banner si es visible
- about
- featured
- links salientes
- oferta implicita
- prueba social visible
- CTA principal
- consistencia entre post, perfil y activo de captura

No asumir conversion solo porque el perfil “se siente bien escrito”.

### 3. Comentarios
Si son accesibles, analizar:
- uso de comentarios para ampliar la promesa
- objeciones de la audiencia
- prueba social
- repeticion de CTA
- derivacion a DM, link o recurso

Si no son accesibles, decirlo. No inventar la conversacion.

### 4. Primer comentario
Verificar si el primer comentario:
- contiene link
- aclara la oferta
- entrega recurso
- mueve a la siguiente etapa
- corrige o expande el framing del post

No asumir existencia de primer comentario estrategico sin verlo.

### 5. Lead magnet u opt-in
Analizar si existe:
- titulo
- promesa
- especificidad
- friccion de acceso
- formato del activo
- coherencia con el hook de entrada
- tipo de captura
- siguiente paso inmediato tras el opt-in

No afirmar que convierte bien sin observar al menos parte del flujo real.

## Checklist minimo de cobertura
Cubrir como minimo estas capas del teardown:

- hook
- promesa
- audiencia implicita
- framing
- CTA
- activo de captura
- siguiente paso del funnel
- continuidad o nurturance si es observable
- riesgos o huecos no verificados

Si faltan varias capas, no usar el rotulo de benchmark profundo.

## Reglas de separacion analitica

### Evidencia observada
Incluir solo:
- lo visto de forma directa
- la fuente exacta de cada observacion
- el limite de observacion cuando aplique

Ejemplos validos:
- “el post abre con una promesa de ahorro de tiempo”
- “la landing pide email y nombre”
- “el CTA visible es descargar la guia”
- “el perfil enlaza a una home y no a una landing especifica”

### Inferencia
Incluir:
- deducciones razonables a partir de varias evidencias
- explicacion breve de por que la inferencia es razonable
- nivel de confianza cuando haga falta

Ejemplos validos:
- “probablemente el perfil funciona como puente entre contenido y captura porque repite la misma promesa y concentra los enlaces”
- “es probable que el primer objetivo sea captacion y no venta directa”

### Hipotesis
Incluir:
- lo que podria ser cierto pero no esta probado
- la evidencia faltante para confirmarlo

Ejemplos validos:
- “podria existir nurturance por email tras el opt-in, pero no fue observable”
- “es posible que los comentarios refuercen la conversion, pero no hubo acceso real”

### Decision recomendada para Umbral
Incluir:
- que copiar conceptualmente
- que no copiar
- que adaptar
- que probar primero
- que evidencia falta antes de decidir

No mezclar estas cuatro capas en una misma lista.

## Teardown obligatorio
Entregar siempre un teardown con estas capas, aunque alguna quede como `no verificada`:

1. entrada
   - donde entra la audiencia
   - cual es el hook real

2. promesa
   - que transformacion o beneficio promete
   - cuan especifica o generica es

3. audiencia implicita
   - para quien parece hecha la pieza
   - nivel de sofisticacion
   - pain o deseo dominante

4. framing
   - experto
   - guia
   - caso real
   - autoridad
   - anti-status-quo
   - urgencia
   - identidad aspiracional
   - otro

5. CTA
   - que se pide hacer
   - cuanta friccion hay
   - cuan alineado esta con la promesa

6. activo de captura
   - si existe lead magnet, recurso, formulario o paso de contacto
   - que pide
   - que ofrece a cambio

7. siguiente paso del funnel
   - perfil
   - landing
   - form
   - thank-you
   - email
   - DM
   - llamada
   - otro

8. continuidad o nurturance
   - que secuencia posterior es observable
   - que no fue observable

9. riesgos y huecos no verificados
   - piezas que faltan
   - restricciones del acceso
   - donde un insight seria prematuro

## Anti-patrones
Bloquear estos errores:

- cerrar con una landing
- cerrar con una sola captura
- tratar una captura como prueba suficiente
- confundir marketing copy con evidencia
- mezclar observacion con inferencia
- mezclar inferencia con hipotesis
- dar insights tacticos sin teardown
- decir “estudiado en profundidad” con una sola fuente
- asumir comentarios, perfiles privados o continuidad sin tooling real
- confundir una promesa bien escrita con prueba de conversion
- extrapolar todo el funnel desde una sola pieza de entrada
- recomendar copia tactica sin explicar por que funciona o para quien funciona

## Calidad minima de recomendacion para Umbral
Cerrar siempre con estas cinco decisiones:

1. `copiar conceptualmente`
   - principios, estructura o logica que si conviene trasladar

2. `no copiar`
   - elementos que son demasiado contextuales, debiles o dudosos

3. `adaptar`
   - que habria que reescribir segun audiencia, oferta y marca de Umbral

4. `probar primero`
   - secuencia de test minima y de bajo riesgo

5. `evidencia faltante antes de decidir`
   - que pieza del funnel o del comportamiento falta observar

No cerrar con “haria algo parecido” sin concretar esas cinco decisiones.

## Salida por defecto
Usar este orden salvo que el usuario pida otro:

1. resumen ejecutivo
2. coverage note
3. fuentes consultadas realmente
4. evidencia observada
5. inferencias
6. hipotesis
7. teardown del funnel
8. decision para Umbral
9. siguiente accion recomendada
10. trazabilidad del proyecto si aplica

## Formato recomendado de salida

### 1. Resumen ejecutivo
- 3-6 lineas
- decir que se estudio
- decir el veredicto de cobertura
- decir el aprendizaje principal
- decir el limite principal

### 2. Coverage note
- objeto analizado
- fuentes cubiertas
- senales intentadas
- restricciones de acceso
- veredicto: `benchmark profundo`, `benchmark parcial`, `senal inicial` o `no verificable`

### 3. Fuentes consultadas realmente
Listar solo las fuentes reales consultadas, con una linea por fuente:
- tipo de fuente
- URL o identificador visible
- nivel de observabilidad
- por que importa en el teardown

### 4. Evidencia observada
Usar bullets con atribucion clara por fuente.

### 5. Inferencias
Usar bullets separados, indicando brevemente por que se sostienen.

### 6. Hipotesis
Usar bullets separados, indicando que falta para validarlas.

### 7. Teardown del funnel
Cubrir todas las capas del teardown obligatorio.

### 8. Decision para Umbral
Usar exactamente estos subtitulos:
- copiar conceptualmente
- no copiar
- adaptar
- probar primero
- evidencia falta antes de decidir

### 9. Siguiente accion recomendada
Proponer una accion concreta:
- seguir una pieza del funnel con browser real
- comparar con otro caso
- convertir el benchmark en brief
- abrir issue o comentario de proyecto
- pedir una evidencia faltante

## Composicion con otras skills
Usar estas skills como apoyo cuando existan:

- `editorial-source-curation`
  - usar cuando haga falta ampliar contexto, repertorio de referentes o comparables
  - no usarla para sustituir el benchmark profundo del caso principal

- `linkedin-content`
  - usar despues del benchmark si hay que convertir hallazgos en estructura de post, CTA o formato editorial

- `linkedin-david`
  - usar despues del benchmark si hay que traducir el aprendizaje al POV, tono o contenido de David

- `marca-personal-david`
  - usar cuando el benchmark impacte headline, perfil, narrativa, autoridad o posicionamiento de David

- `linear-delivery-traceability`
  - usar cuando el benchmark impacte un proyecto oficial de Umbral y haga falta dejar comentario, artefacto, siguiente accion y estado coherente

Si alguna no esta instalada, continuar manualmente y explicitar la sustitucion.

## Trazabilidad para proyectos del embudo
Si el benchmark cambia una decision del proyecto embudo:
- no declarar avance sin trazabilidad real
- dejar artefacto verificable
- dejar siguiente accion concreta
- dejar comentario de avance si el flujo del proyecto lo exige
- usar `linear-delivery-traceability` antes de afirmar progreso

## Referencias internas
Consultar segun necesidad:
- `references/teardown-template.md`
- `references/evidence-checklist.md`
- `references/linkedin-benchmark-format.md`

## Prompt de ejemplo
```text
Estudia este caso de LinkedIn en profundidad como benchmark para Umbral. Usa la fuente principal que te doy, busca una segunda fuente independiente del mismo caso y una tercera senal si existe. No cierres con una sola landing ni con una captura. Separa evidencia observada, inferencia e hipotesis. Haz teardown obligatorio de hook, promesa, audiencia implicita, framing, CTA, activo de captura, siguiente paso, continuidad observable y huecos no verificados. Cierra con que copiar conceptualmente, que no copiar, que adaptar, que probar primero y que evidencia falta antes de decidir.
```
