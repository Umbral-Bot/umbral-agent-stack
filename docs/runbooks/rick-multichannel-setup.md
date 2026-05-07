# Rick multichannel setup — Notion (canal #1)

> **Scope**: setup operativo del primer canal de Rick (Notion) end-to-end. OAuth identity, watcher, mention router, smoke. Tasks rectoras: 025 (este task) + ADR D1-D6 (identidad única / autoría OAuth / bypass prohibido / least-privilege / propose+confirm / whitelist).
>
> **Status overall**: detección + dispatch en producción desde Ola 1b. **OAuth identity Rick (`rick.asistente@gmail.com`) PENDIENTE** — David completar §2 antes de habilitar reply autoría real. Smoke §4 deferido.

---

## 0. Estado actual de infraestructura (read-only)

| Pieza                                  | Path / unit                                                                       | Status             |
| -------------------------------------- | --------------------------------------------------------------------------------- | ------------------ |
| Watcher polling daemon                 | `scripts/vps/notion-poller-daemon.py`                                             | **running** (cron `*/5` lo mantiene vivo) |
| Cron supervisor                        | `crontab` line `*/5 * * * * scripts/vps/notion-poller-cron.sh`                     | activo             |
| Mention detector                       | `dispatcher/rick_mention.py`                                                      | en producción      |
| Skill wrapper (canonical)              | `scripts/notion/notion_mention_router.py`                                         | nuevo (task 025)   |
| Tests                                  | `tests/test_rick_mention.py` (7) + `tests/test_notion_mention_router.py` (6)      | 13/13 passing      |
| Trace                                  | `~/.openclaw/trace/delegations.jsonl` (append-only)                               | activo             |
| Allowlist envvar                       | `DAVID_NOTION_USER_ID` en `~/.config/openclaw/env`                                | configurado        |
| Integration token (David)              | `NOTION_API_KEY` en `~/.config/openclaw/env`                                      | en uso (read+post) |
| **Integration token (Rick OAuth)**     | `~/.config/umbral/notion/.env` clave `NOTION_RICK_INTEGRATION_TOKEN`              | **vacío — David debe poblar** |
| Watcher mode                           | polling (decisión task 025 B1)                                                    | activo             |
| Latencia detección actual              | hasta 60 min (depende de `NOTION_POLL_AT_MINUTE` default `10`)                    | mitigable a 5 min  |

---

## 1. Decisión técnica — webhook vs polling

**Polling** ya en producción. Detalle completo + tabla comparativa en `/tmp/025/decision-watcher.md` (este task) y log de cierre del task 025. Tradeoffs principales:

- Polling: cero infra extra, auto-recover, dedupe Redis, pero latencia ≤ 60 min con config actual.
- Webhook: < 10s latencia pero requiere endpoint público + Caddy reverse-proxy nuevo (fuera de scope; prohibido sin autorización explícita).

Mejora opcional sin migrar a webhook:

```bash
# David ejecuta para reducir latencia a 5 min:
echo 'NOTION_POLL_INTERVAL_SEC=300' >> ~/.config/openclaw/env
# Reiniciar el daemon para que recoja la var:
PID=$(cat /tmp/notion_poller.pid 2>/dev/null) && [ -n "$PID" ] && kill "$PID"  # cron lo levanta de nuevo en < 5 min
```

---

## 2. OAuth setup — identidad `rick.asistente@gmail.com`

> **Por qué**: ADR D2 exige autoría real OAuth. Hoy todas las respuestas en Notion van firmadas como integration bot de David, no como Rick. Para cumplir D2 completamente y separar identidades, Rick necesita su propia integration con scopes mínimos.

### 2.1. Pasos David (interactivos — Notion UI)

> ⚠️ **secret-output-guard regla #8**: NUNCA pegar el integration secret en chat, comentarios, commits, ni en logs visibles. Solo en el archivo `~/.config/umbral/notion/.env` (chmod 600).

