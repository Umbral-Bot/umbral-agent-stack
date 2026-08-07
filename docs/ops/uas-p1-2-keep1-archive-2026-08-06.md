# P1.2 — ARCHIVE_DOCS_ONLY de la fila 1 (PIT v2 contract) — 2026-08-06

> **Pack:** PKG-UAS-P1-2-KEEP1-ARCHIVE · rama `claude/pkg-uas-p1-2-keep1-archive-20260806` · base `23f7fac3`
> **GO de David (verbatim):** "GO 1 ARCHIVE_DOCS_ONLY" — solo fila 1 del brief
> [uas-p1-2-orphan-keep3-2026-08-06.md](uas-p1-2-orphan-keep3-2026-08-06.md). Filas 2 y 3 FUERA de
> este pack.

---

## 1. Fuente

- Rama: `origin/codex/docs-pit-v2-contract` @ `16e39b40` — verificada viva en el SHA esperado.
- Método: `git checkout origin/codex/docs-pit-v2-contract -- <3 paths>` (no cherry-pick del commit
  completo, para no arrastrar el diff de `SKILL.md`/vision-doc que ese commit también toca).

## 2. Archivos traídos (exactamente 3, prohibido ampliar)

| Archivo | Líneas | Marcador agregado |
|---|---|---|
| `docs/ops/pit-broker-contract.md` | 137 (134 originales + 3 de marcador) | "Estado: HISTÓRICO... no es contrato runtime vigente" |
| `docs/ops/pit-tournament-v2-contract.md` | 603 (597 + 6 de marcador) | idem + nota de que la skill en `main` nunca se cableó a este contrato |
| `docs/ops/pit-mega-diagnostic-20260620-summary.md` | 124 (121 + 3 de marcador) | idem, versión corta |

Cada marcador es una nota de 3-6 líneas al inicio del doc (bajo el H1, antes del `Status:`
original) — sin modificar ni una línea del contenido original más allá de esa nota. Contenido
verificado idéntico al de la rama fuente salvo esas notas (comparado con `git checkout` directo,
no reescrito a mano).

## 3. Confirmación de exclusión (lo que NO se tocó)

```
git diff origin/main -- openclaw/workspace-templates/skills/product-innovation-tournament/SKILL.md
→ (vacío — diff 0, blob idéntico a origin/main: 9ee418b9)

git diff origin/main -- docs/ops/product-innovation-tournament-vision-2026-06-09.md
→ (vacío — diff 0)
```

`git diff --stat origin/main` sobre el árbol completo confirma **solo** los 3 paths autorizados:

```
docs/ops/pit-broker-contract.md                  | 137 +++++
docs/ops/pit-mega-diagnostic-20260620-summary.md | 124 +++++
docs/ops/pit-tournament-v2-contract.md           | 603 +++++++++++++++++++++++
3 files changed, 864 insertions(+)
```

## 4. Rama fuente `codex/docs-pit-v2-contract`

**No se borró en este pack.** Su contenido de docs ya quedaría replicado en `main` una vez este
PR mergee; el delete queda propuesto para después (ver REPORT / TU TURNO), no ejecutado
preventivamente — mismo patrón que RESCUE1 (#592).

## 5. Prohibido (respetado)

- Cero touch a `SKILL.md` (confirmado diff 0).
- Cero touch al vision-doc (confirmado diff 0).
- Cero touch a filas 2 (`rescue/coordinador-dirty-2026-07-13`) y 3 (`rick/stage7_5-multiformat`)
  del brief KEEP3.
- Cero touch a las 58 huérfanas sin merge-base.
- Cero contenido inventado — solo el marcador HISTÓRICO, texto original sin editar.
- Cero self-merge.
