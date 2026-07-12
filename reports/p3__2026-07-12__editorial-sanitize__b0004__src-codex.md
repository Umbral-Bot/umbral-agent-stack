# P3 editorial + saneamiento repo — b0004

Fecha: 2026-07-12

Repo: `Umbral-Bot/umbral-agent-stack`

Base: `29897de3c3047bb84c5d0d0d533d32fa3b41d15e` (`origin/main`)

Branch: `codex/p3-editorial-sanitize-b0004`

PR: [#523 — DO NOT MERGE · P3 editorial gates + repo sanitation](https://github.com/Umbral-Bot/umbral-agent-stack/pull/523) — **draft** hasta review de David.

## Alcance y guardrails

Se consumieron, sin re-auditar, `f3__2026-07-10__stack-multiagente-matriz__b0003__src-sonnet.md` y `codex__2026-07-10__repos-editorial-worker__b0003__src-codex.md`. El trabajo se hizo en un worktree aislado porque el checkout principal contenía cambios ajenos.

- Sin deploy ni cambios de runtime.
- Sin HTTP real a LinkedIn; todos los paths de red afectados están mockeados.
- Sin writes a Notion ni modificación de gates humanos en tests.
- Sin marcar `aprobado_contenido` ni `autorizar_publicacion` en una superficie viva.
- Sin dependencias nuevas ni cambios en `pyproject.toml`/requirements.
- Archive-before-delete aplicado a S6; no se eliminó historia recuperable.

## Resultado A1–A4 + B1–B6

| Bloque | Resultado | Evidencia / decisión |
|---|---|---|
| A1 — S9c PublishFlags | **WIRED** | `stage9c_linkedin_publish.py` construye `PublishFlags.from_env()` y pasa `flags=flags`. Con env fail-closed se emite un único `publish_guard.runtime_block` antes de gates y sin llamar `post_ugc`. El único call-site runtime de `assert_can_publish` es S9c; el contrato legacy sin flags sigue cubierto y verde. |
| A2 — write-back blog | **FIXED** | `page_id=` cambió a `page_id_or_url=`. El test usa `autospec=True` sobre la función real y habría fallado con el kwarg anterior. |
| A3 — visual resolver | **IMPL** | Schema exacto confirmado en `notion-publicaciones-v2-visual-gates-schema.md`. `resolve_visual_asset_urls()` soporta Alt 1–5, selección múltiple determinista y degradación `{}`. La vía Notion bloquea antes de HTTP selecciones vacías/Pendiente/Regenerar, Alt sin URL, estado no seleccionado y mismatch con `Visual asset URL`; `Sin imagen` queda como elección explícita. Páginas sin la propiedad v2 conservan compatibilidad legacy. |
| A4 — D-13 `document.*` | **VERIFICADO** | Los tres handlers existen, están registrados, tienen tests y referencias estáticas; tabla abajo. |
| B1 — S6 triplicado | **DOSSIER + ARCHIVE_PROP** | `stage6_llm_combinator.py` es el único invocado por `discovery-publish-cron.sh`. Stub y skeleton fueron movidos a `_archived/`, con README de recuperación y referencias activas actualizadas. MP-D2 queda **PROPUESTA NO RATIFICADA** en master-plan §7; no mergear sin firma David. |
| B2 — handlers sin invocador | **INVENTARIED** | Se consumió el set 117/108/9. El noveno omitido en b0003 se reconstruyó como `google_drive.upload_presentation`. No se deprecó ninguno: ausencia de invocador estático no prueba cero uso externo. |
| B3 — kwargs / except amplios | **DONE** | 18 call-sites de `update_page_properties`: 17 correctos y 1 roto (A2), ahora 18 correctos. Análisis AST de 441 llamadas a helpers de `notion_client.py`: 0 kwargs incompatibles post-fix. Excepciones amplias clasificadas abajo. |
| B4 — SQLite spines | **DOCUMENTED / NO REDESIGN** | `signals_raw/signals_verified` y `discovered_items` comparten archivo por defecto pero no tienen adapter, `INSERT ... SELECT`, dispatcher ni cron que los conecte. Documentado en `sqlite-policy.md`; no hay wiring mecánico seguro. |
| B5 — higiene | **DONE** | `.gitignore` ya cubre logs, `.cache/`, `.tmp` vía `*.tmp`, outputs generados y `reports/*.json`. Cero `_payload-capture`/ops dumps trackeados; el dump local observado está ignorado. Sin deps nuevas. Tests afectados verdes. |
| B6 — Granola | **DOCUMENTED** | `granola_full_gap_audit.py` quedó marcado `DEPRECATED: LEGACY CACHE-V6 AUDIT`; no debe usarse como intake. La migración a `granola.db`/API queda fuera de este PR, como pidió el dispatch. |

## A4 — handlers documentales (solo lectura)

| Handler | Existe / registrado | Test | Referencia estática | Veredicto |
|---|---:|---:|---:|---|
| `document.create_presentation` | sí / sí | `tests/test_document_generator.py` | bridge OpenClaw; imports en `google_drive.py` y `pit_build_outcome_deck.py` | KEEP |
| `document.create_word` | sí / sí | `tests/test_document_generator.py` | bridge OpenClaw + skill `document-generation` | KEEP |
| `document.create_pdf` | sí / sí | `tests/test_document_generator.py` | bridge OpenClaw + skill `document-generation` | KEEP |

Detalle canónico: `docs/ops/worker-handler-inventory.md`.

## B1 — dossier S5 → S7

1. S5 rankea y escribe columnas de ranking en `state.sqlite.discovered_items`, pero no tiene invocador en dispatcher/cron vigente.
2. El cron operativo ejecuta S4 y luego `stage6_llm_combinator.py`; S6 lee rankings o cae a promovidos recientes y persiste drafts en `proposals`.
3. El mismo cron deja S7 manual; `stage7_publish_drafts.py` lee `proposals` y crea drafts en `📰 Publicaciones`.
4. Dispatcher/Worker no despachan estáticamente S5/S6/S7. No existe una cadena automática S5→S6→S7.

Archivos recuperables:

| Archivo archivado | Estado previo | Recuperación |
|---|---|---|
| `_archived/stage6_aec_combine.py` | stub con `NotImplementedError` | README exige decisión MP-D2, `git mv`, actualización de refs y tests. |
| `_archived/stage6_generate_variants.py` | skeleton multi-plataforma; stubs fuera de LinkedIn | Conservado importable y con recovery test; no es runtime canónico. |

## B2 — nueve handlers registrados sin invocador estático

| Handler | Registrado | Invocador runtime en repo | Veredicto |
|---|---:|---:|---|
| `web.publish_editorial_post` | sí | no; entrada manual/externa documentada | KEEP |
| `web.unpublish_editorial_post` | sí | no; rollback real documentado | KEEP |
| `client.register` | sí | no; API admin + policy/tests | DOCUMENT |
| `client.revoke` | sí | no; API admin + policy/tests | DOCUMENT |
| `client.rotate_key` | sí | no; API admin + policy/tests | DOCUMENT |
| `client.list` | sí | no; API admin + policy/tests | DOCUMENT |
| `client.usage` | sí | no; API admin + policy/tests | DOCUMENT |
| `client.get` | sí | no; API admin + policy/tests | DOCUMENT |
| `google_drive.upload_presentation` | sí | no; wrapper con tests/docs; PIT usa create+upload separados | DOCUMENT |

No hubo veredicto DEPRECATE; por tanto no corresponde comentario de deprecación en `worker/tasks/__init__.py` ni eliminación de handlers sin evidencia de runtime.

## B3 — barrido de contratos Notion y excepciones amplias

### `update_page_properties`

| Grupo | Call-sites | Resultado |
|---|---:|---|
| `worker/tasks/notion.py` | 4 | OK |
| `worker/tasks/granola.py` | 7 | OK |
| `scripts/notion_curate_ops_vps.py` | 5 | OK |
| `scripts/ensure_granola_notion_identity_columns.py` | 1 | OK |
| `worker/tasks/editorial_publish.py` | 1 | **roto antes / FIXED ahora** |

Barrido ampliado por AST: 441 llamadas a funciones de `worker/notion_client.py`; `mismatches=0` después del fix.

### `except Exception`

| Severidad | Path | Resultado |
|---|---|---|
| P1 resuelto | `editorial_publish.py:_maybe_write_back` | El catch best-effort ocultaba operacionalmente el `TypeError` del kwarg. Se conserva best-effort, pero el contrato queda protegido con autospec real. |
| P1 resuelto | visual publish Notion | La revisión detectó fallback a hero legacy con gate visual incompleto. Ahora bloquea con `visual_asset_not_ready` antes de HTTP. |
| P2 abierto | `scripts/vm/granola_watcher.py:293` | Si mover a `processed/` falla, loguea pero retorna éxito; puede reintentar/reprocesar. No se cambia por la restricción B6 “solo documentar”. |
| INFO | 23 catches Granola-related (20 en archivos `*granola*.py`, 3 en ramas Granola del poller) | Todos loguean, aplican backoff o devuelven error estructurado; no se confirmó otro kwarg incompatible ni `TypeError` silencioso. |
| INFO | 3 catches S9c | Notificación, error HTTP y registro dedup son best-effort pero quedan logueados/retornados; ninguno habilita publicación. |

## Tests

### Suite afectada (veredicto del paquete)

Comando focalizado sobre A1/A2/A3, guards, S6 archive/recovery y handlers documentales/Drive:

```text
247 passed / 0 failed / 1 skipped
```

El skip es `test_document_generator.py:230` porque WeasyPrint no tiene sus system libs en este Windows; no afecta los paths cambiados. No hubo HTTP real ni credenciales externas en el proceso.

### Suite completa del repo

```text
4034 passed / 1 failed / 14 skipped / 2 xfailed / 31 setup errors
```

Los resultados no verdes son preexistentes y se reprodujeron en el checkout base `origin/main`:

- 31 setup errors: `tests/mission_control/test_pit_preview.py` requiere privilegio de symlink en Windows (`WinError 1314`).
- 1 fail: `tests/test_pit_collect_tokens.py` compara `/` contra `\` en Windows.
- Reproducción mínima sobre base: `1 failed / 1 error` con esos dos tests.

## PRs

| PR | Estado | Merge gate |
|---|---|---|
| [#523](https://github.com/Umbral-Bot/umbral-agent-stack/pull/523) | **draft** / `do-not-merge` | review David + firma MP-D2 antes del archivado S6 |

## Veredicto

`PAQUETE_OK | s9c=WIRED | writeback=FIXED | visual=IMPL | s6=DOSSIER+ARCHIVE_PROP | handlers=INVENTARIED | sanitize=B1-B6_DONE`

El paquete está listo técnicamente, pero **no autorizado para merge**: el PR debe permanecer draft/`do-not-merge` y MP-D2 sigue sin ratificación humana.

## Pregunta 1 para David

¿Los fixes P0/P1 pueden mergearse directo a `main` con tests afectados verdes, o se mantiene el PR draft `do-not-merge` hasta tu review? Estado aplicado por defecto en b0004: **draft / no merge**.
