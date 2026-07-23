# P2.6 — Puente HITL-2 → publish blog (2026-07-23)

> **Estado:** código + tests implementados, **DEFAULT OFF** (fail-closed).
> Cablea el paquete P2.6 del
> [roadmap norte](editorial-roadmap-norte-p1-p3-2026-07-22.md) §3 (fila H,
> decisión **D3 locked**). No abre gates humanos, no publica en producción
> desde este PR, no autopublica RRSS (Fila I = B), no toca Magnific/copy/
> dedupe/negativos (P2.2-P2.5) salvo lectura incidental de sus campos.

## Qué es (D3, locked — David 2026-07-22)

El contrato (§5.H) exige que el disparo de publish del blog cumpla **tres**
condiciones, **ninguna opcional**:

```
Estado imagen = Seleccionada  ∧  autorizar_publicacion = true  ∧  Telegram "ok publica"
```

Antes de este paquete, `worker/tasks/editorial_publish.py` ya enforzaba las
**dos primeras** (vía `_evaluate_notion_visual_gate` + lectura de
`autorizar_publicacion`/`aprobado_contenido`), pero la **tercera —
confirmación por Telegram— no existía en ningún lugar del código**. El
publish real seguía dependiendo enteramente de que un operador humano lo
invocara manualmente, confiando en que ya hubiera visto el "ok publica" en
Telegram — sin ninguna verificación en código.

## Por qué el diseño es un gate + scan de observabilidad, no un poller que dispara

Investigado antes de escribir código: **no existe en este repo ningún parser
de mensajes entrantes de Telegram** (`dispatcher/smart_reply.py` sólo *envía*
mensajes; el approval-loop vive como instrucciones de prompt para Rick en
`openclaw/workspace-templates/skills/telegram-approval-loop/SKILL.md`, no como
código). Tampoco hay forma hoy de correlacionar un mensaje de Telegram con un
`notion_page_id` específico. Y el propio contrato/roadmap dice explícitamente
que el puente es **"evento Notion→Worker (n8n/webhook, write vía core)"** —
no un poller Python que decide y dispara, a diferencia de P2.1/P2.4/P2.5.

Por eso este paquete se divide en dos piezas:

1. **El gate (el núcleo real del "puente fail-closed")**: `telegram_confirmed`
   — un tercer input booleano en `handle_web_publish_editorial_post`,
   requerido para **cualquier** fuente (`payload` o `notion_page_id`),
   `False` por defecto. Nada en el código lo infiere nunca — debe venir
   explícito de quien llama (un workflow n8n que verificó la respuesta de
   Telegram, o un operador). `worker/app.py`'s `POST /enqueue` ya existe
   genéricamente para que n8n (o Make.com, webhooks, cron) llame cualquier
   task — no hace falta infraestructura nueva para ese borde.
2. **Un scan de observabilidad** (`_scan_hitl2_publish_readiness`, opt-in):
   detecta qué filas de Publicaciones ya cumplen las **dos** condiciones
   Notion-side, y llama al handler real en `dry_run=True` **sin** afirmar
   `telegram_confirmed` — así reutiliza el gate real (una sola fuente de
   verdad) en vez de duplicar su lógica. El resultado (`telegram_confirmation_missing`
   vs cualquier otro bloqueo) sólo se registra en logs — **nunca publica, nunca
   escribe en Notion**.

## Qué hace

### 1. El gate (`worker/tasks/editorial_publish.py`)

- Nuevo input `telegram_confirmed` (bool, default `False`), leído junto a
  `dry_run`/`notion_page_id`/`payload`.
- Nueva verificación dura, tras el gate visual existente: si
  `telegram_confirmed` es falso, bloquea con `error: "telegram_confirmation_missing"`,
  `would_publish: False`, **sin llamada de red**.
- `gates.telegram_confirmed` se expone siempre en la respuesta (dry-run o no)
  para diagnóstico, igual que `gates.autorizar_publicacion`/`aprobado_contenido`.
- Aplica **igual** a fuente `payload` y `notion_page_id` — D3 dice "ninguna
  condición opcional", no depende de dónde vino el payload.

### 2. Scan de observabilidad (`dispatcher/notion_poller.py::_scan_hitl2_publish_readiness`)

1. Escanea Publicaciones (opt-in) buscando filas no archivadas con
   `Estado imagen == "Seleccionada"` **y** `autorizar_publicacion == true`
   (pre-filtro barato, sobre el snapshot aplanado).
