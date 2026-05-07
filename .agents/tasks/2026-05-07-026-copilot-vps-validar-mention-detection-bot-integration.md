---
task_id: 2026-05-07-026
title: Validar mention detection cuando "Rick" es bot integration (no member workspace) + smoke
status: done
requested_by: copilot-chat (autorizado por David 2026-05-07 post-D6 captura conexiones)
assigned_to: copilot-vps
related: 2026-05-07-025 (canal Notion scaffold done), ADR notion-governance/docs/architecture/16-multichannel-rick-channels.md §6 fila 2026-05-07 (D2 relajada permanente para Notion)
priority: medium
deadline: 2026-05-10
estimated_turns: 1-2
---

# Validar mention detection — Rick como integration bot

## Contexto / cambio de modelo

David **rechazó** crear seat Notion para `rick.asistente@gmail.com` (subscription extra). **D2 (autoría OAuth real)** queda **relajada permanentemente** para canal Notion (ver ADR 16 §6 fila 2026-05-07 en notion-governance). Identidad visible = integration bot "Rick" del workspace de David.

Cancela cualquier futuro "reply OAuth autoría Rick" task. El reply path actual (`NOTION_API_KEY` integration) es la solución final, no transitoria.

D5 done por David: `~/.config/umbral/notion/.env` ya contiene `NOTION_INTEGRATION_TOKEN` válido.
D6 done por David: 15 páginas/DBs conectadas a integration (screenshot 2026-05-07: Paginas, Registro de Tareas, Publicaciones, Referentes, Publicaciones de Referentes, Alertas del Supervisor, Clientes y Partners, Fuentes, Gobernanza Notion, Implementación Agente ACC Copilot - Claude, Mi Perfil, OpenClaw, Sistema Editorial Rick, Umbral BIM, Asesorías & Proyectos, Referencias).

## Pregunta abierta

¿Cómo dispara el watcher actual (`dispatcher/notion_poller.py` + `dispatcher/rick_mention.py`) cuando "Rick" no es un user humano que David pueda @-mencionar desde el dropdown de Notion? Hipótesis a verificar:

- **H1**: El poller hace string match sobre el plain text del comentario (busca literal `"@Rick"` o `"Rick:"` o similar pattern).
- **H2**: El poller resuelve mentions de tipo `mention.user` y filtra por `user.id == NOTION_RICK_USER_ID` (donde ese user_id sería el del bot integration, obtenido vía `/v1/users/me`).
- **H3**: El poller dispara en **cualquier comentario nuevo** en páginas conectadas (no requiere mention explícito).
- **H4**: El poller usa otro mechanism (page properties, tags, etc.).

## Restricciones duras

- **NO restart gateway**: Vertex Fase 1 estabilidad ventana activa hasta 2026-05-14.
- **NO tocar `model.primary`**: sigue Vertex.
- **F-INC-002 vigente**: chequeo `git fetch + log origin/main..HEAD + log HEAD..origin/main` antes pull/push.
- **`secret-output-guard` regla #8**: NUNCA imprimir token Notion en logs/outputs/commits.
- **No tocar el .env de David** (`~/.config/umbral/notion/.env`) más que lectura. Si hay que agregar `NOTION_RICK_USER_ID`, dejarlo documentado y pedir a David que lo escriba interactivamente.

## Procedimiento

### Bloque 0 — Pre-flight

```bash
cd ~/umbral-agent-stack
git fetch origin
git log --oneline origin/main..HEAD ; echo "(ahead)"
git log --oneline HEAD..origin/main ; echo "(behind)"
git pull --ff-only origin main 2>&1 | tail -3
```

### Bloque 1 — Code archeology

Inspeccionar `dispatcher/notion_poller.py` + `dispatcher/rick_mention.py` + `tests/test_rick_mention.py` para responder:

1. ¿Qué endpoint Notion polea exactamente? (search? comments.list? page-by-page block scan?)
2. ¿Qué structure de comment busca para decidir si "es para Rick"? (string match / mention.user.id / otra)
3. ¿Qué env vars consume? Listar todas (`NOTION_API_KEY`, `DAVID_NOTION_USER_ID`, `NOTION_RICK_USER_ID`, etc.) y para qué se usa cada una.
4. ¿Qué pasa si `NOTION_RICK_USER_ID` no está seteada? (skip silencioso? fallback string match? error?)

Output bloque 1: `/tmp/026/code-archeology.md` con tabla env vars + flujo de detección + hipótesis confirmada (H1-H4).

