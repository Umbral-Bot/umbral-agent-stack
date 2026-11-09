# REPORT PKG-DIHR-PCRICK-03 — sesión «PCRick node pairing identity repair», 2026-11-09 06:35–06:40Z (recibido ~07:50Z)
Escribió solo en ~\dihr-staging\. Texto del emisor; redacción del coordinador: ninguna (no contiene secretos).

1 · Permisos (D9) — PASS (lectura y respaldo)
- Claude, ~\.claude\settings.json (168 B, 2026-11-03T17:41:37Z): permissions.defaultMode=bypassPermissions; sin allow/deny/ask.
- Codex, ~\.codex\config.toml (3.822 B, modificado **2026-11-09T03:52:37Z**, hoy): approval_policy="never", sandbox_mode="danger-full-access", model="gpt-5.6-sol". 6 proyectos de confianza (codex 2026-09-11 contexto VM; tanda2 cli-probes live-01; pcrick-execution t2-rg-codex-01; pcrick-jobs t2-fix-validation-codex-01 y t2-ide-codex-04; documents\c23-alumno-20260917). No atribuye el cambio de hoy.
- Antigravity (state.vscdb, solo lectura): terminalAutoExecutionPolicy=Always Proceed, artifactReviewPolicy=Always Proceed, secureMode=desactivado. c23-permissions-note.json 345 B, 2026-09-17T12:21:38Z.
- Respaldos en ~\dihr-staging\permisos-bak-20261109T063631Z\ con SHA256SUMS.txt: claude-settings.json 7876A66E…3D8B75; codex-config.toml FF276870…F12B6E; antigravity-c23-permissions-note.json 2994B2D7…198634. No copió state.vscdb (contiene antigravityUnifiedStateSync.oauthToken).
- C:\Github\umbral-agent-stack\.claude\settings.local.json (versionado, modificado 2026-11-09T03:59:12Z): +2 reglas en permissions.allow del servidor MCP e183d34d… (conector Google Drive). Atribución por inferencia: única sesión local activa en ese repo entre 03:55 y 04:02Z fue «Juez ciego de regresión — paquete R1». No demostrado.

2 · Exposición (D7) — inventario; hay riesgo
- 22: sshd (pid 4328) en 0.0.0.0 y [::]. Reglas: «OpenSSH SSH Server (sshd)» (Private), «OpenSSH Server» (Any), «OpenSSH-22» (Any); remoto Any.
- 8088: python worker (pid 6920) en 0.0.0.0. Reglas: «OpenClaw Worker 8088» y «OpenClaw-Worker-8088» (Any/Any) + regla por programa python.exe (Private y Public, cualquier puerto).
- 445/139: System. 445 en [::]; 139 en IPs LAN y Tailscale. Sin regla de permiso habilitada encontrada; efecto depende de la política por defecto: NO PROBADO.
- 18789 (gateway local) y 18790 (túnel): solo loopback. Regla «Node.js JavaScript Runtime» node.exe perfil Public cualquier puerto.
- Interfaces: Ethernet 192.168.42.152/20 (Public), Ethernet 2 192.168.41.104/20 (Public), Tailscale 100.109.16.40/32 (Private).

3 · Worker — PASS (lectura)
- Host de escucha fijado en código: run_openclaw_worker_service.ps1 línea 13, `--host 0.0.0.0 --port 8088`. Script en C:\GitHub\umbral-agent-stack-runtime-main\scripts\vm\ (sin seguimiento en git); NSSM lo lanza.
- Variables (nombres) en C:\openclaw-worker\openclaw-worker-service.env (451 B, 2026-03-22): WORKER_TOKEN, PYTHONPATH, LINEAR_API_KEY, NOTION_API_KEY, NOTION_CONTROL_ROOM_PAGE_ID, NOTION_GRANOLA_DB_ID, NOTION_TASKS_DB_ID, BROWSER_HEADLESS.
- **Riesgo:** ese .env lo puede leer el grupo Usuarios y modificar «Authenticated Users».

4 · Tailscale — PASS en PCRick; FAIL en VPS y TARRO
- PCRick en línea, v1.104.5, clave válida hasta 2027-03-12. srv1431451 (VPS): offline, visto 2026-08-25T19:31Z, KeyExpiry 2026-08-25T18:30:50Z Expired. TARRO: offline, visto 2026-03-24, KeyExpiry 2026-08-31T04:37:03Z Expired. cursor: offline desde 2026-09-21, clave hasta 2027-03-12. netcheck: UDP sí, IPv4 sí, IPv6 no, DERP São Paulo 66,4 ms.

5 · Nodo y túnel — PASS, con **nueva caída del gateway de la VPS**
- Nodo único (13176); socket 54371 (a las 05:36Z era 50784): reconexión. Túnel ssh pid 5692 desde 07-nov 08:30:58Z, 0 reinicios.
- stderr del túnel: última escritura 2026-11-09T06:19:15Z con «connect failed: Connection refused» ×5. Log del nodo: ERROR 06:21:11Z «gateway connect failed: gateway closed (1000)»; luego reconectó.
- Inferencia: el gateway de la VPS cayó/reinició hacia 06:19–06:21Z.

6 · Skills — PASS: tarea Umbral-SkillsReceiver-pcrick-windows Ready; última 06:21:58Z 0x0; último recibo PASS ACTIVATED deploy full commit 7635a45b…, 06:22:27Z; native_usage_verified=false; 2.576 recibos.

7 · Grok Bot — PASS: v0.78.1 instalado; datos últimos 2026-11-02T22:09Z; sin tarea, servicio, Run ni Startup que lo arranque; no corre. Credencial no abierta.

Omitido: copiar state.vscdb; valores de settings.local.json, .env y credencial Grok; cambios de firewall/ACL/puertos/permisos; VPS, AUT-2, crons, /run. Sin cambios de configuración ni servicios.

## Nota del coordinador
- Octava caída del gateway VPS inferida a las ~06:19–06:21Z del 09-nov desde PCRick (previa 21:34:20Z del 08-nov): 8 h 45–47 min. Pendiente confirmar hora exacta y motivo OOM en VPS-03 A1.
- Nuevo riesgo D7: ACL del archivo de entorno del Worker PCRick (modificable por Authenticated Users). Nuevo dato D9: Codex config.toml modificado hoy 03:52Z sin atribución.
