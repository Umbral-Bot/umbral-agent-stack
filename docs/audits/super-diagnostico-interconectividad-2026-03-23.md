# Super diagnostico de interconectividad del sistema

Fecha de ejecucion: 2026-03-23  
Rama de trabajo: `codex/super-diagnostico-interconectividad-r24`

## Resumen ejecutivo

- Este barrido no partio desde cero: toma como base `docs/audits/super-diagnostico-2026-03-22.md` y valida en vivo los enlaces reales entre repo, VPS, VM, Worker, Dispatcher, Redis, Notion, Linear, Google y OpenClaw.
- El codigo del repo local esta sano: `WORKER_TOKEN=test python -m pytest tests -q` dio `1198 passed, 4 skipped, 1 warning`.
- La conectividad base en produccion existe:
  - Worker local VPS: OK
  - Redis VPS: OK
  - Linear via Worker: OK
  - `google.calendar.list_events`: OK en Worker local VPS
  - `gmail.list_drafts`: OK en Worker local VPS
  - VM headless e interactive: ambas responden `/health`
- Los problemas actuales ya no son de "stack caido"; son de interconectividad y coordinacion operativa:
  1. El supervisor de la VPS entra en falso drift cada 5 minutos por un bug en `scripts/vps/dispatcher-service.sh` y luego intenta alertar a una pagina de Notion archivada.
  2. El rate limiter del Worker agrupa todas las llamadas locales bajo `127.0.0.1`, lo que provoca `429 Too Many Requests` entre crons, diagnosticos y pruebas internas.
  3. `research.web` sigue fallando en runtime real aunque `TAVILY_API_KEY` si esta presente en la VPS.
  4. La telemetria mejoro, pero sigue siendo pobre para gobierno real: `source` y `source_kind` solo tienen 4.1% de cobertura en `ops_log`.
  5. El `Control Room`/`OpenClaw` si se refresca, pero el resumen visual vivo sigue siendo malo; el problema ya no es cache ni cron, sino diseño y composicion.
  6. El coverage de skills estaba subestimado: el reporte crudo hablaba de 52%, pero el coverage real sube a 89% al mapear tasks a skills existentes. Los huecos verdaderos son pocos y bien identificables.

## Delta respecto al super diagnostico del 2026-03-22

### Capitalizado desde ayer

- `UMB-141` ya quedo mergeada: trazabilidad runtime mas rica.
- `UMB-140` ya quedo mergeada: auto-issues con dedupe y proyecto canonico.
- `UMB-148` retiro Google Custom Search como camino primario.
- El incidente de Google API keys expuestas ya quedo contenido en `main`, con secret scanning y push protection activados.

### Lo que esta mejor entendido hoy

- El `Control Room` no esta desactualizado: el cron corre y la pagina `OpenClaw` si se esta refrescando. El layout actual es el problema.
- El helper `scripts/run_worker_task.py` tenia una resolucion de URL que hacia que tasks genericas pudieran ir a la VM interactiva en vez del Worker local de la VPS.
- `scripts/env_loader.py` cargaba `.env` del repo pero no el canonico `~/.config/openclaw/env`, por lo que varios scripts de diagnostico daban falsos negativos operativos.
- `/providers/status` y `/quota/status` eran inutiles en VM o workers sin Redis local. El fix ya esta listo en esta rama.
- El supervisor no solo "se queja": entra en un loop falso por dos causas concretas y reproducibles:
  - `USER` no definido en `dispatcher-service.sh`
  - `NOTION_SUPERVISOR_ALERT_PAGE_ID` apuntando a una pagina archivada

## Metodo y alcance

Se ejecutaron comprobaciones en cinco planos:

1. Repo local y tests.
2. VPS por SSH (`vps-umbral`).
3. Worker local de la VPS via `POST /run`.
4. VM headless e interactive via HTTP.
5. Tooling de auditoria y cobertura:
   - `scripts/audit_traceability_check.py --format json`
   - `scripts/governance_metrics_report.py --days 7 --format json`
   - `scripts/skills_coverage_report.py`
   - `scripts/secrets_audit.py`