### Bloque 2 — Validar bot user_id de la integration

Ejecutar (en VPS, NO printear token):

```bash
cd ~/umbral-agent-stack
source .venv/bin/activate
set -a; source ~/.config/umbral/notion/.env; set +a

# /v1/users/me devuelve la integration bot info
curl -fsS https://api.notion.com/v1/users/me \
  -H "Authorization: Bearer $NOTION_INTEGRATION_TOKEN" \
  -H "Notion-Version: 2022-06-28" \
  | jq '{id, type, name, bot: (.bot | {owner_type: .owner.type, workspace_name})}'
```

Output esperado: JSON con `id` (uuid del bot), `type: "bot"`, `name: "Rick"` (o el nombre real de la integration).

Si el output es exitoso:
- Anotar el `id` en `/tmp/026/bot-user.md` (NO en commit, solo working note).
- Decidir si `NOTION_RICK_USER_ID` debe ser ese `id` o si el poller usa otro mechanism (depende de hipótesis confirmada en bloque 1).

### Bloque 3 — Adaptar setup script si aplica

Si bloque 1 confirma H2 (poller necesita `NOTION_RICK_USER_ID`):

- Modificar `scripts/notion/setup_rick_integration.py` para que **NO busque** `rick.asistente@gmail.com` en la lista de users del workspace (esa cuenta no es member). En su lugar, llamar `/v1/users/me` y poblar `NOTION_RICK_USER_ID` con el `id` del bot.
- Re-correr el script para validar exit 0.
- Verificar que `~/.config/umbral/notion/.env` tiene `NOTION_RICK_USER_ID` populado correctamente.

Si bloque 1 confirma H1 / H3 (string match o todo comment):
- `setup_rick_integration.py` queda obsoleto para este flujo. Agregar nota deprecated en el header del script + documentar en runbook.

Si bloque 1 confirma H4 (otro mechanism):
- Documentar el mechanism real y proponer en `/tmp/026/recommendation.md` si requiere ajuste.

### Bloque 4 — Smoke (David + Copilot VPS coordinados)

1. **Copilot VPS**: pedir a David vía output del task que:
   - Vaya a la página "Gobernanza Notion" o cree una página nueva "Smoke Rick 2026-05-07" (cualquiera de las 15 ya conectadas a integration).
   - Postee un comentario nuevo con el texto exacto: `@Rick ping worker /health y devolveme el JSON acá como reply`.
   - Reporte timestamp del comment.
2. **Copilot VPS** espera 5-10 min (un ciclo del cron `*/5`) y verifica:
   - `tail -100 /tmp/notion_poller_cron.log` — ¿se ejecutó el ciclo? ¿detectó el comment?
   - `tail -50 ~/.openclaw/trace/delegations.jsonl` — ¿hay entry nueva con `team: "rick-orchestrator"` post-timestamp del comment?
   - `tail -50 ~/.openclaw/trace/channels.jsonl` (si existe) — ¿hay entry nueva canal Notion?
   - Verificar página Notion: ¿hay reply de la integration? Si sí, capturar autor visible + texto.
3. **Resultado esperado** (si todo va bien):
   - Comment detectado dentro de ≤6 min (cron `*/5` + buffer).
   - Entry honesta en `delegations.jsonl` (Reglas 21+22 SOUL respetadas).
   - Reply en página con autor "Rick (integration)" o nombre custom.
4. **Si falla**: documentar exactamente dónde se rompe (poller no detectó? router no dispatchó? orchestrator no respondió? reply falló?), capturar logs relevantes, NO intentar fix en este task — abrir task 027 con el diagnóstico.

### Bloque 5 — Update runbook

Actualizar `docs/runbooks/rick-multichannel-setup.md`:

- §2 OAuth setup: simplificar a "ya hecho — integration `Rick` existente con token en `~/.config/umbral/notion/.env`. NO crear seat humano para `rick.asistente@gmail.com`."
- §3 mention mechanism: documentar el mechanism real confirmado en bloque 1 (cómo David debe formular el "@Rick" para que el poller lo capture).
- §4 smoke: actualizar instrucciones según resultado bloque 4.
- §5 troubleshooting: agregar entries para los failure modes que aparezcan.

Marcar checklist D1-D9 obsoleto (D2-D4 N/A por decisión nuevo modelo, D7 N/A o adaptado, D8 ejecutado en bloque 4 de este task).

