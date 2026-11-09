<!-- Informe íntegro del subagente de investigación (sesión coordinadora local_815b91f1). Consulta web 9-nov-2026. [P] fuente primaria leída, [S] secundaria, [O] opinión/inferencia. No ejecutó nada local. -->

# Estado del arte aplicado a UAS (consulta web: 9-nov-2026)

## P1. Heap V8 agotado en el gateway (reinicio cada 8–9 h)

**Fuentes**
- [P] Node.js CLI: `--heapsnapshot-near-heap-limit=N` (ya no experimental desde v24.13.1/v25.4.0) escribe snapshot al acercarse al límite; `--heapsnapshot-signal=SIGUSR2`; `--heap-prof` estable. https://nodejs.org/api/cli.html
- [P] Node.js «Understanding and tuning memory»: `--max-old-space-size` limita Old Space; el límite por defecto depende de la RAM (`v8.getHeapStatistics().heap_size_limit`). https://nodejs.org/en/learn/diagnostics/memory/understanding-and-tuning-memory
- [P] systemd.service: `Restart=on-failure`; `RestartSec` + `RestartSteps` + `RestartMaxDelaySec` dan backoff; `OOMPolicy=`; `WatchdogSec` requiere `sd_notify(WATCHDOG=1)`. https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
- [P] systemd.resource-control: usar `MemoryHigh=` como mecanismo principal y `MemoryMax=` como última defensa. https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html
- [P] OpenClaw issue #115424 (cerrado 24-oct-2026, contención en v2026.10.4): OOM en turno de sesión principal + bucle de recuperación; un drop-in de systemd con `Environment=NODE_OPTIONS` había borrado silenciosamente `--max-old-space-size`; pico en `JSON.parse` (~3,3 GB). Causa raíz del crecimiento no identificada. https://github.com/openclaw/openclaw/issues/115424
- [S] Issues relacionados (no leídos en detalle): #58802 `SessionManager.fileEntries` sin poda; #51097 `sessions.json` entero en RAM; #91588 RSS 350 MB → 15 GB.

**Lectura de la evidencia** [O]: el límite de ~2,0–2,2 GB es el defecto de V8 sin flag (confirmado por la sesión VPS: sin `--max-old-space-size` ni `NODE_OPTIONS`, defecto 2.240 MB). RSS 4,4–5,2 GB > heap 2 GB indica memoria externa al heap (buffers, SQLite, nativo); subir el heap no resuelve eso por sí solo.

| | A. Mejorar lo existente | B. Reciclado programado | C. Separar procesos |
|---|---|---|---|
| Qué | Fijar `NODE_OPTIONS` en la unit (verificar `systemctl --user cat`), `--max-old-space-size` acorde a RAM, `--heapsnapshot-near-heap-limit=1`, `MemoryHigh/Max`, `RestartSec+RestartSteps`, versión ≥2026.10.4 (ya 2026.10.10), compactar/`/new` la sesión principal, sacar el canario (P2) | Timer systemd que reinicia en hora valle antes de las 8 h | Gateway en host/contenedor dedicado; memoria/embeddings en proceso aparte |
| Beneficio | Ataca causa probable + da evidencia (snapshot) | Elimina cortes en horario útil | Aísla fallos |
| Medición | `heap_used/heap_limit` cada 5 min a `ops_log`; MTBF; cortes por hora desde reinicio | Cortes en horario activo | Idem A |
| Costo/incertidumbre | Bajo; snapshot usa RAM extra | Nulo; trata el síntoma | Hosting adicional |
| Esfuerzo / Reversible | S / sí | S / sí | L / parcial |

**Recomendación provisional:** A ahora, B como red de seguridad una semana. Confirma: el snapshot muestra transcripts/`fileEntries` dominando y la pendiente de heap baja tras compactar sesión y mover el canario. Refuta: crecimiento idéntico con sesión nueva y sin canario → leak en otra ruta (issue upstream con snapshot).

