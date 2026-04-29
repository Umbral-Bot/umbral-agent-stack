# Codegen Team — Rollout Phases

> Resumen ejecutivo del plan. Detalle completo en [docs/architecture/06-codegen-team-design.md](../architecture/06-codegen-team-design.md).

## Objetivo

Habilitar a Rick para coordinar sub-agentes que escriben código real en `umbral-bot-2`, `umbral-agent-stack` y futuros repos, con HITL gates obligatorios y aprovechando los $15K USD de créditos Azure + Copilot.

## Restricciones inviolables

1. **No merge automático.** Siempre aprobación humana vía Notion.
2. **Sandbox Docker efímero por sub-agente.** Nunca toca repo original.
3. **Branches `agent/<role>/<task-id>`.** Nunca push directo a `main`.
4. **Token PAT scoped per-task, TTL 1 h.**
5. **Network allowlist a nivel iptables**, no solo aplicación.

## Fase 1 — Walking skeleton (semana 1)

Entregables:
- [ ] Equipo `build` en `config/teams.yaml`
- [ ] 5 skills `code-*` en `openclaw/workspace-templates/skills/`
- [ ] Worker Linux desplegado en VPS (port 8089)
- [ ] Task `code.architect` registrado y funcional
- [ ] Smoke test: 1 plan generado y aprobado en Notion en < 10 min

**No incluye:** generación de código, sandbox Docker, Azure jobs.

**Riesgo:** bajo. Architect no toca código. Si falla, no hay daño.

## Fase 2 — Implementer + reviewer (semana 2)

Entregables:
- [ ] Imagen `umbral/codegen-sandbox:0.1` (local en VPS)
- [ ] Network policy iptables documentada y aplicada
- [ ] Tasks `code.implement` y `code.review`
- [ ] HITL gate 2 funcional vía Notion
- [ ] Branch protection en `umbral-bot-2` y `umbral-agent-stack`: `agent/*` requiere 1 approval
- [ ] PAT generator script (per-task, TTL 1 h)
- [ ] Smoke test: 1 PR mergeado en umbral-bot-2

**Riesgo:** medio. Sub-agente escribe código pero queda en branch + PR draft.

**Mitigación:** branch protection bloquea merge sin approval; sandbox aísla ejecución.

## Fase 3 — Azure burst + scale (semana 3-4)

Entregables:
- [ ] ACR creado, imagen sandbox publicada
- [ ] Container Apps Environment + Job template
- [ ] Task `azure.start_codegen_job` con callback al Worker
- [ ] Tasks `code.debug` y `code.scribe`
- [ ] Test de carga: 5 sub-agentes simultáneos sin race condition
- [ ] Smoke test: refactor mediano completado en 1 día

**Riesgo:** medio. Más superficie (Azure), más complejidad de observabilidad.

**Mitigación:** Container Apps Jobs son efímeros; cada job loggea a Langfuse central.

## Fase 4 — Evaluación de migración a framework (mes 2+)

Decisión post-MVP, basada en:
- Resultado del informe Perplexity
- Métricas reales de Fase 1-3
- Dolor observado en orquestación custom vs. valor diferencial de OpenClaw

Opciones a evaluar:
- Mantener todo custom
- Envolver OpenClaw como MCP server y dejar que LangGraph componga
- Reescribir supervisor `build` sobre Microsoft Agent Framework
- Híbrido: control plane custom + ejecutor framework

## Métricas de éxito (rolling)

| Métrica | Target Fase 1 | Target Fase 2 | Target Fase 3 |
|---------|---------------|---------------|---------------|
| Tareas completadas/semana | 3 | 8 | 20 |
| % sin intervención fuera de gates | 100% (solo plan) | ≥ 60% | ≥ 70% |
| Tiempo medio plan→merge | n/a | < 60 min | < 30 min |
| Costo Azure/tarea | n/a | $0 (VPS) | < $2 promedio |
| PRs revertidos por bug | 0 | ≤ 1 | ≤ 2 |
| Incidentes de seguridad | 0 | 0 | 0 |

## Kill switches

- `WORKER_TASKS_ENABLED` env var: quitar `code.*` y el Worker code-gen deja de aceptar.
- Branch protection con admin override: David puede congelar todos los `agent/*` branches.
- `OPENCLAW_BUILD_TEAM_ENABLED=false`: supervisor `build` se desactiva, Rick rechaza tareas de software.

## Cuándo escalar a David (no esperar)

1. Sub-agente intenta escribir fuera de allowlist 2+ veces.
2. PAT scope error o token leak en logs.
3. Más de 3 reintentos del mismo sub-agente.
4. Costo acumulado Azure > $50 en 24 h.
5. Cualquier respuesta del LLM que parezca prompt injection (mitigación heurística primero, alerta humana siempre).
