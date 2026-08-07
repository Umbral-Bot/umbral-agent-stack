# P1.2 — KILL fila 1 CHERRY5: `codex/wip-granola-v2-snapshot-2026-04-30` (2026-08-07)

> **Pack:** PKG-UAS-P1-2-ORPHAN58-CHERRY1-KILL · rama
> `claude/pkg-uas-p1-2-orphan58-cherry1-kill-20260807` · base `23241276`
> **GO de David (verbatim):** "GO 1 KILL" — solo fila 1 del brief
> [uas-p1-2-orphan58-cherry5-20260807.md](uas-p1-2-orphan58-cherry5-20260807.md). Filas 2–5 fuera de
> alcance.

## Qué se hizo

1. Confirmada rama viva @ `e72ebab4` (coincide con el tip del brief), sin PR abierto asociado
   (`gh pr list --state open --search "head:codex/wip-granola-v2-snapshot-2026-04-30"` → vacío).
2. `git push origin --delete codex/wip-granola-v2-snapshot-2026-04-30` → `[deleted]`.
3. Post-check:

```
codex/wip-granola-v2-snapshot-2026-04-30   -> ls-remote vacío (borrada, confirmado)

Filas 2-5 CHERRY (vivas, sin tocar):
rick/editorial-linkedin-writer-flow        410266a0
antigravity/sync-uncommitted-changes       9e32a99b
rick/test-github-mvp-smoke                 9d983463
codex/notion-governance-v1-contract        2221f5af

4 KEEP_FOSSIL (vivas, sin tocar):
cursor/power-bi-libraries-formats-5c1b     6a64515c
cursor/regression-test-coverage-b904       de318aff
feat/bitacora-populate                     fe5d3393
rick/windows-dirty-rescue-2026-04-27       e77ca7c2   <- #58, ver nota abajo
```

## Nota sobre #58 `rick/windows-dirty-rescue-2026-04-27`

El brief CHERRY5 documentó que los 6 paths únicos de esta rama son subconjunto exacto de los 28 de
`codex/wip-granola-v2-snapshot-2026-04-30` (ahora borrada) — es decir, su contenido no aporta nada
que no estuviera ya cubierto por el KILL de arriba. **No se borró.** Sigue en `KEEP_FOSSIL` tal
como la clasificó el acta original del 2026-08-06, a la espera de un GO explícito y aparte —
borrarla no estaba en el alcance de este pack ("NO tocar... aunque el brief diga que #1 la subsume,
NO borrar #58 sin GO aparte").

## Prohibido (respetado)

- Filas 2–5 CHERRY: sin tocar.
- 4 KEEP_FOSSIL (incluida #58): sin tocar.
- #541 / #521: sin tocar (verificados abiertos, `OPEN`, sin relación con este delete).
- `main`: sin tocar (solo se leyó `origin/main` como base de la rama de trabajo).
- Un solo `git push --delete`, sobre la única rama autorizada.

## Actualización norte §5 P1.2

Ver [uas-north-canonical-2026-08-06.md](uas-north-canonical-2026-08-06.md) §5 P1.2: fila 1
(`codex/wip-granola-v2-snapshot-2026-04-30`) → **KILL DONE**. Filas 2–5 quedan `PENDING` GO de
David.
