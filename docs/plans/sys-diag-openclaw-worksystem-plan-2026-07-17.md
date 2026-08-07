# Plan — Diagnóstico total OpenClaw/Umbral × sistema de trabajo de David (2026-07-17)

Estado: `SYS_DIAG_PLAN_READY` (Fase 0 cerrada; Fase 1 en ejecución en esta misma rama)
Rama: `claude/plan-sys-diag-openclaw-worksystem-2026-07-17`
Alcance: **solo docs + captura read-only + prompts multi-IA. Sin fixes, sin deploy, sin reactivar features, sin gasto de créditos Notion AI.**

## 0. Contexto congelado (no reabrir)

- P1 + P2a Granola cerrados: motor determinista create/update-noop/update-safe-patch verificado; poller restaurado con `NOTION_POLLER_ENABLE_V2_CLASSIFY` ausente = OFF (fail-closed).
- Smoke Control Room OK; mención @Rick responde health JSON hard-coded (triage v0, sin LLM).
- Captura David 2026-07-17: "SIM Daily Report" en Control Room con `research.web` 13/13 OK y `llm.generate` 0/5 FAIL ("Sin resumen disponible"). David no recuerda qué es → señal de automatización olvidada/drift/ruido.
- Worker sin proveedor LLM vivo: `GOOGLE_API_KEY` ausente; `UMBRAL_DISABLE_CLAUDE=true`; OAuth Codex del gateway no llega al Worker.

## 1. Mapa de superficies a auditar (checklist)

| # | Superficie | Método | Fuente |
|---|-----------|--------|--------|
| S1 | OpenClaw gateway: `openclaw.json`, agents, models/fallbacks, auth, allowAgents, Telegram, Control UI | `openclaw status --all`, `models status`, `verify-openclaw.sh`, lectura config viva | VPS |
| S2 | Workspace/skills live (`~/.openclaw/workspace/skills`) vs templates repo (`openclaw/workspace-templates/skills`) | diff recursivo | VPS + repo |
| S3 | Crons, systemd user units, watchdogs, daemons (poller, worker, gateway, sim-report) | `crontab -l`, `systemctl --user list-units`, `ps` | VPS |
| S4 | Worker FastAPI: tasks registradas por familia, `/health`, providers LLM, env bindings Notion | `curl /health`, registry de tasks, nombres de env (sin valores) | VPS |
| S5 | Poller / Control Room / smart-reply / triage v0 @Rick | código `dispatcher/`, logs recientes, cursors Redis | repo + VPS |
| S6 | Redis: claves/cursors relevantes (patrones, sin dump de valores sensibles) | `redis-cli --scan` acotado | VPS |
| S7 | SIM Daily Report + research pipelines + editorial + tournament + PIT + Granola/capitalización | scripts, crons, ops_log, última corrida, costo | repo + VPS |
| S8 | Notion surfaces: Control Room, Transcripciones Granola, Registro de Tareas, Bandejas Rick, Publicaciones (solo lectura) | prompt Notion AI (David pega) + env IDs por nombre | Notion |
| S9 | Notion Agents custom + triggers (ON/OFF, modelo, créditos) | prompt Notion AI (David pega); **prohibido ejecutarlos en batch** | Notion |
| S10 | Copilot Windows / Copilot VPS / Azure Foundry leftovers | docs 42/43, env names, prompts Copilot | repo + prompts |
| S11 | n8n / Make / Power Automate | docs 37/39/60, procesos VPS, prompts | repo + VPS + prompts |
| S12 | Mailbox legacy / `.agents` board / Linear | repo `.agents/`, docs 30/34/67 | repo |
| S13 | Sistema de trabajo real de David (ritmos, gates, superficies canónicas) | notion-governance + AGENTS/SOUL/PROTOCOL + capturas multi-IA | repos + Fase 1C |
| S14 | Higiene de repos, clones, worktrees y ramas en `C:\GitHub` (umbral-agent-stack*, notion-governance*, umbral-bot*, `.tmp-*`, `_wt*`) + hilos/agentes propietarios | git status/branch/worktree + `gh pr list` read-only; capturas UI de hilos Claude Code = `[UI_EVIDENCE_PENDING]` si faltan | local + David |

