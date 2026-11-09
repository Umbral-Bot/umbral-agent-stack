<!-- Informe íntegro del subagente de inventario (sesión coordinadora local_815b91f1). Solo lectura. Es evidencia de lectura; el coordinador no verificó cada ítem por separado. -->

# Inventario técnico TARRO — diagnóstico multisistema (solo lectura)

**Inicio UTC:** 2026-11-09 05:35:33Z  **Fin UTC:** 2026-11-09 05:40:34Z
Modo: sin cambios en archivos, configuración, servicios ni tareas; sin autenticaciones; secretos no copiados (solo nombres de variables).

## 1. Identidad del equipo

| Ítem | Resultado | Evidencia / comando | Límite |
|---|---|---|---|
| Hostname | `TARRO` | `$env:COMPUTERNAME` | — |
| Usuario | `TARRO\david` (cuenta local, no dominio) | `$env:USERDOMAIN\$env:USERNAME` | — |
| Windows | Windows 11 Pro 10.0.26200, build 26200, DisplayVersion **25H2** | `Get-CimInstance Win32_OperatingSystem` | — |
| Último arranque / uptime | 2026-10-30 16:48:43Z → **9d 12h 46m** al inicio del inventario | `LastBootUpTime` | — |

## 2. Tailscale

| Ítem | Resultado | Evidencia / comando | Límite |
|---|---|---|---|
| Instalado | Sí, `C:\Program Files\Tailscale\tailscale.exe`, versión **1.94.2** | `tailscale --version` | — |
| `tailscale status` | **Falla**: «failed to connect to local tailscaled process; is the Tailscale service running?» | `tailscale status` | No hay lista de nodos disponible |
| Servicio `Tailscale` | **Stopped, StartType = Disabled** | `Get-Service Tailscale` | No se intentó arrancar |
| Proceso GUI | `tailscale-ipn.exe` (pid 64948) corriendo desde 10-30 17:00Z, pero sin backend | `Win32_Process` | — |
| Pistas de IPs de tailnet | `known_hosts` contiene `100.109.16.40` y `100.113.249.25` | ver ítem 3 | Sin `tailscale status` no se correlacionan con nombres |

**Conclusión:** TARRO tiene el cliente instalado pero el servicio está deshabilitado; en este momento no está en la tailnet. (PCRick reporta además que la clave de TARRO caducó el 2026-08-31.)

## 3. SSH

| Ítem | Resultado | Evidencia / comando | Límite |
|---|---|---|---|
| `~/.ssh/config` | Existe (291 B, mod. 2026-04-12). Un solo bloque: `Host vps-umbral umbral-vps` → `HostName <IP pública VPS>`, `User rick` (puerto 22) | `Get-Content` filtrado | IdentityFile no reportado por diseño |
| `known_hosts` | 14 líneas, mod. 2026-08-04. Hosts: `[<IP redactada>]:65002`, `100.109.16.40`, `100.113.249.25`, `<IP pública VPS>`, `<IP LAN redactada>`, `github.com`, `<host VPS>`, `<host VPS>` | `cut -d' ' -f1 \| sort -u` | — |
| Otros archivos en `.ssh` | `id_rsa` (2026-02-27), `id_rsa.pub`, `known_hosts.old` | `Get-ChildItem` | Solo nombres |
| Sesiones SSH activas | 2 procesos `ssh.exe` (pids 85580, 64436) hacia `<IP pública VPS>` usuario `rick`, iniciados 11-06 01:57Z, padre = proceso de la app Claude Desktop; túneles de control (`-T`, `-s`) de la sesión Remote Control «UAS - VPS» | `Win32_Process` CommandLine | — |
| Clave suelta fuera de `.ssh` | `C:\Users\david\openclaw` **no es carpeta: es un archivo de 464 B con cabecera `OPENSSH PRIVATE KEY`** (ed25519), fecha 2026-02-25 23:44Z | `Get-Item`, cabecera | Contenido no copiado |

