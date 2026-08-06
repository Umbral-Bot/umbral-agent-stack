# P1.2 — Clasificación de las 32 huérfanas con merge-base (2026-08-06)

> **Pack:** PKG-UAS-P1-2-ORPHAN-32 · rama `claude/pkg-uas-p1-2-orphan-32-20260806` · base `d0fd5a92`
> **GO de David:** clasificar las 32 huérfanas con merge-base del acta [uas-p1-2-branch-wt-2026-08-06.md](uas-p1-2-branch-wt-2026-08-06.md)
> §4.4. **Cero `git push --delete` en este pack** — solo clasificación con diff citado.
> Las 58 huérfanas sin merge-base quedan fuera (necesitan cherry-pick puntual, no esto).

---

## 0. Resumen

| Etiqueta | # | Significado |
|---|---|---|
| **KILL** | 28 | Sin valor único vs `main` — contenido ya absorbido (mismo o evolucionado), residuo de torneo trivial, o log operativo superado por estado posterior en `main` |
| **RESCUE** | 1 | Contenido único real, de bajo riesgo, con destino claro — recomendado traer a `main` |
| **KEEP** | 3 | Ambiguo, grande, o de valor incierto — queda en origin hasta decisión humana explícita |
| **Total** | **32** | |

Re-verificación previa a clasificar: las 32 ramas existen en origin, las 32 tienen merge-base con
`origin/main` (`git merge-base` no falló en ninguna), y ninguna tiene PR mergeado ni open — se
recruzaron contra `gh pr list --state merged` + `--state open` (600 límite) en este pack, no se
confió en el acta anterior.

---

## 1. Metodología por fila

Para cada rama: `git log origin/main..origin/<rama>` (hasta 5 commits), `git rev-list --left-right
--count`, `git diff --stat origin/main...origin/<rama>`, y luego — la parte que no estaba en el acta
anterior — **verificación de si los paths tocados ya existen en `origin/main`** vía `git ls-tree` y,
cuando había duda real, `git diff <path>` puntual entre `main` y la rama para ver si el contenido es
idéntico, superado (main más evolucionado), o genuinamente ausente.

---

## 2. Tabla completa