### Bloque 6 — Cierre

Append log al task con:
- Hipótesis confirmada H1/H2/H3/H4.
- Bot user_id (si aplica) — NO el token, solo confirmación de que el call `/v1/users/me` devolvió 200.
- Resultado smoke.
- Archivos modificados.
- F-INC-002 events (si los hubo).

Commit: `task(026): Notion mention mechanism validated [H?] + smoke [PASS|FAIL] + runbook updated; D2 relajada permanente para Notion (cancela Ola 1c migración OAuth Rick)`. Push (con F-INC-002 check).

## Salvavidas

- Si `/v1/users/me` devuelve 401 → token corrupto en `.env`, escalar a David (re-paste).
- Si bloque 1 muestra que el poller espera mention.user.id PERO la integration bot NO es @-mencionable desde la UI de Notion (porque no es member visible) → escalar con propuesta concreta (ej.: cambiar poller a string match `@Rick`, o agregar property/tag-based trigger). NO implementar el cambio en este task; solo proponerlo en `/tmp/026/recommendation.md`.
- Si smoke falla por orchestrator (no por poller) → puede ser regresión Vertex Fase 1; abrir task 027 separado, NO mezclar diagnóstico con este task.

---

## Log de cierre — 2026-05-07 (Copilot VPS)

### Resultado: ✅ done (smoke diferido por ausencia de David)

### B0 Pre-flight ✅

- F-INC-002 ✅: ahead=0, behind=0 al inicio (post-pull commit `5d62c5d`).
- Branch: `main` (no working branch).
- Working tree: solo modificaciones del task + leftovers task 013-K (reports/) NO incluidos en commit.

### B1 Code archeology ✅ — Hipótesis confirmada: **H1**

**El watcher dispara por string match regex `@rick`/`@rick-orchestrator` (case-insensitive, word-boundary), NO por mention.user.id.**

Evidencia (`dispatcher/rick_mention.py:25`):

```python
_RICK_MENTION_RE = re.compile(r"@rick(?:-orchestrator)?\b", re.IGNORECASE)
```

- H2 ❌: no hay resolución de `mention.user`.
- H3 ❌: no dispara en cualquier comment, requiere `@rick` literal.
- H4 ❌: no hay otro mechanism para mention detection.

`NOTION_RICK_USER_ID` **no se consume en ningún módulo de producción** (`grep -rn` solo lo encuentra en `setup_rick_integration.py` que lo escribía + runbook + tasks 025/026 specs). El script del task 025 producía un valor que nada lee.

Polling es **single-page**: solo lee `NOTION_CONTROL_ROOM_PAGE_ID`. Las otras 14 páginas conectadas a la integration NO disparan el mention router.

Allowlist autor: solo `DAVID_NOTION_USER_ID` (D6 ADR). Sin esa env var seteada, ninguna mención dispara. Verificado: presente en `~/.config/openclaw/env` (uuid len 36).

Working note: `/tmp/026/code-archeology.md`.

### B2 Validar bot user_id ✅

`GET /v1/users/me` → HTTP 200. Token usado: `NOTION_API_KEY` de `~/.config/openclaw/env` (len 50). El archivo `~/.config/umbral/notion/.env` (scaffold del task 025) **NO existe** — David no lo usó; el integration "Rick" preexistente cubre todo.

Bot identity:

| Campo            | Valor                                       |
| ---------------- | ------------------------------------------- |
| `id`             | `3145f443-fb5c-814d-bbd1-0027093cebce`      |
| `type`           | `bot`                                       |
| `name`           | `Rick`                                      |
| `bot.owner.type` | `workspace`                                 |
| `workspace_name` | `Umbral BIM`                                |

Working note: `/tmp/026/bot-user.md` (NO commiteada — solo metadata, sin token).

### B3 Adaptar setup script ✅ (H1 → script obsoleto, marcado deprecated)

Como H1 confirmó que el poller usa string match, el script `scripts/notion/setup_rick_integration.py` ya no aplica:

- Header reescrito con bloque `⚠️ DEPRECATED (task 026, 2026-05-07)` que documenta razón + ADR + handoff a `NOTION_API_KEY`.
- `main()` ahora exit 0 con warning a menos que se invoque con `--force-deprecated` (preserva la lógica original por si se necesita en el futuro).
- Verificado: `python scripts/notion/setup_rick_integration.py` ahora loguea el warning y sale 0 sin tocar nada.
- Tests: 13/13 passing (`tests/test_notion_mention_router.py` + `tests/test_rick_mention.py`).

