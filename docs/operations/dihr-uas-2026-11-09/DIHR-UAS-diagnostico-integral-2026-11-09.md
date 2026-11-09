# DIHR UAS · Diagnóstico integral y hoja de ruta — corte 2026-11-09

**Frente:** Diagnóstico integral y hoja de ruta UAS (DIHR UAS, también DSIR UAS). Ficha Notion: https://app.notion.com/p/4135f443fb5c8110a1b2e608ee85cb19 · Dashboard: https://app.notion.com/p/40d5f443fb5c8139ade4ddc857afdf83 · Hoja de ruta oficial UAS (13-sep): https://app.notion.com/p/3ca5f443fb5c813f9238e308259e4bd9
**Coordinador:** sesión Claude Code «Control remoto de hilos Claude Code» (local_815b91f1), TARRO. Modelo observado `claude-fable-5-1`, esfuerzo `high`, permisos bypass, Remote Control activo. No es «ultra»: el modo ultracode no estaba seleccionado.
**Ventana de trabajo:** 2026-11-09 05:21–07:00 UTC aprox. Todas las lecturas remotas fueron de solo lectura; ningún sistema productivo fue modificado (sección H).
**Ubicación de trabajo:** `C:\GitHub\umbral-agent-stack-claude\docs\operations\dihr-uas-2026-11-09\` (este documento, `ESTADO.md`, `ledger-dihr-uas.jsonl`, `investigacion-estado-del-arte-2026-11-09.md`, carpeta `evidencia/`). No se tocó el clone coordinador `C:\GitHub\umbral-agent-stack` (rama `rick/motor-piezas-lab`, 114 archivos sucios, en uso por otra sesión).
**Cómo leer:** «Verificado» = observado por esta sesión o por un hilo ejecutor con comando y hora; «Reportado» = afirmación de otro agente o documento sin comprobación independiente; «Hipótesis» = inferencia. Fecha del hecho y fecha de lectura se indican por separado.

---

## A. Resumen ejecutivo y decisiones

### A.1 Qué pasa (hechos verificados hoy)

1. **Rick en el VPS está degradado por tres causas comprobadas, ninguna reparada** (segunda verificación VPS-03, 06:35Z). (a) El gateway OpenClaw corre con el heap V8 por defecto (2.240 MB, sin `NODE_OPTIONS` ni drop-ins) y muere por OOM: **octava caída a las 06:18:42Z de hoy tras 8 h 44 min de uptime** (NRestarts=8), coherente con las 7 anteriores; lo que sigue sin identificarse es la fuente del crecimiento (≈ +4 MB/min estimado; la sesión `main` acumula 10.264 eventos y la base 1,36 GB). (b) El canario de salud corre cada 30 min dentro de la sesión principal de Telegram sin `--session-key`: en 24 h, 35 fallos de 48 ticks y **25 de 25 abortos de tu sesión principal coinciden en ≤ 60 s con un fallo del canario** (0 abortos sin canario): la contaminación ya no es correlación sino evidencia directa. (c) `openclaw.json` no tiene ninguna clave `memory.search`, por lo que el runtime usa el proveedor por defecto OpenAI sin clave mientras el índice es Gemini (3072 dims, 9 chunks) y `GOOGLE_API_KEY` sí está en el entorno del gateway: memoria inoperante («provider openai configured but unavailable», último 06:30Z). Archivos de reparación preparados y verificados en `~/dihr-staging/` del VPS (drop-in dimensionado con la RAM real, parche del canario con el flag real `--session-key agent:main:canario`, diff de memoria con su reversión). **Aplicación aprobada por David (opción B, D2+D3) a las ~14:3xZ:** D3 se aplicó con recarga en caliente, pero Gemini rechazó la clave de Google del gateway («400 API key not valid») y se revirtió: la causa (c) tiene una segunda capa, una clave de Google hoy inválida para la API de Gemini, que requiere acción de David antes de reintentar. **Opción A de David (~15:2xZ), ejecutada (PKG-DIHR-VPS-05, 15:06–15:50Z):** D2 aplicado por la vía normal (PR #711 squash-merged → `origin/main` 49404b9 → `release-deploy.sh`, release inmutable nueva, rollback disponible a 125af3a); el tick del canario de las 15:30Z corrió en la sesión `agent:main:canario` y la sesión principal no recibió entradas (G2, primer tick PASS). D1 paso 2 aplicado: drop-in con `--max-old-space-size=2560` (heap efectivo 2.752 MB), `MemoryHigh=5000M`, `MemoryMax=5500M`, `Restart=on-failure` con backoff, en un corte único de 97,6 s (15:47:22–15:48:59Z); PCRick reconectó a las 15:48:57Z; observación G1 de 24 h en curso. D3 omitido por falta de clave Gemini (pendiente de David). Antes de la opción A, el gateway no se reinició por nosotros, pero sí por sí solo: **noveno reinicio a las 10:01:32Z, tras solo 3 h 42 min**, causa no verificada en esa ventana; el ciclo de OOM es recurrente pero no fijo (3,7 a 8,7 h). Tras revertir D3, la memoria vuelve a OpenAI y falla ahora con 429 (cuota) en vez de «unavailable»: alguna credencial OpenAI sí se resuelve pero sin cupo para embeddings (VPS-04, 14:53Z).
2. **La red privada está caída por caducidad de claves, no por un fallo transitorio.** Verificado: Tailscale en el VPS está en `NeedsLogin` con 0 peers; desde PCRick (`tailscale status`), la clave del VPS figura caducada el 2026-08-25 y la de TARRO el 2026-08-31; en TARRO el servicio Tailscale está detenido y deshabilitado (la caducidad de TARRO solo es observable desde PCRick). La única ruta VPS↔PCRick es el túnel SSH inverso (PID 5692 en PCRick, estable desde 7-nov 08:30Z). Hipótesis: los reinicios OOM del gateway (~1 min sin puerto) explican las reconexiones del nodo; el stderr del túnel registra 10 «Connection refused» frente a 7 reinicios, y solo el último (21:34:53Z) coincide con una caída registrada (21:34:20Z). El notebook MSI no está en la tailnet y no fue alcanzable desde ningún hilo.
3. **PCRick está sano en local y emparejado una sola vez** (confirmado desde ambos lados: `nodes status` en VPS y `node status` en PCRick). AUT-1 queda aceptado en su parte remota; falta la prueba tras próximo inicio de sesión. AUT-2 no se ejecutó (auxiliares fuera de alcance). La solicitud de ampliación de capacidades 7ae25185 (4→11 capacidades, 7→21 comandos, incluye terminal remota, pantalla y MCP) sigue pendiente de David.
4. **El circuito de extremo a extremo VPS→PCRick→Worker→retorno no está probado.** El Worker de PCRick (8088, v0.4.0) responde /health; la sesión PCRick reportó el 08-nov (tabla de 12:30Z, fila 14, leída en su pestaña) que no recibe una petición externa desde el 14-oct, y hoy «0 peticiones externas». Como la ruta VPS→Worker por Tailscale caducó el 25-ago, el origen de aquella última petición no está identificado. La ruta VPS→PCRick por el nodo OpenClaw sí existe y permite la prueba E2E sin esperar a Tailscale. La prueba está diseñada (sesión VPS, 00:51Z) y no ejecutada.
5. **Mission Control existe y corre, pero no tiene URL de acceso.** Es el módulo `mission_control/` (FastAPI+HTMX, solo lectura, ADR-009 de mayo), unit `mission-control` activa en el VPS desde el 23-oct, /health 200, escuchando únicamente en 127.0.0.1:8089; su README documenta un script de túnel SSH (`pit-judge-open.ps1`) para abrirlo desde un cliente, no probado hoy. Las URL que circularon (127.0.0.1:8784 en TARRO el 7-nov; 127.0.0.1:18991/uas/ en el VPS el 6-nov) fueron prototipos locales o servidores sintéticos temporales (reportado por Rick GPT). El tablero vivo de seguimiento es el provisional de Notion, mantenido a mano por Rick GPT/dot.
6. **La coordinación depende de David como mensajero, pero hoy quedó demostrada una vía directa.** Seis paquetes de solo lectura fueron emitidos por mensajería entre sesiones Claude y devueltos con ACK y REPORT sin pegado humano (los dos primeros en 5 y 9 minutos según las horas de sus REPORT; los `ts` del ledger son horas de escritura del coordinador, no del evento). Rick GPT respondió en su hilo con el formato acordado. Según Rick GPT, lo que le impidió actualizar la ficha DIHR fue la instrucción de su automatización «monitor del tablero» («No modifiques Notion…»), no un permiso de Notion; esta sesión no verificó ese mecanismo.
7. **Higiene y seguridad:** TARRO tiene una clave privada OpenSSH suelta en `C:\Users\david\openclaw` (archivo, 2026-02-25; ed25519, huella SHA256:ZBeipjmQ…, distinta de la `id_rsa` de TARRO; si sigue autorizada en el VPS se sabrá por las huellas de `authorized_keys` pedidas en VPS-03); el Worker local escucha en 0.0.0.0:8088 y la única regla de firewall que lo permite es la de la app Spotify (perfil Any, remoto Any), no una regla de UAS; el clone desde el que corre ese Worker (`-codex`) está 15 commits detrás de `main` con 49 archivos sucios; el clone de PCRick está 370 commits detrás; la contraseña expuesta el 11-sep (ficha 006) no tiene rotación acreditada. En Drive: carpeta `_local-secrets` dentro de 02_Operacion, estado de agentes (`.claude`, `.codex-*`) dentro de carpetas de cliente, una carpeta «Butic» de un tercero con acceso por enlace, y ~30 snapshots duplicados del repo en un export de abril.
8. **La comparativa Rick GPT / Grok no es comparable todavía.** El juez ciego R1 (Fable 5.1, high, aislamiento procedimental) puntuó 5 piezas de regresión como PARCIAL sin fallo crítico, C3 NO_EVALUABLE, sin ganador: no hay dos candidatos sobre el mismo caso, ni run_id, T0, trazas ni sorteo. Cuatro decisiones de David están pendientes (ver D6).
9. **Las decisiones de la entrevista (Q01–Q12) están vigentes y conciliadas** (acta verificada por hash); la ficha 006 de C23 estaba atrasada. Verificado en TARRO (07:25Z): el PBIX del ensayo docente del 17-sep existe en `Clase-23\ensayo-claude-20260917\AEC23_OBRA01_C23_docente.pbix` (125.351 B, SHA-256 b7aefd23…, idéntico al respaldo en `demo-clase\0-powerbi\`), junto con el proyecto PBIP, los prompts MCP y `LEEME_original_interno.md`. Verificado hoy en PCRick: la carpeta de evidencia del alumno tiene 88 archivos (17-sep); se abrieron 2: el informe IDE+MCP del ejecutor Grok (09:16–09:44 CLT) da 3 PASS (permisos, auditoría CSV de 12 filas, MCP Power BI solo lectura con `[Incidencias activas]=8` y `[Avance % ponderado]=0,275`) y 1 BLOCKED (escritura MCP sobre copia, por instancia única de Power BI Desktop); el PBIX del ejercicio existe (77.805 B, SHA-256 8024…) y fue modificado a las 15:44:44Z, cuatro minutos después del PASS_PARTIAL del ledger (15:40Z). Que el informe IDE+MCP sea el origen del PASS_PARTIAL es inferencia coherente, no texto literal.
10. **Tres hallazgos nuevos del segundo corte.** (a) El Worker del VPS ejecutó 100.051 `notion.poll_comments` en 7 días (≈10 req/min, ≈5,5 % del límite de 180 req/min de la integración) de 127.979 tareas; el poller no registra fallos en 24 h y hubo 5 respuestas HTML en 100 k: es carga evitable, no saturación demostrada. (b) La medición de coste está rota: `runtime-snapshot` reporta tokens 0 y coste 0 con 158 `llm_usage` reales (124 atribuidos por proveedor en el REPORT: Claude Sonnet 4.6 vía proxy y directo, Haiku 3, GPT-5.3-codex y 5.4 vía Azure Foundry, Gemini 2.5 Flash; 34 sin desglose). (c) PCRick documenta desde el 17-sep, por decisión de David para C23, una postura de permisos máxima en los tres IDE (Claude `bypassPermissions`, Codex `approval never` + `danger-full-access`, Antigravity `Always Proceed` + secure mode off). Vigencia actual no verificada; hay un indicio de cambio posterior: `.claude/settings.local.json` del clone de PCRick modificado el 09-nov 03:59Z por otra sesión.

### A.2 Decisiones que requieren a David (agrupadas; acción · motivo · impacto · reversión)

| # | Decisión | Acción propuesta | Motivo | Impacto | Reversión |
|---|---|---|---|---|---|
| D1 | **Reparación mínima del gateway OpenClaw (VPS), en dos pasos** | Paso 1 (sin tocar memoria): sacar el canario (D2) y compactar o abrir sesión nueva de `main`; medir 24 h el ciclo de OOM. Paso 2 (solo si el ciclo persiste): drop-in systemd `--user` para `openclaw-gateway.service` con `Environment=NODE_OPTIONS=--max-old-space-size=2560 --heapsnapshot-near-heap-limit=1`, `MemoryHigh=6G`, `MemoryMax=6800M`, `RestartSec=5`, `RestartSteps=4`, `RestartMaxDelaySec=30`; `daemon-reload` + un reinicio controlado (≈1 min sin gateway). Ejecuta la sesión «UAS - VPS» como operador único, previo aviso. | Causa (a) comprobada; heap por defecto 2.240 MB. **Riesgo declarado:** RSS 4,4 GB con heap 2,2 GB implica 2–3 GB fuera del heap; el cgroup ya usa 5,45 GB y la RAM libre bajó de 997 a 618 MB en 15 min. Subir el heap a 3 GB con `MemoryMax=6G` mataría el proceso antes de que el snapshot se dispare, y escribir el snapshot necesita RAM libre. Por eso el paso 2 sube el heap solo 320 MB, deja `MemoryHigh` por encima del uso actual y reserva margen hasta `MemoryMax`. | Paso 1: cero corte. Paso 2: 1 minuto de corte planificado; si la fuga es externa al heap, el límite de cgroup convierte el OOM en reinicio limpio y más frecuente, no lo evita. | Borrar el drop-in y reiniciar: 2 minutos. |
| D2 | **Sacar el canario de la sesión principal** | Cambiar `canary-inference.sh` a `openclaw agent … --session-key canary` (o job de automation `isolated`, `--light-context`, modelo barato, `NO_REPLY`), PR en rama `rick/`; editar el cron en el VPS tras el merge. | Causa (b) comprobada; contamina el historial de David y compite con su uso. | Historial limpio; canario mide el gateway y no la sesión. | Revertir PR y cron. |
| D3 | **Fijar proveedor de embeddings = Gemini** | Paso 0: verificar en el VPS la clave de configuración vigente (`agents.defaults.memorySearch` según VPS-01; `memory.search.provider` según la documentación) y que `GOOGLE_API_KEY` está en el entorno del proceso del gateway (la sesión VPS lo afirmó a las 00:51Z; no reverificado en VPS-01). Luego: `provider: gemini`, modelo `gemini-embedding-001`, dims del índice; `openclaw memory index --force`; respaldar `openclaw.json` antes. | Causa (c) comprobada (VPS-01 ítem 5). | Memoria vuelve a funcionar; reindex de 9 chunks es trivial. | Restaurar `openclaw.json.bak`. |
| D4 | **Reautenticar Tailscale en VPS y TARRO** | `tailscale up --force-reauth` en cada equipo con un tag (expiry deshabilitado) o «Disable key expiry» en la consola; en TARRO habilitar el servicio. Requiere login interactivo de David en la consola de Tailscale (no puede hacerlo un agente). | Claves caducadas desde agosto; sin tailnet no hay ruta VPS→Worker PCRick ni al notebook, y el túnel SSH es punto único de fallo. | Recupera la ruta privada; permite la prueba E2E y la matriz completa. Cambio de VPN: requiere tu aprobación expresa. | `tailscale down` / deshabilitar servicio. |
| D5 | **Solicitud 7ae25185 de PCRick** | Recomendación: **mantener pendiente** hasta que D1–D4 y la prueba E2E estén aceptadas; después decidir por capacidad, no en bloque (la solicitud pide terminal remota, pantalla y MCP a la vez). | Amplía 4→11 capacidades sin un circuito básico probado. | Sin cambio operativo hoy. | — |
| D6 | **Comparativa Rick GPT / Grok** | (a) aceptar evaluación en `high` declarado o esperar «ultra»; (b) aislamiento: copia a cuenta/unidad separada vs aceptar el procedimental; (c) autorizar sorteo congelado + T0 de la primera comparación inédita; (d) vía de transporte a los participantes. Coordinación reservada al hilo Slack #uas 1794197926.927949. | Sin estas decisiones no hay comparación válida; lo existente solo es regresión. | Define el calendario de la competición. | — |
| D7 | **Secretos, claves y exposición** | Rotar la contraseña expuesta el 11-sep (ficha 006, incidente de un subagente); mover o eliminar `C:\Users\david\openclaw` (clave OpenSSH suelta) tras confirmar que `id_rsa` cubre el acceso; revisar `env.rick-oauth.pending` en TARRO (refresh tokens de Google de junio: aplicar o destruir) y el archivo de credencial de Grok Bot en PCRick; en PCRick, Worker 8088, sshd 22 y SMB 445/139 escuchan en todas las interfaces: restringir a la LAN/tailnet; en TARRO, Worker 8088 en 0.0.0.0 con firewall Allow: restringir a loopback/LAN; revisar `_local-secrets` en Drive y sacar el estado de agentes (`.claude`, `.codex-*`) de las carpetas de cliente; quitar el acceso por enlace de la carpeta «Butic» del tercero si contiene material del Máster. | OWASP: una exposición es incidente abierto hasta rotar; superficie de red innecesaria en dos equipos. | Reduce superficie; ninguna de estas acciones afecta servicios si se hace en orden (claves nuevas antes de retirar las viejas; reglas de firewall probadas desde la LAN). | Reglas de firewall y archivos restaurables desde copia previa. |
| D8 | **Dónde quedan los entregables** | Confirmar commit de `docs/operations/dihr-uas-2026-11-09/` en rama `claude/dihr-uas-2026-11-09` y PR a `main` de umbral-agent-stack (los identificadores sensibles ya fueron redactados en el paquete); actualización de la ficha DIHR en Notion con enlace y avance calculado (sin tocar respuestas ni el GDoc de control del monitor). | Ubicación identificable y versionada. | Ninguno operativo. | Cerrar PR sin merge. |
| D9 | **Postura de permisos en PCRick** | Paso 0: una sesión PCRick lee los tres archivos de configuración (Claude `settings.json`, Codex `config.toml`, Antigravity `state.vscdb`) y crea `.bak` fechados. Después, decidir si la configuración del 17-sep (bypass / approval never + danger-full-access / Always Proceed) sigue vigente fuera de un encargo concreto. Propuesta: volver a modos por defecto y conceder bypass por paquete y carpeta de trabajo (project trust), no de forma global. | Fue una decisión acotada a C23 y quedó global en una VM que recibe trabajo de varios agentes y expone servicios en red. Hay indicio de cambio no atribuido (settings.local.json 09-nov 03:59Z). | Más prompts de aprobación en PCRick en trabajo interactivo; ninguno en paquetes con trust por carpeta. | Restaurar los tres archivos desde los `.bak` creados en el paso 0. |
| D10 | **Carga del poller de comentarios Notion (optimización, no urgencia)** | Medir primero req/min reales de la integración (hoy ≈10 req/min por `poll_comments`, más `read_database`); si se confirma, bajar la cadencia de ≈6 s a 30–60 s o pasar a webhooks de Notion si el plan lo permite; mantener el cursor ADR-010. | 100 k llamadas/7 d son carga evitable (≈5,5 % del límite de 180 req/min); no hay 429 en la evidencia y el poller no falla. | Latencia de reacción a comentarios de 6 s a 30–60 s; menos ruido en ops_log (100 k eventos/semana). | Volver al intervalo anterior (variable de entorno). |

Nada de lo anterior se ejecutó. D2, D3 y el paso 1 de D1 son < 1 h de trabajo del hilo VPS y revierten en minutos; D4 necesita tu login; D7 y D9 requieren tu confirmación por ser cambios de seguridad.

---

## B. Inventario y mapa multisistema

### B.1 Equipos

| Equipo | Rol | Estado observado (fecha) | Fuente |
|---|---|---|---|
| **TARRO** (Windows 11 Pro 25H2, `TARRO\david`) | Puesto de David; host Hyper-V de PCRick; coordinación Claude/Codex/Cursor/Antigravity/Grok Bot | Uptime 9d 12h; Tailscale deshabilitado; Worker UAS 8088 v0.4.0 vivo (114 tareas) desde clone `-codex`; 72 clones git bajo C:\GitHub; ~350 procesos node/python de servidores MCP; 7 tareas programadas Umbral (3 con error: GranolaVmRawIntake ×2 0x1, OpsResumeWriter 0x2) | evidencia/inventario-TARRO (05:35–05:40Z) |
| **PCRick** (VM Hyper-V «OpenClaw», Windows 11, GUID 870F59FD…) | Ejecución Windows/AEC; nodo OpenClaw; Worker 8088 | Nodo único PID 13176, v2026.10.10, emparejado; túnel SSH inverso PID 5692; Worker v0.4.0, 80 tareas, 0 peticiones externas (desde 14-oct según su tabla del 08-nov); Worker 8088, sshd 22 y SMB 445/139 en 0.0.0.0; Tailscale en línea (100.109.16.40); claude 2.1.273, codex 0.154.0, openclaw 2026.10.10, Grok Bot 0.78.1 instalado sin proceso; repo 370 commits detrás; File History detenido | evidencia/REPORT-PKG-DIHR-PCRICK-01 (05:36–05:39Z) |
| **VPS** srv1431451 (Ubuntu, Hostinger, usuario rick, <IP pública VPS>) | Gateway OpenClaw (Rick Telegram), Dispatcher, Worker, Redis, n8n, Mission Control, 14 crons | Gateway 8h uptime/NRestarts 7; user units activas: openclaw-gateway, openclaw-dispatcher, umbral-worker, mission-control, n8n; Redis 7.0.15; release 125af3a (3 detrás de main); Tailscale NeedsLogin; público solo 22/80/443 | evidencia/REPORT-PKG-DIHR-VPS-01 (05:35–05:38Z) |
| **Notebook MSI** | Equipo secundario; puente Drive TARRO-MSI (Codex MSI) | **No accesible** desde ningún hilo; no está en la tailnet; último REPORT por Drive 05-nov 16:54Z («pendiente de validación y recibo del coordinador») | inventario-drive; ficha Notion TARRO–MSI (4-nov) |

### B.2 Servicios y runtime UAS

| Componente | Dónde | Versión / estado | Observación |
|---|---|---|---|
| OpenClaw Gateway | VPS 127.0.0.1:18789 | 2026.10.10 | OOM cíclico (A.1-1a) |
| OpenClaw Node | PCRick → túnel → VPS 18790 | 2026.10.10 | único, emparejado |
| Dispatcher | VPS (`openclaw-dispatcher`) | activo desde 23-oct | sin VM health polling (#691) |
| Worker | VPS 8088 (v0.4.0), PCRick 8088 (v0.4.0, 80 tareas), TARRO 8088 (v0.4.0, 114 tareas, 0.0.0.0) | tres instancias | solo la del VPS está en la ruta del Dispatcher |
| Redis | VPS 6379 loopback | 7.0.15, PONG | — |
| Mission Control | VPS 127.0.0.1:8089 | unit activa, /health 200 | solo loopback; UI no abierta |
| n8n | VPS 5678/5679 loopback (v2.10.2, 2 workflows activos, 672 OK/7 d); n8n Cloud «dmbutic» (32 workflows, relay Slack→Grok activo) | dos instancias con propósitos distintos | VPS-02 ítem 2 |
| Crons VPS | 14: health-check */30 (canario), supervisor */5, notion-poller */5, scheduled-tasks */1, quota-guard */15, runtime-snapshot, … | activos | runtime-snapshot sin log desde 23-oct |
| Memoria OpenClaw | VPS, índice gemini 9 chunks | inoperante (proveedor) | A.1-1c |
| Respaldos VPS | `~/respaldos-openclaw/sqlite` (main 7-nov 02:46Z, 1,34 GB), `.bak` de config | manuales, sin programación ni destino externo | — |

### B.3 Agentes y coordinación

| Actor | Superficie | Rol vigente (fuente) |
|---|---|---|
| David | decide; único humano | — |
| Rick VPS | Telegram vía gateway | asistente principal; degradado |
| Rick GPT / dot | ChatGPT (hilo «Rick GPT», proyecto Rick GPT) | coordinación conversacional, monitor del tablero Notion (automatización cada 10 min con GDoc de control), redactó el encargo DIHR |
| Rick Grok / Grok Bot | PCRick (instalado, sin proceso hoy), TARRO (9 procesos) | par de Rick VPS (Q03); tester alumno AEC; relay Slack→Grok vía n8n cloud |
| Codex | TARRO, PCRick, MSI; coordinador del programa `stack-roadmap-diag` (ledger 238 eventos, último 4-nov) | coordinación y ejecución; hoja de ruta oficial 13-sep |
| Claude Code | TARRO (esta sesión + 6 locales), VPS («UAS - VPS»), PCRick (3 sesiones Remote Control), cloud (8 sesiones) | ejecución y, hoy, coordinación DIHR |
| Cursor, Antigravity, Copilot M365 | TARRO | ejecutores; Antigravity solicitado para Drive sin resultado recibido; M365 sin conector en esta sesión |
| Morty | Notion | operador de Notion (decisión 13-sep); `OpsResumeWriter` en TARRO falla 0x2 |

### B.4 Registros, fuentes y canales

| Registro | Ubicación | Estado |
|---|---|---|
| Ledger programa `stack-roadmap-diag` | `C:\GitHub\umbral-agent-stack\docs\operations\ledger-stack-roadmap-diag.jsonl` (sin versionar) | 238 eventos, último 2026-11-04 |
| Macro-plan / plan siete frentes / acta entrevista | mismo directorio | acta SHA-256 85c9e86f… verificado hoy |
| Hoja conciliada DIHR (Rick GPT) | `/workspace/shared/UAS-hoja-conciliada-2026-11-09.md` en ChatGPT | no accesible desde TARRO como archivo; texto íntegro recibido en el hilo y guardado en evidencia/HOJA-CONCILIADA-RICK-GPT |
| Notion | dashboard provisional (12 frentes + DIHR), página UAS (13-sep, última edición 05-oct), Ops Resume | dashboard mantenido a mano; página UAS desactualizada respecto al ledger local |
| Drive | Puente TARRO-MSI (inbox/outbox/control, 03→05-nov), control WSP M5, ledgers por cliente, export agentes abril | owner único, sin unidades compartidas |
| Slack | canal privado #uas (05-nov); hilo 1794197926.927949 reservado a la comparativa | — |
| GitHub | umbral-agent-stack main 97f2d87; PRs abiertos 710 (motor piezas), 709 (cloud pilot), 693 (HIGIENE-01); notion-governance PR 48 (ADR 11 #uas), 6, 3 | — |
| Linear | UMB-276 incidente Rick VPS | no accesible (auth) |
| Azure | tenant f67a8c0b…, 3 suscripciones; reclamo de cobro en curso con soporte Microsoft (correo 8/9-nov) | solo listado |

### B.5 Matriz de conectividad TARRO ↔ PCRick ↔ VPS ↔ notebook (observable sin secretos)

| Origen → Destino | Ruta existente | Identidad/puerto | Estado (fecha) | Prueba | Vacío |
|---|---|---|---|---|---|
| TARRO → VPS | SSH público `rick@<IP pública VPS>:22` (alias `vps-umbral`) | known_hosts incluye srv1431451 | **Activa**: 2 sesiones ssh de la app Claude (Remote Control «UAS - VPS») desde 06-nov | Remote Control operativo hoy | Tailscale caducado 31-ago |
| TARRO → PCRick | Hyper-V local (VMConnect), TeamViewer (bloqueado por ID desde 12-sep), RustDesk | 192.168.x | VMConnect abierto desde 07-nov; Remote Control Claude en PCRick operativo | paquetes hoy | sin SSH directo; Tailscale off en TARRO |
| PCRick → VPS | túnel SSH inverso `openclaw-node-tunnel` (PID 5692) → VPS 18790; sesión 192.168.42.152→<IP pública VPS>:22 | ssh rick | **Activa** desde 07-nov 08:30Z; 10 reconexiones por OOM del gateway | nodo emparejado | ping prohibido por coordinación previa |
| VPS → PCRick | solo a través del nodo OpenClaw (`node.invoke`) por el túnel | nodeId 9650c4eb… | **Disponible**, E2E no ejecutado | — | sin Tailscale; sin túnel 22024 |
| VPS → Worker PCRick (8088) directo | requería Tailscale (WORKER_URL_VM) | — | **Caída**: clave Tailscale del VPS caducada el 25-ago; el Worker reporta su última petición externa el 14-oct por una ruta no identificada | — | D4; alternativa: invocar el Worker desde el nodo (`system.run`) |
| notebook MSI ↔ resto | Drive «Puente TARRO-MSI» (asíncrono) | — | último REPORT 05-nov | — | no está en tailnet; sin sesión alcanzable |
| Grok (Linux/PC) → PCRick | enlace Tailscale informado 13-sep; RustDesk | — | **No verificado** hoy | — | — |

---

## C. Matriz de cobertura

| Ámbito | Estado | Cómo / fecha de lectura | Límite |
|---|---|---|---|
| VPS: gateway, nodos, canario, embeddings, red, units, crons, respaldos, repo, solicitud 7ae25185 | **Verificado** | sesión «UAS - VPS», 05:35–05:38Z, 10/10 ítems | sin sudo (auth.log, origen del túnel); Telegram no leído |
| VPS: agentes OpenClaw, n8n VPS, editorial, Granola, ops_log 7d, MC /risks y /gates, supervisor/poller | **Verificado** | sesión «UAS - VPS», 05:50–05:53Z, 8/8 | `memory status` no probado (RAM baja); montos de coste por diseño |
| PCRick: nodo, túnel, gateway local, Worker, tareas, Tailscale, herramientas, repos, AUT-1/2, C23 (rutas y 2 archivos de evidencia), respaldos | **Verificado** | sesión PCRick, 05:36–05:39Z y 05:50Z | sin admin (VSS, Hyper-V); vigencia actual de la postura de permisos no verificada |
| TARRO: identidad, Tailscale, SSH, puertos, procesos, tareas, herramientas, 82 repos, Drive local, Worker, OpenClaw, .env (nombres), ops_log | **Verificado** | subagente, 05:35–05:40Z | VM Hyper-V sin elevación; procesos huérfanos no medidos |
| Notebook MSI | **No accesible** | — | sin sesión ni tailnet; solo REPORT por Drive del 05-nov |
| Notion: dashboard, ficha DIHR, 4 fichas dependencia, página UAS (98 k chars, 100 %), 2 alternativas de interfaz | **Verificado (lectura)** | MCP Notion, 05:25–05:40Z | ficha DIHR escrita a las 07:10Z (sección + propiedades) |
| Notion: Ops Resume (855 filas), Gobernanza, Dashboard Rick, búsquedas Mission Control / UAS-TESTIGO-01 | **Verificado (lectura)** | subagente MCP Notion, ≈07:40Z | Freshness por fila no consultable; DCS no existe en Notion |
| Drive | **Parcial** | subagente MCP Drive, ≈05:45–06:05Z: estructura, duplicados, permisos, 6 docs de coordinación | sin fullText; `_local-secrets` no abierta; PROTOCOLO-BASE no legible |
| Rick GPT (ChatGPT) | **Verificado (lectura)** + relevo | 41 turnos leídos; dos consultas y dos respuestas en el hilo | hoja conciliada recibida como texto pegado; sus anexos solo por resumen de Rick GPT |
| Ledger / macro-plan / acta / fichas / plan siete frentes (clone coordinador) | **Verificado** | lectura directa; hash del acta coincide | ledger sin eventos desde 4-nov |
| Comparativa Rick GPT/Grok y juez R1 | **Reportado por sesiones ejecutoras** | 2 REPORT, 05:45Z | contenido de casos no abierto (reserva) |
| GitHub | **Verificado** | gh CLI | — |
| n8n Cloud dmbutic | **Verificado (contexto)** | MCP n8n | no es runtime UAS |
| Slack | **Parcial** | canal #uas localizado; mensajes no leídos | — |
| Azure | **Parcial** | 3 suscripciones listadas | costos no consultados |
| Microsoft 365 / Outlook / SharePoint / Copilot | **No accesible** | sin conector en esta sesión | — |
| Linear, Supabase, Telegram | **No accesible** | MCP sin auth / fallo de conexión | — |
| Editorial, Granola, skills (instalación por host), Power Automate | **Parcial** | VPS-02 ítems 3–4 (editorial sin actividad; Granola con gaps); TARRO tareas Granola con error; skills y Power Automate solo por fuentes documentales | ejecución real de editorial y conciliación Granola no observadas |
| Mission Control UI | **Parcial** | código, unit, /health, /risks y /gates verificados; UI no abierta | requiere túnel SSH al 8089 del VPS (script documentado, no probado) |
| Revisión independiente | **Recibida** | subagente con instrucción de refutar; 15 hallazgos; veredicto APTO_CON_CORRECCIONES; correcciones mínimas aplicadas en este documento | evidencia/REVISION-INDEPENDIENTE-2026-11-09.md |

---

## D. Diagnóstico por componente

Cada ítem: hallazgo · evidencia · límite · gravedad (Alta/Media/Baja) · relación con la investigación (E).

**D.1 Gateway OpenClaw (VPS).** OOM cíclico por heap por defecto; RSS > heap indica memoria externa; restart deja ~1 min sin puerto que rompe la sesión del nodo. Evidencia: VPS-01 ítems 1 y 3 (journal «Ineffective mark-compacts… heap out of memory» 04:44:15Z; `systemctl show`; `v8.getHeapStatistics`). Límite: causa raíz de la fuga no identificada (upstream #115424 tampoco). **Alta.** E-P1.

**D.2 Canario.** Corre en `agent:main:main`; 34 fallos de 48 en 24 h (VPS-01 ítem 4, verificado). Reportado por la sesión VPS a las 00:51Z (leído en su pestaña, no incluido en evidencia/): 22 `chat.abort` a :03/:33 y 52 entradas pendientes del historial de David atribuibles al canario. **Alta.** E-P2.

**D.3 Memoria / embeddings.** Proveedor `auto` → openai sin clave; índice gemini 9 chunks (VPS-01 ítem 5, verificado). Reportado por la sesión PCRick en su tabla del 08-nov (leída en su pestaña): índice de memoria de PCRick con 0 fuentes y cron «Memory Dreaming» ejecutándose vacío. **Media.** E-P3.

**D.4 Conectividad.** Claves Tailscale caducadas (VPS 25-ago, TARRO 31-ago), servicio deshabilitado en TARRO; túnel SSH único; sin túnel inverso 22024; notebook fuera. Evidencia: VPS-01 ítem 6; PCRick-01 ítem 3; TARRO ítem 2. **Alta.** E-P4.

**D.5 Nodo PCRick y AUT.** Nodo único y emparejado desde ambos lados; AUT-1 vigente (cuarentena del .vbs de Startup 08-nov 01:49Z), prueba tras reinicio pendiente; AUT-2 no autorizado; auxiliares 17564/8512 fuera de alcance. **Baja** (sano) con riesgo abierto declarado por la sesión PCRick. 

**D.6 Worker y Dispatcher.** Tres Workers v0.4.0 (VPS, PCRick, TARRO). El de TARRO corre desde el clone `-codex` desactualizado y expuesto en 0.0.0.0; ops_log de TARRO sin eventos desde 06-nov 12:30Z. El de PCRick no recibe tráfico externo (desde 14-oct según su tabla del 08-nov). El del VPS responde; en 7 días 127.979 tareas (ver D.17). **Media.** E-P5/P11.

**D.7 Mission Control / dashboards.** Tres superficies distintas. (1) Mission Control: prototipo read-only en loopback del VPS; «banner synthetic» en PIT; datos: openclaw.json, colas Redis, quota; `/risks` y `/gates` responden. (2) «Dashboard Rick» en Notion (3265f443…): lo reescribe un cron horario del VPS (24 actualizaciones/0 fallos en 24 h, última 06:00Z) y hoy dice «Operativo» con cifras internamente inconsistentes (tareas hoy 4.565 vs 114 del Worker vs 4.954 completadas; 100 % éxito con 0 tokens trazados; «+1074 % vs ayer»), 727 tareas bloqueadas en Redis, 2 `research.web` «en ejecución» desde hace ≈186 días y sin distinción real/sintético (evidencia/notion-ops-resume-gobernanza-dashboard). (3) Tablero provisional de Notion mantenido a mano por Rick GPT/dot, con porcentajes subjetivos; su monitor (automatización ChatGPT) tiene prohibido escribir en Notion según Rick GPT. La contradicción «dashboard sano con 727 bloqueadas y un 502» que reportó Rick GPT el 7-nov sigue vigente hoy en el Dashboard Rick. **Alta** (vista de estado que induce a error). E-P5/P7.

**D.8 Coordinación y continuidad.** Ledger del programa sin versionar y detenido el 4-nov; página Notion UAS detenida el 5-oct; **Ops Resume (855 filas) sin proyección nueva desde el 17-sep 12:00Z** aunque Gobernanza y la página UAS declaran mantenimiento activo desde el 14-sep: coincide con la tarea programada `\Umbral\OpsResumeWriter` de TARRO fallando con código 0x2 cada 30 min (inventario TARRO ítem 6). La base DCS/Decisiones que citan Rick GPT y PR48 no existe en Notion (si existe, vive en repo o ledger). La página de Gobernanza (editada 7-nov sin entrada fechada posterior al 15-sep) afirma que Claude y Antigravity no tienen acceso a Notion, lo que esta misma lectura desmiente: matriz de actores desactualizada. Ficha 006 atrasada respecto al ensayo real; prompts pegables con David como transporte. Hoy: mensajería entre sesiones Claude funcionó para 6 paquetes; los dos primeros REPORT llegaron 5 y 9 minutos después de la emisión según sus propias horas (los `ts` del ledger DIHR son horas de escritura del coordinador). **Media.** E-P6/P7.

**D.9 Repos e higiene.** 72 clones en TARRO; coordinador en rama de laboratorio con 114 sucios; `-codex` (runtime del Worker TARRO) 15 detrás/49 sucios; `-claude` 16 detrás; PCRick 370 detrás; PRs draft antiguos (693 desde 14-sep, 709 desde 29-sep). Programa de higiene H2–H6 (jul) pendiente de GO. **Media.**

**D.10 Drive y fuentes canónicas.** Cuenta Gmail personal, owner único, sin unidades compartidas; HOJA-DE-RUTA.md ×4 versiones; ~30 snapshots del repo; secretos y estado de agentes en carpetas de cliente; carpeta de tercero con acceso por enlace. Ejemplo bueno de versionado: INDICE-MATERIALES v1.1/v1.2. **Media-alta** (acceso). E-P7/P10.

**D.11 Evaluación / comparativa.** Protocolo V3 (04-nov), banco sintético de 12 casos, 4 piezas de un pre-ensayo fuera de protocolo; R1 = regresión PARCIAL sin comparación; faltan sorteo, T0, trazas, aislamiento técnico. **Media.** E-P8.

**D.12 Costos y cuotas.** Reportado: reclamo Azure en curso con soporte Microsoft (correo de David, hilo Rick GPT turno 2: PDF con importe acumulado 4.280,24 USD vs «pagado» en portal; crédito ISV 5.000 USD); créditos API Anthropic diferidos por David hasta después del test comparativo (ficha Notion «OpenClaw y créditos Anthropic API», 5-nov). Verificado: quota-guard cada 15 min sin dejar estado; runtime-snapshot con coste 0 pese a 158 usos (VPS-02 ítem 6); el canario gasta una inferencia cada 30 min en el modelo principal (VPS-01 ítem 4). **Media.** E-P9.

**D.13 Respaldos, secretos y exposición.** VPS: snapshots SQLite manuales (último 7-nov), 1 backup_run fallido de 3, sin destino externo (VPS-01 ítem 8); `authorized_keys` con la clave `pcrick-openclaw` duplicada y ninguna clave con restricciones `from=`/`command=` (VPS-03 A4). PCRick: .bak locales, File History detenido, Documents (con C23) fuera de OneDrive; checkpoints Hyper-V NO PROBADOS hoy (según la ficha 006 del 12-sep había dos de febrero); **el archivo de entorno del Worker (`C:\openclaw-worker\openclaw-worker-service.env`, con WORKER_TOKEN, LINEAR_API_KEY, NOTION_API_KEY…) es legible por Usuarios y modificable por Authenticated Users** (PCRick-03 ítem 3); sshd 22 y Worker 8088 escuchan en 0.0.0.0 con reglas de firewall «Any» y las interfaces LAN están en perfil Public (PCRick-03 ítem 2); la política de aprobaciones del nodo es `security=full, ask=off`, por lo que `system.run` desde el VPS se ejecuta sin preguntar (VPS-03 A5); `config.toml` de Codex modificado hoy 03:52Z sin atribución y `.claude/settings.local.json` del clone con dos reglas nuevas para el conector Drive (atribuible por inferencia a la sesión del juez). TARRO: clave OpenSSH suelta (ED25519 SHA256:ZBeipjmQ…) que **no está autorizada en el VPS** (solo `david@TARRO` RSA y `pcrick-openclaw`): queda por comprobar PCRick y GitHub antes de destruirla; `env.rick-oauth.pending` (junio) con nombres de variables de refresh tokens de Google; `.env` de marzo con 21 entradas; rotación de la contraseña expuesta el 11-sep (ficha 006) no acreditada; Worker 8088 en 0.0.0.0 permitido por la regla de Spotify. PCRick: credencial de Grok Bot presente (no abierta). **Alta.** E-P10.

**D.14 Dependencia de TARRO y tareas locales rotas.** Host de PCRick, puesto de David, origen de 7 tareas programadas Umbral, 350 procesos MCP; si TARRO se apaga, caen PCRick, OpsResumeWriter, SkillsReceiver, GranolaDriveFeeder. Dos tareas fallan con causa verificada hoy: (1) `GranolaVmRawIntake` y su variante Startup (0x1): el script `granola_vm_raw_intake.py` del clone `-codex` busca `%APPDATA%\Granola\cache-v6.json` y la app Granola (activa desde 05-nov) ahora escribe `cache-v6.json.enc` cifrado (626 KB, 09-nov 03:33Z); la ingesta de transcripciones lleva al menos días sin correr, coherente con los «recent gaps» del VPS; (2) `\Umbral\OpsResumeWriter` (0x2 cada 30 min): la línea 112 del ledger `ledger-stack-roadmap-diag.jsonl` (17-sep 13:10Z, ACK de PKG-C23-GROK-ALUMNO) tiene una ruta de Windows con barras sin escapar; el lector estricto lanza `MALFORMED_JSON` y bloquea el ciclo completo; primer bloqueo 17-sep 13:30Z, 2.532 ciclos consecutivos hasta hoy; reproducido en seco con 0 escrituras; el motivo nunca llegó al log porque el wrapper lo manda a stderr y pythonw lo descarta. La proyección Ops Resume está detenida desde el 17-sep por una línea inválida de 237, no por decisión. Ambas tareas requieren un cambio pequeño (una línea del ledger ajeno; un PR para registrar el motivo) y despliegue local; detalle y alternativas en D12/D13 del archivo de decisiones. **Media-alta.** E-P11.

**D.15 Slack / n8n / Power Automate.** n8n Cloud dmbutic activo para relays Slack→Grok y Slack→Notion AI (piloto, ~40 versiones en un día); n8n VPS v2.10.2 con 2 workflows activos (B3 health→Telegram cada 15 min, B1 Telegram→/enqueue), 672 ejecuciones OK en 7 días; Power Automate aparece solo en C28 según la página Notion UAS (flujo desactivado tras el ejercicio); no se inventarió el tenant M365. Dos instancias n8n con propósitos distintos y sin duplicar disparadores: cumple Q08. **Baja.**

**D.16 Agentes OpenClaw y modelos.** 9 agentes en openclaw.json; modelo primario `openai/gpt-6.1-sol` en 7 de ellos y `gpt-6-luna` en 2, todos con 2 fallbacks (`anthropic/claude-sonnet-5-5`, `openai/gpt-6-luna`); un solo binding Telegram→main; heartbeat en 8 agentes (otra fuente de carga periódica sobre el gateway, ver P1/P2). Editorial sin cron ni unidad y 0 eventos en 7 días pese a `NOTION_POLLER_ENABLE_PROMOTE=true`; Granola con «recent gaps» (7 issues, última página 05-nov) y 0 eventos. **Media.**

**D.17 Carga del poller Notion y medición de coste.** 100.051 `notion.poll_comments` + 27.266 `notion.read_database` en 7 días (≈12 req/min sumadas, bajo el límite de 180 req/min por integración; sin 429 observados; poller con 0 fallos en 24 h); 17 fallos en total (8 tareas inexistentes, 5 respuestas HTML de Notion, 3 timeouts del proxy LLM, 1 Calendar sin auth). Es carga y ruido evitables, no saturación. `runtime-snapshot`: `llm_usage tracked=false`, coste 0 vs 158 usos reales (124 con proveedor atribuido); `quota-guard` corre sin dejar estado. Mission Control `/risks`: pip-audit high, env-acl medium, board-drift medium, stale-prs medium (needs_david_authorization), linkedin-autopublish high (blocked_by_policy); `/gates`: D6.1 blocked_source_repair, Gmail+Calendar ready, editorial hitl_required. **Media.** E-P7/P9.

---

## E. Investigación aplicada y alternativas

Informe completo con fuentes primarias (Node.js, systemd, OpenClaw docs e issue #115424, Tailscale KB, OTel GenAI, Langfuse, Notion API, OWASP, Microsoft Learn, Anthropic pricing): [`investigacion-estado-del-arte-2026-11-09.md`](investigacion-estado-del-arte-2026-11-09.md). Para cada problema P1–P11 hay 2–3 alternativas incluida «mejorar lo existente», beneficio, medición, costo, riesgo, esfuerzo y reversibilidad. Resumen:

| Problema | Recomendación provisional | Esfuerzo | Reversible |
|---|---|---|---|
| P1 Heap V8 | `NODE_OPTIONS` en unit + snapshot near-limit + `MemoryHigh/Max` + backoff | S | Sí |
| P2 Canario | sesión aislada, light-context, modelo barato, `NO_REPLY`; luego probe externo | S | Sí |
| P3 Embeddings | pin gemini + manifest del índice + reindex | S | Sí |
| P4 Conectividad | re-auth Tailscale con tag; túnel SSH endurecido; probe E2E con `trace_id` | S/M | Sí |
| P5 Observabilidad | `trace_id` único propagado + campos `gen_ai.*`; piloto Langfuse | S→M | Sí |
| P6 Coordinación | ledger con esquema + hooks ACK/REPORT; mensajería entre sesiones ya probada; luego MCP «UAS board» | S/M | Sí |
| P7 Memoria/Notion | un solo escritor con backoff; JSONL fuente, Notion proyección | S/M | Sí |
| P8 Evaluación | estados preparado/ejecutado/validado + evidencia obligatoria por prueba | S | Sí |
| P9 Costos | `modelPolicy.allow` + sin fallbacks + ledger de coste + alertas | S | Sí |
| P10 Respaldo/secretos | rotación inmediata; inventario RPO/RTO; restic con check y restore de prueba | M | Sí |
| P11 TARRO | estado en repo/VPS; runner headless piloto | S/M → M | Sí |

Lo que **no** se recomienda ahora: un orquestador nuevo, migrar a otra plataforma de agentes, o seguir ampliando Mission Control antes de tener `trace_id` y datos reales.

---

## F. Hoja de ruta priorizada

Separa **reparación** (restaurar lo que ya existía), **validación operativa** (probar que el circuito funciona) y **evolución** (mejoras). Costo indicado por paquete: «0» = trabajo de agentes en cuentas y servidores existentes; cualquier gasto nuevo se señala y queda sujeto a Q07 (consultar antes de gastar).

| Fase | Paquete | Depende de | Responsable propuesto | Costo | Aceptación | Reversible |
|---|---|---|---|---|---|---|
| **R0 (hoy)** | R0.1 D2 canario aislado · R0.2 D1 paso 1 (sesión main compactada) · R0.3 D3 embeddings gemini · R0.4 D1 paso 2 solo si R0.2 no corta el ciclo | aprobación D1–D3 | sesión «UAS - VPS» (operador único, aviso previo) + PR en `rick/` para el canario | 0 | canario < 5 % fallos en 24 h; `memory status` con fuentes > 0; 24 h sin OOM o snapshot capturado | sí (minutos) |
| **R1 (esta semana)** | R1.1 prueba E2E VPS→PCRick→Worker→retorno por el nodo OpenClaw con `UAS-E2E-<UTC>-<hex>` (ya diseñada; no requiere Tailscale) · R1.2 D4 Tailscale VPS+TARRO · R1.3 túnel SSH endurecido (keepalives, `ExitOnForwardFailure`, backoff) | R1.1: gateway con < 3 h desde reinicio y PCRick conectado; R1.2: login de David; R1.3: ninguna | VPS ejecuta; PCRick observa; coordinador registra | 0 | R1.1: ID en 4 trazas, /health y /run 200, < 30 s, una sola ejecución; R1.2: 3 nodos online sin expiry | sí |
| **R2** | R2.1 D7 rotación de secretos, clave suelta y cierre de puertos · R2.2 inventario de respaldos (qué/dónde/RPO/RTO) + restic a destino externo + restauración de prueba · R2.3 inventario de checkpoints Hyper-V con elevación; limpieza solo si el inventario los confirma, con export previo | D7; R2.3 además requiere elevación en TARRO | TARRO (David para elevación) + VPS | R2.1 0 · R2.2 **almacenamiento externo nuevo** (Hostinger/Azure Blob/otro: precio por confirmar; alternativa 0: disco local de TARRO como destino inicial) · R2.3 0 | lista fechada de secretos rotados; restore de prueba OK; checkpoints inventariados | sí |
| **V1 (validación)** | V1.1 dos encargos reales cerrados y reanudables (Q10): candidatos C23 cierre de alumno (evidencia ya localizada) e Interoperabilidad AEC (#5 de la cartera) · V1.2 reingreso tras pausa 24–48 h | R0, R1.1 | Rick/Grok owner por encargo; Codex/Claude ejecutan; revisor distinto | 0 | resultado recuperable en Notion con evidencia; reanudación sin repetir efectos | — |
| **V2** | V2.1 comparativa inédita (D6 a–d) con sorteo, T0, trazas, aislamiento | D6 | sesión preparadora PCRick + juez fresco; coordinación en Slack #uas | 0 (si se exige cuenta Drive separada para el juez: cuenta adicional, coste por confirmar) | bloques comparables, trazas por pieza, C3 con salida | — |
| **E1 (evolución)** | E1.1 `trace_id` propagado (Worker, Dispatcher, ops_log, ledgers, Notion) · E1.2 ledger JSONL con esquema + hooks ACK/REPORT · E1.3 un solo escritor Notion con backoff; **decisión de David:** si el monitor de Rick GPT sigue sin escribir y la ficha la escribe otro actor, o si se levanta esa restricción (no se elude) | R0 | Codex (Worker/Dispatcher), Claude Code (hooks), escritor de notion-governance (Codex) | 0 | una corrida E2E reconstruible solo por id; 0 bloqueos de escritura en 7 días | sí |
| **E2** | E2.1 Mission Control alcanzable por tailnet (Tailscale Serve, no Funnel) leyendo `trace_id` y marcando real/sintético · E2.2 higiene de repos H2–H6 (GO pendiente desde julio) · E2.3 estado de coordinación en VPS/repo para que TARRO sea un cliente más · E2.4 runner headless piloto **en el VPS** (no en PCRick, que depende de TARRO) | E1, R1.2 | Codex + Claude | E2.1–E2.3 0 · E2.4 **uso de API facturable** (clave API, no suscripción): presupuesto por fijar antes | E2.1: bitácora manual de aperturas ≥2/día durante 2 semanas (el middleware de vistas de MC aún no existe); E2.2: ≤ 5 clones por repo; E2.3/E2.4: un ciclo paquete→REPORT→Notion con TARRO apagado | parcial |
| **E3 (opcional)** | piloto Langfuse autoalojado; MCP «UAS board»; `gemini-embedding-2` | E1 | — | Langfuse autoalojado: RAM adicional en VPS o servidor aparte (coste por confirmar); embeddings: reindex con API Gemini | según E | sí |

Prioridad de valor para David: R0 y R1.1 devuelven a Rick y prueban el circuito con < 1 día de trabajo y cero gasto; V1 cumple Q10 (confianza por resultado); E1 elimina el rol de mensajero.

---

## G. Plan de pruebas de aceptación

| Prueba | Entradas | Criterio | Evidencia requerida | Quién |
|---|---|---|---|---|
| G1 Gateway estable | drop-in aplicado; 24 h | 0 OOM o 1 snapshot `.heapsnapshot` escrito; NRestarts sin cambio | `systemctl show`, journal, ls del snapshot | VPS |
| G2 Canario aislado | 48 ticks (24 h) | fallos < 5 %; 0 `chat.abort` en sesión main a :03/:33; historial de David sin entradas del canario | ops_log, `openclaw sessions` | VPS |
| G3 Memoria | reindex | `memory status`: provider gemini, fuentes > 0; 1 recuperación conocida acierta | salida CLI | VPS |
| G4 Tailnet | re-auth | `tailscale status` muestra VPS, TARRO, PCRick online; claves sin expiry | salida en los 3 equipos | David + VPS + TARRO |
| G5 E2E | ID único | ID en journal VPS, log nodo PCRick, log Worker PCRick, registro privado VPS; `/run ping` eco exacto; < 30 s | 4 recibos | VPS/PCRick |
| G6 Secretos | lista | cada secreto expuesto rotado con fecha; clave suelta retirada; `.env` sin claves muertas | lista fechada (sin valores) | David/TARRO |
| G7 Respaldo | restic | `restic check --read-data-subset 1/10` OK; restauración de prueba de main.sqlite abre | logs | VPS |
| G8 Encargo real | Q10 | resultado en Notion con evidencia y reanudación tras pausa | ficha + ledger | owner del encargo |
| G9 Comparativa | D6 | bloques con 2 candidatos, T0, trazas; juez sin ver identidades | paquete + informe | preparador + juez |
| G10 Observabilidad | E1 | corrida reconstruida por `trace_id` desde 4 fuentes | consulta | coordinador |
| G11 TARRO apagado | E2.3 + E2.4 (runner en VPS) | ciclo paquete→REPORT→Notion sin TARRO ni PCRick encendidos | ledger | coordinador |

---

## H. Cambios realmente efectuados y verificaciones

**Cambios en sistemas productivos (corte 2, aprobados por David, opción B):** en el VPS, `~/.openclaw/openclaw.json` recibió el patch de memoria Gemini a las 14:33Z (sha f44ce55e…) y fue **revertido byte a byte a las 14:52Z** (sha ccc40458… = original) tras comprobar que la clave de Google no es válida para Gemini; respaldos en `~/dihr-staging/` (openclaw.json.bak-20261109T143308Z, canary-inference.sh.bak-20261109T143241Z). El script del canario desplegado no cambió en ese corte (release inmutable). **Corte 4 (15:06–15:50Z, opción A de David):** release nueva 49404b9 activa (D2), drop-in del gateway instalado y un reinicio controlado de 97,6 s (D1 paso 2); `openclaw.json` sin cambios; cron, Tailscale, firewall, puertos, permisos y credenciales intactos; respaldos de `openclaw.json` y de la unit en `~/dihr-staging/`. Reversiones: `release-deploy.sh --rollback`; borrar `override.conf` + daemon-reload + restart. Fuera del VPS: PR borrador #711 en GitHub (rama `claude/dihr-canary-session-aislada`), ficha DIHR en Notion (secciones de corte y propiedades), archivos de esta carpeta. **Corte 1 (05:21–07:10Z): ningún cambio.** VPS, PCRick, TARRO, Notion, Drive, Slack, n8n, GitHub remoto: solo lecturas. Los hilos ejecutores declararon lo mismo en sus REPORT (archivos temporales en scratchpad, borrados o reutilizados). Fuera de esta coordinación y antes de ella, la sesión «Auditoría de comparativa ciega» reportó haber creado hoy a las 03:01Z 15 archivos y 1 carpeta en Drive (paquete R1 del juez); no es un cambio de esta sesión y se registra por completitud.

Efectuado por esta sesión:
- Carpeta de trabajo `docs/operations/dihr-uas-2026-11-09/` en el clone `-claude` (sin commit): este documento, `ESTADO.md`, `ledger-dihr-uas.jsonl` (eventos EMITIDO/ACK/REPORTADO con msg_id; `ts` = hora de escritura), `investigacion-estado-del-arte-2026-11-09.md`, `evidencia/` (REPORT VPS-01/02, PCRick-01/02, JUEZ-01, COMPARATIVA-01, inventarios TARRO, integraciones y Drive, digest Notion UAS, relevo y hoja conciliada de Rick GPT, revisión independiente).
- Mensajes enviados: 6 paquetes a sesiones Claude (VPS-01/02, PCRick-01/02, JUEZ-01, COMPARATIVA-01) y 3 mensajes `[Claude Code]` en el hilo Rick GPT; 4 acuses de recibo. Ningún correo, Slack ni publicación.
- Verificaciones propias: hash del acta de entrevista; coherencia cruzada VPS↔PCRick (nodo único desde ambos lados; caducidad Tailscale vista desde PCRick y NeedsLogin en VPS; la relación «Connection refused»↔OOM queda como hipótesis: 10 vs 7 eventos, una coincidencia horaria); existencia y estado de la unit mission-control; redacción de identificadores sensibles en el paquete tras la revisión.

---

## I. Preguntas delta y prompt para lo bloqueado

Las únicas decisiones necesarias son D1–D10 (A.2). No se repiten Q01–Q12.

**Tarea realmente bloqueada:** inventario, runtime y conectividad del **notebook MSI**. Ninguna sesión de esta coordinación lo alcanza; el único canal es el puente Drive operado por Codex MSI vía Rick GPT/dot. Prompt para ese canal (ficha fuera del bloque; David decide IDE/modelo):

Hilo: puente Drive «Puente TARRO-MSI» (inbox) · Destinatario: Codex en notebook MSI · Encargo: PKG-DIHR-MSI-01, inventario de solo lectura · Sugerido: Codex app + modelo de su selector

```text
Ejecuta en solo lectura en el notebook MSI y deja el resultado en outbox como REPORT con MANIFEST, EVIDENCE y READY. Abre con ACK PKG-DIHR-MSI-01 y cierra con REPORT PKG-DIHR-MSI-01. Sin cambios de configuración, credenciales, Tailscale, firewall ni servicios; sin secretos (solo nombres de variables). Entrega con hora UTC y comando por ítem: identidad del equipo y uptime; tailscale status e ip; alias de ssh config (solo Host y HostName) y hosts de known_hosts; puertos en escucha con proceso; tareas programadas que mencionen umbral, uas, openclaw, rick, codex o claude con último resultado; versiones de claude, codex, gh, node, python, git, openclaw; clones git bajo el directorio de trabajo con rama, último commit, sucios y ahead/behind; existencia de Worker local y respuesta de GET /health en 8088; archivos .env con solo nombres de variables; última línea de ops_log si existe. Termina con la lista de lo que no pudiste verificar y por qué.
```

---

## J. Fuentes, fechas, rutas y recibos

| Fuente | Ruta / URL | Fecha del hecho | Fecha de lectura |
|---|---|---|---|
| Encargo DIHR (prompt de David redactado con Rick GPT) | hilo ChatGPT «Rick GPT» dots/8e101007… turnos 31–33 | 09-nov ~02:5x Chile | 09-nov 05:2x UTC |
| Acta entrevista | `C:\GitHub\umbral-agent-stack\docs\operations\decisiones-entrevista-2026-09-11.md` (SHA-256 85c9e86f…) | 11/13-sep | 05:30Z |
| Ledger programa | `…\docs\operations\ledger-stack-roadmap-diag.jsonl` (238 líneas) | hasta 04-nov | 05:33Z |
| Macro-plan, plan siete frentes, ficha 006 | mismo directorio y `.agents/tasks/2026-09-11-006-clase23-aec4-v2.md` | ago–nov | 05:33Z |
| Notion ficha DIHR / dashboard / UAS / 4 fichas / 2 alternativas | URLs en cabecera y evidencia/notion-uas-digest.md | 03-nov → 09-nov 01:07Z | 05:25–05:40Z |
| REPORT VPS-01 | evidencia/REPORT-PKG-DIHR-VPS-01.md (msg_id 79c435db…) | 05:35–05:38Z | 05:40Z |
| REPORT PCRick-01 | evidencia/REPORT-PKG-DIHR-PCRICK-01.md (msg_id 1f821c93…) | 05:36–05:39Z | 05:47Z |
| REPORT JUEZ-01 / COMPARATIVA-01 | evidencia/… (msg_id 85afbbbc…, 379d6703…) | 09-nov 03:01–04:15Z (hechos) | 05:45Z |
| Inventario TARRO | evidencia/inventario-TARRO-2026-11-09.md | 05:35–05:40Z | — |
| Inventario Drive | evidencia/inventario-drive-2026-11-09.md | ≈05:45–06:05Z | — |
| Inventario integraciones | evidencia/inventario-integraciones-2026-11-09.md | 05:55Z | — |
| Relevo Rick GPT | evidencia/RELEVO-RICK-GPT-2026-11-09.md | 09-nov 02:38 Chile | 06:10Z |
| Investigación | investigacion-estado-del-arte-2026-11-09.md (URLs dentro) | web 09-nov | — |
| Código Mission Control | `mission_control/README.md`, `docs/adr/ADR-009-mission-control-scope.md` | 04-may | 05:50Z |
| GitHub | `gh pr list` Umbral-Bot/umbral-agent-stack y notion-governance | — | 05:52Z |
| Ledger DIHR | ledger-dihr-uas.jsonl | — | — |

| REPORT PCRick-02 (C23) | evidencia/REPORT-PKG-DIHR-PCRICK-02.md (msg_id 299be87d…) | 17-sep (hechos), 05:50Z (lectura) | 06:20Z |
| REPORT VPS-02 | evidencia/REPORT-PKG-DIHR-VPS-02.md (msg_id 7745e2b2…) | 05:50–05:53Z | 06:22Z |

| Hoja conciliada de Rick GPT (texto íntegro) + conclusiones de 2 anexos | evidencia/HOJA-CONCILIADA-RICK-GPT-2026-11-09.md | 09-nov (elaboración), 08-nov (anexos) | 06:30Z |
| Revisión independiente (refutación) | evidencia/REVISION-INDEPENDIENTE-2026-11-09.md | 06:55Z | 06:55Z |
| Digest Notion UAS | evidencia/notion-uas-digest.md (escrito 06:50Z a partir del informe del subagente; el revisor lo leyó antes de que existiera) | 05-oct (página) | 05:40Z |

La hoja conciliada de Rick GPT coincide con este diagnóstico en alcance, decisiones vigentes (con la corrección de Q05), estado de C23 y recomendación «fortalecer el stack existente»; difiere en que no asigna porcentaje. Sus anexos del 8-nov (continuidad/conectividad y PR48) son anteriores a las lecturas de hoy y quedan conciliados: AUT-1 ahora confirmado desde el VPS; PR48 sigue draft.

---

## K. Avance del frente (criterio fijado antes de calcular)

Avance **documental** del 100 % definido en la ficha (diagnóstico + investigación + entrevista + propuestas + hoja de ruta + revisión), no salud operativa. Componentes y pesos fijados antes de puntuar (registrados también en `ledger-dihr-uas.jsonl`, evento DIHR-K-PESOS). Se muestran tres columnas: la puntuación del coordinador antes de la revisión, la del revisor independiente, y la del coordinador tras aplicar las correcciones mínimas.

| Componente | Peso | Coord. previo | Revisor | Tras correcciones | Base de la puntuación final |
|---|---|---|---|---|---|
| Inventario y mapa | 15 | 80 | 65 | 75 → 11,25 | 18 ámbitos en C: 11 verificados (incl. Ops Resume, Gobernanza, Dashboard Rick, PCRick permisos/exposición), 4 parciales, 3 no accesibles (MSI, M365, Linear/Supabase/Telegram) |
| Diagnóstico verificable con cobertura | 25 | 75 | 60 | 72 → 18,0 | las tres causas de Rick verificadas dos veces (OOM #8, canario↔abort 25/25, memory.search ausente); red, nodo, MC, poller, C23 (PBIX en TARRO), Granola y OpsResumeWriter con causa; MSI, skills por host y vigencia de permisos PCRick pendientes |
| Investigación aplicada | 10 | 80 | 75 | 75 → 7,5 | 11 problemas con fuentes primarias; clave de configuración confirmada (`memory.search`) |
| Entrevista y decisiones incorporadas | 10 | 90 | 85 | 85 → 8,5 | acta verificada por hash; decisiones posteriores al 11-sep solo por relevo de Rick GPT |
| Propuestas y alternativas | 15 | 70 | 55 | 72 → 10,8 | D1–D11 con alternativas y consecuencias (archivo propio); staging verificado en VPS y PCRick; parche D2 con flag real; reversión en todas |
| Hoja de ruta priorizada | 15 | 60 | 45 | 60 → 9,0 | costos por paquete, dependencias corregidas, pruebas con comandos; pendiente de decisiones de David y de precios de almacenamiento externo |
| Revisión independiente | 10 | 0 | 50 | 70 → 7,0 | recibida y aplicada sobre el primer corte; el material añadido en la continuación (VPS-03, PCRick-03, Notion, Granola, OpsResume) no tiene segunda pasada del revisor |
| **Total** | 100 | 67 | 61 | **72 %** | avance documental; no salud operativa |

Salud operativa, aparte: Rick VPS **degradado**; ruta privada **caída**; E2E **no probado**; PCRick **sano**; Mission Control **no alcanzable**.
