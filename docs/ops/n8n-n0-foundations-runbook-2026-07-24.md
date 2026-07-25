# Runbook N0 — Fundaciones n8n (bordes) — 2026-07-24

> **Estado:** N0 entregado en repo (directorio + export + README + este runbook
> + guard CI). Los pasos marcados **[VPS — GO David]** requieren acceso al VPS y
> **no** se ejecutan desde el PR. Nada se activa hasta GO explícito por borde.
> **Marco:** [propuesta n8n↔Notion](n8n-notion-integration-proposal-post-smoke-2026-07-24.md)
> §5 (N0/N1/N3) + [ADR-011](../adr/ADR-011-orquestacion-editorial-criterios-duros.md)
> (hereda costos operativos de [ADR-008](../adr/ADR-008-orquestacion-editorial.md)).

Este runbook cubre el paquete **N0** y el import/activación de los workflows
**N1 (B1)** y **N3-lite (B3)** que viajan en el mismo PR, **inactivos**.

---

## 0. Evidencia de estado n8n (lo verificable hoy + lo BLOCKED)

| Ítem | Estado | Evidencia / nota |
|---|---|---|
| Instancia n8n alcanzable por tooling MCP | **Cloud/personal** (no VPS) | El MCP de instancia disponible en Cursor/Claude lista 16 workflows del proyecto personal `David … <david.moreira@butic.es>` (Speckle/AEC/Master AEC). Es el **sandbox** de §3, no el runtime de bordes. Autoría/validación OK; **runtime NO**. |
| Credenciales pre-existentes (por nombre) | Visible en Cloud | Hay `telegramApi` ("Telegram account"), `httpBearerAuth` ("Automatizacion_speckle"), `notionApi` ("Notion account"/"Notion account 2"). Son de la instancia Cloud — **no** presumir que existen en el VPS. |
| Versión n8n del **VPS**, URL loopback, módulo MCP on/off en VPS | **BLOCKED** (sin acceso VPS desde el PR) | Completar en §6. Comandos abajo. |

**[VPS — GO David]** Evidenciar sin secretos, y pegar el resultado como comentario del PR (no en git):

```bash
# versión y healthz de n8n (loopback del VPS)
curl -s http://127.0.0.1:5678/healthz ; echo
docker ps --format '{{.Names}}\t{{.Image}}' | grep -i n8n   # si corre en docker
# módulo MCP: ¿está deshabilitado?
printenv N8N_DISABLED_MODULES        # esperado "mcp" si se mantiene apagado (§2.B5)
printenv GENERIC_TIMEZONE WEBHOOK_URL N8N_HOST N8N_PROTOCOL
# NUNCA imprimir N8N_ENCRYPTION_KEY ni WORKER_TOKEN
```

---

## 1. Reverse proxy: `WEBHOOK_URL` + TLS + websockets  **[VPS — GO David]**

Requerido por el Telegram Trigger de B1 (webhook entrante HTTPS público) y por
la UI. La doc n8n exige, detrás de reverse proxy self-host:

- `N8N_HOST`, `N8N_PROTOCOL=https`, y **`WEBHOOK_URL=https://<dominio-n8n>/`**
  (sin esto, el webhook que Telegram registra apunta mal).
- **TLS** terminado en el proxy (Caddy/nginx/Traefik) con cert válido.
- **WebSockets** habilitados en el proxy (`Upgrade`/`Connection` headers) — la
  UI de n8n y el push los necesitan.

Checklist de verificación tras configurar:

```bash
curl -sI https://<dominio-n8n>/    # 200/302 con cert válido
# En n8n: Settings → un webhook de prueba debe mostrar URL https://<dominio-n8n>/webhook/...
```

> **Telegram = 1 webhook por bot.** Bot de **test** y bot de **prod** son bots
> distintos, cada uno con su credencial `telegramApi`. Activar B1 primero con el
> bot de test.

