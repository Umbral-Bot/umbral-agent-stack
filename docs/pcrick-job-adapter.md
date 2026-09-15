# PCRick: admisión y recibos de trabajos CLI

Este adaptador acotado se invoca mediante el transporte privado ya existente.
No abre puertos, instala servicios, crea colas periódicas ni modifica Worker,
Dispatcher, cuentas o permisos. Un proceso supervisor vive únicamente durante
el trabajo. La fuente del encargo sigue siendo el PKG/ledger existente; SQLite
es su registro local de ejecución, no otro dashboard.

## Interfaces existentes y brecha que cubre

| Interfaz UAS revisada | Capacidad | Límite pertinente |
|---|---|---|
| Worker `POST /run` | Handler en threadpool, Bearer interno o cliente | No dedup por task_id ni recibo previo a todos los efectos. Resultado `/tasks/{id}` en memoria, máximo1000. |
| `POST /enqueue`, `GET /task/{id}/status` | Cola Redis y estado | Un UUID nuevo por POST; `BRPOP` mueve la tarea fuera de pending sin ACK/reclaim durable de ejecución. No es reserva de PCRick. |
| `WorkerClient.run` | Transporte HTTP existente | Reintenta timeouts de lectura/escritura por defecto. Para un inicio sin idempotencia demostrada usar `retries=0` y reconciliar. |
| `windows.fs.*` | Operaciones de archivos dentro de ToolPolicy | No ejecuta terminal general. |
| `gui.*` en Worker interactivo8089 | Escritorio, capturas y acciones | Sus handlers no aplican reserva compartida; solo deben ser usados por el operador GUI vigente. No equivale a disponer de computer-use en cada agente. |
| `copilot_cli.run` | Capacidad Docker/VPS con gates y auditoría | No invoca los tres IDE/CLI de PCRick. |
| Nodo oficial OpenClaw y SSH | Transporte privado candidato al runner local | Debe probarse conexión, identidad y proceso en PCRick por cada origen. Su mera instalación no acredita ruta. |

No existe `shell.execute` en el registry Worker inspeccionado. Referencias:
`worker/app.py`, `worker/tasks/__init__.py`, `worker/tasks/gui.py`,
`client/worker_client.py`, `dispatcher/queue.py`,
`scripts/vm/install_openclaw_node_stack.ps1`.

## Contrato

`scripts/vm/pcrick_job.py` usa Python3.11+ y solo stdlib. El directorio `--root`
debe ser el **mismo** para los dos Rick en PCRick, local a NTFS y protegido como
evidencia privada. No usar un directorio por solicitante ni sincronizar SQLite
con Drive/OneDrive. Respaldar DB con SQLite backup o cuando no haya escritores;
no copiar arbitrariamente un journal activo.

Cada solicitud JSON contiene exactamente:

- `job_id`: ID inmutable de un paso del PKG. Repetición devuelve el recibo;
  contenido distinto con el mismo ID se rechaza.
- `requester`, `owner`: `rick` o `rick-grok`, conservando solicitante y responsable.
- `target_host`, `target_user`: identidad OS esperada (`PCRick`, `Rick` según
  inventario real). Se verifica otra vez dentro del supervisor.
- `runner`: `codex`, `claude` o `antigravity`.
- `workspace`: carpeta absoluta existente y aislada del trabajo.
- `prompt_path`, `prompt_sha256`: prompt UTF-8 local, máximo1MB, sin secretos.
- `skills_commit`: SHA Git completo. `skills`: lista de `{name,path,sha256}`.
- `acceptance`: criterio observable, que no se deduce del exitcode.
- `gui`: booleano; reservar escritorio global si este encargo va a usarlo.

El perfil local contiene solo `{runner, argv, input_mode}`. `argv` es una lista
verificada contra la CLI instalada; su primer elemento es ejecutable absoluto.
No se aceptan `.cmd`, `.bat` o `.ps1` como ejecutable directo. Cuando una CLI se
instala con npm, resolver su ejecutable nativo o `node.exe` más entrypoint real,
sin construir comandos de shell. `input_mode` es `stdin` (el adaptador entrega
EOF) o `last_arg` cuando la CLI oficial exija el prompt como argumento. El hash
del perfil queda fijado. No incluir secretos en argumentos o prompts.

El adaptador no adivina flags por marca o por versión de otra máquina. Las
cuentas y permisos efectivos pertenecen al proceso de PCRick. Los perfiles
reales deben pasar un trabajo local y una reanudación antes de declararse listos.

## Invocación sobre el transporte existente

Comandos de destino; el transporte autenticado decide cómo entregar los dos
JSON y ejecutar Python, con rutas cotejadas y hashes antes de admitir:

```text
python scripts/vm/pcrick_job.py --root <registro-local> start --request <encargo.json> --profile <perfil-cli.json>
python scripts/vm/pcrick_job.py --root <registro-local> status --job-id <id>
```

