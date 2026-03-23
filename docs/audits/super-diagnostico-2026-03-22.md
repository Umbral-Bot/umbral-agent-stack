# Super diagnostico del sistema Umbral Agent Stack

Fecha de ejecucion: 2026-03-22 (con varias comprobaciones remotas ya en UTC 2026-03-23)
Rama de trabajo: `codex/super-diagnostico-sistema`

## Resumen ejecutivo

- El repo local esta sano a nivel de codigo: `python -m pytest tests/ -v` dio `1171 passed, 4 skipped, 1 warning`.
- La VPS esta operativa en lo basico: Redis responde `PONG`, el Worker local responde `200` con 77 handlers, Linear responde via Worker y el proyecto canonico de Agent Stack existe.
- El runtime productivo sigue con drift operativo real:
  - la VPS esta atrasada respecto a GitHub (`HEAD 9b9b28c` vs `origin/main ee09ef3` despues de `git fetch origin`);
  - hay dos procesos `dispatcher.service` vivos en la VPS;
  - el Notion Poller no estaba corriendo al momento del diagnostico;
  - la VM expone `/run` con contrato legacy (`task`) y devuelve `400` si se usa `task_type`;
  - `/providers/status` en la VM devuelve `503` porque no tiene Redis.
- El E2E productivo de la VPS esta casi verde, pero `research.web` falla hoy por cuota agotada de Tavily, no por falta de key.
- El sistema de issues automaticas sigue generando ruido: el proyecto canonico `Mejora Continua Agent Stack` existe, pero el path automatico actual crea issues crudas `[Auto] ...` y duplica mucho backlog.
- La trazabilidad mejora respecto de auditorias antiguas en un punto (`task_queued` si existe en el log local), pero sigue incompleta: `source` tiene 0% de cobertura y el log auditado localmente no muestra eventos `task_completed`, `task_failed` ni `task_blocked`.
- Rick/OpenClaw tiene 28 skills en workspace y 6 skills globales, mientras el repo trae 73 plantillas. Hay drift claro entre lo instalado y lo versionado.

## Alcance y metodo

Se ejecutaron comprobaciones en cuatro planos:

1. Repo local y tests.
2. VPS por SSH (`vps-umbral`).
3. Worker VM por HTTP usando `WORKER_URL_VM`.
4. Estado de Linear y configuraciones locales de Codex, Cursor, Claude, Antigravity y OpenClaw.

## Fase 1 - Funcionamiento completo del sistema

### 1. VPS - servicios, crons y git

Estado observado en vivo:

| Componente | Resultado |
| --- | --- |
| Redis | OK (`PONG`) |
| Worker local | OK (`/health` 200, version `0.4.0`, 77 handlers) |
| Dispatcher | Parcial: hay 2 procesos vivos |
| Notion Poller daemon | FAIL: no habia proceso vivo al revisar `pgrep` |
| OpenClaw Gateway | Parcial: proceso `openclaw-gateway` vivo, pero `openclaw` no esta en PATH |
| Crons | 13 entradas activas |
| Git en VPS | `main` atrasada 6 commits vs `origin/main` |

Hallazgos concretos:

- La VPS corre `main`, pero no esta al dia:
  - `HEAD`: `9b9b28c`
  - `origin/main` despues de `git fetch origin`: `ee09ef3`
  - `behind_count`: 6
- `git status` mostro `?? .venv` en la VPS, o sea hay un artefacto local no trackeado en el clone productivo.
- Los cron jobs reales son 13, no 12. El extra es:
  - `notion-curate-cron.sh`
- El Notion Poller no estaba corriendo al momento del diagnostico, aunque el cron de watchdog si existe. El log `/tmp/notion_poller_cron.log` muestra intentos de arranque el `2026-03-16` y `2026-03-17`, pero no evidencia de proceso vivo actual.
- Los procesos `dispatcher.service` observados fueron:
  - `/home/rick/umbral-agent-stack/.venv/bin/python -m dispatcher.service`
  - `/usr/bin/python3 -m dispatcher.service`

### 2. VM - Worker y conectividad

Resultados:

| Check | Resultado |
| --- | --- |
| `GET /health` directo a VM | OK |
| `POST /run` con payload legacy `{\"task\":\"ping\"}` | OK |
| `POST /run` con payload moderno `{\"task_type\":\"ping\"}` | FAIL 400 |
| `GET /providers/status` | FAIL 503 (`Redis not available`) |

Hallazgos:

