# Plan Del Pipeline De Publicaciones LinkedIn

> **Estado**: solo diseno, cero codigo.
> **Owner natural**: `rick-linkedin-writer`, orquestado por `rick-orchestrator`.
> **Restriccion arquitectonica**: disenar encima de la topologia Rick, Ola 1 ya en runtime (`3cbf344`, segun David). No disenar esto como `worker/` tasks paralelas.
> **Estado Notion lectura/escritura**: bloqueado hasta que el audit `2026-05-05-006-copilot-vps-audit-rick-notion-mcp-integration.md` defina que token escribe en que superficie.

## 1. Vision

Este pipeline no es solo un generador de posts. Es un sistema de transformacion editorial.

La idea es:

1. Leer la base de referentes de David.
2. Descubrir publicaciones nuevas de esos referentes en las plataformas donde publican.
3. Seleccionar la publicacion/referencia mas relevante segun el perfil de David.
4. Si hace falta, combinar esa referencia con una noticia o referencia AEC.
5. Agregar vision, criterio, posicionamiento comercial y estilo comunicacional de David.
6. Generar una o dos variantes candidatas.
7. Guardar el candidato en la base de publicaciones con trazabilidad.
8. Permitir que David seleccione una alternativa.
9. Despues de la seleccion, activar una futura generacion visual para LinkedIn con Nano Banana 2.

La generacion actual de muchas variantes en CAND-002/CAND-003 sirve para afinar el redactor. El modo de produccion deseado es mas pequeno: normalmente una o dos variantes fuertes, no diez.

## 2. Superficies Notion

### Fuente: referentes

- URL: `https://www.notion.so/umbralbim/05f04d48c44943e8b4acc572a4ec6f19?v=71d3f67ec4214b898cf1f43e3c034e2f&source=copy_link`
- Funcion real verificada via MCP: base `👤 Referentes`, no feed de publicaciones.
- Data source: `collection://afc8d960-086c-4878-b562-7511dd02ff76`.
- Contiene personas con propiedades como `Nombre`, `Categoría`, `Expertise`, `Plataformas`, `LinkedIn`, `Arquetipo`, `Estilo Narrativo`, `Idioma`, `País`, `Seguidores`, `Modelo de Monetización` y `Técnicas Clave`.
- Schema canónico extendido el 2026-05-05 con 10 columnas de canales cargadas vía Notion AI a partir de investigación OSINT (Perplexity Deep Research):
  - `LinkedIn activity feed` (URL): feed de actividad, formato `<perfil>/recent-activity/all/`.
  - `YouTube channel` (URL): canal, formato `@handle`.
  - `Web / Newsletter` (URL): sitio personal, blog o Substack canónico.
  - `RSS feed` (URL): solo si verificable; algunos referentes pueden quedar con flag `RSS_NO_CONFIRMADO`.
  - `Otros canales` (Text): X, Instagram, Patreon, GitHub, Medium, etc., separados por ` · `.
  - `Última actividad detectada` (Text): `MMM YYYY` o `NO VERIFICADO`.
  - `Confianza canales` (Select): `ALTA`, `MEDIA`, `BAJA`, `DUPLICADO`.
  - `Flags canales` (Multi-select): `ACTIVIDAD_BAJA`, `POSIBLE_INACTIVO`, `SLUG_DIFIERE`, `DUP`, `RSS_NO_CONFIRMADO`, `REQUIERE_VERIFICACION_MANUAL`, `SIN_LINKEDIN`, `CAMBIO_DE_PLATAFORMA`.
  - `Notas canales` (Text).
  - `Última auditoría canales` (Date): primera carga `2026-05-05`.