2. Por cada candidata (máximo 3 por ciclo), llama a
   `web.publish_editorial_post` con `{"notion_page_id": ..., "dry_run": true}`
   — **sin** `telegram_confirmed` — y registra el resultado:
   - `error == "telegram_confirmation_missing"` → `READY pending Telegram
     "ok publica" confirmation` (la fila está genuinamente lista, sólo falta
     el tercer leg).
   - Cualquier otro resultado (`ok=False` con otro error, o incluso `ok=True`
     si alguien ya coló `telegram_confirmed` por otra vía) → `not actually
     ready`, con el error real para diagnóstico.
3. Checkpoint en Redis (1h, sólo para no re-loguear la misma fila cada
   ciclo) — **no** es una idempotencia de escritura, porque este scan nunca
   escribe nada.

El scan **nunca** escribe a Notion ni llama al Azure Function — cada llamada
al handler es `dry_run=True` y nunca pasa `telegram_confirmed=True`, así que
el propio gate del handler bloquea cualquier intento, incluso si este código
tuviera un bug.

### 3. CLI (`scripts/editorial/trigger_hitl2_publish.py`)

Wrapper delgado sobre `web.publish_editorial_post` vía HTTP al Worker (mismo
patrón que `magnific_generate_variants.py` — no toca Notion/Azure directo).
Doble seguro: sin `--live`, siempre `dry_run=True` sin importar
`--telegram-confirmed`; con `--live` pero sin `--telegram-confirmed`, se
niega **antes** de llamar al Worker. Un publish real exige **ambas** flags
explícitas — el script nunca decide por sí mismo que Telegram fue
confirmado, sólo transmite la afirmación del operador.

## Qué NO hace (por diseño — alcance estricto de P2.6)

- No implementa un webhook/parser de Telegram entrante — eso sigue fuera de
  este repo (Rick/OpenClaw), o sería un paquete n8n aparte.
- No dispara publish real automáticamente desde ningún proceso de este repo.
- No cambia el comportamiento de RRSS (Fila I = B se mantiene: el blog se
  publica, LinkedIn/X siguen siendo manuales).
- No toca Magnific (P2.2), copy (P2.3), dedupe (P2.4) ni negativos (P2.5).
- No crea ni modifica schema Notion.

## Impacto en compatibilidad (ruptura intencional)

Cualquier llamador existente de `web.publish_editorial_post` que esperaba
publicar con sólo `autorizar_publicacion`/`aprobado_contenido`/gate visual en
`true` **ahora también necesita `telegram_confirmed: true`** para tener
éxito. Esto es intencional — es exactamente lo que D3 exige (cerrar el hueco
de la fila H) — pero significa que **todos** los tests existentes de éxito
en `tests/test_editorial_publish.py` se actualizaron para incluirlo. Los
tests que ya esperaban bloqueo (gate de autorización, gate visual) no
cambiaron: bloquean en un paso anterior al nuevo gate, así que su resultado
es idéntico.

## Flags / env vars (todas fail-closed por ausencia)

| Var | Proceso | Default | Efecto |
|---|---|---|---|
| `NOTION_POLLER_ENABLE_HITL2_SCAN` | dispatcher (poller) | off | Habilita el scan de observabilidad. Sin esto, el poller nunca corre este scan — el resto no se ve afectado. |
| `NOTION_PUBLICACIONES_DB_ID` | dispatcher (poller) + Worker | vacío | Ya usado por P2.1/P2.2. Sin esto, el scan es no-op. |
| `telegram_confirmed` (input del task, no env var) | Worker | `False` | El gate real. Nunca inferido — debe venir explícito de quien llama `web.publish_editorial_post`. |

## Cómo correr un dry-run

**Verificar el gate directamente** (handler, sin scan):

```bash
curl -s -X POST "$WORKER_URL/run" \
  -H "Authorization: Bearer $WORKER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task": "web.publish_editorial_post", "input": {"notion_page_id": "<page_id>", "dry_run": true}}'
# Si Estado imagen + autorizar_publicacion ya están OK:
#   {"ok": false, "error": "telegram_confirmation_missing", "would_publish": false, "gates": {...}}
```

**Vía el CLI** (readiness check, siempre seguro — nunca live, nunca afirma Telegram):

```bash
export WORKER_URL=http://127.0.0.1:8088 WORKER_TOKEN=xxx
python scripts/editorial/trigger_hitl2_publish.py --notion-page-id <page_id>
```