## Inventario de interconectividad

| Plano | Estado actual | Evidencia | Lectura |
| --- | --- | --- | --- |
| Repo local | OK | `1198 passed, 4 skipped, 1 warning` | Codigo sano y con regresiones cubiertas en esta rama |
| Worker VPS | OK | `scripts/verify_stack_vps.py` -> 80 tareas, health 200 | Control plane base arriba |
| Redis VPS | OK | `pending=0, blocked=0`, `PING` OK | Cola viva, sin backlog actual |
| Linear via Worker | OK | `linear.list_teams`, `linear.list_projects`, `linear.list_agent_stack_issues` | Integracion canonicamente usable |
| Notion via Worker | Parcial-OK | `notion.read_page`, `notion.poll_comments` OK | API viva, pero algunas superficies tienen drift de pagina/uso |
| Dashboard/OpenClaw cron | OK con UX mala | `/tmp/dashboard_cron.log`, `last_edited_time` de `OpenClaw` | El refresco ocurre; el diseno actual no da |
| Supervisor / reconciliacion Dispatcher | FAIL operativo | `/tmp/supervisor.log` cada 5 min | Ruido continuo, falsos FAIL y canal de alerta roto |
| VM headless | OK base | `/health` 200, `ping` OK | Endpoint vivo |
| VM interactive | OK base | `/health` 200, `gui.desktop_status` OK | Endpoint vivo para GUI |
| `/providers/status` en VM | Insuficiente en runtime actual | devolvia 503 sin Redis local | Fix listo en esta rama, no desplegado aun |
| Google Calendar/Gmail | OK en Worker local VPS | `google.calendar.list_events`, `gmail.list_drafts` | Readiness real validada en VPS |
| Search / Tavily | FAIL real | `research.web` 500 | No basta con tener la env; el path sigue roto en vivo |
| Telemetria ops_log | Parcial | cobertura `source`/`source_kind` 4.1% | Mejor que antes, todavia insuficiente |
| Skills | Mejor de lo que parecia | coverage corregido a 89% | El hueco real es pequeno y focalizado |

## Hallazgos por severidad

### P0 - Operacion

#### P0.1 - Loop falso del supervisor en la VPS

Evidencia fresca:

```text
[supervisor 2026-03-23 07:30 UTC] Dispatcher: drift detected
[supervisor 2026-03-23 07:30 UTC] /home/rick/umbral-agent-stack/scripts/vps/dispatcher-service.sh: line 13: USER: unbound variable
[supervisor 2026-03-23 07:30 UTC] Dispatcher: FAILED to reconcile
Failed to connect to bus: No medium found
```

Impacto:

- ensucia logs y percepcion operativa;
- oculta si el problema es real o falso;
- dispara intentos de reconciliacion que no pueden funcionar en ese contexto;
- contamina la capa de alertas de Notion.

Causa raiz:

- `scripts/vps/dispatcher-service.sh` asume `USER` y `systemd --user`;
- en ese entorno el servicio real vive como proceso, no como `systemd --user` disponible.

Estado:

- diagnosticado en vivo;
- fix local listo en esta rama;
- no desplegado aun.

#### P0.2 - Canal de alerta del supervisor roto por pagina archivada

Evidencia fresca:

```text
Failed to post Notion alert (HTTP 400)
Can't edit block that is archived. You must unarchive the block before editing.
```

Lectura:

- la integracion Notion no esta "caida";
- la pagina configurada para alertas (`NOTION_SUPERVISOR_ALERT_PAGE_ID`) ya no es una pagina editable valida;
- esto convierte errores operativos reales en silencio o ruido sin destino.

Estado:

- diagnosticado;
- requiere cambio de env o pagina en produccion;
- no se resuelve solo con deploy de codigo.

#### P0.3 - Rate limiting interno por `127.0.0.1`

Evidencia:

- el Worker limita por `request.client.host`;
- en la VPS, crons y llamados internos comparten `127.0.0.1`;
- durante el barrido exhaustivo empezaron a aparecer `429 Too Many Requests` tras varias llamadas locales seguidas.

Impacto:

- degrada pruebas E2E honestas;
- mezcla trafico humano, cron y diagnosticos en el mismo bucket;
- genera falsos sintomas de inestabilidad.

Estado:

- diagnosticado;
- no corregido en esta rama;
- merece slice propio.

### P1 - Integraciones vivas pero con drift

#### P1.1 - `research.web` sigue fallando en vivo

Evidencia:

- `research.web` devolvio `500` desde la VPS durante el barrido.
- `TAVILY_API_KEY` si existe en `~/.config/openclaw/env`.

Lectura:

- ya no es valido el diagnostico "falta env";
- queda un problema runtime real de proveedor, cuota o respuesta upstream que necesita inspeccion dedicada.

#### P1.2 - `scripts/run_worker_task.py` enrutaba mal tareas genericas

Sintoma:

- si no se exportaba `WORKER_URL`, el helper preferia `WORKER_URL_VM_INTERACTIVE` por sobre `WORKER_URL`;
- un smoke naive de Gmail/Calendar podia terminar en la VM interactive en vez del Worker local VPS.

Estado:

- corregido en esta rama;
- testeado;
- no desplegado aun.

#### P1.3 - `scripts/env_loader.py` era ciego al entorno canonico de la VPS

Sintoma:

- varios scripts leian solo `.env` del repo;
- en la VPS, el canonico real es `~/.config/openclaw/env`;
- eso genero falsos negativos en tooling de diagnostico.

Estado:

- corregido en esta rama;
- testeado;
- no desplegado aun.

#### P1.4 - `/providers/status` y `/quota/status` eran inutiles sin Redis local

Lectura:

- en la VM y otros runtimes parciales, estos endpoints devolvian `503`;
- eso los hacia poco utiles para observabilidad en el execution plane.

Estado:

- corregido en esta rama para devolver snapshot de configuracion con `redis_available: false`;
- skill `provider-status` alineada a ese comportamiento;
- no desplegado aun.

#### P1.5 - `Control Room`/`OpenClaw` si se actualiza, pero el resumen visual sigue mal

Hallazgo confirmado:

- la pagina `OpenClaw` fue leida en vivo por API;
- `last_edited_time` estaba al dia;
- el resumen actual sigue montado como callout + tarjetas angostas que no escalan bien.

Lectura:

- esto ya no es un problema de cron ni de despliegue atrasado;
- es un problema de composicion, densidad de texto y lenguaje visual.

#### P1.6 - `verify_stack_vps.py` sobre-prometia salud operativa

Hallazgo:

- el helper terminaba con "el stack esta listo" si Worker, Redis y Linear daban OK;
- eso era engañoso frente al estado real del supervisor y de Notion alerting.

Estado:

- corregido en esta rama para hablar de "plano base verificado", no de sanidad completa.

### P2 - Gobernanza, lenguaje y tooling

#### P2.1 - La palabra "Kris" en comentarios de Rick es semantica ambigua, no confusion fuerte de identidad

Hallazgo:

- en `Proyecto Embudo Ventas`, Rick escribio "no hace falta agregar comentario nuevo a Kris";
- en la pagina del entregable `Benchmark parcial de Kris Wojslaw para el embudo` no aparecio confusion adicional.

Lectura:

- parece shorthand impreciso para el caso/entregable `Kris Wojslaw`;
- conviene endurecer prompts para decir `caso Kris`, `benchmark de Kris` o `entregable Kris`, nunca solo `Kris`.

#### P2.2 - `notion.search_databases` es debil para descubrimiento libre

Hallazgo:

- una busqueda por `"embudo"` devolvio `count=0` pese a existir registros relevantes.

Lectura:

- para navegacion operativa conviene priorizar IDs canonicos y registry-first;
- no conviene vender search libre como base de coordinacion.

