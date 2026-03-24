# Diagnostico integral OpenClaw - 2026-03-23

## Alcance

Barrido exhaustivo de OpenClaw en la VPS despues del update a `2026.3.23`, enfocado en:

- servicio y gateway
- dashboard y config
- modelos y autenticacion
- agentes, sesiones, skills y workspace
- tareas cron
- canales, nodos y bindings
- integraciones vivas con el stack Umbral
- hallazgos operativos y plan de mejora

No se reaudito todo el stack Umbral desde cero. Se reutilizo el diagnostico de interconectividad y las fases 0-5 ya cerradas, pero se repitieron pruebas vivas de OpenClaw para verificar el runtime actual.

## Resumen ejecutivo

Estado general: **OpenClaw esta operativo, pero no completamente saneado**.

Lo que funciona bien:

- Gateway local en VPS funcionando y dashboard accesible.
- Version `2026.3.23` activa.
- `main`, `rick-ops` y `rick-tracker` ejecutan en vivo.
- Telegram operativo.
- Cron scheduler operativo con 5 jobs activos.
- Herramientas del stack Umbral disponibles desde `main`: provider status, Linear, Calendar y `research.web`.
- Wiring real OpenClaw -> Worker/Linear/Calendar verificado.

Lo que sigue pendiente:

- Hay **dos gateways systemd** vivos a la vez: `openclaw-gateway.service` y `openclaw.service`.
- El workspace compartido en VPS esta **desalineado** respecto del repo y no incluye las skills nuevas de fase 5.
- `research.web` sigue degradado por cuota Tavily agotada.
- La higiene de sesiones/transcripts esta degradada: sesiones recientes sin transcript y transcripts huerfanos.
- El endurecimiento de seguridad de OpenClaw sigue incompleto: plugin `umbral-worker`, `trustedProxies`, perfil permisivo y drift de tool profile.

## Estado por componente

| Componente | Estado | Evidencia |
|---|---|---|
| Gateway OpenClaw | OK con drift | `openclaw status --all`, `systemctl --user list-units` |
| Dashboard | OK | `openclaw dashboard` volvio a abrir tras corregir `acpx` |
| Canales | OK parcial | Telegram `enabled, configured, running` |
| Modelos | OK parcial | 10 configurados; auth viva en OpenAI Codex y Google Vertex; OpenAI Codex y Vertex ejecutados en vivo |
| Agentes | OK parcial | 6 agentes configurados; 3 activos recientemente |
| Sessions | OK con deuda | 109 sesiones; `doctor` detecta sesiones sin transcript y transcripts huerfanos |
| Skills runtime | OK con drift | core skills accesibles en runtime; workspace compartido no esta sincronizado al repo |
| Cron | OK con degradacion funcional | jobs corren; discovery Tavily falla por quota |
| Bindings | Sin bindings | `openclaw agents bindings` -> `No routing bindings.` |
| Nodos | Sin nodos | `Pending: 0 · Paired: 0` |
| Integraciones Umbral | OK parcial | Linear y Calendar OK; `research.web` falla tipado con `quota_exceeded` |

## Pruebas corridas

### 1. Estado general y servicio

Comandos:

- `openclaw status --all`
- `openclaw models status`
- `openclaw cron status`
- `openclaw cron list`
- `openclaw channels status --probe`
- `openclaw nodes list`
- `openclaw agents bindings`
- `openclaw doctor`
- `openclaw security audit --deep`
- `systemctl --user list-units | grep -E 'openclaw|umbral-worker'`

Resultado:

- Version: `2026.3.23`
- Gateway alcanzable en `ws://127.0.0.1:18789`
- Dashboard local: `http://127.0.0.1:18789/`
- Cron: `enabled=true`, `jobs=5`
- Telegram: OK
- Nodes: `0`
- Routing bindings: ninguno
- Servicios activos:
  - `openclaw-gateway.service`
  - `openclaw.service`
  - `openclaw-dispatcher.service`
  - `umbral-worker.service`

### 2. Modelos y autenticacion

Resultado:

- Default: `openai-codex/gpt-5.4`
- Fallbacks declarados: 6
- Modelos configurados: 10
- Auth/config efectiva detectada para:
  - `openai-codex`
  - `anthropic`
  - `azure-openai-responses`
  - `google`
  - `google-vertex`
