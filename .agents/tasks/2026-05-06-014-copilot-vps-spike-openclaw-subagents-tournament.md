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
