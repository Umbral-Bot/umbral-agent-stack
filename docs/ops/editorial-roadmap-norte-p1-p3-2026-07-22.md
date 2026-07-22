# Hoja de ruta — Norte editorial P0.5 → P3 (2026-07-22)

> **Estado:** Proposed — **docs-only / plan**. Este documento NO crea ni modifica
> ninguna DB o fila de Notion, NO abre gates, NO publica, NO produce copy, NO
> reactiva stage8/9c y NO simula a Rick. Sólo **planifica** el saneamiento y el
> cableado hacia el norte editorial validado por David (2026-07-22).
> **Owner experiencia:** David · **Schema Notion:** solo David
> ([ADR-007](../adr/ADR-007-notion-como-hub-editorial.md) §44) ·
> **Writes Notion:** monopolio Worker/core vía Rick
> ([ADR-011](../adr/ADR-011-orquestacion-editorial-criterios-duros.md) #1) ·
> **Producción de contenido:** Rick (OpenClaw) en runtime.
> **Base de verdad:** [editorial-norte-hitl-contract-2026-07-22.md](editorial-norte-hitl-contract-2026-07-22.md)
> (#550, `29e512bf`) + [editorial-gap-matrix-norte-2026-07-22.md](editorial-gap-matrix-norte-2026-07-22.md).

---

## 0. Resumen ejecutivo

El norte editorial ya está **contratado** (#550): fila I = B (blog auto tras gates;
RRSS = inyección de link + `listo_rrss` + post humano), schema HÍBRIDO propuesto
(BD Shortlist → promueve a Publicaciones al `Aprobar`), HITL-1 de 4 salidas, y
loop de aprendizaje de `Descartar`. Lo que falta es **ejecutar** ese norte en tres
frentes encadenados, con un saneamiento previo de nits residuales:

```
P0.5  Saneamiento docs residuales (nits Cursor sobre #550)   → docs-only, no bloquea a David
   ↓
P1    Schema Notion (David crea BD Shortlist + 2 campos)      → GATE HUMANO, desbloquea todo P2
   ↓
P2    Cableado (8 paquetes orquestables Cursor→Codex/…)       → depende de P1
   ↓
P3    Smoke E2E por fase (dry-run gates=false → GO David)     → depende de P2
   ↓
P4    Optimizaciones / deuda (en paralelo donde no dependa)
```

**Ruta crítica:** `P1.1 (BD Shortlist)` es el cuello de botella. Todo P2 salvo el
puente HITL-2 (P2.6) y la inyección `listo_rrss` (P2.7) depende de que la BD exista.
P0.5 y P4 pueden avanzar sin esperar a David.

**Decisiones abiertas para David** (no bloquean el plan; son inputs a P1/P2): ver §7.

---

## 1. P0.5 — Saneamiento contrato/docs residuales

> Nits que Cursor levantó **después** del merge #550 (distintos de los 3 auto-fixes
> internos del PR). Todos **docs-only**, sin tocar schema/runtime. Dueño de edición:
> **Claude** (PR docs-only) con **GO de Cursor**. No bloquean a David.

| ID | Nit | Archivo(s) | Edición exacta propuesta | Criterio done |
|----|-----|-----------|--------------------------|---------------|
| **N1** | `listo_rrss` no aparece en el checklist de Publicaciones | [editorial-publicaciones-human-review-contract.md](editorial-publicaciones-human-review-contract.md) | Añadir bloque **"Postcondiciones de publicación (Fila I = B)"**: tras publish del blog, el sistema inyecta `published_url` + copy en las copies RRSS y marca estado **`listo_rrss`**; el post a LinkedIn/X es **humano** (no autopublish). Referencia cruzada a contrato §5.I. | El doc nombra `listo_rrss` como estado terminal RRSS bajo B |
| **N2** | Contrato cita **ADR-010 por línea** (frágil a shifts) | [contrato §5.F/§5.H/§5.I/§7](editorial-norte-hitl-contract-2026-07-22.md) + [gap-matrix](editorial-gap-matrix-norte-2026-07-22.md) | Reemplazar `ADR-010:29` → **`ADR-010 §Contexto` ("El código nunca autopublica RRSS")**; `ADR-010:39,72` → **`ADR-010 §Gates`** (handler fail-closed) / **`§Contexto` (secuencia blog→RRSS)**. Mismo criterio shift-immune que ya se aplicó a ADR-005/production-flow-v2 en el PR. | 0 citas `ADR-010:<línea>` en contrato y gap-matrix |
| **N3** | production-flow-v2 **§5 (cuerpo) contradice la Nota P0** del encabezado | [production-flow-v2-2026-06-06.md §5](../editorial-pipeline/production-flow-v2-2026-06-06.md) | La Nota P0 vive arriba; el lector que aterriza en §5 ve "Automático vía API" para LinkedIn empresa y X sin marca inline. Añadir en esas 2 celdas: **"⚠️ superseded → Fila I = B (no autopublish; ver Nota P0 y contrato §5.I)"**. | Celdas §5 de LinkedIn empresa y X marcadas inline |
| **N4** | **Telegram vs "check imagen = publish"** — ambigüedad de disparo | [contrato §5.H](editorial-norte-hitl-contract-2026-07-22.md) | **Decisión de David** (§7 de esta hoja): ¿el disparo automático de publish exige `confirmación Telegram "ok publica"` como 3ª condición **dura**, o basta `Estado imagen = Seleccionada ∧ autorizar_publicacion = true` (Telegram = sólo aviso)? production-flow-v2 §3.4 hoy la marca **obligatoria**. Tras la decisión, anotar §5.H sin ambigüedad. | §5.H declara el disparo canónico sin lectura doble |

**Nota de scope:** esta hoja **no aplica** N1–N4; los especifica listos para un PR
docs-only de seguimiento (o para agruparlos con la actualización de schemas de P1.4).

---

## 2. P1 — Schema Notion (checklist paso a paso para David)

> **Sólo David** ejecuta P1.1–P1.3 (creación/cambio de schema, ADR-007). Claude sólo
> actualiza los `.yaml` del repo **después** (P1.4), reflejando lo creado. Ningún
> agente escribe en Notion en esta fase.

### P1.1 — Crear BD **"Alternativas / Shortlist"** (superficie V1)

- **Nombre exacto sugerido:** `Alternativas / Shortlist`
- **Parent:** ⚠️ **decisión abierta (§7-D1)** — el prompt de misión indica *"Sistema
  Editorial Rick"*, pero [publicaciones.schema.yaml](../../notion/schemas/publicaciones.schema.yaml)
  fija `recommended_parent: Sistema Editorial Automatizado Umbral`. **Recomendación:**
  co-ubicar la Shortlist bajo el **mismo parent que Publicaciones** para que la
  relación `promovido_a` viva en el mismo espacio. David confirma el nombre real.
- **Propiedades** (tipo + opciones de select) — copiar del bloque **§5** de este doc.

### P1.2 — Adición mínima a **Publicaciones** (sólo David)

| Campo nuevo | Tipo | Uso |
|-------------|------|-----|
| `origen_alternativa` | relation → `Alternativas / Shortlist` | Back-link de la fila promovida a su alternativa de origen |
| `listo_rrss` | checkbox **o** opción de status | Estado terminal RRSS bajo Fila I = B (blog publicado, link+copy inyectados, post humano pendiente). **Decisión §7-D2:** checkbox aparte vs. nueva opción en `Estado`. Recomendación: **checkbox** (`Estado` se queda lineal para el blog; `listo_rrss` es marca lateral de RRSS) |

> **Nada más cambia en Publicaciones.** El resto del schema se reusa tal cual.

### P1.3 — Archivar / legacy

- Archivar la **página "shortlist" suelta** de OpenClaw (la que produce hoy
  `editorial-source-curation` como
  [shortlist-format.md](../../openclaw/workspace-templates/skills/editorial-source-curation/references/shortlist-format.md)
  a mano) **una vez** exista la BD Shortlist. Mover a un espacio "Legacy", **no borrar**.
  (También listado en P4 como limpieza.)

### P1.4 — Actualizar schemas del repo (Claude, docs-only, **después** de P1.1–P1.3)

- Crear `notion/schemas/shortlist.schema.yaml` espejando la BD real que David creó.
- Añadir `origen_alternativa` + `listo_rrss` a
  [publicaciones.schema.yaml](../../notion/schemas/publicaciones.schema.yaml).
- Nota en [ADR-007](../adr/ADR-007-notion-como-hub-editorial.md): registrar la
  superficie Shortlist como decisión de schema aprobada por David + fecha.

### P1.NOT — Qué **NO** tocar en Publicaciones

- La máquina de estados lineal (`Idea→…→Publicado`) — la Shortlist absorbe el fan-in.
- Los gates existentes (`aprobado_contenido`, `autorizar_publicacion`, `gate_invalidado`).
- Las 5 columnas de imagen (`imagen_alt_*_url`, `Selección imagen`, `Estado imagen`).
- `content_hash` / `idempotency_key` (idempotencia de **publish**, distinta del dedupe de candidato).
- El invariante `gate_invalidation_on_comment` a nivel de código: **superseded sólo para el flujo V2** (edición de David = verdad final); un agente que regenere tras aprobar **sí** resetea (contrato §7-1).

---

## 3. P2 — Cableado (paquetes orquestables Cursor → Codex/Claude/Worker/Rick)

> Cursor orquesta y emite un GO por paquete. Writes a Notion = **Worker/core**
> ([ADR-011](../adr/ADR-011-orquestacion-editorial-criterios-duros.md) #1); n8n = sólo
> bordes. Todos arrancan **gates=false / dry-run**. Ninguno autopublica RRSS.

| ID | Paquete | Superficie de código | Depende de | Riesgo | Criterio done |
|----|---------|----------------------|-----------|--------|---------------|
| **P2.1** | **Poller Aprobar → promueve a Publicaciones** | [dispatcher/notion_poller.py](../../dispatcher/notion_poller.py) + writer de promoción vía Worker/core | P1.1, P1.2 (`promovido_a`, `origen_alternativa`) | Doble-promoción / carrera → idempotencia por `alternativa_id` | Al marcar `Resultado revisión = Aprobar`, se crea **1** fila Publicaciones en `Borrador`, con back-link; re-ejecutar no duplica |
| **P2.2** | **Magnific 5 alternativas + OAuth** | **greenfield** `scripts/editorial/magnific_generate_variants.py` (hoy ausente); setup [magnific-editorial-setup-2026-06-06.md](magnific-editorial-setup-2026-06-06.md) | OAuth Magnific (**David**), P2.1 (dispara tras Aprobar) | OAuth no completado / rate limits; conteo 3 vs 5 | Genera **5** variantes → sube a `imagen_alt_1..5_url`; `Estado imagen = Listo para selección` |
| **P2.3** | **Copy Blog largo + medios + `Copy LinkedIn empresa`** | [apply_publication_copy.py](../../scripts/editorial/apply_publication_copy.py) (extender) | P1 (columna `Copy LinkedIn empresa`); ancla CAND-001 | Límite `rich_text` de `Copy Blog` (Notion ~2k) trunca cuerpos largos | Copy Blog ~350-500+ palabras vía **body de página o payload explícito al Worker**; copies por canal presentes; `Copy LinkedIn empresa` escrita (no consumida por código) |
| **P2.4** | **Dedupe de candidato vs backlog** | [scripts/discovery/lib/notion_publicaciones.py](../../scripts/discovery/lib/notion_publicaciones.py) + helper nuevo | P1 (`topic_key`, `dedupe_status`, `publicacion_relacionada`) | Falsos positivos/negativos de match de tema | Antes de registrar alternativa, consulta backlog (`Borrador`+`Publicado`) y marca `dedupe_status` + relación si aplica. **Distinto** de la idempotencia de publish |
| **P2.5** | **Loop Descartar / negativos (aprendizaje)** — fila D, la **AUSENTE** | captura de `ejemplo_negativo` + `error_kind` + `motivo_descarte` → realimenta QA/generación | P1 (esos 3 campos en Shortlist) | Loop que no cierra (se captura pero no se consume) | Al `Descartar`, se persiste el negativo estructurado y `rick-qa`/generación lo consultan para no repetir el fallo |
| **P2.6** | **Puente HITL-2 → publish blog** | evento Notion→Worker (n8n/webhook, write vía core); [worker/tasks/editorial_publish.py](../../worker/tasks/editorial_publish.py) ya fail-closed | **N4 decidido** (Telegram), gates existentes | Disparo por check de imagen suelto (¡no basta!) | Trigger exige `Estado imagen = Seleccionada` **∧** `autorizar_publicacion = true` **∧** (Telegram según N4). Publish a Azure ([ADR-010](../adr/ADR-010-azure-editorial-blog-cms.md)) sólo con gates abiertos |
| **P2.7** | **Inyección `published_url` + `listo_rrss` (NO autopublish LI/X)** | extensión post-publish de [editorial_publish.py](../../worker/tasks/editorial_publish.py) | P1 (`listo_rrss`), P2.6 | Cruzar la línea a autopublish RRSS (**prohibido**, [ADR-010 §Contexto](../adr/ADR-010-azure-editorial-blog-cms.md)) | Tras publish OK: inyecta `published_url`+copy en copies RRSS, marca `listo_rrss`; **cero** llamadas a API LinkedIn/X |
| **P2.8** | **Activar/ajustar `rick-editorial` ROLE/payload a contrato V1** | [rick-editorial/ROLE.md](../../openclaw/workspace-agent-overrides/rick-editorial/ROLE.md) + [payload template](rick-editorial-candidate-payload-template.md) | P1 (Shortlist), contrato §3 | Rick produce sin arco/estructura → `rick-qa` rechaza | Payload V1 exige `arco_narrativo`, `estructura_discurso`, `fuente_pieza_url` (no home); alineado a campos Shortlist; activación con GO David + PR aparte |

---

## 4. P3 — Smoke E2E (dry-run primero; publish sólo con GO David)

> Un smoke **por fase**, en `dry-run` / `gates=false`, encadenados. Publish real
> **sólo** con GO explícito de David y por Worker (nunca por agente/Cursor).

| ID | Smoke | Precondición | Criterio done |
|----|-------|--------------|---------------|
| **P3.1** | V1: alternativa con arco + estructura + fuente-pieza en Shortlist | P2.8 | `rick-qa` la valida; 3 exigencias §3 presentes; fuente = `item_url` (no home) |
| **P3.2** | HITL-1: las 4 salidas (Archivar/Observar/Descartar/Aprobar) | P1, P2.1, P2.5 | Cada salida produce su efecto de sistema; `Aprobar` promueve; `Descartar` captura negativo |
| **P3.3** | V2: copy largo + 5 imágenes tras Aprobar | P2.2, P2.3 | Copy ancla ~CAND-001; 5 `imagen_alt_*_url`; sin exceder rich_text |
| **P3.4** | Dedupe: candidato duplicado detectado | P2.4 | `dedupe_status = duplicado_*` con relación correcta |
| **P3.5** | HITL-2 → publish blog **dry-run** | P2.6 | `would_publish` respeta doble gate (+Telegram según N4); `dry_run` no toca Azure |
| **P3.6** | RRSS = B: `published_url` + `listo_rrss`, **sin** post RRSS | P2.7 | Estado `listo_rrss`; cero llamadas LinkedIn/X |
| **P3.7** | Publish real (blog) | **GO David** + Worker | 1 post en Azure, idempotente; `published_url` real inyectado |

---

## 5. Cambios Notion — bloque listo para copiar/pegar cuando David cree la BD

> **No crear aún.** Campos exactos de la BD **`Alternativas / Shortlist`**
> (fuente: contrato §6). Tipos Notion entre paréntesis; opciones de select listadas.

```text
BD: Alternativas / Shortlist
Parent: <confirmar — recomendado: mismo parent que Publicaciones>

CAMPOS:
- Título                     (title)      → título/ángulo de la alternativa
- alternativa_id             (rich_text)  → ID estable (correlación / promoción)
- topic_key                  (rich_text)  → tema normalizado para dedupe (fila J)
- arco_narrativo             (rich_text)  → OBLIGATORIO (§3): trayectoria de la pieza
- estructura_discurso        (rich_text)  → OBLIGATORIO (§3): pie de estructura de discurso usado
- premisa                    (rich_text)  → tesis condensada 1-2 frases
- fuente_pieza_url           (url)        → OBLIGATORIO: URL de la PIEZA concreta (NO home)
- fuente_tipo                (select)     → opciones:
      primary_source | original_article | official_doc |
      analysis_source | discovery_source | contextual_reference
- fuente_discovery_url       (url)        → home/feed de descubrimiento (trace interno, no citable)
- canal_sugerido             (select)     → opciones: blog | linkedin | x | newsletter
- score_alineacion           (number)     → score compuesto 0-100
- Resultado revisión         (select)     → opciones (HITL-1, §4):
      Pendiente | Archivar | Observar | Descartar | Aprobar
- motivo_descarte            (rich_text)  → requerido si Descartar
- ejemplo_negativo           (checkbox)   → marca captura de negativo (loop aprendizaje)
- error_kind                 (multi_select) → tipo de fallo (alimenta QA/generación)
- dedupe_status              (select)     → opciones: nuevo | duplicado_borrador | duplicado_publicado
- publicacion_relacionada    (relation → Publicaciones) → fila detectada por dedupe
- promovido_a                (relation → Publicaciones) → fila creada al Aprobar
- (Observar)                 → usar COMENTARIOS nativos de Notion (sin campo dedicado)

ADICIÓN MÍNIMA A "Publicaciones" (solo David):
- origen_alternativa         (relation → Alternativas / Shortlist) → back-link
- listo_rrss                 (checkbox | opción de status)         → estado terminal RRSS (Fila I = B)

NO TOCAR EN PUBLICACIONES:
- máquina de estados lineal, gates existentes, columnas de imagen (5),
  content_hash / idempotency_key.
```

---

## 6. Backlog de megaprompts sugeridos (uno por paquete)

> Uno por GO. Cursor los emite cuando toque; aquí sólo el **titular + objetivo +
> gate de cierre**. Todos declaran: sin publish, gates=false, no simular Rick, no
> rotar secretos, no reactivar stage8/9c.

| # | Megaprompt (titular) | Objetivo | Dueño ejecutor | Gate de cierre |
|---|----------------------|----------|----------------|----------------|
| MP-0.5 | **Docs sanitize N1–N4** | Aplicar N1–N3 (docs) + registrar decisión N4 | Claude | `EDITORIAL_DOCS_SANITIZED` |
| MP-1.4 | **Schemas repo espejo Shortlist** | `shortlist.schema.yaml` + campos en `publicaciones.schema.yaml` + nota ADR-007 (**tras** P1 David) | Claude | `EDITORIAL_SCHEMAS_SYNCED` |
| MP-2.1 | **Poller Aprobar→promueve** | Promoción idempotente Shortlist→Publicaciones vía Worker | Codex/Worker | `EDITORIAL_PROMOTE_WIRED` |
| MP-2.2 | **Magnific 5 alts** | Generador `magnific_generate_variants.py` + OAuth (David) | Codex + David | `EDITORIAL_MAGNIFIC_WIRED` |
| MP-2.3 | **Copy largo + LinkedIn empresa** | Extender `apply_publication_copy.py`; resolver límite rich_text | Codex | `EDITORIAL_COPY_WIRED` |
| MP-2.4 | **Dedupe candidato** | Helper de dedupe vs backlog Publicaciones | Codex | `EDITORIAL_DEDUPE_WIRED` |
| MP-2.5 | **Loop negativos (fila D)** | Captura `ejemplo_negativo`/`error_kind` → consumo QA | Codex/Rick | `EDITORIAL_NEGATIVE_LOOP_WIRED` |
| MP-2.6 | **Puente HITL-2 publish** | Evento Notion→Worker con triple condición (N4) | Codex/Worker | `EDITORIAL_HITL2_BRIDGE_WIRED` |
| MP-2.7 | **Inyección link + listo_rrss** | Post-publish: `published_url`+`listo_rrss`, sin auto RRSS | Codex/Worker | `EDITORIAL_RRSS_INJECTION_WIRED` |
| MP-2.8 | **Rick-editorial V1** | Ajustar ROLE/payload a §3; activación con GO David | Claude+Rick | `RICK_EDITORIAL_V1_READY` |
| MP-3 | **Smoke E2E por fase** | P3.1–P3.7 dry-run; publish real sólo GO David | Cursor+David | `EDITORIAL_SMOKE_E2E_PASS` |

---

## 7. Decisiones abiertas para David (inputs, no bloqueantes del plan)

| # | Decisión | Opciones | Recomendación |
|---|----------|----------|---------------|
| **D1** | **Parent de la BD Shortlist** | (a) `Sistema Editorial Rick` (prompt misión) · (b) `Sistema Editorial Automatizado Umbral` (parent de Publicaciones) | **(b)** co-ubicar con Publicaciones; confirmar el nombre real del parent vivo |
| **D2** | **`listo_rrss`: forma** | (a) checkbox lateral · (b) nueva opción en `Estado` | **(a)** checkbox — mantiene `Estado` lineal para blog |
| **D3** | **N4 — Telegram en el disparo de publish** | (a) Telegram "ok publica" = 3ª condición dura · (b) basta `autorizar_publicacion=true`, Telegram = aviso | **(a)** coherente con production-flow-v2 §3.4; confirmar |
| **D4** | **Fila I** | queda en **B** (no autopublish) | Mantener B; A requiere PR aparte + access review LinkedIn |

---

## 8. Optimizaciones / deuda (P4 — en paralelo donde no dependa de P1)

| ID | Deuda | Acción | Dueño | Nota |
|----|-------|--------|-------|------|
| **P4.1** | **Referentes vs Publicaciones** (drift master-plan) | Aclarar en docs que **S4 escribe en `📰 Publicaciones de Referentes`** (discovery), no en la editorial `📰 Publicaciones` (esa la escribe S7). Fuente: `stage4_push_notion.py:2,8` | Claude (docs) | Ya anotado en contrato §7-3 y gap-matrix; falta cerrar el drift en `master-plan.md` §3/§4 |
| **P4.2** | **stage8 / stage9c en HOLD** | **NO reactivar** (fail-closed por Ola-guards). Documentar como deuda con HOLD explícito; revisión sólo con GO David | — (HOLD) | PROHIBIDO reactivar en este frente |
| **P4.3** | **Conflictos residuales en docs superseded** | Verificar que ADR-005 §Blog y production-flow-v2 §5 llevan su Nota P0 coherente (ligado a N2/N3) | Claude (docs) | Cierra el círculo de §7 del contrato |
| **P4.4** | **Cleanup página OpenClaw shortlist suelta** | Archivar a "Legacy" tras crear la BD Shortlist (= P1.3) | David | No borrar; mover |
| **P4.5** | **Límite `rich_text` de `Copy Blog`** | Decidir body-de-página vs payload explícito al Worker (ligado a P2.3) | Codex + David | [notion-blog-linkedin-v3-content-model.md §Limitation](notion-blog-linkedin-v3-content-model.md) |

---

## 9. Referencias

- Contrato del norte: [editorial-norte-hitl-contract-2026-07-22.md](editorial-norte-hitl-contract-2026-07-22.md)
- Matriz de brecha: [editorial-gap-matrix-norte-2026-07-22.md](editorial-gap-matrix-norte-2026-07-22.md)
- [production-flow-v2-2026-06-06.md](../editorial-pipeline/production-flow-v2-2026-06-06.md) · [master-plan.md](../editorial-pipeline/master-plan.md)
- ADRs: [005](../adr/ADR-005-publicacion-multicanal.md) · [007](../adr/ADR-007-notion-como-hub-editorial.md) · [009](../adr/ADR-009-linkedin-company-api.md) · [010](../adr/ADR-010-azure-editorial-blog-cms.md) · [011](../adr/ADR-011-orquestacion-editorial-criterios-duros.md)
- Schema: [publicaciones.schema.yaml](../../notion/schemas/publicaciones.schema.yaml)
- Contenido: [notion-blog-linkedin-v3-content-model.md](notion-blog-linkedin-v3-content-model.md) · [editorial-source-attribution-policy.md](editorial-source-attribution-policy.md)
- Rick: [rick-editorial/ROLE.md](../../openclaw/workspace-agent-overrides/rick-editorial/ROLE.md) · [payload template](rick-editorial-candidate-payload-template.md)

---

**EDITORIAL_ROADMAP_READY** [E]

- [E1] Base verificada: `origin/main` incluye #550 (`29e512bf`); contrato + gap-matrix presentes.
- [E2] Cobertura: P0.5 (N1–N4) · P1 (schema David + §5 copy/paste) · P2 (8 paquetes) · P3 (7 smokes) · P4 (5 deudas).
- [E3] Entregables: tabla `paso|dueño|dependencia|riesgo|criterio done` (§3), bloque Notion copy/paste (§5), backlog de 11 megaprompts (§6), 4 decisiones para David (§7).
- [E4] Cumplimiento PROHIBIDO: sólo plan/docs; sin DB/filas live, sin gates/publish/RRSS auto, sin copy Rick, sin merge, sin rotar secretos, sin reactivar stage8/9c.
