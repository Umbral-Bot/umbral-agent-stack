---
task_id: 2026-05-07-025
title: O15.1b primer canal Notion — OAuth rick.asistente@gmail.com + watcher menciones + skill notion-mention-router + smoke con mención real
status: done
requested_by: copilot-chat (autorizado por David 2026-05-07 post task 023 close)
assigned_to: copilot-vps
related: 2026-05-07-023 (F-NEW2 closed, O15.1b unblocked), ADR docs/architecture/16-multichannel-rick-channels.md
priority: high
deadline: 2026-05-12
estimated_turns: 2-3 (bloque 4 OAuth interactive deferred a David)
note: renumbered from 024→025 post creation due to F-INC-002 collision (Codex created concurrent 2026-05-07-024-fix-test-copilot-agent-preexisting-fails)
---

# O15.1b primer canal — Notion mention router

## Contexto

F-NEW2 cerrado en task 023 (commit `42ca3f1f`): orchestrator nested ahora detecta tool gap honestamente y respeta Reglas 21+22 SOUL. **O15.1b DESBLOQUEADO**. Empezamos con canal Notion (primero por estrategia David).

ADR canales rectora ya aplicada 2026-05-06: `docs/architecture/16-multichannel-rick-channels.md` define identidad única, autoría real OAuth, bypass prohibido, least-privilege scopes, propose+confirm default, whitelist explícita.

Provider primary durante este task: **`google-vertex/gemini-3.1-pro-preview`** (sin tocar — Fase 1 estabilidad activa).

## Objetivo

Implementar canal Notion end-to-end para Rick:

1. OAuth `rick.asistente@gmail.com` como guest del workspace de David (pasos manuales David + automatables Copilot VPS).
2. Watcher de menciones (decisión técnica webhook vs polling en bloque 1).
3. Skill `notion-mention-router` que detecta `@Rick` en páginas Notion y dispatcha al orchestrator vía dispatcher API.
4. Smoke: David @-menciona Rick en una página de prueba → router triggers → orchestrator responde como comentario en la misma página, autoría = `rick.asistente@gmail.com`.

## Restricciones duras

- **NO restart gateway este task**: Fase 1 estabilidad Vertex activa. Si el smoke requiere restart, abortar y escalar.
- **NO tocar `model.primary`**: sigue Vertex.
- **F-INC-002 vigente**: chequeo `git fetch + log origin/main..HEAD + log HEAD..origin/main` antes de cada pull/push.
- **`secret-output-guard` regla #8 vigente**: NUNCA imprimir tokens OAuth, integration secrets, refresh tokens o cookies de session en outputs/logs/commits. Si necesitás referirlos, usar fingerprint (primeros 4 chars + `…` + últimos 4) o variable env name solamente.
- **Reglas 21+22 SOUL vigentes**: el orchestrator usado en smoke debe respetar anti-faking + workaround nested.
- **Least-privilege scopes** (ADR D4): Notion integration con scopes mínimos necesarios para read mentions + post comments. NO `read all content` global.
- **Autoría real OAuth** (ADR D2): Rick comenta como `rick.asistente@gmail.com`, NO como integration bot ni como David. Bypass prohibido (ADR D3).
- **Backups obligatorios** si se editan archivos de config (`openclaw.json`, identity files, dispatcher routes).

## Procedimiento

### Bloque 0 — Setup + lectura ADR + estado actual

```bash
cd ~/umbral-agent-stack
git fetch origin
git log --oneline origin/main..HEAD ; echo "(ahead)"
git log --oneline HEAD..origin/main ; echo "(behind)"
git pull --ff-only origin main 2>&1 | tail -3

TS=$(date +%Y%m%d-%H%M%S); echo "TS=$TS"
mkdir -p /tmp/024

# Lectura ADR canales (decisiones D1-D6 + matriz Notion)
cat docs/architecture/16-multichannel-rick-channels.md | head -200

# Estado actual integraciones Notion (si existe algo previo)
grep -rn "notion" config/ scripts/ skills/ 2>/dev/null | grep -v "^Binary" | head -30 || echo "no notion refs en config/scripts/skills"

# Worker tasks registrados (orchestrator dispatch endpoint)
curl -fsS http://127.0.0.1:8088/health | jq '{worker_version, tasks_registered: (.tasks_registered // .tasks // [] | length)}'
```

### Bloque 1 — Decisión técnica: webhook vs polling Notion