- Ejecucion viva verificada para:
  - `openai-codex/gpt-5.4`
  - `openai-codex/gpt-5.3-codex`
  - `google-vertex/gemini-3.1-pro-preview`

Nota importante:

- No se invoco en vivo cada modelo fallback individual. El diagnostico separa explicitamente:
  - **configurado/autenticado**
  - **ejecutado en vivo**

### 3. Agentes

Pruebas vivas:

- `main` -> `PONG-OPENCLAW`
- `rick-ops` -> `OK-RICK-OPS`
- `rick-tracker` -> `OK-RICK-TRACKER`

Resultado:

- `main` responde con `openai-codex/gpt-5.4`
- `rick-ops` responde con `openai-codex/gpt-5.3-codex`
- `rick-tracker` responde con `google-vertex/gemini-3.1-pro-preview`

Observaciones:

- `systemPromptReport` muestra `BOOTSTRAP.md` ausente en `main`, `rick-ops` y `rick-tracker`.
- Los prompts si cargan `AGENTS.md`, `SOUL.md`, `TOOLS.md`, `IDENTITY.md`, `USER.md` y `HEARTBEAT.md`.

### 4. Skills y wiring con el stack

Pruebas vivas corridas desde `main`:

- Provider status -> `{"redis_available":true,"providers":["azure_foundry","gemini_flash","gemini_flash_lite","gemini_pro","gemini_vertex"]}`
- Linear -> `{"ok":true,"team_count":1}`
- Google Calendar -> `{"ok":true,"event_count":0}`
- `research.web` -> `{"ok":false,"provider":"tavily","error_kind":"quota_exceeded"}`

Conclusiones:

- OpenClaw si tiene acceso real a tools del stack Umbral.
- Las warnings de `openclaw skills check` fuera del entorno del servicio son engañosas a nivel shell; el proceso systemd si tiene cargadas las vars criticas.
- `research.web` no esta roto de forma muda: ahora falla de forma tipada y observable.

### 5. Cron

Cron jobs activos:

- `Seguimiento cada 30 min` -> `rick-ops`
- `SIM — Google Trends RSS`
- `Investigacion Profunda Mercado AECO`
- `SIM — recoleccion señales`
- `SIM — discovery web por keywords`

Resultado:

- Scheduler sano.
- Los jobs siguen ejecutando.
- Los jobs basados en Tavily degradan salida por quota o resultados vacios, no por fallo del scheduler.

## Hallazgos priorizados

### P1. Duplicidad de gateway systemd en la VPS

Estado:

- `openclaw-gateway.service` y `openclaw.service` estan ambos `active/running`.

Impacto:

- ruido en logs
- topologia ambigua
- riesgo de drift en proximos updates o reinicios

Evidencia:

- `openclaw.service` intenta arrancar aunque el gateway real ya esta arriba.
- `doctor` recomienda un solo gateway por host.

### P1. Workspace compartido de OpenClaw desalineado con el repo

Estado:

- El repo declara skills nuevas que el workspace compartido de la VPS no tiene.

Faltantes detectados en VPS:

- `browser-automation-vm`
- `google-audio-generation`
- `system-interconnectivity-diagnostics`

Impacto:

- OpenClaw sigue operando con capacidades reales parciales respecto del repo.
- La fase 5 quedo mergeada en `main`, pero no capitalizada del todo en la VPS.

### P1. `research.web` sigue degradado por cuota Tavily

Estado:

- La integracion responde con `error_kind=quota_exceeded`.

Impacto:

- Jobs de discovery e investigacion profunda quedan "ok" a nivel scheduler pero con salida degradada.
- OpenClaw no pierde conectividad con el Worker, pero si pierde valor de esa capa de investigacion.

### P2. Higiene de sesiones/transcripts degradada

Estado:

- `doctor` reporta `2/5 recent sessions are missing transcripts`
- y `6 orphan transcript files`

Impacto:

- memoria operativa inconsistente
- limpieza y troubleshooting mas dificiles
- riesgo de historial parcial para auditoria

### P2. Hardening de seguridad OpenClaw incompleto

