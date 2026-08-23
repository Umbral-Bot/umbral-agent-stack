# `infra/n8n/` — workflows de bordes n8n (export a git)

Home canónico de los workflows n8n de **bordes** del Agent Stack. Nace con el
paquete **N0** de la propuesta
[n8n-notion-integration-proposal-post-smoke-2026-07-24](../../docs/ops/n8n-notion-integration-proposal-post-smoke-2026-07-24.md)
y está gobernado por
[ADR-011](../../docs/adr/ADR-011-orquestacion-editorial-criterios-duros.md).

> **Runtime = n8n del VPS** (el Worker escucha en loopback `127.0.0.1:8088`).
> n8n **Cloud** es solo sandbox/lab **sin** `WORKER_TOKEN` (§3 de la propuesta).
> El MCP de instancia disponible en tooling (Cursor/Claude) apunta hoy a la
> instancia **Cloud/personal**, no al VPS — sirve para *autoría/validación*,
> nunca como runtime del pipeline (§2.B5).

## RRSS-vía-n8n: cerrado (2026-08-21, Q10)

La instancia n8n del VPS solo tiene **B1 y B3** — los 4 workflows editoriales
y los 2 SIM que E-p11 (2026-08-12) encontró `active=false` y sin versionar
(stubs de 2 nodos, marzo 2026, nunca ejecutados) fueron exportados y borrados
del VPS el 2026-08-21 [PKG-MACRO-P5-Q10-T1]. Exports scrubbed en
[`archive/killed-2026-08-21/`](archive/killed-2026-08-21/) (no en
`workflows/` — ver anti-patrón #1 más abajo). RRSS-vía-n8n queda cerrado como
binaria: no se reconstruye, no se reactiva. Detalle:
[docs/operations/q10-n8n-killed-2026-08-21.md](../../docs/operations/q10-n8n-killed-2026-08-21.md).

## Qué vive acá

`workflows/*.json` — export literal (formato Import/Export de la UI de n8n) de
cada workflow productivo. **Un workflow que existe solo en el VPS no existe**
(anti-patrón #5): un disk-crash lo borra. El export es la fuente de verdad
versionada.

| Archivo | Borde | Estado en este pack | Qué hace |
|---|---|---|---|
| [`workflows/telegram-ok-publica-b1.json`](workflows/telegram-ok-publica-b1.json) | **B1 / N1** | **ACTIVO con bot TEST** desde 2026-07-25 (smoke PASS) | Telegram Trigger → doble allowlist (chat_id + from.id) → parse `ok publica <publication_id>` → `POST /enqueue` `web.publish_editorial_post` con `telegram_confirmed:true`. Sin match → reply corto y STOP. |
| [`workflows/worker-health-cron-b3.json`](workflows/worker-health-cron-b3.json) | **B3 / N3-lite** | **ACTIVO con bot TEST** (smoke PASS previo) | Schedule (15 min) → `GET /health` del Worker → si falla tras reintentos, alerta Telegram a David. Nada más (sin scan HITL-2, ver N3b). |

> **El sufijo `(INACTIVE)` en el *nombre* se sacó (2026-08-22, [PKG-MACRO-P5-T8-T1](../../docs/operations/t8-n8n-b1b3-rename-2026-08-22.md))** —
> mentía: ambos estaban `active=true` desde antes. Rename vía la API REST
> documentada de la instancia (la CLI no tiene verbo de rename), sin tocar
> nodos, credenciales, cron ni webhook. `active` de cada JSON ahora coincide
> con el live.

Runbook de activación (WEBHOOK_URL/TLS, timezone, backup encryption key, alta de
credenciales, import y GO por bot de test): [docs/ops/n8n-n0-foundations-runbook-2026-07-24.md](../../docs/ops/n8n-n0-foundations-runbook-2026-07-24.md).

## Convención de export

1. **Naming**: `<borde-o-función>-<código>.json` en kebab-case, prefijo por
   borde cuando aplica (`telegram-ok-publica-b1`, `worker-health-cron-b3`).
2. **Cómo exportar**: manual, en la UI del VPS (abrir el workflow → menú `⋯`
   → **Download**), o vía CLI (`n8n export:workflow --id=<id> --pretty`,
   usado en [PKG-MACRO-P5-T8-T1](../../docs/operations/t8-n8n-b1b3-rename-2026-08-22.md)
   por no requerir sesión de UI). Ambos producen JSON válido para este repo;
   el formato de indentado difiere. Reemplazar el `.json` acá y abrir PR.
   (Export nocturno automatizado documentado en el runbook §"Export a git".)
3. **`active` refleja el estado real** del workflow al momento del export. El
   pack N0 original (2026-07-24) shippeó ambos con `active:false` a propósito
   (nada productivo hasta GO); desde entonces ambos pasaron a `active:true`
   con bot TEST — ver tabla arriba.
4. **Credenciales por NOMBRE, jamás por valor** (anti-patrón #6). En el JSON las
   credenciales aparecen como `{ "id": "...", "name": "<nombre legible>" }` —
   solo `id` + `name`, **cero secretos**. En import, un humano re-vincula la
   credencial real. Los `id` acá son siempre `REPLACE_ON_IMPORT` — un export
   crudo de la CLI trae los `id` reales de la instancia; hay que volver a
   sustituirlos antes de commitear (no son secretos, pero un import a otra
   instancia con esos `id` reales apuntaría a una credencial equivocada o
   inexistente en vez de forzar el relink humano).
5. **URLs por variable de entorno** (anti-patrón #7): los nodos usan
   `={{ $env.WORKER_URL }}/...`, nunca `127.0.0.1:8088` hardcodeado. Ver
   `.env.example` y el runbook para las env vars de n8n.

## Anti-patrones (ADR-011 — rechazo automático en PR)

- **#1** n8n **nunca** escribe Notion. Su única salida al dominio es
  `POST /enqueue` al Worker (`Authorization: Bearer $WORKER_TOKEN`). El Worker
  es el único escritor de Notion.
- **#3 / §4.4** Nada de **Notion Trigger nativo** (polling) en producción —
  duplica el Notion Poller del core y quema cuota. La vía event-driven correcta
  es B2 (webhook oficial → nodo Webhook), fuera de este pack.
- **§4.3** Nunca adjuntar el nodo Notion como *AI-agent tool* (expondría los
  writes a un LLM).
- **#5** Todo workflow productivo se exporta acá.
- **#6** Credenciales por nombre, cifradas con `N8N_ENCRYPTION_KEY` en el VPS.
- **#7** URLs entre motores en env vars, documentadas en `.env.example`.

Estos invariantes se verifican en CI: [`tests/test_n8n_workflows_governance.py`](../../tests/test_n8n_workflows_governance.py)
falla el PR si algún `workflows/*.json` reintroduce el nodo Notion (write o
tool), el Notion Trigger nativo, credenciales con claves fuera de `id`/`name`,
o cualquier clave portadora de secreto embebida.

## Credenciales e IDs que David completa (nombres, no valores)

Ver el runbook para el detalle. Resumen de lo que hay que crear/confirmar en el
n8n del VPS antes de activar:

- Credencial **`Telegram Bot — Umbral Editorial (TEST)`** (tipo `telegramApi`) —
  bot de **test** primero; el de prod es un bot separado (Telegram admite un
  solo webhook por bot). Un `telegramApi` "Telegram account" ya existe en la
  instancia Cloud, pero el runtime es el VPS: crear/confirmar allí.
- Credencial **`Umbral Worker Bearer (WORKER_TOKEN)`** (tipo `httpBearerAuth`) —
  el `WORKER_TOKEN` del Worker, como Bearer. **Solo el humano** la vincula.
- Env vars de n8n (VPS): `WORKER_URL`, `TELEGRAM_ALLOWED_CHAT_ID`,
  `TELEGRAM_ALLOWED_USER_ID`, `GENERIC_TIMEZONE`, y `WEBHOOK_URL` para el
  ingress de Telegram. Valores → runbook.
