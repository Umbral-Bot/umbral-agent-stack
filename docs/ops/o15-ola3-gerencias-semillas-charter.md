# O15 Ola 3 — Gerencias semilla (charter bundle)

- **Status:** Active (repo prompts 2026-06-01)
- **Model:** `notion-governance/docs/architecture/15-rick-organizational-model.md` §5.3, §6 Ola 3+
- **Scope:** Formalizar en ROLE las cuatro gerencias con semilla runtime + Marketing transitorio

---

## Gerencias cubiertas

| Gerencia | Agent | ROLE override | Runtime |
|---|---|---|---|
| Comunicación | `rick-communication-director` | ✅ bloque O15 | read-only / dry-run |
| Desarrollo | `rick-delivery` | ✅ bloque O15 | activo (torneo lanes) |
| Operaciones | `rick-ops` | ✅ ROLE nuevo | activo |
| Marketing (transitorio) | `rick-linkedin-writer` | ✅ bloque O15 | **PAUSED** EDITORIAL-03 |

Mejora Continua (`rick-qa`, `rick-tracker`) → Ola 2 (`docs/ops/o15-ola2-mejora-continua-charter.md`).

---

## Reglas comunes (todas las gerencias)

1. Entrada solo vía `main` o `rick-orchestrator` — bypass humano prohibido.
2. Delegaciones registrables en `~/.openclaw/trace/delegations.jsonl` cuando aplique §3.3.
3. Cierre con evidencia observable; QA cross-cutting vía `rick-qa` cuando el entregable lo requiera.
4. Escalación a David siempre vía `main`.

---

## Quality gate §3.6 (por gerencia)

| Gerencia | Carta | Skill operativa | Trigger | Caso 30d |
|---|---|---|---|---|
| Comunicación | ✅ | ✅ director-comunicacion-umbral | 🟡 bajo demanda | 🟡 editorial pipeline |
| Desarrollo | ✅ | ✅ github-ops, code-* | ✅ torneos/spawn | 🟡 D3.1+ |
| Operaciones | ✅ | ✅ openclaw-vps-operator | ✅ heartbeat/cron | ✅ runbooks vivos |
| Marketing | ✅ | ✅ linkedin-* | ⏸ pause | ⏸ EDITORIAL-03 |

---

## Próximo paso

- Ola 3.1: smoke delegación orchestrator → cada gerencia con registro en `delegations.jsonl`.
- Ola 4+: `IDENTITY.md` por gerencia solo si el ROLE no basta (hoy ROLE es suficiente).

## Referencias

- Task: `.agents/tasks/2026-06-01-007-o15-ola3-gerencias-prompts.md`
- Sync: `scripts/sync_openclaw_workspace_governance.py`