## P2. Canario de inferencia dentro de la sesión de Telegram

**Fuentes**
- [P] OpenClaw automation payloads: estilos `main | current | isolated | session:<id>`; `isolated` no lee ni escribe el historial; `--light-context`; `--model` y `--fallbacks ""`; `--timeout-seconds`; responder `NO_REPLY` no publica nada; «si el chequeo puede decidir que no hay nada que hacer, use un condition trigger o script payload para que las corridas sanas se salten el modelo». https://docs.openclaw.ai/automation/cron-jobs/payloads
- [P] OpenClaw heartbeat: migra a automation jobs (`openclaw doctor --fix`); políticas `idleOnly` y `activeHours`. https://docs.openclaw.ai/gateway/heartbeat
- [S] Patrón blackbox: Prometheus Blackbox Exporter, Cloudprober.

**Alternativas**
- A. Mejorar: job `--session isolated`, `--light-context`, modelo barato (clase Haiku), `--fallbacks ""`, entrega `none`, `NO_REPLY` si sano, `idleOnly`. Esfuerzo S, reversible. Medición: tasa de fallo y p95 del canario; longitud del transcript principal.
- B. Externalizar: script payload o cron de sistema que hace `GET /health` + inferencia mínima vía API directa del proveedor (fuera del gateway) y escribe `probe_success` + latencia en `ops_log`. S/M.
- C. Sin inferencia: solo health HTTP + `WatchdogSec` (requiere `sd_notify`; no verificado en OpenClaw). S.

**Recomendación:** A hoy, B esta semana. Confirma: fallos bajan de 70 % a <5 % y los cortes de P1 dejan de correlacionar con :00/:30. Refuta: siguen timeouts aislados → proveedor/red.

## P3. Embeddings: proveedor OpenAI sin clave, índice construido con Gemini

**Fuentes**
- [P] OpenClaw memory search: usa OpenAI por defecto; con `provider` no fijado o `"auto"` cae a palabras clave si falla; con proveedor explícito que devuelve mala autenticación, `memory_search` reporta unavailable; si las dimensiones no coinciden, `openclaw memory index --force --agent <id>`; `provider: "none"` = fts-only. https://docs.openclaw.ai/concepts/memory-search
- [P] Google: `gemini-embedding-001` (estable) y `gemini-embedding-2` (abr-2026); espacios incompatibles → migrar exige re-embeber; `output_dimensionality` 128–3072. https://aistudio.google.com/docs/embeddings

**Lectura** [O]: la sesión VPS confirmó `agents.defaults.memorySearch` no definido (auto) y el runtime eligiendo openai; el índice tiene provider gemini, 9 chunks. Hay desajuste entre config y runtime; verificar override por agente.

**Alternativas**
- A. Pin: `memory.search.provider: "gemini"`, modelo `gemini-embedding-001`, dimensiones iguales al índice; manifest del índice (modelo, dims, fecha, nº fragmentos) validado al arrancar; `memory index --force` si difiere. S, reversible.
- B. Migrar a `gemini-embedding-2` con reindexado completo. M.
- C. Local (Ollama/GGUF): elimina clave; calidad y CPU inciertas con el VPS ya en presión de RAM. M.

**Recomendación:** A. Confirma: `openclaw memory status` muestra gemini, fuentes>0, fragmentos>0 y una recuperación conocida acierta. Refuta: sigue vacío → índice corrupto o scope cerrado.

## P4. Conectividad VPS ↔ PCRick (Tailscale caído, túnel SSH único)

