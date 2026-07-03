# Pass 10 (VPS) — Checkouts UAS en la VPS

> Ejecutado 2026-07-03 por Copilot-VPS vía `docs/ops/MEGAPROMPT-copilot-vps-workspace-hygiene-audit-2026-07-02.txt`.

**Reporte completo:** [`docs/audits/workspace-hygiene-vps-2026-07-03/`](../workspace-hygiene-vps-2026-07-03/README.md)

## Veredicto

```
WORKSPACE_HYGIENE_VPS_READY | checkouts=15 | rescue=5 | canonical_proposed=YES
VPS_WORKSPACE_HYGIENE_READY | checkouts=15 | rescue=5 | crons_repo=17 | drift_openclaw=YES
```

## Resumen de 1 pantalla

- 15 checkouts git (5 clones + 10 worktrees) + 2 residuos → 1 KEEP (canónico), 3 RESCUE, 8 ARCHIVE, 5 DELETE-candidate.
- Runtime sano: 17 crons + worker/dispatcher/mission-control leen SOLO el canónico; gateway = npm-global (esperado).
- P0: `rick/vps` con 7 commits sin respaldo remoto (CAND-PROD001 brief + Embudo V2 + scripts) · poller-hardening con ~20 commits sin respaldo.
- Canónico: 24 stashes + 103 ramas con tip no respaldado (espejo del problema Windows Pass 8) → triage bajo gate.
- Drift OpenClaw runtime→repo en AGENTS/SOUL/VOICE (material vivo sin capitalizar).
- Gate **G-WH-VPS-1** pendiente de firma para cualquier push-rescue/move/delete.
