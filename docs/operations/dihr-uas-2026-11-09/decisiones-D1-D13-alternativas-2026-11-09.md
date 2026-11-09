# DIHR UAS · Decisiones D1–D13: clasificación, propuesta, alternativas y consecuencias

Corte 2026-11-09 06:40 UTC (horas por el reloj del ledger DIHR). Complementa A.2 del documento integral. Para cada decisión: qué puede hacer el coordinador con las autorizaciones vigentes (y si ya lo hizo), qué requiere a David, la propuesta, las alternativas con consecuencias, y el criterio de aceptación (G). Nada operativo se aplicó.

## Clasificación

| # | Decisión | Ejecutable ahora (hecho / en curso) | Requiere a David |
|---|---|---|---|
| D1 | Gateway OpenClaw: memoria y reinicios | Verificar causa (VPS-03 A1: unit, drop-ins, serie RSS, tamaño de sesión); preparar drop-in en staging (B1) | Aplicar paso 1 (compactar/abrir sesión `main`: toca tu conversación con Rick) y paso 2 (drop-in + reinicio de 1 min) |
| D2 | Canario fuera de la sesión principal | Rama con parche preparada (sin commit/PR); confirmar flag real (VPS-03 B2) | Aprobar PR y cambio del cron en el VPS |
| D3 | Embeddings = Gemini | Verificar clave de config y variables presentes (VPS-03 A3); preparar diff (B3) | Aplicar edición de `openclaw.json` y reindex (llama a la API de Gemini) |
| D4 | Tailscale VPS y TARRO | Preparado el punto exacto de login (abajo) | Tu login interactivo en ambos equipos; habilitar servicio en TARRO |
| D5 | Solicitud 7ae25185 PCRick | Nada que ejecutar | Decidir (recomendación: mantener pendiente) |
| D6 | Comparativa Rick GPT / Grok | Nada que ejecutar (coordinación reservada a Slack #uas) | Cuatro decisiones (a–d) |
| D7 | Secretos, claves, puertos | Huellas de claves y reglas de firewall leídas (TARRO; VPS-03 A4; PCRick-03) | Rotación, retirada de clave suelta, cierre de puertos, limpieza Drive |
| D8 | Commit/PR del entregable | Identificadores redactados; contenido y destino listos para tu revisión | Confirmar destino y autorizar commit/PR |
| D9 | Permisos en PCRick | Lectura y copias de respaldo (PCRick-03) | Cambiar modos por defecto |
| D10 | Cadencia del poller Notion | Medición hecha (≈10 req/min) | Cambiar intervalo (optimización, no urgente) |
| D11 | Inventario del notebook MSI por el puente Drive | Paquete redactado; Rick GPT lo publica | Autorizar a Rick GPT a publicar PKG-DIHR-MSI-01 y a compartir el informe saneado con Claude Code |

## D1 · Gateway OpenClaw (VPS)

**Evidencia:** heap por defecto 2.240 MB sin `NODE_OPTIONS` (VPS-01 ítem 1); OOM V8 registrados 7-nov 03:24, 11:50, 20:41 y 8-nov 04:44, 13:01, 21:34 UTC; RSS 4,4 GB con RAM disponible 997→618 MB en 15 min; swap 0. **Correlación, no causa:** el ciclo de 8–9 h es inferencia sobre 6 eventos; la fuga podría estar en transcripts de sesión (issues upstream #58802/#51097), en memoria externa al heap, o en el propio canario cada 30 min. VPS-03 A1 mide la pendiente de RSS y el tamaño de la sesión `main` para discriminar.

**Verificación VPS-03 (06:35Z):** octavo OOM a las 06:18:42Z tras 8 h 44 min (NRestarts=8); unit sin drop-ins ni `NODE_OPTIONS`; RSS arranca en ≈2,4 GB y llega a 4,4 GB a las 8 h (≈ +4 MB/min, inferencia); la sesión `main` acumula 10.264 eventos y la base 1,36 GB; otras sesiones grandes: rick-tracker (10.100 eventos) y rick-ops (9.895).

**Propuesta (dos pasos):** paso 1, sacar el canario (D2) y abrir sesión nueva de `main` conservando la anterior; medir 24 h. Paso 2 solo si persiste: aplicar el drop-in ya preparado y dimensionado por la propia sesión VPS con la RAM real (`~/dihr-staging/openclaw-gateway.service.d-override.conf.PROPUESTO`, sha256 19b54e37…): `NODE_OPTIONS=--max-old-space-size=2560 --heapsnapshot-near-heap-limit=1 --diagnostic-dir=/home/rick/dihr-diag`, `MemoryHigh=5000M`, `MemoryMax=5500M`, `Restart=on-failure`, `RestartSec=5`, `RestartSteps=4`, `RestartMaxDelaySec=30`; reinicio controlado de 1 min. Cálculo del VPS: RAM 7.940 MB sin swap; el resto de servicios usa ≈2.690 MB en picos (n8n 1.102, sesiones Claude ≈819, núcleo ≈350, worker 224…), quedan ≈5.250 MB; el gateway al final de ciclo con heap 2.560 ≈ 5,0 GB. Riesgo anotado por el VPS: el snapshot cerca del límite puede exigir ≈2,5 GB extra y chocar con `MemoryMax`; alternativa `--heapsnapshot-signal=SIGUSR2` disparado a las ~3 h de uptime. README con secuencia y reversión en el mismo directorio.

| Alternativa | Consecuencia | Cuándo preferirla |
|---|---|---|
| A. Dos pasos (propuesta) | Primero elimina las dos cargas periódicas conocidas sin tocar memoria; el drop-in aporta snapshot para encontrar la fuga | Siempre que se acepte medir 24 h |
| B. Drop-in directo con heap 3 GB | Riesgo: 3 GB heap + 2–3 GB externos supera `MemoryMax` antes del snapshot; la RAM libre (< 1 GB) no alcanza para escribir el snapshot | Solo si se amplía la RAM del VPS |
| C. Reinicio programado cada 6 h (timer) | Convierte el corte en planificado; no da evidencia ni corrige | Como red de seguridad mientras se decide A |
| D. Ampliar el VPS (más RAM) | Coste mensual nuevo; no corrige la fuga | Si A+B no bastan tras medir |
| E. No hacer nada | Rick seguirá cayendo cada 8–9 h con 1 min de corte y reconexión del nodo | — |

**Aceptación:** G1 y G1b. **Reversión:** borrar el drop-in y reiniciar (2 min); la sesión anterior de `main` se conserva.

**Estado (15:51Z):** paso 2 APLICADO por decisión A de David (≤15:04Z) **antes que el paso 1** (sesión main no compactada): la prueba G1b deja de servir para discriminar si la fuga está en el transcript; se observa G1 directamente (PKG-DIHR-VPS-05): drop-in instalado, `stop → daemon-reload → start`, corte 97,6 s, NODE_OPTIONS activo (heap 2.752 MB), MemoryHigh/Max 5000M/5500M, memory.events high=316 durante el arranque (reclamo de caché), oom 0. Paso 1 (sesión `main` nueva) no se ejecutó. G1: 24 h desde 15:48:59Z.

## D2 · Canario en sesión propia

**Evidencia:** `canary-inference.sh` (origin/main) ejecuta `openclaw agent --agent main -m … --json` sin clave de sesión; 34 fallos de 48 en 24 h con mediana 180,2 s; 22 `chat.abort` a :03/:33 y 52 entradas pendientes en el historial de David (reportado por la sesión VPS a las 00:51Z; VPS-03 A2 contrasta minuto a minuto).

**Verificación VPS-03 (06:35Z):** 25 de 25 abortos de la sesión `main` en 24 h coinciden en ≤ 60 s con un fallo del canario (35 fallos: 27 timeouts de 180 s, 6 «CLI command failed», 1 lentitud, 1 «Lost the connection» = OOM de las 13:01Z). Flag real confirmado en `openclaw agent --help` 2026.10.10: `--session-key <key>` (forma `agent:<id>:<key>`); no existe `--light-context`.

**Propuesta:** parche en rama `claude/dihr-canary-session-aislada` (base origin/main 97f2d87): `CANARY_SESSION_KEY="${UMBRAL_CANARY_SESSION_KEY:-agent:${AGENT}:canario}"` y `--session-key "$CANARY_SESSION_KEY"`; equivalente al `canary-inference.sh.PROPUESTO` del VPS (sha256 6ffc2269…; original desplegado a2a708b1…).

**Estado (2026-11-09 15:0xZ):** commit a66ad62 y **PR borrador #711** abierto (https://github.com/Umbral-Bot/umbral-agent-stack/pull/711), checks 2/2 en verde, mergeable; Auto-fix activo en la sesión coordinadora. **La aplicación directa en el VPS no fue posible:** la release desplegada en `/home/rick/.umbral/current/` es inmutable por diseño (`release-deploy.sh` retira el permiso de escritura) y cambiarla exigiría tocar permisos de la release, no aprobado. Por tanto D2 se despliega únicamente por la vía normal: merge del PR 711 y `release-deploy` de una release nueva, seguido de la verificación G2 en el primer tick.

**Estado (15:51Z): APLICADO.** PR 711 squash-merged (origin/main 49404b9); `release-deploy.sh --ref origin/main` → release 49404b9 activa, anterior 125af3a (rollback); canario desplegado sha 5899e40d…; tick 15:30Z: status=ok, sesión `agent:main:canario` creada, 0 entradas en `main`. G2 completa a las 24 h (< 5 % fallos). Rama local y worktree eliminados.

| Alternativa | Consecuencia | Cuándo preferirla |
|---|---|---|
| A. Sesión propia con flag (propuesta) | Historial de David limpio; el canario mide el gateway; cambio de 9 líneas, reversible | Siempre |
| B. Job de automation `isolated` + `--light-context` + modelo barato + `NO_REPLY` (docs OpenClaw) | Mejor aislamiento y menos coste; implica migrar del cron a los jobs de OpenClaw | Siguiente iteración, tras A |
| C. Sonda sin inferencia (solo `/healthz` + `WatchdogSec`) | Pierde la pregunta clave «¿puede generar texto?» que motivó el canario (UMB-276) | No recomendado |
| D. Desactivar el canario (`UMBRAL_SKIP_CANARY=1`) | Elimina la carga y la contaminación hoy; deja ciego al supervisor | Solo como medida temporal mientras se aprueba A |

**Aceptación:** G2. **Reversión:** vaciar `UMBRAL_CANARY_SESSION_ARGS` o revertir el PR.

## D3 · Embeddings fijados en Gemini

**Evidencia (VPS-03 A3, confirmada):** `openclaw.json` no tiene `memory.search` ni `agents.defaults.memorySearch` (solo `plugins.entries.memory-core={"config":{}}`); el esquema 2026.10.10 fija `memory.search.provider` por defecto en «openai»; el entorno del gateway tiene `GOOGLE_API_KEY` (no `GEMINI_API_KEY` ni `OPENAI_API_KEY`); índice `memory_index_meta_v1`: gemini-embedding-001, 3072 dims, 9 chunks, actualizado 2026-04-20; último error 06:30:15Z.

**Propuesta:** aplicar el diff preparado en el VPS (`~/dihr-staging/openclaw.json.memory.PROPUESTO.diff`, sha256 b464df97…; patch de reversión `{"memory": null}` 0ce434f8…): añade `memory.search = {provider: "gemini", model: "gemini-embedding-001", outputDimensionality: 3072}`; respaldo previo de `openclaw.json`; `openclaw memory index --force --agent main` (llama a la API de Gemini: 9 chunks); verificar con `memory status` (G3).

**Resultado de la aplicación (2026-11-09 14:33Z; aprobación B de David ~14:28Z y confirmación en la pestaña del hilo VPS):** el diff se aplicó y el gateway lo recargó en caliente sin reinicio; el reindex fue rechazado porque exige el gateway parado (no aprobado); y **Gemini respondió `400 API key not valid` con la `GOOGLE_API_KEY` presente en el entorno del gateway**. La causa (c) tiene por tanto dos capas: el proveedor por defecto (corregida) y una clave de Google que hoy no es válida para la API de Gemini (el índice de abril sí se construyó con ella: fue rotada, restringida o revocada después). La sesión VPS recomendó revertir D3 y David decide en su pestaña. **D3 corregida:** requiere primero una clave Gemini válida (acción de David en Google AI Studio o Cloud, cargada en `gateway.systemd.env` sin pegarla en ningún documento); después reaplicar el diff y reindexar en una ventana con el gateway parado (≈1 min) o esperar su reinicio natural. Mientras tanto, revertir evita llamadas fallidas en cada sincronización.

**Estado (16:45Z): REVERTIDO y REFORMULADO; PAUSA.** Criterio de David (16:2xZ): solo infraestructura propia y suscripciones vigentes, sin pago por uso; no activar facturación ni cambiar el índice existente; comparar y recomendar con una prueba reversible antes de aplicar. David cargó una `GEMINI_API_KEY` nueva en `gateway.systemd.env` del VPS (mtime 15:52Z; solo nombre y fecha, valor no leído). PKG-DIHR-VPS-06 quedó en PAUSA antes de usarla: la sesión VPS no hará prueba de clave, parche ni parada hasta «REANUDAR PKG-DIHR-VPS-06». Comparativa completa en `investigacion-embeddings-D3-2026-11-09.md`; el dimensionado de la vía local depende del REPORT PKG-DIHR-VPS-07 (capacidad del VPS, proveedores `memory.search` soportados por el esquema, agente de prueba con índice aparte). Recomendación provisional: **A′ sin embeddings (`provider: none`, solo FTS) como paso inmediato reversible**, y **E Ollama local** solo si el VPS tiene ≥1 GB libres sostenidos tras D1; Gemini gratuito queda condicionado a que David acepte los términos del nivel gratuito (uso del contenido por Google); Azure OpenAI con créditos de patrocinio es pago por uso diferido y requiere alerta de consumo. Prueba reversible preparada: índice aparte en un agente de prueba (no `main`), respaldo de `openclaw.json` con sha, patch y patch de reversión ya en `~/dihr-staging/`, sin reindexar `main`.

| Alternativa | Consecuencia | Cuándo preferirla |
|---|---|---|
| A. Pin a Gemini (nivel gratuito) | Memoria operativa con el índice existente (gemini-embedding-001, 3072 dims); reindex de 9 chunks trivial; 0 coste en nivel gratuito, pero Google puede usar el contenido para mejorar productos y hay cuotas por minuto/día | Solo si David acepta los términos del nivel gratuito; descartado el nivel de pago (pago por uso) |
| A′. `provider: none` (solo FTS) | Sin dependencia externa ni coste; búsqueda por palabras exactas, menor recuperación semántica; reversible al instante | Paso inmediato mientras se decide la vía definitiva |
| B. Clave OpenAI de API | Pago por uso y reindex completo por espacio de embeddings distinto | No (criterio de David) |
| D. Migrar a `gemini-embedding-2` | Reindex total; mejor calidad declarada; mismas condiciones de A | Solo después de A, con manifest del índice |
| E. Ollama local en el VPS (`nomic-embed-text`, 274 MB; 768 dims) | Sin coste ni salida de datos; +0,4–0,7 GB RAM y CPU en el VPS (8 GB, sin swap, gateway hasta ~5 GB); reindex completo por cambio de dimensiones | Si VPS-07 confirma ≥1 GB libres sostenidos; probar primero en agente aparte |
| F. Azure OpenAI `text-embedding-3-small` con créditos de patrocinio | Compatible con `openai-compatible`; consume créditos y pasa a pago por uso al agotarse; reindex completo | Solo con tope/alerta de consumo y decisión explícita de David |

**Aceptación:** G3. **Reversión:** restaurar `openclaw.json.bak`.

## D4 · Tailscale (requiere tu login)

**Evidencia:** VPS `NeedsLogin`, 0 peers; desde PCRick, claves del VPS (25-ago) y TARRO (31-ago) caducadas; servicio Tailscale de TARRO detenido y deshabilitado.

**Punto exacto para ti:**
- VPS (desde la sesión «UAS - VPS» o tu terminal): `tailscale up --force-reauth --ssh=false` → abrirá una URL de login; autentica en la consola de Tailscale; después, en la consola, en el dispositivo <host VPS>: «Disable key expiry» (o asignar un tag ACL).
- TARRO (PowerShell como administrador): `Set-Service Tailscale -StartupType Automatic; Start-Service Tailscale; tailscale up` → login; «Disable key expiry» en el dispositivo TARRO.
- Verificación: G4.

| Alternativa | Consecuencia |
|---|---|
| A. Re-auth con expiry deshabilitado (propuesta) | Recupera la ruta privada VPS↔PCRick↔TARRO; sin coste; reversible con `tailscale down` |
| B. Solo VPS (no TARRO) | Recupera VPS→Worker PCRick; TARRO sigue fuera de la tailnet |
| C. No reautenticar; depender del túnel SSH | Punto único de fallo; E2E solo por el nodo; notebook y Worker PCRick sin ruta directa |

## D5 · Solicitud 7ae25185 de PCRick
Pide pasar de 4 a 11 capacidades y de 7 a 21 comandos (terminal remota, pantalla, MCP). **Propuesta:** mantener pendiente hasta que R0 y el E2E (G5) estén aceptados; luego aprobar por capacidad. **Alternativas:** aprobar todo ahora (máxima autonomía de Rick sobre PCRick sin circuito probado); rechazar (Rick no podrá usar Codex/Claude en PCRick por el nodo, solo por SSH).

## D6 · Comparativa Rick GPT / Grok
Decisiones (a) aceptar evaluación en `high` o esperar «ultra»; (b) aislamiento procedimental o copia a cuenta separada; (c) autorizar sorteo + T0 de la primera comparación inédita; (d) transporte a los participantes. **Propuesta:** (a) aceptar `high` declarado (ultracode no es seleccionable); (b) procedimental con declaración explícita, salvo que el resultado vaya a publicarse; (c) sí, con las variantes no expuestas (C1-V2/V3/V4, C2-V1/V4, C3-V1..V4); (d) carpeta Drive por participante con enlace de solo lectura. Coordinación en Slack #uas.

## D7 · Secretos, claves y exposición
**Evidencia:** clave ed25519 suelta en `C:\Users\david\openclaw` (huella SHA256:ZBeipjmQ…; **no autorizada en el VPS**, cuyo `authorized_keys` solo tiene `david@TARRO` RSA y `pcrick-openclaw` ED25519 duplicada, ninguna con restricciones `from=`/`command=`); `env.rick-oauth.pending` (junio) con refresh tokens de Google en TARRO; credencial de Grok Bot en PCRick; **en PCRick el archivo de entorno del Worker (`C:\openclaw-worker\openclaw-worker-service.env` con WORKER_TOKEN, LINEAR_API_KEY, NOTION_API_KEY…) es legible por Usuarios y modificable por Authenticated Users**; Worker 8088 y sshd 22 en 0.0.0.0 en PCRick con reglas de firewall «Any» e interfaces LAN en perfil Public; Worker 8088 en 0.0.0.0 en TARRO permitido por la regla de Spotify; el host 0.0.0.0 del Worker PCRick está fijo en `run_openclaw_worker_service.ps1` línea 13 (script sin seguimiento en git); contraseña expuesta el 11-sep sin rotación acreditada; `_local-secrets` y estado de agentes en Drive; carpeta «Butic» de un tercero con acceso por enlace.

**Propuesta (orden):** 1) rotar la contraseña del 11-sep; 2) ACL del `.env` del Worker PCRick: solo SYSTEM y la cuenta del servicio (y rotar WORKER_TOKEN/NOTION_API_KEY/LINEAR_API_KEY después, por si ya fueron leídos); 3) clave suelta de TARRO: comprobar si está autorizada en PCRick o GitHub; si no, destruirla; si sí, moverla a `.ssh` con permisos 600; 4) `authorized_keys` del VPS: eliminar la línea duplicada y añadir `from=` para `pcrick-openclaw`; 5) aplicar o destruir `env.rick-oauth.pending`; 6) Worker TARRO y PCRick a `127.0.0.1` (cambio en el script del servicio y en la regla de firewall; para PCRick requiere que el VPS lo invoque vía nodo, no por HTTP directo) o regla con ámbito LAN/tailnet; sshd de PCRick con ámbito LAN; 7) revisar `_local-secrets`; 8) retirar enlace público de la carpeta de tercero si contiene material del Máster. **Alternativa:** solo 1–5 ahora (sin tocar red) y 6–8 después de D4. **Aceptación:** G6.