**Fuentes**
- [P] Tailscale key expiry: 180 días por defecto; «Disable Key Expiry» por dispositivo; dispositivos con tags nacen sin expiry; renovar con `tailscale up --force-reauth` (no desde la propia sesión remota). https://tailscale.com/kb/1028/key-expiry
- [P] Tailscale SSH: servidor solo Linux/macOS; Windows solo cliente; ACL `ssh` con `action: check`. https://tailscale.com/kb/1193/tailscale-ssh
- [P] Tailscale Funnel (beta, ene-2026): solo 443/8443/10000, ancho de banda limitado. https://tailscale.com/kb/1223/funnel
- [P] OpenClaw nodes: patrón recomendado «Remote gateway via SSH tunnel (loopback bind)». https://docs.openclaw.ai/nodes
- [P] Microsoft Learn: OpenSSH Server en Windows 10/11 vía Optional Features. https://learn.microsoft.com/windows-server/administration/openssh/openssh_install_firstuse
- [S] Túnel resiliente: `ServerAliveInterval/CountMax`, `ExitOnForwardFailure=yes`, `Restart=always`, `StartLimitIntervalSec=0`, autossh `-M 0`.

**Evidencia local cruzada:** claves caducadas del VPS (2026-08-25) y TARRO (2026-08-31) según PCRick; VPS en `NeedsLogin`; TARRO con servicio Tailscale deshabilitado.

**Alternativas**
- A. Mejorar: re-autenticar Tailscale en VPS (y TARRO) con tag (expiry off) y endurecer el túnel SSH (keepalives, `ExitOnForwardFailure`, backoff). S, reversible. **Requiere aprobación de David (cambio VPN).**
- B. Tailnet directo: gateway escucha en IP Tailscale; nodo PCRick sin túnel; ACL VPS↔PCRick; SSH a PCRick con OpenSSH Server por tailnet. M, reversible (túnel como respaldo).
- C. Probe E2E: job aislado VPS → `node.invoke` PCRick → `ping` del Worker → retorno, con `trace_id`, cada 30 min. S.

**Recomendación:** A + C ya; B después. Confirma: éxito del probe >99 % en 48 h incluyendo un reinicio del gateway; reconexión del nodo <60 s.

## P5. Observabilidad: recibos dispersos sin correlación

**Fuentes**
- [P] OTel GenAI semantic conventions: spans `invoke_agent`, `create_agent`; atributos `gen_ai.operation.name`, `gen_ai.provider.name`, `gen_ai.agent.name`, `gen_ai.conversation.id`; estado Development. https://github.com/open-telemetry/semantic-conventions-genai (docs/gen-ai/gen-ai-agent-spans.md)
- [P] Langfuse data model: traces/observations/sessions; sobre OTel; autoalojable. https://langfuse.com/docs/observability/data-model
- [P] OpenAI Agents SDK tracing: `group_id`; `set_trace_processors`. https://openai.github.io/openai-agents-python/tracing/
- [P] Claude Code hooks: `PreToolUse`, `PostToolUse`, `SubagentStart/Stop`, `TaskCreated/Completed`, `Stop`, `SessionStart/End`. https://code.claude.com/docs/en/hooks

**Alternativas**
- A. Mejorar: un `trace_id` único (32 hex) por paquete/corrida, propagado en `ops_log.jsonl`, ledgers, cabecera `X-Trace-Id` del Worker/Dispatcher, campo en Notion y en la salida del canario; nombres alineados a `gen_ai.*`. S, reversible.
- B. Sink único: Langfuse (autoalojado o nube) recibiendo OTLP del Worker y recibos de hooks. M; añade servicio al VPS (atención RAM).
- C. Stack completo (Collector + Prometheus + Grafana + Loki). L.
- [O] Mission Control: no seguir construyendo prototipo hasta que exista A; el dashboard debe leer el mismo `trace_id`.

**Recomendación:** A ahora, B piloto. Confirma: reconstruir una corrida E2E (P4-C) desde 4 recibos distintos solo por id.

## P6. Coordinación humana costosa (David como mensajero)

**Fuentes**
- [P] Claude Code subagents/hooks; Agent SDK: sesiones, hooks, subagentes, MCP, permisos; headless `claude -p --output-format json`; terceros no pueden usar login claude.ai en agentes del SDK → clave API. https://code.claude.com/docs/en/agent-sdk/overview
- [P] MCP spec 2026-07-28: requests sin estado, extensiones Tasks (operaciones largas con durable handles) y Skills over MCP. https://modelcontextprotocol.io/specification/latest
- [P] Managed Agents (beta, `managed-agents-2026-04-01`). https://platform.claude.com/docs/en/managed-agents/overview (no leída completa)

