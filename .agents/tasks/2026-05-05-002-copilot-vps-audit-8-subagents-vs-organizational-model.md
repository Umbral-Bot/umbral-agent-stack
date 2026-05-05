# 2026-05-05-002 — Auditoría runtime de los 8 subagents vs modelo organizacional Rick

- **Created**: 2026-05-05
- **Assigned to**: copilot-vps (acceso SSH real a VPS Hostinger)
- **Status**: ready
- **Priority**: P1 (bloquea Ola 1 del modelo organizacional)
- **Depends on**: ninguna
- **Blocks**: Ola 1 fundamentos (re-prompt de Rick + archivar/promover subagents).

## Contexto

El doc `notion-governance/docs/architecture/15-rick-organizational-model.md` (commit `7a11af7` en `main` de `notion-governance`) define un modelo de Rick CEO + 6 gerencias. La §5 hace un mapeo **conceptual** de los 8 subagents existentes en `~/.openclaw/agents/` contra ese modelo, asumiendo que la mayoría son placeholders sin contenido. Antes de archivar o promover nada, hay que **verificar runtime** qué tiene cada uno realmente.

## Hipótesis a verificar

Según §5 del doc:

| Subagent | Hipótesis | Acción propuesta si se confirma |
|---|---|---|
| `rick-orchestrator` | Vacío / redundante con `main`. | Archivar. |
| `rick-delivery` | Concepto ambiguo, sin uso. | Archivar o reconvertir. |
| `rick-qa` | No tiene contenido de gerencia, sí podría tener lógica QA. | Reconvertir a skill `qa-runner`. |
| `rick-tracker` | Trackea experiencia, no es gerencia. | Reconvertir a skill `experience-tracker` dentro de Mejora Continua. |
| `rick-ops` | Health/ops, no es gerencia. | Reconvertir a skills (`ops-runner`, `health-checker`) dentro de Desarrollo. |
| `rick-communication-director` | Semilla válida de gerencia. | Promover a Gerencia de Comunicación. |
| `rick-linkedin-writer` | Skill puntual mal envuelto en agent. | Reconvertir a skill `linkedin-writer` dentro de Marketing. |
| `improvement-supervisor` | Semilla válida de gerencia. | Promover a Gerencia de Mejora Continua. |

## Qué hay que hacer (en VPS)

Para **cada uno** de los 8 directorios bajo `~/.openclaw/agents/`:

```bash
ssh rick@<vps>
cd ~/.openclaw/agents/<agent_id>
ls -la                          # estructura completa
ls -la agent/ 2>/dev/null       # subdir agent si existe
find . -type f -name "*.md" -exec wc -l {} \;   # docs
find . -type f -name "*.json" -exec ls -la {} \;
find . -type f -name "*.yaml" -o -name "*.yml" 2>/dev/null
# Buscar prompt real:
cat agent/*.md 2>/dev/null | head -200
cat *.md 2>/dev/null | head -200
# Buscar config:
cat agent/auth.json 2>/dev/null | jq '.'
# Buscar referencias en openclaw.json:
jq --arg id "<agent_id>" '.agents[] | select(.id == $id)' ~/.openclaw/openclaw.json
```

Y también:

1. **Uso histórico**: revisar logs/sessions/trajectories de últimos 30 días buscando si **alguno** de estos 8 fue invocado:

   ```bash
   sudo journalctl -u openclaw-gateway --since '30 days ago' | grep -iE "(rick-orchestrator|rick-delivery|rick-qa|rick-tracker|rick-ops|rick-communication-director|rick-linkedin-writer|improvement-supervisor)"
   # Sessions JSONL:
   find ~/.openclaw/sessions -name "*.jsonl" -mtime -30 | xargs grep -lE "<agent_id>" 2>/dev/null
   # Trajectories:
   find ~/.openclaw/trajectories -name "*.json" -mtime -30 | xargs grep -lE "<agent_id>" 2>/dev/null
   ```

2. **Referencias entre subagents**: `grep -r "<agent_id>" ~/.openclaw/agents/` (qué agente menciona a otro).

## Output esperado (entregable)

Append al final de **este mismo archivo** una sección `## Resultado auditoría 2026-05-05`, con una tabla por agente:

| Agent ID | ¿Tiene system prompt real? (path + first 5 lines) | ¿Tiene skills propias? | ¿Tiene config no-default? | Invocaciones últimos 30d | Recomendación final | Justificación |

Y al final de la tabla, **clasificación final**:

- **Archivar inmediatamente** (mover a `~/.openclaw/agents/_archive/`): lista.
- **Promover a Gerencia** (mantener + completar charter después): lista.
- **Reconvertir a skill** (extraer lógica útil + borrar agent): lista, indicando skill destino y gerencia destino.
- **Caso ambiguo / requiere decisión humana**: lista con recomendación opcional.

## Reglas operativas

1. **NO modificar nada** en esta task. Es read-only audit. Cualquier cambio (archivar, mover, borrar) viene en task posterior con aprobación de David.
2. **NO inventar uso** si los logs no lo muestran. "0 invocaciones" es resultado válido.
3. **Respetar memoria cross-repo**: este archivo se commitea a `umbral-agent-stack/main` para que Copilot Chat lo vea de vuelta.
4. **Push obligatorio** cuando termines: `git add` + commit + `git push origin main`.
5. **Si encontrás secretos** en algún archivo de agent → reportar **path + tipo de secreto**, NUNCA pegar el valor en el output.

## Referencias

- Doc del modelo: `notion-governance/docs/architecture/15-rick-organizational-model.md` (commit `7a11af7`).
- Task que originó esto: `2026-05-05-001-copilot-vps-telegram-bot-bind-o15.md` (HOLD por falta de prefix routing en OC 5.3-1).
- Baseline OpenClaw: `2026.5.3-1 (2eae30e)`, `~/.openclaw/openclaw.json` md5 `44be041f8650197b6e00c35034d96282`.

## Resultado auditoría 2026-05-05

_Pendiente — completar por copilot-vps._
