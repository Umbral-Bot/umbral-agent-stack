# Fuente primaria = home: causa raíz + guard fail-closed (PKG-MACRO-P5-Q12-T3, 2026-08-25)

David confirmó T2 paso 0: `CAND-OLA3-03` (`3a55f443-fb5c-81d1-b1f6-fe1b95dfd336`,
Canal blog) tiene `Fuente primaria = https://www.buildingsmart.org/` — la home,
no la pieza. Pedido: no parche manual de esa URL — causa raíz + fail-closed
en el sistema.

## Corrección a T1/T2: la fecha de creación que usé estaba mal

En T1/T2 asumí (sin verificarlo contra la página) que `CAND-OLA3-03` se creó
2026-03-09 — dato que en realidad correspondía a un workflow n8n muerto no
relacionado ("Editorial Shortlist", stub de 2 nodos, ver Q10). Releído
directo de la API de Notion (`get_page`, solo lectura): **`created_time` =
`2026-07-22T07:31:00.000Z`**, igual a `last_edited_time` — la fila nunca se
tocó desde que se creó. Esto cambia la lectura de causa raíz por completo:
no es un defecto de marzo sin corregir en 4 meses, es un defecto del mismo
día en que se escribió la política que lo hubiera atrapado.

## Causa raíz — productor [E]

