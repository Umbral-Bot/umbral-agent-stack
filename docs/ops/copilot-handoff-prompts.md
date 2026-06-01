# Copilot handoff prompts (Windows + VPS)

Copy-paste blocks for David. **Cursor must push `main` before VPS prompts.**

Last push: _update after commit_

---

## Estado rápido (2026-06-01)

| Hilo | Estado | Acción |
|---|---|---|
| **A** Copilot-VPS D3.1 | ✅ Hecho | #437 mergeado squash (David aprobó) |
| **B** Copilot-VPS O15 delegación | ✅ Hecho | `O15_DELEGATION_SMOKE_OK` |
| **C** Copilot Windows OAuth discovery | ✅ Hecho | `D51_OAUTH_DISCOVERY_OK` |
| **E** Copilot-VPS G-D5.1 audit | 🔴 **PEGAR AHORA** | Task 011 |
| **F** Copilot-VPS delivery post-mortem | ⏸ opcional | Task 012 (si se crea) |

---

## Thread E — Copilot-VPS · G-D5.1 OAuth audit (SIGUIENTE)

**Dónde:** hilo **Copilot con SSH VPS** (nuevo o el de O15 delegación ya cerrado).

```
Sos Copilot-VPS (rick@srv1431451.hstgr.cloud). David aprobó opción b: audit read-only primero.

Lee y ejecuta:

  ~/umbral-agent-stack/.agents/tasks/2026-06-01-011-copilot-vps-gd51-oauth-audit.md

Preflight:
  cd ~/umbral-agent-stack && git pull --ff-only origin main && git log -1 --oneline
  test -f .agents/tasks/2026-06-01-011-copilot-vps-gd51-oauth-audit.md && echo TASK_FILE_OK

Objetivo: inventariar vars GOOGLE_* en ~/.config/openclaw/env (solo nombres SET/UNSET, NUNCA valores),
smoke read-only Gmail + Calendar vía Worker si aplica, tabla vs ADR-16 G1-G5.

Evidencia: ~/.coord-ag-evidence/G-D5.1/
NO OAuth browser, NO gateway restart, NO imprimir tokens.

VEREDICTO: G_D51_VPS_AUDIT_OK o bloqueo honesto. Log + push task si actualizás.
```

---

## Thread B — Copilot-VPS · O15 delegación ✅ CERRADO

Ya ejecutado (`O15_DELEGATION_SMOKE_OK`, push `52a4b6e`). **No pegar de nuevo** salvo regresión.

---

## Thread A — Copilot-VPS · D3.1 torneo ✅ CERRADO

Torneo partial + **#437 mergeado squash** por David. **No pegar de nuevo.**

Follow-up opcional (post-mortem lane delivery vacía) — pedir a Cursor task 012.

---

## Thread C — Copilot Windows · OAuth discovery ✅ CERRADO

Discovery hecho en task 010. **No pegar de nuevo.**

---

## Thread G — Copilot Windows · housekeeping env.rick (opcional, 2 min)

**Dónde:** Copilot Chat **Windows** (sin SSH). Solo si querés confirmar local.

```
Read-only en c:\GitHub\umbral-agent-stack:

1. Confirmá que env.rick NO está trackeado: git ls-files env.rick (debe estar vacío).
2. Confirmá que .gitignore incluye la línea env.rick (Cursor ya la agregó).
3. NO abras ni pegues contenido de env.rick ni .env.

Reportá: TRACKED yes/no, gitignore ok yes/no.
```

---

## Thread F — Copilot-VPS · post-mortem rick-delivery lane vacía (opcional)

**Dónde:** hilo VPS **después** de G-D5.1, si David pide diagnosticar por qué sqlite-impl entregó 0.

```
Sos Copilot-VPS. Read-only post-mortem D3.1 lane sqlite-impl (rick-delivery):

Revisá sesión subagent f430c306... en ~/.openclaw/agents/rick-delivery/sessions/
y evidencia ~/.coord-ag-evidence/D3.1/. Explicá por qué el run terminó done sin commits.

NO fixes, NO prompt changes — solo diagnóstico + recomendación para task Cursor.
```