## D8 · Commit y PR del entregable
**Destino propuesto:** repo `Umbral-Bot/umbral-agent-stack`, rama `claude/dihr-uas-2026-11-09` desde `origin/main` (97f2d87), ruta `docs/operations/dihr-uas-2026-11-09/` (documento integral, investigación, pruebas de aceptación, este archivo, `ESTADO.md`, `ledger-dihr-uas.jsonl`, `evidencia/` con 14 archivos). Identificadores redactados tras la revisión (IP pública, usuario SSH, email personal, handle de tercero, id de correspondencia del juez, URL del GDoc de control). PR en borrador, sin merge. **Estado (16:30Z):** David autorizó D8 («Sí, ambas», ~15:54Z); commit 238cac4 y PR #712 abiertos a las 15:54Z; tests 3.11/3.12 en verde; el PR se abrió como listo y se devolvió a borrador tras la segunda revisión independiente, que exigió correcciones (aplicadas en el commit siguiente). Sin merge: David pidió no fusionar. **Estado (16:45Z):** en el commit de corrección f407ace los tests 3.11/3.12 fallan por `test_la_secuencia_completa_con_reloj_controlado` (tests/test_vps_monitor_alerting.py): prueba intermitente con margen de 1 s frente al reloj real, preexistente en main (#704/#705) y ajena a un commit solo de documentación; reproducida en local 1 de 4 veces. No se fusiona; la corrección de la prueba es trabajo aparte. **Alternativas:** mantener solo local (riesgo de pérdida, sin trazabilidad compartida); commit sin PR en rama remota (versionado sin revisión). 

