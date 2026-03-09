---
name: editorial-source-curation
description: curate recent items from authority sources into a ranked editorial shortlist
  before any derivative content is drafted. use when chatgpt needs to fetch or review
  the latest accessible items from gartner, mckinsey, every, and ruben substack; normalize
  them into a shared schema; score alignment against david's narrative, proposal,
  and audience; present a shortlist for human selection; and only then hand off to
  derivative-content workflows. also use when planning manual or semi-automated source
  monitoring with research, n8n, linkedin-content, or linkedin-david if those skills
  are installed. do not use this skill to promise scraping behind logins or paywalls,
  or automatic publishing without real tooling and permissions.
metadata:
  openclaw:
    emoji: 📚
    requires:
      env: []
---

# Editorial Source Curation

## Objetivo
Ayudar a Rick a convertir un lote de novedades de fuentes de autoridad en una decision editorial clara para David: que leer, que priorizar y que angulo derivar despues.

Trabajar siempre en dos fases separadas:
1. curar y puntuar fuentes
2. solo tras seleccion humana, derivar un brief o handoff de contenido

## Reglas de trabajo
- Priorizar items recientes, accesibles y con atribucion clara.
- Cubrir explicitamente Gartner, McKinsey, Every y Ruben Substack en cada barrido, salvo que el usuario cambie el alcance.
- Usar solo accesos y herramientas reales. No prometer scraping, bypass de paywalls, parsing de inboxes ni publicacion automatica si no existen permisos y tooling reales.
- Distinguir hechos de la fuente, interpretacion editorial y recomendacion.
- Pedir una sola aclaracion solo cuando falte una pieza critica para puntuar. Si no, trabajar con supuestos explicitos.
- No redactar post, thread, newsletter, carrusel ni guion antes de que David elija uno o mas items del shortlist.

## Baseline editorial
Antes de puntuar, fijar o inferir estas tres referencias:
- Narrativa de David: tesis, worldview, contrarian take e ideas que quiere repetir.
- Propuesta: oferta, servicio, producto, posicionamiento o CTA implicito.
- Audiencia: ICP lector o comprador, nivel de sofisticacion, pains y jobs-to-be-done.

Si faltan datos, inferir una baseline provisional en 3-5 bullets y marcarla como `assumption`.

## Source of truth recomendado
Cuando exista, tomar como fuente viva:

- la pagina Notion `Fuentes`
- la base hija `Fuentes confiables`
- la base `Referentes`

No tratar la lista de fuentes y la lista de referentes como si fueran lo mismo:

- fuentes de autoridad / research / mercado
- fuentes de industria / instituciones / estandares
- referentes de divulgacion / estilo / framing
- fuentes experimentales en observacion

## Cobertura de fuentes requerida
Mantener estas cuatro fuentes como minimo:
- Gartner
- McKinsey
- Every
- Ruben Substack

Para cada fuente:
- Preferir paginas oficiales, newsletters, posts o articulos accesibles con el tooling actual.
- Si existe contenido licenciado o de suscripcion y no es accesible, registrar el hueco como `inaccessible` y no fingir lectura.
- Si "Ruben Substack" es ambiguo, usar la URL o publicacion que David ya haya indicado. Si no existe, pedirla una vez o trabajar con el identificador textual y marcar la ambiguedad.

## Flujo de trabajo
### 1. Fetch
- Reunir los items mas recientes dentro de la ventana pedida por el usuario. Por defecto usar 30 dias.
- Buscar al menos 1-3 items por fuente cuando sea posible.
- Capturar fecha, titulo, URL, formato y una sintesis fiel de la tesis.
- Si la fuente no ofrece suficiente material en la ventana, ampliar a 60-90 dias y documentarlo.

### 2. Normalize
- Convertir cada item al esquema de `references/scoring-schema.md`.
- Deduplicar items casi iguales y fusionar versiones del mismo lanzamiento, informe o ensayo.
- Separar `source_claim`, `editorial_interpretation` y `why_now`.

