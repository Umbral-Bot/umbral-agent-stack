# Contrato del Norte Editorial + HITL (v-norte 2026-07-22)

> **Estado:** Proposed — contrato de proceso, **docs-only**. Este documento NO
> crea ni modifica ninguna DB de Notion, NO abre gates, NO publica y NO produce
> copy. Define el **contrato** que Rick/Worker deberán cumplir en fases
> posteriores (P1 schema por David, P2 cableado por Codex/Worker).
> **Norte validado por David:** 2026-07-22.
> **Precede:** gate `EDITORIAL_GAP_MATRIX_READY` (ver
> [editorial-gap-matrix-norte-2026-07-22.md](editorial-gap-matrix-norte-2026-07-22.md)).
> **Owner experiencia:** David · **Schema:** solo David ([ADR-007](../adr/ADR-007-notion-como-hub-editorial.md) §44) ·
> **Writes Notion:** monopolio del Worker/core vía Rick ([ADR-011](../adr/ADR-011-orquestacion-editorial-criterios-duros.md) #1) ·
> **Producción de contenido:** Rick (OpenClaw) en runtime — este paquete no simula a Rick.

Reemplaza como **fuente de verdad del norte** a la secuencia aspiracional de
[production-flow-v2-2026-06-06.md](../editorial-pipeline/production-flow-v2-2026-06-06.md)
**solo** en los puntos que este documento marca explícitamente (ver §7
Conflictos resueltos). En todo lo no marcado, production-flow-v2 sigue vigente.

---

## 1. Modelo de trabajo (roles)

- **Cursor** orquesta (plan, GO, prompts, tablero de gates, supervisión).
- **Claude** diagnostica y documenta (este paquete).
- **Rick (OpenClaw)** produce en runtime: cura, redacta alternativas, genera
  imágenes, registra en el hub editorial. Cursor/Claude **no** sustituyen a Rick
  creando filas en Publicaciones ni redactando copy final.
- **Worker/core** es el único que escribe en Notion y publica (idempotencia,
  gates, OpsLogger). n8n = bordes; nunca escribe Notion directo ([ADR-011](../adr/ADR-011-orquestacion-editorial-criterios-duros.md) #1).
- **David** es el único humano operador y el único que abre gates y aprueba
  schema.

---

## 2. Flujo end-to-end deseado (norte)

```
[CURADO / V1 — automático, produce Rick]
  1. Descubrir señales (referentes + fuentes) → dedup vs backlog (§5.J)
  2. Curar y presentar ALTERNATIVAS (no artículo final), cada una con:
       - arco narrativo claro
       - pie de estructura de discurso explícito (§3)
       - fuente = URL de la PIEZA concreta (no home de la organización) (§3)
     en la superficie Notion de ALTERNATIVAS (BD Shortlist propuesta, §6)

[HITL-1 — humano, sobre las alternativas]  (§4)
  3. David elige por alternativa una de cuatro salidas:
       Archivar · Observar · Descartar · Aprobar

[V2 COPY + BRIEF — automático tras Aprobar, produce Rick]  (§5.F)
  4. Promover el Borrador y producir Copy Blog largo (ancla CAND-001,
     ~350-500+ palabras), Copy LinkedIn, Copy X, Copy Newsletter y
     Visual brief v2 en la misma fila de Publicaciones

[HITL DEL BRIEF — humano, sobre la fila promovida]  (§5.F)
  5. David lee Copy* + Visual brief y aprueba u observa ese input; las
     observaciones se dejan como comentarios de la página

[V2 IMÁGENES — sólo después del HITL del brief]  (§5.G)
  6. Generar 5 alternativas de imagen → subir a Notion

[HITL-2 — humano]  (§5.H)
  7. David elige imagen(es) + marca autorización + confirmación final Telegram

[PUBLICACIÓN]  (§5.H, §5.I, Fila I = B)
  8. Blog: publica automáticamente a Azure (ADR-010) tras gates + confirmación
  9. RRSS: se inyecta el link del blog + copy de Notion; queda en estado
     `listo_rrss`; el post a LinkedIn/X es MANUAL/semi-automático (no autopublish)
```

---

## 3. Contrato de la Alternativa V1 (P0.2)

Cada alternativa presentada en la etapa V1 **debe** declarar, además de los
campos de curado existentes ([docs/67 §5](../67-editorial-source-curation.md),
[scoring-schema.md](../../openclaw/workspace-templates/skills/editorial-source-curation/references/scoring-schema.md)):

1. **Arco narrativo** — no un ángulo suelto: el CUERPO es la historia de la
   pieza (de qué parte, qué tensiona, a dónde llega, pero como historia, no
   como rótulo). Reemplaza al `recommended_angle` único como requisito mínimo
   por alternativa. Se lee como historia: un lector que no conoce el pipeline
   debe poder seguirlo. **No** incrusta etiquetas de etapa del sistema
   (`claim`, `tesis editorial`, `HITL`, `V1`, `V2`, `payload`) **ni** usa el
   andamiaje `Parte de…` / `Parte de que…` / `Tensiona…` / `Llega a que…` /
   `La pieza llega a…` como verbo principal de la oración, con o sin
   etiquetas. Las alusiones a estrategia interna van entre paréntesis
   **después** de la frase que etiquetan: `(punto de partida: …)`,
   `(tensión: …)`, `(cierre: …)`. Ejemplo negativo: `CAND-WLCA-01-SHORTLIST-V1`
   (2026-08-31) metió "claim respaldado por RICS" y "tesis editorial propia"
   en el arco — la trayectoria era correcta; las etiquetas eran metadata de
   proceso. Ejemplo negativo adicional: `CAND-IA-FLUJOS-AEC-SHORTLIST-V1`
   (2026-09-03) usó el andamiaje `Parte de.../Tensiona.../Llega a que...` sin
   ninguna etiqueta y pasó QA igual — el arco seguía ilegible como historia.
   `rick-qa` rechaza ambos casos con `blocked_arco_process_metadata`.

2. **Pie de estructura de discurso** — línea explícita y obligatoria. Formato por
   defecto (cambiable, pero **debe declararse el efectivamente usado**):

   ```
   Estructura de discurso usada: [hipótesis, introducción, argumento 1, argumento 2, contraargumento, contra-contraargumento, conclusión]
   ```

   La lista puede variar (otra secuencia discursiva válida; p. ej. `claim de
   fuente → brecha operativa → tesis editorial → aplicación`), pero **nunca**
   puede omitirse: si falta, `rick-qa` rechaza la alternativa. **Acá sí van las
   etiquetas.** El pie declara el mapa; no recuenta el arco después de los dos
   puntos.

3. **Fuente = URL de la pieza concreta** — la fuente citable de cada alternativa
   es la **URL directa del ítem** (`item_url`), nunca la home/feed de la
   organización. Una home/landing es `contextual_reference`, `public_citable:
   false` (ver [editorial-source-attribution-policy.md](editorial-source-attribution-policy.md)
   reglas #5/#6/#7). Ejemplo negativo real: CAND-OLA3-03 usó
   `buildingsmart.org` (home) como fuente — **no conforme**.

4. **Cadena de la tesis** (`cadena_tesis`, 2026-08-31) — árbol lineal para que
   David u otro agente valide cómo se formuló el salto editorial. No es una
   DB nueva ni una relation de Notion. Cuatro líneas, en este orden:
   `Evidencia (fuente):` / `Inferencia (brecha):` / `Salto editorial:` /
   `No afirmado:`. Evidencia tiene que poder sostenerse con `fuente_pieza_url`.
   El salto no puede colarse en Evidencia. `premisa` es el salto condensado
   sin voz de operador (`la editorial propone`, `proponemos`). Si falta o
   está malformado, `rick-qa` rechaza con `blocked_cadena_tesis`.

Estas exigencias se propagan a: [docs/67](../67-editorial-source-curation.md),
[docs/68](../68-editorial-phase-1-manual.md),
[shortlist-format.md](../../openclaw/workspace-templates/skills/editorial-source-curation/references/shortlist-format.md),
la SKILL `editorial-source-curation`, y el payload/ROLE de `rick-editorial`
(este último se ajusta en P2, no aquí).

---

## 4. HITL-1 — cuatro salidas (P0.3)

Sobre la etapa de ALTERNATIVAS, David dispone de cuatro salidas operativas
(hoy sólo existe el binario `aprobado_contenido` + el estado `Descartado`; ver
brecha filas B–E). Definiciones contractuales:

| Salida | Qué hace | Efecto de sistema |
|--------|----------|-------------------|
| **Archivar** | No procede, pero se conserva como historial neutro. | Estado terminal `Archivar`, distinto de `Descartar`. No es señal negativa. No promueve a Publicaciones. |
| **Observar** | Sigue en revisión; David deja **comentarios de Notion** para sugerir cambios. | Estado `Observar`; Rick puede iterar la alternativa según los comentarios. Bucle pre-aprobación (distinto del gate post-aprobación, §7 conflicto 1). |
| **Descartar** | No procede **y** registra un **ejemplo negativo**. | Estado terminal `Descartar` + `motivo_descarte` + captura de error → realimenta QA/generación para no repetir el fallo (loop de aprendizaje). Contrato aquí; implementación en P2. |
| **Aprobar** | Procede y **dispara la entrada de V2**. | Marca la alternativa como aprobada, **promueve** una fila a Publicaciones (§6) y habilita la producción por Rick de Copy Blog, Copy LinkedIn, Copy X, Copy Newsletter y Visual brief v2. **No genera imágenes**: las cinco variantes quedan después del HITL del brief (§5.F/G). |

Notas:
- **Descartar ≠ Archivar.** Archivar es neutro (parkear); Descartar es señal
  negativa que alimenta el aprendizaje. Hoy ambos colapsan en `Descartado`
  (brecha).
- **Observar** usa comentarios nativos de Notion como canal de cambio; opcional
  poller en P2 para estructurar el feedback.
- El **loop de aprendizaje de Descartar** (ejemplo negativo → no repetir) es la
  pieza **AUSENTE** hoy (fila D, verificada); es contrato aquí, código en P2.

---

## 5. V2, HITL-2 y publicación

### F — Copy largo + copys definitivos por canal
- **Copy Blog largo**: ancla de longitud/estilo = CAND-001 (~350-500+ palabras).
  Resolver el límite `rich_text` de `Copy Blog` (usar body de página o payload
  explícito al Worker; ver [ADR-010](../adr/ADR-010-azure-editorial-blog-cms.md)
  Negativas y [notion-blog-linkedin-v3-content-model.md](notion-blog-linkedin-v3-content-model.md) §Limitation).
- **Copys por canal**: Rick (`ROLE rick-editorial`) produce `Copy Blog`
  (consumido por publish), `Copy LinkedIn`, `Copy X` y `Copy Newsletter`, junto
  con `Visual brief` v2, en la **misma fila promovida** de Publicaciones.
- **HITL del brief**: David lee los cuatro `Copy*` + `Visual brief` en esa fila
  y aprueba u observa ese input. `Observar` se expresa mediante **comentarios
  nativos de esa página**; este contrato no agrega una columna para el feedback.
  Un select dedicado al brief queda para un GO futuro de schema por David
  (ADR-007); este paquete no lo crea ni lo presupone.
- La producción de copy/brief no abre `aprobado_contenido` ni
  `autorizar_publicacion`, no publica y no llama a Magnific.

### G — Cinco alternativas de imagen
- **5** variantes generadas por Rick (Magnific) **sólo después del HITL del
  brief**, subidas a Notion como `imagen_alt_1_url`…`imagen_alt_5_url`, con `Selección imagen`
  (`Pendiente` → `Alt 1`…`Alt 5` / `Regenerar` / `Sin imagen`) y `Estado imagen`.
- Aprobar en Shortlist no es autorización para generar imágenes. El scan de
  Magnific permanece `DEFAULT OFF` y, como defensa adicional, omite toda fila
  cuyo `Visual brief` esté vacío. La futura señal estructurada de aprobación
  del brief requiere GO de schema de David; este paquete no crea ese select ni
  enciende la automatización de imágenes.
- La **selección** ya está cableada read-only en el Worker; la **generación**
  (`scripts/editorial/magnific_generate_variants.py`) es P2 (hoy TODO/OAuth
  pendiente). Estandarizar el conteo en **5** (no 3).

### H — HITL-2 → publish blog (Azure, ADR-010)
- David elige imagen(es), marca `autorizar_publicacion` y confirma por Telegram
  ("ok publica"). El blog se publica automáticamente a Azure ([ADR-010](../adr/ADR-010-azure-editorial-blog-cms.md)).
- **Disparo (D3 — David 2026-07-22, condición DURA):** el check de imagen **no**
  basta por sí solo. El trigger de publish exige las **tres** condiciones, ninguna
  opcional: `Estado imagen = Seleccionada` **∧** `autorizar_publicacion = true`
  **∧** confirmación Telegram "ok publica" (coherente con
  [production-flow-v2 §3.4](../editorial-pipeline/production-flow-v2-2026-06-06.md)).
  Un puente Notion-evento→Worker (n8n/webhook, write vía core) es P2 (hoy el
  publish es tarea de Worker invocada por el operador).

### I — RRSS = **OPCIÓN B** (no autopublish)
> **Fila I aplicada: B.** El norte deseado (autopublish LinkedIn+X tras HITL-2)
> **choca** con contrato vinculante y ToS y queda **ajustado a B**.

- **Regla canónica:** el código **nunca autopublica RRSS**
  ([ADR-010 §Contexto](../adr/ADR-010-azure-editorial-blog-cms.md)). LinkedIn requiere
  HITL obligatorio (LinkedIn ToS §3.1.26, [ADR-005 §LinkedIn](../adr/ADR-005-publicacion-multicanal.md));
  X es asistido (David publica), API directa diferida a v2 ([ADR-005 §X](../adr/ADR-005-publicacion-multicanal.md)).
- **Qué hace el sistema (B):** publica el blog → inyecta `published_url` +
  copy de Notion en las copies → marca estado `listo_rrss`. El **post** a
  LinkedIn/X lo hace un humano (manual/semi-auto).
- **X hoy no tiene publisher** (stage10 spec; `publish_guard` lo lista como
  `future`) — cualquier "auto X" sería vaporware aun si se quisiera A.
- **ADR-009 (LinkedIn empresa auto) queda diferido bajo B:** [ADR-009-linkedin-company-api.md](../adr/ADR-009-linkedin-company-api.md)
  propone publicar en la Company Page **automáticamente vía API** tras gates +
  Telegram. Bajo **Fila I = B** ese POST automático se **difiere**: el sistema deja
  `listo_rrss` y el post es humano.
- **Si en el futuro David decide Fila I = A:** requiere PR aparte que modifique
  ADR-005/010/**009** + invariante `linkedin_x_require_hitl`, con **sección de
  riesgo ToS explícita**, construir el adapter X, y que LinkedIn apruebe el access
  review de Community Management API. No se hace en este paquete.

### J — Dedupe de candidato (P0.3)
- Antes de registrar una nueva alternativa/candidata, el sistema **consulta el
  backlog de Publicaciones** (filas `Borrador` **y** `Publicado`) por un
  identificador de tema/fuente (`idempotency_key` / hash de tema normalizado) y
  marca `dedupe_status` (nuevo / duplicado_borrador / duplicado_publicado).
- Distinto de la idempotencia de **publish** (que ya existe: `content_hash` vs
  `published_history` SQLite). El dedupe de **candidato vs backlog** es AUSENTE
  hoy y es contrato aquí; código en P2.

---

## 6. Recomendación de schema: **HÍBRIDO** (Proposed — decide David)

**Nueva superficie "Alternativas / Shortlist" (DB propia, ligera) que, al
`Aprobar`, promueve una fila a la DB `Publicaciones` existente.** Promoción
**unidireccional** y puntual (un único evento: Aprobar) — **no** sincronización
bidireccional continua.

**Por qué híbrido (y no las otras dos):**
- **vs Extender Publicaciones:** la máquina de estados de Publicaciones es lineal
  (una pieza); las alternativas son un *fan-in* de competidoras donde la mayoría
  muere. Meter 4-estados + churn + negativos ahí ensucia el registro limpio y
  choca con el gate booleano.
- **vs Nueva DB total:** no reconstruimos la mitad V2/publish — reusamos las
  columnas de Publicaciones ya ejecutadas (5 imágenes + `Selección imagen`, copy
  por canal, gates, multicanal).
- **Objeción "overhead de sync" de [ADR-007:90-92](../adr/ADR-007-notion-como-hub-editorial.md) alt#6:**
  aquí el sync es unidireccional/puntual, y es exactamente el **borde natural de
  dedupe** (fila J).
- **Restricción dura:** cualquier creación/cambio de schema es **solo David**
  ([ADR-007:44,47](../adr/ADR-007-notion-como-hub-editorial.md)); Notion writes =
  monopolio Worker/core ([ADR-011](../adr/ADR-011-orquestacion-editorial-criterios-duros.md) #1).

### Campos propuestos para la BD Shortlist (checklist P1, no crear aún)

| Campo | Tipo | Uso |
|-------|------|-----|
| `Título` | title | Título/ángulo de la alternativa |
| `alternativa_id` | rich_text | ID estable (correlación / promoción) |
| `topic_key` | rich_text | Tema normalizado para dedupe (fila J) |
| `arco_narrativo` | rich_text | Arco narrativo (obligatorio, §3) |
| `estructura_discurso` | rich_text | Pie de estructura de discurso usado (obligatorio, §3) |
| `premisa` | rich_text | Tesis condensada 1-2 frases (salto, sin voz de operador) |
| `cadena_tesis` | rich_text | Árbol evidencia / inferencia / salto / no afirmado (obligatorio en V1 nuevas, §3.4) |
| `fuente_pieza_url` | url | URL de la PIEZA concreta (obligatorio, no home) |
| `fuente_tipo` | select | primary_source / original_article / official_doc / analysis_source / discovery_source / contextual_reference |
| `fuente_discovery_url` | url | Home/feed de descubrimiento — trace interno, no citable |
| `canal_sugerido` | select | blog / linkedin / x / newsletter |
| `score_alineacion` | number | Score compuesto 0-100 |
| `Resultado revisión` | select | Pendiente / Archivar / Observar / Descartar / Aprobar (HITL-1, §4) |
| `motivo_descarte` | rich_text | Requerido si `Descartar` |
| `ejemplo_negativo` | checkbox | Marca captura de negativo para el loop de aprendizaje |
| `error_kind` | multi_select | Tipo de fallo (alimenta QA/generación) |
| `dedupe_status` | select | nuevo / duplicado_borrador / duplicado_publicado |
| `publicacion_relacionada` | relation → Publicaciones | Fila existente detectada por dedupe (si aplica) |
| `promovido_a` | relation → Publicaciones | Fila creada al `Aprobar` (promoción) |
| Comentarios `Observar` | (comentarios nativos) | Canal de sugerencias en `Observar` (sin campo dedicado) |

**Adición mínima a Publicaciones** (solo David): `origen_alternativa` (relation →
Shortlist) como back-link **y** `listo_rrss` (checkbox, decisión D2) — estado
terminal RRSS bajo Fila I = B (blog publicado, `published_url` + copy inyectados,
post LinkedIn/X **humano** pendiente; ver §5.I y
[human-review-contract §Postcondiciones](editorial-publicaciones-human-review-contract.md)).
El resto de Publicaciones no cambia.

---

## 7. Conflictos internos resueltos (P0.1)

| # | Conflicto | Regla CANÓNICA (gana) | SUPERSEDED (anotado) |
|---|-----------|-----------------------|----------------------|
| 1 | Editar invalida el gate **vs** edición = verdad final | **La edición de David en Notion es la verdad final; editar NO revierte la aprobación** ([production-flow-v2 §3.2 regla 2 + §7](../editorial-pipeline/production-flow-v2-2026-06-06.md)). | Invariante `gate_invalidation_on_comment` / `aprobado_contenido` "si David comenta tras aprobar se invalida" ([notion/schemas/publicaciones.schema.yaml:400-404](../../notion/schemas/publicaciones.schema.yaml)) — **superseded** para el flujo V2. **Residual de seguridad:** si un *agente* (Rick) regenera contenido tras la aprobación, eso **sí** resetea el gate (no las ediciones de David). El bucle "Observar + comentarios" del HITL-1 (§4) es **pre-aprobación**, distinto de este. |
| 2 | ADR-005 blog "automatización completa" (Ghost) **vs** ADR-010 operador/Worker-trigger (Azure) | **[ADR-010](../adr/ADR-010-azure-editorial-blog-cms.md): Azure Blob + Function; publish por tarea Worker gate-checked tras gates + Telegram.** | [ADR-005 §Blog](../adr/ADR-005-publicacion-multicanal.md) "Ghost — automatización completa (v1)" — plataforma y matiz de auto-scheduling **superseded** por ADR-010 (más nuevo: 2026-06-08). |
| 3 | Rename de gates spec-only + drift S4→Publicaciones | **Claves de campo canónicas = `aprobado_contenido` / `autorizar_publicacion`** (schema + código). "Texto aprobado" / "Autorizar publicación" ([production-flow-v2 §4](../editorial-pipeline/production-flow-v2-2026-06-06.md)) son **etiquetas de UI** que mapean a esas claves. **S4 escribe en la DB de discovery `📰 Publicaciones de Referentes`** (no la editorial `📰 Publicaciones`; esa la escribe S7). Fuente de verdad: `scripts/discovery/stage4_push_notion.py:2,8` + `discovery-publish-cron.sh:68`. | [master-plan.md:33](../editorial-pipeline/master-plan.md) "S4 → páginas en `📰 Publicaciones`" = **drift/ambiguo** (lee como la editorial; el código apunta a "Publicaciones de Referentes"). |
| 4 | production-flow-v2 §5 "Automático vía API (LinkedIn/X)" **vs** ADR-005/010 "nunca autopublica RRSS" | **Fila I = B** (David 2026-07-22 + ToS §3.1.26 + [ADR-010 §Contexto](../adr/ADR-010-azure-editorial-blog-cms.md)): blog auto tras gate; RRSS = inyección de link + `listo_rrss` + post humano. | [production-flow-v2 §5](../editorial-pipeline/production-flow-v2-2026-06-06.md) "LinkedIn empresa / X = Automático vía API" — **superseded a B**. También [ADR-009](../adr/ADR-009-linkedin-company-api.md) (Company Page auto vía API) queda **diferido** bajo B (revive con Fila I = A + access review LinkedIn). |

---

## 8. Qué NO hace este contrato

- No crea ni modifica la DB de Notion (Shortlist ni Publicaciones) — eso es P1,
  solo David ([ADR-007](../adr/ADR-007-notion-como-hub-editorial.md)).
- No abre gates ni publica. El copy/brief lo produce Rick tras Aprobar; las
  imágenes permanecen separadas hasta el HITL del brief.
- No reactiva stage8/stage9c (fail-closed por Ola-guards).
- No autoriza autopublish LinkedIn/X (Fila I = B).

## 9. Qué sigue (P1 → P2 → P3)

- **P1 (David):** aprobar/crear la BD Shortlist (§6) + `origen_alternativa` en
  Publicaciones; actualizar `notion/schemas/*` + ADR-007.
- **P2 (Codex/Worker):** poller Aprobar→promueve; Rick produce Copy Blog,
  Copy LinkedIn, Copy X, Copy Newsletter + Visual brief; tras el HITL del brief,
  generador Magnific de 5 imágenes + OAuth; dedupe de candidato; puente HITL-2;
  captura de negativos (loop D); inyección de link + `listo_rrss`
  (NO autopublish).
- **P3:** smoke end-to-end por fase en dry-run / gates=false.

## Referencias

- Matriz de brecha: [editorial-gap-matrix-norte-2026-07-22.md](editorial-gap-matrix-norte-2026-07-22.md)
- [production-flow-v2-2026-06-06.md](../editorial-pipeline/production-flow-v2-2026-06-06.md) · [master-plan.md](../editorial-pipeline/master-plan.md)
- [ADR-005](../adr/ADR-005-publicacion-multicanal.md) · [ADR-007](../adr/ADR-007-notion-como-hub-editorial.md) · [ADR-010](../adr/ADR-010-azure-editorial-blog-cms.md) · [ADR-011](../adr/ADR-011-orquestacion-editorial-criterios-duros.md)
- [notion-blog-linkedin-v3-content-model.md](notion-blog-linkedin-v3-content-model.md) · [editorial-source-attribution-policy.md](editorial-source-attribution-policy.md)
- [docs/67](../67-editorial-source-curation.md) · [docs/68](../68-editorial-phase-1-manual.md) · [shortlist-format.md](../../openclaw/workspace-templates/skills/editorial-source-curation/references/shortlist-format.md)
