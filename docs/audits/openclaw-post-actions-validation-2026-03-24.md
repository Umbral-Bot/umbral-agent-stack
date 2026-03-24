# Validacion general post-acciones OpenClaw - 2026-03-24

## Alcance

Cierre de validacion post-acciones sobre OpenClaw despues de las Acciones 1, 2, 3, 4, 5, 6 y 8.

El objetivo de esta pasada no fue reauditar el sistema desde cero, sino confirmar que:

- el gateway, cron, canales, agentes y skills siguen operativos
- el wiring principal con Umbral Agent Stack sigue vivo
- no quedaron regresiones reales despues de los cambios ya mergeados

## Pruebas corridas

### Repo local

- `WORKER_TOKEN=test python -m pytest tests -q`

Resultado:

- `1223 passed, 4 skipped`

### VPS / OpenClaw

Comandos y chequeos principales:

- `openclaw status --all`
- `openclaw models status`
- `openclaw security audit --deep`
- `openclaw cron status`
- `openclaw channels status --probe`
- `openclaw agent --agent main` con:
  - `umbral_provider_status`
  - `umbral_linear_list_teams`
  - `umbral_google_calendar_list_events`
  - `umbral_research_web`
- `openclaw agent --agent rick-ops`
- `openclaw agent --agent rick-tracker`
- `openclaw agent --agent rick-qa`
- `python3 scripts/verify_stack_vps.py`
- `python3 scripts/research_web_smoke.py --query "BIM trends 2026"`
- `python3 scripts/dashboard_report_vps.py --trigger post_actions --force`
- `python3 scripts/openclaw_panel_vps.py --trigger post_actions --force`

## Hallazgos reales detectados durante la validacion

### 1. Worker VPS fuera de systemd

Hallazgo:

- `umbral-worker.service` estaba en `auto-restart`
- `127.0.0.1:8088` seguia ocupado por un `python -m uvicorn worker.app:app ...` huerfano

Impacto:

- el servicio canonico no podia bindear el puerto
- el stack parecia sano por `health`, pero el owner del puerto era incorrecto

Causa:

- scripts VPS viejos reiniciaban el Worker con `nohup ... &`
- eso dejaba un proceso detached fuera de systemd

### 2. Carga fragil de `~/.config/openclaw/env`

Hallazgo:

- varios wrappers VPS usaban `source ~/.config/openclaw/env` o `export $(grep ... | xargs)`
- eso fallaba con valores con espacios, en particular:
  - `LINEAR_AGENT_STACK_PROJECT_NAME=Mejora Continua Agent Stack`

Impacto:

- cron wrappers y refresh manual de paneles podian romperse o cargar env parcial
- el error visible era:
  - `Continua: command not found`

### 3. Verificador VPS desalineado

Hallazgo:

- `scripts/verify_stack_vps.py` seguia mostrando:
  - ejemplo inseguro de carga de env
  - referencia a la cadencia vieja del dashboard

Impacto:

- el verificador daba instrucciones operativas ya obsoletas

## Fixes aplicados

### Helper seguro de env

Nuevo archivo:

- `scripts/vps/load-openclaw-env.sh`

Funcion:

- carga `~/.config/openclaw/env` preservando valores con espacios
- ignora comentarios y lineas vacias
- tolera lineas con prefijo `export `

### Scripts VPS endurecidos

Actualizados para usar el helper:

- `scripts/vps/dashboard-cron.sh`
- `scripts/vps/dashboard-rick-cron.sh`
- `scripts/vps/notion-curate-cron.sh`
- `scripts/vps/notion-poller-cron.sh`
- `scripts/vps/openclaw-panel-cron.sh`
- `scripts/vps/quota-guard-cron.sh`
- `scripts/vps/restart-worker.sh`
- `scripts/vps/sim-daily-cron.sh`
- `scripts/vps/sim-report-cron.sh`
- `scripts/vps/supervisor.sh`

### Restart canonico del Worker

Cambios:

- `restart-worker.sh` ahora:
  - limpia procesos `worker.app` sobre `127.0.0.1:8088`
  - reinicia `umbral-worker.service` si la unidad existe
  - solo cae a `nohup` si el servicio no existe
- `supervisor.sh` aplica la misma logica cuando reinicia el Worker
- la deteccion del servicio paso a una consulta exacta:
  - `systemctl --user list-unit-files 'umbral-worker.service' --no-legend`

### Verificador alineado

`scripts/verify_stack_vps.py` ahora:

- muestra la cadencia actual:
  - `dashboard-rick-cron.sh` cada 1h
  - `openclaw-panel-cron.sh` cada 6h (fallback)
- recomienda la carga segura via `load-openclaw-env.sh`

## Estado final validado

### Servicio Worker

Resultado final:

- `umbral-worker.service` -> `ActiveState=active`, `SubState=running`
- `NRestarts` estable: `52 -> 52` durante una ventana de 10 segundos
- `127.0.0.1:8088` ya queda servido por el PID del servicio systemd

### OpenClaw

Resultado:

- `openclaw status --all` -> OK
- gateway reachable
- Telegram OK
- cron OK
- skills elegibles: `29`
- missing skills: `0`

### Wiring con Umbral

Resultado:

- `umbral_provider_status` -> `{"redis_available":true,...}`
- `umbral_linear_list_teams` -> `{"ok":true,"team_count":1}`
- `umbral_google_calendar_list_events` -> `{"ok":true,"event_count":0}`
- `umbral_research_web` -> `{"ok":true,"provider":"gemini_google_search"}`

### Discovery web

Resultado:

- `research_web_smoke.py --query "BIM trends 2026"` -> `HTTP 200`
- engine efectivo: `gemini_google_search`

### Paneles

Resultado:

- `dashboard_report_vps.py --trigger post_actions --force` -> sin stderr
- `openclaw_panel_vps.py --trigger post_actions --force` -> sin stderr
- desaparece el error asociado a `Mejora Continua Agent Stack`

## Residuales y pendientes

Pendientes diferidos que ya venian del plan general:

- snapshot repo-side del tracking de paneles/OpenClaw
- atribucion fina de costo/tokens por componente
- decision Tavily/proveedor a nivel costo/operacion
- revalidacion Tailscale VPS -> VM despues del reboot del host

Residuales aceptados de seguridad, sin cambio en esta validacion:

- `gateway.trusted_proxies_missing` mientras la UI siga local-only
- `plugins.code_safety` warning `potential-exfiltration` del plugin `umbral-worker` por lectura deliberada de `tokenFile`

## Conclusiones

El test general post-acciones ya no es solo un chequeo pasivo: encontro dos regresiones operativas reales y quedaron corregidas.

Estado final:

- OpenClaw y el wiring principal con Umbral siguen sanos
- el Worker VPS vuelve a quedar bajo control canonico de systemd
- la operacion de cron/paneles deja de depender de una carga insegura del env
- el cierre post-acciones queda validado con evidencia local y en vivo