- `LinkedIn activity feed` es la fuente de verdad para el Stage 1 cuando se busque actividad LinkedIn. No inferir el feed desde el slug del perfil ni desde `LinkedIn`; leer la columna explícita.
- Hallazgos de la primera carga: 26 referentes efectivos; 1 duplicado confirmado (Pascal Bornet en filas `yourpascal` y `pascalbornet`, canonico `pascalbornet`); 1 referente sin LinkedIn (Jose Luis Crespo / QuantumFracture); 5 referentes con confianza baja o verificacion manual; Lucas Dalto usa `ar.linkedin.com`; Pascal Bornet publica en LinkedIn Pulse y Substack en paralelo; Andrew Ng, Ruben Hassid, Pascal Bornet y Bernard Marr son candidatos razonables para primera oleada de calibracion por RSS publico o LinkedIn Pulse de mayor cadencia.
- Uso esperado: solo lectura hasta que el audit Notion MCP confirme limites de acceso.

### Capa faltante: publicaciones recientes de referentes

La base de referentes dice **quien seguir** y en que plataformas publica, pero no contiene necesariamente las publicaciones recientes que alimentan el pipeline.

El pipeline necesita una capa adicional:

- Descubrir publicaciones nuevas por referente.
- Guardar o cachear esas publicaciones con URL, fecha, plataforma, extracto, tema y estado de procesamiento.
- Evitar procesar la misma publicacion dos veces.
- Mantener trazabilidad desde candidato final hasta referente y publicacion original.

La base ya contiene canales de publicacion por referente. Sigue pendiente definir si las publicaciones descubiertas se cachean en una base separada o en una superficie temporal de dry-run.

### Destino: candidatos de publicacion

- URL: `https://www.notion.so/umbralbim/e6817ec4698a4f0fbbc8fedcf4e52472?v=8ae76db01b7c453aaef3edb8093fb5c8&source=copy_link`
- Funcion: guardar candidatos editoriales generados.
- Uso esperado: escritura bloqueada hasta que el audit Notion MCP defina el token, herramienta y superficie autorizados.

## 3. Mapa De Responsabilidades Por Subagente

| Componente | Responsabilidad | Puede leer | Puede escribir | No debe hacer |
|---|---|---|---|---|
| `rick-orchestrator` | Orquestar secuencia, handoffs humanos y routing entre subagentes. | Estado del pipeline, brief del candidato, estado del audit. | Handoffs y artefactos de planificacion cuando este autorizado. | Redactar copy final directamente, saltarse `rick-linkedin-writer`, aprobar publicacion, marcar gates. |
| `rick-linkedin-writer` | Seleccion de fuentes, transformacion editorial, combinacion AEC, adaptacion a voz David y redaccion candidata. | Referencias, posible noticia AEC complementaria, perfil/voz David, trazabilidad. | Payloads de candidatos y specs de pagina Notion cuando este autorizado. | Escribir directamente en Notion antes del audit, generar imagenes, publicar, marcar gates. |
| `rick-communication-director` | Revisar angulo, estrategia narrativa, audiencia, voz y alineacion con marca/comercial. | Drafts, trazabilidad, racional de transformacion. | Veredictos, recomendaciones y microedits. | Convertirse en redactor principal o selector de fuentes. |
| `rick-qa` | Validar claims, trazabilidad, gates, seguridad de publicacion, terminos prohibidos y disciplina de fuentes. | Payload del candidato, source trace, mapa de claims. | Veredicto QA y flags de riesgo. | Aprobar publicacion o resolver claims ambiguos sin evidencia. |
| `rick-orchestrator` + David | Loop de decision humana despues de crear candidatos. | Shortlist, pagina candidata, trazabilidad, brief visual. | Senal de seleccion/aprobacion solo mediante contrato explicito. | Inferir aprobacion por existencia de pagina o comentario ambiguo. |
| Futura tool `nano-banana-2` | Generar visual LinkedIn despues de seleccion humana. | Candidato seleccionado y brief visual. | Asset visual y metadata cuando este autorizado. | Ejecutarse antes de seleccion, publicar imagen, inferir direccion visual sin brief. |

## 4. Etapas Del Pipeline

### Etapa 0: Leer catalogo de referentes

El input inicial es la base `👤 Referentes`. Esta etapa lee el catalogo de personas, etiquetas, plataformas y links disponibles.

Bloqueado por audit Notion MCP:

- Que actor lee la base de referentes.
- Que token/superficie esta autorizado.
- Si Rick lee Notion via MCP, API directa o herramienta OpenClaw.

Salida:

- Lista de referentes activos.
- Plataformas por referente.
- Links disponibles por referente.
- Etiquetas de relevancia: `Categoría`, `Expertise`, `Arquetipo`, `Idioma`, `Estilo Narrativo`.
- Referentes sin links suficientes para discovery.

### Etapa 1: Descubrir publicaciones nuevas de cada referente

Esta etapa busca publicaciones recientes de los referentes leidos en la etapa 0. El input ya no es una lista hardcodeada ni scraping ciego de LinkedIn. El input es una query read-only a la DB `👤 Referentes` filtrando:

- `Confianza canales` en `{ALTA, MEDIA}`.
- `Flags canales` no contiene `POSIBLE_INACTIVO`.
- Al menos una columna de canal poblada: `LinkedIn activity feed` OR `YouTube channel` OR `RSS feed` OR `Web / Newsletter`.

Si `Confianza canales = DUPLICADO`, saltar la fila. No procesar duplicados.

Fuentes posibles por referente:

- LinkedIn si existe `LinkedIn activity feed`.
- LinkedIn Pulse si se detecta desde actividad o fuente asociada.
- YouTube si existe `YouTube channel`.
- Newsletter/Substack o web/blog si existe `Web / Newsletter`.
- RSS si existe `RSS feed` y no requiere verificacion manual.
- X/Twitter, Instagram, Patreon, GitHub, Medium u otros desde `Otros canales`, solo si hay tool/metodo autorizado.

#### Etapa 1a: Channel fan-out

Por cada referente seleccionado, expandir a sus canales activos. Un referente puede generar N candidatos de publicacion si publica en multiples canales.

Ejemplo: si un referente tiene LinkedIn Pulse y Substack en paralelo, ambos canales deben monitorearse como fuentes posibles. La deduplicacion por contenido queda como decision abierta.

Salida:

- Lista de publicaciones nuevas candidatas.
- Referente asociado.
- URL canonica.
- Plataforma.
- Canal de origen normalizado.
- URL del canal de origen copiada desde la columna correspondiente en `👤 Referentes`.
- Snapshot de `Confianza canales`.
- Fecha aproximada o fecha verificada.
- Titulo/extracto.
- Tema detectado.
- Etiquetas inferidas.
- Estado: `nuevo`, `ya procesado`, `sin acceso`, `requiere revision manual`.

Restricciones:

- No scraping agresivo ni bypass de plataformas.
- Si LinkedIn u otra plataforma no permite lectura automatica estable, marcar como `sin acceso` o requerir captura/manual/API aprobada.
- No inventar contenido de una publicacion si solo se conoce el perfil del referente.

### Etapa 2: Ranking de relevancia

`rick-linkedin-writer` puntua las referencias nuevas contra el perfil de David y la estrategia editorial actual.

Salida:

- Publicacion/referencia principal seleccionada.
- Razonamiento del ranking.
- Motivos por los que las publicaciones descartadas no fueron elegidas.

### Etapa 3: Chequeo de combinacion AEC

Si la referencia seleccionada no pertenece al sector AEC, el writer debe buscar entre los candidatos una noticia o referencia AEC que pueda combinarse sin forzar la conexion.

Si la referencia ya es AEC, puede quedar como transformacion de una sola fuente. Tambien puede combinarse con otra noticia solo si esa segunda fuente agrega contexto, tension u operacionalizacion clara.

Salida:

- `single_reference` o `combined_reference`.
- Explicacion de por que la combinacion es necesaria o innecesaria.
- Chequeo explicito de conexion no forzada.

### Etapa 4: Vision David y alineacion comercial

El writer agrega perspectiva de David solo cuando esta justificada por la fuente y por su posicionamiento.

Salida:

- Tesis o punto de vista de David.
- Relevancia comercial, si corresponde.
- Limites: que no se debe afirmar.

### Etapa 5: Redaccion candidata