## 2. Taxonomía de hallazgos (obligatoria en todo entregable)

`ACTIVE_HEALTHY` | `ACTIVE_DEGRADED` | `ACTIVE_NOISY` | `OBSOLETE` | `ORPHAN` | `DRIFT_REPO_VPS` | `NEVER_SHIPPED` | `DUPLICATE` | `SECURITY_RISK` | `COST_RISK` | `UNKNOWN`

Reglas: una etiqueta primaria por hallazgo (secundarias entre paréntesis); `UNKNOWN` es legítimo y preferible a inventar; toda etiqueta exige evidencia citada (comando+salida, path+línea, o "contrato gov").

Sub-taxonomía para S14 (higiene git): `ACTIVE | STALE | MERGED_REMOTE_ONLY | ORPHAN_LOCAL | DIRTY_HIGH_RISK | CONFLICT_RISK | UNKNOWN`, con recomendación por hallazgo `KEEP | COMMIT_SEPARATELY | PR | ARCHIVE | IGNORE | DELETE_CANDIDATE | DO_NOT_TOUCH`. Regla dura S14: **cero** borrado/stash/reset/checkout destructivo/cierre de PR/eliminación de ramas durante el diagnóstico; distinguir trabajo real (D-19, QW-2, P10-SEC63, auditorías) de basura potencial (`.audit-*`, `.tmp-*`, evidencia no gitignored); la correspondencia clone↔hilo sin captura UI se marca `[UI_EVIDENCE_PENDING]`, nunca se inventa.

## 3. Fuentes de verdad a cruzar

1. **notion-governance** (`C:\GitHub\notion-governance`): policies 02/03/05/06/07/10, registry runtime-bridge, AGENTS.md, skills de capitalización/routing → *contrato*.
2. **umbral-agent-stack**: AGENTS.md, SOUL.md, board `.agents/`, PROTOCOL, runbooks, ADRs, plan híbrido capitalización → *intención*.
3. **VPS** (`~/umbral-agent-stack` desplegado + `~/.openclaw/*` + crons + Redis) → *realidad*. Regla: repo=intent, VPS=reality; todo delta = `DRIFT_REPO_VPS`.
4. **Capturas multi-IA** (Fase 1C): lo que ninguna fuente local ve (Gmail, memoria ChatGPT, Notion Agents, M365, extensiones Copilot).

Etiquetado de evidencia obligatorio: `[VPS evidencia]` / `[repo inferencia]` / `[gov contrato]` / `[multi-IA pendiente]`.

## 4. Matriz de prompts multi-IA

| # | Destinatario | Captura | Por qué esa IA | No puede | Timeout | Formato |
|---|-------------|---------|----------------|----------|---------|---------|
| 1 | ChatGPT (Work + conectores) | flujos email, compromisos, memoria de proyectos, custom GPTs, trabajo manual automatizable | única con memoria ChatGPT + Gmail/Drive conectados | ver VPS/repo/Notion internals | 10 min | YAML |
| 2 | Notion AI (desde Gobernanza/Control Room) | inventario agentes, DBs canónicas, triggers, vivo vs legacy | única con vista nativa workspace + agentes custom | ver VPS/repo; **no ejecutar agentes** | 10 min | tabla MD |
| 3 | Cursor (Auto) | reglas `.cursor`, skills locales, multi-root, hilos activos | vive en el editor local de David | ver VPS runtime ni Notion | 5 min | YAML |
| 4 | Codex (clone coordinador) | ADRs, deuda técnica, handlers nunca activados, PRs abandonados, Foundry/OAuth configs | mejor lector de historia del repo; contexto Codex OAuth | ver runtime vivo ni Notion | 15 min | tabla MD |
| 5 | GitHub Copilot (chat/Windows) | extensiones, Actions workflows, entornos Azure/GitHub, scripts locales Windows | ve GitHub org + entorno Windows local | ver VPS ni Notion | 10 min | YAML |
| 6 | Copilot VPS (operador GO MIN) | procesos, crons, disk, logs, drift, nombres de secretos | está dentro de la VPS con shell | tocar config/deploy (read-only) | 15 min | YAML |
| 7 | Microsoft Copilot 365/Graph | calendario, Teams, SharePoint/OneDrive AEC/docencia | única con Graph del tenant | ver stack Umbral | 10 min | tabla MD |
| 8 | Perplexity Pro | research externo 2026: gobernanza multi-agente, credit hygiene Notion AI, patrones poller+worker, riesgos gateways | mejor research web citado | opinar del stack de David (prohibido) | 15 min | MD citado |
| 9 | Claude Code/Fable (auto) | consolidación de todas las respuestas al volver David | dueño del paquete y del repo | — | siguiente sesión | matriz D |
| 10 | (opcional) n8n/Make/Linear MCP | solo si el inventario detecta superficie activa | acceso directo a esas plataformas | — | 5 min | tabla MD |

