# Housekeeping post-P1.2 — pack-branches kill + PRs #541/#521 (2026-08-07)

> **Ejecutor:** Cursor (orquestador) · GO David: "ok, vamos por esos recomendables, go"
> **Base previa:** `main` @ `72a40403` (post FOSSIL3 EXEC #604)

## 1. Kill de ramas de packs ya mergeadas (16/16)

Ramas `claude/pkg-uas-p1-2-*` + `cursor/pkg-uas-p1-2-orphan58-cherry4-archive-kill-20260807`
borradas de origin tras verificar que el contenido ya estaba en `main` vía PRs squash
(#588–#604 cadena P1.2). Cero PRs open sobre esas heads.

## 2. PRs docs-only mergeados como registro

| PR | Acción | Tip merge | Nota |
|---|---|---|---|
| #541 | squash-merge | `470706c9` | sys-diag 2026-07-17 (plan + inventario + inputs multi-IA). HISTÓRICO: no reabrir S14 contra conteos viejos. |
| #521 | squash-merge | `d12da293` | audit models.json per-agent. HISTÓRICO: auth vigente en norte §1. Doc sin secretos literales (scan). |

Heads de ambos PRs borradas tras merge (GitHub no auto-delete).

## 3. Estado de origin tras higiene

```
main
rick/stage7_5-multiformat   # KEEP_INDEFINITE (producto previo)
```

**2 heads** en origin (antes ~20 post-FOSSIL3, antes cientos en el arranque P1.2).

## 4. Fuera de alcance (sin tocar)

- P1.3 clones hermanos WIP
- P1.4 UX-01
- P2.3–P2.5 / P3.*
- Evento calendar E2E
- Capitalización adicional de skills (no requerida por este housekeeping)
