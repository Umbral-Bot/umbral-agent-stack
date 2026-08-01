# Diagnóstico de frescura — runtime Rick (2026-08-01)

**Tipo:** diagnóstico read-only. No hay cambio de runtime ni de código en este PR.
**Repo:** `945ca688` (main, limpio) · **Host:** `srv1431451`
**Ventana de evidencia:** logs 7 días + 4 sondas en vivo a `rick-orchestrator` (15:56–16:04 UTC).

## Titular

Rick **no está stale**. En las 4 sondas consultó en vivo, reportó su fuente con
honestidad y su respuesta coincidió literalmente con la evidencia del stack.

Lo que está stale es **el dato en Notion** y **tres subsistemas apagados**
(Calendar, RAG, pairing de la VM). El síntoma "Rick contesta cosas viejas" es
correcto; la causa no es Rick.

## Tabla de frescura

| Fuente | Lo que Rick dice | Evidencia real | Gap |
|---|---|---|---|
| **Hora / TZ** | `2026-08-01 11:57:30 UTC-04:00`, fuente "reloj del sistema" | Real `11:57:32 -04`. NTP sync, offset `-1.057 ms`, stratum 2 | **Ninguno** (2 s). El drift de ~12 min del toque previo **no se reproduce** |
| **Calendar** | "No operativo por autenticación no configurada" + error textual | `google.calendar.list_events` corre 07:30 diario y falla siempre desde ≥27-jul. Sin `GOOGLE_CALENDAR_*` en env. Rick ejecutó la task a las 11:58:37 durante la sonda | **Ninguno en el reporte.** Gap real: credencial ausente hace ≥6 días |
| **Notion tareas** | 3 urgentes: Konstruedu `2026-04-16`, Comgrap Dynamo `2026-04-20`, WSP España `2026-04-30`. `FUENTE=notion-live` | Query directa a la DB `517bfeb9`: mismas 3 tareas, mismo orden, todas `Pendiente` | **Ninguno.** Rick lee live y ordena bien |
| **Backlog Notion (dato)** | "Filtro: Estado ≠ Hecha/Archivada, orden Prioridad→fecha asc" | 33 filas: 24 `Pendiente`, 1 `En curso`, 2 `Hecha`, 6 sin Estado. **20 de 31 abiertas sin `Fecha objetivo`**. Última con fecha: `2026-07-18` | **GAP REAL.** El filtro es correcto; el dato está podrido. Sin fechas, el orden asc devuelve abril para siempre |
| **Memoria / RAG** | "Pausado por cambio de embeddings. Última indexación `2026-04-20`. Índice de `rick-orchestrator`: 0 archivos / 0 chunks" | 0 ejecuciones `rag.*` en 7 días. Sin vector store en disco. `worker/rag/` sin commits desde `885e732` (12-abr) | **Ninguno en el reporte.** Gap real: memoria apagada hace ~3,5 meses |
| **Worker** | — | `:8088` OK (156 tasks), `:8089` mission-control OK, Redis PONG, 5 units `active` | Sano |
| **Canal Telegram** | — | Bot `@Rick_lot_bot` (correcto, ≠ TEST n8n). `pending_update_count: 0` → ingress drena bien. Solo 1 outbound/día L-V = cron "Briefing matutino" | Sin bug de canal. Silencio = no hubo conversación, no falla |

**Latencia de Rick:** 54 s / 58 s / 119 s / 143 s (media ~94 s, creciente con el contexto de sesión).

## Hallazgos no anticipados

1. **679 intentos de pairing fallidos en 24 h.** La VM (`100.109.16.40`) reintenta
   conectarse al gateway cada ~30 s: `pairing required: device is not approved yet`.
   Loop infinito que ensucia el log del gateway.
2. **`model_router` declara providers inexistentes.** 65 warnings/24 h:
   `No configured providers available for task_type 'general'
   (preferred=azure_foundry, fallback=[claude_pro, gemini_pro, gemini_flash])`.
   OpenClaw real corre `openai/gpt-5.5`. Todas las tasks salen con `model=` vacío.
