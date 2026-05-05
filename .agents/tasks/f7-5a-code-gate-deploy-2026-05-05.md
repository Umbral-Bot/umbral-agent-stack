---
id: "2026-05-05-f7-5a-code-gate-deploy"
title: "F7.5A Copilot CLI code gate deploy + runtime reality check"
status: done
assigned_to: copilot-vps
created_by: codex
priority: high
sprint: F7.5
created_at: 2026-05-05T00:00:00-04:00
updated_at: 2026-05-05T22:47:46Z
verdict: verde
verdict_reason: "L5=True deployed, L3 still closed, probe=execute_flag_off_dry_run, real_execution_implemented=true"
---

## Objetivo

Desplegar en la VPS el cambio ya mergeado a `main` que abre solo el gate L5
(`_REAL_EXECUTION_IMPLEMENTED=True`) y verificar runtime que el worker sigue
bloqueado por L3 (`RICK_COPILOT_CLI_EXECUTE=false`).

El resultado esperado NO es un run productivo. El resultado esperado es una
transición de evidencia:

```text
policy.real_execution_implemented: false -> true
decision: execute_flag_off_dry_run
execute_enabled: false
would_run: false
egress_activated: false
```

## Bootstrap obligatorio

```bash
cd ~/umbral-agent-stack
git checkout main
git pull --ff-only origin main
```

## Contexto

- PR #291 mergeado a `main`: F7.5A abre solo L5 en código.
- `worker/tasks/copilot_cli.py` debe contener `_REAL_EXECUTION_IMPLEMENTED = True`.
- L3 debe permanecer cerrado en la VPS: `RICK_COPILOT_CLI_EXECUTE=false`.
- L4 debe permanecer cerrado: `copilot_cli.egress.activated=false`; no tabla nft
  persistente ni Docker network copilot.
- Esta task es solo deploy + reality check. No abre gates productivos.

## Reglas duras

- NO abrir L3. No editar `RICK_COPILOT_CLI_EXECUTE`.
- NO activar L4. No editar `copilot_cli.egress.activated`.
- NO aplicar nft. NO crear Docker network.
- NO ejecutar Copilot real. NO Copilot HTTPS.
- Secret-output-guard: nunca imprimir tokens. Solo reportar nombres presentes
  como `present_by_name`.
- Si hay drift entre repo y proceso vivo, reportar `"repo dice X / VPS muestra Y"`
  y detener con verdict `rojo` o `amarillo` según impacto.

## Pasos

### O1 — Preflight repo + worker

Ejecutar y capturar:

```bash
cd ~/umbral-agent-stack
git branch --show-current
git rev-parse HEAD
git status --short
systemctl --user show umbral-worker.service -p MainPID -p ActiveState -p SubState
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8088/health
```

### O2 — Verificar gates antes de restart

Verificar con formato `repo dice X / VPS muestra Y`:

```bash
PID=$(systemctl --user show umbral-worker.service -p MainPID --value)

echo "L1/L3 process env names+safe booleans:"
tr '\0' '\n' < /proc/$PID/environ \
  | awk -F= '
      $1=="RICK_COPILOT_CLI_ENABLED" {print "process RICK_COPILOT_CLI_ENABLED="$2}
      $1=="RICK_COPILOT_CLI_EXECUTE" {print "process RICK_COPILOT_CLI_EXECUTE="$2}
      $1=="COPILOT_GITHUB_TOKEN" {print "process COPILOT_GITHUB_TOKEN=present_by_name"}
      $1=="WORKER_TOKEN" {print "process WORKER_TOKEN=present_by_name"}
    '

echo "L1/L3 envfile safe booleans:"
grep -E '^RICK_COPILOT_CLI_(ENABLED|EXECUTE)=' /home/rick/.config/openclaw/copilot-cli.env

echo "L2/L4 repo policy:"
grep -A12 '^copilot_cli:' config/tool_policy.yaml | head -15
grep -A8 '^  egress:' config/tool_policy.yaml | head -10

echo "L5 code gate:"
grep -n '^_REAL_EXECUTION_IMPLEMENTED' worker/tasks/copilot_cli.py

echo "live egress state:"
sudo nft list table inet copilot_egress 2>/dev/null && echo "COPILOT_NFT_TABLE_PRESENT" || echo "no copilot nft table"
docker network ls 2>/dev/null | grep -i copilot || echo "no copilot docker network"
```

Expected before restart:

- Repo `worker/tasks/copilot_cli.py`: `_REAL_EXECUTION_IMPLEMENTED = True`.
- Process may still show old code until restart; report honestly if so.
- Envfile/process L3 must be `false`.

### O3 — Restart once to load code

```bash
OLD_PID=$(systemctl --user show umbral-worker.service -p MainPID --value)
systemctl --user restart umbral-worker.service
sleep 3
NEW_PID=$(systemctl --user show umbral-worker.service -p MainPID --value)
echo "OLD_PID=$OLD_PID"
echo "NEW_PID=$NEW_PID"
systemctl --user show umbral-worker.service -p ActiveState -p SubState
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8088/health
```

