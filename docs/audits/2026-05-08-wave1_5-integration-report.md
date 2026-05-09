# Wave 1.5 — Integration Report

> **Branch:** `wave1.5-integration` (local + origin) · **Status:** DRAFT · DO NOT MERGE
> **Operator:** Copilot-VPS · **Date:** 2026-05-08
> **Source task:** [`.agents/tasks/2026-05-08-001-copilot-vps-wave1_5-integration.md`](../../.agents/tasks/2026-05-08-001-copilot-vps-wave1_5-integration.md)

## 1. Resumen ejecutivo

Las 6 PRs draft de Wave 1 (#394 H1, #395 H5, #396 H4, #397 H2, #398 H3, #399 H6)
fueron integradas en una branch única `wave1.5-integration` siguiendo el orden
estricto **H1 → H4 → H2 → H3 → smoke → H5 → H6** dictado por la review externa.
Cinco contratos cruzados (hashes, SQLite, Notion helpers, Stage 7.5 freeze,
publish-guard imports) quedaron documentados o resueltos sin tocar código de
features. Smoke S0→S2 read-only confirma 0 writes a Notion y 0 requests a
LinkedIn. Detectada UNA falla real de aislamiento de tests post-integración
(`test_stage9c_idempotency.py::test_successful_post_calls_register_published`)
que NO fue reescrita — se reporta como hallazgo de integración por antipattern
brief #9.

## 2. Orden de integración ejecutado

| Fase | Acción | Commit | Resultado |
|---|---|---|---|
| 0 | Branch `wave1.5-integration` desde main `8d118a8` | — | OK |
| 1 | merge H1 (#394) `copilot/docs-editorial-master-plan` | `31306b6` | sin conflictos |
| 2 | merge H4 (#396) `copilot/docs-notion-schema-gates` | `a79d23e` | conflicto en `notion-schema.md` resuelto (kept H4) |
| — | smoke `pytest tests/lib/` | — | 30 passed |
| 3 | merge H2 (#397) `copilot/feat-s0-s1-discovery` | `b03e2fc` | conflictos en `lib/__init__.py` y `stage1-discovery-spec.md` resueltos |
| — | smoke `pytest tests/discovery/test_stage0_load_referentes.py tests/discovery/test_stage1_*.py tests/discovery/test_stage0_stage1_extra.py tests/lib/` | — | **61 passed** |
| 4 | merge H3 (#398) `copilot/feat-s2-source-verification` | `780c9c4` | conflicto en `lib/__init__.py` resuelto |
| — | full suite `pytest tests/discovery/ tests/lib/` | — | **336 passed** |
| 5 | smoke S0→S2 read-only en SQLite efímero | — | ver §4 |
| 6–8 | nuevos docs `hash-contract.md`, `sqlite-policy.md`, `notion-helpers-policy.md` + `tests/discovery/test_hash_contract.py` | `3298a58` | 9 hash tests passed |
| 9 | merge H5 (#395) `copilot/docs-s6-s7-multiplatform-design` | `20ee96b` | conflicto en `lib/__init__.py` resuelto · 38 H5 tests passed · `import scripts.discovery.stage6_generate_variants` sin side-effects · Stage 7.5 freeze = 0 |
| 10 | merge H6 (#399) `copilot/feat-s10-publish-guard` | `9064c36` | sin conflictos · `publish_guard` resuelve `gates`/`dedup` reales · dry-run S10 (3 escenarios) verde · suite total: **402 passed / 1 failed** (ver §10) |
| 11 | master-plan §7 actualizado: D1=resuelto, D3=resuelto, D2/D4/D5=postponed Wave 2 | `978e056` | OK |
| 12 | verificación final | — | ver §8 |
| 13 | push branch + crear PR draft | — | ver §11 |

## 3. Conflictos cruzados — matriz

> **Convención del task brief:** "ChatGPT/equipo dice X" vs "Verificación VPS muestra Y" cuando difieren.

| # | Conflicto | Owner declarado | Repo dice | VPS muestra | Estado Wave 1.5 |
|---|---|---|---|---|---|
| 1 | H2↔H3 contrato `signals_raw` columna URL | review externa | H2 usa `url` + `canonical_url` (no `source_url`) | S2 (`stage2_verify_sources.py:419-425`) introspecta `PRAGMA table_info` y acepta ambos nombres → contrato funciona en branch integrada | **Resuelto en código (auto-detect)** |
| 2 | H4↔H3 `idempotency_key` ya existe en Notion | equipo | propuesta de crear propiedad nueva | audit Notion (`docs/audits/2026-05-08-notion-publicaciones-schema-audit.md`) confirma propiedad ya presente → propuesta cancelada | **Resuelto: no-op** |
| 3 | H5↔H4 `Copy Carrusel`/`Copy Video` propuestos | equipo | docs proponen DBs nuevas | 0 DBs creadas en este task; quedan como propuesta documentada | **Resuelto: PROPUESTO sin crear** |
| 4 | H6↔H3 `publish_guard` lazy-importa `dedup` | equipo | sí, usa `_load_module` con `importlib` + `sys.modules` lookup | en branch integrada, `gates` y `dedup` son reales y se resuelven directo (no hay try/except `ImportError`); el lazy import es **deferred resolution para tests**, no fallback | **Resuelto en estructura — ver §10** |
| 5 | Orden de merge inicial vs corregido | equipo + review externa | propuesta inicial: H1→H4→H3→H2→H5→H6 | review externa corrigió a: **H1→H4→H2→H3→H5→H6**; ejecutado en este orden | **Aplicado** |
| 6 | Dos capas de hash sin contrato (`signal_hash` H2 vs `content_hash`/`idempotency_key` H3) | review externa | sin doc cross-stage | Wave 1.5 produce [`docs/editorial-pipeline/hash-contract.md`](../editorial-pipeline/hash-contract.md) + 9 tests en `test_hash_contract.py` | **Resuelto (documentación + tests)** |
| 7 | Duplicación potencial clientes Notion | review externa | sospecha | live: `notion_publicaciones.py` no hace HTTP (pura parsing); `notion_read.py` único módulo con cliente | **Falsa alarma — ver [`docs/editorial-pipeline/notion-helpers-policy.md`](../editorial-pipeline/notion-helpers-policy.md)** |
| 8 | Ambigüedad `Canal` vs `Tipo de contenido`/`Formato` (carrusel/video) | review externa | docs vagos | `scripts/discovery/lib/variants.py` define `PLATFORMS = ("linkedin","x","blog","newsletter","carousel","video")` → carrusel/video son tratados como plataformas, no formatos | **NO cumplido en Wave 1.5 — deuda explícita Wave 2.** Brief original pedía confirmar carrusel/video como `formato`, no como `Canal`. Implementación H5 dejó ambos como plataformas. No se corrige en este fix porque rompería 38 tests H5; corrección semántica + refactor de tests es scope Wave 2 (ver §12 backlog item #1). |
| 9 | Dashboard `stageX_pipeline_dashboard.py` no leería eventos `publish_guard.block/pass` | review externa | sospecha | NO verificado en este task (fuera de scope Wave 1.5; dashboard es Stage X, no parte de las 6 PRs) | **Postponed Wave 2** |
| 10 | Stage 7.5 FROZEN pero H5 importa `stage7_5_copy_writer` para delegación | review externa | riesgo de side-effects al importar | `import scripts.discovery.stage6_generate_variants` ejecutado en CLI sin error y sin escribir nada → import limpio | **Resuelto (verificado)** |

## 4. Smoke S0→S2 — referencia

Detalle completo y output literal en
[`reports/2026-05-08-wave1_5-smoke.md`](../../reports/2026-05-08-wave1_5-smoke.md).

| Métrica | Valor |
|---|---|
| `referentes_snapshot` | 70 (16 web, 11 rss, 11 youtube, 32 linkedin) |
| `signals_raw` total | 116 (50 rss ok, 15 web ok, 32 linkedin_skip, 11 youtube out_of_scope, resto errores) |
| `signals_verified` | 30 (4 ok, 7 paywall, 16 blocked, 3 404) |
| Notion writes | **0** |
| LinkedIn HTTP requests | **0** |

Migraciones 0001+0002 verificadas idempotentes (re-run con exit=0 sobre DB no-vacía).

## 5. Hash contract — resumen

Ver [`docs/editorial-pipeline/hash-contract.md`](../editorial-pipeline/hash-contract.md).

| Hash | Stage | Inputs | Estabilidad |
|---|---|---|---|
| `dedup_hash` (alias `signal_hash`) | S1 (H2) | `sha256(canonical_url + "\n" + (published_at or ""))` | Determinístico; date-independent en None/"" — verificado en `test_hash_contract.py` |
| `content_hash` | S2 (H3) | `sha256(canonical_url + "\n" + normalize(title) + "\n" + normalize(excerpt))` | Date-independent; sensible a edits |
| `idempotency_key` | S2 (H3) | `sha256(canonical_url + "\n" + content_hash)` | Cambia sólo si `content_hash` cambia |

**Edge case `published_at` ausente:** `sha256(url + "\n")` (estable). UNIQUE
constraint deduplica re-discoveries. Sin observabilidad para el caso —
**postponed Wave 2**, no se implementa fix en 1.5 (antipattern brief #8).

## 6. SQLite policy — decisiones

Ver [`docs/editorial-pipeline/sqlite-policy.md`](../editorial-pipeline/sqlite-policy.md).

- `journal_mode = delete` (default). Mantener en Wave 1.5 (single-writer cron). Wave 2 revisar si llega S10b paralelo.
- `busy_timeout = 0`. **Gap.** Postponed Wave 2 (config `PRAGMA busy_timeout=5000` por connect).
- Cada stage abre conexión propia y commitea al final (verificado leyendo S0/S1/S2 + `lib/dedup`).
- Migraciones idempotentes via `IF NOT EXISTS` — verificadas.

## 7. Notion helpers policy — decisión

Ver [`docs/editorial-pipeline/notion-helpers-policy.md`](../editorial-pipeline/notion-helpers-policy.md).

**Mantener split por dominio.** `notion_read.py` (Referentes, único con HTTP)
y `notion_publicaciones.py` (Publicaciones, pure parsing) NO se refactorizan
en Wave 1.5. Revisitar cuando Hilo 6 implemente el writer real S10
(`PATCH /v1/pages/{id}`).

## 8. Stage 7.5 freeze check — output literal

```
$ git diff main wave1.5-integration -- 'scripts/discovery/stage7_5_*' | wc -l
0
```

```
$ grep -r "CAND-00[234]" tests/discovery/fixtures/ ; echo exit=$?
exit=1
```

(grep exit=1 = sin matches, fixtures CAND-002/003/004 confirmadamente
ausentes, antipattern brief #10.)

## 9. Dry-run S10 — 3 escenarios

Detalle en [`reports/2026-05-08-wave1_5-stage10-dryrun.md`](../../reports/2026-05-08-wave1_5-stage10-dryrun.md).

| # | Escenario | Test | Resultado |
|---|---|---|---|
| 1 | SYN-pass (todos los gates verdes) | `test_dry_run_all_gates_ok_would_publish_true` | **PASSED**, `would_publish=true`, 0 POST |
| 2 | SYN-blocked-by-gate (`aprobado_contenido=False`) | `test_dry_run_gate_failing_would_publish_false` | **PASSED**, `would_publish=false`, `reasons=[aprobado_contenido_missing]`, 0 POST |
| 3 | SYN-blocked-by-dup (`content_hash` ya en `published_history`) | `test_dry_run_duplicate_content_hash_blocks` | **PASSED**, `would_publish=false`, `reasons=[contenido_duplicado]`, 0 POST |

`test_no_hardcoded_linkedin_post_urls`: PASSED. 0 hits de `httpx.Client` o
`POST.*linkedin.com` en estos 4 tests.

**Nota:** el CLI real (`stage9c_linkedin_publish`) no expone
`--proposal-id` como sugería el brief; los 3 escenarios viven en el harness
de tests con SQLite seed + Notion fixtures sintéticas. Cobertura
funcionalmente equivalente.

## 10. Test results — full suite tras integración

```
$ PYTHONPATH=. python -m pytest tests/discovery/ tests/lib/ -q
402 passed, 1 failed in 26.23s
```

**402 passed** incluye los 9 tests nuevos `test_hash_contract.py`.

**1 failed:** `tests/discovery/test_stage9c_idempotency.py::test_successful_post_calls_register_published`.

| Aspecto | Hallazgo |
|---|---|
| ¿Pasa aislado? | **Sí** (`pytest tests/discovery/test_stage9c_idempotency.py` → 2 passed). |
| ¿Pasa con `test_publish_guard.py + test_stage9c_idempotency.py`? | Sí. |
| ¿Falla con la suite completa `tests/discovery/`? | Sí. |
| Causa raíz probable | `publish_guard.assert_can_publish` resuelve `dedup` vía `from scripts.discovery.lib import dedup as _dedup` (en `stage9c_linkedin_publish.py:407`). Algún test anterior importa el `scripts.discovery.lib.dedup` real, lo cual setea `scripts.discovery.lib.dedup` como atributo del paquete padre. Posteriormente `monkeypatch.setitem(sys.modules, ...)` reemplaza la entrada en `sys.modules` pero NO el atributo del paquete padre, así que `from … import dedup` recupera el módulo real (no el fake), y el fake `register_published` (que registra en `register_calls`) nunca se invoca. |
| Acción | **No se reescribió el test** (antipattern brief #9). Reportado como hallazgo real de integración. Recomendación Wave 2: o bien (a) cambiar `publish_guard._load_module` para hacer `importlib.import_module` directo siempre (saltando atributo del paquete), o bien (b) cambiar el callsite en `stage9c_linkedin_publish.py:407` por `import scripts.discovery.lib.dedup as _dedup; _dedup = sys.modules['scripts.discovery.lib.dedup']`, o (c) refactorizar el test para inyectar `dedup` por parámetro en `publish_one`. |
| ¿Bloquea Wave 1.5? | **No.** El runtime real (sin monkeypatch) usa siempre el módulo real `scripts.discovery.lib.dedup` y `register_published` se ejecuta correctamente. Es un defecto de aislamiento de tests, no de producción. |

**Verificación de `publish_guard` sin lazy fallback:**

```
$ grep -nE "try:|except.*Import|fallback|ImportError" scripts/discovery/lib/publish_guard.py
117:    try:        # OSError-only — ops_log write
```

→ NO hay `try/except ImportError` en `publish_guard.py`. El uso de
`importlib.import_module` con `sys.modules` lookup es **deferred resolution**
(diseñado para tests), no **fallback** (que requeriría `try/except ImportError`).
Criterio de aceptación interpretado como cumplido.

**Verificación de imports reales:**

```
$ python -c "from scripts.discovery.lib import publish_guard, gates, dedup; print(gates.__file__, dedup.__file__)"
/home/rick/umbral-agent-stack/scripts/discovery/lib/gates.py /home/rick/umbral-agent-stack/scripts/discovery/lib/dedup.py
```

## 10bis. Wave 1.5 Fix (2026-05-09)

Correcciones aplicadas sobre `wave1.5-integration` tras la review externa
que diagnosticó tres blockers pre-merge. Decisiones técnicas se documentan
en `.agents/tasks/2026-05-09-001-copilot-vps-wave1_5-fix.md`.

| Item | Estado pre-fix | Estado post-fix | Commit |
|---|---|---|---|
| `test_stage9c_idempotency::test_successful_post_calls_register_published` | 1 failed en suite completa | **PASSED** en suite completa | `0e111bd` |
| Suite total `tests/discovery/` + `tests/lib/` | 402 passed / 1 failed | **403 passed / 0 failed** | `0e111bd` |
| `content_hash` documentado como "contenido final" (engañoso) | sí | corregido — alias `source_content_hash` + contrato `publication_content_hash` diferido explícito (Wave 2) | `0f633e6` |
| Carrusel/video declarado "Postponed Wave 2" sin admitir incumplimiento | sí | **corregido — declarado NO cumplido + carry-over backlog top** (este reporte §3#8 + §12#1) | _commit que contiene este §10bis_ |

Ver también: [`docs/audits/2026-05-09-wave1_5-fix-report.md`](./2026-05-09-wave1_5-fix-report.md).

## 11. Recomendación final por PR

> **Estado post-Wave 1.5 Fix (2026-05-09):** suite verde (403 passed / 0 failed),
> hash contract corregido (alias `source_content_hash` + contrato
> `publication_content_hash` diferido explícito), carrusel/video documentado
> como deuda Wave 2 explícita. Ver §10bis para detalle pre/post fix.
> PR #400 listo para review final por David antes de quitar `do-not-merge`.

| PR | Branch | Recomendación | Razón |
|---|---|---|---|
| #394 H1 | `copilot/docs-editorial-master-plan` | **Reemplazar por wave1.5-integration** | El master-plan §7 fue actualizado en la branch de integración (D1/D3 resueltos). El stub `notion-schema.md` quedó obsoleto cuando se mergeó H4. |
| #396 H4 | `copilot/docs-notion-schema-gates` | **Reemplazar por wave1.5-integration** | Schema audit + gates + models quedaron consolidados con H2/H3/H6. Mergear H4 aislado dejaría libs huérfanas. |
| #397 H2 | `copilot/feat-s0-s1-discovery` | **Reemplazar por wave1.5-integration** | Conflictos en `lib/__init__.py` ya resueltos en la branch de integración. |
| #398 H3 | `copilot/feat-s2-source-verification` | **Reemplazar por wave1.5-integration** | Idem; depende de H2 + H4 mergeados. |
| #395 H5 | `copilot/docs-s6-s7-multiplatform-design` | **Reemplazar por wave1.5-integration** | Depende de H4 (`Variants` referenciados desde `lib`). |
| #399 H6 | `copilot/feat-s10-publish-guard` | **Reemplazar por wave1.5-integration**, con tarea Wave 2 para fix del aislamiento de tests (§10) | Funcionalmente correcto en runtime; defecto de tests documentado. |

**Acción consolidada recomendada para David:** revisar este PR de
`wave1.5-integration` en lugar de las 6 PRs originales; cerrar las 6 sin
mergear cuando se apruebe la integración.

## 12. Wave 2 backlog

1. **[CARRY-OVER WAVE 1.5]** Ambigüedad **Canal vs Formato** — separar
   `PLATFORMS = (linkedin, x, blog, newsletter)` de
   `FORMATS = (carousel, video, thread, post_largo, post_corto, ...)` en
   `scripts/discovery/lib/variants.py`. Refactor de los 38 tests H5 que
   asumen el shape actual. **Brief original Wave 1.5 lo pidió como
   criterio §7a; quedó NO cumplido.**
2. **[CARRY-OVER WAVE 1.5]** `publication_content_hash` separado de
   `source_content_hash` — definir, computar sobre el copy final post-S6/S7,
   persistir en `published_history`, migrar `register_published` para
   usarlo. **Brief original Wave 1.5 lo pidió como criterio §8c; quedó NO
   cumplido.** Hasta entonces, el guard provisional descrito en
   `hash-contract.md §1b` aplica y NO debe activarse publicación real.
3. **D2** — definir canónico de S6 (`stage6_aec_combine` vs `stage6_llm_combinator` vs `stage6_generate_variants` H5).
4. **D4** — naming "Etapa N" vs "Stage M" — migración doc + código.
5. **D5** — política S8 imagen (cuándo dispara, pre/post review).
6. Dashboard `stageX_pipeline_dashboard.py` debe consumir eventos `publish_guard.pass/block` y conteos discovery/verification.
7. Fix de aislamiento del test `test_stage9c_idempotency.py::test_successful_post_calls_register_published` (ver §10) — **resuelto en Wave 1.5 Fix vía opción (c), commit `0e111bd`**.
8. SQLite hardening: `PRAGMA busy_timeout=5000` por connect; runner de migraciones con `schema_migrations` table.
9. Observabilidad para `signals_raw.published_at IS NULL` (gap mencionado en hash-contract.md §3 / sqlite-policy.md §5).
10. Cuando Hilo 6 implemente writer real S10 (`PATCH /v1/pages/{id}`), considerar refactor de auth/retry compartido entre `notion_read.py` y `notion_publicaciones.py`.

---

**Las 6 PRs originales (#394–#399) permanecen draft + `do-not-merge`. NO
se mergea ninguna en este task.**