Investigar API real de Notion para detectar menciones a una user en páginas:

- **Webhook nativo**: Notion API tiene webhooks desde 2025 para algunos eventos. Verificar si `comment.created` / `mention.created` / `page.updated` están disponibles para el plan que tiene David. Doc: <https://developers.notion.com/reference/webhooks>.
- **Polling**: alternativa fallback. Endpoint `POST /v1/search` con filter por timestamp + post-filter por mentions hacia user_id de Rick. Frecuencia: cada 5 min (cron). Trade-off: latencia 5 min vs simplicidad.
- **3rd party (Zapier/Make)**: descartar — viola D3 (bypass prohibido) si introduce intermediario.

Output bloque 1:
- Tabla comparativa webhook vs polling: latencia, scopes requeridos, complejidad, costo (API rate limits).
- **Decisión documentada** en `/tmp/024/decision-watcher.md` con justificación + fallback plan.
- Si webhook viable: documentar payload schema esperado.
- Si polling: definir cron schedule + dedupe strategy (evitar procesar misma mención 2 veces).

### Bloque 2 — OAuth setup (mixed: Copilot VPS prep + David interactive)

**Pasos automatables (Copilot VPS):**

1. Crear directorio config: `mkdir -p ~/.config/umbral/notion/`
2. Crear template env: `~/.config/umbral/notion/.env.template` con keys:
   - `NOTION_INTEGRATION_TOKEN` (integration secret de la integration que David creará).
   - `NOTION_RICK_USER_ID` (user_id de `rick.asistente@gmail.com` en el workspace, lo extrae el script una vez OAuth completo).
   - `NOTION_WORKSPACE_ID`.
   - `NOTION_WATCHER_MODE` = `webhook` | `polling`.
   - `NOTION_POLLING_INTERVAL_SEC` = `300` (si polling).
3. Script `scripts/notion/setup_rick_integration.py` (esqueleto): valida token, lista usuarios del workspace, busca `rick.asistente@gmail.com`, devuelve `user_id` para escribir en `.env` real. **NO escribe el token en logs**.
4. Documentar en `docs/runbooks/rick-multichannel-setup.md` (crear si no existe) la sección "Notion OAuth setup" con pasos numerados para David.

**Pasos interactivos (David — documentar en runbook, NO ejecutar):**

1. David crea cuenta `rick.asistente@gmail.com` en Notion (si no existe) y la invita como guest a su workspace personal.
2. David crea Notion Integration en <https://www.notion.so/my-integrations> con nombre "Rick Asistente CEO", asocia al workspace, scopes mínimos: `Read content`, `Insert comments`, `Read user information without email`.
3. David comparte explícitamente las páginas/databases donde Rick puede operar con la integration (Notion requiere share-per-page).
4. David copia integration secret + lo pega en `~/.config/umbral/notion/.env` (path real, NO commit) — formato `NOTION_INTEGRATION_TOKEN=secret_xxxxxxxxxxxxxx`.
5. David ejecuta el script de bloque 2.3 para auto-poblar `NOTION_RICK_USER_ID` y `NOTION_WORKSPACE_ID`.

### Bloque 3 — Skill `notion-mention-router` (implementación)

Path: `scripts/notion/notion_mention_router.py` (consistente con `scripts/discovery/spike_youtube_via_vm_and_dataapi.py` patrón).

Responsabilidades:

1. **Detect**: leer último batch de menciones (vía webhook handler O endpoint polling).
2. **Filter**: solo menciones donde `mentioned_user_id == NOTION_RICK_USER_ID` y `created_by != NOTION_RICK_USER_ID` (evitar loops).
3. **Dispatch**: POST a worker (`http://127.0.0.1:8088/dispatch` o similar — confirmar endpoint en bloque 0) con payload:
   ```json
   {
     "channel": "notion",
     "source_user": "<david_notion_user_id>",
     "page_id": "<notion_page_id>",
     "comment_id": "<notion_comment_id>",
     "mention_text": "<texto literal del bloque que contiene @Rick>",
     "context_blocks": ["<3 bloques previos para context>"],
     "ts": "<ISO8601>"
   }
   ```
   y request `target_agent: "rick-orchestrator"` (cumple identidad única ADR D1: David → Rick → gerencia, no directo).