El writer produce una o dos candidatas de publicacion. Deben ser suficientes para decidir, no exploracion masiva.

Salida:

- Candidata LinkedIn.
- Version X opcional.
- Diferencia en una frase entre variantes.
- Source trace.
- Transformation trace.
- Riesgos y preguntas abiertas.

### Etapa 6: Revision y QA

`rick-communication-director` revisa narrativa y fit. `rick-qa` valida claims, trazabilidad, seguridad y gates.

Salida:

- Variante recomendada.
- Variante reserva opcional.
- Microedits requeridos.
- `ready_for_publication: false` salvo aprobacion explicita posterior de David.

### Etapa 7: Creacion del candidato en Notion

Bloqueada hasta que el audit Notion MCP resuelva la autoridad de escritura.

Cuando se desbloquee, Rick guarda el candidato en la base de publicaciones con layout navegable estilo CAND-004:

- Premisa.
- Mapa del discurso.
- Resumen de alternativas.
- Texto candidato.
- Trazabilidad.
- QA/gates.
- Seccion de decision humana.

### Etapa 8: Seleccion humana

David selecciona una candidata mediante un contrato explicito. El contrato todavia no esta definido.

Opciones posibles:

- Propiedad de estado, por ejemplo `Seleccionado para imagen`.
- Checkbox, por ejemplo `generar_imagen`.
- Comentario comando, por ejemplo `Rick: generar imagen con esta alternativa`.
- Relacion o ticket dedicado en una base de produccion visual.
- Webhook desde automatizacion Notion.

Decision abierta.

### Etapa 9: Generacion de imagen

Despues de una seleccion explicita, Rick genera un brief visual y usa una futura herramienta Nano Banana 2.

Este plan no implementa esa herramienta. Solo declara el requisito futuro.

## 5. Criterios 1/2/3 Como Texto Para `SKILL.md`

El siguiente texto esta escrito para poder migrarse despues a `SKILL.md` de `rick-linkedin-writer`, una vez aprobada la arquitectura.

### Prepaso: descubrir publicaciones antes de seleccionar

Antes de aplicar los criterios 1/2/3, no asumas que la base `👤 Referentes` contiene publicaciones listas. Esa base contiene personas, etiquetas, plataformas y algunos links.

Primero debes convertir el catalogo de referentes en un conjunto de publicaciones candidatas:

- Leer referentes activos y sus propiedades.
- Identificar en que plataformas publica cada uno.
- Usar links disponibles, empezando por `LinkedIn`.
- Buscar publicaciones recientes solo con herramientas autorizadas.
- Registrar URL, fecha, plataforma, extracto y referente.
- Marcar como `sin acceso` cuando una plataforma no pueda leerse de forma segura.
- No inventar publicaciones desde la descripcion del referente.

### Criterio 1: seleccionar la referencia mas relevante para David

Cuando ya tengas publicaciones candidatas descubiertas desde los referentes de David, selecciona primero la publicacion/referencia mas relevante para su perfil editorial.

Evalua relevancia segun:

- Encaje con los dominios de David: AEC, BIM, automatizacion, IA aplicada al trabajo profesional, interoperabilidad, flujos de datos, productividad en construccion, coordinacion y toma de decisiones operativas.
- Encaje con la voz de David: practica, tecnico-operativa, clara, anti-slop y alejada del futurismo generico.
- Encaje con la direccion comercial de Umbral: consultoria, automatizacion, sistemas BIM/datos, flujos con IA, educacion y credibilidad de implementacion.
- Frescura y utilidad de la publicacion: suficientemente reciente para entrar en la conversacion actual, pero no elegida solo por ser nueva.
- Potencial de transformacion: la referencia debe permitir que David diga algo con criterio propio, no solo resumir.
- Valor para la audiencia: el post resultante debe ayudar a BIM managers, lideres AEC, consultores, coordinadores tecnicos o responsables de transformacion digital a ver una decision con mas claridad.

No elijas una publicacion solo porque es viral, famosa o facil de reescribir. Elige la que pueda convertirse en una idea editorial util en voz de David.