#### P2.3 - `scripts/secrets_audit.py` sigue siendo util pero ruidoso

Corrida actual:

- 9 findings;
- 3 son secretos locales reales en `.env`;
- el resto son falsos positivos sobre URLs de docs y una public key SSH.

Lectura:

- hoy no es un gate de CI suficientemente limpio;
- sirve como detector conservador, no como veredicto final de fuga.

## Telemetria y trazabilidad

Resultados frescos de `scripts/audit_traceability_check.py --format json`:

- `total_events`: 443
- `task_queued`: 326
- `task_completed`: 108
- `task_failed`: 9
- `trace_id`: 100%
- `task_type`: 100%
- `source`: 4.1%
- `source_kind`: 4.1%
- veredicto: `PARCIAL`

Resultados frescos de `scripts/governance_metrics_report.py --days 7 --format json`:

- `tasks_total`: 117
- `tasks_completed`: 108
- `tasks_failed`: 9
- `success_rate`: 92.3%
- todos los eventos del periodo cayeron en `2026-03-23`
- la carga esta sesgada a:
  - `ping`: 108 completadas
  - `nonexistent_task`: 9 fallidas

Lectura:

- la telemetria ya no esta ciega como antes;
- sigue demasiado dominada por smokes sintenticos;
- falta masa real de eventos cross-app con `source`/`source_kind`.

## Skills: que faltaba de verdad

### Resultado corregido

`scripts/skills_coverage_report.py` corrigio el mapeo y el coverage real quedo asi:

- Total Worker tasks: 80
- Tasks con skill: 71
- Tasks sin skill: 9
- Cobertura real: 89%

### Conclusion

No hacian falta "muchas skills nuevas". Hacia falta, sobre todo, distinguir tres cosas:

1. **Skills existentes pero sub-mapeadas**
   - `linear`
   - `notion`
   - `n8n`
   - `browser-automation-vm`

2. **Skills existentes pero todavia demasiado generales**
   - `notion-project-registry`
   - `browser-automation-vm`

3. **Huecos autenticos**
   - `gui.*`
   - `windows.open_url`
   - `google.audio.generate`
   - skill dedicada de diagnostico de interconectividad cross-system

Importante:

- el coverage corregido de este informe (`71/80`, 89%) es **coverage operativo por mapeo util**;
- el warning de `tests/test_skills_coverage.py` sigue reportando tasks sin `SKILL.md` directo porque esa prueba mide una nocion mas estricta: presencia de skill folder/task mas cercana a "una task = una skill".
- No es una contradiccion: hoy el repo tiene mejor cobertura operativa que cobertura estricta uno-a-uno.

### Recomendacion

- **No crear skill nueva de Linear**: con `linear` + `linear-delivery-traceability` alcanza; el problema era de coverage/reporting, no de ausencia.
- **No crear skill nueva de Notion desde cero**: conviene actualizar `notion-project-registry` o `notion`, no duplicar.
- **Si crear una skill nueva de diagnostico cross-system**.
- **Si ampliar `browser-automation-vm` para cubrir `gui.*` y `windows.open_url`**.

## Prompts listos para skills

### Prompt 1 - Nueva skill `system-interconnectivity-diagnostics`