**Simular el "ok publica" en dry-run** (para probar que las tres condiciones
juntas sí destraban el publish, sin llamar a Azure):

```bash
python scripts/editorial/trigger_hitl2_publish.py --notion-page-id <page_id> --telegram-confirmed
# dry_run sigue forzado a true sin --live — sólo confirma que sería publicable
```

**Publish real** (requiere que el operador haya verificado la respuesta de
Telegram fuera de este script):

```bash
python scripts/editorial/trigger_hitl2_publish.py --notion-page-id <page_id> --telegram-confirmed --live
```

## Cómo habilitar el scan de observabilidad (staging/producción)

1. Confirmar `NOTION_PUBLICACIONES_DB_ID` configurado (ya debería estarlo).
2. Setear `NOTION_POLLER_ENABLE_HITL2_SCAN=true` en el entorno del poller.
3. Relanzar el poller — mismo procedimiento que
   [runbooks/runbook-notion-poller.md](../../runbooks/runbook-notion-poller.md).
4. Verificar en el log: `HITL-2 readiness scan ENABLED` al boot, y por ciclo
   `HITL-2 readiness scan: hitl2_scan_enabled=True scanned=N eligible=N
   ready_pending_telegram=N not_ready=N skipped=N errors=N`.

## Habilitar el puente real (fuera de alcance de este PR)

Conectar un workflow n8n que: (a) reciba el webhook de Telegram, (b)
verifique que el texto es "ok publica" y que corresponde a la página
correcta (mecanismo de correlación aún por diseñar — hoy no existe), y (c)
llame a `POST {WORKER_URL}/enqueue` con
`{"task": "web.publish_editorial_post", "input": {"notion_page_id": ...,
"telegram_confirmed": true}}` — es trabajo de un paquete n8n aparte, con GO
explícito de David, no de este PR.

## Tests

- [tests/test_editorial_publish.py](../../tests/test_editorial_publish.py)`::TestTelegramConfirmationGate` —
  bloqueo sin `telegram_confirmed` (fuente `payload` y `notion_page_id`),
  bloqueo con `telegram_confirmed=False` explícito, el gate de autorización/
  visual sigue bloqueando primero (diagnóstico correcto), `dry_run` sigue
  bloqueado sin Telegram, éxito con las tres condiciones (dry-run y real).
  El resto de la suite (46 tests previos) se actualizó para incluir
  `telegram_confirmed: True` en los casos de éxito — ninguna aserción de
  comportamiento cambió, sólo el input necesario para alcanzarlo.
- `tests/test_notion_poller.py::TestHitl2ScanFlagParsing` /
  `TestHitl2ScanBehavior` — scan: flag default-off, filtrado
  `Estado imagen`/`autorizar_publicacion`/archivadas, siempre llama con
  `dry_run=True` y nunca con `telegram_confirmed`, checkpoint sin backoff
  separado (no hay escritura que reintentar), límite de batch.
- [tests/test_trigger_hitl2_publish.py](../../tests/test_trigger_hitl2_publish.py) —
  CLI: invocación por defecto es dry-run sin confirmar, `--live` sin
  `--telegram-confirmed` se niega antes de llamar al Worker,
  `--telegram-confirmed` solo (sin `--live`) sigue forzando dry-run,
  `--live --telegram-confirmed` sí llama en vivo, manejo de bloqueo/errores.

## Referencias

- Contrato: [editorial-norte-hitl-contract-2026-07-22.md](editorial-norte-hitl-contract-2026-07-22.md) §5.H, D3 (§7 decisiones)
- Roadmap: [editorial-roadmap-norte-p1-p3-2026-07-22.md](editorial-roadmap-norte-p1-p3-2026-07-22.md) fila P2.6
- ADR-010 (Azure editorial blog CMS, gates): [ADR-010-azure-editorial-blog-cms.md](../adr/ADR-010-azure-editorial-blog-cms.md)
- Handler existente: [worker/tasks/editorial_publish.py](../../worker/tasks/editorial_publish.py)
- Content model / operator flow: [notion-blog-linkedin-v3-content-model.md](notion-blog-linkedin-v3-content-model.md)
- Telegram approval-loop (prompt de Rick, no código): [openclaw/workspace-templates/skills/telegram-approval-loop/SKILL.md](../../openclaw/workspace-templates/skills/telegram-approval-loop/SKILL.md)