**Alternativas**
- A. Mejorar el protocolo PKG: ledgers JSONL con esquema fijo (id, estado, `trace_id`, pruebas ya hechas); hooks `Stop`/`SubagentStop` que escriben ACK/REPORT automáticamente; registro de pruebas por id para no repetirlas. S/M, reversible. **Evidencia de hoy:** la mensajería entre sesiones Claude (SendMessage/cross-session) ya eliminó el pegado manual para 4 paquetes en esta sesión.
- B. Servidor MCP «UAS board»: tareas/ledger/pruebas como tools/resources legibles por Claude Code, Codex y Cursor. M.
- C. Orquestador headless (Agent SDK/Managed Agents). L; coste API.

**Recomendación:** A, luego B. Confirma: nº de pegados manuales por paquete y nº de pruebas repetidas caen.

## P7. Memoria y continuidad; bloqueos de escritura en Notion

**Fuentes**
- [P] Notion API límites: 180 req/min por integración, ~3 rps por data source, 429 con `Retry-After`, 529 reintentable, 500 KB/1.000 bloques por payload. https://developers.notion.com/reference/request-limits
- [P] OpenClaw memoria: Markdown es la fuente, índice derivado. https://docs.openclaw.ai/concepts/memory

**Alternativas**
- A. Mejorar: fuente de verdad = JSONL en repo; Notion es proyección escrita por un solo escritor con backoff según `Retry-After` y cola; cada resumen lleva hash/ids de las fuentes; el monitor del tablero usa la misma cola. S/M, reversible.
- B. Memoria del agente pinneada (P3) + notas diarias indexadas; Notion solo lectura humana. S.
- C. Sesiones Langfuse como memoria operativa (si P5-B). M.

**Recomendación:** A + B. Confirma: 0 bloqueos del monitor en 7 días; divergencia resumen↔fuente detectable por hash.

## P8. Evaluación (comparativas ciegas, simulado vs real)

**Fuentes**
- [P] LangSmith: `evaluate_comparative` pairwise; LLM-as-judge; datasets + experiments. https://docs.smith.langchain.com/how_to_guides/evaluation/evaluate_pairwise

**Alternativas**
- A. Mejorar: cada prueba en un archivo con `criterios_aceptacion`, `estado ∈ {preparado, ejecutado, validado}`, `evidencia` (ruta/`trace_id`), `entorno real|simulado`; un paquete ciego solo se emite si el checklist está completo. S, reversible. **Evidencia de hoy:** el juez R1 reportó exactamente estas carencias (sin run_id, T0, trazas, pares comparables).
- B. Plataforma (Langfuse o LangSmith) para datasets, experimentos y juicio pairwise. M.
- C. Harness propio en el Worker. M.

**Recomendación:** A; B solo si P5-B se adopta.

## P9. Costos y cuotas

**Fuentes**
- [P] Anthropic pricing (9-nov-2026): Fable 5.1 $10/$50 por MTok; Opus 5.5 $4/$20; Sonnet 5.5 $2/$10; Haiku 5.5 $0,10/$0,50; modelos ≥4.7 usan tokenizador ~30 % más tokens. https://platform.claude.com/docs/en/about-claude/pricing
- [S] Cambio de facturación del Agent SDK/`claude -p` pausado el 15-jun-2026; estado actual no verificado.
- [P] OpenClaw: `--fallbacks ""` y `modelPolicy.allow` acotan modelos por job.

**Alternativas**
- A. `modelPolicy.allow` por agente y `--fallbacks ""` en jobs; ledger de coste por proveedor/modelo/`trace_id`; canario y tareas de bajo valor en clase Haiku/local; cache de prompt. S.
- B. Consolidar proveedores. M.
- C. Presupuesto duro (alertas de gasto en cada consola). S.

