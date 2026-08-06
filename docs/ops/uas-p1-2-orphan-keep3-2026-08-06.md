# P1.2 — Brief de decisión sobre los 3 KEEP (2026-08-06)

> **Pack:** PKG-UAS-P1-2-ORPHAN-KEEP3 · rama `claude/pkg-uas-p1-2-orphan-keep3-20260806` · base `193a579e`
> **GO de David:** brief de decisión por fila. **Cero deletes, cero cherry-pick a `main` en este pack**
> — solo acta + recomendación.
> **Precede:** [uas-p1-2-orphan-32-classify-2026-08-06.md](uas-p1-2-orphan-32-classify-2026-08-06.md)
> (clasificación original) → RESCUE1 (#592, ya mergeado, `rescue/copilot-dirty-2026-07-13` ya
> borrada — no se rehace aquí).

Re-verificado antes de escribir: las 3 ramas existen en origin, con el SHA esperado, y tienen
merge-base con `origin/main`.

---

## Tabla

| Rama | Recomendación | Esfuerzo si RESCUE |
|---|---|---|
| `codex/docs-pit-v2-contract` @ `16e39b40` | **ARCHIVE_DOCS_ONLY** (solo los 3 `.md` nuevos; excluir `SKILL.md` y el vision-doc) | Bajo |
| `rescue/coordinador-dirty-2026-07-13` @ `16219f25` | **RESCUE_SELECTIVE** — solo `scripts/export-vscode-config.ps1` | Bajo |
| `rick/stage7_5-multiformat` @ `a2635398` | **KEEP_INDEFINITE** | N/A |

---

## 1. `codex/docs-pit-v2-contract` — ARCHIVE_DOCS_ONLY

**Problema que resolvía:** definir el contrato v2 del torneo PIT (Ruta B broker-real: OpenClaw como
orquestador, `copilot_cli.run` como única superficie de coding) — 3 docs nuevos + edición de la
skill runtime `product-innovation-tournament/SKILL.md` para reflejar ese contrato.

**¿Main ya tiene equivalente?** Los 3 docs (`pit-broker-contract.md`, `pit-tournament-v2-contract.md`,
`pit-mega-diagnostic-20260620-summary.md`) **no existen en `main`**. Pero `SKILL.md` **sí existe** en
`main`, con contenido **anterior** (v1.3 "PIT-2b + PIT-DEV") — la rama lo actualiza a "v2.0 P0
alignment" agregando una sección entera "Contrato canónico v2 — Ruta B broker-only" que cambia
comportamiento runtime (menciona `copilot_cli.run`, gate `PIT_RUN_PASS_BROKER_REAL`, reglas de
fallback prohibido).

**Riesgo runtime si se mergea tal cual:** **alto** para `SKILL.md` — es una skill que Rick puede leer
y ejecutar; mergearla sin GO cambiaría comportamiento real de torneos PIT, aunque el frente esté
archivado. **Bajo/nulo** para los 3 docs puros (nadie los referencia desde código).

**Recomendación:** archivar solo los 3 `.md` nuevos como registro histórico del frente PIT (ya
"ARCHIVAR" por gobernanza, inventario §1 A.2) — **sin tocar** `SKILL.md` ni el vision-doc, que quedan
excluidos explícitamente. Si David prefiere no conservar ni el registro histórico, KILL es la
alternativa razonable; no hay urgencia en ninguna dirección.

## 2. `rescue/coordinador-dirty-2026-07-13` — RESCUE_SELECTIVE

**Problema que resolvía:** rescatar el WIP dirty que quedó en el clone hermano
`umbral-agent-stack-codex-coordinador` el 2026-07-13 (H1 b0004) — una edición del contrato de
revisión humana editorial + un script nuevo de exportación de config de VS Code.

**¿Main ya tiene equivalente?** `docs/ops/editorial-publicaciones-human-review-contract.md` **sí**
tiene equivalente en `main`, pero **divergente** (158 inserciones / 32 deleciones de diferencia) —
mismo patrón ambiguo/solapado con otras 2 ramas rescue del mismo doc ya visto en el pack de
clasificación; no es un cherry-pick limpio. `scripts/export-vscode-config.ps1` **no existe** en
`main` en absoluto — confirmado.

**Riesgo runtime:** nulo — es tooling de desarrollo (config de editor), no código de producto ni
infraestructura.

**Recomendación:** traer **solo** `scripts/export-vscode-config.ps1` (path exacto), dejando fuera el
contrato editorial — ese archivo necesita una decisión de contenido (¿cuál versión es la correcta
entre `main` y las 3 ramas rescue que lo tocan?), no un rescate mecánico.

## 3. `rick/stage7_5-multiformat` — KEEP_INDEFINITE

**Problema que resolvía:** explorar un enfoque "multi-formato" para el copywriter de Rick — un
`writer` con `FORMATS` y variantes por canal (blog / LinkedIn-share / LinkedIn-standalone), evaluador
con flag `--format`, 31 tests nuevos, informe real de 36 llamadas.

**¿Main ya tiene equivalente?** Sí, pero **diseñado distinto**: `main` adoptó un archivo por canal
(`blog-copy-system.md`, `linkedin-copy-system.md`, `x-copy-system.md`) en vez del modelo
multi-variante de esta rama. Es un **fork de diseño real** (583 líneas propias de la rama que `main`
no tiene, 410 líneas propias de `main` que la rama no tiene) — no absorción, no ausencia trivial.

**Riesgo runtime si se mergea:** **alto** — `stage7_5_copy_writer.py` es el writer de producción
(marcado FROZEN Ola 1 en `docs/editorial-pipeline/master-plan.md`); mergear el enfoque multi-formato
reemplazaría o competiría con el enfoque canónico vigente sin que nadie haya decidido retomarlo.

**Recomendación:** ninguna acción — es una decisión de producto ("¿retomamos el enfoque
multi-formato para blog/LinkedIn?"), no una limpieza de higiene git. Queda viva en origin sin costo
mientras no se decida.

---

## Prohibido (respetado)

- Cero `git push --delete`.
- Cero `cherry-pick` a `main` en este pack (las recomendaciones de RESCUE/ARCHIVE quedan para un
  pack de ejecución con GO fila a fila).
- Cero re-ejecución de RESCUE1 (`rescue/copilot-dirty-2026-07-13` ya está mergeado y borrado).
- Cero touch a las 58 huérfanas sin merge-base.
- Cero touch a VPS, Notion.