### Criterio 2: combinar con AEC solo cuando crea un puente real

Despues de seleccionar la referencia mas fuerte:

- Si la referencia no es AEC, busca una segunda referencia candidata que si sea relevante para AEC.
- Combinalas solo si el puente es real: mecanismo compartido, problema compartido, consecuencia operativa compartida o contraste util.
- Si el puente se siente forzado, no combines. Transforma la referencia no AEC en una lectura util para AEC sin fingir que viene del sector.
- Si la referencia ya es AEC, mantenla como candidata de una sola fuente salvo que otra referencia actual agregue contexto, tension u operacionalizacion clara.
- No combines dos referencias solo para parecer mas investigado.

La combinacion debe hacer que el post final sea mas claro, mas aterrizado o mas util. Si solo agrega complejidad, rechaza la combinacion.

### Criterio 3: agregar vision de David y alineacion comercial

Despues de seleccionar la fuente y la posible referencia AEC complementaria, agrega perspectiva de David.

La vision de David debe:

- Reencuadrar la fuente como una decision operativa AEC/BIM.
- Agregar criterio, no solo comentario.
- Conectar tecnologia con proceso, datos, coordinacion, adopcion o calidad de decision.
- Evitar lenguaje de consultoria generica, claims inflados y marcos tipo "la IA lo cambia todo".
- Alinearse comercialmente solo cuando sea pertinente. Si el post no conecta naturalmente con la oferta de Umbral, no fuerces un angulo de venta.
- Mantener primero el problema del lector y despues la oferta de David.

La alineacion comercial puede aparecer como:

- Una forma sutil de nombrar el tipo de problemas que Umbral resuelve.
- Una pregunta practica que revela la necesidad de mejores sistemas.
- Un cierre que abre conversacion sin convertirse en pitch.

No conviertas todos los posts en piezas de venta.

## 6. Requisitos De La Pagina Candidata

Cada candidato guardado en la base de publicaciones debe incluir:

- ID del candidato.
- Referente original.
- Referencia o referencias usadas.
- URL de publicacion original.
- Plataforma.
- `source_channel`, con valores enumerados: `linkedin_activity`, `linkedin_pulse`, `youtube`, `rss`, `substack`, `web_blog`, `x_twitter`, `otro`.
- `source_channel_url`, copiado tal cual desde la columna correspondiente de `👤 Referentes`.
- `referente_canal_confianza`, snapshot del valor `Confianza canales` al momento de la deteccion.
- Fecha de publicacion o fecha de captura.
- Por que se selecciono la fuente.
- Si se uso o no una referencia AEC complementaria.
- Por que la combinacion fue aceptada o rechazada.
- Vision David.
- Relevancia comercial, si existe.
- Candidata LinkedIn, normalmente una o dos variantes.
- Diferencia entre variantes.
- Trazabilidad:
  - fuentes;
  - transformacion;
  - evidencia;
  - inferencia;
  - hipotesis;
  - estrategia narrativa;
  - decisiones;
  - riesgos;
  - cadena de custodia.
- Estado QA.
- Estado de seleccion humana.
- Gates de publicacion, todos falsos por defecto.

## 7. Tools Necesarias

### Requeridas, bloqueadas por audit

| Tool / capacidad | Funcion | Estado |
|---|---|---|
| Lectura Notion de base de referentes | Leer personas, etiquetas, plataformas y links de referentes. | Bloqueado por `2026-05-05-006-copilot-vps-audit-rick-notion-mcp-integration.md`. |
| Escritura Notion en base de publicaciones | Guardar candidatos en `Publicaciones`. | Bloqueado por el mismo audit. |
| Readback Notion de pagina/bloques | Verificar estructura del candidato y gates. | Bloqueado por el mismo audit. |
| Discovery de publicaciones por referente | Encontrar publicaciones recientes en LinkedIn, X, YouTube, newsletter, web/RSS u otras plataformas autorizadas. | Tool/capacidad pendiente; no implementar hasta definir acceso y limites. |
| Cache de publicaciones descubiertas | Evitar duplicados y conservar trazabilidad entre referente, publicacion y candidato. | Decision abierta: misma DB vs DB separada. |