3. **124 escalaciones a Linear en 7 días**, 94 de ellas por el mismo fallo
   (`windows.fs.list` → 400), colapsadas en ~10 issues. Ruido que entierra señal real.
4. **Causa raíz del 400 de `windows.fs.list`:** payload **idéntico** en ejecuciones
   `done` y `failed` (`{"path": "G:\\Mi unidad\\Rick-David\\Proyecto-Embudo-Ventas"}`).
   No es determinista por input → `G:\` (Google Drive Desktop en la VM) se desmonta
   de forma intermitente. Falla de la VM, no del stack.
5. **`gateway.trustedProxies` sin configurar** → conexiones vía Tailscale no se
   detectan como locales.

## Fixes priorizados

Ninguno aplicado: los cuatro primeros tocan credenciales, config viva de routing o
aprobación de dispositivos. Requieren GO explícito.

| # | Fix | Desbloquea | Riesgo | Esfuerzo |
|---|---|---|---|---|
| **1** | **Curar fechas del backlog Notion** — poner `Fecha objetivo` a las 20 tareas abiertas sin fecha, cerrar las de abril ya resueltas | **La frescura percibida.** Es el único fix que cambia lo que Rick le responde a David mañana | Nulo (dato) | Bajo — decisión de David |
| **2** | **Credencial Google Calendar** — `GOOGLE_CALENDAR_REFRESH_TOKEN` + `CLIENT_ID` + `CLIENT_SECRET` (ver `docs/35-google-calendar-token-setup.md`) | Agenda en el briefing matutino | Bajo | Medio — OAuth de David |
| **3** | **Alinear `model_router`** con los providers reales (`openai/gpt-5.5` + fallback `gpt-5.4`) | Elimina 65 warnings/día y el routing ciego | Medio — toca routing en producción | Bajo |
| **4** | **Aprobar o desactivar el nodo VM** (`openclaw devices`) | Corta 679 reintentos/día | Medio — decisión de seguridad | Bajo |
| **5** | **Cortar el ruido de escalación** — no abrir issue Linear por fallo recurrente conocido; agrupar o silenciar `windows.fs.list` mientras `G:\` sea inestable | Devuelve señal útil a Linear | Bajo | Medio |
| **6** | **Reactivar RAG** — reindexar con el modelo de embeddings nuevo | Memoria de largo plazo de Rick | Bajo | Alto |
| 7 | Higiene: quitar `plugins.entries.umbral-tournament-github` (stale), `load.paths` redundante, `gateway.trustedProxies` | Limpia warnings de arranque | Bajo | Bajo |

**Orden recomendado:** 1 → 2 → 5 → 3 → 4 → 6 → 7.
El #1 es el que mueve la aguja: sin fechas en Notion, arreglar Calendar y RAG no
cambia lo que David ve cada mañana.

## Checkpoint David

- **Telegram Web no se pudo abrir desde la VPS**: Chrome no está instalado
  (`/opt/google/chrome/chrome` ausente) y el login requiere QR presencial.
  Las sondas se hicieron por el runtime de OpenClaw
  (`openclaw agent --agent rick-orchestrator`, **sin `--deliver`**), que ejercita
  el mismo agente y las mismas herramientas sin escribir en el chat de David ni
  suplantarlo.
- El canal Telegram quedó **sin tocar**: cero mensajes enviados durante este ciclo.

## Método

```bash
# Reloj
timedatectl; chronyc tracking
curl -sSI https://www.google.com | grep -i '^date:'

# Runtime
openclaw status --all; openclaw models status; openclaw cron list
curl -fsS http://127.0.0.1:8088/health
redis-cli ping

# Canal (read-only, no envía)
curl -sS "https://api.telegram.org/bot$TOKEN/getWebhookInfo"

# Sondas (sin --deliver → no escribe en Telegram)
openclaw agent --agent rick-orchestrator --session-key agent:rick-orchestrator:diag-frescura-20260801 -m "..."
```