> **Nota de exactitud (post-verificación independiente):** la columna `ahead/behind` se calculó en un
> punto de esta sesión y `main` avanzó 2 commits después (los PR #588/#589 mergeando en paralelo);
> el `behind` de ~17 filas quedó desactualizado en exactamente 2 (p. ej. una fila muestra `1/349`
> cuando el valor real pasó a ser `1/351`). **No afecta ningún veredicto** — cada etiqueta se decidió
> con el diffstat de contenido y la verificación puntual de paths citada en "Evidencia", no con el
> conteo ahead/behind. Re-computar la columna para las 32 quedaría obsoleto de nuevo en el próximo
> commit a `main`; no se hizo por no ser el dato que sostiene la clasificación.

| Rama | Etiqueta | ahead/behind | Diff | Evidencia | Paths clave |
|---|---|---|---|---|---|
| `codex/cand-prod001-stage2` | **KILL** | 2/165 | 3 files, +770 | `main` tiene `docs/ops/cand-prod001-decision-brief.md` (mismo candidato CAND-001, mismo backfill 2026-06-07) — el payload/intake/benchmark crudo de esta rama es la data de trabajo detrás de esa decisión ya cerrada | `docs/ops/cand-prod001-{payload,source-intake}.md`, `.../variants-benchmark-*` |
| `codex/docs-pit-v2-contract` | **KEEP** | 1/138 | 5 files, +893/−2 | Ninguno de `pit-broker-contract.md`, `pit-tournament-v2-contract.md`, `pit-mega-diagnostic-*-summary.md` existe en `main`. Frente PIT está "ARCHIVAR" por gobernanza (inventario §1 A.2), pero el contenido es real y sustancial — no auto-KILL | `docs/ops/pit-broker-contract.md`, `pit-tournament-v2-contract.md` |
| `coord-ag-2a/build-push-aeco-source-crawler` | **KILL** | 1/306 | 1 file, +252 | Log de un build+push puntual; la infra real (`infra/azure/modules/aeco-source-crawler-job.bicep`, `infra/docker/aeco-source-crawler/`, task `048-o16-2-aeco-source-crawler.md`) ya vive en `main`, evolucionada | `.agents/tasks/...-coord-ag-2a-build-push-aeco-source-crawler-pinned.md` |
| `copilot-vps/052-aeco-kb-build-blocked-pat-scope` | **KILL** | 1/348 | 1 file, +34/−2 | Mismo task-log que `main` tiene, pero `main` está en un estado **posterior** (status `in_progress`, "PUSH COMPLETO 6/6", menciona PR #379) — esta rama es un snapshot intermedio ya superado | `.agents/tasks/2026-05-08-052-...-ghcr.md` |
| `copilot-vps/052-aeco-kb-pushed-visibility-manual` | **KILL** | 1/347 | 1 file, +42/−2 | Mismo archivo, mismo motivo — `main` está más adelante en el tiempo que esta rama | idem |
| `copilot-vps/recover-post-force-push-2026-05-06` | **KILL** | 1/507 | 27 files, +4338/−73 | `scripts/discovery/stage2_ingest.py`, `stage3_promote.py` y sus tests ya existen en `main` (verificado por ls-tree) | `scripts/discovery/stage{2,3}_*.py` |
| `copilot-vps/stage4-013e-execution-2026-05-07` | **KILL** | 1/491 | 4 files, +1259 | `scripts/discovery/stage4_push_notion.py` + test ya existen en `main` | `scripts/discovery/stage4_push_notion.py` |
| `copilot/burn-q2-o7-o9-delegates` | **KILL** | 1/485 | 3 files, +431 | Los 3 runbooks/task (`runbook-anthropic-telemetry-off.md`, `runbook-copilot-cli-via-ssh-from-tarro.md`, task `014-...-spike-openclaw-subagents-tournament.md`) ya existen en `main` | `runbooks/runbook-{anthropic-telemetry-off,copilot-cli-via-ssh-from-tarro}.md` |
| `copilot/docs-editorial-master-plan` | **KILL** | 1/312 | 6 files, +405 | `docs/editorial-pipeline/master-plan.md` existe en `main` y está **más evolucionado** (agrega aclaración P0 del norte 2026-07-22, referencia a `production-flow-v2`); diff puntual confirma `main` es superset | `docs/editorial-pipeline/master-plan.md` |
| `copilot/docs-notion-schema-gates` | **KILL** | 2/312 | 13 files, +1692 | `scripts/discovery/lib/gates.py` — **diff 0 líneas** entre `main` y esta rama, absorbido idéntico | `scripts/discovery/lib/gates.py`, `notion_publicaciones.py` |
| `copilot/docs-s6-s7-multiplatform-design` | **KILL** | 1/312 | 9 files, +1300 | `docs/editorial-pipeline/stage6-multiplatform-spec.md`, `scripts/discovery/lib/variants.py`, `stage6_llm_combinator.py` todos en `main`, con `stage6_aec_combine.py`/`stage6_generate_variants.py` ya movidos a `_archived/` — absorbido y evolucionado | `docs/editorial-pipeline/stage6-multiplatform-spec.md` |
| `copilot/feat-o16-2-047-gap-closure` | **KILL** | 2/295 | 3 files, +514/−2 | `param deployPdfParser bool = false` existe literal en `main:infra/azure/aeco-kb-pipeline.bicep`; `tests/test_pdf_parser.py` mismo largo (250 líneas) en ambos | `infra/azure/aeco-kb-pipeline.bicep` |
| `copilot/feat-o16-infra-base` | **KILL** | 1/496 | 15 files, +1161 | `infra/azure/*.bicep` existe en `main`, reorganizado bajo `infra/azure/modules/`; `docs/runbooks/azure-off-sponsorship-2026-07-30.md` presente | `infra/azure/main.bicep`, `docs/runbooks/azure-off-sponsorship-2026-07-30.md` |
| `copilot/feat-s0-s1-discovery` | **KILL** | 3/312 | 11 files, +1998 | `stage0_load_referentes.py` + `stage1_discover_signals.py` en `main`, diff puntual solo 15 líneas (evolución menor, no ausencia) | `scripts/discovery/stage{0,1}_*.py` |
| `copilot/feat-s10-publish-guard` | **KILL** | 3/312 | 23 files, +3433/−32 | `publish_guard.py` + `stage9c_linkedin_publish.py` en `main`, y **más chicos** que en la rama (main refactorizó/simplificó después) | `scripts/discovery/lib/publish_guard.py`, `stage9c_linkedin_publish.py` |
| `copilot/feat-s2-source-verification` | **KILL** | 2/312 | 9 files, +1532 | `stage2_verify_sources.py` presente en `main`, diff puntual 46 líneas (evolución, no ausencia) | `scripts/discovery/stage2_verify_sources.py` |
| `cursor/cand001-magnific-megaprompt` | **KILL** | 1/122 | 1 file, +114 | Familia `MEGAPROMPT-*` clasificada `ARCHIVAR` por el inventario norte ("prompts de un solo uso ya ejecutados") — este es exactamente ese patrón, el prompt ya cumplió su función | `docs/ops/MEGAPROMPT-rick-vps-cand001-magnific-3alts.txt` |
| `evidence/openclaw-e2e-cycle-001` | **KILL** | 2/275 | 6 files, +344 | `docs/audits/openclaw-e2e-cycle-001/` existe completo en `main`, **más** un archivo extra (`B2_ANTI_LOOP_DECISION.md`) que la rama no tiene — diff = solo 111 deletions (nada que rescatar) | `docs/audits/openclaw-e2e-cycle-001/*` |
| `rescue/coordinador-dirty-2026-07-13` | **KEEP** | 1/60 | 2 files, +413/−26 | `scripts/export-vscode-config.ps1` **no existe en `main`** (confirmado, genuino). El otro archivo (`editorial-publicaciones-human-review-contract.md`) se solapa de forma compleja con otras 2 ramas rescue del mismo doc — mezcla ambigua, no auto-KILL | `scripts/export-vscode-config.ps1` |
| `rescue/copilot-dirty-2026-07-13` | **RESCUE** | 1/60 | 2 files, +128/−1 | `docs/15-model-quota-policy.md` en `main` **no tiene** el bloque "Estado operativo vigente 2026-07-04 — post-MP1 `OPENCLAW_AZURE_ONLY=YES`"; el audit doc que referencia (`docs/audits/azure-foundry-capacity-openclaw-sync-2026-07-04.md`) **no existe en `main` en absoluto** — contenido real, ausente, bajo riesgo (2 docs) | `docs/15-model-quota-policy.md`, `docs/audits/azure-foundry-capacity-openclaw-sync-2026-07-04.md` |
| `rescue/copilot-vps/editorial-contract-paths-backup-2026-07` | **KILL** | 1/126 | 1 file, +2/−1 | Diff puntual muestra que `main` **ya tiene** la sección "Postcondiciones de publicación (Fila I=B)" que esta rama (2026-06-29) todavía no tenía — `main` es cronológicamente posterior | `docs/ops/editorial-publicaciones-human-review-contract.md` |
| `rescue/copilot-vps/editorial-contract-paths-canonical-2026-07` | **KILL** | 1/110 | 1 file, +3 | Mismo archivo, mismo motivo — predata la reescritura que ya está en `main` | idem |
| `rescue/copilot-vps/poller-hardening-2026-07` | **KILL** | 19/450 | 5 files, +149/−2 | `scripts/vps/check-notion-poller.sh` — **diff 0 líneas** vs `main`; el task doc (`.agents/tasks/2026-05-07-001-rick-delivery-notion-poller-healthcheck-hardening.md`) también existe en `main` | `scripts/vps/check-notion-poller.sh` |
| `rick-delivery/notion-poller-healthcheck-hardening` | **KILL** | 3/451 | 6 files, +81/−8 | Mismo `check-notion-poller.sh` con diff 0; `.env.example` en `main` es **mucho más grande** (evolucionado, 86 líneas de diferencia en la dirección de que main tiene más) | `scripts/vps/check-notion-poller.sh`, `.env.example` |
| `rick/stage7_5-multiformat` | **KEEP** | 7/336 | 14 files, +5491/−14 | `stage7_5_copy_writer.py` diverge de verdad: 583 líneas únicas de la rama (`FORMATS`, variantes blog/linkedin-share/linkedin-standalone) que `main` no tiene, y `main` tiene 410 líneas propias que la rama no tiene — es un **fork real**, no absorción. `main` fue en la dirección de un archivo por canal (`blog-copy-system.md`, `linkedin-copy-system.md`, `x-copy-system.md`), no la de "multi-formato con variantes". Contenido genuino, no auto-KILL | `scripts/discovery/stage7_5_copy_writer.py`, `prompts/rick/blog-system.md` (ausente en main) |
| `rick/stage7_5-voice-v2` | **KILL** | 4/334 | 14 files, +6268/−33 | `stage7_5_copy_writer.py` + `source_verifier.py` existen en `main`; diff puntual es **419 deletions / 41 insertions** yendo main→rama — `main` tiene 419 líneas que la rama no tiene, la rama solo 41 que main no tiene. `main` es el superset evolucionado | `scripts/discovery/{stage7_5_copy_writer,source_verifier}.py` |
| `rick/stage7_5-voice-v3` | **KILL** | 4/334 | 11 files, +5032/−32 | Mismo patrón que voice-v2 (410 deletions / 38 insertions main→rama) — iteración anterior ya superada | idem |
| `tournament/…-375-fa19920/lane-docs-explanatory` | **KILL** | 1/349 | 1 file, +2/−2 | Diff trivial de 2 líneas en `README.md` (espaciado de comentario) — residuo de lane de torneo | `README.md` |
| `tournament/…-440-462ef1c1/lane-backup-impl` | **KILL** | 1/212 | 16 files, +457 | `registry_backup_alert.py` existe en `main` bajo `scripts/registry/` (refactorizado desde `infra/`, contenido distinto pero **misma feature ya shipeada**) | `scripts/registry/registry_backup_alert.py` |
| `tournament/…-440-462ef1c1/lane-backup-qa` | **KILL** | 1/212 | 15 files, +453 | Lane duplicado del mismo ejercicio de torneo que `lane-backup-impl` — mismo motivo | idem |
| `tournament/…-445-d5f34a07/lane-sync-delivery` | **KILL** | 1/208 | 4 files, +736/−158 | `scripts/sync_skills_adapters.py` existe en `main`, diff puntual trivial (3 inserciones/12 deleciones) — absorbido | `scripts/sync_skills_adapters.py` |
| `tournament/…-d35-33863db/lane-openclaw-skill` | **KILL** | 1/153 | 1 file, +27 | Un ejemplo (§4.3.1) agregado a `docs/79-tournament-protocol-openclaw-native.md`; no está en `main` pero es trivial (27 líneas, un solo ejemplo) — residuo de lane de torneo por heurística del pack | `docs/79-tournament-protocol-openclaw-native.md` |

---

## 3. Propuesta — pack siguiente (solo si David da GO explícito)

### 3.1 Set KILL (28 ramas, nombres exactos listos para `--delete`)

```
codex/cand-prod001-stage2
coord-ag-2a/build-push-aeco-source-crawler
copilot-vps/052-aeco-kb-build-blocked-pat-scope
copilot-vps/052-aeco-kb-pushed-visibility-manual
copilot-vps/recover-post-force-push-2026-05-06
copilot-vps/stage4-013e-execution-2026-05-07
copilot/burn-q2-o7-o9-delegates
copilot/docs-editorial-master-plan
copilot/docs-notion-schema-gates
copilot/docs-s6-s7-multiplatform-design
copilot/feat-o16-2-047-gap-closure
copilot/feat-o16-infra-base
copilot/feat-s0-s1-discovery
copilot/feat-s10-publish-guard
copilot/feat-s2-source-verification
cursor/cand001-magnific-megaprompt
evidence/openclaw-e2e-cycle-001
rescue/copilot-vps/editorial-contract-paths-backup-2026-07
rescue/copilot-vps/editorial-contract-paths-canonical-2026-07
rescue/copilot-vps/poller-hardening-2026-07
rick-delivery/notion-poller-healthcheck-hardening
rick/stage7_5-voice-v2
rick/stage7_5-voice-v3
tournament/umbral-agent-stack-375-fa19920/lane-docs-explanatory
tournament/umbral-agent-stack-440-462ef1c1/lane-backup-impl
tournament/umbral-agent-stack-440-462ef1c1/lane-backup-qa
tournament/umbral-agent-stack-445-d5f34a07/lane-sync-delivery
tournament/umbral-agent-stack-d35-33863db/lane-openclaw-skill
```

### 3.2 Set RESCUE (1 rama, método sugerido)

- **`rescue/copilot-dirty-2026-07-13`** → cherry-pick de 2 archivos a `main` vía PR docs-only:
  `docs/15-model-quota-policy.md` (merge del bloque "2026-07-04 post-MP1") +
  `docs/audits/azure-foundry-capacity-openclaw-sync-2026-07-04.md` (archivo nuevo completo).
  Bajo riesgo — 2 docs, sin código, sin runtime. Requiere GO fila a fila o en lote explícito de David
  antes de ejecutar (no incluido en el set KILL de este pack).

### 3.3 Set KEEP (3 ramas — quedan en origin, sin acción)

- `codex/docs-pit-v2-contract` — contenido real de un frente archivado; decisión de fondo (¿vale la
  pena mergear contrato de un torneo cerrado?) es de David.
- `rescue/coordinador-dirty-2026-07-13` — tiene un script genuino no absorbido
  (`export-vscode-config.ps1`) mezclado con ediciones de doc ambiguas; separar antes de decidir.
- `rick/stage7_5-multiformat` — fork real de diseño (variantes multi-formato) que main no adoptó;
  valor incierto sin lectura humana de si el enfoque "multiformato" se quiere retomar.

---

## 4. Prohibido (respetado)

- Cero `git push --delete` / `gh api` delete ref en este pack.
- Cero touch a las 58 huérfanas sin merge-base.
- Cero touch a `#541`/`#521`.
- Cero touch a VPS, Notion, registry.
- Ninguna etiqueta sin diffstat/evidencia citada (tabla §2 completa antes de esta sección).
