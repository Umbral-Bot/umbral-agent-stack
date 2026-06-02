# Copilot handoff prompts (Windows + VPS)

Copy-paste blocks for David. **Cursor pushes `main` before VPS prompts.**

Last updated: 2026-06-02 (G-D5.2 hilos O/P/N cerrados; gate formal → Q; skills → Codex 018)

---

## Estado G-D5.2

| Hilo | Superficie | VEREDICTO |
|---|---|---|
| L | Copilot-VPS | ✅ G_D52_VPS_CLOSEOUT_OK (015) |
| O | Copilot-VPS | ✅ G_D52_CALENDAR_E2E_OK (016) |
| P | Copilot Windows | ✅ GD52_DOCS35_MERGED (#438 → `1187eaa9`) |
| N | Notion | ✅ ADR16_LIVE_LOG_OK |
| **Q** | Copilot-VPS | 🔴 **Siguiente** — gate closeout sync (017) |
| **R** | Codex (meta) | 🟡 O15 skills Gmail/Calendar (018) |
| H | Copilot-VPS | 🟡 opcional — worktree D3.1 (013) |

**VPS env:** NO re-patch. Client `285813488732-ij582…`, smoke PASS.

Trazabilidad: `~/.coord-ag-evidence/G-D5.2/traceability-report.md`

---

## Thread Q — Copilot-VPS · gate G-D5.2 closed (task 017) 🔴 SIGUIENTE

**Dónde:** Copilot-VPS (SSH). Read-only salvo refresh traceability script.

```
Sos Copilot-VPS. Cierre formal gate G-D5.2 post hilos O/P/N.

Lee:
  ~/umbral-agent-stack/.agents/tasks/2026-06-01-017-copilot-vps-gd52-gate-closeout-sync.md
  ~/.coord-ag-evidence/G-D5.2/traceability-report.md
  ~/.coord-ag-evidence/G-D5.2/calendar-david-primary-list.json

Preflight:
  cd ~/umbral-agent-stack && git pull --ff-only origin main && git log -1 --oneline
  # Esperado: 1187eaa9 Align Google OAuth docs with ADR scopes (#438) o posterior

NO tocar ~/.config/openclaw/env — NO re-OAuth.

Ejecutá:
  bash scripts/vps/write-gd52-traceability.sh
  bash scripts/vps/smoke-gd52-oauth.sh
  Reconfirmar list_events calendar_id=david.a.moreira.m@gmail.com (read-only)

PASS → VEREDICTO: G_D52_GATE_CLOSED
Actualizá Log task 017. NO merge PRs.
```

---

## Thread R — Codex · O15 Gmail + Calendar skills (task 018) 🟡 META

**Dónde:** Codex VS Code (modo extendido / meta). Repo: `umbral-agent-stack` o clone codex-coordinador.

```
Sos Codex con razonamiento extendido. Gate D5.1 skills router (spine Q2).

Lee task completa:
  umbral-agent-stack/.agents/tasks/2026-06-01-018-codex-o15-gmail-calendar-skills.md

ADR fuente (canónico):
  notion-governance/docs/architecture/16-multichannel-rick-channels.md
  §2.3 Gmail, §2.4 Calendar, D5 propose+confirm, D6 whitelist

Entrega: skills OpenClaw gmail-router + calendar-propose (SKILL.md + tests + runbook).
Patrón: scripts/notion/notion_mention_router.py — wrapper fino, lógica en worker.

NO VPS, NO env, NO ampliar scopes, NO outbound/eventos sin gate humano.

PR branch codex/feat-o15-gmail-calendar-skills — Copilot merge después.
VEREDICTO: O15_GMAIL_CALENDAR_SKILLS_OK
```

---

## Thread O/P/N — CERRADOS (no repetir)

| Thread | VEREDICTO |
|---|---|
| O Calendar E2E | G_D52_CALENDAR_E2E_OK |
| P merge #438 | GD52_DOCS35_MERGED |
| N Notion §6 | ADR16_LIVE_LOG_OK |

---

## Thread H — worktree D3.1 cleanup (opcional)

```
Sos Copilot-VPS. Read-only salvo "autorizo remove worktree".
  ~/umbral-agent-stack/.agents/tasks/2026-06-01-013-copilot-vps-d31-worktree-cleanup.md
VEREDICTO: D31_WORKTREE_CLEANUP_OK
```

---

## Próximo foco Q2 (post G-D5.2)

| Prioridad | Spine | Agente | Acción |
|---|---|---|---|
| 1 | D5.1 skills | Codex 018 | gmail-router + calendar-propose |
| 2 | D3.2 | Cursor/Codex | Torneo #2 (issue lane) |
| 3 | D4.1 | Copilot Windows | PR Mission Control O13.1 |
| 4 | D5.3 | Copilot-VPS | Granola soak post G-D0 |
| 5 | D6.1 | Copilot + Azure | O16.2 KB AECO smoke (deadline 26-jun) |

Friday retro **2026-06-05** — actualizar dashboard §4 spine v2.

---

## Cerrados — no repetir

- G-D5.1 → G_D51_VPS_AUDIT_OK
- G-D5.2 re-OAuth runtime → Rick OpenClaw en VPS
- Consent legacy Rick Calendar → revocado
- GCP Rick legacy clients → eliminados
- Decisión OAuth scope → **B** re-OAuth ADR