## 4. Puertos en escucha (TCP)

| Puerto | Resultado | Proceso |
|---|---|---|
| **8088** | **ESCUCHA en 0.0.0.0** (todas las interfaces) | `python.exe` pid 19900 |
| 8089, 18789, 18790, 6379, 5985, 22 | NO escuchan | — |

Otros: `5432` postgres (0.0.0.0, pid 7444); `5179`/`5180` node (vite); `8765`, `8781`, `8783` python (127.0.0.1); `8782` node (127.0.0.1); `49502`/`49508`/`56392` Antigravity (127.0.0.1); `9222` D5Launcher; `2179` vmms (Hyper-V). Firewall: dos reglas inbound **Allow** para 8088, perfil Any, nombre `ms-resource:AppTitle` (reglas creadas por app/Store).

## 5. Procesos relevantes

| Familia | Resultado |
|---|---|
| openclaw | **Ningún proceso** en el host. Solo `VmConnect.exe` (pid 59096, 11-07 00:39Z) conectado a la **VM Hyper-V «OpenClaw»** (GUID 870F59FD-…) |
| python / uvicorn | 102 `python.exe`: 40 `illustrator-mcp`, 42 `dynamo-graph-mcp`, 4 windows-mcp, 4 blender-mcp, 4 `live_conductor_mcp.py`, 4 `tools.py` (Bonsai_mcp), 3 servidores por puerto y **1 worker: `Python313\python.exe C:\GitHub\umbral-agent-stack-codex\scripts\vm\start_primary_worker.py`** (pid 19900, inicio 2026-10-30 16:52Z) |
| node | 247 `node.exe` + 48 `node_repl.exe` (runtime CUA de Codex). Casi todos servidores MCP lanzados por hosts de agente (88 `npx-cli.js`, 28 `@playwright/mcp`, 21 `hostinger-api-mcp`, 20 `./server.mjs`, 19 `copilot-studio-mcp`, 8 notion-mcp-server, 8 desktop-commander, 8 server-pdf, …). Muchos probablemente huérfanos (no verificado) |
| redis | **No hay proceso ni puerto** |
| codex | 3 `codex.exe` + `codex-code-mode-host.exe`, `codex-computer-use-swift.exe`, `codex-windows-sandbox-service.exe` |
| claude | 34 `claude.exe`: app Claude Desktop (`Claude_4.23118.0.0`) y Claude Code embebido `2.1.317` |
| cursor | 16 `Cursor.exe` (3 principales desde 11-07 01:08Z) |
| antigravity | 3 `Antigravity.exe` desde 11-05 15:19Z |
| grok | 9 `Grok Bot.exe` (Electron, principal pid 84964 desde 11-07 00:34Z) |
| ngrok / tailscaled / sshd | Ninguno |
| ssh | 2 `ssh.exe` a la VPS (ítem 3) |

## 6. Tareas programadas (filtro openclaw|uas|umbral|worker|dispatcher|rick|grok|claude|codex)