- **No hay pipeline automatizado que la haya creado.** `scripts/discovery/`
  y `scripts/editorial/` no existían en marzo 2026 y no tienen ningún script
  de "shortlist Ola 3" en julio tampoco. Grep de todo el repo por
  Ola-3/CAND-OLA3: los únicos productores rastreables son
  `docs/ops/ola3-editorial-5-pitches-2026-07-20.md` (5 pitches humanos) y,
  para `CAND-OLA3-02` específicamente, un flujo pitch→GO humano→archivo
  docs-only (`docs/ops/candidates/ola3-pitch02-...md`, PR #546).
  **`CAND-OLA3-01`/`-03` no tienen ese archivo** — se escribieron directo en
  Notion por un flujo "Shortlist editorial guiada" sin equivalente en el repo.
- Notion `created_by` de la fila = el usuario/integración `3145f443-...` y
  `Creado por sistema = true` — atribución de API, consistente con una
  sesión Claude/Cursor escribiendo vía la integración, no un humano
  clickeando "New" en la UI. `trace_id`, `idempotency_key`, `content_hash`,
  `origen_alternativa` todos vacíos — sin relación a ninguna fila
  Alternativas/Shortlist, sin rastro de ningún pipeline determinístico
  (contrasta con `editorial_promote.py`, que sí los llenaría).
- **Identidad exacta del run: UNVERIFIED.** Sin `trace_id` ni archivo docs
  para -03 específicamente, no hay forma de nombrar un run id/lane preciso —
  solo la ventana (mismo día que la creación de la página "Shortlist
  editorial guiada" LEGACY, `docs/ops/uas-panel-4-content-classify-20260810.md:120`,
  creada 2026-07-22T07:27Z, 4 minutos antes).

## Por qué pasó una home — el agujero real [E]

Tres capas revisadas, las tres con el mismo resultado — **nada rechazaba
home/feed en ningún lado ejecutable**:

1. **`scripts/discovery/lib/gates.py`** (`fuente_primaria_ok`, antes de este
   pack): `fuente_ok = bool(fuente_primaria)` — presencia, nada más. No
   parsea la URL, no distingue home de pieza. Cableado real (no muerto): lo
   llama `publish_guard.assert_can_publish()`, y a eso lo llama
   `stage9c_linkedin_publish.py` en el loop real de publish — pero esa es
   **la base "📰 Publicaciones de Referentes" para LinkedIn**, un pipeline
   distinto al de `Publicaciones` (blog HITL-2) donde vive `CAND-OLA3-03`.
   El "Stage 10" que el propio código dice que debería ser "el único writer"
   de `Publicaciones` (`notion_publicaciones.py:8`) **nunca se implementó** —
   está en el spec doc, no en código.
2. **`rick-editorial` ROLE.md** exige `fuente_pieza_url` de la pieza
   concreta — pero el propio ROLE dice **"Status: design-only / not
   active"**. Confirmado en vivo: cero referencias a `rick-editorial` en
   `~/.openclaw/openclaw.json`, sin directorio en `~/.openclaw/agents/`.
   Nunca corrió.
3. **`rick-qa` ROLE.md** exige rechazar `fuente_pieza_url` home/feed en V1,
   citando a `CAND-OLA3-03` como ejemplo — pero es **prosa para un agente
   LLM invocado a demanda**, sin ningún código/test que lo ejecute
   independiente de que alguien lo invoque. Confirmado en vivo: `rick-qa` sí
   está registrado en `openclaw.json` y tiene sesiones recientes, pero cero
   wiring hacia el path real que escribe `Publicaciones`
   (`editorial_dedupe.py`, `editorial_promote.py`, `editorial_publish.py`
   son Python puro, ninguno llama a un subagente). Y la regla específica que
   cita a `CAND-OLA3-03` (commit `29e512bf`, 2026-07-22) se escribió el
   **mismo día** que la fila — usándola como el ejemplo que motivó la regla,
   no como una regla preexistente que la fila esquivó.

**El agujero que sí importa para el futuro** (no el histórico, el que deja
pasar el próximo `CAND-OLA3-04`): `worker/tasks/editorial_promote.py`
(`handle_editorial_promote_shortlist_approval`) copia `fuente_pieza_url` de
Alternativas/Shortlist a `Fuente primaria` sin validar nada.

**Corrección sobre la marcha (encontrada por `/code-review`, no por Fase A):**
no es el único escritor. `scripts/discovery/stage7_publish_drafts.py`
(línea ~197) escribe `Fuente primaria` en la **misma DB**
(`e6817ec4698a4f0fbbc8fedcf4e52472` == `NOTION_PUBLICACIONES_DB_ID` sin
guiones) tomando `fuentes_urls[0]` sin ningún gate — vivo, no archivado,
documentado en `scripts/vps/discovery-publish-cron.sh` como invocable a
mano ("NOT wired into cron — manual hasta gate humano"). Los dos quedaron
cerrados en este pack. Un tercero, menor: `scripts/create_cand003_notion.py`
(script de un solo uso, ya corrido, con su propio chequeo de idempotencia —
no re-dispara) también escribe `Fuente primaria` sin gate; queda sin
cerrar, riesgo bajo dado que es histórico y no recurrente.

## Guard fail-closed agregado — [E] tests

- **`scripts/discovery/lib/url_classify.py`** (nuevo): `is_home_or_feed_url(url)`
  — estructural (path vacío = home; `/feed`, `/rss`, `/atom`, `.xml`/`.rss`/`.atom`
  = feed), **no un dominio hardcodeado**. `buildingsmart.org/` → home;
  `buildingsmart.org/ifc-4-3-approved-as-a-final-standard/` (la pieza real,
  mismo dominio) → no flaggeado.
- **`gates.py`**: `fuente_primaria_ok` ahora exige presencia Y
  `not is_home_or_feed_url(...)`. Tests: home bloquea, feed bloquea, pieza
  concreta en el mismo dominio pasa (`tests/lib/test_gates.py`).
- **`editorial_promote.py`**: `handle_editorial_promote_shortlist_approval`
  ahora **rechaza la promoción completa** (`ok:false,
  error:fuente_pieza_url_is_home_or_feed`) si `fuente_pieza_url` es home/feed
  — en dry_run y en real, antes de escribir nada a Notion. Tests con la URL
  real de `CAND-OLA3-03` (`tests/test_editorial_promote.py`).
- **`stage7_publish_drafts.py`**: `build_page_payload` ahora levanta
  `ValueError` si `fuentes_urls[0]` es home/feed; `main()` lo captura con el
  mismo camino ya existente de fail/log/`mark_proposal_failed` (no crashea,
  no crea la página, no pierde el proposal — queda en `draft` con
  `last_error` explicando por qué). Tests en
  `tests/discovery/test_stage7_publish_drafts.py`.
- `tests/lib/test_url_classify.py`: 24 casos unitarios (home, feed, pieza
  concreta, edge cases vacío/malformado).
- `tests/discovery/`, `tests/lib/`, `tests/test_editorial_promote.py` y la
  suite completa: verde. Ver REPORT para el conteo.

## Fase C — BLOCKED_RUNTIME

No hay productor runtime vivo para re-emitir `CAND-OLA3-03` por el path
oficial: `rick-editorial` es design-only (confirmado arriba), y
`editorial_promote.py` no tiene nada que promover — `origen_alternativa` de
la fila está vacío, **no existe una fila Alternativas/Shortlist previa**
para este candidato (se escribió directo a Publicaciones). Crear una fila
Shortlist con una URL elegida por Claude sería exactamente lo prohibido
("no sustituye a Rick"); pedirle la URL a David también está prohibido.

**GO de activación exacto para David**, dos caminos, no excluyentes:

1. **Activar `rick-editorial`** (registro en `openclaw.json` + workspace) —
   condiciones de activación ya declaradas en su propio ROLE.md, sin
   cumplir hoy. Decisión de producto, no de este pack.
2. **Puntual, sin activar el agente**: alguien con criterio editorial (David
   o Rick bajo supervisión) identifica la URL concreta real del artículo/
   reporte de buildingSMART/openBIM que sustenta el claim de `CAND-OLA3-03`,
   crea la fila Alternativas/Shortlist correspondiente con esa
   `fuente_pieza_url`, marca `Resultado revisión = Aprobar`, y se invoca
   `editorial.promote_shortlist_approval` con ese page id — el guard nuevo
   la deja pasar si es una pieza real, o la vuelve a rechazar (esta vez de
   verdad, no en docs) si no lo es.

Ninguno de los dos caminos se ejecuta en este pack.
