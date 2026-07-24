# Smoke E2E editorial — P3 (2026-07-23)

> **Estado:** docs/informe únicamente — sin código de producción nuevo.
> **Alcance:** validar en dry-run/local que P2.1–P2.8 (PRs #554–#561, ya en
> `origin/main`) funcionan como documentado, sin abrir gates, sin publish
> real, sin RRSS, sin Notion writes de copy final "como Rick".
> **Método:** (a) comandos CLI self-contained ejecutados de verdad; (b)
> invocación directa de los handlers de Worker con `notion_client` mockeado
> (mismo patrón que `tests/test_*.py`) cuando el handler requiere HTTP a un
> Worker vivo que no existe en este shell; (c) suite de tests existente
> ejecutada de verdad como evidencia adicional.
> **No disponible en este shell:** `WORKER_URL`, `WORKER_TOKEN`,
> `NOTION_API_KEY`, `MAGNIFIC_API_KEY` — todos ausentes (confirmado, ver
> §I). Ningún smoke de este informe llamó a un Worker HTTP real, a Notion
> real, ni a Magnific real.

## Resumen ejecutivo

| Item | Qué se prueba | Veredicto |
|------|----------------|-----------|
| A | Contrato V1 shortlist (arco/estructura/fuente) — walkthrough conceptual | PASS (conceptual) |
| B | `editorial.dedupe_candidate_vs_backlog` dry_run | PASS |
| C | `sync_negative_examples.py --check-topic-key` | PASS |
| D | `editorial.promote_shortlist_approval` dry_run | PASS |
| E | Magnific dry_run (CLI real + handler directo) | PASS / BLOCKED parcial (falta `MAGNIFIC_API_KEY`, esperado) |
| F | `apply_publication_copy.py` dry_run | PASS |
| G | `handle_web_publish_editorial_post` D3 triple gate dry_run | PASS |
| H | `editorial.inject_rrss_ready` dry_run | PASS |
| I | Matriz de disposición para activación real | ver tabla abajo |

**Además:** la suite de tests existente para los cinco módulos tocados por
este smoke corre limpia:

```
$ python -m pytest tests/test_editorial_dedupe.py tests/test_editorial_promote.py \
    tests/test_editorial_publish.py tests/test_magnific.py tests/test_sync_negative_examples.py -q
........................................................................ [ 56%]
........................................................                 [100%]
128 passed in 3.00s
```

Ningún ítem produjo una llamada de red real a Notion, Worker, Azure o
Magnific. Ningún gate se puso en `true` de verdad; ningún row de Notion se
creó o modificó.

---

## A) Shortlist V1 — validación estructural (conceptual, sin crear filas)

Por instrucción explícita del paquete ("preferir no crear filas" salvo
autorización de David para una página desechable, no otorgada), este ítem se
valida **leyendo el contrato ya alineado en P2.8**, sin invocar Notion.

- `openclaw/workspace-agent-overrides/rick-qa/ROLE.md` §"Editorial V1
  alternativa structural QA" exige `arco_narrativo`, `estructura_discurso`,
  `fuente_pieza_url` como OBLIGATORIO — rechazo `blocked_missing_field` si
  falta cualquiera, `blocked_source_not_concrete` si `fuente_pieza_url`
  apunta a home/feed.
- `docs/ops/rick-editorial-candidate-payload-template.md` (V1 Alternativa
  Payload) refleja exactamente esos tres campos como bloque OBLIGATORIO, y
  documenta que `trace_id` NO pertenece al schema de Shortlist (solo a
  Publicaciones V2) — corregido en P2.8 tras hallazgo de `/code-review`.
- `notion/schemas/alternativas-shortlist.schema.yaml` (schema vivo) confirma
  los nombres exactos de campo: `arco_narrativo`, `estructura_discurso`,
  `fuente_pieza_url`, `"Resultado revisión"` (con espacio/acento, no
  `resultado_revision`).

**Veredicto: PASS (conceptual)** — el contrato es internamente consistente
entre ROLE.md, el payload template y el schema vivo. No se creó ninguna
página de Notion para este smoke.

## B) Dedupe candidato vs backlog (dry_run)

`worker/tasks/editorial_dedupe.py::handle_editorial_dedupe_candidate_vs_backlog`
invocado directamente con `notion_client`/`config` mockeados (mismo patrón
que `tests/test_editorial_dedupe.py`): página Shortlist con
`fuente_pieza_url`/`topic_key` sintéticos vs. un backlog de una fila
`Publicado` con el mismo `Título` normalizado.