| Tarea | Estado | Último resultado | Última / próxima (hora local UTC-3) | Acción |
|---|---|---|---|---|
| `\UmbralWorkerPrimary` | Ready | **0x0** | 10/30 13:52 / — (logon) | `…umbral-agent-stack-codex\scripts\vm\start_primary_worker_hidden.ps1` → origen del worker 8088 |
| `\GranolaVmRawIntake` | Ready | **0x1 (error)** | 11/09 00:15 / 11/09 04:15 | `…umbral-agent-stack-codex\scripts\vm\start_granola_vm_raw_intake_hidden.ps1` |
| `\GranolaVmRawIntakeStartup` | Ready | **0x1 (error)** | 10/30 13:52 / — (logon) | `…start_granola_vm_raw_intake_startup_hidden.ps1` |
| `\Umbral-SkillsReceiver-tarro-windows` | Ready | 0x0 | 11/09 02:20 / 02:50 | `…SkillsReceiver\venv\Scripts\pythonw.exe run-skills-receiver.py --profile tarro-windows` (cada 30 min) |
| `\UmbralGranolaDriveFeeder` | Ready | 0x0 | 11/08 09:30 / 11/09 09:30 | `…umbral-agent-stack-claude\scripts\vm\granola_drive_feeder.py --max-creates 10 --max-updates 1 --execute` (diaria) |
| `\UmbralRegistryBackupDaily` | Ready | 0x0 | 11/08 04:00 / 11/09 04:00 | `…notion-governance\scripts\daily-registry-backup.ps1` |
| `\Umbral\OpsResumeWriter` | Ready | **0x2 (error)** | 11/09 02:30 / 03:00 | `…notion-governance\scripts\ops_resume_projection_scheduled.py --maintenance-config …ops-resume-maintenance.json` (cada 30 min) |

## 7. Herramientas de agente instaladas

| Herramienta | Resultado |
|---|---|
| claude | **2.1.280** CLI en PATH; la app Desktop ejecuta 2.1.317 |
| codex | codex-cli **0.163.0** |
| gh | **2.87.3** |
| node / npm | v22.20.0 / 10.9.3 |
| python | 3.13.7; uv 0.8.19 con CPython 3.12.11 |
| az | azure-cli 2.83.0 |
| tailscale | 1.94.2 (servicio deshabilitado) |
| git | 2.51.0.windows.1 |
| cursor | CLI 1.6.35; app 3.29.9 |
| antigravity | No en PATH; `Programs\Antigravity\Antigravity.exe` 2.29.0.0 |
| openclaw, ngrok, redis-server | No instalados |
| pwsh | 7.6.9 |

## 8. Clones git

Total 72 repos bajo `C:\GitHub` (incl. `_archive`, `_worktrees`) y 10 bajo `C:\Users\david\source`.

