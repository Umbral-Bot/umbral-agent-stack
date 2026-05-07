# Rick multichannel setup — Notion (canal #1)

> **Scope**: setup operativo del primer canal de Rick (Notion) end-to-end. Detección, dispatch, reply, smoke. Tasks rectoras: 023 (SOUL Reglas 21+22) → 025 (skill wrapper + scaffold) → **026 (modelo bot integration confirmado, H1 string match)**.
>
> **Status overall**: detección + dispatch + reply en producción desde Ola 1b. Identidad final del agente en Notion = **integration bot "Rick"** (no usuario humano). D2 ADR (autoría OAuth real) **relajada permanente** para canal Notion (ver `notion-governance/docs/architecture/16-multichannel-rick-channels.md` §6 fila 2026-05-07).

---

## 0. Estado actual de infraestructura (read-only)

| Pieza                                  | Path / unit                                                                       | Status             |
| -------------------------------------- | --------------------------------------------------------------------------------- | ------------------ |
| Watcher polling daemon                 | `scripts/vps/notion-poller-daemon.py`                                             | **running** (cron `*/5` lo mantiene vivo) |
| Cron supervisor                        | `crontab` line `*/5 * * * * scripts/vps/notion-poller-cron.sh`                     | activo             |
| Mention detector                       | `dispatcher/rick_mention.py`                                                      | en producción      |
| Skill wrapper (canonical)              | `scripts/notion/notion_mention_router.py`                                         | task 025           |
| Tests                                  | `tests/test_rick_mention.py` (7) + `tests/test_notion_mention_router.py` (6)      | 13/13 passing      |
| Trace                                  | `~/.openclaw/trace/delegations.jsonl` (append-only)                               | activo             |
| Allowlist envvar                       | `DAVID_NOTION_USER_ID` en `~/.config/openclaw/env`                                | configurado (uuid 36) |
| Integration token "Rick"               | `NOTION_API_KEY` en `~/.config/openclaw/env`                                      | en uso (read+post). Bot id `3145f443-fb5c-814d-bbd1-0027093cebce`, name=`Rick`, workspace=`Umbral BIM`. |
| Páginas/DBs conectadas a integration   | 15 (David 2026-05-07)                                                              | Páginas, Registro de Tareas, Publicaciones, Referentes, Publicaciones de Referentes, Alertas del Supervisor, Clientes y Partners, Fuentes, Gobernanza Notion, Implementación Agente ACC Copilot - Claude, Mi Perfil, OpenClaw, Sistema Editorial Rick, Umbral BIM, Asesorías & Proyectos, Referencias |
| Página objetivo del polling            | `NOTION_CONTROL_ROOM_PAGE_ID` (single-page scope)                                 | configurado        |
| Watcher mode                           | polling                                                                           | activo             |
| Latencia detección actual              | hasta 60 min (depende de `NOTION_POLL_AT_MINUTE` default `10`)                    | mitigable a 5 min  |

---

## 1. Modelo de identidad (decisión 2026-05-07, task 026)

**Identidad final visible de Rick en Notion = integration bot "Rick"** (preexistente, owner=workspace, name="Rick", id `3145f443…7093cebce`).

Razones (David 2026-05-07):

- Crear seat humano `rick.asistente@gmail.com` requería suscripción extra.
- Notion no permite invitar bots como members; la distinción "humano vs bot" en autoría visible es aceptable para el flujo conversacional con David.
- D2 ADR (autoría OAuth real) queda **relajada permanente** SOLO para canal Notion; aplica para futuros canales (Telegram, Linear, Email) caso por caso.

**Cancela cualquier futuro task de "reply OAuth autoría Rick" en Notion.** El reply path actual (`NOTION_API_KEY` integration) es la solución final, no transitoria.

---

## 2. Decisión técnica — webhook vs polling

**Polling** ya en producción. Tradeoffs:

- Polling: cero infra extra, auto-recover, dedupe Redis, latencia ≤ 60 min con config actual.
- Webhook: < 10 s latencia pero requiere endpoint público + Caddy reverse-proxy nuevo (fuera de scope; prohibido sin autorización explícita).

Mejora opcional sin migrar a webhook:

```bash
# David ejecuta para reducir latencia a 5 min:
echo 'NOTION_POLL_INTERVAL_SEC=300' >> ~/.config/openclaw/env
PID=$(cat /tmp/notion_poller.pid 2>/dev/null) && [ -n "$PID" ] && kill "$PID"  # cron lo levanta de nuevo en < 5 min
```

---

## 3. Mention mechanism (verificado en task 026 — hipótesis H1)

**El watcher dispara por string match `@rick` (regex), NO por mention.user.id.**

Detección en `dispatcher/rick_mention.py`:

```python
_RICK_MENTION_RE = re.compile(r"@rick(?:-orchestrator)?\b", re.IGNORECASE)
```

Pasos del watcher (verificado contra código en commit `5d62c5d`):

