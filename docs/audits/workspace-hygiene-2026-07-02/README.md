# Workspace Hygiene Audit — 2026-07-02

> Task `2026-07-02-006` · Copilot Windows Pass 0–11 · **PR #496 merged** · **G-WH-1 firmado 2026-07-03** · Pass 8 en curso.

## Veredicto

```
WORKSPACE_HYGIENE_AUDIT_READY | clones_windows=17 | rescue=4 | hilos_activos=5 | canonical_proposed=YES
```

## Índice

| Pass | Doc | Contenido clave |
|---|---|---|
| 1 | [01-clones-windows.md](01-clones-windows.md) | 17 clones inventariados: 2 KEEP, 2 RESCUE críticos, resto ARCHIVE/DELETE |
| 2 | [02-cursor-threads.md](02-cursor-threads.md) | Hilo lead sobre clone base sucio; colisión IDs task; sprint docs sin push |
| 3 | [03-copilot-windows-threads.md](03-copilot-windows-threads.md) | PR #495 activo (G-GR-1 firmado); 6 PRs zombi de mayo; ramas fósiles |
| 4 | [04-claude-threads.md](04-claude-threads.md) | Sin hilo activo; clone re-apuntar a main; `.claude/commands` OK |
| 5 | [05-other-agents-threads.md](05-other-agents-threads.md) | Triple clone Codex; Antigravity fósil marzo; PR #480 a decidir |
| 6 | [06-working-method.md](06-working-method.md) | Flujo real, qué conservar, regla "done = pushed", skills mínimos por IDE |
| 7 | [07-debt-register.md](07-debt-register.md) | 5×P0, 9×P1, 6×P2 con owner sugerido |
| 8 | [08-rescue-candidates.md](08-rescue-candidates.md) | Plan cherry-pick/copiar/descartar por clone — NO ejecutado |
| 9 | [09-canonical-model.md](09-canonical-model.md) | **TABLA PRINCIPAL**: clone canónico por superficie + hilos MANTENER/ARCHIVAR — gate **G-WH-1** |
| 10 | [`docs/ops/MEGAPROMPT-copilot-vps-workspace-hygiene-audit-2026-07-02.txt`](../../ops/MEGAPROMPT-copilot-vps-workspace-hygiene-audit-2026-07-02.txt) | Espejo VPS — generado, **NO ejecutado** (David lo pega en Copilot-VPS tras merge de este PR) |

## Los 5 hilos activos (MANTENER)

1. **GR** Graphify — ✅ PR #495 merged, task 002 done
2. **WH** Pass 8 rescates — `docs/ops/MEGAPROMPT-copilot-windows-workspace-hygiene-pass8-2026-07-03.md`
3. **RV** Rick voz capitalización — Cursor, task 004
4. **NM** Notion MCP audit — Codex/Cursor, task 005
5. **PIT** contrato v2 — PR #480, decisión David

Todo lo demás: ARCHIVAR (detalle en Pass 9).

## Gates para David

| Gate | Decisión |
|---|---|
| **G-WH-1** | ✅ Firmado 2026-07-03 — modelo canónico aprobado; Pass 8 autorizado |
| **G-WH-2** | (a 30 días) borrado definitivo de lo archivado |
| PR #495 | ✅ merged |
| PR #480 + zombis mayo | merge/cierre según Pass 3 |