Hallazgos:

- `plugins.code_safety` critica el plugin `umbral-worker`
- `gateway.trusted_proxies_missing`
- `models.weak_tier` por `azure-openai-responses/gpt-4.1`
- `plugins.tools_reachable_permissive_policy`
- `skills.workspace.symlink_escape`

Lectura correcta:

- no todo esto es "vulnerabilidad explotada"
- pero si es deuda de hardening que debe clasificarse y resolverse

### P2. `BOOTSTRAP.md` ausente en workspaces activos

Estado:

- `main`, `rick-ops` y `rick-tracker` reportan `BOOTSTRAP.md` ausente.

Impacto:

- se pierde una capa clara de arranque/control por agente
- hoy no rompe ejecucion, pero empobrece gobernanza del runtime

## Lo que no resulto ser un problema

- Telegram funciona.
- `provider status` real funciona desde OpenClaw.
- Linear funciona desde OpenClaw.
- Google Calendar funciona desde OpenClaw.
- `rick-tracker` con Google Vertex si responde.
- El update a `2026.3.23` no dejo caido el dashboard despues de corregir `acpx`.

## Plan de acciones propuesto

### Accion 1. Regularizar topologia OpenClaw en VPS

Objetivo:

- dejar un unico gateway systemd vivo

Trabajo:

- detener y deshabilitar `openclaw.service`
- dejar `openclaw-gateway.service` como servicio canonico
- verificar `status --all`, dashboard y cron despues del cambio

Prioridad: inmediata

### Accion 2. Sincronizar el workspace compartido de la VPS con el repo

Objetivo:

- capitalizar de verdad lo mergeado en fase 5

Trabajo:

- actualizar `~/.openclaw/workspace/AGENTS.md`
- incorporar skills faltantes desde `openclaw/workspace-templates/skills/`
- validar que `main`, `rick-ops` y `rick-tracker` cargan lo esperado

Prioridad: inmediata

### Accion 3. Resolver el frente Tavily / discovery web

Objetivo:

- sacar a OpenClaw del estado "scheduler sano / contenido degradado"

Trabajo:

- definir si Tavily se recarga, se cambia de plan o se reemplaza
- verificar los 2 cron jobs afectados despues del cambio

Prioridad: inmediata

### Accion 4. Sanear sesiones y transcripts

Objetivo:

- dejar el store consistente

Trabajo:

- correr `openclaw sessions cleanup ... --dry-run`
- decidir si se aplica `--fix-missing`
- archivar transcripts huerfanos

Prioridad: media

### Accion 5. Hardening de seguridad OpenClaw

Objetivo:

- reducir drift entre setup actual y setup defendible

Trabajo:

- clasificar el warning critico del plugin `umbral-worker`
- revisar `trustedProxies`
- revisar perfil `coding` y entradas desconocidas en allowlist
- decidir si el fallback `gpt-4.1` sigue siendo aceptable o no

Prioridad: media

### Accion 6. Bootstrap y gobernanza por agente

Objetivo:

- endurecer el arranque de `main`, `rick-ops` y `rick-tracker`

Trabajo:

- definir `BOOTSTRAP.md` por agente o justificar su ausencia
- comprobar si aporta claridad real al runtime

Prioridad: media

### Accion 7. Pendientes diferidos ya conocidos

Mantener anotados para despues del refresh/test general:

- snapshot repo-side del tracking de paneles/OpenClaw a partir de `ops_log`
- atribucion mas fina de costo/tokens por componente dentro de OpenClaw

## Conclusion

OpenClaw esta **operativo**, el dashboard ya abre y el wiring principal con Umbral esta **vivo**. No esta caido ni roto como sistema. Pero tampoco esta totalmente saneado: sigue habiendo drift de topologia, drift de workspace, deuda de hardening y degradacion funcional en la capa de research.

La siguiente ronda no deberia ser otra auditoria completa. Deberia ser una regularizacion quirurgica de OpenClaw en 3 frentes:

1. topologia/runtime
2. workspace/skills
3. discovery web / quota

Con eso, el siguiente test de OpenClaw ya puede enfocarse en confirmar mejora real y no en seguir encontrando drift basico.