Acceptance:

- PID changed exactly once.
- Worker is `active/running`.
- `/health` returns HTTP 200.

### O4 — Runtime probe after restart

Use the worker token without printing it:

```bash
WTOKEN=$(grep '^WORKER_TOKEN=' /home/rick/.config/openclaw/env | cut -d= -f2-)

curl -s -X POST http://127.0.0.1:8088/run \
  -H "Authorization: Bearer $WTOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task":"copilot_cli.run",
    "input":{
      "mission":"research",
      "prompt":"F7.5A code gate deploy probe",
      "requested_operations":["read_repo"],
      "repo_path":"/home/rick/umbral-agent-stack",
      "dry_run":true,
      "metadata":{"phase":"F7.5A","agent":"copilot-vps"}
    }
  }' | tee /tmp/f7-5a-code-gate-probe.json | python3 -m json.tool
```

Expected response:

```json
{
  "result": {
    "would_run": false,
    "decision": "execute_flag_off_dry_run",
    "policy": {
      "env_enabled": true,
      "policy_enabled": true,
      "execute_enabled": false,
      "real_execution_implemented": true
    },
    "egress_activated": false
  }
}
```

### O5 — Side-effect checks

```bash
sudo nft list table inet copilot_egress 2>/dev/null && echo "COPILOT_NFT_TABLE_PRESENT_BAD" || echo "no copilot nft table"
docker network ls 2>/dev/null | grep -i copilot && echo "COPILOT_DOCKER_NETWORK_PRESENT_BAD" || echo "no copilot docker network"

LATEST_AUDIT=$(find reports/copilot-cli -type f -name '*.jsonl' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)
echo "latest_audit=$LATEST_AUDIT"
if [ -n "$LATEST_AUDIT" ]; then
  grep -qE 'ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|ghs_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{30,}' "$LATEST_AUDIT" \
    && echo "TOKEN_PATTERN_FOUND_BAD" || echo "audit token scan: clean"
fi
```

Expected:

- No nft table.
- No Docker copilot network.
- Audit token scan clean.
- No Copilot HTTPS or subprocess evidence.

## Output requerido

Crear:

```text
reports/copilot-cli/f7-5a-code-gate-deploy-2026-05-05.md
```

Debe incluir:

- verdict: `verde` si L5 true + L3 false + probe `execute_flag_off_dry_run`;
  `amarillo` si hay drift no peligroso; `rojo` si algo abre ejecución o hay leak.
- HEAD, OLD_PID, NEW_PID, health.
- Gate matrix `repo dice X / VPS muestra Y`.
- Probe JSON resumido con campos: `decision`, `would_run`,
  `execute_enabled`, `real_execution_implemented`, `egress_activated`.
- Side-effect checks.
- Tokens/costo/run fields:
  - `batch_id: n/a`
  - `agent_id: n/a`
  - `mission_run_id: <del probe si existe>`
  - `tokens: 0 / n/a`
  - `cost_usd: 0 / n/a`
  - `artifacts: n/a`

## Branch / PR

Crear branch:

```bash
rick/f7-5a-code-gate-deploy-2026-05-05
```

Commit + push + PR a `main` con Codex como reviewer.

## Criterios de aceptación

- [ ] `main` en VPS contiene `_REAL_EXECUTION_IMPLEMENTED = True`.
- [ ] Worker reiniciado una vez y `/health` 200.
- [ ] L3 sigue `false` en envfile y proceso vivo.
- [ ] Probe retorna `execute_flag_off_dry_run`.
- [ ] Probe muestra `real_execution_implemented=true`.
- [ ] Probe muestra `execute_enabled=false`.
- [ ] `would_run=false`.
- [ ] `egress_activated=false`.
- [ ] No nft table persistente.
- [ ] No Docker network copilot.
- [ ] Secret scan del audit/report limpio.
- [ ] PR abierto con evidencia completa.

## Log

### codex 2026-05-05

Task creada después de mergear PR #291 (`[F7.5A] Copilot CLI — open code gate only`).
Queda lista para ejecución por Copilot-VPS. Codex no ejecutó runtime VPS.

### copilot-vps 2026-05-05T22:47:46Z

Ejecutado bootstrap, pull `--ff-only` → HEAD `4b4b70a`.
VPS Reality Check aplicado. L5 verificado `True` en disco antes del restart.

O3: restart único PID `1418206 → 1438752`, health HTTP 200.
O4: probe `copilot_cli.run` → `execute_flag_off_dry_run`, `real_execution_implemented=true`,
`execute_enabled=false`, `would_run=false`, `egress_activated=false`.
O5: no nft table, no Docker network, audit token scan clean.

**Verdict:** 🟢 VERDE. L5 abierto en producción. L3 sigue cerrado.
Report: `reports/copilot-cli/f7-5a-code-gate-deploy-2026-05-05.md`
