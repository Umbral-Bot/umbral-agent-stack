# REPORT PKG-DIHR-PCRICK-01 — sesión «PCRick node pairing identity repair» (Remote Control, bypass; equipo PCRick)
Recibido por cross-session-message en «Control remoto de hilos Claude Code», 2026-11-09 ~05:47Z. Ventana declarada 2026-11-09 05:36–05:39Z. Texto del emisor; no verificado por el coordinador salvo donde se indique.

1 · Estado frente a la tabla de 08-11 12:30Z
- Nodo canónico único: PASS. Un solo `node run` (PID 13176, lanzado por la tarea); `openclaw node status` → pid 13176; el .vbs de Startup sigue ausente. [05:36:05Z · Win32_Process + CLI]
- Socket del nodo: PASS. Uno solo, 50784/pid13176. El puerto cambió desde 50474: hubo una reconexión. El stderr del túnel registra «connect failed: Connection refused» ×10, el último a las 21:34:53Z del 08-11. Inferencia: el gateway de la VPS no estaba disponible.
- Túnel SSH: PASS. PID 5692, iniciado el 07-11 a las 08:30:58Z; 0 reinicios desde las 12:30Z.
- Gateway local: PASS en salud. GET /healthz 200 live; GET /readyz 200 ready, 0 fallos, sin degradación. Que esté vivo es justamente el riesgo abierto.
- Worker: PASS en salud local. GET /health 200, v0.4.0, 80 tareas, 0 en memoria, 0 peticiones externas.
- Errores nuevos: PASS. 0 ERROR; 9 WARN de lentitud de session-sqlite entre 13:30Z y 01:31Z.

2 · Tareas programadas: PASS (inventario)
- En marcha: OpenClaw Node (inicio 07-11 08:31Z).
- Ready: Umbral-SkillsReceiver-pcrick-windows (última 05:21:58Z, 0x0; próxima 05:51:57Z), GranolaWatcher (última 07-11, 0x0), StartInteractiveWorker* (últimas 23-03 y 05-04).
- Disabled: OpenClaw Gateway, OpenClaw-TelegramAudioAgent, Rick-Granola-Sync-Daily, Rick-Multiagent-Progress-30min, Umbral-PCRick-5e118d…, Umbral-T2-* ×9.
- No hay tareas de Dispatcher ni de Grok. [Get-ScheduledTask]

3 · Conectividad
- Tailscale de PCRick en línea (100.109.16.40, pcrick.<tailnet>.ts.net).
- VPS <host VPS>: FAIL. Offline, visto por última vez el 25-08 a las 19:31Z; KeyExpiry 2026-08-25T18:30:50Z, Expired=True. Es la causa probable del corte de la ruta del worker.
- TARRO: FAIL. Offline; KeyExpiry 2026-08-31, Expired=True; `tailscale ping` → «peer's node key has expired».
- cursor: offline (visto el 21-09); su clave vale hasta el 2027-03-12.
- Notebook MSI: NO PROBADO, no está en la tailnet.
- Alias SSH: ninguno (solo los hosts de Azure en el ssh_config de Git).
- Puertos en escucha: sshd 0.0.0.0:22; worker 0.0.0.0:8088; gateway local 127.0.0.1:18789; túnel 127.0.0.1:18790; tailscaled 100.109.16.40:443; SMB 445/139; TeamViewer 127.0.0.1:5939.
- Rutas: a la VPS pública por Ethernet (gw 192.168.x.x), con sesión 192.168.x.x:49693→<IP pública VPS>:22 Established. Hacia los 100.x de la VPS y de TARRO no hay ruta Tailscale; caen en la ruta por defecto.

4 · Herramientas: PASS (existencia y versión)
- claude 2.1.273; codex-cli 0.154.0; node v24.22.2; python 3.13.10 en el PATH; 3.11.9 con uvicorn 0.41.0 para el worker; git 2.53.0; openclaw 2026.10.10 (7dc3350).
- gh: no instalado.
- Grok Bot 0.78.1: instalado, sin proceso ni arranque automático; datos en %APPDATA%\Grok Bot y ~\.grokbot, último cambio 02-11 22:09Z. Hay un archivo de credencial; no lo abrí.
- Servicios persistentes: CodexSandbox, CoworkVM, openclaw-node-tunnel, openclaw-worker, RustDesk, sshd, Tailscale, TeamViewer.