**Recomendación:** A + C. Confirma: 0 llamadas de pago no autorizadas en 30 días.

## P10. Respaldo, recuperación y rotación de secretos

**Fuentes**
- [P] restic: `check`, `--read-data-subset n/t`. https://restic.readthedocs.io/en/stable/045_working_with_repos.html
- [P] Microsoft Learn: checkpoint estándar no es respaldo completo; producción usa VSS; exportar checkpoints sirve como backup. https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/checkpoints
- [P] OWASP Secrets Management: ante exposición, revocar de inmediato, rotar, eliminar del sistema expuesto incluidos código y logs. https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html

**Evidencia local:** VPS con snapshots SQLite manuales (último 7-nov) y sin respaldo programado ni externo; PCRick con .bak locales, File History detenido, Documents sin OneDrive; TARRO con clave privada SSH suelta en `C:\Users\david\openclaw` y una exposición histórica de contraseña (ficha 006, 11-sep) con rotación pendiente.

**Alternativas**
- A. Inventario (qué/dónde/RPO/RTO) en repo; restic cifrado a destino externo con check parcial semanal y restauración de prueba mensual; limpiar checkpoints antiguos y exportar la VM; ejecutar la rotación pendiente ahora con lista fechada. M, reversible.
- B. Snapshots del hosting + almacenamiento en nube (Hostinger/Azure Blob). S/M; coste y retención no verificados.
- C. Ensayo DR completo. M/L.

**Recomendación:** A (rotación primero; es incidente abierto, no pendiente).

## P11. Dependencia de TARRO

**Alternativas**
- A. Mover el estado de coordinación al repo/VPS (P6-A, P7-A) para que TARRO sea un cliente más. S/M.
- B. Runner headless en PCRick/VPS (Claude Code `-p` o Agent SDK con clave API) para paquetes sin GUI; Revit sigue en PCRick. M; coste API.
- C. Managed Agents (beta). L.

**Recomendación** [O]: A, luego B piloto. Confirma: un ciclo completo de paquete con TARRO apagado.

## Tabla resumen

| Problema | Recomendación provisional | Esfuerzo | Reversible |
|---|---|---|---|
| P1 Heap V8 | `NODE_OPTIONS` en unit + snapshot near limit + `MemoryHigh/Max` + backoff; compactar sesión | S | Sí |
| P2 Canario | Job `isolated`, light-context, modelo barato, `NO_REPLY`, `fallbacks ""`; luego probe externo | S | Sí |
| P3 Embeddings | Pin `provider: gemini` + modelo/dims + manifest; reindex forzado | S | Sí |
| P4 Conectividad | Re-auth Tailscale con tag; túnel SSH endurecido; probe E2E con `trace_id` | S/M | Sí |
| P5 Observabilidad | `trace_id` único propagado + campos `gen_ai.*`; piloto Langfuse | S→M | Sí |
| P6 Coordinación | Ledger con esquema + hooks ACK/REPORT; luego MCP «UAS board» | S/M | Sí |
| P7 Memoria/Notion | Un solo escritor con backoff; JSONL fuente, Notion proyección | S/M | Sí |
| P8 Evaluación | Estados preparado/ejecutado/validado + evidencia obligatoria | S | Sí |
| P9 Costos | `modelPolicy.allow` + sin fallbacks + ledger de coste + alertas | S | Sí |
| P10 Respaldo/secretos | Rotación inmediata; inventario; restic con check y restore de prueba; limpiar checkpoints | M | Sí |
| P11 TARRO | Estado en repo/VPS; runner headless piloto | S/M → M | Sí |

**Límites de esta investigación:** no se abrió la página de soporte de Anthropic sobre facturación del Agent SDK, ni la guía de evals de Anthropic, ni la página completa de `--max-old-space-size`; precios del 9-nov-2026.
