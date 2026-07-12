# Verificación PR #523 — P3 editorial + saneamiento b0004

Fecha: `2026-07-12`

Repo: `Umbral-Bot/umbral-agent-stack`

PR: [#523 — DO NOT MERGE · P3 editorial gates + repo sanitation](https://github.com/Umbral-Bot/umbral-agent-stack/pull/523)

Rama: `codex/p3-editorial-sanitize-b0004`

Base observada: `origin/main` @ `29897de3c3047bb84c5d0d0d533d32fa3b41d15e`

HEAD funcional verificado: `27608c8b50b734713af252f505cfd61ae6349eed`

## Alcance y guardrails

Verificación acotada al PR #523. No se re-auditaron F0–F4 ni Granola VM. No se hizo merge, deploy, HTTP a LinkedIn ni writes a Notion. Las pruebas se ejecutaron sin credenciales de LinkedIn/Notion y con todos los accesos externos mockeados.

## 1. Preflight Git y PR

Se ejecutó `git fetch origin main codex/p3-editorial-sanitize-b0004 --prune` antes de verificar.

| Comprobación | Resultado |
|---|---|
| Rama local | `codex/p3-editorial-sanitize-b0004` |
| `HEAD` local | `27608c8b50b734713af252f505cfd61ae6349eed` |
| Rama remota | `origin/codex/p3-editorial-sanitize-b0004` @ `27608c8b50b734713af252f505cfd61ae6349eed` |
| Head declarado por PR #523 | `27608c8b50b734713af252f505cfd61ae6349eed` |
| Estado PR | `OPEN`, `draft=true`, `mergeStateStatus=CLEAN` |
| Checks GitHub observados | Python 3.11 `SUCCESS`; Python 3.12 `SUCCESS` |
| Worktree antes del informe | limpio |
| Higiene del diff | `git diff --check origin/main...HEAD` limpio |

El commit que incorpore este informe solo añade documentación; el SHA anterior identifica exactamente el contenido funcional sometido a pruebas y revisión manual.

## 2. Tests focalizados

Se cubrieron S9c, publish guards y flags, `editorial_publish`, gates visuales y Stage 6:

```text
tests/discovery/test_stage9c_linkedin_publish.py
tests/discovery/test_stage9c_dry_run.py
tests/discovery/test_stage9c_idempotency.py
tests/discovery/test_publish_guard_flags_integration.py
tests/discovery/test_publish_guard.py
tests/discovery/test_publish_guard_publication_hash_integration.py
tests/lib/test_publish_flags.py
tests/test_editorial_publish.py
tests/test_editorial_function_shared.py
tests/discovery/test_stage6_dispatcher.py
tests/discovery/test_stage6_llm_combinator.py
```

Ejecución con `WORKER_TOKEN=test`, `PYTHONDONTWRITEBYTECODE=1`, sin variables de publicación/LinkedIn/Notion y con `pytest -q -rs -p no:cacheprovider`:

```text
212 passed / 0 failed / 0 skipped
```

Tiempo reportado por pytest: `7.36s`.

## 3. Revisión manual del diff

| Control | Estado | Evidencia |
|---|---|---|
| A1 — PublishFlags en S9c | **OK** | `PublishFlags` se importa en `scripts/discovery/stage9c_linkedin_publish.py:43`; `PublishFlags.from_env()` se construye en `:371` y se entrega como `flags=flags` a `assert_can_publish()` en `:372-374`, antes del POST en `:405-407`. El test `tests/discovery/test_stage9c_linkedin_publish.py:234-280` verifica que, sin `PUBLISH_ENABLED`, retorna `publish_disabled` antes de gates editoriales y sin HTTP. El contrato legacy sin flags permanece cubierto en `tests/discovery/test_publish_guard_flags_integration.py:167-180`. |
| A2 — write-back blog | **OK** | La firma real está en `worker/notion_client.py:1119-1124`. La llamada usa `page_id_or_url=notion_page_id` en `worker/tasks/editorial_publish.py:404-407`. El test usa `autospec=True` contra la función real y valida el kwarg exacto en `tests/test_editorial_publish.py:356-379`; el antiguo `page_id=` habría producido `TypeError`. |
| A3 — visual fail-closed antes de HTTP | **OK** | La evaluación del schema visual está en `worker/tasks/editorial_publish.py:152-238`. Un gate v2 incompleto retorna `visual_asset_not_ready` en `:611-624`; `_post_to_function()` ocurre recién en `:659`. Los casos Pendiente/Regenerar/sin selección, Alt sin URL, estado no seleccionado y mismatch canónico están cubiertos sin red en `tests/test_editorial_publish.py:472-607`, con `urlopen.assert_not_called()`. |
| B1 — Stage 6 archivado recuperable | **OK** | Existen `scripts/discovery/_archived/stage6_aec_combine.py` y `scripts/discovery/_archived/stage6_generate_variants.py`. Git los reconoce como renames, no deletes (`R088` y `R096`). `scripts/discovery/_archived/README.md:26-44` inventaría ambos y documenta recuperación mediante `git mv`, actualización de referencias y repetición de tests. |

Precisión A3 no bloqueante: el fail-closed descrito aplica a páginas que exponen `Selección imagen`. Si esa propiedad no existe, `worker/tasks/editorial_publish.py:187-194` conserva deliberadamente el comportamiento legacy para páginas anteriores al schema v2. No se encontró ningún camino con gate v2 incompleto que alcance HTTP.

## 4. MP-D2 — propuesta para master-plan §7

MP-D2 queda **READY como propuesta, no ratificado**. El canónico propuesto es `scripts/discovery/stage6_llm_combinator.py`: es el único Stage 6 invocado por el cron operativo (`scripts/vps/discovery-publish-cron.sh:112`). No hay callers runtime de los dos legacy en `dispatcher/` o `worker/`; ambos permanecen versionados bajo `_archived/`. El estado actual ya figura como propuesta pendiente de firma en `docs/editorial-pipeline/master-plan.md:35,127`.

Texto propuesto de exactamente cinco líneas para §7; se entrega aquí y no implica commit directo a `main`:

```text
**MP-D2 — PROPUESTA b0004; NO RATIFICADA.**
Canónico propuesto: `scripts/discovery/stage6_llm_combinator.py`, único Stage 6 invocado por `scripts/vps/discovery-publish-cron.sh`.
Archivados: `stage6_aec_combine.py` (stub) y `stage6_generate_variants.py` (skeleton), ambos versionados bajo `scripts/discovery/_archived/`.
Recuperación: restaurar solo el elegido con `git mv`, actualizar referencias y ejecutar los tests focalizados de Stage 6.
**Gate: NO MERGE** del PR #523 hasta ratificación explícita de David; mantenerlo draft/do-not-merge.
```

## 5. Hallazgos y recomendación

- Bloqueos P0/P1 encontrados en esta verificación: **0**.
- MP-D2: técnicamente preparado, pendiente de decisión humana.
- Recomendación: conservar PR #523 como draft/do-not-merge hasta review y ratificación explícita de David.
- No se autoriza merge ni deploy desde este informe.

## Pregunta para David

¿Ratificás MP-D2 con `stage6_llm_combinator.py` como canónico y los otros dos Stage 6 conservados bajo `_archived/` para habilitar una decisión posterior de merge?

## Veredicto

`PR523_VERIFY_OK | tests=212_passed_0_failed_0_skipped | mpd2_proposal=READY | merge_recommendation=DRAFT_UNTIL_DAVID`
