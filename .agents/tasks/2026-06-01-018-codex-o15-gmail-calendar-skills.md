# Task 018 — O15 Gmail + Calendar OpenClaw skills (Codex · meta)

- **assigned_to:** codex
- **status:** done
- **created:** 2026-06-02
- **depends_on:** G-D5.2 gate closed (tasks 015–017), ADR-16 §2.3–§2.4, worker handlers live
- **gate:** D5.1 skills router (spine Q2 v2)
- **mode:** extended reasoning / meta — diseño + implementación + tests en un solo hilo

## Objective

Cerrar el gap **D5.1** post-OAuth: skills OpenClaw operativas para Gmail y Calendar que respeten ADR-16 (D4 least-privilege, D5 propose+confirm, D6 whitelist), reutilizando worker tasks existentes.

`notion-mention-router` ya existe como script (`scripts/notion/notion_mention_router.py`). Este task entrega los equivalentes **documentados + invocables** para Gmail y Calendar.

## Preflight repo

```bash
cd ~/umbral-agent-stack   # o clone codex-coordinador sincronizado
git fetch origin main && git checkout main && git pull --ff-only origin main
test -f .agents/tasks/2026-06-01-018-codex-o15-gmail-calendar-skills.md && echo TASK_FILE_OK
```

Leer antes de codear:

- `notion-governance/docs/architecture/16-multichannel-rick-channels.md` (§2.3 Gmail, §2.4 Calendar, D5, D6)
- `umbral-agent-stack/docs/external-context/adr-16-multichannel-rick-channels.md` (espejo read-only)
- `docs/runbooks/rick-multichannel-setup.md`
- `worker/tasks/gmail.py`, `worker/tasks/google_calendar.py`
- `openclaw/workspace-templates/skills/` (convención SKILL.md existente)

## Entregables

### Fase A — Diseño (meta, sin writes runtime)

1. Tabla skill → worker task → scopes → gate humano (propose vs auto).
2. Decidir ubicación: `openclaw/workspace-templates/skills/gmail-router/` y `calendar-propose/` (o nombres alineados al repo).
3. Explicitar qué NO hace cada skill (no outbound sin gate, no calendarios fuera whitelist).

### Fase B — Implementación repo

1. **SKILL.md** por skill con: triggers, inputs, worker payload examples, failure modes, ADR pointers.
2. Wrapper Python mínimo si hace falta (patrón `scripts/notion/notion_mention_router.py`), sin duplicar lógica worker.
3. Tests unitarios con mocks (`tests/test_gmail_router_skill.py`, `tests/test_calendar_propose_skill.py` o equivalente).
4. Actualizar `docs/runbooks/rick-multichannel-setup.md` § skills + smoke commands read-only.
5. Sync header en `docs/external-context/adr-16-multichannel-rick-channels.md` si ADR canónico cambió (solo si notion-governance ya mergeó — si no, pointer en PR).

### Fase C — Validación local

```bash
source .venv/bin/activate
pip install -e ".[test]"
WORKER_TOKEN=test python -m pytest tests/test_gmail_router_skill.py tests/test_calendar_propose_skill.py -v
```

No deploy VPS en este task — handoff separado a Copilot-VPS post-merge PR.

## Criterios PASS

- [x] Dos skills con SKILL.md completos y consistentes con ADR-16 D5/D6
- [x] Tests nuevos pasan; no regresión en suite existente relacionada
- [x] Runbook actualizado con comandos smoke read-only (list drafts, list events David primary)
- [x] PR `codex/feat-o15-gmail-calendar-skills` — **no merge** (Copilot merge master)
- [x] Log en este task con PR #439 + resumen diseño

## Boundaries

- NO tocar `~/.config/openclaw/env` ni VPS
- NO ampliar OAuth scopes
- NO autopublicar Gmail outbound ni crear eventos Calendar sin gate `propose + confirm`
- NO editar `notion-governance` ADR canónico desde este repo (solo espejo + PR pointer)

## VEREDICTO

**O15_GMAIL_CALENDAR_SKILLS_OK**

## Log
- [codex] 2026-06-02 — Entregado:
  - Wrappers mínimos entregados:
    - `scripts/gmail/gmail_router.py`
    - `scripts/google_calendar/calendar_propose.py`
  - SKILL.md por skill agregados:
    - `openclaw/workspace-templates/skills/gmail-router/SKILL.md`
    - `openclaw/workspace-templates/skills/calendar-propose/SKILL.md`
  - Tests agregados:
    - `tests/test_gmail_router_skill.py`
    - `tests/test_calendar_propose_skill.py`
  - Runbook de cobertura actualizado en:
    - `docs/runbooks/rick-multichannel-setup.md` (sección `## 10. Skills O15 — Gmail y Calendar`)
  - Validación:
    - `python -m pytest tests/test_gmail_router_skill.py tests/test_calendar_propose_skill.py -v` → `7 passed`
  - PR:
    - https://github.com/Umbral-Bot/umbral-agent-stack/pull/439
  - Merge:
    - No mergeado; Copilot merge después.
