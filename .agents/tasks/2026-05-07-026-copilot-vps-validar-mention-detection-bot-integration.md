---
task_id: 2026-05-07-026
title: Validar mention detection cuando "Rick" es bot integration (no member workspace) + smoke
status: pending
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
