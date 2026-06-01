# O15 Ola 2 — Gerencia Mejora Continua (charter)

- **Status:** Active (transitorio bajo `rick-orchestrator`)
- **Date:** 2026-06-01
- **Model:** `notion-governance/docs/architecture/15-rick-organizational-model.md` §6 Ola 2
- **Agents runtime:** `rick-qa`, `rick-tracker` (semillas operativas; `improvement-supervisor` sigue design-only)

---

## Propósito

Primera gerencia formal del modelo O15. Sin Mejora Continua operativa no hay manera fiable de saber si las demás gerencias funcionan.

## Scope de la gerencia

| Función | Owner agent | Evidencia |
|---|---|---|
| Validación cross-cutting | `rick-qa` | tests, diffs, smoke, editorial voice gate |
| Trazabilidad operativa | `rick-tracker` | Linear, Notion state, delegations trace |
| Retro / patrones | ambos + `main` | Friday retro Q2, `~/.openclaw/trace/delegations.jsonl` |

## Quality gate §3.6 (estado Ola 2)

| # | Condición | Estado |
|---|---|---|
| 1 | Carta de gerencia documentada | ✅ este doc + ROLE updates |
| 2 | ≥1 skill operativa real | ✅ 18+ skills QA, 20+ tracker |
| 3 | ≥1 trigger explícito | 🟡 heartbeat + delegación orchestrator; formalizar retro semanal |
| 4 | ≥1 caso de uso 30 días | 🟡 Friday retro Q2 + D3.4 post-torneos |

## Contrato con orchestrator

- Entrada: solo vía `rick-orchestrator` o `main` (validación directa mono-slice).
- Salida: reporte con evidencia observable; nunca marcar `done` sin prueba.
- Escalación a David: riesgo residual alto o criterios ambiguos.

## Próximo paso (Ola 2.1)

1. Smoke delegación → `rick-qa` con registro en `delegations.jsonl`.
2. Activar cadencia retro semanal en prompt `rick-tracker` (viernes, enlace a skill `q-friday-retro`).
3. Decidir activación `improvement-supervisor` (D5.2) vs mantener dual QA+tracker.

## Referencias

- Task: `.agents/tasks/2026-06-01-006-o15-ola2-mejora-continua-prompts.md`
- Prompts: `openclaw/workspace-agent-overrides/rick-qa/ROLE.md`, `rick-tracker/ROLE.md`
