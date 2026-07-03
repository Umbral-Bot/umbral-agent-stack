# Pass V3 — Workspaces OpenClaw vs repo

> Fecha: 2026-07-03 · Read-only · Comparación por nombres/fechas/bytes/conteo de líneas diff — **sin volcar contenido**.
> Gateway: v2026.6.10, loopback :18789, systemd user active. 8 agentes, 3 activos, 25 sesiones.

## Drift archivos core — `openclaw/workspace-templates/` (repo main) vs `~/.openclaw/workspace/` (runtime Rick)

| Archivo | Repo dice (template) | VPS muestra (runtime) | Diff | Estado |
|---|---|---|---|---|
| `AGENTS.md` | 27.734 B | 27.996 B (jul-02 18:44) | 524 líneas | **DRIFT** |
| `SOUL.md` | 14.234 B | 14.427 B (jul-02 18:44) | 386 líneas | **DRIFT** |
| `VOICE.md` | 3.139 B | 3.209 B (jul-02 18:44) | 140 líneas | **DRIFT** |
| `IDENTITY.md` | 619 B (template) | 3.220 B | 64 líneas | **cubierto por override** `workspace-agent-overrides/main/IDENTITY.md` (== runtime, SYNC) |
| `TOOLS.md` | 7.454 B | 7.159 B (mar-22) | 4 líneas | drift menor |
| `USER.md` | 564 B | 564 B | 0 | SYNC |
| `HEARTBEAT.md` | 435 B | 435 B | 0 | SYNC |

**Dirección del drift**: runtime > repo (los archivos runtime son más nuevos y más grandes). No es incidente de deploy: es el workspace vivo de Rick evolucionando sin capitalizarse de vuelta al repo. El override `main/` del repo solo captura `IDENTITY.md`.

> Nota: Windows Pass 8 (PR #498) rescató "VOICE.md + persona voz Rick" hacia el repo, pero el override desplegable `workspace-agent-overrides/main/` sigue conteniendo únicamente IDENTITY.md → el VOICE runtime de la VPS (3.209 B, jul-02) sigue sin fuente canónica desplegable.

## Overrides repo vs workspaces desplegados

- **Overrides en repo SIN workspace desplegado** (repo dice X / VPS no lo muestra):
  - `rick-editorial` — sin `~/.openclaw/workspaces/rick-editorial`
  - `rick-tech` — sin `~/.openclaw/workspaces/rick-tech`
- **Workspaces desplegados SIN override en repo**: ninguno (excluyendo `pit-*`, `skills`, `.bak`) — los 9 agentes rick-* + improvement-supervisor tienen override.

## Inventario `~/.openclaw/workspaces/` (27 entradas)

- 9 agentes: `improvement-supervisor`, `rick-communication-director`, `rick-delivery`, `rick-linkedin-writer`, `rick-ops`, `rick-orchestrator`, `rick-qa`, `rick-tracker`, `skills`
- 18 lanes PIT: `pit-openclaw-broker-v1..v4` ×3 lanes, `pit-salud-mental-pilot` ×3, `pit-umbral-bim2-sharepoint-acc` ×3
- 1 residuo: `rick-orchestrator.bak-pre-019-20260507-093659` (backup manual may-07) → candidato ARCHIVE bajo gate
- Dentro de `rick-delivery/`: el worktree `umbral-agent-stack-poller-hardening` (RESCUE, ver Pass V1/V4)

## Residuo en workspace de Rick

- `~/.openclaw/workspace/IDENTITY.md.bak.20260505-101646` (374 B, may-05) → candidato DELETE bajo gate.
- `tmp_experimento_embudo_posts_news_blog.md` (mar-13) → contenido experimento Embudo; cruza con los commits `rick/vps` de marzo (Pass V1) — evaluar en el mismo rescate.

## Config warning (informativo, NO tocado)

`openclaw status` reporta: `plugins.load.paths` apunta al directorio de plugins bundled (redundante) — sugerencia del propio CLI: `openclaw doctor --fix`. Queda para decisión operador; **no se ejecutó**.

## Veredicto Pass V3

`drift_openclaw=YES` — dirección runtime→repo (material vivo sin capitalizar), sin evidencia de runtime sirviendo material viejo. Acción propuesta (bajo gate, y con skill `openclaw-vps-operator`): sesión de capitalización AGENTS/SOUL/VOICE runtime → `workspace-agent-overrides/main/` en PR.