4. **Reply**: cuando orchestrator devuelve respuesta vía `sessions_yield`, postear como comment en `page_id` usando integration token (autoría = `rick.asistente@gmail.com` per ADR D2).
5. **Log**: append entry estructurada a `~/.openclaw/trace/channels.jsonl` (NEW path canónico para auditoría multi-canal):
   ```json
   {"ts":"...","channel":"notion","page_id":"...","mention_id":"...","dispatched_to":"rick-orchestrator","status":"dispatched|completed|error","duration_ms":..."}
   ```

Restricciones código:
- **NO log token**: usar `os.getenv("NOTION_INTEGRATION_TOKEN")`, nunca print/log el value.
- **Idempotencia**: dedupe por `comment_id` (set persistido en `~/.cache/umbral/notion-processed-comments.json`, last 1000 entries TTL 7 días).
- **Error handling**: structured logging, never bare `except`.
- **Tests**: `tests/test_notion_mention_router.py` con mocks (no real API calls). Cubrir: filter loop, dispatch payload, reply path, dedupe.

### Bloque 4 — Cron / systemd unit (si polling) o webhook handler (si webhook)

**Si polling decisión bloque 1**:
- Crear `infra/systemd/notion-watcher.service` + `notion-watcher.timer` (user units, no sudo).
- Schedule: cada 5 min.
- ExecStart: `/home/rick/umbral-agent-stack/.venv/bin/python -m scripts.notion.notion_mention_router --mode poll`
- Logs vía journald.
- **NO instalar todavía** — dejarlo en repo + documentar en runbook el `systemctl --user enable --now` que David autorizará después del smoke.

**Si webhook decisión bloque 1**:
- Endpoint expuesto vía worker FastAPI: agregar route `POST /webhooks/notion` en `worker/app.py` con verificación de signature (Notion firma webhooks con shared secret).
- Documentar en runbook el setup de webhook URL en Notion integration (apunta a `https://<vps-public>/webhooks/notion` vía Caddy/reverse-proxy existente).

### Bloque 5 — Smoke (deferred a David — documentar pasos)

NO ejecutar smoke este task. Documentar en runbook el smoke esperado para que David ejecute después de OAuth setup completo:

1. David crea página Notion "Rick smoke 2026-05-07" en su workspace, comparte con integration.
2. David escribe en la página: `@Rick, pingeá worker /health y devolveme JSON acá como comment`.
3. Esperado:
   - Watcher detecta mención dentro de N segundos (5 min si polling, <10s si webhook).
   - Dispatcher routea a orchestrator (Vertex primary).
   - Orchestrator nested: respeta Regla 22 (tool gap), ejecuta inline curl `/health`, devuelve JSON.
   - Reply postea como comment en la página, autoría = `rick.asistente@gmail.com`.
   - Entry registrada en `channels.jsonl` con `status:"completed"` + `duration_ms < 30000`.
   - Entry registrada en `delegations.jsonl` con `assigned_to: agent:rick-orchestrator` honesto (Reglas 21+22 SOUL).

Cuenta como muestra Fase 1 estabilidad Vertex.

### Bloque 6 — Cierre

Append log estructurado al final de este task con:
- Bloque 1 decisión (webhook|polling) + justificación.
- Bloque 2 archivos creados (lista paths) + checklist David interactive (qué falta para él).
- Bloque 3 skill implementado: paths + bytes + tests pasando (`pytest tests/test_notion_mention_router.py -v`).
- Bloque 4 cron/webhook setup: archivo creado, NO activado.
- Bloque 5 runbook section creado.
- F-INC-002 events si los hubo.
- Estado final: gateway pid (sigue 75421 si no hay restart), `model.primary` Vertex, sin diffs no autorizados.

Commit: `task(024): O15.1b canal Notion done — watcher [webhook|polling] + skill notion-mention-router + runbook OAuth setup; smoke deferido a David`. Push (con F-INC-002 check).

## Output esperado

1. Decisión técnica documentada (webhook vs polling).
2. Skill `notion-mention-router` funcional + tests pasando (mocks).
3. Runbook `docs/runbooks/rick-multichannel-setup.md` con sección Notion completa (OAuth setup + smoke).
4. Cron unit / webhook handler creado pero NO activado (David autoriza activación después de OAuth setup + smoke OK).
5. Sin restart gateway, sin tocar `model.primary`, sin secrets en commits.
6. Checklist explícito de qué pasos David debe ejecutar interactivamente (Notion integration creation, scopes, share pages, paste token).

## Salvavidas