- La VM responde por HTTP y ejecuta `ping`, asi que la conectividad base y el token funcionan.
- El contrato efectivo de la VM no esta alineado con el contrato moderno documentado:
  - `task_type` falla con error de validacion pydantic.
  - `task` funciona.
- Eso implica drift de despliegue o drift de contrato, aunque el `health` publique 77 handlers.
- No hubo acceso SSH/WinRM directo a la VM desde esta sesion, asi que no se pudo verificar:
  - rama git de la VM,
  - estado del servicio NSSM,
  - logs locales,
  - `git pull origin main` en la propia VM.

### 3. Dispatcher -> Worker E2E

Comando remoto ejecutado en VPS:

`PYTHONPATH=. python3 scripts/e2e_validation.py`

Resultado:

- `16/17 PASS`
- `3 SKIP`
- `1 FAIL`

El unico fallo real fue:

- `research.web` -> `500 Internal Server Error`

Causa raiz capturada por llamada directa al Worker:

```text
Tavily API error 432: This request exceeds your plan's set usage limit
```

Interpretacion:

- El problema no es ausencia de `TAVILY_API_KEY`.
- El problema es cuota/plan agotado.
- Como `ESCALATE_FAILURES_TO_LINEAR` esta activo, estas corridas pueden seguir creando issues automaticas de ruido si se repiten sin dedupe.

## Fase 2 - Testeo

### pytest completo

Comando local:

`WORKER_TOKEN=test python -m pytest tests/ -v`

Resultado:

- `1171 passed`
- `4 skipped`
- `1 warning`
- Tiempo total aproximado: `13.91s`

Notas:

- Se ejecuto con Python global `3.13.7`; no habia `.venv` local en este clone.
- La advertencia fue de cobertura de skills (`21 task(s) have no SKILL.md`), no un fallo funcional.
- Con esta corrida quedan cubiertos tambien los tests especificos de Linear, Notion, Granola y routing.

## Fase 3 - APIs y conexiones

### 1. APIs externas en VPS

Presencia de config observada en `~/.config/openclaw/env`:

| Variable / servicio | Estado |
| --- | --- |
| `LINEAR_API_KEY` | present |
| `NOTION_API_KEY` | present |
| `TAVILY_API_KEY` | present |
| `GOOGLE_API_KEY` | present |
| `N8N_URL` | present |
| `N8N_API_KEY` | present |
| `OPENAI_API_KEY` | missing |
| `ANTHROPIC_API_KEY` | missing |
| `LANGFUSE_PUBLIC_KEY` | missing |
| `LANGFUSE_SECRET_KEY` | missing |

Validaciones vivas:

- Linear via Worker: OK (`linear.list_teams`)
- Notion via Worker: OK (`notion.update_dashboard` en `verify_stack_vps.py`)
- `research.web`: FAIL por cuota Tavily agotada
- OpenAI / Anthropic: no configurados en VPS al momento del diagnostico
- Langfuse: no configurado en VPS al momento del diagnostico

### 2. Notion en vivo via Worker VM

Se leyo `notion.read_database` en tres DBs usando el Worker de la VM:

| DB | Resultado |
| --- | --- |
| `Proyectos - Umbral` | OK |
| `Entregables Rick - Revision` | OK |
| `Tareas - Umbral Agent Stack` | OK |

Muestras devueltas:

- Proyectos: `Proyecto Embudo Ventas`, `Sistema Editorial Automatizado Umbral`, `Uso de Freepik via VM`
- Entregables: `Cierre critico del estado real del proyecto embudo`, `Estado real de Freepik en VM`, `Prueba final del flujo ordenado de entregables`
- Tareas: `Prueba final del flujo ordenado de tareas`, `Prueba de herencia de icono...`, `Prueba de gobernanza enlazada...`

Conclusiones:

- Notion no esta bloqueado.
- El stack si tiene conectividad real hacia los artefactos de gestion operativa.

## Fase 4 - Modelos, routing y OpenClaw

### 1. Providers y routing observados

`/providers/status` en la VPS devolvio:

- configurados: `azure_foundry`, `gemini_flash`, `gemini_flash_lite`, `gemini_pro`, `gemini_vertex`
- no configurados: `claude_haiku`, `claude_opus`, `claude_pro`, `openclaw_proxy`

Lectura operativa:

- La realidad productiva hoy es Gemini + Azure.
- Claude no esta configurado en el Worker de la VPS, aunque la politica declarada lo siga prefiriendo para `coding`, `general`, `ms_stack` y `writing`.
- Esto ya habia sido corregido a nivel repo por `UMB-77`, pero la VPS sigue atrasada 6 commits; por eso el runtime productivo no refleja plenamente el fix mergeado en GitHub.