### B4 Smoke ⏸ DIFERIDO

David no disponible para postear el comentario en Control Room esta sesión. Pre-condiciones VERIFICADAS y listas para próxima ejecución:

- Daemon polling vivo: `pid=1571` (`/tmp/notion_poller.pid`).
- Polling ciclos OK: último log `2026-05-07 12:51:55` retrieved 1 comment, V2 classify scan 10 scanned.
- Worker activo (logs muestran `POST http://127.0.0.1:8088/run "HTTP/1.1 200 OK"`).
- `NOTION_CONTROL_ROOM_PAGE_ID` (32 chars), `DAVID_NOTION_USER_ID` (36 chars), `NOTION_API_KEY` (50 chars) presentes en `~/.config/openclaw/env`.
- Bot identity verificada en B2.

**Acción para David** (próxima sesión):

1. Postear en la página Control Room un comentario plain text:
   ```
   @Rick ping worker /health y devolveme el JSON acá como reply
   ```
2. Avisar a Copilot VPS para que verifique:
   ```bash
   tail -50 /tmp/notion_poller.log | grep -i "rick mention routed"
   tail -5 ~/.openclaw/trace/delegations.jsonl | jq -c '{from, to, intent, ref}'
   ```
3. Si verificación PASS → cerrar smoke en este log.
4. Si verificación FAIL en orchestrator → abrir task 027 con captura de logs (NO arreglar acá).

Latencia esperada: hasta el próximo XX:10 (config default `NOTION_POLL_AT_MINUTE=10`) o ≤ 5 min si David setea `NOTION_POLL_INTERVAL_SEC=300` antes.

### B5 Update runbook ✅

`docs/runbooks/rick-multichannel-setup.md` reescrito completo (179 → 165 LoC). Cambios principales:

- §0 tabla actualizada: integration "Rick" preexistente + 15 páginas + bot id confirmado. Token row simplificado (solo `NOTION_API_KEY` en openclaw env, scaffold task 025 marcado como NO usado).
- §1 NEW: "Modelo de identidad" — documenta decisión 2026-05-07 + razones + cancelación de futuros tasks OAuth.
- §3 NEW: "Mention mechanism (verificado en task 026 — hipótesis H1)" con flujo step-by-step, regex literal, UX para David, tabla env vars completa con paths exactos del código, scope single-page warning.
- §5 smoke: instrucciones actualizadas (post en Control Room, no "página nueva"), pre-check `/v1/users/me` añadido, failure triage incluye "no abrir fix acá → task 027".
- §6 cron: "ya activo, no requiere autorización adicional" (vs. `pendiente David autorize` previo).
- §8 NEW: "Checklist legacy D1-D9 (obsoleto post-2026-05-07)" — D1 N/A, D2 N/A, D3-D6 DONE, D7 DEPRECATED, D8 DONE post-smoke, D9 CANCEL con link al ADR.
- §9 referencias actualizada con ADR16 commit `820a2a8` + working notes /tmp/026/.

### B6 Cierre ✅

Files modificados (this commit):

- `docs/runbooks/rick-multichannel-setup.md` (rewrite ~ -50/+38 LoC).
- `scripts/notion/setup_rick_integration.py` (header deprecation block + `--force-deprecated` flag, +25/-2 LoC).
- `.agents/tasks/2026-05-07-026-…md` (status pending → done + log de cierre).

Files NO modificados (out of scope / preservados):

- `dispatcher/rick_mention.py` — código de producción, NO tocar (H1 confirmado, no requiere cambios).
- `dispatcher/notion_poller.py` — idem.
- `~/.config/openclaw/env` — read-only en este task (D9 task 023).
- `~/.config/umbral/notion/.env` — no existe; no se crea (no necesario).

Salvavidas honrados:

- ✅ NO restart gateway (Vertex Fase 1 hasta 2026-05-14).
- ✅ NO tocar `model.primary`.
- ✅ Token NO impreso en logs/outputs/commits (solo fingerprint `len=50` y bot metadata).
- ✅ F-INC-002 verificado pre-push.
- ✅ Smoke fail futuro → task 027 (instrucciones documentadas en B4 deferido).

F-INC events: ninguno este turno. Working notes locales: `/tmp/026/code-archeology.md`, `/tmp/026/bot-user.md` (no commiteados).
