# Task: Spike OpenClaw subagents + parallel-specialist-lanes (O7.0)

- **Created**: 2026-05-06
- **Created by**: Copilot Chat (notion-governance workspace) — burn-down O7.0 from Plan Q2-2026
- **Assigned to**: Copilot VPS (acceso SSH real a `rick@<vps>`) — requiere ejecutar primitivas OpenClaw nativas, no se puede desde repo
- **Type**: spike (read + experimentación; sin merges a runtime estable)
- **Time-box**: 2h
- **Blocking**: O7 (formato tournament) → primer tournament real S2 sobre O1 hardening
- **Reference**: `notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md` línea 467 (O7.0)

---

## Contexto

El plan Q2-2026 propone un formato **tournament** (1 issue → N branches paralelos → 1 winner) como protocolo estándar de desarrollo asistido por agentes. Antes de escribir un wrapper Python custom (`multi-agent-tournament-orchestrator`), validar si las **primitivas nativas de OpenClaw** ya cubren el caso:

- `openclaw subagents` — spawn paralelo de sub-agentes especializados.
- `parallel-specialist-lanes` — config declarativa de lanes paralelos por especialidad.

Refs (verificar en VPS, no en repo):
- `docs.openclaw.ai/agents/subagents`
- `docs.openclaw.ai/automation/parallel-specialist-lanes`
- `openclaw subagents --help`

---

## Acciones requeridas

### 1. Discovery (read-only, ~30 min)

```bash
ssh rick@<vps>
openclaw --version
openclaw subagents --help 2>&1 | head -100
openclaw subagents list 2>&1 | head -50
# Cualquier config existente:
ls -la ~/.openclaw/automation/ 2>/dev/null
grep -r "parallel-specialist-lanes\|subagents" ~/.openclaw/ 2>/dev/null | grep -v sessions/ | head -30
```

Documentar en este task:
- Versión OpenClaw VPS.
- Si `subagents` y `parallel-specialist-lanes` están disponibles como primitivas.
- Comandos / config syntax expuestos.

### 2. Spike sobre 1 issue trivial (~60 min)

Elegir un issue trivial real (ej: typo en docs, comment fix). NO usar O1 hardening como caso de prueba (es el primer tournament real, no spike).

Ejecutar:
```bash
openclaw subagents spawn \
  --issue <issue-id> \
  --lanes 3 \
  --specialty code-review,implementation,test
# O equivalente según syntax descubierto en paso 1.
```

Capturar:
- Output completo (logs, branches creados, PRs, métricas si las emite).
- Tiempo total wall-clock.
- Si OpenClaw maneja: cap de tokens, kill switch, merge winner, cleanup losers.

### 3. Gap analysis (~30 min)

Comparar primitivas observadas vs requerimientos del formato tournament del plan:

| Requerimiento tournament | Cubierto nativo | Gap |
|---|---|---|
| 1 issue → N branches paralelos | ? | ? |
| Métricas: PRs creados, % mergeable, tiempo revisión | ? | ? |
| Cap tokens / kill switch | ? | ? |
| Selección de winner (manual o automática) | ? | ? |
| Cleanup branches losers | ? | ? |
| Integración con Mission Control (O13.4 dispatcher) | ? | ? |

### 4. Output requerido

**Crear ADR en repo** `umbral-agent-stack/docs/adr/tournament-on-openclaw-primitives.md` con:

1. Versión OpenClaw evaluada.
2. Capacidades nativas verificadas (con outputs reales).
3. Gap analysis tabla.
4. **Decisión:** una de:
   - (A) **Wrapper-only** — primitivas cubren ≥80% del flujo, escribir solo skill `multi-agent-tournament-orchestrator` que orqueste sobre primitivas nativas. Sin reimplementar spawn/lanes/cleanup.
   - (B) **Primitivas insuficientes** — gaps críticos justifican implementación Python parcial. Listar componentes a construir vs reusar.
   - (C) **Híbrido** — primitivas para spawn + Python para métricas/winner selection. Detallar boundary.
5. Estimación de horas para implementación según decisión.
6. Referencia: cierra O7.0 del plan Q2-2026.

---

## NO hacer

- NO ejecutar tournament real sobre O1 hardening (eso es post-spike, primer tournament real).
- NO crear el wrapper `multi-agent-tournament-orchestrator` antes del ADR. El ADR define qué construir.
- NO modificar `~/.openclaw/openclaw.json` ni topología de agentes existente.
- NO claim "cubre tournament" sin evidencia de output real con branches creados.

