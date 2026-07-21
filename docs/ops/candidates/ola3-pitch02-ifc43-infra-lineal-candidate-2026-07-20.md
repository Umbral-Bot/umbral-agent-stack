# CAND-OLA3-02 — En infraestructura lineal, IFC 4.3 cierra el hueco del formato: el que queda es de proceso

> **Estado:** candidato editorial **(Borrador)** — entregable **docs-only**.
> Amplía **solo** `PITCH-OLA3-02` de `docs/ops/ola3-editorial-5-pitches-2026-07-20.md`
> por **GO humano de ampliación** de David (selección: únicamente el pitch 02).
> **No** publica (blog/Azure/LinkedIn/X), **no** abre gates humanos, **no** escribe
> en Notion, **no** activa runtime de Rick, **no** genera imágenes (stage8) ni
> POST LinkedIn (stage9c). Guards Ola 2 (`stage9c`/`stage8`) intactos.
> Base en `main`: **`165f441c`** (PR #545 — Ola 3, smoke + 5 pitches).
> Fuente del pitch: `docs/ops/ola3-editorial-5-pitches-2026-07-20.md` §PITCH-OLA3-02.
> Smoke del pipeline: `docs/ops/ola3-editorial-smoke-note-2026-07-20.md` (**PASS**, no rehecho).
> Plantilla: `docs/ops/rick-editorial-candidate-payload-template.md`.
> Flujo aplicado: `docs/ops/editorial-agent-flow.md` **pasos 1–6** (diseño). **NO** pasos 7–10 (registro Notion / gates / publicación).
> ADRs aplicables: `ADR-007` (Notion hub), `ADR-010` (Azure blog CMS), `ADR-011` (orquestación editorial).

---

## 0. Cómo leer este documento

Este es el **candidato completo** de un pitch: rellena la plantilla `rick-editorial`
con contenido editorial real (tesis, ángulo, borrador de blog, teasers, brief
visual) para que **David lo revise**. No es el artículo final publicable ni un
registro de Notion. Los **gates humanos permanecen en `false`** y así deben quedar
hasta que David decida lo contrario en un GO posterior.

Disciplina de fuente aplicada (por `docs/ops/editorial-source-attribution-policy.md`):
lo **verificable** va anclado a fuente primaria; lo demás va marcado como
**opinión / contexto / pendiente de fuente primaria**. No se inventan cifras (%/USD),
mandatos de licitación, datos de clientes ni URLs.

> **Tesis única del pitch 02 (no diluir):** con IFC 4.3 el hueco ya **no** es el
> formato; queda el **proceso**. El material sobre "definir antes de automatizar"
> se mantiene **subordinado** a esa tesis, no como un segundo argumento (esa es la
> tesis de `PITCH-OLA3-05`, fuera de alcance de este GO).

---

## 1. Payload `rick-editorial` (campos de la plantilla)

```yaml
# --- Identity ---
publication_id: "CAND-OLA3-02"
title: "En infraestructura lineal, IFC 4.3 cierra el hueco del formato: el que queda es de proceso"
trace_id: "CAND-OLA3-02-ifc43-infra-lineal-candidate"

# --- Classification ---
estado: Borrador
canal: "blog"                         # canal sugerido (autoridad evergreen)
tipo_de_contenido: "blog_post"
etapa_audiencia: "consideration"      # sugerencia; ver §Pendiente humano
prioridad: "media"                    # pitch 02: "usar ahora / esperar"

# --- Editorial content ---
claim_principal: >-
  Con IFC 4.3 aprobado como ISO 16739-1:2024, la infraestructura lineal
  (rail, carretera, puente, puerto y vías navegables; IfcAlignment) entra por
  primera vez al esquema IFC abierto. Al desaparecer la explicación histórica de
  las entregas fragmentadas en obra lineal —"no había estándar abierto para esto"—
  el bloqueo se ve donde siempre estuvo: en el proceso. Queda una pregunta de
  proceso, no de formato: qué información del modelo intercambiado necesita cada
  decisión de coordinación, definida antes de automatizar cualquier comprobación.
angulo_editorial: >-
  Proceso-primero aplicado a obra lineal. El estándar es precondición del
  intercambio trazable, no sustituto de definir qué debe sobrevivir al handover y
  para qué decisión sirve. La pieza no celebra el estándar: muestra que, cuando el
  formato deja de faltar, lo que queda expuesto es la falta de definición del proceso.
premisa: >-
  El estándar cerró el hueco del formato en obra lineal. El hueco que queda es de
  proceso, y ese nadie lo cierra por ti.
resumen_fuente: >-
  IFC 4.3 fue publicado como ISO 16739-1:2024 (edición 2 del esquema de datos IFC),
  incorporando por primera vez la infraestructura horizontal/lineal —puentes,
  carreteras, ferrocarriles, vías navegables y puertos, más elementos comunes como
  la alineación (IfcAlignment), terreno y movimiento de tierras—. Los túneles
  (IfcTunnel) NO entran en IFC 4.3: se difirieron a la extensión IFC 4.4. Es una
  fuente primaria citable (estándar oficial de ISO / buildingSMART). La tesis de
  "proceso-primero" es interpretación editorial de Umbral, no una afirmación del estándar.

# --- Sources ---
fuente_primaria: "https://www.iso.org/standard/84123.html"   # ISO 16739-1:2024 (catálogo ISO)
fuente_referente: ""   # sin referente de descubrimiento; buildingSMART (oficial, corroborante) va en source_classification, no como discovery signal

# --- Source classification (per editorial-source-attribution-policy.md) ---
source_classification:
  - source_name: "ISO 16739-1:2024 (Industry Foundation Classes — Part 1: Data schema)"
    source_url: "https://www.iso.org/standard/84123.html"
    type: "primary_source"         # estándar ISO = rango 1 de la Source Hierarchy
    public_citable: true
    internal_trace_only: false
    pending_direct_read: true      # verificado vía catálogo ISO indexado; lectura directa 403 (ver §7 y §10)
    reason: >-
      Estándar oficial que sustancia el claim verificable "IFC 4.3 = ISO 16739-1:2024"
      y la incorporación de infraestructura lineal al esquema. Es la fuente de verdad.
    original_source_url: ""
    original_source_name: "ISO / buildingSMART"
  - source_name: "buildingSMART International — 'IFC 4.3 approved as a Final Standard'"
    source_url: "https://www.buildingsmart.org/ifc-4-3-approved-as-a-final-standard/"
    type: "official_doc"           # documentación oficial de la institución del estándar (rango 2)
    public_citable: true
    internal_trace_only: false
    pending_direct_read: true      # confirmar lectura directa antes de citar en copy pública (403 en verificación)
    reason: >-
      Anuncio oficial de la institución que gobierna IFC. Corrobora el mismo hecho que ISO.
      Nota de honestidad: lectura directa de la página bloqueada por HTTP 403 (anti-bot)
      en la verificación; la equivalencia y el año se confirmaron vía catálogo ISO indexado.
    original_source_url: ""
    original_source_name: "buildingSMART International"

# --- Per-channel copies ---
copy_linkedin: "Ver §5 (teaser LinkedIn) — borrador teaser, sin published_url."
copy_x: "Ver §5 (teaser X) — borrador teaser, sin published_url."
copy_blog: "Ver §4 (outline) y §4-bis (primer borrador ~1.000 palabras). No incrustado en YAML por longitud."
copy_newsletter: ""

# --- Visual ---
visual_brief: "Ver §6. Brief conceptual, sin generar imagen y sin logos/marcas."
visual_hitl_required: false          # brief abstracto, sin personas ni marcas; ver §Pendiente humano

# --- Review ---
comentarios_revision: >-
  Candidato ampliado desde PITCH-OLA3-02 por GO humano de David (solo pitch 02).
  Tesis única: con IFC 4.3 el hueco ya no es el formato, es el proceso. Sin hype,
  sin celebrar el estándar, sin cifras inventadas. "Aceptación" tratada como
  decisión de proceso, no como asesoría legal/contractual. Material de "definir
  antes de automatizar" subordinado a la tesis 02 (no se amplía PITCH-05).
communication_review:
  required: true                     # copy pública de blog: la voz importa
  status: "pending"
  reviewer: "rick-communication-director"
  voice_source: "marca_personal_docs"   # o limited_evidence; validar en revisión
  selected_variant: ""
  notes: >-
    Verificar: apertura sin etiqueta "AEC/BIM" en seco; entrar por proceso
    (entregable/revisión/decisión) antes de "modelo BIM"; no usar "escalación"
    como sustantivo; evitar muletillas de consultor ("criterio operativo",
    "capacidad tecnológica", "umbrales") como relleno; una sola idea central.

# --- Human gates (never set by rick-editorial) ---
gates:
  aprobado_contenido: false
  autorizar_publicacion: false
  gate_invalidado: false

# --- Post-publication (empty until publish_success) ---
post_publication:
  published_url: ""
  published_at: ""
  platform_post_id: ""
  publish_error: ""
  error_kind: ""

# --- System metadata ---
system:
  creado_por_sistema: false
  rick_active: false
  publish_authorized: false
  content_hash: ""                   # vacío: se calcula solo tras aprobación de contenido
  idempotency_key: ""                # vacío: derivado de canal + content_hash + page_id
  proyecto: "Sistema Editorial Rick"
  trace_id: "CAND-OLA3-02-ifc43-infra-lineal-candidate"
```

---

## 2. Encuadre AEC/BIM (paso 3 de `editorial-agent-flow.md`)

Se decide **antes** de escribir el copy. Formato del `Expected Output` del flujo.

```yaml
aec_angle: >-
  Con IFC 4.3 (ISO 16739-1:2024) la infraestructura lineal entra al esquema IFC
  abierto. El intercambio deja de estar bloqueado por el formato; queda expuesta la
  pregunta de proceso: qué información del modelo intercambiado necesita cada decisión
  de coordinación en el handover, definida antes de automatizar cualquier comprobación.
bim_relevance: >-
  Aplica a coordinación e intercambio openBIM en obra lineal (rail, carretera, puente,
  puerto y vías navegables), handover entre fases (diseño → construcción → operación)
  y a la información que debe sobrevivir a ese handover para sostener una decisión.
operational_examples:
  - "un tramo de alineación (IfcAlignment) que se intercambia entre disciplinas y debe conservar su geometría de referencia y a qué decisión sirve"
  - "un modelo de puente que pasa de diseño a construcción: qué información tiene que sobrevivir para que la siguiente fase decida sin re-preguntar"
  - "un handover de obra lineal que antes se justificaba fragmentado 'porque no había estándar abierto para esto'"
  - "un intercambio cuya información-por-decisión nadie definió, sobre el que se activa una comprobación automática"
allowed_terms:
  - "IFC 4.3"
  - "ISO 16739-1:2024"
  - "infraestructura lineal"
  - "IfcAlignment / alineación"
  - "handover / intercambio openBIM"
  - "coordinación"
  - "entregable / revisión / aceptación (como decisión de proceso)"
terms_to_avoid:
  - "\"AEC/BIM\" como etiqueta de apertura en seco"
  - "\"escalación\" como sustantivo en copy pública"
  - "cifras de adopción, ROI o % de productividad (no hay fuente primaria)"
  - "\"mandato de licitación\" presentado como hecho"
  - "celebrar el estándar / tono de anuncio de producto"
  - "incluir \"túnel\" en el alcance verificable de IFC 4.3 (se difirió a IFC 4.4)"
  - "muletillas de consultor: \"criterio operativo\", \"capacidad tecnológica\", \"umbrales\" como relleno"
claim_boundaries:
  - "IFC 4.3 = ISO 16739-1:2024 y la entrada de infraestructura lineal por primera vez son verificables (fuente primaria)."
  - "Alcance verificable de IFC 4.3: rail, carretera, puente, puerto y vías navegables (más alineación/terreno/movimiento de tierras)."
  - "Los túneles (IfcTunnel) NO entran en IFC 4.3: se difirieron a la extensión IFC 4.4. No incluirlos en el claim verificable."
  - "\"Antes no había estándar abierto para esto\" se usa como CONTEXTO, no como dato duro."
  - "No afirmar mandatos de licitación, % de adopción ni ROI: van como opinión / pendiente de fuente primaria."
  - "\"Aceptar el entregable\" es decisión de PROCESO, no asesoría legal/contractual (quién firma, responsabilidad civil)."
  - "Lenguaje condicional: muchos equipos, cuando el proceso sigue informal, en obra lineal donde el handover era fragmentado."
  - "El estándar es PRECONDICIÓN del intercambio trazable, no sustituto de definir qué debe sobrevivir al handover."
source_trace:
  - claim: "IFC 4.3 corresponde a ISO 16739-1:2024 (edición 2, esquema de datos)"
    source: "ISO 16739-1:2024 (iso.org/standard/84123.html) + buildingSMART"
    confidence: "alta"
  - claim: "La infraestructura lineal (rail/carretera/puente/puerto y vías navegables; IfcAlignment) entra al esquema IFC por primera vez"
    source: "ISO 16739-1:2024 / buildingSMART"
    confidence: "alta"
  - claim: "Los túneles (IfcTunnel) NO entran en IFC 4.3; se difirieron a IFC 4.4"
    source: "buildingSMART (estado de IFC 4.3 y extensiones IFC 4.4)"
    confidence: "alta — no incluir túnel en el claim verificable de IFC 4.3"
  - claim: "Fecha exacta de aprobación final como estándar"
    source: "ISO catálogo indica publicación 2024; el pitch citaba 'enero 2024' (fecha buildingSMART)"
    confidence: "media — pendiente lectura directa de fuente primaria (page 403 en verificación)"
  - claim: "Antes no había estándar abierto para obra lineal"
    source: "contexto sectorial / opinión editorial"
    confidence: "contexto (no dato duro)"
  - claim: "Mandatos de licitación / ROI / % de adopción"
    source: "—"
    confidence: "opinión / pendiente de fuente primaria (no afirmar en el post)"
handoff_to_linkedin_writer:
  objective: "Pieza de autoridad evergreen (blog) con tesis única proceso-primero para obra lineal; teasers cortos de LinkedIn/X que enlacen al blog."
  audience: "Infraestructura / coordinación / handover openBIM; dirección técnica que evalúa automatizar la revisión."
  tone: "Sobrio, sin hype, sin celebrar el estándar; problema-primero antes de tocar el objeto técnico."
  constraints:
    - "No inventar cifras, mandatos ni datos de clientes."
    - "No citar URLs no verificadas; usar las anclas de §7 o marcar pending."
    - "No incluir túnel en el alcance de IFC 4.3."
    - "Aceptación = decisión de proceso, nunca asesoría legal/contractual."
    - "Una sola idea central (formato→proceso); no derivar hacia la tesis de PITCH-05; el teaser no resume todo el blog."
```

---

## 3. Clasificación honesta de la fuente

| Afirmación | Estatus | Base |
|---|---|---|
| IFC 4.3 = **ISO 16739-1:2024** | **Verificable** | Estándar oficial ISO/buildingSMART (fuente primaria). |
| Infraestructura **lineal** (rail/carretera/puente/puerto y vías navegables, `IfcAlignment`) entra al esquema IFC **por primera vez** | **Verificable** | Alcance de la edición 2024 del esquema. |
| **Túnel** (`IfcTunnel`) dentro de IFC 4.3 | **NO verificable — falso** | Los túneles se **difirieron a IFC 4.4**; no forman parte de IFC 4.3. No incluir en el claim. |
| Mes exacto de aprobación como estándar final | **Parcial / pending** | ISO publica 2024; "enero 2024" (buildingSMART) sin confirmar por lectura directa (page 403). Redactar sin mes exacto o marcar pending. |
| "Antes no había estándar abierto para obra lineal" | **Contexto** | Marco narrativo, no dato duro. Usar como contexto. |
| Mandatos de licitación / ROI / % de adopción | **Opinión / pending** | Sin fuente primaria. **No afirmar** en el post. |
| Tesis "proceso-primero: el hueco que queda es de proceso" | **Opinión editorial (Umbral)** | Interpretación, no afirmación del estándar. Presentar como análisis. |

> Regla aplicada: solo las dos primeras filas se usan como "verificable" en copy pública.
> Todo lo demás va marcado como contexto/opinión/pending/falso, sin cifras ni URLs inventadas.

---

## 4. Outline de **Copy Blog** (secciones + bullets)

1. **Apertura — el hueco que se cerró (sin celebrar)**
   - Durante años, la obra lineal tuvo una explicación cómoda para las entregas fragmentadas: "no había un estándar abierto para esto".
   - Ese argumento se agota. No como noticia de producto, sino como cambio de qué queda por resolver.

2. **Qué cambió, en concreto (precondición, no solución)**
   - IFC 4.3 se publicó como ISO 16739-1:2024; la infraestructura lineal entra al esquema IFC abierto por primera vez (rail, carretera, puente, puerto y vías navegables; alineación).
   - Lo que se cerró es el **formato**: ahora existe una forma abierta y trazable de intercambiar estos modelos.

3. **Lo que el estándar no decide por ti**
   - Un esquema no define qué información del modelo necesita cada decisión de coordinación.
   - No decide qué debe sobrevivir a un handover ni para qué decisión sirve. Lo codifica y lo transporta; el requisito lo pones tú.

4. **El bloqueo se ve ahora donde siempre estuvo**
   - Cuando desaparece la falta de formato, queda expuesta la pregunta que estaba detrás: qué información del intercambio necesita cada decisión y qué debe sobrevivir al handover.
   - Esa es una pregunta de **proceso**, no de formato. Y automatizar una comprobación sobre un intercambio cuya información-por-decisión nadie definió acelera el reproceso.

5. **Definir el proceso, no la herramienta** *(subordinado a la tesis 02)*
   - Definir qué información sostiene cada decisión, y qué se da por bueno para que la siguiente fase avance, es trabajo del equipo —previo a automatizar cualquier comprobación—.
   - Es una decisión de proceso, no un método propietario ni asesoría legal/contractual. (No es el tema de la pieza; es la consecuencia de que el formato ya no sea la excusa.)

6. **Cierre — orden, no herramienta**
   - El trabajo difícil se movió: de "no tenemos formato" a "no habíamos definido el proceso".
   - El estándar es el punto de partida del intercambio trazable, no la respuesta a qué información sostiene cada decisión.

---

## 4-bis. Primer borrador corto de **Copy Blog** (~1.000 palabras, estructurado)

> Borrador para revisión de David — **no** artículo final, **no** publicable tal cual.
> Cumple: tesis única (formato→proceso), sin hype, sin cifras/URLs inventadas, sin
> túnel en el alcance, aceptación como proceso.

**En infraestructura lineal, IFC 4.3 cierra el hueco del formato: el que queda es de proceso**

Durante años, en obra lineal hubo una explicación cómoda para las entregas
fragmentadas. Cuando un modelo de una carretera, un ferrocarril o un puente llegaba
troceado, con piezas que no encajaban entre disciplinas, siempre estaba a mano la
misma frase: "es que no hay un estándar abierto para esto". Era, en parte, cierto.
Y por eso funcionaba tan bien como excusa: mientras faltaba el formato, no hacía
falta mirar el proceso.

Ese argumento se está agotando. IFC 4.3 se publicó como ISO 16739-1:2024, y con esa
edición la infraestructura lineal entra por primera vez al esquema IFC abierto: rail,
carretera, puente, puerto y vías navegables, y elementos comunes como la alineación.
En términos prácticos, lo que se cerró es el **hueco del formato**. Ahora existe una
manera abierta y trazable de intercambiar estos modelos, sin depender de un contenedor
propietario ni de conversiones que pierden información por el camino.

Conviene decir esto sin tono de celebración. Un estándar nuevo no es, por sí mismo,
un resultado. Es una **precondición**. Y aquí empieza la parte incómoda: cuando dejas
de poder culpar al formato, aparece a la vista lo que estaba detrás.

**Lo que un esquema no decide por ti**

Un esquema de datos define cómo se representa la información y cómo se intercambia.
No define qué información necesita cada decisión de coordinación. No decide qué debe
sobrevivir a un handover entre fases —de diseño a construcción, de construcción a
operación— ni para qué decisión concreta sirve cada dato que viaja en el modelo.

Tomemos un caso sencillo. Un tramo de alineación se intercambia entre disciplinas.
El estándar te permite transportarlo de forma trazable: eso es real y es nuevo en
obra lineal. Pero que el dato llegue no significa que llegue **lo que hacía falta**.
¿Se conserva la geometría de referencia que la siguiente disciplina necesita para
decidir? ¿Viaja la información que permite aceptar ese tramo, o solo la que llena el
contenedor? El estándar no responde eso. Lo codifica y lo mueve; el requisito lo
pones tú.

**El bloqueo se ve ahora donde siempre estuvo**

Aquí está el giro de la pieza. Mientras faltaba el estándar, la conversación se
quedaba en la herramienta: "necesitamos un formato". Con el formato disponible, la
pregunta que queda no es de herramienta, es de proceso: qué información del modelo
intercambiado necesita cada decisión de coordinación, y qué debe sobrevivir al
handover, definido **antes** de automatizar cualquier comprobación.

Es tentador saltarse ese paso. La comprobación automática ya está al alcance, y la
promesa de "que la revisión la cierre la máquina" es atractiva. Pero automatizar una
comprobación sobre un intercambio cuya información-por-decisión nadie definió no
ahorra trabajo: sobre un proceso sin escribir, la automatización acelera el reproceso
en lugar de producir retorno. El estándar no cambió eso; solo quitó la última excusa
que lo tapaba.

**Definir el proceso, no la herramienta**

Lo que hace útil un intercambio no es solo que el dato llegue, sino que llegue la
información que cada decisión necesita y que esa información sobreviva al handover. Eso
—qué sostiene cada decisión de coordinación— es precisamente lo que el estándar no
define por ti. En obra lineal, donde el handover cruza disciplinas, fases y a veces
organizaciones, esa definición suele vivir implícita: en la cabeza de una persona, en
una costumbre no escrita. Mientras faltó el formato, su ausencia disimulaba que el
proceso tampoco estaba definido.

Definir ese proceso es trabajo del equipo, no del software. Incluye decidir qué se da
por bueno para que la siguiente fase avance. Y conviene ser explícito en un punto:
cuando aquí se habla de "aceptar" un entregable, se habla de una **decisión de
proceso** —qué se da por bueno para avanzar—, no de responsabilidad jurídica ni de
quién firma. Eso es otra conversación, y no es esta. El punto de la pieza no es la
regla de aceptación en sí, sino que, sin el formato como excusa, esa definición de
proceso ya no se puede posponer.

**Orden, no herramienta**

IFC 4.3 resuelve un problema real de la obra lineal, y no hace falta fingir lo
contrario. Pero su efecto más útil quizá no sea el que se anuncia. Al cerrar el hueco
del formato, mueve el trabajo difícil a donde siempre estuvo: de "no tenemos un
estándar" a "no habíamos definido el proceso". El estándar es el punto de partida de un
intercambio trazable. No es la respuesta a qué información sostiene cada decisión de
coordinación.

Esa respuesta sigue siendo tuya. Y ahora, sin el formato como excusa, es más difícil
posponerla.

*(Cierre operativo, sin muletilla: la próxima vez que un handover de obra lineal
vuelva incompleto, la pregunta ya no es "¿teníamos el formato?". Es "¿habíamos escrito
qué tenía que sobrevivir, y para qué decisión?".)*

---

## 5. Teasers por canal (borradores — **teaser**, sin `published_url`)

> Marcados **teaser**: enlazan al blog (versión canónica, `ADR-010`). **No** hay
> `published_url` (el blog no está publicado). **No** se publican aquí. Sujetos a
> `communication_review` y `rick-qa` antes de cualquier uso.

**Teaser LinkedIn (David)** — *teaser, ~140 palabras*

> En obra lineal, durante años hubo una excusa cómoda para las entregas troceadas:
> "no hay un estándar abierto para esto".
>
> Con IFC 4.3 publicado como ISO 16739-1:2024, esa excusa se acaba: la infraestructura
> lineal entra por primera vez al esquema IFC abierto.
>
> Pero cerrar el hueco del formato no cierra el otro hueco.
>
> Un estándar mueve la información de forma trazable. No decide qué información necesita
> cada decisión de coordinación, ni qué debe sobrevivir a un handover.
>
> Cuando ya no puedes culpar al formato, queda a la vista lo que estaba detrás: el
> proceso que nadie escribió.
>
> Y automatizar una comprobación sobre lo que nadie definió no ahorra trabajo: acelera
> el reproceso.
>
> El estándar es el punto de partida. No la respuesta.
>
> *(Lo desarrollo en el blog — link pendiente de publicación.)*

**Teaser X** — *teaser, corto*

> En obra lineal, la excusa para las entregas troceadas era cómoda: "no hay estándar
> abierto para esto".
>
> Con IFC 4.3 (ISO 16739-1:2024) esa excusa se acaba: la infraestructura lineal entra
> al esquema IFC abierto.
>
> Pero el formato no decide qué información necesita cada decisión, ni qué debe
> sobrevivir a un handover. Eso es proceso, y hay que definirlo antes de automatizar la
> revisión. El estándar no lo hace por ti.

---

## 6. `visual_brief` (breve — **sin generar imagen, sin stage8**)

- **Concepto:** una línea de alineación (obra lineal) que cruza de izquierda a derecha
  tres marcas de handover (diseño → construcción → operación). Bajo la línea, el
  "formato" aparece como un tramo que ahora se dibuja continuo (hueco cerrado). Sobre
  la línea, en los puntos de handover, una pregunta discreta sin responder: *¿qué
  información necesita esta decisión, y qué debe sobrevivir?* — el "hueco de proceso"
  que queda abierto.
- **Mensaje visual:** el formato se cerró (línea continua); el proceso sigue abierto
  (pregunta en los nudos del handover).
- **Estética:** sobria, técnica, apta para blog/LinkedIn. Sin interfaces internas ni
  referencias a sistemas propios.
- **Restricciones:** **sin logos ni marcas** (buildingSMART, ISO, ni de terceros); sin
  personas; sin capturas de software real. Por eso `visual_hitl_required: false`
  (ver §Pendiente humano para confirmación de David; si el diseño final incorporara
  logos del estándar, pasa a `true`).

---

## 7. Anclas verificables (fuentes)

| # | Ancla | Qué sostiene | URL | Clasificación |
|---|---|---|---|---|
| 1 | **ISO 16739-1:2024** (IFC 4.3) | Esquema de datos IFC, edición 2024; infraestructura lineal entra por primera vez | <https://www.iso.org/standard/84123.html> | `primary_source`, público-citable |
| 2 | **buildingSMART** — "IFC 4.3 approved as a Final Standard" | Mismo hecho, institución del estándar | <https://www.buildingsmart.org/ifc-4-3-approved-as-a-final-standard/> | `official_doc`, público-citable |

> Nota de verificación: ambas páginas devolvieron **HTTP 403** a la lectura directa
> (bloqueo anti-bot, no inexistencia). La equivalencia IFC 4.3 = ISO 16739-1:2024, el
> alcance de infraestructura lineal (sin túnel) y el año 2024 se confirmaron vía el
> catálogo ISO indexado. Compromiso: **confirmar lectura directa de ambas URLs** (y el
> **mes exacto** de aprobación final) antes de citarlas en copy pública — ver §10.

---

## 8. `communication_review` + riesgos + `claim_boundaries`

### 8.1 communication_review (resumen)

- **required:** `true` (copy pública de blog: la voz de David es material).
- **status:** `pending` — `rick-communication-director` (read-only/dry-run) aún no pasó.
- **A vigilar (de `editorial-agent-flow.md`):** apertura sin "AEC/BIM" en seco; entrar
  por proceso (entregable/revisión/decisión) antes de "modelo BIM"; **no** usar
  "escalación" como sustantivo; podar muletillas de consultor; una sola idea central
  (formato→proceso, sin derivar a la tesis de PITCH-05); el teaser no resume todo el blog.

### 8.2 Riesgos editoriales (pitch 02: **medio**)

| Riesgo | Mitigación en este candidato |
|---|---|
| Leerse como celebración del estándar / anuncio de producto | Ángulo proceso-primero explícito; el estándar es precondición, no resultado; cierre "resuelve un problema real" sin hype. |
| Afirmar cifras (ROI, % adopción) o mandatos de licitación sin fuente | Excluidos del borrador; marcados opinión/pending en §2–§3. |
| Incluir "túnel" como parte de IFC 4.3 (error de alcance) | Corregido: túnel diferido a IFC 4.4; excluido del claim verificable (§1, §2, §3, §4-bis). |
| "Aceptar el entregable" leído como asesoría legal/contractual | Frase explícita en el borrador: es decisión de proceso, no de quién firma. |
| Diluir la tesis 02 hacia la de PITCH-05 ("define la puerta") | Material de "definir antes de automatizar" subordinado a la tesis formato→proceso; sin arco completo de 05. |
| Presentar "no había estándar abierto" como dato duro | Redactado como contexto/excusa histórica, no como hecho verificable. |
| Fecha exacta incorrecta | El borrador evita el mes exacto; §7 marca el mes como pending. |
| Sobregeneralizar a "toda la obra lineal" | Lenguaje condicional (muchos equipos, cuando el proceso sigue informal). |

### 8.3 claim_boundaries (frontera de afirmaciones)

- Verificable y afirmable: **IFC 4.3 = ISO 16739-1:2024** y la entrada de infraestructura
  lineal (rail/carretera/puente/puerto y vías navegables) por primera vez.
- **Falso — no afirmar:** túnel dentro de IFC 4.3 (se difirió a IFC 4.4).
- Contexto (no dato duro): "antes no había estándar abierto para esto".
- Opinión / pending (no afirmar): mandatos de licitación, ROI, % de adopción, mes exacto.
- Opinión editorial de Umbral (presentar como análisis): la tesis proceso-primero.
- Fuera de alcance: responsabilidad jurídica/contractual de la "aceptación"; y la tesis
  de PITCH-05 ("define la puerta antes de automatizar") como argumento propio.

---

## 9. Checklist de QA (de la plantilla) — estado

- [x] `publication_id` único y con formato (`CAND-OLA3-02`).
- [x] `estado` = `Borrador` (nunca superior).
- [x] `canal` válido (`blog`).
- [x] `tipo_de_contenido` válido (`blog_post`).
- [x] **Gates humanos todos `false`** (`aprobado_contenido`, `autorizar_publicacion`, `gate_invalidado`).
- [x] Sin campos de publicación (`published_url`, `platform_post_id` vacíos).
- [x] Separación de fuente clara (`fuente_primaria` = ISO; buildingSMART = oficial corroborante en `source_classification`; sin referente de descubrimiento).
- [x] `source_classification` presente (§1) por la policy de atribución (ISO = `primary_source`; buildingSMART = `official_doc`).
- [x] Ningún referente citado como autoridad pública que no sea fuente original.
- [x] Sin afirmaciones factuales sin fuente primaria (cifras excluidas o marcadas pending; túnel corregido).
- [x] `visual_hitl_required` explícito (`false`, con justificación y confirmación pendiente).
- [x] `trace_id` seteado.
- [x] `communication_review` presente (required `true`, status `pending`).
- [x] Copy pública **no** usa "escalación" como sustantivo.
- [x] `content_hash` / `idempotency_key` **vacíos** (se calculan solo tras aprobación).
- [x] Listo para **revisión de David**, **no** listo para publicación.

---

## 10. Pendiente humano (qué falta verificar en fuente primaria antes de aprobar)

1. **Lectura directa de las fuentes + mes exacto.** Confirmar leyendo directamente la
   página de buildingSMART y el registro ISO (ambas bloqueadas por 403 en esta
   verificación) antes de citarlas en copy pública. Reconciliar "enero 2024" (pitch)
   con la publicación ISO 2024. Hasta entonces, el borrador **no** fija mes.
2. **Alcance de dominios (doble-check).** Confirmar la enumeración verificable
   (rail/carretera/puente/puerto y vías navegables) y que **túnel** queda fuera de
   IFC 4.3 (diferido a IFC 4.4) al leer la fuente primaria.
3. **"Por qué ahora" fuerte.** El pitch marcó decisión "usar ahora / esperar": si David
   quiere un gancho de actualidad más fuerte, atar a una señal de adopción concreta y
   **fechada** (con fuente), sin fingir urgencia por la fecha del estándar.
4. **`etapa_audiencia`.** Propuesta `consideration`; David puede preferir `awareness`
   o `trust` según intención de la pieza.
5. **`visual_hitl_required`.** Propuesto `false` (brief abstracto, sin personas/marcas).
   Confirmar; si el diseño final incorporara logos del estándar, pasa a `true`.
6. **Longitud/forma final del blog.** Este es un borrador corto (~1.000 palabras). Si
   David quiere la pieza de autoridad completa (2.000+), es una ampliación posterior.
7. **Voz (`communication_review`).** Falta la pasada de `rick-communication-director`
   y `rick-qa` antes de considerar el copy "listo para revisión final".
8. **Registro en Notion `Borrador`.** Fuera de alcance de este GO (docs-only). Es un GO
   aparte si David lo pide (paso 7 de `editorial-agent-flow.md`, operador/humano).

---

## 11. Confirmación de alcance (lo que este entregable **no** hizo)

- [x] Solo se amplió **PITCH-OLA3-02**. Pitches 01/03/04/05 **no** tocados (material de 05 solo subordinado, no ampliado).
- [x] **Sin publish** (blog/Azure/LinkedIn/X), ni real ni simulado con red.
- [x] **Gates humanos no abiertos** (`aprobado_contenido=false`, `autorizar_publicacion=false`).
- [x] **Sin escritura a Notion** (Publicaciones ni Borrador). Docs-only.
- [x] **Sin runtime de Rick / SSH / VPS / rotación de secretos.**
- [x] **Sin generar imágenes (stage8)** ni **POST LinkedIn (stage9c)**; guards Ola 2 intactos.
- [x] Sin inventar cifras (%/USD), McKinsey, mandatos ni datos de clientes; sin URLs no verificadas.
- [x] Entrega **docs-only** en worktree `claude/docs-ola3-expand-pitch02-candidate`; **sin merge**.

---

## Referencias

- Pitch fuente: `docs/ops/ola3-editorial-5-pitches-2026-07-20.md` §PITCH-OLA3-02
- Smoke: `docs/ops/ola3-editorial-smoke-note-2026-07-20.md`
- Plantilla: `docs/ops/rick-editorial-candidate-payload-template.md`
- Flujo: `docs/ops/editorial-agent-flow.md` (pasos 1–6)
- Policy de atribución: `docs/ops/editorial-source-attribution-policy.md`
- ADRs: `docs/adr/ADR-007-notion-como-hub-editorial.md` · `docs/adr/ADR-010-azure-editorial-blog-cms.md` · `docs/adr/ADR-011-orquestacion-editorial-criterios-duros.md`
- Ejemplo de payload previo: `docs/ops/cand-002-payload.md`