### 1.1 Implementado 2026-07-25 — camino B (Caddy + Let's Encrypt)

Se evaluaron los dos caminos y se eligió **B**:

- **A (Tailscale Funnel) — descartado.** El tailnet existe y el nodo tiene cert
  propio (`*.ts.net`), pero el atributo `funnel` **no está en la policy del
  tailnet**, así que habilitarlo exige editar el ACL en la consola admin de
  Tailscale (checkpoint humano). Además `tailscale serve` ya está ocupado por el
  gateway OpenClaw en `:18789`, y superponer Funnel ahí arriesga publicarlo.
  Cloudflare Tunnel quedó fuera por la misma razón: `cloudflared` no está
  instalado y haría falta login de la cuenta CF.
- **B (elegido) — sin comprar dominio y sin checkpoint.** Hostinger ya asigna al
  VPS el hostname público `srv1431451.hstgr.cloud`, con **A y AAAA apuntando a
  este host**. Además `hstgr.cloud` está en la *Public Suffix List*, así que Let's
  Encrypt lo trata como dominio registrado propio (cupo de rate-limit propio, sin
  competir con el resto de los VPS Hostinger).

Piezas:

| Pieza | Dónde | Nota |
|---|---|---|
| Proxy TLS | `/etc/caddy/Caddyfile` (Caddy 2.11.4, systemd `caddy.service`) | cert LE automático + renovación |
| Env de n8n | `~/.config/systemd/user/n8n.service.d/10-https.conf` | `WEBHOOK_URL`, `N8N_HOST`, `N8N_PROTOCOL`, `N8N_LISTEN_ADDRESS`, `N8N_PROXY_HOPS` |
| ufw | `80/tcp` + `443/tcp` (v4 y v6) | única apertura nueva; el resto sigue en deny |

**Surface público mínimo.** Caddy publica **solo `/webhook*`**; todo lo demás
responde `404`. La UI de n8n **no** se expone: la instancia tiene
`userManagement.isInstanceOwnerSetUp=false` (sin dueño ni login), así que
publicarla dejaría que cualquiera la reclame con el wizard de owner. Acceso a la
UI por túnel SSH:

```bash
ssh -L 5678:127.0.0.1:5678 rick@srv1431451.hstgr.cloud   # -> http://localhost:5678
```

En el mismo movimiento n8n dejó de escuchar en `*:5678` (todas las interfaces,
incluida la pública) y pasó a `127.0.0.1` vía `N8N_LISTEN_ADDRESS`.

> **El `webhookId` real no se commitea.** El export del repo conserva
> `REPLACE_ON_IMPORT_TELEGRAM_WEBHOOK` a propósito: n8n deriva el secret de
> Telegram como `` `${workflowId}_${nodeId}` `` (`getSecretToken()` en
> `n8n-nodes-base/dist/nodes/Telegram/GenericFunctions.js`), y ambos ids están en
> el JSON versionado. Si además se publicara el `webhookId`, cualquiera con acceso
> al repo podría forjar updates contra el endpoint público. La ruta real vive solo
> en el VPS.

### 1.2 n8n 2.10 corre la versión **publicada**, no el draft

n8n 2.x separa *draft* de *published*: `workflow_entity.activeVersionId` apunta a
la versión que realmente ejecuta, y al arrancar loguea
`Processed N draft workflows, M published workflows`. Guardar cambios en la UI
(o `import:workflow`) toca el **draft**; hasta publicar, el runtime sigue con la
versión vieja — incluido el re-vinculado de credenciales. Por eso `update:workflow`
quedó **deprecado**:

```bash
n8n publish:workflow --id=<workflowId>     # publica la versión actual
systemctl --user restart n8n               # el CLI avisa: no aplica con n8n corriendo
```

---

## 2. `GENERIC_TIMEZONE`  **[VPS — GO David]**