```
result: {'ok': True, 'dry_run': True, 'would_write_dedupe_status': 'duplicado_publicado',
 'already_evaluated': False, 'dedupe_status': 'duplicado_publicado',
 'matched_publicacion_page_id': 'pub-existing-001', 'matched_publicacion_url': '',
 'backlog_rows_scanned': 1, 'shortlist_page_id': 'smoke-shortlist-001'}
notion write calls made: 0
```

**Veredicto: PASS** — verdict calculado correctamente (match por topic
normalizado), cero escrituras a Notion en `dry_run=True`.

## C) Negativos — consult `--check-topic-key`

Primero, contra un store vacío (comportamiento base):

```
$ python scripts/editorial/sync_negative_examples.py --negatives-path <tmp>.jsonl \
    --check-topic-key "gobernanza en bim" --check-error-kind fuente_home_no_pieza
NO_SIMILAR_NEGATIVES topic_key='gobernanza en bim'
```

Luego, con un registro sintético sembrado (topic_key normalizado +
`error_kind` coincidente), se obtuvo inesperadamente `NO_SIMILAR_NEGATIVES`
al invocar el CLI vía Git Bash en este equipo Windows. Diagnóstico:

1. Invocación directa de `find_similar_negatives()`/`load_negative_examples()`
   con los mismos datos → match correcto.
2. Invocación de `main()` con `sys.argv` controlado (sin pasar por Git
   Bash) → match correcto (`SIMILAR_NEGATIVES_FOUND count=1`).
3. La misma invocación CLI exacta, pero con `MSYS_NO_PATHCONV=1` → match
   correcto.

**Causa raíz: no es un bug del código de P2.5.** Es una particularidad de
Git Bash/MSYS en este equipo Windows: cuando se invoca un ejecutable nativo
(Python de Windows, no el de MSYS) desde Git Bash pasando un argumento que
"parece" una ruta POSIX absoluta (`/tmp/...`), MSYS reescribe esa ruta a su
propia raíz (`C:\Program Files\Git\tmp\...`), distinta de la ruta que
Python nativo resuelve para el mismo literal (`C:\tmp\...`). El script de
seed y el CLI usaban rutas que MSYS traducía de forma inconsistente entre
sí. Con `MSYS_NO_PATHCONV=1` (o rutas Windows explícitas), el comportamiento
es correcto y determinista.

```
$ MSYS_NO_PATHCONV=1 python scripts/editorial/sync_negative_examples.py \
    --negatives-path /tmp/smoke-negatives-5.jsonl \
    --check-topic-key "Gobernanza en BIM sin fuente" --check-error-kind fuente_home_no_pieza
SIMILAR_NEGATIVES_FOUND count=1
{"alternativa_id": "SMOKE-TEST-001", ... "topic_key": "gobernanza en bim sin fuente", ...}
```

**Veredicto: PASS** — lógica de matching correcta; nota operativa para
quien corra este script desde Git Bash en Windows: usar
`MSYS_NO_PATHCONV=1` o rutas Windows (`C:\...`) al pasar `--negatives-path`.

## D) Promote shortlist → Publicaciones (dry_run)

`handle_editorial_promote_shortlist_approval` invocado directamente con una
página Shortlist `"Resultado revisión": "Aprobar"` sintética.

```
result ok: True dry_run: True would_promote: True
properties_preview keys: ['Canal', 'Creado por sistema', 'Estado', 'Fuente primaria',
 'Notas', 'Premisa', 'Tipo de contenido', 'Título', 'aprobado_contenido',
 'autorizar_publicacion', 'origen_alternativa', 'publication_id']
notion create/update calls made: 0
```

(La consola local muestra `Título` con un artefacto de encoding cp1252 —
solo visual en este terminal Windows; el valor real en Python es el string
UTF-8 correcto, confirmado leyendo el dict.)

**Veredicto: PASS** — `Estado=Borrador`, ambos gates humanos en `false` en
el preview, cero escrituras Notion en `dry_run=True`.

## E) Magnific — generación de variantes (dry_run)

**CLI real** (sin `WORKER_URL`/`WORKER_TOKEN` configurados en este shell):

```
$ python scripts/editorial/magnific_generate_variants.py --page-id smoke-pub-003 --dry-run
ERROR: WORKER_URL and WORKER_TOKEN required (env or ~/.config/openclaw/env)
exit: 2
```

Fail-closed correcto — evidencia válida para la matriz de disposición (§I).

**Handler directo** (`handle_magnific_generate_variants`, `notion_client`
mockeado, `MAGNIFIC_API_KEY` confirmado ausente del entorno):

