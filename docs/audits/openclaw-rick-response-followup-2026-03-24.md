# Follow-up del chequeo de Rick - 2026-03-24

## Alcance

Contrastar la respuesta operativa de Rick contra evidencia real del runtime OpenClaw/VPS y decidir si habia una degradacion nueva o si el estado actual ya era aceptable.

## Respuesta de Rick: lectura ajustada

La respuesta de Rick fue razonable como chequeo humano rapido, pero mezclo tres tipos de senal distintas:

1. residuales aceptados de seguridad o topologia;
2. limitaciones manuales conocidas de la VM;
3. una degradacion de research/discovery que hoy ya no aparece en la evidencia reciente.

## Evidencia real contrastada

### OpenClaw status

Comando:

- `openclaw status --all`

Estado observado en VPS:

- gateway `running` y `reachable` por loopback;
- Telegram `OK`;
- `Node service: systemd not installed`;
- `Tailscale: off · Running`.

Lectura correcta:

- `gateway.trustedProxies` vacio sigue siendo un residual aceptado mientras la Control UI permanezca local-only por loopback + SSH tunnel;
- `Tailscale off` en este host no es una caida del gateway porque la topologia canonicamente usada sigue siendo loopback local;
- `node service not installed` en la VM sigue siendo un pendiente real, pero requiere intervencion manual y no bloquea el gateway VPS.

### Snapshot runtime OpenClaw

Comando:

- `python3 scripts/openclaw_runtime_snapshot.py --days 7 --sessions-root ~/.openclaw/agents --format json`

Senales relevantes:

- `research_usage.tracked_events = 3`
- `research_usage.by_provider = gemini_google_search: 3 calls`
- `fallback_calls = 0`
- `openclaw_runtime.top_tasks` incluye:
  - `research.web` completado;
  - `composite.research_report` completado;
  - `windows.fs.list` bloqueado `16` veces

Lectura correcta:

- el discovery web actual esta sano en la ventana trazada;
- Gemini grounded search es hoy el provider primario real;
- Tavily no entro como fallback en la evidencia reciente;
- el residual operativo mas visible no es search, sino la execution plane de Windows/VM.

## Diagnostico final

### No criticos / aceptados

- `gateway.trustedProxies` vacio con UI local-only
- `Tailscale off` en la VPS mientras OpenClaw siga operando por loopback

### Pendiente manual real

- persistencia del nodo / servicio en `PCRick`
- estado exacto en la VPS:
  - `openclaw devices list` -> `PCRick` ya `paired`
  - `openclaw nodes status` -> `paired · disconnected`
- correccion conceptual:
  - mientras el gateway VPS siga en `loopback`, el node remoto debe entrar por tunel SSH local + `openclaw node install`, no apuntando directo a `srv1431451:18789`

### Degradacion real mas cercana

- tasks Windows/VM siguen bloqueadas (`windows.fs.list`) por reachability de la execution plane

### Discovery web

- operativo y sano en esta ventana;
- no requiere cambio de proveedor urgente;
- se mantiene:
  - Gemini grounded search como canonico
  - Tavily como backup secundario

## Mejora repo-side aplicada a partir de este follow-up

Aunque el discovery actual estaba sano, quedaba un hueco repo-side util:

- `composite.research_report` hacia una sola llamada final de `llm.generate`;
- si Gemini devolvia `503 UNAVAILABLE` transitorio, el flujo caia de inmediato al fallback crudo.

Se endurecio ese punto con retry/backoff acotado antes de degradar a raw research data.

## Recomendacion

La respuesta de Rick no amerita reabrir una accion de provider strategy. Lo correcto ahora es:

1. mantener Gemini primario y Tavily backup;
2. dejar la VM como pendiente manual/operativo;
3. tratar cualquier nuevo problema de research sobre evidencia trazada (`research_usage`), no sobre memoria de degradaciones pasadas.