1. Cron `*/5` mantiene vivo `scripts/vps/notion-poller-daemon.py`.
2. `dispatcher.notion_poller` llama `wc.notion_poll_comments(page_id=NOTION_CONTROL_ROOM_PAGE_ID, …)` cada `NOTION_POLL_INTERVAL_SEC` (o cada hora a XX:10 si no seteado).
3. `worker.notion_client.poll_comments` → `GET https://api.notion.com/v1/comments?block_id=<page_id>` con `Authorization: Bearer NOTION_API_KEY`.
4. Para cada comment retornado:
   - Skip si `text` empieza con `Rick:` (echo prevention del propio reply).
   - Skip si Redis dedupe lo marca como ya procesado (TTL 24h).
   - **Si `is_rick_mention(text, created_by, {DAVID_NOTION_USER_ID})` → True**:
     - `handle_rick_mention()` enqueue envelope `task: rick.orchestrator.triage`, `team: rick-orchestrator`.
     - Append a `~/.openclaw/trace/delegations.jsonl` (`from: channel-adapter:notion-poller`).
   - Else → fallback `intent_classifier` + `smart_reply`.

### Implicancias UX para David

- **Comentar `@rick ...` o `@Rick ...` en plain text** dentro de la Control Room. Word-boundary `\b`, case-insensitive. Alias `@rick-orchestrator` también funciona.
- **NO** es necesario usar el dropdown nativo `@` de Notion (no podríamos: el bot no es @-mencionable como user). Es texto literal.
- **Scope single-page**: el polling solo lee la página apuntada por `NOTION_CONTROL_ROOM_PAGE_ID`. Los comments en las otras 14 páginas conectadas a la integration **no disparan el mention router** (sí pueden disparar otros workflows del poller, pero ese es scope distinto).
- **Allowlist autor**: solo `DAVID_NOTION_USER_ID`. Comments de cualquier otro autor son ignorados por el mention path (D6 ADR least-privilege/whitelist).

### Env vars consumidas (verificado, no spec)

| Var                              | Consumida en                                                         | Uso                                                                  |
| -------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------- |
| `NOTION_API_KEY`                 | `worker/notion_client.py`                                            | Único token del poller (es la integration "Rick").                  |
| `NOTION_CONTROL_ROOM_PAGE_ID`    | `dispatcher/notion_poller.py:210`                                    | Página objetivo del polling.                                        |
| `DAVID_NOTION_USER_ID`           | `dispatcher/rick_mention.py:_david_allowlist`                        | Allowlist autor.                                                    |
| `NOTION_POLL_AT_MINUTE`          | `dispatcher/notion_poller.py:498`                                    | Default 10 → polling solo XX:10 si interval no seteado.             |
| `NOTION_POLL_INTERVAL_SEC`       | `dispatcher/notion_poller.py:497`                                    | Override de at_minute (recomendado 300 para latencia 5 min).         |
| `NOTION_POLL_OVERLAP_SEC`        | `dispatcher/notion_poller.py:103`                                    | Buffer hacia atrás para comments de borde.                          |
| `REDIS_URL` / `WORKER_URL` / `WORKER_TOKEN` | `dispatcher/notion_poller.py:494-496`                       | Conexiones internas.                                                |

**No se consume `NOTION_RICK_USER_ID` en producción.** El script `scripts/notion/setup_rick_integration.py` (task 025) escribía ese valor pero nada lo leía. Marcado deprecated en task 026; solo corre con `--force-deprecated`.

---

## 4. Skill `notion-mention-router`

- Wrapper canonical: `scripts/notion/notion_mention_router.py`. Re-exporta `is_rick_mention` y `handle_rick_mention` de `dispatcher.rick_mention` + agrega `route_one_mention(comment, *, allowlist, wc, queue, scheduler, page_kind=None)`.
- Tests: `tests/test_notion_mention_router.py` (6) + `tests/test_rick_mention.py` (7) → **13/13 passing**.

---

## 5. Smoke

Pre-requisitos:

- Daemon polling vivo: `[ -f /tmp/notion_poller.pid ] && kill -0 $(cat /tmp/notion_poller.pid)`.
- Worker /health OK: `curl -fsS http://127.0.0.1:8088/health | jq .ok` → `true`.
- `NOTION_API_KEY`, `NOTION_CONTROL_ROOM_PAGE_ID`, `DAVID_NOTION_USER_ID` poblados en `~/.config/openclaw/env`.
- Verificar bot identity (read-only):
  ```bash
  set -a; source ~/.config/openclaw/env; set +a
  curl -fsS https://api.notion.com/v1/users/me \
    -H "Authorization: Bearer $NOTION_API_KEY" \
    -H "Notion-Version: 2022-06-28" \
    | jq '{id, type, name, workspace_name: .bot.workspace_name}'
  # Esperado: {"id":"3145f443-…","type":"bot","name":"Rick","workspace_name":"Umbral BIM"}
  ```

Pasos:

1. **David** va a la página Control Room (la apuntada por `NOTION_CONTROL_ROOM_PAGE_ID`).
2. Postea un comentario en plain text:
   ```
   @Rick ping worker /health y devolveme el JSON acá como reply
   ```
