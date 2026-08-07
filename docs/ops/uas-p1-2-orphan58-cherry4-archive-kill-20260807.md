# P1.2 — Fila 4 CHERRY: ARCHIVE hook + KILL rama (2026-08-07)

> **Pack:** PKG-UAS-P1-2-ORPHAN58-CHERRY4-ARCHIVE-KILL · rama
> `cursor/pkg-uas-p1-2-orphan58-cherry4-archive-kill-20260807` · base `a08ae3dc`
> **GO de David (verbatim):** "ok aplica todo eso , lo mas segurio, lo mas higenico y trazable"
> — opción **(d)** del orquestador: archivar el `.sh` bajo `docs/archive/` + KILL
> `rick/test-github-mvp-smoke` (sin `git add -f`, sin wire en `settings.json`).
> **Antecedente STOP:** [uas-p1-2-orphan58-cherry25-exec-20260807.md](uas-p1-2-orphan58-cherry25-exec-20260807.md) §1
> (hook gitignoreado en `.gitignore:78`).

## 1. Fuente

| Campo | Valor |
|---|---|
| Rama | `origin/rick/test-github-mvp-smoke` @ `9d983463` |
| Merge-base con `origin/main` | ausente (`git merge-base` exit 1) |
| Path tip | `.claude/hooks/block-deployed-repo-writes.sh` |
| Blob SHA | `7d18d8c1ae82cb79e3b6f383001450609b8a69ac` |
| PR abierto sobre la rama | ninguno |

## 2. Archive (trazable, sin violar `.gitignore`)

Destino:

- `docs/archive/hooks-block-deployed-repo-writes-2026-04/block-deployed-repo-writes.sh`
- `docs/archive/hooks-block-deployed-repo-writes-2026-04/README.md`

Evidencia de identidad: `git hash-object` del archivo archivado == blob del tip (`7d18d8c1…`).

**No** se escribió en `.claude/hooks/` (sigue ignorado). **No** se tocó `.claude/settings.json`.
**No** se usó `git add -f`.

## 3. KILL

Tras el commit de archive en la rama del pack:

```
git push origin --delete rick/test-github-mvp-smoke
```

Post-check: `git ls-remote --heads origin rick/test-github-mvp-smoke` → vacío.

## 4. Exclusiones (intactas)

- Resto de contenido de la rama fuente (audits smoke / snapshot / ruido `.claude/skills`) — no archivado (ya descartado en CHERRY5).
- KEEP residuales: `cursor/power-bi-libraries-formats-5c1b`, `cursor/regression-test-coverage-b904`, `feat/bitacora-populate`, `rick/stage7_5-multiformat` (KEEP_INDEFINITE previo).
- PRs open `#541` / `#521` — sin tocar.

## 5. Cierre P1.2 CHERRY

Con este pack, las 5 CHERRY_CANDIDATE + #58 quedan resueltas (1 KILL granola, 3 ARCHIVE+KILL, 1 ARCHIVE-hook+KILL, #58 KILL). Residual P1.2: FOSSIL/KEEP listados arriba + clones hermanos P1.3 — fuera de este pack.