Default self-host de n8n = `America/New_York` → hay que fijarlo. **Propuesta:
`America/Santiago`** (operación de David, CL). El export de B3 ya pin-ea
`settings.timezone = America/Santiago` a nivel workflow para el cron; igual
conviene fijar el default de instancia:

```bash
# en el env del servicio/contenedor n8n:
GENERIC_TIMEZONE=America/Santiago
```

Confirmar contra la realidad del VPS (si el host está en UTC y hay preferencia
distinta, ajustar aquí y en `settings.timezone` del B3 antes de activar).

---

## 3. Backup de `N8N_ENCRYPTION_KEY` fuera del VPS  **[VPS — GO David]**

Riesgo **crítico** heredado (ADR-011 #6 / ADR-008): las credenciales viven
cifradas con esta clave en la DB de n8n. Perderla sin backup = perder todas las
credenciales. **No pegar el valor en el PR ni en git.** Solo verificar
existencia + custodia:

```bash
# ¿dónde está definida? (ver la fuente, no el valor)
grep -rl N8N_ENCRYPTION_KEY /etc /opt 2>/dev/null      # localizar el archivo de env
# confirmar que hay backup fuera del VPS (gestor de secretos / bóveda de David)
```

Acción: si no hay backup off-VPS confirmado, crear uno en el gestor de secretos
personal **antes** de activar cualquier borde, y anotar la ubicación (no el
valor) en el gestor. Procedimiento de restore probado = pendiente DR (ADR-011
§Deuda técnica 5).

---

## 4. Alta de credenciales en n8n del VPS (nombres, no valores)  **[VPS — GO David]**

| Nombre de credencial | Tipo n8n | Contenido | Usada por |
|---|---|---|---|
| `Umbral Worker Bearer (WORKER_TOKEN)` | `httpBearerAuth` | el `WORKER_TOKEN` del Worker como Bearer | B1 → `POST /enqueue` |
| `Telegram Bot — Umbral Editorial (TEST)` | `telegramApi` | token del **bot de test** | B1 (trigger + replies), B3 (alerta) |
| `Telegram Bot — Umbral Editorial (PROD)` | `telegramApi` | token del **bot de prod** | B1/B3 al pasar a prod (bot distinto) |

La vinculación credencial↔valor la hace **un humano** en la UI (los JSON traen
`id: REPLACE_ON_IMPORT` + el `name`). El `httpBearerAuth` setea
`Authorization: Bearer <token>` automáticamente — no poner el token en headers
del nodo.

### Env vars de n8n (VPS)

```bash
WORKER_URL=http://127.0.0.1:8088          # loopback al Worker (ver caveat §5)
TELEGRAM_ALLOWED_CHAT_ID=<chat_id David>  # allowlist dura (trigger + IF)
TELEGRAM_ALLOWED_USER_ID=<user_id David>
GENERIC_TIMEZONE=America/Santiago
WEBHOOK_URL=https://<dominio-n8n>/
```

---

## 5. Reachability n8n → Worker (caveat de red)  **[VPS — GO David]**

`WORKER_URL=http://127.0.0.1:8088` asume n8n **co-localizado** con el Worker en
el mismo host loopback (consistente con `.env.example` `N8N_URL=127.0.0.1:5678`).
**Si n8n corre en un contenedor**, `127.0.0.1` es el contenedor, no el host:
usar host-gateway (`http://host.docker.internal:8088`, con
`--add-host=host.docker.internal:host-gateway`) o red host. Verificar antes de
activar:

```bash
# desde dentro del entorno de ejecución de n8n:
curl -s $WORKER_URL/health ; echo    # debe responder {"ok":true,...}
```

El Worker permanece en **loopback** — nunca se expone a internet (§4.8). Solo
n8n se acerca al Worker, no al revés.

---

## 6. Import + activación de B1 / B3  **[VPS — GO David]**

1. **Import**: UI n8n → *Import from File* → `telegram-ok-publica-b1.json` y
   `worker-health-cron-b3.json`. Quedan **inactivos** (así vienen).
2. **Vincular credenciales** (§4) en cada nodo `telegramApi` / `httpBearerAuth`.
3. **Setear env vars** (§4).
4. **Smoke con bot de TEST** (no prod):
   - B1: mandar `ok publica <publication_id-de-prueba>` desde el chat de David.
     Verificar en *Executions* que llamó `POST /enqueue`. **El Worker aplica el
     D3**: sin `autorizar_publicacion` + gate visual en Notion, no publica —
     `telegram_confirmed:true` solo aporta el tercer leg (ver evidencia dry-run
     Worker en el informe del PR, patrón smoke G.2). Un texto que no matchea
     `ok publica <id>` → reply "formato no reconocido", **sin** `/enqueue`.
   - B3: forzar un fallo (parar el Worker un ciclo, o apuntar `WORKER_URL` a un
     puerto muerto temporalmente) → debe llegar **una** alerta Telegram. Con el
     Worker arriba, camino feliz = no-op silencioso (sin spam).
5. **GO David** explícito, **una cosa a la vez** (protocolo smoke §GO David):
   activar B3 (bajo riesgo) primero; B1 después, aún con **bot de test**;
   recién con confianza, migrar B1 al **bot de prod** (credencial PROD).
6. **Re-export a git** si la UI cambió algo en el import (IDs de credencial se
   re-escriben a `REPLACE_ON_IMPORT` antes de commitear, o se deja el `id` real
   solo si no es secreto — el guard CI exige únicamente `id`+`name`).

---

## 7. Export a git (anti-patrón #5)  **[VPS — GO David]**

Manual: UI → workflow → `⋯` → *Download* → reemplazar el `.json` en
`infra/n8n/workflows/` → PR. Automatizable como cron nocturno (`n8n export:workflow
--all --output ...` + commit); documentar el cron cuando se implemente. Un
workflow productivo que no está acá **no existe**.

---

## 8. N3b pendiente (fuera de este pack)

Este pack **no** incluye la alerta de filas HITL-2 listas (solo health-check).
Cuando se retome (N3b), elegir mecanismo (propuesta §2.B3), **con GO aparte**:

- **(a) Poller emite, n8n transporta** (preferida, sin código Worker nuevo):
  activar `NOTION_POLLER_ENABLE_HITL2_SCAN` (log-only, ya fail-closed) y que el
  poller/scan notifique; n8n queda como canal Telegram saliente.
- **(b) Task Worker nueva read-only** `editorial.scan_hitl2_readiness` +
  polling `GET /tasks/{task_id}` desde n8n. Más control, pero es código Worker
  nuevo.

**No** escanear Shortlist/Publicaciones desde n8n en este pack. **No** activar
flags `NOTION_POLLER_ENABLE_*` acá.

---

## 9. Checklist de lo que David debe completar (nombres, no valores)

- [x] Reverse proxy VPS: `WEBHOOK_URL` + TLS (§1, §1.1 — Caddy+LE 2026-07-25)
- [x] `GENERIC_TIMEZONE=America/Santiago` confirmado en VPS (§2)
- [ ] Backup off-VPS de `N8N_ENCRYPTION_KEY` verificado (§3)
- [x] Credencial `Umbral Worker Bearer (WORKER_TOKEN)` (`httpBearerAuth`) (§4)
- [x] Credencial `Telegram Bot — Umbral Editorial (TEST)` (`telegramApi`) (§4)
- [ ] (luego) Credencial `Telegram Bot — Umbral Editorial (PROD)` (§4)
- [x] Env vars n8n: `WORKER_URL`, `TELEGRAM_ALLOWED_CHAT_ID`, `TELEGRAM_ALLOWED_USER_ID` (§4)
- [x] Confirmar reachability n8n→Worker `curl $WORKER_URL/health` (§5)
- [x] Import B1 + B3, smoke con bot de test (2026-07-25 PASS; ver §1.1)
