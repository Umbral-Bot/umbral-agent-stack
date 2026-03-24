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

## Actualizacion 2026-03-24

La Accion 1 de este diagnostico ya fue ejecutada despues del barrido inicial:

- `openclaw.service` dejo de existir como unidad cargada en la VPS.
- `openclaw-gateway.service` quedo como unico gateway systemd canonico.
- `openclaw status --all`, `openclaw dashboard` y una ejecucion minima de `main` siguieron funcionando tras la regularizacion.
- La Accion 2 tambien quedo ejecutada: se sincronizaron `~/.openclaw/workspace` y las copias relevantes de `rick-ops` / `rick-tracker` contra las skills endurecidas en el repo, con backup previo y validacion por hash.
- La Accion 3 tambien quedo ejecutada: `research.web` y `scripts/web_discovery.py` comparten ahora un fallback real via Gemini grounded search. En la VPS, Tavily sigue respondiendo `432`, pero el runtime ya no queda degradado por eso.
- El estado bueno de red tras la intervencion en la VM tambien quedo asentado: se agrego una segunda NIC en Hyper-V (`Default Switch`) para restaurar internet de la VM sin quitar la NIC interna. La VM recupero salida web durante la intervencion; la reachability tailnet VPS -> VM debe revalidarse tras reinicios del host.

El resto del documento preserva el barrido original del 2026-03-23, pero las secciones de resumen, estado por componente y plan ya reflejan el cierre de las Acciones 1-3.

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

- La higiene de sesiones/transcripts esta degradada: sesiones recientes sin transcript y transcripts huerfanos.
- El endurecimiento de seguridad de OpenClaw sigue incompleto: plugin `umbral-worker`, `trustedProxies`, perfil permisivo y drift de tool profile.
- Tavily sigue sin cuota como proveedor primario; queda pendiente decidir si se recarga, se deja como backend secundario o se retira del discovery ahora que Gemini grounded cubre el fallback real.

## Estado por componente

| Componente | Estado | Evidencia |
|---|---|---|
| Gateway OpenClaw | OK | `openclaw status --all`; `openclaw-gateway.service` canonico, `openclaw.service` retirado |
| Dashboard | OK | `openclaw dashboard` volvio a abrir tras corregir `acpx` |
| Canales | OK parcial | Telegram `enabled, configured, running` |
| Modelos | OK parcial | 10 configurados; auth viva en OpenAI Codex y Google Vertex; OpenAI Codex y Vertex ejecutados en vivo |
| Agentes | OK parcial | 6 agentes configurados; 3 activos recientemente |
| Sessions | OK con deuda | 109 sesiones; `doctor` detecta sesiones sin transcript y transcripts huerfanos |
| Skills runtime | OK con seleccion pendiente | workspace compartido y copias activas sincronizadas; queda pendiente curar la seleccion fina por rol |
| Cron | OK con fallback operativo | jobs corren; discovery cae a Gemini grounded cuando Tavily responde `432` |
| Bindings | Sin bindings | `openclaw agents bindings` -> `No routing bindings.` |
| Nodos | Sin nodos | `Pending: 0 · Paired: 0` |
| Integraciones Umbral | OK con deuda de proveedor | Linear y Calendar OK; `research.web` y `web_discovery.py` operan via `gemini_google_search` cuando Tavily quota-exceeded |

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
- `research.web` -> `{"ok":true,"provider":"gemini_google_search","fallback_reason":"research_provider_quota_exceeded:quota"}`
- `python3 scripts/web_discovery.py "BIM trends 2026" --count 3` -> `engine_used=gemini_google_search`, `error=null`

Conclusiones:

- OpenClaw si tiene acceso real a tools del stack Umbral.
- Las warnings de `openclaw skills check` fuera del entorno del servicio son engañosas a nivel shell; el proceso systemd si tiene cargadas las vars criticas.
- La capa de research ya no queda degradada por cuota Tavily: el path efectivo cae a Gemini grounded search y sigue devolviendo resultados.
- Tavily sigue sin cuota y Google CSE legado sigue sin acceso; la deuda que queda es de proveedor/costo, no de runtime.

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
- Los jobs de discovery ya no quedan degradados por quota Tavily: cuando Tavily responde `432`, el path efectivo cae a Gemini grounded y el scheduler sigue produciendo contenido.

## Hallazgos priorizados

### Resuelto. Duplicidad de gateway systemd en la VPS

Estado:

- Resuelto por la Accion 1 el `2026-03-24`.

Impacto:

- Se elimino ruido y drift de topologia para updates/reinicios posteriores.