- Si bloque 1 muestra que webhook NO está disponible para el plan de David → polling como default, sin escalada.
- Si bloque 3 requiere endpoint dispatcher que no existe → escalar a David antes de inventar route nueva (puede haber ADR pendiente).
- Si bloque 4 webhook handler requiere reverse-proxy config nuevo → escalar (no tocar Caddy sin autorización).
- Si la integration scope `Insert comments` no existe en Notion → fallback a `Update content` (más amplio, documentar trade-off + flag para revisar).

---

## Log de ejecución — 2026-05-07T12:17-12:23 (copilot-vps)

### Bloque 0 — Setup + estado actual

- F-INC-002: main al día con `7352cfa` (PR #343 YouTube Data API). Working tree limpio en main (excepto reports leftover de tasks anteriores no relacionados).
- TS = `20260507-121739`.
- **F-INC-003 detectado**: el task referencia `docs/architecture/16-multichannel-rick-channels.md` que **no existe en el repo**. ADR canales D1-D6 está inlineado en el body del task spec; procedí con esos principios documentados como rectores (no inventé interpretación nueva). Nota para próximos tasks: crear ese ADR formalmente (out-of-scope task 025) o actualizar tasks futuros para citar al task 025 spec en su lugar.
- **Hallazgo grande**: la infraestructura Notion ya existe casi completa desde Ola 1b (2026-04):
  - `dispatcher/notion_poller.py` (555 LoC) — daemon polling.
  - `scripts/vps/notion-poller-daemon.py` + cron `*/5 * * * * scripts/vps/notion-poller-cron.sh` (auto-restart si daemon muere).
  - `dispatcher/rick_mention.py` (90 LoC) — detect + dispatch a `rick.orchestrator.triage` con trace en `~/.openclaw/trace/delegations.jsonl`.
  - `tests/test_rick_mention.py` 7/7 passing.
  - Env var `DAVID_NOTION_USER_ID` ya configurada en `~/.config/openclaw/env`.
- Worker `/health` OK (v0.4.0, 103 tasks).
- Gateway pid 75421 (sin restart).

### Bloque 1 — Decisión: **POLLING**

- Ya en producción. Detalle completo y tabla comparativa: `/tmp/025/decision-watcher.md`.
- Razones: (a) cero infra extra, (b) auto-recover via cron, (c) dedupe Redis maduro, (d) webhook implicaría exponer endpoint público nuevo + Caddy (ADR salvavidas: prohibido sin autorización), (e) Fase 1 estabilidad Vertex prefiere cero superficie nueva.
- Trade-off: latencia hasta 60 min con default `NOTION_POLL_AT_MINUTE=10`. Mitigable a 5 min via `NOTION_POLL_INTERVAL_SEC=300` (documentado en runbook §1).

### Bloque 2 — OAuth scaffold para `rick.asistente@gmail.com`

- Nuevo directorio: `~/.config/umbral/notion/` (chmod default 775; el `.env` real será chmod 600 cuando David lo cree).
- Archivo nuevo: `~/.config/umbral/notion/.env.template` (74 líneas, comentarios + 5 keys vacías). NO commiteado al repo (config per-host, fuera de tree).
- Script nuevo: `scripts/notion/setup_rick_integration.py` (189 LoC) — valida token, lista users del workspace, busca `rick.asistente@gmail.com`, escribe `NOTION_RICK_USER_ID` y `NOTION_WORKSPACE_ID` al `.env`. Exit codes: 0=ok / 2=token vacío / 3=token inválido / 4=user no encontrado.
- **`secret-output-guard` regla #8 cumplida**: el script solo loguea fingerprint `first4…last4` del token, nunca el value completo.
- Verificación: `python -c "import ast; ast.parse(...)"` OK + dry-run con `.env-test-empty` exit code 2 (correcto).

### Bloque 3 — Skill `notion-mention-router`

- Wrapper canonical (named per task spec): `scripts/notion/notion_mention_router.py` (100 LoC). Re-exporta `is_rick_mention` y `handle_rick_mention` desde `dispatcher.rick_mention` + agrega `route_one_mention(comment, *, allowlist, wc, queue, scheduler, page_kind=None)` para dispatch programático.
- **Decisión anti-duplicación**: el skill NO duplica la lógica de `dispatcher/rick_mention.py` (que ya está en producción con tests). El wrapper expone el nombre que pide el spec sin tocar código vivo.
- Tests nuevos: `tests/test_notion_mention_router.py` (124 LoC, 6 tests).
- Resultado: **`pytest tests/test_notion_mention_router.py tests/test_rick_mention.py -v` → 13/13 PASSED en 0.53s**.

### Bloque 4 — Cron / activación

- **Cron polling YA en producción** (no se duplica). Línea actual:
  ```
  */5 * * * * bash /home/rick/umbral-agent-stack/scripts/vps/notion-poller-cron.sh >> /tmp/notion_poller_cron.log 2>&1
  ```
- **Lo que NO está activado y queda diferido a David** (cumple "creado pero NO activado"):
  - Reply path con autoría OAuth Rick (vs integration de David). Hoy `worker.tasks.notion.handle_notion_add_comment` usa `NOTION_API_KEY` (David). Cuando David complete OAuth setup B2 + autorice, próximo task implementará variant que use `NOTION_RICK_INTEGRATION_TOKEN` cuando `team == "rick-orchestrator"`.
  - Migración a webhook (futura, no activada en este task).

### Bloque 5 — Runbook

- Nuevo: `docs/runbooks/rick-multichannel-setup.md` (179 LoC). 7 secciones: estado actual, decisión técnica, OAuth setup con checklist David interactivo (D1-D6 todos checkboxes), skill, activación pendiente, smoke procedure (deferido), troubleshooting.
- Smoke explícitamente NO ejecutado en este task. Documentado paso a paso para que David lo ejecute después de §2 OAuth.

### Bloque 6 — Cierre

- **Estado preservación**:
  - `~/.openclaw/openclaw.json`: NO tocado este task. Diff vs `.bak-pre-021-…` solo en `model.primary` (cambio del task 021). `model.primary` = `google-vertex/gemini-3.1-pro-preview` ✅.
  - Gateway pid: **75421** (activo, sin restart consumido) ✅.
  - `~/.config/openclaw/env`: NO tocado este task ✅.
  - Workspaces SOUL: NO tocados este task ✅.
  - Cron crontab: NO modificado este task ✅.
- **F-INC-002**: pre-commit `git fetch && log origin/main..HEAD && log HEAD..origin/main` → ambos vacíos, sin divergencia.
- **F-INC-003** (nuevo, anotado): ADR formal `docs/architecture/16-multichannel-rick-channels.md` inexistente; D1-D6 vienen del task spec body. Sin acción tomada en este task; recomendado próximo task crearlo formalmente.

#### Archivos a commitear (solo task 025)

- `.agents/tasks/2026-05-07-025-copilot-vps-o151b-canal-notion-mention-router-oauth.md` (modificado: status pending → done + log)
- `scripts/notion/setup_rick_integration.py` (nuevo, 189 LoC)
- `scripts/notion/notion_mention_router.py` (nuevo, 100 LoC)
- `tests/test_notion_mention_router.py` (nuevo, 124 LoC)
- `docs/runbooks/rick-multichannel-setup.md` (nuevo, 179 LoC)

NO se commitea: reports `backfill-youtube-content-…` ni `stage4-push-…` (artefactos de task 013-K, fuera de scope).

Mantenimiento `~/.config/umbral/notion/.env.template` y `.env` (cuando David lo cree): per-host, fuera del repo, nunca se commitea.

#### Checklist David interactivo (gate de activación reply OAuth)

- [ ] D1: cuenta `rick.asistente@gmail.com` en Notion confirmada/creada.
- [ ] D2: invitada como guest del workspace.
- [ ] D3: integration `Rick Asistente CEO` creada con scopes mínimos (`Read content`, `Insert comments`, `Read user information without email`).
- [ ] D4: integration secret copiado.
- [ ] D5: secret pegado en `~/.config/umbral/notion/.env` (chmod 600).
- [ ] D6: páginas relevantes (incluido smoke page) compartidas con la integration.
- [ ] D7: `python scripts/notion/setup_rick_integration.py` exit 0.
- [ ] D8: smoke §5 del runbook ejecutado.
- [ ] D9: David autoriza implementación del reply handler con `NOTION_RICK_INTEGRATION_TOKEN` (próximo task).

Commit: `task(025): O15.1b canal Notion done — watcher polling [in-prod since Ola 1b] + skill notion-mention-router + runbook OAuth setup; reply OAuth autoría diferido a David (gate D1-D9)`. Push con F-INC-002 check.
