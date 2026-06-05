# D3.6 — Plugin + skill GitHub CLI para participantes de torneo

- **Estado:** 🚧 Fases 2–3 implementadas en PR; deploy/allowlist VPS pendiente.
- **Owner:** Codex (Worker + plugin TS) / Copilot-VPS (deploy + allowlist) / Cursor (docs + skill + protocolo).
- **Depende:** D3.4 retro ✅, protocolo `docs/79` §3–§4, preflight torneo 8/8.
- **No confundir con:** skill `tournament` (ideacional) ni `github.orchestrate_tournament` (Worker legacy `rick/t/{id}/`).

## Problema

Hoy las **lanes** del torneo OpenClaw-native deben cerrar con `git push` + `gh pr create` + línea `PR_URL=…` (`docs/79` §4.1). En la práctica:

- `github-ops` / tools `umbral_github_*` exigen prefijo **`rick/`** — **incompatible** con ramas `tournament/<id>/lane-<specialty>`.
- Las lanes usan `tools.profile: coding` (shell libre) → **sin guardrails** de título PR, branch, ni announce obligatorio.
- Resultado histórico: spawn OK, **PR URLs faltantes** (D3.1–D3.3).

## Objetivo

**Plugin OpenClaw** + **skill** dedicados para que cada participante (lane agent) use **GitHub CLI de forma gobernada** en torneos reales.

| Entregable | Rol |
|------------|-----|
| Skill `tournament-github-cli` | Contrato operativo para el agente lane (cuándo, orden, announce) |
| Plugin `umbral-tournament-github` | Tools tipadas en el gateway (preflight, branch, commit, PR, verify) |
| Worker `tournament_lane.*` | Validación servidor: ramas `tournament/…`, título `[tournament:…]`, sin merge |
| Preflight torneo | Exigir plugin habilitado + tools en allowlist de lane agents |

## Arquitectura objetivo

```text
main (orchestrator)
  └── sessions_spawn → rick-delivery | rick-ops (lane)
        └── tools: umbral_tournament_*  (plugin)
              └── Worker HTTP → tournament_lane.* (subprocess gh/git en VPS)
        └── skill: tournament-github-cli (procedimiento + fallbacks)
        └── announce: PR_URL=https://...
```

**Inferencia:** sigue en Azure Foundry vía alias OpenClaw. **Git/gh:** VPS clone `~/umbral-agent-stack`.

## Fases

### Fase 1 — Skill + docs (✅ en repo)

- [x] Skill [`openclaw/workspace-templates/skills/tournament-github-cli/SKILL.md`](../../openclaw/workspace-templates/skills/tournament-github-cli/SKILL.md)
- [x] Este roadmap
- [ ] Referencia en `multi-agent-tournament-orchestrator` (append lane contract)
- [ ] `d35-tournament-judge-kit` § “herramientas lane”

### Fase 2 — Worker tasks `tournament_lane.*` (implementado en PR D3.6)

Nuevo módulo `worker/tasks/tournament_lane_github.py`:

| Task | Descripción |
|------|-------------|
| `tournament_lane.preflight` | `gh auth`, repo path, clean worktree, `main` ff-only |
| `tournament_lane.create_branch` | Valida `tournament/<tournament_id>/lane-<specialty>` |
| `tournament_lane.commit_and_push` | Lista explícita de files; rechaza `main` |
| `tournament_lane.open_pr` | Título `[tournament:<id>:<specialty>] …`; body con checklist |
| `tournament_lane.verify_pr` | `gh pr view` + branch head + checks rollup → JSON para collect |

**Guardrails (no negociables):**

- Sin merge PR.
- Sin `git add -A`.
- Sin ramas fuera del patrón `tournament/<id>/lane-<specialty>`.
- Respuesta siempre incluye `pr_url` cuando OK.

Registrar en `worker/tasks/__init__.py`. Tests en `tests/test_tournament_lane_github.py`.

**PR sugerido:** Codex, issue “D3.6 tournament lane github tasks”.

### Fase 3 — Plugin `umbral-tournament-github` (implementado en PR D3.6; no habilitado en VPS)

Carpeta: [`openclaw/extensions/umbral-tournament-github/`](../../openclaw/extensions/umbral-tournament-github/).

- `openclaw.plugin.json` — id `umbral-tournament-github`, `skills: ["./skills"]`
- `index.ts` — tools espejo de Fase 2 (mismo patrón que `umbral-worker`)
- `skills/umbral-tournament-github/SKILL.md` — índice de tools del plugin

Config VPS (`plugins.entries.umbral-tournament-github`):

```json5
{
  "enabled": true,
  "config": {
    "baseUrl": "http://127.0.0.1:8088",
    "tokenFile": "/home/rick/.config/openclaw/worker-token",
    "defaultRepoPath": "/home/rick/umbral-agent-stack"
  }
}
```

**Allowlist:** añadir `umbral_tournament_*` solo en agentes lane (`rick-delivery`, `rick-ops`, …), no en `main` salvo preflight opcional.

### Fase 4 — Integración protocolo + D3.5

- Actualizar `docs/79` §3 `task_template`: “usar `umbral_tournament_open_pr` antes de gh manual”.
- `tournament-preflight-dry-run.sh`: check plugin loaded + skill synced.
- D3.5 acceptance: lanes deben reportar tool calls `umbral_tournament_*` en transcript (evidencia).

### Fase 5 — Deprecación gradual shell libre

- Lane agents: `tools.profile: coding` mantiene bash, pero skill marca **preferir plugin**.
- Métricas Mission Control (futuro): % PRs cerrados vía plugin vs rescate manual.

## Criterios de aceptación D3.6

1. Lane puede ejecutar flujo completo **solo con tools del plugin** (sin `gh` manual).
2. PR title y branch rechazados si no cumplen convención torneo.
3. `tournament_lane.verify_pr` devuelve JSON usable por orchestrator collect.
4. Documentado en unified plan + judge kit.
5. VPS: rsync skill + plugin path; restart gateway; smoke 1 lane dry-run (sin merge).

## Owners y prompts

| Fase | Agente | Prompt gate |
|------|--------|-------------|
| 2 | Codex | `autorizo PR D3.6 worker tournament_lane github` |
| 3 | Codex + Copilot-VPS | deploy plugin + allowlist |
| 4 | Cursor | docs-only + protocol bump |
| Smoke | Copilot-VPS | tras Fase 3 |

## Relación con existentes

| Artefacto | Uso en torneo OpenClaw-native |
|-----------|-------------------------------|
| `github-ops` / `umbral_github_*` | Flujo **`rick/`** diario — **no** lanes |
| `github.orchestrate_tournament` | Torneo Worker legacy — **no** `sessions_spawn` |
| `multi-agent-tournament-orchestrator` | Parent spawn — referencia skill lane |
| `tournament-github-cli` | **Participantes** |

## Referencias

- [`docs/79-tournament-protocol-openclaw-native.md`](../79-tournament-protocol-openclaw-native.md)
- [`docs/architecture/tournament-protocol.md`](../architecture/tournament-protocol.md)
- [`d35-tournament-judge-kit-2026-06-04.md`](d35-tournament-judge-kit-2026-06-04.md)
- [`q2-core-first-unified-plan-2026-06-04.md`](q2-core-first-unified-plan-2026-06-04.md)