Evidencia:

- `openclaw-gateway.service` queda como gateway canonico.
- `openclaw.service` ya no existe como unidad cargada en la VPS.

### Resuelto. Workspace compartido de OpenClaw desalineado con el repo

Estado:

- Resuelto por la Accion 2 el `2026-03-24`.

Impacto:

- El inventario fisico de skills quedo alineado con el repo en las rutas sincronizadas.
- Lo que sigue pendiente no es sync fisico sino curar la seleccion efectiva por rol, derivado a la Accion 8.

### P2. Tavily sigue sin cuota, pero el runtime ya no queda degradado

Estado:

- Tavily sigue respondiendo `432 usage limit`.
- `research.web` y `web_discovery.py` ya operan via `gemini_google_search` cuando eso pasa.

Impacto:

- El scheduler y el discovery real ya no quedan degradados.
- La deuda restante es decidir si Tavily se recarga o queda como backend secundario por costo/control.

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

Estado: **cerrada el 2026-03-24**

Objetivo:

- dejar un unico gateway systemd vivo

Trabajo:

- detener y deshabilitar `openclaw.service`
- dejar `openclaw-gateway.service` como servicio canonico
- verificar `status --all`, dashboard y cron despues del cambio

Prioridad: inmediata

### Accion 2. Sincronizar el workspace compartido de la VPS con el repo

Estado: **cerrada el 2026-03-24**

Objetivo:

- capitalizar de verdad lo mergeado en fase 5

Trabajo:

- actualizar `~/.openclaw/workspace/AGENTS.md`
- incorporar skills faltantes desde `openclaw/workspace-templates/skills/`
- validar que `main`, `rick-ops` y `rick-tracker` cargan lo esperado

Resultado:

- `~/.openclaw/workspace` quedo alineado por hash en las rutas sincronizadas.
- Tambien se sincronizaron skills relevantes en `~/.openclaw/workspaces/rick-ops` y `~/.openclaw/workspaces/rick-tracker` para evitar drift entre workspaces por agente y el repo.
- La capa que sigue pendiente no es el inventario fisico, sino la seleccion efectiva de skills por rol/prompt en runtime; eso se deriva a la Accion 8.

Prioridad: inmediata

### Accion 3. Resolver el frente Tavily / discovery web

Estado: **cerrada el 2026-03-24**

Objetivo:

- sacar a OpenClaw del estado "scheduler sano / contenido degradado"

Trabajo:

- agregar backend compartido Tavily -> Gemini grounded -> Google CSE legado opt-in
- verificar `research_web_smoke.py` y `web_discovery.py` en VPS
- verificar una corrida manual de `sim_daily_research.py` y `sim_daily_report.py`

Resultado:

- `research_web_smoke.py --query "BIM trends 2026"` devolvio `HTTP 200` con `engine=gemini_google_search`.
- `web_discovery.py "BIM trends 2026" --count 3` devolvio `engine_used=gemini_google_search`.
- `sim_daily_research.py` volvio a completar 6 tareas `research.web` y un resumen `llm.generate` en la VPS.
- `sim_daily_report.py --hours 1` volvio a producir reporte con URLs recientes del path grounded.
- Tavily sigue respondiendo `432`, pero el runtime ya no queda degradado por eso.

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

### Accion 8. Revisar skills faltantes en OpenClaw VPS

Objetivo:

- separar skills faltantes por drift de workspace de los huecos reales que si ameritan skill nueva

Trabajo:

- inventariar skills presentes en `~/.openclaw/workspace` vs `openclaw/workspace-templates/`
- clasificar cada gap en:
  - `sync desde skill existente`
  - `skill existente mal cargada o no consumida`
  - `skill nueva realmente necesaria`
- proponer una priorizacion operativa por agente/canal

Prioridad: media

## Conclusion

OpenClaw esta **operativo**, el dashboard ya abre y el wiring principal con Umbral esta **vivo**. No esta caido ni roto como sistema. Con las Acciones 1-3 cerradas, ya no queda drift basico de topologia/workspace ni degradacion runtime en discovery web. Lo que sigue abierto es higiene de sesiones, hardening y la decision sobre el rol futuro de Tavily como proveedor.

La siguiente ronda no deberia ser otra auditoria completa. Deberia ser una regularizacion quirurgica de OpenClaw en 3 frentes:

1. higiene de sesiones/transcripts
2. hardening de seguridad
3. seleccion de skills por rol + decision Tavily/proveedor

Con eso, el siguiente test de OpenClaw ya puede enfocarse en confirmar mejora real y no en seguir encontrando drift basico.
