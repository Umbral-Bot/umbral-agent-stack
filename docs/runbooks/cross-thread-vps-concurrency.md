# Cross-thread VPS concurrency policy (2026-05-10)

**Owner:** Copilot Chat (autonomous mandate)
**Aplica a:** Cualquier hilo que delegue trabajo a Copilot-VPS, Codex VPS, Claude Code, o
cualquier agente que opere sobre `~/umbral-agent-stack` en la VPS Hostinger.
**Status:** ACTIVA. Vinculante para todos los hilos cross-IDE.

## Problema que resuelve

Tres frentes activos pueden tocar la misma VPS y el mismo repo `~/umbral-agent-stack`:

1. **Coordinador O16.2** (este hilo) — branches `coord-o16/*`, foco AECO KB pipeline.
2. **Automatización RRSS Wave 2A** (otro coordinador) — branches `rrss-wave2a/*`, foco
   editorial pipeline + `scripts/discovery/stage7_5_*`.
3. **Operación Granola/Notion writer** (operacional, no es hilo de cambio) — corre cron
   y systemd units; NO debe ser interrumpido.

Sin política, los riesgos son:

- Dos hilos hacen `git pull --ff-only origin main` en la VPS al mismo tiempo y compiten
  por el lock del repo.
- Hilo A redeploya un job ACA mientras hilo B está leyendo logs del job anterior.
- Branch checkout cruzado: Copilot-VPS deja la VPS en `rrss-wave2a/foo` y luego un
  prompt de O16.2 asume `main` y commitea a la branch equivocada (observado 2026-05-05).
- Cron del Granola writer falla porque otro hilo apagó el container OpenClaw.

## Reglas duras

### R1 — Branch prefix obligatorio

Todo prompt VPS de un hilo coordinador debe declarar su prefix y NO tocar prefijos ajenos:

| Hilo | Prefix permitido | Prohibido leer/escribir |
|---|---|---|
| Coordinador O16.2 | `coord-o16/*` | `rrss-wave2a/*`, `copilot-vps/ola-*` |
| RRSS Wave 2A | `rrss-wave2a/*` | `coord-o16/*` |
| Operación (no-coord) | n/a | n/a — solo lectura |

### R2 — Archivos forbidden por hilo

Lista explícita de archivos que cada hilo NO puede tocar:

**Coordinador O16.2 NO toca:**
- `scripts/discovery/stage7_5_*`
- `scripts/discovery/lib/variants.py`
- `docs/editorial-pipeline/*`
- Issues #401-#406 (RRSS)
- Cualquier path bajo `notion-governance/` salvo lectura.

**RRSS Wave 2A NO toca:**
- `scripts/aeco-kb/*`
- `infra/azure/aeco-kb-pipeline.bicep`
- `infra/docker/aeco-*`
- `docs/audits/*o16-2*`

### R3 — Runtime VPS no-overlap windows

Si un hilo va a ejecutar acción runtime que afecta servicios compartidos (OpenClaw
gateway, worker FastAPI, dispatcher, cron Granola), debe declarar la ventana en el
prompt y NO solapar con otros hilos.

Servicios compartidos críticos:
- `umbral-worker` (FastAPI :8088) — usado por dispatcher + Granola writer
- `openclaw-dispatcher` — control plane
- `openclaw-gateway` (npm-global :18789) — runtime OpenClaw
- Cron jobs en `scripts/vps/*-cron.sh`

Acciones que afectan compartidos:
- `systemctl --user restart umbral-worker|openclaw-dispatcher`
- `pkill openclaw` o restart del gateway
- Cualquier `docker stop/restart` sobre containers OpenClaw
- `crontab -e` o edición de cron files

Acciones aisladas (no overlap):
- `git fetch/pull` sobre branches con prefix propio
- `az deployment group create` (Azure, no VPS)
- `docker build / push` a GHCR (CPU local del host, no afecta servicios VPS)

### R4 — Checkout main explícito al inicio de todo prompt VPS

Por bug observado 2026-05-05 (VPS quedó en `rick/copilot-cli-f7-*`), todo prompt VPS
debe empezar con:

```bash
cd ~/umbral-agent-stack \
  && git fetch origin \
  && git checkout main \
  && git pull --ff-only origin main \
  && git status --short
```

Si `git status --short` no está vacío, ABORTAR y reportar al usuario antes de cualquier
otra acción.

### R5 — Sibling repos no asumir

`~/notion-governance` NO está clonado oficialmente en la VPS (verificado 2026-05-05).
Los dirs `~/notion-governance-git` y `~/notion-governance-local` son restos viejos sin
remote correcto. Si una task VPS necesita leer ese sibling:

1. Verificar token con acceso (`curl /repos/Umbral-Bot/notion-governance` espera 200).
2. Clonar limpio en `~/notion-governance` (NO usar `-git`/`-local`).
3. Pasar ruta absoluta vía flag al script.

### R6 — Reporte formato Repo dice / VPS muestra

Todo reporte de hilo VPS debe separar explícitamente:

- **Repo dice X** — lo que el código/Bicep/runbook declara
- **Azure deployed** — lo que `az resource show` confirma en runtime
- **VPS verifica Y** — lo que `journalctl`/`systemctl`/`curl` muestra en runtime

Si X ≠ Y, esa divergencia ES el hallazgo principal del reporte.

### R7 — Nunca escribir a Notion desde un hilo coordinador no-Notion

El coordinador O16.2 NO escribe a Notion (no tiene scope). Los writes a Notion los hace
solo el writer Granola operacional o un hilo coordinador notion-governance específico.

## Mailbox protocol entre hilos

Si un hilo necesita coordinación con otro hilo (ej: O16.2 necesita esperar que RRSS
termine un deploy compartido), debe dejar mensaje en `.agents/mailbox/` con:

```yaml
from: coord-o16
to: rrss-wave2a
date: 2026-05-10
type: coordination
action: wait_for
detail: "Esperar fin de deploy ACA Job stage7_5 antes de tocar CAE cae-umbral-agents-prod"
unblock_signal: "git push de rrss-wave2a/* a main + reply mailbox"
```

## Antipatrones bloqueados

- ❌ Pull en VPS sin checkout main explícito previo.
- ❌ Asumir que el repo VPS está en main porque "el último prompt lo dejó así".
- ❌ Restart de `umbral-worker` sin avisar al hilo Granola.
- ❌ Tocar archivos del prefix forbidden "porque están relacionados".
- ❌ Reportar "está OK" sin haber corrido el `Repo / Azure / VPS` triple-check.

## Rollback genérico VPS

Si cualquier prompt VPS de cualquier hilo deja la VPS en estado raro:

```bash
cd ~/umbral-agent-stack
git stash push -m "EMERGENCY-cross-thread-rollback-$(date +%s)"
git fetch origin
git checkout main
git reset --hard origin/main
systemctl --user restart umbral-worker openclaw-dispatcher
sleep 5
curl -fsS http://127.0.0.1:8088/health
journalctl --user -u umbral-worker --since "2 minutes ago" | tail -50
```

Reportar el stash key al usuario antes de descartarlo.

## Referencias

- VPS Reality Check Rule: `umbral-agent-stack/.github/copilot-instructions.md`
- Mandatory protocol after editing runtime: `.agents/skills/vps-deploy-after-edit/SKILL.md`
- Plan O16.2: [docs/audits/2026-05-10-o16-2-execution-plan.md](../audits/2026-05-10-o16-2-execution-plan.md)
- Kill list Q2: [docs/audits/2026-05-10-q2-runtime-focus-and-kill-list.md](../audits/2026-05-10-q2-runtime-focus-and-kill-list.md)