`run` espera al proceso; `start` devuelve después de lanzar un supervisor. El
supervisor no depende de un daemon nuevo. **La supervivencia tras desconexión
SSH/nodo debe probarse en Windows real**: un Job Object de la sesión puede tener
una política de cierre que un grupo de procesos nuevo no evite. El registro
persistente evita un segundo lanzamiento; no prueba que el primero siga vivo.

Usar el mismo `job_id` para recuperar una respuesta perdida; si cambió un
archivo de entrada, consultar `status` en vez de modificar hashes para forzar
la repetición. Un ID cerrado nunca vuelve a ejecutar. Un nuevo paso deliberado
requiere ID nuevo, relación en el PKG y entradas fijadas.

## Estados, exclusión y recuperación

`RESERVED → STARTING → RUNNING → PROCESS_EXITED → CLOSED`.
Un error incierto produce `UNKNOWN` con tipo de error, conservando la reserva.
Una interrupción puede dejar el último estado observado, incluso RUNNING.
No hay expiración automática ni liberación por PID ausente/antiguo.

La transacción SQLite reserva workspace (incluidos solapes padre/hijo) y, si
corresponde, `gui:<host>`. Dos trabajos CLI en carpetas independientes pueden
coexistir. Los procesos o herramientas que no usan este registro no quedan
bloqueados mágicamente: inventariar trabajo externo y respetar un solo operador
GUI sigue siendo necesario, incluido RustDesk/TeamViewer y `gui.*`.

La salida y el error se conservan en `jobs/<id>/stdout.log` y `stderr.log`.
El recibo expone rutas/hash, usuario/host/PID, fechas, sesión cuando se observa,
exitcode y `acceptance=NOT_REVIEWED`. No publica el contenido de logs. Estos
logs pueden contener datos de trabajo: deben mantenerse privados y sanearse
antes de enviarlos a Notion/Linear.

Tras revisar artefactos, sesión y ausencia de actividad descendiente, guardar
evidencia concreta y cerrar con owner/generación actuales:

```text
python scripts/vm/pcrick_job.py --root <registro-local> close --job-id <id> --owner rick-grok --generation 1 --evidence <revision.md>
```

Para un estado que no sea PROCESS_EXITED se exige además `--reconciled`. Es una
declaración explícita del operador, no una prueba automática: debe documentar
proceso/árbol/sesión, efectos ya producidos, qué no se repetirá y por qué es seguro
liberar. Un archivo no vacío por sí solo no demuestra esa comprobación. Nunca
usar este flag como recuperación rutinaria de un timeout. Conservar el recibo
original y las evidencias en rollback; no borrar la DB para conseguir verde.

`handoff` requiere que haya terminado el proceso o que el trabajo esté cerrado,
evidencia y owner/generación correctos. Incrementa la generación; el owner viejo
ya no puede cerrar o transferir mediante este adaptador. No transfiere un proceso
vivo ni concede revocación de una clave SSH o de herramientas externas.

## Identidad, skills y sesiones: límites explícitos

- **Autenticación de origen:** requester/owner son etiquetas de coordinación.
  El recibo declara `origin_authentication=EXTERNAL_TRANSPORT_REQUIRED`. La
  evidencia del transporte debe demostrar qué origen/clave/nodo autenticado
  emitió la orden, sin publicar claves. `X-Umbral-Caller` y un WORKER_TOKEN común
  no distinguen criptográficamente a ambos Rick. SSH con claves diferenciadas
  y nodo paired verificable se evalúan en la prueba real; no se finge esa capa.
- **Skills:** se cotejan hashes al admitir y al ejecutar. Durante el encargo
  usar el lease del receptor existente o un snapshot inmutable. El adaptador
  no instala ni actualiza skills y no garantiza inmutabilidad de una ruta que
  otro proceso pueda sobrescribir. Declarar un SHA no prueba su procedencia.
- **Sesiones:** se captura Codex `thread.started.thread_id` y Claude
  `system/result.session_id`, solo si hay un ID inequívoco. Antigravity queda
  UNKNOWN hasta observar su schema real. No se usa “latest”. La continuación
  requiere perfil con el ID exacto, nuevo paso vinculado y comprobación del
  contexto; este corte no afirma reanudación automática de las tres CLIs.
- **Aceptación:** exit0, archivo creado y sesión emitida son hechos distintos.
  El revisor coteja artefacto/hash/contenido/rúbrica. Una prueba de admisión no
  reemplaza el segmento nativo C23.

## Validación offline y despliegue

```text
python tests/test_pcrick_job.py -v
```

La suite ejecuta procesos Python de fixture y concurrencia SQLite local:
dedup tras reinicio, exclusión GUI/workspace/solapes, entrega de EOF, respuesta
incierta, generación de owner, bootstrap alterado, drift de prompt/skills,
proceso con exit no cero, sesión y supervisor asincrónico. No llama CLIs reales,
red, VM, Worker ni servicios. No equivale a las seis rutas de aceptación.

Este componente se revisa y despliega como archivo desde una revisión fijada;
primero una ruta útil C23 y después las restantes. No exige completar la flota
para avanzar con la ruta pertinente. No modifica la política de Editorial.
