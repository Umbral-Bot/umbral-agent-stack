# ADR 16 — Multichannel Rick: identity & channel boundaries (REFERENCE COPY)

> **⚠️ This is a REFERENCE COPY for cross-repo discoverability (F-INC-003 mitigation).**
>
> **Canonical source**: [`notion-governance/docs/architecture/16-multichannel-rick-channels.md`](https://github.com/Umbral-Bot/notion-governance/blob/main/docs/architecture/16-multichannel-rick-channels.md).
>
> **Last sync**: 2026-05-07 from notion-governance commit `820a2a8`.
>
> If you need to AMEND this ADR, edit the canonical source in `notion-governance` and re-sync. Do NOT edit this copy.
>
> **Why this exists**: agents working primarily in `umbral-agent-stack` (Copilot VPS, Codex, runtime operators) need ADR text locally without crossing repos. The original session-summary referenced this ADR by inferring path — F-INC-003 = ADR path inconsistency cross-repo. Mitigation = reference copy here.

---

## How to consume

- **For runtime decisions** (channel adapter implementation, env var conventions, identity policy enforcement): read this file.
- **For ADR amendments** (relaxing a decision, adding an exception, marking obsolete): edit canonical in `notion-governance` then sync.
- **For sync**: `cp ~/notion-governance/docs/architecture/16-multichannel-rick-channels.md docs/external-context/adr-16-multichannel-rick-channels.md` and update the "Last sync" line above + commit SHA.

---

## Operative summary (for quick agent consumption — full text below)

**Decisions cross-canal** (D1-D6, ADR §1):

| ID | Decisión | Status |
|---|---|---|
| D1 | Identidad funcional única "Rick" cross-canal | strict |
| D2 | Autoría real (no spoofing de la cuenta humana de David) | **strict EXCEPT canal Notion** (relajado permanente 2026-05-07 — ver §6 fila) |
| D3 | NO usar `NOTION_API_KEY` de David como bypass de identidad/scope (a menos que esté declarado como autoría aceptada de la integration "Rick" propia, no de la integration personal de David) | strict |
| D4 | Telegram exempt de D2 (limitación técnica documentada — bots no pueden ser miembros user) | exempt |
| D5 | Token storage convention: `~/.config/umbral/<channel>/.env` (one file per channel) | guideline |
| D6 | Whitelist scopes: cada canal limita scopes a workspace de David + páginas/conversaciones explícitamente autorizadas | strict |

**Canales contemplados** (ADR §2):

| Canal | Status | Mecánica input | Mecánica output | Identidad visible |
|---|---|---|---|---|
| Telegram | 🟢 active (Ola 1) | Bot polling | Bot send_message | "Rick" bot |
| Notion | 🟡 plan Ola 1 (polling activo, smoke pendiente) | Watcher poll comments + regex `@rick` | API comment con `NOTION_API_KEY` integration "Rick" | Integration bot "Rick" (D2 relajada permanente — costo seat extra no justifica delta auditoría) |
| Gmail | 🔴 no implementado (Ola 2+) | OAuth Gmail watch | Gmail send | OAuth `rick.asistente@gmail.com` (D2 strict) |
| Calendar | 🔴 no implementado (Ola 2+) | Calendar watch | Calendar API | OAuth `rick.asistente@gmail.com` (D2 strict) |

**Pre-canal new ADR required** (§5 anti-sprawl).

---

## Full ADR text (synced verbatim — see canonical for source of truth)

> **NOTE**: To minimize duplication risk, this section is intentionally NOT a verbatim paste of the full ADR. For the complete decision rationale, alternatives considered, evidence, and §6 Relajaciones registradas table, **read the canonical**: `notion-governance/docs/architecture/16-multichannel-rick-channels.md` (commit `820a2a8` or later).
>
> The operative summary above captures everything an `umbral-agent-stack` agent needs for runtime/code decisions. If you find yourself needing more depth (e.g., to amend), open the canonical.

---

## Sync history

| Date | Synced from commit | Reason |
|---|---|---|
| 2026-05-07 | `820a2a8` (notion-governance) | F-INC-003 mitigation — first sync after task 026 confirmed D2 relaxation permanent for Notion canal. |