| Repo | Rama | Último commit | Sucio | Ahead/Behind |
|---|---|---|---|---|
| `C:\GitHub\umbral-agent-stack` | `rick/motor-piezas-lab` | `2356a1e1` 2026-11-09 | **114** | 0/0 |
| `C:\GitHub\umbral-agent-stack-claude` | `main` | `57879ae` 2026-09-05 (#691) | 1 | **0/16 detrás** |
| `C:\GitHub\umbral-agent-stack-codex` | `main` | `442e23b` 2026-09-13 (#692) | **49** | **0/15 detrás** |
| `C:\GitHub\umbral-agent-stack-antigravity` | `main` | `66564a2` 2026-08-11 | 0 | 0/0 |
| `C:\GitHub\umbral-agent-stack-copilot` | `main` | `66564a2` 2026-08-11 | 0 | 0/0 |
| `C:\GitHub\umbral-agent-stack-astra6-medium` | `codex/editorial-astra6-medium-20260913` | `4f4beb2` | 0 | 0/0 |
| `C:\GitHub\notion-governance` | `main` | `48a9344` 2026-09-15 | 0 | 0/0 |
| `C:\GitHub\notion-governance-cursor` | `cursor/b2b-root-move` | `110109c` 2026-03-30 | **142** | sin upstream |
| `C:\GitHub\umbral-skills-registry` | `main` | `aab2d24` 2026-11-06 | 0 | 0/10 detrás |
| `C:\GitHub\umbral-skills-receiver-client` | `main` | `04aceb2` 2026-11-04 | 0 | 0/0 |
| `C:\GitHub\umbral-ai-registry-backup` | `main` | `d47b9b5` 2026-11-08 «snapshot (daily auto)» | 0 | 0/0 |
| `C:\GitHub\dynamo-mcp` | `main` | `dea1d37` 2026-09-15 | 21 | 0/0 |
| `C:\GitHub\umbral-bot-cursor` | `cursor/beta-3-parts-handoffs-2026-06-08` | `ccbd9809` 2026-08-06 | **211** | 3/0 |
| `C:\GitHub\umbral-bot-copilot` | `main` | `8b4b3fd` 2026-08-11 | 1 | 0/110 detrás |
| `C:\GitHub\_archive\umbral-bot-2` | `main` | `0670595` 2026-07-02 | **2073** | 0/4 |
| `C:\Users\david\source\konstruedu-flow-lab` | `main` | `264e2af` 2026-11-06 | 0 | 0/0 |
| `C:\Users\david\source\kn5nov-wt\*` (9 worktrees) | `claude/kn-5nov-*`, `claude/kn-retro-*` | 2026-10-27…11-06 | 0–1 | mayoría sin upstream |

Resto: ~45 worktrees `C:\GitHub\_worktrees\skills-*` (ramas `codex/*`, limpios). Worktrees de `umbral-agent-stack`: principal [rick/motor-piezas-lab] + 6 en `_worktrees/` (`uas-arco-strategy-parens` sucio 3 y 0/20, `uas-editorial-v1-arco`, `uas-editorial-v1-cadena` sucio 2, `uas-pcrick-agy-receipts`, `uas-pcrick-execution-adapter`, `uas-pcrick-interactive-package`). `umbral-agent-stack-claude` sin worktrees adicionales.

## 9. Unidades y sincronizaciones

- Unidades: C: (1658 GB usados / 204 libres), D: «M.2», E:, **G: «Google Drive»** (732/200 GB), J:, L:.
- `G:\Mi unidad\01_Entrada` y `02_Operacion` existen. `C:\Users\david\Umbral BIM` (SharePoint sync): `Master AEC 4.0 - Documentos`, `Master AEC 4.0 V2 - Documentos`, `USM - Aula I+D - Documentos`. `OneDrive - Umbral BIM` existe.
- `02_Operacion` (2 niveles): `_local-secrets` · `_Plantilla-Programa` {00_Gobierno del Programa, 01_Clases y Sesiones, 02_Contenido Docente, 03_Difusion Activa, 04_Compartido, 05_Referencias y Complementos} · `Clientes y Partners` {Adarcus, Arquitectura Carola y David, Berrilan, BIM Forum, Boragó, Butic, Cecilia Sepulveda, Congrap, Dessau Peru, Enjofrabim, Iglú, Konstruedu, Mario Morales, N8N, Netzun, OXXO, Shimin, Speckle, TEDI, Universidad Continental, USM, WSP} · `Entidades Propias` {Umbral Arquitectura, Umbral BIM} · `Oportunidades sin Cuenta Anclada` {Corfo - CDPR Metropolitano 2025} · `Proyectos y Asesorias` {_Plantilla-Cliente, Diego Santiago - Levantamiento HEAD, Happy Days - Habilitacion Local, Karrito Market - Miguel Claro, Lita - App Web}.
- Sync: `GoogleDriveFS` y `OneDrive.Sync.Service` activos.

## 10. Worker UAS local

- Proceso pid 19900 → `umbral-agent-stack-codex\scripts\vm\start_primary_worker.py`, desde 2026-10-30 16:52Z (tarea `UmbralWorkerPrimary` al logon).
- `GET http://127.0.0.1:8088/health` → **HTTP 200**, `ok=true`, **version 0.4.0**, **114 tareas registradas** (notion 15, windows 12, linear 11, granola 9, gui 7, editorial 6, client 6, browser 6, figma 5, n8n 5, github 4, google 4, rag 4, document 3, gmail 2, google_drive 2, system 2, web 2, y 1 de rick, research, llm, make, magnific, copilot_cli, composite, ping, azure).
- Exposición: escucha en **0.0.0.0** con firewall Allow en 8088 (perfil Any). 8089 no escucha.

## 11. OpenClaw en TARRO

- `~\.openclaw` **no existe**. CLI `openclaw` **no instalado**. No hay nodo OpenClaw en el host Windows; sí la **VM Hyper-V «OpenClaw»** (= PCRick) con consola `vmconnect` abierta desde 11-07 00:39Z.
- `~\.config\openclaw\env.rick-oauth.pending` (835 B, 2026-06-01): variables GCLOUD_LOCATION, GOOGLE_CALENDAR_CLIENT_ID/SECRET/REFRESH_TOKEN, GOOGLE_CLOUD_LOCATION, GOOGLE_GMAIL_CLIENT_ID/SECRET/REFRESH_TOKEN (valores no leídos). Encabezado: OAuth de Rick para pegar en la VPS.
- `C:\Users\david\openclaw`: **archivo** de 464 B con clave privada OpenSSH (2026-02-25).

## 12. Archivos `.env` (solo nombres de variables)

| Ruta | Mod. (UTC) | Variables |
|---|---|---|
| `umbral-agent-stack\.env` | 2026-03-24 | FIGMA_API_KEY, GITHUB_TOKEN, GOOGLE_API_KEY, GOOGLE_API_KEY_NANO, GOOGLE_API_KEY_RICK_UMBRAL, GOOGLE_CALENDAR_*, GOOGLE_CLOUD_PROJECT_RICK_UMBRAL, GOOGLE_CSE_*, GOOGLE_GMAIL_*, HOSTINGER_API_TOKEN, KIMI_AZURE_API_KEY, LINEAR_API_KEY, NOTION_API_KEY, NOTION_CONTROL_ROOM_PAGE_ID, NOTION_DASHBOARD_PAGE_ID, NOTION_TASKS_DB_ID, TAVILY_API_KEY, WORKER_TOKEN, WORKER_URL, WORKER_URL_VM, WORKER_URL_VM_INTERACTIVE |
| `umbral-agent-stack\.env.example` | 2026-11-06 | plantilla de 326 líneas (ANTHROPIC_API_KEY, AZURE_*, LANGFUSE_*, OPENCLAW_GATEWAY_TOKEN, RICK_*, …) |
| `umbral-agent-stack-claude\.env` | **No existe** | — |
| `umbral-agent-stack-codex\.env` (clon del worker activo) | 2026-08-24 | NOTION_* (15 ids/keys), WORKER_TOKEN, WORKER_URL, WORKER_URL_VM, WORKER_URL_VM_INTERACTIVE |

## 13. Logs de ops locales

- `~\.config\umbral\ops_log.jsonl`: 4,1 MB, 17.465 líneas, **última modificación 2026-11-06 12:30Z** (`task_completed`). Últimas 200 líneas: 2026-09-04 → 2026-11-06; task_completed 122, llm_usage 67, task_failed 10, task_queued 1.
- Observación: el log no registra nada desde el 6-nov aunque el worker sigue vivo (sin tareas, o escribe a otro log; no verificado).

## No pude verificar

1. Nodos y estado de la tailnet (servicio Tailscale detenido; no se arrancó).
2. VM Hyper-V «OpenClaw»: `Get-VM` requiere elevación.
3. Si los 300+ procesos node/python MCP están vivos o huérfanos.
4. Endpoints autenticados del worker (sin token, por diseño).
5. Ahead/behind de repos sin upstream o en HEAD desprendido.
6. Causas de los errores 0x1 (GranolaVmRawIntake ×2) y 0x2 (OpsResumeWriter).
7. Destino de los puertos 8765/8781/8783 (python) y 8782 (node).

**Hallazgos a atender (señalados, no actuados):** clave privada OpenSSH suelta en `C:\Users\david\openclaw`; worker 8088 escuchando en 0.0.0.0 con firewall Allow mientras Tailscale está apagado; clon `-claude` 16 commits detrás y `-codex` 15 detrás con 49 archivos sucios siendo el clon desde el que corre el worker.
