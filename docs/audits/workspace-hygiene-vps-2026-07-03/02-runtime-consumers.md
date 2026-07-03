# Pass V2 — Consumidores del repo en runtime

> Fecha: 2026-07-03 · Read-only · Método: `crontab -l`, `systemctl --user list-units/show`, grep de unit files
> **Resultado: SIN hallazgo P0 — todos los consumidores leen el checkout canónico.**

## Crontab (17 activos + 1 pausado)

| Schedule | Script | Path base |
|---|---|---|
| `*/30 * * * *` | `scripts/vps/health-check.sh` | canónico |
| `*/5 * * * *` | `scripts/vps/supervisor.sh` | canónico |
| `0 8,14,20 * * *` | `scripts/vps/sim-daily-cron.sh` | canónico (`~`) |
| `*/5 * * * *` | `scripts/vps/notion-poller-cron.sh` | canónico |
| `30 8,14,20 * * *` | `scripts/vps/sim-report-cron.sh` | canónico |
| `0 22 * * *` | `scripts/vps/daily-digest-cron.sh` | canónico |
| `0 9,15,21 * * *` | `scripts/vps/sim-to-make-cron.sh` | canónico |
| `0 6 * * *` | `scripts/vps/e2e-validation-cron.sh` | canónico |
| `0 7 * * 1` | `scripts/vps/ooda-report-cron.sh` | canónico |
| `* * * * *` | `scripts/vps/scheduled-tasks-cron.sh` | canónico |
| `*/15 * * * *` | `scripts/vps/quota-guard-cron.sh` | canónico |
| `20 5 * * *` | `scripts/vps/notion-curate-cron.sh` | canónico |
| `20 */6 * * *` | `scripts/vps/openclaw-runtime-snapshot-cron.sh` | canónico |
| `0 * * * *` | `scripts/vps/dashboard-rick-cron.sh` | canónico |
| `0 */6 * * *` | `scripts/vps/openclaw-panel-cron.sh` | canónico |
| `0 8 * * *` | `scripts/vps/granola-gap-check.sh` | canónico (`$HOME`) |
| — pausado — | `# B1-paused 2026-05-24 discovery-publish-cron.sh` | canónico |

Paths referenciados por cron (normalizados): `[$HOME|~|/home/rick]/umbral-agent-stack` — **ninguno apunta a un checkout secundario**.

## Services systemd (user units)

| Unit | Estado | ExecStart | WorkingDirectory / PYTHONPATH |
|---|---|---|---|
| `umbral-worker.service` | active | `~/umbral-agent-stack/.venv/bin/python -m uvicorn worker.app:app :8088` | `/home/rick/umbral-agent-stack` |
| `openclaw-dispatcher.service` | active | `/usr/bin/python3 -m dispatcher.service` | `WorkingDirectory` + `PYTHONPATH` = canónico |
| `mission-control.service` | active | `~/umbral-agent-stack/.venv/bin/python -m uvicorn mission_control.app:app :8089` | canónico |
| `openclaw-gateway.service` | active (pid 1462018, v2026.6.10) | `/usr/bin/node ~/.npm-global/lib/node_modules/openclaw/dist/index.js gateway --port 18789` | npm-global (NO consume repo) — **coincide con lo documentado** en copilot-instructions |

- Unit files con referencia al repo: `umbral-worker.service`, `openclaw-dispatcher.service`, `mission-control.service` (+ symlinks en `default.target.wants/`).
- Timers systemd: solo `launchpadlib-cache-clean.timer` (sistema, irrelevante).

## Observaciones

1. **repo dice / VPS muestra**: la tabla de servicios en `.github/copilot-instructions.md` no lista `mission-control.service` como consumidor de `mission_control/**`. La unit existe y corre desde el canónico. → Deuda menor de docs (añadir fila a la tabla de deploy).
2. El cron `discovery-publish` sigue comentado (`B1-paused 2026-05-24`) — estado intencional, se reporta para trazabilidad.
3. Ningún cron/unit lee `~/.openclaw/workspace/umbral-agent-stack` (clone `rick/vps`) ni ningún otro checkout secundario → el riesgo de la divergencia `rick/vps` es **pérdida de material**, no runtime sirviendo código viejo.
