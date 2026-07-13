---
id: "2026-07-12-001"
title: "URGENTE — OpenClaw OAuth-only; Rick = gpt-5.6-sol"
status: assigned
assigned_to: copilot
created_by: cursor-notion-governance
priority: high
sprint: exec-post-diag-2026-07
created_at: 2026-07-13T01:55:00Z
updated_at: 2026-07-13T05:40:00Z
---

## Contexto previo

David pidió **urgente**:

1. Quitar **todos** los LLM de Azure AI Foundry en OpenClaw.
2. Dejar **solo ChatGPT vía OAuth**.
3. **Rick (`main`)** debe quedar en **`openai/gpt-5.6-sol`** (tier flagship OAuth; ref canónica OpenClaw 2026).

Estado documentado previo (jun-2026): todos los agentes en `azure-openai-responses/gpt-5.5` + `xhigh`.

Script: `scripts/vps/patch-openclaw-oauth-only.py` (actualizado 2026-07-13).

Antes de empezar:
```bash
cd ~/umbral-agent-stack && git pull origin main
```

## Matriz objetivo post-patch

| Agente | Modelo primary | Notas |
|---|---|---|
| **`main` (Rick)** | **`openai/gpt-5.6-sol`** | OAuth ChatGPT; fallbacks `openai/gpt-5.5`, `openai-codex/gpt-5.4` |
| `rick-orchestrator`, `rick-communication-director`, `rick-linkedin-writer` | `openai-codex/gpt-5.4` | Rol heavy |
| `rick-delivery`, `rick-qa`, `rick-ops`, `rick-tracker` | `openai-codex/gpt-5.3-codex` | Rol light; tracker mantiene `thinkingDefault: medium` |
| `agents.defaults.model` | `openai-codex/gpt-5.4` | No hereda 5.6-sol salvo agente `main` |

**Prohibido tras patch:** cualquier `azure-openai-responses/*`.

## Objetivo

1. Backup `~/.openclaw/openclaw.json`
2. Ejecutar patch OAuth-only (Rick → 5.6-sol)
3. `openclaw doctor --fix` (migra refs legacy `openai-codex/*` si aplica)
4. Comentar claves Foundry en env sin borrarlas
5. Restart gateway + probe OAuth
6. Smoke Rick con modelo 5.6-sol

## Procedimiento mínimo

```bash
cd ~/umbral-agent-stack && git pull origin main

# 1) Estado previo
openclaw models list | head -50
python3 - <<'PY'
import json
from pathlib import Path
p = Path.home()/".openclaw"/"openclaw.json"
d = json.loads(p.read_text())
print("default", d.get("agents",{}).get("defaults",{}).get("model"))
print("providers", list(d.get("models",{}).get("providers",{}).keys()))
for a in d.get("agents",{}).get("list",[]):
    print(a.get("id"), a.get("model"))
PY

# 2) Patch
python3 ~/umbral-agent-stack/scripts/vps/patch-openclaw-oauth-only.py

# 3) Doctor (refs canónicas openai/* + auth profiles)
openclaw doctor --fix

# 4) Env — comentar Foundry (no delete)
for f in ~/.config/openclaw/env ~/.openclaw/.env; do
  [ -f "$f" ] && sed -i.bak.oauth 's/^\(AZURE_OPENAI_\|KIMI_AZURE_API_KEY\)/# oauth-only-disabled &/' "$f" && echo "patched $f"
done

# 5) Restart + probe
systemctl --user restart openclaw-gateway.service
sleep 3
systemctl --user is-active openclaw-gateway.service
openclaw models list | head -50
openclaw models status --probe-provider openai

# 6) Verificar Rick = 5.6-sol
python3 - <<'PY'
import json
from pathlib import Path
d = json.loads((Path.home()/".openclaw"/"openclaw.json").read_text())
main = next(a for a in d["agents"]["list"] if a["id"]=="main")
print("main_model", main.get("model"))
PY

# 7) Smoke
openclaw agent --agent main --model openai/gpt-5.6-sol --message "Responde solo: PASS-GPT56-SOL" --timeout 180
```

### Si OAuth o GPT-5.6 fallan

```bash
# Re-auth ChatGPT OAuth
openclaw models auth login --provider openai
# o: openclaw onboard --auth-choice openai

openclaw models status --probe-provider openai

# Si la cuenta NO tiene preview GPT-5.6 (error upstream de acceso):
# reportar a David — fallback temporal acordado: openai/gpt-5.5 en main
# NO reactivar Foundry sin autorización explícita.
```

## Criterios de aceptación

- [ ] `models.providers` **no** contiene `azure-openai-responses`
- [ ] `main.model.primary` = **`openai/gpt-5.6-sol`**
- [ ] Resto de agentes: solo refs `openai/*` o `openai-codex/*` (sin Foundry)
- [ ] Ningún fallback contiene `azure-openai-responses/`
- [ ] `openclaw models status --probe-provider openai` → OK
- [ ] Smoke `PASS-GPT56-SOL` desde `main` con `--model openai/gpt-5.6-sol`
- [ ] Gateway `active` tras restart
- [ ] Log separa **Repo dice X** vs **VPS muestra Y**

## Antipatrones que esta tarea prohíbe

- Declarar fixed sin verificar `main.model.primary` en JSON post-patch
- Poner gpt-5.6-sol en todos los agentes (solo Rick/main)
- Borrar permanentemente claves env (solo comentar)
- Re-ejecutar `patch-openclaw-gpt55-xhigh.py`

## Rollback

```bash
cp -a ~/.openclaw/openclaw.json.bak.oauth-only.* ~/.openclaw/openclaw.json
# restaurar .env.bak.oauth si aplica
systemctl --user restart openclaw-gateway.service
```

## Log

- 2026-07-13 — Cursor creó script + tarea tras solicitud urgente David.
- 2026-07-13 — David: Rick (`main`) = `openai/gpt-5.6-sol`; matriz role-tiered para el resto.