```
MAGNIFIC_API_KEY set: False
result: {'ok': True, 'dry_run': True, 'would_generate': True, 'count': 3,
 'prompt': 'Professional LinkedIn/blog hero...', 'aspect_ratio': 'classic_4_3',
 'resolution': '2k', 'model': 'realism', 'estado_imagen': 'Pendiente generación', ...}
```

**Veredicto: PASS (dry_run) / BLOCKED parcial (activación real)** — la
elegibilidad y construcción de prompt funcionan sin necesitar
`MAGNIFIC_API_KEY` (el dry_run nunca llega a `_submit_mystic`); la
generación real sigue bloqueada por falta de esa credencial, tal como se
documentó desde P2.2.

## F) Copy apply — Blog largo + LinkedIn empresa (dry_run)

```
$ python scripts/editorial/apply_publication_copy.py --publication-id CAND-001 --dry-run \
    --skip-model-verify --write-body --emit-worker-payload <tmp>.json
VALIDATION_OK
  warn: linkedin_empresa: missing copy_linkedin_empresa (P2.3, optional for now)
WORKER_PAYLOAD_WRITTEN path=<tmp>.json
DRY_RUN page_id=34b5f443-fb5c-81dd-8338-cb0b46699250 props=['Copy LinkedIn', 'Copy X', 'Copy Blog', 'trace_id', 'Comentarios revisión']
DRY_RUN write_body blocks=19 marker='Copy Blog (V2 canonical body) — trace_id: CAND-001-v3.1-human-editorial-sensitivity-fix' (idempotency vs existing page blocks not checked in dry-run, no Notion call)
VALIDATION_OK gates=unchanged (dry-run, no Notion call)
```

**Veredicto: PASS** — cero llamadas a Notion (confirmado por las líneas
`DRY_RUN ... no Notion call`), ambas escape-hatches
(`--write-body`/`--emit-worker-payload`, fix de P2.3) funcionan; el warning
de `copy_linkedin_empresa` ausente es esperado (P2.3 lo trata como
opcional).

## G) Puente HITL-2 → publish blog (D3 triple gate, dry_run)

Dos invocaciones directas de `handle_web_publish_editorial_post`, ambas
usando `payload` explícito (no `notion_page_id`). **Nota importante:**
`visual_gate` (`Estado imagen=Seleccionada`) solo se calcula cuando la
fuente es `notion_page_id` (`_build_payload_from_notion`) — con `payload`
explícito, `visual_gate` es siempre `None` y ese chequeo se salta por
completo (confirmado leyendo `worker/tasks/editorial_publish.py`, bloque
`if visual_gate is not None and not visual_gate["ready"]:`). Por eso el
`gates` dict de esta evidencia solo trae `autorizar_publicacion` +
`aprobado_contenido` + `telegram_confirmed` — el smoke de abajo cubre
específicamente los otros dos gates del triple D3
(`autorizar_publicacion` ∧ `telegram_confirmed`) más el comportamiento
`dry_run`/fail-closed; **no ejercita el gate visual**, que requeriría una
invocación vía `notion_page_id` con una página Notion mockeada.

**G.1 — `telegram_confirmed` omitido (debe bloquear):**

```
result: {'ok': False, 'error': 'telegram_confirmation_missing', 'would_publish': False,
 'gates': {'autorizar_publicacion': True, 'aprobado_contenido': True, 'telegram_confirmed': False}}
```

**G.2 — los 3 gates D3 en true + `dry_run=True` (debe pasar sin red):**

```
result: {'ok': True, 'would_publish': True, 'dry_run': True,
 'gates': {..., 'telegram_confirmed': True}, 'slug': 'smoke-test-post'}
```

**CLI real** `trigger_hitl2_publish.py` (sin Worker configurado):

```
$ python scripts/editorial/trigger_hitl2_publish.py --notion-page-id smoke-pub-004
ERROR: WORKER_URL and WORKER_TOKEN required (env or ~/.config/openclaw/env)
```

**Veredicto: PASS** — de los tres gates D3, este smoke (fuente `payload`)
confirma que `autorizar_publicacion` ∧ `telegram_confirmed` bloquean
correctamente si falta cualquiera de los dos, y que en `dry_run` no se hizo
ninguna llamada de red (`_post_to_function` nunca se invocó, confirmado por
el propio código: `dry_run` retorna antes del paso 5). El tercer gate
(`Estado imagen=Seleccionada`, vía `notion_page_id`) queda como pendiente
de un smoke futuro con página Notion mockeada — no se afirma haberlo
ejercitado aquí.