### Requeridas dentro de Rick/OpenClaw

| Tool / capacidad | Funcion | Estado |
|---|---|---|
| Routing de `rick-orchestrator` | Orquestar writer, communication director, QA y handoff humano. | Debe usar topologia existente. |
| Skill de `rick-linkedin-writer` | Contener criterios 1/2/3 y redaccion. | Requiere update de skill despues de aprobar el plan. |
| Lectura read-only de las 10 columnas nuevas de `👤 Referentes` via Notion MCP | Alimentar Stage 1 con canales, confianza, flags y fecha de auditoria. | Requerida antes de codear Stage 1; bloqueada por audit 006 para runtime. |
| `rick-communication-director` | Revisar estrategia narrativa y fit de voz. | Patron existente. |
| `rick-qa` | Validar claims, trazabilidad, gates y seguridad. | Patron existente. |

### Tool futura

| Tool / capacidad | Funcion | Estado |
|---|---|---|
| Nano Banana 2 image generation | Generar imagen LinkedIn despues de que David seleccione candidata. | Tool nueva pendiente. No implementar en este plan. |
| Validador HTTP de RSS feeds | Resolver flags `RSS_NO_CONFIRMADO` antes de incluir un feed en el polling de Stage 1. | Tool futura; no implementar en este plan. |

## 8. Fuera De Scope Explicito

- No implementar worker tasks.
- No hacer integracion directa con Notion antes del audit Notion MCP.
- No automatizar publicacion.
- No publicar en LinkedIn.
- No implementar generacion de imagen.
- No inferir gates ni aprobaciones desde la creacion de una pagina.
- No usar generacion masiva de variantes como default productivo.
- No reemplazar paginas CAND-002/CAND-003 hasta que David apruebe el formato tipo CAND-004.

## 9. Decisiones Abiertas