## 5. Orden de ejecución de la captura

1. **Ya (esta sesión, sin David):** captura VPS read-only (S1–S7, S10–S12 parte repo) + síntesis fuentes locales (S13 parcial) + inventario git/gh de clones y ramas (S14) → inventario draft.
2. **David, primera tanda (independientes, en paralelo):** prompt 10-n8n (**adelantado**: n8n corre en VPS con workflows sin export canónico en repo — riesgo de pérdida), 6 (Copilot VPS, valida mi captura), 2 (Notion AI), 1 (ChatGPT).
3. **David, segunda tanda:** 4 (Codex), 5 (GitHub Copilot), 3 (Cursor), 7 (M365 si aplica).
4. **David, tercera tanda:** 8 (Perplexity — no depende de nada, puede ir cuando quiera).
5. **Cierre:** David pega todas las respuestas en una sesión nueva con el prompt 9 → consolidación final (paquete siguiente), cruzando contra el inventario git/gh de S14 (no contra nombres de hilos).

## 6. Criterios PASS/FAIL

**Del diagnóstico (Fase 1):**
- PASS: todo ítem del checklist S1–S14 tiene etiqueta taxonómica + evidencia o `UNKNOWN` explícito; SIM Daily Report identificado (generador, causa del fail, recomendación KEEP/FIX/DISABLE); triage v0 documentado incluyendo la reconciliación de métricas del reply `/health` (tasks_registered vs tasks_in_memory); skills drift cuantificado; inventario de clones/ramas con etiquetas o gaps `[UI_EVIDENCE_PENDING]`; ≥9 prompts listos.
- FAIL: cualquier "verificado" sin evidencia (SOUL §18); cualquier fix aplicado; cualquier crédito Notion AI gastado por el stack.

**Del cruce con work system:**
- PASS: cada hallazgo `ACTIVE_*` mapeado a una superficie/ritmo real de David (o marcado sin dueño → candidato retiro); oportunidades separadas en quick wins / apalancamiento / retiros / nuevas / anti-recomendaciones.
- FAIL: recomendaciones genéricas sin anclaje en gobernanza o en el uso real de David.

## 7. Anti-scope (prohibiciones activas)

- No reabrir P1/P2a capitalización (solo citarlos como hallazgo cerrado).
- No gastar créditos Notion Agent en batch ni ejecutar agentes Notion.
- No mergear working trees sucios de notion-governance (clones `-cursor`, `-antigravity`, `-temp`, etc. quedan fuera).
- No deploy, no restart, no editar `openclaw.json`/env, no reactivar V2 classify.
- No secretos/PII: env solo por NOMBRE; logs sanitizados; sin correos completos ni terceros innecesarios.
- No confundir techo de créditos/cuota con gasto real.

## 8. Entregables y gates

1. Este plan → gate `SYS_DIAG_PLAN_READY`.
2. `docs/plans/sys-diag-capture-prompts-2026-07-17.md` — ≥9 prompts listos para pegar.
3. `docs/audits/sys-diag-openclaw-inventory-draft-2026-07-17.md` — inventario propio con taxonomía + matriz de consolidación (sección D) + oportunidades (sección E).
4. Commit en rama; PR solo-docs (confirmado por David 2026-07-17) → gate `SYS_DIAG_DOCS_PR_READY` con el PR abierto (sin merge; base de la consolidación con prompt 9).
5. Resumen operativo a David: orden de pegado (≤10 líneas).
→ gate `SYS_DIAG_CAPTURE_READY` cuando 2+3 estén completos.