```text
Crea una nueva skill repo-native para Umbral Agent Stack llamada `system-interconnectivity-diagnostics`.

Objetivo:
- diagnosticar el sistema completo sin confundir conectividad base con sanidad operativa;
- validar enlaces repo <-> VPS <-> VM <-> Worker <-> Dispatcher <-> Redis <-> Notion <-> Linear <-> Google <-> search providers;
- dejar siempre evidencia fresca, hallazgos priorizados y siguiente accion.

Debe cubrir:
- lectura de `.agents/PROTOCOL.md`, `.agents/board.md` y tareas activas;
- repo local: git status, ramas, tests, scripts de auditoria;
- VPS por SSH: procesos, crons, logs `/tmp/*.log`, env canonico `~/.config/openclaw/env`;
- Worker local VPS: `/health`, `/run`, `/providers/status`, `/quota/status`;
- VM headless e interactive: readiness, session choice, pruebas seguras;
- Notion: validar page IDs, paginas archivadas, lectura de comments/pages/databases;
- Linear: listar proyectos, issues canonicas de Agent Stack y issues de proyecto;
- Google: readiness real de Calendar/Gmail en el mismo turno;
- search: diferenciar env presente de backend realmente operativo;
- separar siempre `evidencia`, `inferencia` y `bloqueos`.

Guardrails:
- no declarar "stack sano" solo porque Worker/Redis/Linear responden;
- distinguir siempre lo que fue corrido en vivo vs lo inferido por codigo;
- si el runtime no esta desplegado, dejarlo explicito;
- si una pagina de Notion esta archivada o un canal de alertas esta roto, tratarlo como finding operativo.

Salida obligatoria:
- resumen ejecutivo;
- tabla por integracion con estado, evidencia y lectura;
- hallazgos P0/P1/P2;
- mejoras inmediatas vs mejoras diferidas;
- lista de follow-ups o issues sugeridas;
- seccion final `que fue probado en vivo`.
```

### Prompt 2 - Actualizar skill `browser-automation-vm`

```text
Actualiza la skill existente `browser-automation-vm` del repo Umbral Agent Stack para que deje de cubrir solo `browser.*` planificado y pase a gobernar la operacion completa de sesion interactiva en VM.

Objetivo:
- unificar `browser.*`, `gui.*` y `windows.open_url` bajo una sola disciplina operativa;
- decidir correctamente entre VM headless e interactive;
- exigir readiness antes de actuar;
- dejar secuencia segura de acciones y evidencia visual.

Debe cubrir:
- tasks `browser.navigate`, `browser.read_page`, `browser.screenshot`, `browser.click`, `browser.type_text`, `browser.press_key`;
- tasks `gui.desktop_status`, `gui.screenshot`, `gui.click`, `gui.type_text`, `gui.hotkey`, `gui.list_windows`, `gui.activate_window`;
- task `windows.open_url`;
- cuando usar cada familia y en que orden;
- como validar foco de ventana, pantalla y session antes de hacer clics;
- como tomar captura previa y posterior cuando la accion sea sensible.

Guardrails:
- no hacer clics destructivos ni enviar formularios finales sin instruccion explicita;
- si falta sesion interactiva, no improvisar;
- distinguir claramente navegacion browser DOM-driven de automatizacion de escritorio;
- no declarar exito sin capturar estado de ventana o resultado legible.

Salida de la skill:
- flujo recomendado paso a paso;
- checklist de readiness;
- ejemplos JSON reales;
- anti-patrones;
- decision tree simple: `browser` vs `gui` vs `windows.open_url`.
```

### Prompt 3 - Actualizar skill `notion-project-registry`

```text
Actualiza la skill existente `notion-project-registry` para endurecer la operacion registry-first del stack Umbral.

Objetivo:
- que cualquier trabajo sobre proyectos, entregables, bandeja puente y pages sueltas quede amarrado al registro canonico;
- cubrir mejor las tools low-level y evitar page sprawl o comentarios ambiguos.

Debe cubrir:
- tasks `notion.read_page`, `notion.read_database`, `notion.search_databases`, `notion.create_database_page`, `notion.update_page_properties`, `notion.upsert_project`, `notion.upsert_deliverable`, `notion.upsert_bridge_item`;
- cuando usar IDs canonicos en vez de search libre;
- como detectar paginas archivadas o contenedores invalidos;
- como escribir comentarios o updates sin ambiguedad de entidad;
- como reflejar proyecto, entregable y siguiente accion de forma coherente.

Guardrails:
- no crear paginas sueltas si ya existe proyecto o entregable canonico;
- no dejar comentarios tipo "Kris" o referencias ambiguas a una persona/caso;
- no depender de `search_databases` como mecanismo principal de navegacion;
- cada actualizacion debe dejar `proyecto`, `artefacto`, `siguiente accion` y `estado`.

Salida obligatoria:
- flujo registry-first;
- lista de tasks y payloads ejemplo;
- errores comunes;
- politica anti-page-sprawl;
- politica de naming y comentarios no ambiguos.
```

### Prompt 4 - Nueva skill `google-audio-generation`

```text
Crea una nueva skill repo-native llamada `google-audio-generation` para Umbral Agent Stack.

Objetivo:
- cubrir honestamente la task `google.audio.generate`, hoy sin skill dedicada;
- documentar prerrequisitos reales, proveedor, limites y ejemplos validos;
- evitar que agentes inventen soporte donde no existe.

Debe cubrir:
- task `google.audio.generate`;
- diferencias entre Gemini/Vertex/otros paths Google del repo;
- variables de entorno necesarias;
- formato de input y output;
- casos de uso permitidos y no permitidos.

Guardrails:
- no asumir que `google.image.generate` y `google.audio.generate` comparten el mismo backend;
- no afirmar operatividad sin prueba viva si el usuario pide usarla;
- separar claramente AI Studio vs Vertex si aplica.

Salida:
- overview;
- prerequisitos;
- payloads JSON ejemplo;
- troubleshooting;
- decision de fallback si la task no esta lista para produccion.
```

## Cambios dejados en esta rama

### Corregidos y testeados localmente

- `scripts/env_loader.py`
  - ahora carga `~/.config/openclaw/env` antes de `.env` del repo.
- `scripts/run_worker_task.py`
  - ya no enruta tasks genericas a la VM interactive por defecto;
  - ahora prioriza `WORKER_URL` para tasks genericas.
- `worker/app.py`
  - `/quota/status` y `/providers/status` devuelven snapshot util aunque Redis no exista localmente.
- `scripts/vps/dispatcher-service.sh`
  - deja de depender ciegamente de `USER`;
  - tolera ausencia de `systemd --user`;
  - cae a modo `process_only` cuando corresponde.
- `scripts/verify_stack_vps.py`
  - ya no declara "stack listo" por conectividad minima.
- `scripts/skills_coverage_report.py`
  - coverage corregido;
  - fecha dinamica;
  - reporte util para lectura actual.
- `openclaw/workspace-templates/skills/provider-status/SKILL.md`
  - alineada al nuevo comportamiento sin Redis.

### Validacion local de esta rama

- `tests/test_env_loader.py`
- `tests/test_run_worker_task.py`
- `tests/test_provider_status.py`
- `tests/test_quota_endpoint.py`
- `tests/test_worker_inventory_smoke.py`
- `tests/test_google_calendar_gmail.py`
- `tests/test_research_handler.py`
- `tests/test_linear.py`
- `tests/test_notion_read_page.py`
- `tests/test_notion_search_databases.py`
- `WORKER_TOKEN=test python -m pytest tests -q`

Resultado final:

- `1198 passed, 4 skipped, 1 warning`

## Que sigue

### Siguiente slice recomendado

1. Desplegar esta rama o sus fixes equivalentes en VPS/VM.
2. Corregir `NOTION_SUPERVISOR_ALERT_PAGE_ID` para que apunte a una pagina activa.
3. Verificar que el loop del supervisor desaparezca en vivo.
4. Abrir slice propio para rate limiting interno por `127.0.0.1`.
5. Abrir slice propio para `research.web` runtime real.
6. Rehacer visualmente el resumen de `OpenClaw` con una composicion mas robusta: menos texto por tarjeta, ancho util real y una sola jerarquia visual dominante.

### Veredicto final

El sistema no necesita otra auditoria "desde cero". Necesita:

- desplegar fixes operativos ya identificados;
- separar conectividad minima de sanidad real;
- mejorar dos puntos estructurales de interconexion:
  - supervisor/alerting
  - rate limiting interno

Lo positivo es que el stack ya no esta en modo caos: hoy esta en modo **conectado pero mal coordinado**. Esa diferencia importa, porque permite atacar slices concretos en vez de volver a auditar todo a ciegas.