### 2. OpenClaw

Hallazgos:

- Existe instalacion real en `~/.openclaw/`.
- `openclaw-gateway` aparece como proceso vivo.
- El binario `openclaw` no esta en PATH de la VPS.
- `~/.openclaw/openclaw.json` declara integraciones para:
  - Linear
  - Notion
  - n8n
  - browser

Esto confirma que Rick esta montado sobre un workspace OpenClaw real, no solo sobre documentacion.

## Fase 5 - Sistema de reportes automaticos de incidencias

### Estado actual

Ruta actual en codigo:

- `dispatcher/service.py` -> `_escalate_failure_to_linear(...)`
- hace `linear.create_issue`
- construye titulo/descripccion crudos tipo `[Auto] Tarea fallida: ...`
- no usa el flujo canonico rico de Agent Stack

Ruta rica existente pero no integrada al runtime automatico:

- `worker/tasks/linear.py` -> `handle_linear_publish_agent_stack_followup`
- documentada en `docs/67-linear-agent-stack-protocol.md`

### Estado real en Linear

Proyecto canonico:

- `Mejora Continua Agent Stack`
- URL: `https://linear.app/umbral/project/mejora-continua-agent-stack-943c9a8c98f6`

Labels relevantes existentes:

- `Agent Stack`
- `Mejora Continua`
- `Operational Debt`
- `Drift`
- `Agente: Codex`
- `Agente: Cursor`
- `Agente: Rick`

Backlog observado:

- `UMB-140` y `UMB-141` ya representan el camino correcto de follow-ups canonicos.
- Sigue habiendo una gran cantidad de issues `[Auto] ...` como:
  - `UMB-118` a `UMB-139` por `research.web`
  - multiples issues historicas por `windows.fs.*`
- Muchas de estas issues automaticas:
  - no estan adjuntas al proyecto canonico,
  - no tienen labels base del stack,
  - no deduplican raiz comun,
  - no dejan evidencia rica.

### Diseno objetivo recomendado

1. Reemplazar la escalacion automatica cruda por `linear.publish_agent_stack_followup`.
2. Adjuntar siempre al proyecto canonico `Mejora Continua Agent Stack`.
3. Aplicar labels base:
   - `Agent Stack`
   - `Mejora Continua`
   - tipo (`Operational Debt`, `Drift`, `Incident`, `Quota`, `Auth`, `Config Drift`)
4. Ownership:
   - por defecto sin asignar
   - opcional `designated_agent`
   - nombre generico operativo: `Stack Engineers`
5. Dedupe obligatoria por huella:
   - `task`
   - clase de error normalizada
   - plano afectado (`vps`, `vm`, `openclaw`, `notion`, `linear`)
   - ventana temporal
6. Evidencia minima requerida:
   - `task_id`
   - `trace_id`
   - `source`
   - worker/plano afectado
   - HTTP status / provider
   - primer fallo / ultimo fallo
   - proximo paso sugerido

## Fase 6 - Real vs esperado

| Principio / componente | Esperado | Real | Brecha |
| --- | --- | --- | --- |
| Solo David manda | Rick y backlog interno con trazabilidad | El control humano existe, pero el backlog automatico mete mucho ruido | Media |
| Resiliencia | Modo degradado sano y un solo control plane consistente | Redis/Worker OK, pero poller caido, 2 dispatchers y Tavily saturado | Alta |
| Auditable | Traza completa end-to-end | Hay `trace_id` parcial y falta `source`; el log auditado no refleja completions/failures | Alta |
| Multi-modelo | Routing real segun providers configurados | Repo ya corregido, pero VPS atrasada y VM con contrato legacy | Alta |
| Equipos como config | Routing y escalacion alineados a config y proyecto canonico | `teams.yaml` existe, pero auto-issues no usan el proyecto canonico rico | Media |
| Extensible | Skills/MCPs sincronizados entre repo y runtimes | Rick tiene skills en workspace que no estan en repo templates | Media |

## Fase 7 - Proyectos estancados

Proyectos de Linear con poco o nulo movimiento reciente:

| Proyecto | Ultima actualizacion observada | Lectura |
| --- | --- | --- |
| `Sistema Editorial Automatizado Umbral` | 2026-03-09 | Sigue en backlog; en Notion y Linear hay artefactos, pero sin integracion final real |
| `Proyecto Embudo Ventas` | 2026-03-09 | Sigue vivo en Notion, pero sin empuje operativo reciente |
| `Proyecto Granola` | 2026-03-10 | Hay pipeline y DB viva, pero aparecieron tareas huerfanas y drift reciente |
| `Control de Navegador VM` | 2026-03-10 | Sigue como backlog tecnico |
| `Autonomia RPA GUI en VM` | 2026-03-10 | Sigue como backlog tecnico |
| `Uso de Freepik via VM` | 2026-03-10 | Aparece en Notion y Linear, pero no muestra actividad posterior |
| `Sistema Automatizado de Busqueda y Postulacion Laboral` | 2026-03-10 | Proyecto backlog sin movimiento reciente |

Causas probables recurrentes:

- falta de sync repo/VPS/VM;
- falta de cierre de integraciones reales (destinos finales, browser/gui, publicaciones);
- backlog contaminado por auto-issues de bajo valor;
- ausencia de ownership operativo sostenido;
- skills/configuracion repartidas entre repo, Codex home y OpenClaw workspace.

## Fase 8 - Trazabilidad

Comandos locales:

- `python scripts/audit_traceability_check.py --format json`
- `python scripts/governance_metrics_report.py --days 7 --format json`

Resultados:

- `ops_log.jsonl` auditado localmente: `202` eventos
- todos los eventos auditados son `task_queued`
- `trace_id`: `100%`
- `task_type`: `100%`
- `source`: `0%`
- `governance_metrics_report`: `0 tasks_total` para 7 dias en ese log

Interpretacion:

- El gap historico "task_queued nunca se emite" ya no describe bien el estado actual del log auditado local.
- El gap vivo ahora es otro:
  - falta `source`;
  - el log auditado no refleja el resto del ciclo de vida.
- Eso hace imposible responder con fiabilidad preguntas como:
  - cuantas tareas terminaron,
  - cuantas fallaron,
  - cuanto tardaron,
  - desde que origen entraron.

## Fase 9 - Oportunidades de mejora priorizadas

### P0

1. Sincronizar VPS a `origin/main` y validar que incorpore los fixes de `UMB-77`.
2. Dejar un solo `dispatcher.service` vivo en VPS.
3. Recuperar el Notion Poller daemon y dejar evidencia del metodo real de arranque.
4. Cortar el flood de `research.web`:
   - subir plan Tavily,
   - o meter fallback/guard explicito cuando Tavily este en limite.
5. Homologar el contrato `/run` de la VM para aceptar `task_type` igual que el resto del stack.

### P1

6. Reemplazar `_escalate_failure_to_linear` por el flujo canonico `linear.publish_agent_stack_followup`.
7. Implementar dedupe real de incidencias automaticas.
8. Agregar `source` y completar eventos `task_completed` / `task_failed` / `task_blocked` en el log que realmente se monitorea.
9. Hacer que `/providers/status` tenga modo degradado util tambien en la VM sin Redis.
10. Backport al repo las skills `google-agenda-readiness`, `granola-meeting-capitalization` y `umbral-worker`.

### P2

11. Dejar `openclaw` accesible en PATH o documentar el binario real.
12. Consolidar inventario de skills por herramienta y evitar drift entre homes locales y workspace de Rick.
13. Reducir overlap semantico en familias de skills `linear/*`, `notion/*`, `linkedin/*`, `editorial/*`.

## Fase 10 - Debugging

Fuentes y comandos utiles observados:

- VPS:
  - `scripts/verify_stack_vps.py`
  - `scripts/e2e_validation.py`
  - `scripts/smoke_test.py`
  - `/tmp/supervisor.log`
  - `/tmp/notion_poller_cron.log`
  - `~/.config/umbral/ops_log.jsonl`
- Local:
  - `scripts/audit_traceability_check.py`
  - `scripts/governance_metrics_report.py`
  - `python -m pytest tests/ -v`

Fallos reproducibles utiles:

- `research.web` en VPS -> 500 por Tavily `432 usage limit`
- VM `/run` con `task_type` -> 400
- VM `/providers/status` -> 503 sin Redis

## Fase 11 - Seguridad

Hallazgos:

- `.env` no esta trackeado en git; `.env.example` si.
- `LINEAR_WEBHOOK_SECRET` ya existe en `.env.example` y el codigo del webhook lo referencia.
- `worker/app.py` mantiene auth Bearer y rate limit por `RATE_LIMIT_RPM`.
- `python scripts/secrets_audit.py` requiere `PYTHONIOENCODING=utf-8` en esta terminal de Windows; sin eso falla por encoding y puede dar un falso negativo operativo.
- La auditoria de secretos encontro:
  - secretos reales en `.env` local (esperable, no trackeado),
  - varios falsos positivos en docs/URLs,
  - una clave publica SSH hardcodeada en `scripts/fix-vm-authorized-keys.py` (no es secreto, pero si artefacto sensible a revisar).

Limitaciones:

- No se verifico rotacion real de tokens.
- No se auditaron ACLs de Tailscale ni permisos Windows de la VM porque no hubo acceso admin/SSH a la VM.

## Fase 12 - Skills y MCPs

### Codex

- Skills locales en `~/.codex/skills`: `37`
- MCPs declarados en `~/.codex/config.toml`:
  - Notion
  - Figma
  - Linear
  - Revit
  - Playwright

### Cursor

- Skills locales en `~/.cursor/skills-cursor`: `6`
- MCPs declarados en `~/.cursor/mcp.json`:
  - Notion
  - Linear
  - Revit
  - Power BI Remote
  - Power BI Modeling
  - GitHub
  - Hostinger

### Claude

- No se vio un listado de MCP servers equivalente al de Cursor/Codex en `settings.json`.
- Si aparece evidencia de:
  - permiso `mcp__claude_ai_Notion__notion-fetch`
  - plugins habilitados: GitHub, Playground, Stripe, Supabase, Linear, Commit Commands, Agent SDK Dev, Code Review, Code Simplifier

### Antigravity

- No se encontro un archivo explicito de MCP config bajo `~/.antigravity`.
- Si hay instalacion tipo VS Code con extensiones para:
  - Claude Code
  - GitHub / PRs
  - Azure
  - Docker
  - Python
  - PowerShell

### Rick / OpenClaw

- Plantillas versionadas en repo: `73`
- Skills instaladas en `~/.openclaw/workspace/skills`: `28`
- Skills globales en `~/.openclaw/skills`: `6`
- `~/.openclaw/openclaw.json` referencia herramientas de:
  - Notion
  - Linear
  - n8n
  - browser

## Fase 13 - Oportunidades de skills / MCPs para Rick

### Drift detectado

- Skills instaladas en el workspace de Rick pero no presentes hoy en `openclaw/workspace-templates/skills/` del repo:
  - `google-agenda-readiness`
  - `granola-meeting-capitalization`
  - `umbral-worker`

### Overlap semantico

No hay duplicados exactos en nombres, pero si familias muy solapadas:

- `linear`, `linear-issue-triage`, `linear-project-auditor`, `linear-delivery-traceability`
- `notion`, `notion-workflow`, `notion-project-registry`
- `linkedin-content`, `linkedin-david`, `linkedin-marketing-api-embudo`
- `editorial-voice-profile`, `editorial-source-curation`, `multichannel-content-packager`, `publication-gatekeeper`

### Skills nuevas recomendadas para Rick

1. `stack-runtime-diagnostic`
   - health, dispatcher singleton, poller, crons, provider status, quota, E2E.
2. `stack-incident-publisher`
   - usar `linear.publish_agent_stack_followup` con payload rico y proyecto canonico.
3. `stack-issue-dedupe-triage`
   - agrupar `[Auto]` por raiz comun y proponer cierres/merge.
4. `vm-contract-smoke`
   - validar `/run`, `/providers/status`, handlers criticos y version API en la VM.
5. `repo-runtime-sync-check`
   - comparar repo local, VPS `main`, VM y skills instaladas.

## Bloqueos explicitos

1. No hubo acceso SSH/WinRM directo a la VM desde esta sesion.
2. `openclaw` no esta en PATH de la VPS, asi que no se pudo usar `openclaw status --all` como comando directo.
3. El entorno local no tenia `.venv`, `redis-cli` ni `openclaw` en PATH.
4. `WORKER_URL` del `.env` local no corresponde a un worker local activo en esta maquina.
5. `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` y Langfuse no estaban configurados en la VPS al momento del diagnostico.

## Conclusiones

El sistema no esta caido; esta en un estado de "operativo con drift".

Lo mas importante hoy no es agregar mas features. Lo prioritario es estabilizar la operacion real:

1. alinear VPS y VM con `origin/main`;
2. dejar un solo dispatcher y recuperar el poller;
3. cortar la cascada de errores repetidos de `research.web`;
4. endurecer la generacion automatica de issues;
5. cerrar el drift de skills entre repo, homes locales y workspace de Rick.

