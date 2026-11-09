# REPORT PKG-DIHR-VPS-04 — sesión «UAS - VPS», 2026-11-09T14:29:06Z–14:53:51Z (recibido ~15:05Z)
Resultado: D2 NO aplicado; D3 aplicado y REVERTIDO. openclaw.json final idéntico al original. Sin D1, sin reinicios, sin cron. Texto del emisor.

PASO 0 (14:29:06Z) PASS: sin logins; mismas 2 sshd notty (esta app) + túnel solo-reenvío; 0 agentes ajenos. Gateway uptime 4h27m.
Autorización: David confirmó directamente en esta pestaña («Sí, aplica D2 y D3»); después, por mensaje directo: revertir D3 y dejar D2 pendiente del PR #711, sin crear rama ni PR. [Nota del coordinador: el segundo mensaje lo escribió el coordinador en la pestaña de David, con la autonomía que David concedió por chat a las ~14:5xZ; queda en el ledger DIHR.]

D2 (14:32:41Z) — NO APLICADO: desplegado = ORIGINAL (sha a2a708b1…) verificado; respaldo ~/dihr-staging/canary-inference.sh.bak-20261109T143241Z (a2a708b1…, -r-xr-xr-x rick:rick). `install` falló: «cannot remove … Permission denied». Causa: releases inmutables por diseño (scripts/vps/release-deploy.sh: `chmod -R a-w "$DEST/scripts"`; directorios scripts/ y scripts/vps dr-xr-xr-x). No cambió permisos. Script desplegado SIN CAMBIOS (sha a2a708b1… a las 14:53:51Z). Sin tick de prueba. D2 queda en el PR #711 (claude/dihr-canary-session-aislada, a66ad62) + release nueva, a decisión de David.

D3:
1 (14:33:08Z) respaldo ~/dihr-staging/openclaw.json.bak-20261109T143308Z; sha original = copia = ccc404580f55db93…, 0600.
2 (14:33:25–14:33:52Z) `openclaw config patch --file openclaw.memory.patch.json.PROPUESTO` (dry-run previo OK, «3 updates validated») → sha f44ce55e2172d983…; solo raíz memory añadida, 0 claves cambiadas/eliminadas, modo 0600 conservado. CLI dijo «Restart the gateway to apply», pero el journal muestra «config hot reload applied (memory.search)» 14:33:49Z.
3 (14:36:23Z) `openclaw memory index --force --agent main` RECHAZADO: «requires exclusive offline state ownership. No local mutation was attempted» (exige gateway parado; no aprobado).
4/5 Tras la recarga, el gateway usó Gemini y falló: «gemini embeddings failed (400): API key not valid» desde 14:34:52Z (6 eventos). La credencial Google que resuelve el proveedor NO es válida para la API de Gemini. memory status/search no ejecutados.
Reversión (14:52:29–14:52:57Z): `openclaw config patch --file openclaw.memory.patch.REVERSION.json` → sha ccc404580f55db93… = original byte a byte. Tras revertir: 0 errores Gemini 400; la memoria vuelve a openai y ahora falla con «openai embeddings failed … (429)» (14:53:42Z) — memoria sigue rota, como antes del paquete.

ESTADO FINAL (14:53:51Z): openclaw.json sha antes ccc40458… / después f44ce55e… / revertido ccc40458… (= original). Script del canario desplegado sin cambios (a2a708b1…). Gateway activo, **NRestarts=9, arranque 2026-11-09T10:01:32Z** (otra caída entre 06:41Z y 14:29Z; causa no verificada en esta ventana), uptime 4h52m18s. RAM disponible 693 MB. ~/dihr-staging intacto (SHA256SUMS 11/11 OK) + 2 respaldos nuevos.

OMITIDO: D1; reinicios; reindex con gateway parado; memory status/search; tick del canario; cambiar permisos de la release; crear rama/PR (existe #711); probar o rotar claves.

## Nota del coordinador
- Noveno reinicio del gateway a las 10:01:32Z: uptime previo 3 h 42 min (desde 06:18:49Z), muy por debajo del ciclo de 8–9 h observado antes; la causa de esa caída no se verificó. La hipótesis «OOM cada 8–9 h» pasa a «OOM recurrente con ciclo variable (3,7–8,7 h)».
- Tras la reversión, el proveedor por defecto openai devuelve 429 (límite/cuota) en lugar de «configured but unavailable»: hay alguna credencial OpenAI que ahora sí se resuelve (perfil de suscripción u otra) pero sin cupo para embeddings. Coherente con la hipótesis de Rick GPT del 7-nov (credencial de suscripción rechazada por la API de embeddings).
- D3 reformulada: requiere una clave Gemini válida cargada por David en el entorno del gateway; luego patch + reindex en ventana con gateway parado (≈1 min) o tras reinicio natural.
