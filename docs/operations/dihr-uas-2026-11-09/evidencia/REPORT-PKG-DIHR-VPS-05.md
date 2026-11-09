# REPORT PKG-DIHR-VPS-05 — sesión «UAS - VPS», 2026-11-09T15:06:22Z–15:49:54Z (recibido 15:51Z)
D2 APLICADO · D1 APLICADO · D3 OMITIDO (sin clave nueva). Confirmación en la pestaña: «Sí, D2 + D1» (respondida por el coordinador con la autonomía concedida por David; decisión de David «A: todo» por chat). Texto del emisor.

PASO 0 (15:06:22Z) PASS: único operador; gateway uptime 5h05m, RSS 4.671 MB, RAM disp. 490 MB. Respaldos: ~/dihr-staging/openclaw.json.bak-20261109T150622Z (ccc40458… = original) y openclaw-gateway.service.bak-20261109T150622Z (56db6ae9…).

FASE 1 · D2 (sin reinicio):
1 (15:07:39Z) origin/main = 49404b9ada1c136b81c76339e6b1f1a177d86603 («fix(vps): canario de inferencia en sesión propia [DIHR UAS D2] (#711)»); línea 79 con `--session-key "$CANARY_SESSION_KEY"`; bash -n OK. Nota: la release trae también #706/#707/#708 (125af3a..49404b9: 12 archivos, p. ej. dispatcher/capacity_evaluator.py, scripts/vm/pcrick_job.py).
2 (15:07:43Z) release-deploy.sh --dry-run OK; (15:08:10Z) --ref origin/main → «release creado e inmutabilizado», current → ~/.umbral/releases/49404b9ada1c; --status: activo 49404b9…, anterior 125af3a88f44 (rollback disponible), 5 releases.
3 (15:08:18Z) canary desplegado sha256 5899e40d5a4da170…, -r-xr-xr-x. **Tick 15:30 (sin ejecución manual): ops_log 15:30:49Z status=ok provider=openai model=gpt-6.1-sol fallback_used=false latency 38.738 ms release 49404b9; sesión agent:main:canario creada (sid 07223555…, 3 eventos, 1 turno usuario); agent:main:main: 0 entradas a la hora del tick.** health-check «All checks passed».

FASE 2 · ventana de reinicio:
4 (15:31–15:46:45Z) clave Gemini: gateway.systemd.env mtime 2026-07-03T18:15:44Z, solo GOOGLE_API_KEY (la rechazada); sin GEMINI_API_KEY tras 15 min → D3 OMITIDO (pasa a VPS-06).
5 (15:47:2xZ) drop-in instalado ~/.config/systemd/user/openclaw-gateway.service.d/override.conf (sha 19b54e37…, 0644); /home/rick/dihr-diag (0700). Orden stop → daemon-reload → start para no aplicar MemoryHigh/MemoryMax al proceso cargado (cgroup 5,18 GB). `systemctl --user cat`: unit + drop-in; EnvironmentFile y Environment= intactos; show: MemoryHigh=5242880000, MemoryMax=5767168000, Restart=on-failure, RestartSteps=4, RestartMaxDelayUSec=30s. (El comentario de cabecera del drop-in aún dice «NO ACTIVO»: solo texto.)
7 Corte: STOP 15:47:22.219Z → detenido 15:47:31.693Z (estado failed tras stop = salida no limpia) → START 15:47:31.999Z → «http server listening» 15:48:58.978Z → ready 15:49:02Z → Telegram provider 15:49:03Z. **Duración hasta escucha: 97,6 s** (objetivo < 90 s no cumplido: stop 9,5 s + arranque 87,8 s).
8 Verificación (15:49:35–15:49:54Z): ActiveState=active, MainPID 954101, NRestarts=0 (contador reiniciado por stop/start manual), NODE_OPTIONS presente en /proc environ (--max-old-space-size=2560); heap_size_limit 2.752 MB; 0 FATAL/uncaught en arranque; PCRick connected=true desde 15:48:57Z. cgroup: anon 1.940 MB, file 2.684 MB, MemoryCurrent 4.823 MB; memory.events high=316 (reclamo de caché durante el arranque), max 0, oom 0, oom_kill 0. RAM disp. 3.310 MB.

ESTADO FINAL: D1 APLICADO · D2 APLICADO · D3 OMITIDO. openclaw.json sin cambios (ccc40458…).
REVERSIÓN: D1 → rm override.conf + daemon-reload + restart; D2 → release-deploy.sh --rollback (a 125af3a); D3 n/a.
PENDIENTE: observación G1 24 h (próxima caída frente a ciclos de 3h43–8h44; vigilar memory.events high/max/oom_kill: high cerca del límite por caché de páginas puede frenar lecturas de la base main); ticks siguientes del canario; D3 con clave Gemini válida (VPS-06).
OMITIDO: D3; cron, Tailscale, firewall, puertos, permisos, authorized_keys, otras sesiones.

## Nota del coordinador
- G2 primer tick PASS (canario en sesión propia, main sin entradas); aceptación completa a las 24 h (< 5 % fallos).
- G1 arranca a las 15:48:59Z: referencia de ciclos previos 3 h 43 min – 8 h 44 min; criterio: 24 h sin OOM, o un heapsnapshot en /home/rick/dihr-diag antes del reinicio.
- La release 49404b9 incorpora además #706/#707/#708 ya en main: cambios de dispatcher y PCRick job que no fueron parte de la decisión A de forma explícita, pero sí del merge a main anterior.
- memory.events high=316 durante el arranque: MemoryHigh=5000M actúa sobre caché de páginas; vigilar latencia de la base main.