## D9 · Permisos en PCRick
**Evidencia (PCRick-03, 06:36Z, valores vigentes):** Claude `settings.json` (03-nov) `defaultMode=bypassPermissions` sin allow/deny; Codex `config.toml` **modificado hoy 03:52:37Z sin atribución**: `approval_policy="never"`, `sandbox_mode="danger-full-access"`, 6 proyectos de confianza; Antigravity `Always Proceed` ×2 y secure mode off. Además, la política de aprobaciones del nodo OpenClaw (`exec_approvals_config`: `security=full, ask=off, askFallback=full`) hace que `system.run` desde el VPS corra sin preguntar (VPS-03 A5). `.claude/settings.local.json` del clone: +2 reglas para el conector Drive el 09-nov 03:59Z (atribuible por inferencia a la sesión del juez). Copias de respaldo con SHA-256 en `~\dihr-staging\permisos-bak-20261109T063631Z\` (no se copió `state.vscdb` porque contiene un oauthToken).

**Propuesta:** (a) IDE: modos por defecto + trust por carpeta de trabajo por paquete; (b) nodo: `ask=on` o allowlist de comandos para `system.run` al menos hasta que el E2E esté aceptado. **Alternativas:** mantener todo (máxima autonomía, máxima superficie en una VM que expone 8088/22/445 y cuyo `.env` es modificable por cualquier usuario autenticado); solo Codex a sandbox y nodo con allowlist (compromiso). **Aceptación:** relectura de los tres archivos y de `exec_approvals_config`; un paquete de prueba con trust por carpeta; `system.run` de prueba que pida aprobación.

## D10 · Cadencia del poller Notion
**Evidencia:** 100.051 `poll_comments` en 7 días ≈ 10 req/min (5,5 % del límite de 180 req/min por integración); 0 fallos del poller en 24 h; 5 respuestas HTML en 100 k. Es optimización. **Propuesta:** intervalo 30–60 s o webhooks. **Alternativa:** dejar como está (ruido en ops_log y carga innecesaria, sin fallo observado). **Aceptación:** G12.

## D12 · Ingesta de Granola en TARRO (tarea rota, causa verificada)
**Evidencia:** `GranolaVmRawIntake` y `GranolaVmRawIntakeStartup` fallan (0x1) porque `scripts/vm/granola_vm_raw_intake.py` (clone `-codex`) busca `%APPDATA%\Granola\cache-v6.json` y la app Granola (activa desde 05-nov) ahora escribe `cache-v6.json.enc` cifrado (626 KB, 09-nov 03:33Z); `C:\Granola\vm-raw-intake-stderr.log` 09-nov 00:15Z. Coincide con los «recent gaps» del gap-check del VPS (última página 05-nov). **Propuesta:** PR que detecte el formato cifrado y use la vía soportada por la versión actual de Granola (exportación oficial o la tarea `GranolaWatcher` de PCRick, que sí corrió el 07-nov) en lugar del caché; mientras, documentar el hueco. **Alternativas:** descifrar el caché (depende de una clave de la app: frágil y posiblemente fuera de sus términos); desactivar la tarea hasta reescribirla (evita el ruido de errores, no recupera datos). **Requiere:** cambio de código (PR) y despliegue en TARRO.

## D13 · Escritor automático de Ops Resume (tarea rota, causa acotada)
**Evidencia (causa raíz verificada hoy):** `\Umbral\OpsResumeWriter` devuelve 0x2 cada 30 min. `automatic/cycles.jsonl`: último ciclo con mutaciones 2026-09-17T12:00Z (2); **primer `BLOCKED / ERROR_SourceError` 2026-09-17T13:30:01Z; 2.532 ciclos bloqueados consecutivos hasta hoy 06:45Z**; `health.json` = FAILED. Reproducido en seco (`--dry-run`, 0 escrituras). La fuente del scope `ng01-continuidad-v1` es `umbral-agent-stack/docs/operations/ledger-stack-roadmap-diag.jsonl` (sin versionar, en el clone coordinador). **La línea 112 de ese ledger** (ts 2026-09-17T13:10:00Z, PKG-C23-GROK-ALUMNO-20260917, evento ACK) contiene una ruta de Windows con barras invertidas sin escapar (`C:\Users\Rick\Documents\…`): `json.loads` falla («Invalid \escape», carácter 322) y el lector `ops_resume_source.py` lanza `SourceError("MALFORMED_JSON", "record cannot be safely attributed")`, deteniendo el ciclo completo por diseño (0 escrituras). Es la única línea inválida de 237. El wrapper no deja rastro en `scheduled.log` porque la excepción se captura en `main()` y solo va a stderr (pythonw lo descarta). Ops Resume (855 filas) no recibe proyección desde entonces aunque Gobernanza y la página UAS declaren el mantenimiento activo.

**Propuesta:** (1) corregir la línea 112 escapando las barras (`\` → `\\`), con copia `.bak` fechada del ledger y nota en el propio ledger (evento de reconciliación), coordinado con la sesión dueña del clone coordinador; (2) PR en notion-governance para que el wrapper escriba el motivo (`ERROR_SourceError MALFORMED_JSON path:line`) en `scheduled.log` y `health.json`, y opcionalmente para que el modo mantenimiento ponga en cuarentena la línea inválida y continúe (hoy bloquea todo); (3) un ciclo verificado W1/W2 con recibo (G13: `cycles.jsonl` con `result != BLOCKED` y `Projected at` de hoy en Ops Resume). **Alternativas:** solo (2) sin tocar el ledger (la proyección sigue bloqueada hasta que alguien repare la línea); desactivar la tarea y declarar Ops Resume congelado al 17-sep; rehacer la proyección a mano una vez. **Requiere:** tu OK para editar una línea del ledger ajeno y para el PR; sin credenciales ni seguridad implicadas.

## D11 · Inventario del notebook MSI por el puente Drive
**Situación:** ninguna sesión alcanza MSI; Rick GPT opera el puente con Codex MSI y pide tu autorización para publicar PKG-DIHR-MSI-01 (inventario de solo lectura: identidad, Tailscale, SSH alias, puertos, tareas, versiones, clones, Worker, nombres de variables de .env, última línea de ops_log) y compartir con Claude Code un informe saneado. **Propuesta:** autorizar con esos límites. **Alternativa:** dejar MSI fuera del diagnóstico (queda como «no accesible» en la matriz C). Advertencia de Rick GPT: hubo bloqueos previos de publicación; la autorización no garantiza que el puente acepte.