- [ ] **D1**. Crear / confirmar cuenta `rick.asistente@gmail.com` en Notion (login dedicado, separado del de David).
- [ ] **D2**. En el workspace personal de David, invitar a `rick.asistente@gmail.com` como **guest** (no admin). Validar que aparece en Settings → Members → Guests.
- [ ] **D3**. Crear integration en <https://www.notion.so/my-integrations>:
  - Name: `Rick Asistente CEO`
  - Associated workspace: el de David
  - Type: `Internal`
  - **Scopes mínimos** (tildar SOLO estas 3, ADR D4 least-privilege):
    - [ ] Read content
    - [ ] Insert comments
    - [ ] Read user information without email
- [ ] **D4**. Copiar el integration secret (formato `secret_xxxxxxxxxxxxxx`).
- [ ] **D5**. Pegar el secret en `~/.config/umbral/notion/.env` (crear desde template):
  ```bash
  cp ~/.config/umbral/notion/.env.template ~/.config/umbral/notion/.env
  chmod 600 ~/.config/umbral/notion/.env
  $EDITOR ~/.config/umbral/notion/.env  # pegar valor en NOTION_RICK_INTEGRATION_TOKEN=
  ```
- [ ] **D6**. Compartir explícitamente con la integration **solo** las páginas/databases donde Rick puede operar (Notion es share-per-page). Recomendación inicial: la página "Rick smoke 2026-05-07" + Control Room. NO compartir databases sensibles.

### 2.2. Auto-popular `NOTION_RICK_USER_ID` y `NOTION_WORKSPACE_ID` (Copilot VPS o David)

```bash
cd ~/umbral-agent-stack
source .venv/bin/activate
python scripts/notion/setup_rick_integration.py
# Esperado: log con fingerprint del token (NUNCA full token), bot name, y "Found rick user_id=… workspace_id=…".
# Si "User rick.asistente@gmail.com not found": volver a §2.1.D2 (invitar como guest) o §2.1.D6 (compartir página).
```

Exit codes:

| Código | Significado |
| ------ | ----------- |
| `0`    | OK, env actualizado |
| `2`    | Token vacío en .env (volver a §2.1.D5) |
| `3`    | Token inválido / API rechaza (rotar token, repetir D3-D5) |
| `4`    | Rick user no encontrado en workspace (D2/D6) |

Validar resultado:

```bash
grep -E '^(NOTION_RICK_USER_ID|NOTION_WORKSPACE_ID)=' ~/.config/umbral/notion/.env
# Ambas líneas deben tener uuid.
```

---

## 3. Skill `notion-mention-router`

- Wrapper canonical: `scripts/notion/notion_mention_router.py`. Re-exporta `is_rick_mention` y `handle_rick_mention` de `dispatcher.rick_mention` + agrega `route_one_mention(comment, *, allowlist, wc, queue, scheduler, page_kind=None)` para dispatch programático.
- Tests: `tests/test_notion_mention_router.py` (6) + `tests/test_rick_mention.py` (7) → **13/13 passing**.
- Comportamiento:
  - Filtra texto por regex `@rick` (case-insensitive, alias `@rick-orchestrator`).
  - Filtra author por `allowlist` (default `{DAVID_NOTION_USER_ID}` per ADR D6).
  - Enqueue envelope `task: rick.orchestrator.triage`, `team: rick-orchestrator`.
  - Escribe entry trace en `~/.openclaw/trace/delegations.jsonl` con `from: channel-adapter:notion-poller`, `to: rick-orchestrator`, intent `triage`.
  - Idempotencia: dedupe por `comment_id` en Redis (`umbral:notion_poller:processed_comment:*` TTL 24h, manejado por `dispatcher/notion_poller.py`).

---

## 4. Cron / activación (NO ejecutar hasta David autorice)

El cron de polling ya corre (§0). Lo que **NO** está activado y requiere autorización David:

- [ ] Reply path "Rick autorizado" usando `NOTION_RICK_INTEGRATION_TOKEN` (vs integration de David). Hoy las respuestas (cuando existan) postean con `NOTION_API_KEY` por el handler `worker.tasks.notion.handle_notion_add_comment`. Para activar autoría OAuth Rick:
  1. Completar §2 OAuth setup (token + IDs poblados).
  2. Implementar variant del handler que use `NOTION_RICK_INTEGRATION_TOKEN` cuando `team == "rick-orchestrator"` (NO en este task — escalar nuevo task si se requiere).
  3. Smoke §5 OK.
  4. David autoriza switch.

