# Copilot handoff prompts (Windows + VPS)

Copy-paste blocks for David. **Cursor pushes `main` before VPS prompts.**

Last updated: 2026-06-02 (post G-D5.2 closeout + GCP hygiene)

---

## Estado

| Hilo | Superficie | Estado |
|---|---|---|
| A–E, F, G, I | varios | ✅ Cerrados |
| **L** | Copilot-VPS | ✅ **G_D52_VPS_CLOSEOUT_OK** (task 015) |
| **M** | Copilot Windows | 🟡 PR [#438](https://github.com/Umbral-Bot/umbral-agent-stack/pull/438) OPEN — merge |
| **N** | Notion / governance | 🟡 §6 en repo; falta página live Gobernanza Notion |
| **O** | Copilot-VPS | 🔴 **Siguiente** — Calendar E2E task 016 |
| **P** | Copilot Windows | 🟡 Merge PR 438 + post-merge checklist |
| H, J, K | opcional | 🟡 backlog |

**VPS env:** **NO re-patch.** Client `285813488732-ij582…` (Rick OpenClaw), secret suffix `LDVA`, audit 7/7 SET + smoke PASS. Borrar clients legacy en GCP Rick **no** cambia env VPS.

Trazabilidad: `~/.coord-ag-evidence/G-D5.2/traceability-report.md`

---

## Thread O — Copilot-VPS · Calendar E2E (task 016) 🔴 SIGUIENTE

**Dónde:** Copilot-VPS (SSH). Read-only salvo que David autorice evento prueba.

```
Sos Copilot-VPS. Gate Calendar post G-D5.2 (ADR-16 D6).

Lee:
  ~/umbral-agent-stack/.agents/tasks/2026-06-01-016-copilot-vps-gd52-calendar-e2e.md
  ~/.coord-ag-evidence/G-D5.2/traceability-report.md

Preflight:
  cd ~/umbral-agent-stack && git pull --ff-only origin main && echo TASK_FILE_OK

NO tocar ~/.config/openclaw/env — ya Rick OpenClaw; audit PASS; no re-OAuth.

Ejecutá:
  bash scripts/vps/smoke-gd52-oauth.sh
  curl worker list_events con calendar_id=david.a.moreira.m@gmail.com (ver task 016)
  Guardar JSON en ~/.coord-ag-evidence/G-D5.2/calendar-david-primary-list.json

PASS si inner_ok=True sobre calendar_id David (lista vacía OK).
NO crear eventos salvo "autorizo evento prueba" de David.

VEREDICTO: G_D52_CALENDAR_E2E_OK
Actualizá Log task 016. NO merge PRs.
```

---

## Thread P — Copilot Windows · merge PR 438 + sync

**Dónde:** Copilot Chat Windows (gh CLI).

```
Sos Copilot Windows. Cierre docs G-D5.2.

1. Revisá PR https://github.com/Umbral-Bot/umbral-agent-stack/pull/438
   (docs/35-gmail + docs/35-calendar → scopes ADR-16)
2. Si David autoriza merge en este mensaje → gh pr merge 438 --repo Umbral-Bot/umbral-agent-stack --squash
3. Post-merge: avisá a Copilot-VPS que haga git pull en ~/umbral-agent-stack

NO tocar .env ni VPS secrets.
VEREDICTO: GD52_DOCS35_MERGED
```

---

## Thread N — Notion / governance · §6 live

**Dónde:** Cursor o notion-governance-expert (Notion MCP). Repo ya tiene fila 2026-06-01 en ADR-16 §6.

```
Actualizar página live Gobernanza Notion con fila G-D5.2 (re-OAuth Rick OpenClaw, enforcement scopes, no relajación).
Fuente: notion-governance/docs/architecture/16-multichannel-rick-channels.md §6 fila 2026-06-01.
NO duplicar Umbral-bot / Rick legacy GCP Rick.
VEREDICTO: ADR16_LIVE_LOG_OK
```

---

## Thread L — G-D5.2 closeout (CERRADO)

VEREDICTO: **G_D52_VPS_CLOSEOUT_OK** — task 015 done. No repetir salvo smoke FAIL.

---

## Thread M — docs/35 ADR (histórico → PR 438)

VEREDICTO: **GD52_DOCS35_ALIGN_PLAN** — PR #438. Seguir en Thread P para merge.

---

## Thread H — worktree D3.1 cleanup (opcional)

```
Sos Copilot-VPS. Read-only salvo "autorizo remove worktree".
  ~/umbral-agent-stack/.agents/tasks/2026-06-01-013-copilot-vps-d31-worktree-cleanup.md
VEREDICTO: D31_WORKTREE_CLEANUP_OK
```

---

## Cerrados — no repetir

- G-D5.1 → G_D51_VPS_AUDIT_OK
- G-D5.2 re-OAuth runtime → Rick OpenClaw en VPS
- Consent legacy Rick Calendar (cuenta Rick) → revocado
- GCP Rick legacy clients Rick Gmail / Rick Calendar Playground → eliminados
- Decisión OAuth scope → **B** re-OAuth ADR

## Orden sugerido ahora

1. **Copilot-VPS** → Thread O (Calendar E2E)
2. **Copilot Windows** → Thread P (merge #438)
3. **Notion** → Thread N (log live)
4. Opcional → Thread H (worktree)