### 3. Alignment scoring
- Aplicar la rubrica de `references/scoring-schema.md`.
- Puntuar narrativa, propuesta, audiencia, frescura, autoridad, novedad y potencial derivativo.
- Anotar supuestos, lagunas y riesgos de acceso o derechos.

### 4. Shortlist
- Ordenar por score total, pero ajustar por diversidad de angulos y evitar duplicados.
- Devolver una shortlist de 3-5 items usando `references/shortlist-format.md`.
- Incluir por que entra, por que ahora y que angulo podria explotar David.

### 5. Human selection
- Cerrar siempre con una decision explicita para David:
  - elegir 1 item
  - elegir 2 items para combinacion
  - pedir otra pasada con otro tema o ventana temporal
- No avanzar a contenido derivado sin esta seleccion.

## Fase manual antes de automatizar
Antes de proponer automatizacion n8n seria, validar que existe una fase manual estable:

- shortlist consistente durante 3-4 semanas
- criterios de scoring claros y repetibles
- al menos 2 fuentes con captura fiable
- baja ambiguedad al elegir piezas
- costo operativo manual suficientemente alto como para justificar automatizacion

Mientras eso no ocurra:

- no proponer autopublicacion
- no saltarse la shortlist humana
- no convertir referentes de divulgacion en scraping pesado

### 6. Derivative content
- Solo despues de la seleccion humana, producir:
  - un brief de contenido
  - posibles hooks o takes
  - un handoff a otra skill
- Si `linkedin-content` o `linkedin-david` estan instaladas, usarlas para el draft final o la adaptacion de voz.
- Si no estan instaladas, producir un brief estructurado listo para otra etapa.

## Composicion con otras skills
- `research`: usar para ampliar contexto, validar claims o encontrar supporting evidence alrededor de un item ya capturado. No reemplazar la cobertura explicita de las cuatro fuentes base.
- `n8n`: usar solo para disenar o documentar una automatizacion aprobada, como feeds, alertas, Airtable o Notion handoff, o scoring pipelines. No afirmar que ya existe una automatizacion operativa si no se creo realmente y no hay permisos.
- `linkedin-content`: usar despues de la seleccion humana para convertir el item elegido en estructura de post, carrusel o brief social.
- `linkedin-david`: usar despues de la seleccion humana para afinar POV, tono, audience-fit y CTA de David.

Si alguna de estas skills no esta instalada, continuar manualmente y explicitar la sustitucion.

## Entregables por defecto
Entregar en este orden:
1. `coverage note`: ventana temporal, fuentes cubiertas, huecos y restricciones
2. `normalized set`: tabla compacta de items
3. `shortlist`: 3-5 opciones rankeadas
4. `selection request`: que debe decidir David
5. tras seleccion, `derivative brief`

## Formato de salida
Usar este orden salvo que el usuario pida otro:
1. resumen ejecutivo de 3-5 lineas
2. coverage note
3. normalized set, como tabla compacta o bullets densos
4. shortlist
5. seleccion solicitada
6. si ya hubo seleccion, brief derivativo

## Criterios de calidad
- Priorizar senal sobre volumen.
- No inflar el score si el item es prestigioso pero poco alineado.
- Favorecer items que permitan una opinion, traduccion o aplicacion util para la audiencia de David.
- Penalizar piezas demasiado genericas, viejas, duplicadas o dificiles de atribuir.
- Cuando el mejor item no sea el mas obvio, explicar la decision en una linea.

## Prompts de ejemplo
Curacion inicial:
```text
Trae los latest items de Gartner, McKinsey, Every y Ruben Substack sobre AI agents para servicios B2B. Normaliza, puntua alineacion con la narrativa de David sobre leverage operativo para equipos pequenos, arma shortlist de 4 y no redactes contenido todavia.
```

Despues de la seleccion:
```text
Usa el shortlist #2 y prepara un derivative brief para LinkedIn. Si esta disponible, apoyate en linkedin-david para el POV y en linkedin-content para la estructura. No publiques ni asumas automatizacion.
```

## Referencias
- Usar `references/scoring-schema.md` para el esquema normalizado y la rubrica.
- Usar `references/shortlist-format.md` para el formato de shortlist y el handoff posterior.

