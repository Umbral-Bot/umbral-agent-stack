# P1.2 — RESCUE de rescue/copilot-dirty-2026-07-13 (2026-08-06)

> **Pack:** PKG-UAS-P1-2-ORPHAN-RESCUE1 · rama `claude/pkg-uas-p1-2-orphan-rescue1-20260806` · base `f86e4ce1`
> **GO de David:** rescatar a `main` los 2 docs de `rescue/copilot-dirty-2026-07-13` (acta
> [uas-p1-2-orphan-32-classify-2026-08-06.md](uas-p1-2-orphan-32-classify-2026-08-06.md) §3.2 / PR #590).

---

## 1. Fuente

- Rama: `origin/rescue/copilot-dirty-2026-07-13` @ `003bafc2` — verificado vivo y con el SHA
  esperado antes de tocar nada.
- Método: `git cherry-pick 003bafc2` sobre `claude/pkg-uas-p1-2-orphan-rescue1-20260806`
  (rama nueva desde `origin/main`). **Aplicó limpio, cero conflictos.**

## 2. Archivos traídos (exactamente 2, nada más)

| Archivo | Cambio | Verificación |
|---|---|---|
| `docs/15-model-quota-policy.md` | +8/−1 | El bloque "Estado operativo vigente (2026-07-04 — post-MP1 `OPENCLAW_AZURE_ONLY=YES`)" se inserta **antes** del bloque histórico de 2026-03-08, que se conserva íntegro (solo se le agregó la etiqueta "histórico"). Cero contenido de `main` perdido — confirmado con `git diff origin/main HEAD -- docs/15-model-quota-policy.md` |
| `docs/audits/azure-foundry-capacity-openclaw-sync-2026-07-04.md` | archivo nuevo, 121 líneas | No existía en `main`; ahora completo. El propio doc declara "Sin secretos: ninguna key impresa ni almacenada en este documento" |

`git diff --stat origin/main HEAD` confirma **exactamente estos 2 paths**, ningún otro archivo tocado.

## 3. Post-commit

```
git show HEAD:docs/15-model-quota-policy.md                                   # bloque 2026-07-04 presente
git show HEAD:docs/audits/azure-foundry-capacity-openclaw-sync-2026-07-04.md  # 121 líneas, completo
```

Ambos confirmados en el tip de la rama del PR.

## 4. Rama fuente `rescue/copilot-dirty-2026-07-13`

**No se borró en este pack.** El GO condicionaba el delete a que "el PR de rescate quede listo" —
dado que el PR de este pack aún no tiene merge de David, el borrado de la rama fuente se propone
como paso explícito post-merge (ver REPORT / TU TURNO), no se ejecuta preventivamente.

## 5. Prohibido (respetado)

- Cero touch a los 3 KEEP (`codex/docs-pit-v2-contract`, `rescue/coordinador-dirty-2026-07-13`,
  `rick/stage7_5-multiformat`).
- Cero touch a las 58 huérfanas sin merge-base.
- Cero KILL de otras ramas.
- Cero touch a VPS, Notion.
- Cero self-merge.