> **Salvavidas**: hasta que §2 + handler nuevo estén OK, el reply de Rick (cuando suceda) saldrá firmado como integration bot de David. Esto es funcionalmente correcto pero **viola D2 estrictamente**. Documentado como gap aceptado para Fase 1.

---

## 5. Smoke (David ejecuta — NO en task 025)

Pre-requisitos:

- §2 OAuth setup completo (`NOTION_RICK_USER_ID` poblado).
- Daemon polling vivo: `pgrep -f notion-poller-daemon` debe devolver PID.
- Worker /health OK: `curl -fsS http://127.0.0.1:8088/health | jq .ok` → `true`.

Pasos:

1. **David** crea página Notion "Rick smoke 2026-05-07" y la comparte con la integration (§2.1.D6).
2. **David** escribe en la página:
   ```
   @Rick, pingeá worker /health y devolveme el JSON acá como comentario.
   ```
3. Esperado:
   - Watcher detecta el comment dentro de N segundos (≤ 60 min config actual; ≤ 5 min si aplicó tweak §1; < 10 s si migra a webhook futuro).
   - Aparece entry en `~/.openclaw/trace/delegations.jsonl`:
     ```json
     {"from":"channel-adapter:notion-poller","to":"rick-orchestrator","intent":"triage", "ref":{"comment_id":"…","page_id":"…"}, ...}
     ```
   - Orchestrator nested respeta Reglas 21+22 SOUL (anti-faking + tool-gap workaround). Si reply path activado: comentario nuevo en la misma página firmado por Rick (autoría real OAuth si §4 hecho, integration bot si gap aún abierto).
   - Entry final con `assigned_to: agent:rick-orchestrator` honesta (NO fabricación rick-ops).

Verificación post-smoke:

```bash
tail -5 ~/.openclaw/trace/delegations.jsonl | jq -c '{ts, from, to, intent, ref}'
grep -c notion-poller ~/.openclaw/trace/delegations.jsonl  # debe haber subido ≥ 1
```

---

## 6. Troubleshooting rápido

| Síntoma                                                 | Causa probable                                | Fix                                                                   |
| ------------------------------------------------------- | --------------------------------------------- | --------------------------------------------------------------------- |
| `setup_rick_integration.py` exit 3                      | Token revocado o mal pegado                   | Rotar en my-integrations + repegar en `.env` (`chmod 600`)            |
| `setup_rick_integration.py` exit 4                      | Rick no es guest o página no compartida       | Invitar guest (§2.1.D2) y/o compartir página (§2.1.D6)                |
| Mention de David no se procesa                          | `DAVID_NOTION_USER_ID` mal en `~/.config/openclaw/env` | Validar UUID con `python scripts/notion/setup_rick_integration.py` (loguea workspace users) |
| Daemon polling muerto                                   | OOM / segfault                                | El cron `*/5 notion-poller-cron.sh` lo levanta automáticamente. Si persiste, `tail /tmp/notion_poller.log` |
| Latencia > 1h                                           | `NOTION_POLL_AT_MINUTE=10` corre solo XX:10   | Setear `NOTION_POLL_INTERVAL_SEC=300` (§1) y reiniciar daemon         |
| Entry duplicada en `delegations.jsonl`                  | Dedupe Redis se borró                         | Verificar Redis vivo: `redis-cli ping` → `PONG`. Restart dispatcher si necesario. |

---

## 7. Referencias

- Task 025 spec: `.agents/tasks/2026-05-07-025-copilot-vps-o151b-canal-notion-mention-router-oauth.md`
- ADR canales D1-D6 (inlined en task 025 spec; archivo formal `docs/architecture/16-multichannel-rick-channels.md` pendiente de creación, F-INC-003 anotado en log).
- Reglas SOUL 21+22: `~/.openclaw/workspaces/rick-orchestrator/SOUL.md` (task 023).
- Trace canónico: `~/.openclaw/trace/delegations.jsonl`.
- Decisión watcher: `/tmp/025/decision-watcher.md` (snapshot de cierre task 025).