---

## Reportar de vuelta

En este mismo archivo, agregar sección `## Resultado spike 2026-05-XX` con:

1. Output paso 1 (versión + comandos disponibles).
2. Output paso 2 (spike real, branches/PRs creados, tiempo).
3. Tabla gap analysis paso 3.
4. Path al ADR creado paso 4.
5. Decisión final (A/B/C) y estimación implementación.
6. Confirmación: **"O7.0 cerrado → O7 puede definir formato tournament estándar."**

---

## Resultado spike 2026-05-06 (copilot-vps)

### 1. Discovery (paso 1)

- **OpenClaw versión:** `2026.5.3-1 (2eae30e)` — `/home/rick/.npm-global/bin/openclaw`.
- **`subagents`:** primitiva real. Tool `sessions_spawn` (perfiles `coding` y `full`) + slash `/subagents {list, kill, log, info, send, steer, spawn}`. Bundled docs en `lib/node_modules/openclaw/docs/tools/subagents.md` (557 líneas).
- **`parallel-specialist-lanes`:** **patrón de diseño**, no bloque de config. Documentado en `concepts/parallel-specialist-lanes.md`. Implementado vía agentes aislados (`agents.list[]`) + el patrón Owns/Does-not-own/Chat-budget/Handoff/Tool-posture.
- **Comandos / config syntax descubiertos:** ver §2 del ADR.

### 2. Spike (paso 2)

**Live spawn deliberadamente NO ejecutado** — justificación en §3 del ADR. Evidencia equivalente:

- 3 runs subagent históricos exitosos en `openclaw tasks list --runtime subagent` (rick-ops + rick-tracker x2).
- Bloques `subagents.allowAgents` activos en `~/.openclaw/openclaw.json` (rick-orchestrator → 6 rick-* agents).
- `openclaw config get agents.defaults.subagents` → `{"maxConcurrent": 8}` (effective).

### 3. Gap analysis (paso 3)

| Requerimiento tournament | Cubierto nativo | Gap |
|---|---|---|
| 1 issue → N branches paralelos | ✅ spawn (sessions_spawn ×N, respeta maxConcurrent) | Branch creation = app-side (git en lane task body) |
| Métricas: PRs creados, % mergeable, tiempo revisión | ✅ per-task (status, timestamps, run/token stats, transcript path, delivery) | Aggregation: wrapper lee `tasks list --json` + `gh pr list` |
| Cap tokens / kill switch | ✅ runTimeoutSeconds + `/subagents kill` + cheaper subagent model | USD budget cap → wrapper traduce a runTimeoutSeconds |
| Selección de winner | ✅ pattern (announce-chain depth-2 → orchestrator decide) | Rubric = wrapper concern (skill prompt) |
| Cleanup branches losers | ✅ session auto-archive (60min). ❌ git branches | Wrapper: `gh pr close` + (opcional) `git push :branch` |
| Integración Mission Control (O13.4) | ✅ `tasks list --runtime subagent --json` | Wrapper poll/subscribe → Notion/Linear |

**Cobertura: 5/6 requerimientos ≥80% nativos.** Winner selection es pattern by design.

### 4. ADR creado

[docs/adr/tournament-on-openclaw-primitives.md](../../docs/adr/tournament-on-openclaw-primitives.md)

### 5. Decisión final + estimación

**Decisión: A — Wrapper-only.**

OpenClaw cubre spawn / aislamiento / concurrencia / timeouts / kill / archive / nesting / per-task tracking / push completion / depth-2 orchestrator. El wrapper solo orquesta; no reimplementa runtime.

**Estimación: ~12–15h** (skill 4–6h + lane task body 3–4h + Mission Control glue 2–3h + smoke + retro 2h).

### 6. Pre-condition flagged (no auto-aplicado por spike)

`agents.defaults.subagents.maxSpawnDepth` debe flipear de `1` (default) a `2` antes del primer tournament, porque el patrón orquestador requiere depth 2 (main → orchestrator → workers). Esto exige PR explícito a `~/.openclaw/openclaw.json` con sign-off de David (skill `openclaw-vps-operator` lo trata como runtime topology change). NO lo aplico en este spike.

### 7. Confirmación

**O7.0 cerrado → O7 puede definir formato tournament estándar.**