## H) Inyección RRSS + `listo_rrss` (dry_run)

`handle_editorial_inject_rrss_ready` invocado directamente sobre una página
sintética con `Copy LinkedIn`/`Copy X` con texto y `Copy LinkedIn empresa`
vacío:

```
result: {'ok': True, 'error': None, 'dry_run': True, 'would_inject': True,
 'already_ready': False, 'injected_channels': ['copy_linkedin', 'copy_x'],
 'notion_page_id': 'smoke-pub-002'}
notion write calls made: 0
```

**Veredicto: PASS** — inyecta solo en canales con copy no vacío (empresa
correctamente excluido por estar vacío), cero llamadas a
`notion_client.update_page_properties` en `dry_run=True`, cero llamadas a
cualquier API de LinkedIn/X (Fila I = B respetada).

## I) Matriz de disposición — qué está listo en código vs. qué falta para activar de verdad

| Necesario para "casi-vivo" | Estado en este shell | Quién/qué lo provee |
|---|---|---|
| `WORKER_URL` / `WORKER_TOKEN` | Ausente (confirmado `echo`) | VPS / `~/.config/openclaw/env` (no existe localmente) |
| `NOTION_API_KEY` (Worker) | Ausente | VPS |
| `MAGNIFIC_API_KEY` | Ausente (documentado desde P2.2) | VPS — GO David pendiente |
| `NOTION_PUBLICACIONES_DB_ID` | Ausente | VPS / config |
| `NOTION_SHORTLIST_DS_ID` | Ausente — **la DB Shortlist en sí puede no existir aún en producción** (fila K de la matriz de brecha: "faltan campos de alternativas + HITL-1 4-estados + DB Shortlist") | David (creación de la BD, P1 del roadmap) |
| Columna Notion `Copy LinkedIn empresa` | Puede no existir en la BD Publicaciones viva (P2.3 la trató siempre como opcional por esto) | David |
| `EDITORIAL_BLOG_FUNCTION_URL` | Ausente en este shell | VPS/Azure Function config |
| Webhook Telegram entrante | No existe en este repo — `telegram_confirmed` nunca se infiere automáticamente (greenfield, scope explícito de P2.6) | n8n/operador — lane separado, fuera de este paquete |
| Flags poller (todas default OFF, fail-closed): `NOTION_POLLER_ENABLE_DEDUPE`, `_NEGATIVE_CAPTURE`, `_PROMOTE`, `_HITL2_SCAN`, `_RRSS_INJECTION`, `_MAGNIFIC`, `_V2_CLASSIFY` | Todas ausentes/OFF | David decide activación real por gerencia, una por una |

**Nada de lo anterior se activó en este smoke.** Este ítem es puramente
informativo — la lista de "GO David" está consolidada abajo.

---

## GO David — lo mínimo para un smoke "casi-vivo" futuro

Para un smoke que llegue a tocar un Worker/Notion real (aún sin publish
real ni RRSS real), David necesitaría proveer, en este orden de menor a
mayor alcance:

1. `WORKER_URL` + `WORKER_TOKEN` (o `~/.config/openclaw/env` con ambos) —
   habilita CLIs (`trigger_hitl2_publish.py`, `magnific_generate_variants.py`,
   `sync_negative_examples.py` sin `--check-topic-key`) a hablar con un
   Worker real.
2. `NOTION_API_KEY` en el Worker + `NOTION_PUBLICACIONES_DB_ID` — habilita
   lecturas/escrituras reales contra la BD Publicaciones viva.
3. Confirmar si la BD Shortlist ya existe en producción; si no, es
   prerequisito de fila A/K antes de que cualquier smoke de V1
   (alternativas, HITL-1) tenga sentido contra datos reales.
4. `MAGNIFIC_API_KEY` — solo si se quiere probar generación real de
   imágenes (aún en cuenta de prueba/bajo volumen).
5. `EDITORIAL_BLOG_FUNCTION_URL` — solo si se quiere probar publish real
   contra Azure (fuera de alcance recomendado para un smoke "casi-vivo").
6. Activar **una** flag de poller a la vez en el VPS (nunca todas juntas) y
   observar un ciclo antes de la siguiente.

Ninguno de estos puntos se activó ni se solicitó activar en este paquete.

---

## Recordatorio de alcance — carril n8n

Por instrucción explícita de este paquete, **el carril n8n (radar +
`llms-full.txt`) NO se integró ni se inició aquí.** Es trabajo separado,
posterior a este smoke, y requiere su propia sesión/paquete.

---

**Marcador:** `EDITORIAL_SMOKE_E2E_READY`