5 · Repos: FAIL por desfase
- C:\Github\umbral-agent-stack: main@46aa07c (30-05), 370 detrás de origin/main 97f2d87 (referencia local; último fetch el 01-06). Hoy aparece ` M .claude/settings.local.json`, modificado el 09-11 a las 03:59:12Z; no fue este hilo y no lo abrí. 1 stash, rama backup-local-main-20260601.
- C:\GitHub\umbral-agent-stack-runtime-main: main@a480a0a (23-03), 1.678 commits detrás de 97f2d87; 2 archivos modificados y 1 sin seguimiento (el script del servicio del worker).

6 · AUT-1 y AUT-2 (según AUT1-ROLLBACK.md, PROPUESTA-RECUPERACION y aut1-run.txt)
- AUT-1: PASS en local. Cuarentena de Startup\OpenClaw Node.vbs (sha 799B8B2C…) y parada del PID 20356, ejecutadas el 08-11 a las 01:49:33Z. Aceptación inmediata y 10/10 muestras correctas; sigue vigente a las 05:36Z.
  - Pendiente: confirmación desde la VPS y prueba tras el próximo inicio de sesión (no hubo reinicio desde el 07-11 08:30Z).
- AUT-2: NO EJECUTADO. El control se detuvo el 08-11 a las 01:08:53Z porque hay auxiliares (17564 y 8512) fuera del alcance, y la ampliación no está autorizada.
  - El gateway sigue activo. El cron Memory Dreaming está habilitado, con próxima ejecución el 2026-11-09 a las 06:00:00Z. La anterior fue el 08-11 a las 06:00Z: ok, 0 candidatos, 0 aplicados.

7 · Clase 23 (Máster AEC 4.0): rutas listadas; el PASS_PARTIAL queda NO PROBADO
- ~\Documents\C23-alumno-20260917: 88 archivos, 1.222.345 B, último cambio 17-09 15:44Z. Subcarpetas: ejercicio (13), salidas (22), _evidence (43).
- Probables portadores del veredicto, sin abrir: _evidence\resultados-referencia-status.txt (82 B, 17-09 14:52Z) y _evidence\IDE-MCP-report.md (5.283 B).
- Insumos: ~\.umbral\pcrick-execution\packages\c23-inputs-20260915 (21 archivos, 108.810 B, 15-09).
- Relacionadas pero distintas: C25-alumno-20260924, PKG-AEC-PLANB-C24-TESTER-ALUMNO-01, pcrick-jobs\c25-dalux-claude-01.

8 · Respaldos
- ~\.openclaw: openclaw.json.last-good (07-11 08:36Z) y .bak/.bak.1–.4; backup-pre-state-migration-20261103 (7 archivos) y backup-pre-2026.10.10-20261103 (10); openclaw.sqlite.pre-startup-migration.bak (1,6 MB, 04-11); .bak de los lanzadores (04-11).
- Copias de evidencia en ~\.coord-ag-evidence (04-11, 07-11 y 08-11).
- Git: rama de respaldo y 1 stash.
- File History detenido y sin configurar. OneDrive y Google Drive sincronizan, pero no son respaldo, y ~\Documents (con C23) no está redirigido a OneDrive.
- Puntos de restauración, VSS y checkpoints de Hyper-V: NO PROBADO (requieren administrador o el host).

Omitido por implicar cambios, costo o aprobación: ping o pruebas a la VPS (prohibido por el coordinador el 08-11); ping al MSI (no está en la tailnet); abrir el archivo de estado de C23, .claude/settings.local.json o la credencial de Grok; vssadmin y puntos de restauración (administrador); git fetch; CLI de memoria (podría llamar a un proveedor).

No cambié nada. La evidencia es esta respuesta. Reutilicé un script de lectura que ya estaba en el scratchpad; no creé archivos.

## Cruce del coordinador (2026-11-09 ~05:50Z)
- VPS reporta tailscale BackendState=NeedsLogin con 0 peers; PCRick reporta que la clave del nodo VPS caducó el 2026-08-25 y la de TARRO el 2026-08-31. Ambas lecturas son coherentes: la tailnet está caída por caducidad de claves, no por un fallo transitorio. Reparar requiere re-login Tailscale en VPS y TARRO (cambio de VPN: aprobación de David).
- VPS reporta 7 reinicios del gateway (NRestarts=7) y explica el rechazo de las 04:44:49Z del 08-11 por arranque tras OOM; la línea «Connection refused» no está en los logs del VPS. PCRick registra 10 «Connection refused» en el stderr del túnel, el último a las 21:34:53Z del 08-11, que coincide con la caída OOM de las 21:34:20Z. Que los 10 rechazos correspondan a reinicios OOM es hipótesis (10 eventos frente a 7 reinicios; una coincidencia horaria verificada).
