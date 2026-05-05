# Task: cleanup `improvement-supervisor` orphan registration in `openclaw.json`

- **Created**: 2026-05-05
- **Created by**: Copilot Chat (notion-governance / umbral-agent-stack-copilot workspace)
- **Assigned to**: Copilot VPS (acceso SSH real a `rick@hostinger`)
- **Type**: runtime cleanup (read + edit, NO solo read-only)
- **Blocking**: Ola 0 del modelo organizacional (`notion-governance/docs/architecture/15-rick-organizational-model.md` §6).
- **Decision reference**: David 2026-05-05 → opción **(a)** = borrar registro huérfano del runtime, mantener `ROLE.md` design-only.

---

## Contexto

La auditoría del 2026-05-05 (task `2026-05-05-002-...md`, commit `14fb6a8`) detectó una **divergencia bloqueante** entre repo y runtime para `improvement-supervisor`:

- **Repo (`umbral-agent-stack/openclaw/workspace-agent-overrides/improvement-supervisor/ROLE.md` línea 3):** declara explícitamente *"Current status: Design-only. Not active. Not registered. There is no workspace in `openclaw.json`, no OpenClaw agent entry, and no automatic routing from `config/teams.yaml`."*
- **VPS runtime:** `~/.openclaw/openclaw.json` **sí lo tiene registrado** con `agentDir: ~/.openclaw/agents/improvement-supervisor/agent`, y ese directorio **no existe en disco** (solo existe `~/.openclaw/agents/improvement-supervisor/sessions/` con 1 sesión de test del día de la auditoría).

Esto rompe el principio governance ↔ runtime: el repo dice "design-only", el runtime tiene una entrada huérfana que el gateway intenta resolver.

David eligió la opción **(a)**: la verdad del repo (design-only) gana. La activación real de `improvement-supervisor` queda pendiente de Ola 2 del plan organizacional, y se hará siguiendo `umbral-agent-stack/docs/77-improvement-supervisor-phase6-activation-plan.md` cuando corresponda.

---

## Acciones requeridas (en orden)

### 1. Verificar estado actual (read-only)

```bash
ssh rick@<vps-host>
# Backup pre-cambio
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak.$(date +%Y%m%d-%H%M%S)

# Confirmar la entrada existe en openclaw.json
jq '.agents | map(select(.id == "improvement-supervisor"))' ~/.openclaw/openclaw.json

# Confirmar agentDir está roto
ls -la ~/.openclaw/agents/improvement-supervisor/
# Esperado: solo `sessions/` (jsonl), NO `agent/`
```

### 2. Buscar referencias adicionales antes de borrar

```bash
# Bindings, channels, allowAgents que mencionen improvement-supervisor
jq '.. | objects | select(has("agentId") and .agentId == "improvement-supervisor")' ~/.openclaw/openclaw.json
jq '.. | arrays | map(select(. == "improvement-supervisor"))' ~/.openclaw/openclaw.json | grep -v '\[\]'

# Hooks, standing-orders, taskflows
grep -r "improvement-supervisor" ~/.openclaw/ 2>/dev/null | grep -v sessions/ | grep -v ROLE.md
```

Documentar en este task qué se encontró. Si hay bindings activos → STOP, reportar antes de borrar.

### 3. Borrar la entrada (edit)

```bash
# Usar jq para borrar la entrada del array agents
jq 'del(.agents[] | select(.id == "improvement-supervisor"))' ~/.openclaw/openclaw.json > /tmp/openclaw.json.new
mv /tmp/openclaw.json.new ~/.openclaw/openclaw.json

# Validar JSON sigue siendo válido
jq empty ~/.openclaw/openclaw.json && echo "JSON válido"
```

### 4. Reload gateway y verificar

```bash
# Restart gateway (NO sudo, user unit)
systemctl --user restart openclaw-gateway
sleep 3

# Verificar que arrancó limpio
systemctl --user status openclaw-gateway --no-pager
journalctl --user -u openclaw-gateway --since "1 minute ago" | grep -iE "(error|warn|improvement-supervisor)"
# Esperado: ninguna mención de improvement-supervisor en logs nuevos.

# Verificar lista de agentes activos no incluye improvement-supervisor
openclaw status --all 2>&1 | grep -i improvement
# Esperado: vacío.
```

### 5. NO TOCAR

- `~/.openclaw/agents/improvement-supervisor/sessions/` — conservar histórico.
- Cualquier archivo del repo (`umbral-agent-stack/openclaw/workspace-agent-overrides/improvement-supervisor/ROLE.md` se mantiene design-only).

---

## Reportar de vuelta

En este mismo archivo, agregar sección `## Resultado cleanup 2026-05-05` con:

1. Output de paso 1 (estado pre-cambio).
2. Output de paso 2 (referencias adicionales encontradas, si las hubo).
3. Confirmación de paso 3 (entrada borrada, JSON válido).
4. Output relevante de paso 4 (gateway reload limpio).
5. Path del backup creado en paso 1.
6. Confirmación: **"Ola 0 desbloqueada → modelo organizacional puede proceder a Ola 1."**

---

## Anti-patrones bloqueados

- **NO** crear `~/.openclaw/agents/improvement-supervisor/agent/` para "arreglar" la entrada. La decisión de David es borrar el registro, no rellenarlo.
- **NO** tocar `ROLE.md` en el repo.
- **NO** asumir que está limpio sin verificar logs post-restart.
- **Recordar regla VPS Reality Check**: el repo describe intención, la VPS describe realidad. Acá la verdad gana = repo (design-only).
