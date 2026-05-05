# Umbral Mission Control — MVP

Dashboard **read-only** para OpenClaw + Worker. Cubre los sub-objetivos
`O13.1`, `O13.2`, `O13.6`, `O13.7` del [Plan Q2-2026](../../notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md)
bajo el scope congelado en [ADR-009](../docs/adr/ADR-009-mission-control-scope.md).

> Esto **no ejecuta agentes**. Sólo lee `openclaw.json`, longitudes de cola
> Redis, y el state file de quota Claude Pro. La ejecución sigue en
> `worker/`, `dispatcher/` y OpenClaw Gateway.

## Quickstart local

```bash
source .venv/bin/activate
pip install -e .                # FastAPI/uvicorn/redis ya están en deps
pip install jinja2              # extra requerido para templates HTMX

export MISSION_CONTROL_TOKEN="dev-token-cambiar"
python -m uvicorn mission_control.app:app --host 127.0.0.1 --port 8089
```

Abrí `http://127.0.0.1:8089/` (reemplazá `__PASTE_TOKEN__` en el HTML por tu token)
o consumí JSON con curl:

```bash
curl -fsS -H "Authorization: Bearer $MISSION_CONTROL_TOKEN" \
  http://127.0.0.1:8089/agents | jq
```

## Endpoints

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/health` | anónimo | healthcheck (status, timestamp) |
| GET | `/` | bearer | dashboard HTMX |
| GET | `/agents` | bearer | lectura de `openclaw.json` |
| GET | `/quotas` | bearer | state file de quota Claude Pro |
| GET | `/queue` | bearer | longitudes de colas Redis conocidas |
| GET | `/tournaments` | bearer | placeholder hasta O13.4 |

Todos los endpoints (excepto `/health`) requieren `Authorization: Bearer
$MISSION_CONTROL_TOKEN`. Si la env var no está seteada, todas las rutas
autenticadas responden **503** (fail-closed por diseño).

## Variables de entorno

| Var | Default | Notas |
|---|---|---|
| `MISSION_CONTROL_HOST` | `127.0.0.1` | bind. **No exponer** al público sin túnel SSH |
| `MISSION_CONTROL_PORT` | `8089` | |
| `MISSION_CONTROL_TOKEN` | _(none)_ | Bearer obligatorio. Si falta → 503 |
| `REDIS_URL` | `redis://localhost:6379/0` | Compartido con `dispatcher/` |
| `OPENCLAW_JSON_PATH` | `~/.openclaw/openclaw.json` | Best-effort: si no existe, `/agents` devuelve `available=false` |
| `OPENCLAW_QUOTA_STATE_PATH` | `~/.config/openclaw/claude-quota-state.json` | Idem |
| `MISSION_CONTROL_SNAPSHOTS_DIR` | `mission_control/snapshots/` | Git-ignored |

## Quality gate (ADR-009 D6)

Si en los 3 días posteriores al deploy en VPS el dashboard **no se mira ≥2x/día**,
congelar O13.3-O13.5 y revertir el systemd unit. La métrica vive en Redis
(`mc:views:{date}`) y se incrementa desde un middleware que se agregará
en el primer commit post-deploy.

## Deploy (VPS)

Ver `infra/systemd/mission-control.service.template`. NO se deploya automáticamente
desde este commit — David debe aprobar y delegar a Copilot-VPS vía task en
`.agents/tasks/`.