3. Espera ≤ N min (≤ 60 min config default; ≤ 5 min con `NOTION_POLL_INTERVAL_SEC=300`).
4. **Copilot VPS** verifica:
   ```bash
   tail -50 /tmp/notion_poller.log | grep -i "rick mention routed"
   tail -5 ~/.openclaw/trace/delegations.jsonl | jq -c '{from, to, intent, ref}'
   ```
   Debe haber:
   - Línea `Rick mention routed: comment=… author=… page=… trace=…` en `notion_poller.log`.
   - Entry nueva en `delegations.jsonl` con `from: channel-adapter:notion-poller`, `to: rick-orchestrator`, `intent: triage`.
5. Reply: la integration "Rick" postea un comentario en la misma página con la respuesta del orchestrator. Autor visible en UI = `Rick (integration bot)`.

### Failure triage

- **No `Rick mention routed` log line**: regex no matcheó (texto del comment sin `@rick`) o autor no en allowlist (verificar `DAVID_NOTION_USER_ID`).
- **Routed pero no reply**: orchestrator falló. NO arreglar en task de canal — abrir task separado con captura de logs.
- **`/v1/users/me` devuelve 401**: `NOTION_API_KEY` corrupto o revocado en `~/.config/openclaw/env`. Escalar a David.

---

## 6. Cron / activación

Cron de polling y reply path **activos**. No requiere autorización adicional (D2 relajada permanente cierra el último gap conceptual).

Reply path: `worker.tasks.notion.handle_notion_add_comment` usa `NOTION_API_KEY` (= integration "Rick"). Autor visible = bot Rick. ✅ aceptado como modelo final.

---

## 7. Troubleshooting rápido

| Síntoma                                                 | Causa probable                                | Fix                                                                   |
| ------------------------------------------------------- | --------------------------------------------- | --------------------------------------------------------------------- |
| Mention de David no se procesa                          | `DAVID_NOTION_USER_ID` mal o página fuera de Control Room | Validar UUID; postear en Control Room (no en otras 14 páginas) |
| `/v1/users/me` 401                                      | `NOTION_API_KEY` revocado                     | Rotar integration secret en my-integrations + actualizar env + restart daemon |
| Daemon polling muerto                                   | OOM / segfault                                | El cron `*/5 notion-poller-cron.sh` lo levanta. Si persiste, `tail /tmp/notion_poller.log` |
| Latencia > 1h                                           | `NOTION_POLL_AT_MINUTE=10` corre solo XX:10   | Setear `NOTION_POLL_INTERVAL_SEC=300` (§2) y reiniciar daemon         |
| Entry duplicada en `delegations.jsonl`                  | Dedupe Redis se borró                         | Verificar Redis vivo: `redis-cli ping` → `PONG`. Restart dispatcher si necesario. |
| Reply firmado distinto de "Rick"                        | `NOTION_API_KEY` apunta a otra integration    | `/v1/users/me` debe devolver `name: "Rick"`                           |

---

## 8. Checklist legacy D1-D9 (obsoleto post-2026-05-07)

| Item | Estado          | Nota                                                                          |
| ---- | --------------- | ----------------------------------------------------------------------------- |
| D1   | N/A             | No se crea cuenta humana `rick.asistente@gmail.com`.                          |
| D2   | N/A             | No se invita guest. Bot integration NO es member.                             |
| D3   | DONE (preexistente) | Integration "Rick" creada antes del task 025. Token en `NOTION_API_KEY`.   |
| D4   | DONE            | Token capturado en `NOTION_API_KEY`.                                          |
| D5   | DONE            | Token preexistente; `~/.config/umbral/notion/.env` scaffold del task 025 NO usado. |
| D6   | DONE (15 páginas) | Conexiones manuales David 2026-05-07.                                       |
| D7   | DEPRECATED      | `setup_rick_integration.py` ya no necesario (H1 → no se consume `NOTION_RICK_USER_ID`). Corre solo con `--force-deprecated`. |
| D8   | DONE post-smoke | Validación end-to-end en task 026 §5.                                         |
| D9   | CANCEL          | D2 relajada permanente (ADR16 §6 fila 2026-05-07 commit `820a2a8` notion-governance). |

---

## 9. Referencias

- Task 026 spec: `.agents/tasks/2026-05-07-026-copilot-vps-validar-mention-detection-bot-integration.md`
- Task 025 spec: `.agents/tasks/2026-05-07-025-copilot-vps-o151b-canal-notion-mention-router-oauth.md`
- ADR canales D1-D6 + §6 fila 2026-05-07: `notion-governance/docs/architecture/16-multichannel-rick-channels.md` (commit `820a2a8`).
- Reglas SOUL 21+22: `~/.openclaw/workspaces/rick-orchestrator/SOUL.md` (task 023).
- Trace canónico: `~/.openclaw/trace/delegations.jsonl`.
- B1 archeology task 026: `/tmp/026/code-archeology.md` (working note local).
- B2 bot identity task 026: `/tmp/026/bot-user.md` (working note local).
