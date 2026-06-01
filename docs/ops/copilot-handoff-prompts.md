# Copilot handoff prompts (Windows + VPS)

Copy-paste blocks for David. **Cursor must push `main` before VPS prompts.**

Last push: _after commit_

---

## Estado (2026-06-01)

| Hilo | Superficie | Estado |
|---|---|---|
| A–E | VPS / Windows | ✅ Cerrados (D3.1, O15, discovery, G-D5.1) |
| F | Copilot-VPS | ✅ Post-mortem impl lane (read-only) |
| G | Copilot Windows | ✅ **Cerrado** — `env.rick` NO trackeado; `.gitignore` ok (Cursor verificó) |
| **H** | Copilot-VPS | 🔴 **Siguiente opcional** — cleanup worktree |
| **I** | Copilot Windows | 🟡 Prep G-D5.2 (decisión, no OAuth) |
| **J** | Cursor (este chat) | 🟡 Task 012 lane PR gate |

---

## Thread H — Copilot-VPS · cleanup worktree D3.1 (opcional)

**Dónde:** hilo **Copilot-VPS** (SSH). Solo housekeeping.

```
Sos Copilot-VPS. Read-only primero; remove solo si autorizo abajo.

  ~/umbral-agent-stack/.agents/tasks/2026-06-01-013-copilot-vps-d31-worktree-cleanup.md

Preflight: cd ~/umbral-agent-stack && git pull --ff-only origin main && echo TASK_FILE_OK

Inventariá git worktree list y el worktree umbral-agent-stack-lane-sqlite-impl
(0 commits, nunca pusheado — ver post-mortem Thread F).

Si David NO dijo "autorizo remove worktree" en este mensaje → solo reporte read-only.
Si SÍ autorizó → git worktree remove + evidencia en ~/.coord-ag-evidence/D3.1-cleanup/

VEREDICTO: D31_WORKTREE_CLEANUP_OK
```

**Variante con remove autorizado** (pegá solo si querés borrar el worktree):

```
… (mismo prompt) … David autoriza remove del worktree lane-sqlite-impl huérfano.
```

---

## Thread I — Copilot Windows · prep decisión G-D5.2 (sin OAuth)

**Dónde:** Copilot Chat **Windows**, sin SSH.

```
Sos Copilot Windows. Read-only — preparar decisión para David, NO ejecutar OAuth.

Lee:
  c:\GitHub\umbral-agent-stack\.agents\tasks\2026-06-01-014-gd52-oauth-scope-decision.md
  c:\GitHub\notion-governance\docs\architecture\16-multichannel-rick-channels.md (§2.3 Gmail, §2.4 Calendar, D6)

Contexto: G-D5.1 OK — Gmail+Calendar smoke PASS en VPS. Drift de scope vs ADR mínimo.

Entregá a David una recomendación clara entre:
  A) Aceptar tokens actuales + documentar excepción
  B) Re-OAuth scopes ADR (gmail.modify, calendar.events) — listar pasos, no ejecutar
  C) Diferir Q3

Una página max. Sin pegar secretos. Sin tocar VPS.
```

---

## Thread J — Cursor (este chat) · fix lane PR gate

**Dónde:** acá en Cursor, no Copilot.

```
Implementá task 2026-06-01-012-tournament-lane-pr-gate:
orquestador trata lane sin PR como incomplete (docs/79 + skill tournament).
```

*(O pegalo en un hilo Cursor nuevo si preferís contexto limpio.)*

---

## Thread K — Copilot-VPS · re-run solo lane impl (solo post Task 012 + autorización)

**Dónde:** Copilot-VPS — **NO pegar hasta** Cursor cierre task 012 y David autorice.

```
Sos Copilot-VPS. Re-run acotado lane sqlite-impl para issue #403 usando spec
d31-issue-403-tournament-spec.yaml pero SOLO lane rick-delivery (no re-ejecutar qa).

Precondición: task 012 mergeada + git pull main + preflight PASS.
David autorizó re-run impl lane.

Evidencia ~/.coord-ag-evidence/D3.1-rerun-impl/
NO merge automático — reportar PR URL o incomplete con causa.
```

---

## Cerrados — no repetir

- **E** G-D5.1 → `G_D51_VPS_AUDIT_OK` (`e68cf2b`)
- **F** Post-mortem → diagnóstico en chat; recomendación → task 012
- **G** env.rick → NO tracked (`git ls-files` vacío); `.gitignore` línea 8 ok

## Decisión David (sin prompt — respondé en chat)

**G-D5.2 OAuth scope:** ¿**A** aceptar tokens actuales, **B** re-OAuth ADR, o **C** diferir?