1. **Autoridad de lectura/escritura Notion**: que token/tool lee referentes y escribe candidatos. Bloqueado por `2026-05-05-006-copilot-vps-audit-rick-notion-mcp-integration.md`.
2. **Modelo de datos para publicaciones de referentes**: DECIDIDA 2026-05-05: schema extendido in-place en DB Referentes con 10 columnas nuevas (ver §2). No se creó base separada. Publicaciones descubiertas en runtime van a `Publicaciones de Referentes` o a cache temporal de dry-run (decisión abierta en #5).
3. **Campos de fuentes por referente**: PARCIALMENTE CERRADA 2026-05-05: agregadas YouTube channel, Web/Newsletter, RSS feed. Pendientes solo: X/Twitter URL, Medium URL, GitHub URL, Podcast URL (hoy en `Otros canales` como rich_text). Reabrir cuando un referente real lo requiera.
4. **Discovery por plataforma**: que metodo se permite para leer publicaciones recientes de LinkedIn, X, YouTube, newsletters y web/RSS sin violar limites ni depender de scraping fragil.
5. **Cache y deduplicacion**: donde guardar publicaciones ya procesadas, fechas de captura, hash/URL canonica y estado.
6. **Contrato de seleccion humana**: David selecciona por status, checkbox, comentario, relacion/ticket o webhook.
7. **Contrato de trigger de imagen**: que senal exacta le indica a Rick que debe generar la imagen LinkedIn.
8. **Owner del brief visual**: lo crea `rick-linkedin-writer` o un futuro subagente visual.
9. **Limites de Nano Banana 2**: inputs permitidos, lugar de almacenamiento de outputs, licencias y safety.
10. **Cantidad de variantes**: el default debe ser una o dos, pero falta definir cuando se generan dos en vez de una.
11. **Politica de re-validacion de canales**: cada cuanto re-auditar `Última auditoría canales` (propuesta: trimestral), quien dispara la re-auditoria y como se reflejan referentes que pasan a `POSIBLE_INACTIVO`.
12. **Politica frente a duplicados**: proceso de consolidacion cuando `Confianza canales = DUPLICADO` (hoy hay 1 caso: Pascal Bornet; canonico = `pascalbornet`). Definir si Stage 1 lo ignora silenciosamente o lo reporta a un dashboard de gobernanza.
13. **Multi-canal por referente**: cuando un referente tiene LinkedIn Pulse + Substack (caso Pascal Bornet), definir si se generan dos candidatos separados por publicacion o si se deduplican por `content_hash`.

## 10. Recomendacion De Modelo De Datos Para Referentes Y Publicaciones

La base `👤 Referentes` debe seguir siendo el catalogo de personas. No conviene convertirla en feed de publicaciones porque mezclaria identidad del referente con items temporales.

Recomendacion preferida:

1. Mantener `👤 Referentes` como base canonica de personas.
2. Schema actual de `👤 Referentes` ya cubre el caso (ver §2). Decisión pendiente solo en §9.5 (Cache y deduplicación): si las publicaciones descubiertas van a una base separada `Publicaciones de Referentes` o a un cache temporal de dry-run. Columnas extra por plataforma (X/Twitter, Medium, GitHub, Podcast) se agregarán cuando un referente real lo requiera, no preventivamente.

Campos sugeridos para `Publicaciones de Referentes`:

| Campo | Funcion |
|---|---|
| `Titulo` | Titulo o primer texto identificable de la publicacion. |
| `Referente` | Relacion a `👤 Referentes`. |
| `URL` | URL canonica de la publicacion. |
| `Plataforma` | LinkedIn, X, YouTube, Newsletter, Web/RSS, etc. |
| `Fecha publicacion` | Fecha si se puede verificar. |
| `Fecha captura` | Fecha en que Rick la encontro. |
| `Extracto` | Resumen breve o fragmento permitido. |
| `Tema detectado` | IA, BIM, datos, automatizacion, AEC, etc. |
| `Es AEC` | Checkbox o select. |
| `Estado pipeline` | nuevo, evaluado, usado, descartado, sin acceso, requiere revision manual. |
| `Hash/ID externo` | Para deduplicar. |
| `Candidato generado` | Relacion opcional a `Publicaciones`. |

Alternativa minima:

- Si no se quiere crear una base nueva todavia, agregar en `👤 Referentes` campos de URL por plataforma y dejar la captura de publicaciones como output temporal del dry-run.
- Esta alternativa es mas simple, pero no deja historial ni deduplicacion robusta.

## 11. Secuencia De Implementacion Despues De Aprobar

1. Terminar y revisar el audit de integracion Notion MCP.
2. Decidir contrato de lectura/escritura Notion.
3. Ejecutar smoke test REST read-only via worker runtime con `NOTION_API_KEY` de lectura de las 10 columnas nuevas de `👤 Referentes`. Este gate valida la autoridad runtime real que usará Rick en Stage 1; no valida una integración externa ni un MCP Notion nativo, porque el audit 006 confirmó que ese path no existe hoy. Criterios de éxito del smoke test (verificados contra schema real vía Notion MCP, data_source_id `afc8d960-086c-4878-b562-7511dd02ff76`): (a) lectura exitosa de las 10 columnas nuevas en al menos 3 filas con perfiles distintos: 1 con `Confianza canales = ALTA`, 1 con `MEDIA`, 1 con `Confianza canales = DUPLICADO`; (b) count total de la base = 26; (c) `LinkedIn activity feed` parsea como URL válida cuando está poblada; (d) `Confianza canales` devuelve uno de los 4 valores enumerados reales: `ALTA` / `MEDIA` / `BAJA` / `DUPLICADO`; (e) `Flags canales` solo contiene valores del enum real: `ACTIVIDAD_BAJA` / `POSIBLE_INACTIVO` / `SLUG_DIFIERE` / `DUP` / `RSS_NO_CONFIRMADO` / `REQUIERE_VERIFICACION_MANUAL` / `SIN_LINKEDIN` / `CAMBIO_DE_PLATAFORMA`. Nota: la señal de dedup primaria es `Confianza canales = DUPLICADO`, no `DUP` en `Flags canales` (este último es informativo). Falla si cualquiera de los 5 no se cumple.
4. Marcar ese smoke test como dependencia HARD del primer commit de codigo de Stage 1.
5. Decidir modelo de datos para publicaciones de referentes: cache separada o superficie temporal de dry-run.
6. Definir metodo permitido de discovery por plataforma.
7. Actualizar skill de `rick-linkedin-writer` con prepaso de discovery y criterios 1/2/3.
8. Agregar o actualizar calibraciones para transformacion de fuentes y combinacion AEC.
9. Correr dry-run con algunos referentes sin escribir en Notion.
10. Correr dry-run con una o dos publicaciones descubiertas sin crear candidato.
11. Validar con `rick-communication-director` y `rick-qa`.
12. Crear una pagina candidata en `Publicaciones` usando layout tipo CAND-004.
13. Probar contrato de seleccion humana.
14. Solo despues definir el handoff de imagen con Nano Banana 2.

## 12. Criterios De Aceptacion Del Plan

- Las responsabilidades estan asignadas a subagentes Rick, no a worker tasks.
- La base `👤 Referentes` queda correctamente tratada como catalogo de personas, no como feed de publicaciones.
- El plan incluye una etapa explicita para descubrir publicaciones recientes por referente.
- El plan declara una decision abierta sobre si las URLs/plataformas se agregan a la misma DB o a una base separada.
- El pipeline ignora filas con `Confianza canales` en `{BAJA, DUPLICADO}` y referentes con flag `POSIBLE_INACTIVO` en Stage 1.
- Cada candidato generado tiene `source_channel` y `source_channel_url` poblados; rechazar candidatos sin trazabilidad de canal de origen.
- Los criterios 1/2/3 estan escritos de forma copiable a `SKILL.md`.
- La lectura/escritura Notion queda bloqueada hasta resolver autoridad en el audit MCP.
- Nano Banana 2 queda declarada como tool futura, no implementada.
- La seleccion humana y el trigger de imagen quedan como decisiones abiertas explicitas.
- El plan soporta una o dos variantes productivas, y trata la generacion masiva como calibracion del writer.

## Changelog del plan

- 2026-05-05 — Codex — Stage 1 reanclado a la DB Referentes extendida (10 columnas nuevas, 26 filas, 1 duplicado, 1 sin LinkedIn). Sin cambios en vision, responsabilidades ni criterios. 3 open decisions nuevas (9.11, 9.12, 9.13). Smoke test de lectura MCP read-only agregado como dependencia HARD del primer commit de Stage 1.
- 2026-05-05 (post-merge): cleanup §9.2/§9.3 (decididas), §10 actualizado al schema vigente, §11.3 con criterios de éxito explícitos. Sin cambios funcionales al diseño.
- 2026-05-05 (fix #283): §10 elimina item 3 incoherente con item 2; §11.3 corrige enums (`DUPLICADO` está en `Confianza canales` no en `Flags canales`; enum real ALTA/MEDIA/BAJA/DUPLICADO; agregado criterio (e) sobre `Flags canales`). Verificado contra schema real vía Notion MCP; `data_source_id = afc8d960-086c-4878-b562-7511dd02ff76`.
- 2026-05-05 (fix #283 cross-ref, observación de Codex): §9.2 y §10 item 2 corregían cross-reference a `§9.11` (re-validación de canales) cuando la decisión real sobre base separada vs cache temporal vive en `§9.5` (Cache y deduplicación). Cambiado a `#5` / `§9.5`.
- 2026-05-05 (Stage 1 smoke authority): §11.3 cambia de "MCP read-only" a "REST read-only vía worker con `NOTION_API_KEY`" porque el audit `2026-05-05-006-copilot-vps-audit-rick-notion-mcp-integration.md` confirmó que Rick no tiene MCP Notion nativo hoy. El gate valida la autoridad runtime real que usará Stage 1.
