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
- `outputs`: rutas relativas esperadas dentro del workspace. El recibo conserva
  existencia/hash/tamaño antes y después, sin confundir archivo previo con producido.
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

**Lado VPS (origen):** el transporte autenticado es el túnel SSH reverso
permanente en `127.0.0.1:22024`. Para invocarlo desde un turno real de un
agente (`openclaw_direct__exec` u otro mecanismo de exec del runtime),
**usar siempre `scripts/vm/pcrick_ssh_dispatch.py`**, nunca `ssh` directo ni
`bash -c 'ssh ...'` ad hoc:

```text
python3 scripts/vm/pcrick_ssh_dispatch.py \
  --host 127.0.0.1 --port 22024 --user rick --connect-timeout 8 \
  -- python scripts/vm/pcrick_job.py --root <registro-local> start --request <encargo.json> --profile <perfil-cli.json>
```

Este wrapper existe por un motivo concreto y ya diagnosticado (T2,
2026-09-16): el supervisor de OpenClaw (`service-child-group-anchor`, ver
`node_modules/openclaw/dist/process/supervisor/service-child-group-anchor.js`)
sigue el proceso raíz que despacha mediante un descriptor de linaje extra. Si
ese proceso raíz haz `exec` directo hacia `ssh`, OpenSSH cierra ese
descriptor al iniciar (higiene propia de OpenSSH, no un error), y el
supervisor —sin forma de distinguirlo de un árbol de procesos realmente
huérfano— manda `SIGTERM` a los ~100ms. `pcrick_ssh_dispatch.py` evita esto
sin desactivar la supervisión ni usar `setsid`: lanza `ssh` como hijo real
vía `subprocess.Popen` (nunca `exec`), permaneciendo vivo como proceso padre
mientras `ssh` corre, y propaga su exit code, señales y salida reales. Ver el
docstring del script y `tests/test_pcrick_ssh_dispatch.py` para el
diagnóstico completo y las pruebas de regresión.

Comandos de destino (lado PCRick, ejecutados por el wrapper de arriba); el
transporte autenticado decide cómo entregar los dos JSON y ejecutar Python,
con rutas cotejadas y hashes antes de admitir:

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

El último control de reserva, la creación efectiva del proceso y el recibo de
PID comparten una transacción. Si un cierre reconciliado gana antes, el
supervisor pendiente no lanza nada; si el lanzamiento gana, el cierre espera a
que se registre el proceso. STARTING se persiste previamente: una interrupción
tras lanzar conserva la incertidumbre y no habilita una repetición automática.

La transacción SQLite reserva workspace (incluidos solapes padre/hijo) y, si
corresponde, `gui:<host>`. Dos trabajos CLI en carpetas independientes pueden
coexistir. Los procesos o herramientas que no usan este registro no quedan
bloqueados mágicamente: inventariar trabajo externo y respetar un solo operador
GUI sigue siendo necesario, incluido RustDesk/TeamViewer y `gui.*`.

La salida y el error se conservan en `jobs/<sha256-id>/stdout.log` y `stderr.log`.
El ID exacto se hashea para evitar alias de nombres y diferencias de mayúsculas
en Windows; el recibo mantiene el ID humano original.
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

## Paquete Interactive mantenido y tarea manual

`scripts/vm/pcrick_interactive.py` reemplaza el Python generado por cada agente
con un único preparador/supervisor mantenido. Se ejecuta en **PCRick como Rick**;
la preparación puede usar su sesión SSH, pero el supervisor exige además sesión
interactiva distinta de 0, elevación y el SID fijado al preparar. No configura
cuentas, transporte, permisos globales ni credenciales. Sus dependencias son
`pcrick_job.py` en la misma carpeta y Python3.11+ con `python.exe`/`pythonw.exe`.

Preparar primero el JSON de solicitud con **exactamente** los campos del contrato
anterior, sin `schema`, `model`, `argv` u otros campos añadidos. El perfil tiene
solamente `runner`, `argv`, `input_mode`. Usar un serializador JSON (por ejemplo
`json.dumps` o `ConvertTo-Json`) o rutas `C:/Users/Rick/...`; no generar código
Python que incruste rutas `C:\Users` en literales. El prompt y las skills deben
existir con sus hashes reales. Los flags de la CLI deben corresponder a la versión
efectivamente instalada. Para Antigravity con `last_arg`, dejar `-p` como último
argumento del perfil: el runner añade el prompt después.

```powershell
# Solo lectura: valida contrato, archivos, identidad y presenta archivos/Task previstos.
python C:/ruta-fijada/scripts/vm/pcrick_interactive.py prepare `
  --request C:/encargo/request-source.json --profile C:/encargo/profile-source.json `
  --package C:/encargo/prepared --registry C:/registro-compartido `
  --pythonw C:/ruta-observada/Python313/pythonw.exe
```

Repetir con `--write` materializa `request.json`, `profile.json`, `manifest.json`
y `task.xml`; **no registra, inicia ni admite** el trabajo. El directorio preparado
debe ser nuevo, incluso si el encargo aún no fue admitido. Ante un error parcial
conservar la evidencia y preparar otra ubicación después de revisar el estado;
no sobrescribir el paquete usado por una ejecución. Mantenerlo fuera del registro
SQLite, con ACL privadas para Rick/SYSTEM, y fijar una revisión de scripts que no
se actualice mientras la tarea esté pendiente o activa.

La manifestación fija hashes de solicitud, perfil, runner, supervisor, intérpretes,
prompt y skills. El supervisor vuelve a validar el contrato y los hashes antes
de lanzar. Los hashes detectan cambios accidentales; no autentican un manifiesto
reescrito por un administrador local. Conservar la evidencia del transporte y
del commit revisado en el PKG canónico. El preparador tampoco demuestra que un
perfil full-access no use GUI: si el encargo la necesita, `gui=true` y un operador.

Añadir `--input C:/caso/input.json --input C:/caso/result.json` para fijar archivos
del caso o salidas revisadas que una continuación usará como entrada. Son archivos
locales existentes, con rutas absolutas normalizadas y sin duplicados; no se
aceptan directorios, rutas relativas o UNC. Se conservan como `input_pins` en el
manifiesto, fuera del contrato estricto de solicitud. Un cambio, archivo faltante
o hash omitido bloquea el lanzamiento. El recibo del supervisor fija el hash del
manifiesto revisado. La comprobación ocurre antes de lanzar; no impide que el
propio trabajo modifique un archivo después. Usar copias/snapshots para entradas
que deban permanecer inmutables durante todo el encargo.

El plan devuelve `task_name`. Después de revisar el XML y la autorización del PKG,
registrar explícitamente desde PCRick elevado, sin reemplazar tareas existentes:

```powershell
$taskName = 'Umbral-PCRick-<hash-devuelto-en-el-plan>'
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
  throw 'TASK_EXISTS_REVIEW_BEFORE_CHANGE'
}
Register-ScheduledTask -TaskName $taskName -Xml (Get-Content -LiteralPath C:/encargo/prepared/task.xml -Raw -Encoding UTF8)
# El inicio es otro paso deliberado, después de cotejar solicitud/perfil/lease/origen:
# Start-ScheduledTask -TaskName $taskName
```

El XML usa el SID de Rick, `InteractiveToken`, `HighestAvailable`, `IgnoreNew`,
cero triggers y `ExecutionTimeLimit=PT0S`. No introduce polling ni un daemon.
Se guarda UTF-8 sin declaración de codificación: el cmdlet recibe texto Unicode
y Windows rechaza una declaración UTF-8 dentro de ese BSTR (HRESULT0x8004131a).
Para un paquete anterior ya materializado, conservar sus bytes y pasar
`([xml](Get-Content -LiteralPath <task.xml> -Raw -Encoding UTF8)).DocumentElement.OuterXml`
como `-Xml`, documentando esa normalización y sin reemplazar una Task existente.
Rick debe tener sesión iniciada; no equivale a habilitar ejecución sin sesión.
No hay un límite externo que mate el proceso al vencer la observación del
supervisor (720s por defecto). Entonces registra `TIMEOUT_UNRECONCILED` y continúa
esperando; si termina, registra `PROCESS_EXITED_AFTER_TIMEOUT`. Nunca mata, cierra,
libera leases o reintenta automáticamente. Un proceso que no termina requiere
reconciliación manual, no una espera tomada como éxito.

Cada invocación conserva `task-attempts/<uuid>/{supervisor.json,command.json,
stdout.json,stderr.txt}`. Las actualizaciones del supervisor se escriben de forma
atómica, con PID propio y PID observado del runner; un PID no demuestra liveness.
Los fallos de validación dentro del contexto permitido quedan registrados como
`FAILED_BEFORE_LAUNCH`, sin admitir. Una sesión/identidad no autorizada falla antes
de escribir esos logs. Un fallo anterior a abrir el manifiesto o falta de permiso
de escritura requiere revisar el resultado de la Task y su contexto.

La repetición usa los mismos archivos y el mismo `job_id`, con una carpeta de
intento nueva. El supervisor invoca **`pcrick_job.py run`**, cuya admisión SQLite
devuelve el recibo existente y evita una segunda ejecución del modelo. No añade
otro lock, TTL ni mecanismo de cierre. Conservar las salidas privadas y consultar
`pcrick_job.py status` antes de decidir recuperación o cierre; el proceso terminado
no demuestra aceptación del resultado ni cierre de la reserva de skills.

### Selección opcional de MCP por ejecución Codex

`prepare --mcp-policy C:/encargo/mcp-policy.json` acepta exactamente:

```json
{
  "observed_servers": ["Revit", "node_repl"],
  "enabled_servers": [],
  "config_path": "C:/Users/Rick/.codex/config.toml",
  "config_sha256": "<sha256-real-del-archivo-revisado>"
}
```

Solo para `codex.exe` nativo. Para cada ID observado no seleccionado, antepone
los argumentos separados `-c`, `mcp_servers.ID.enabled=false`, conservando el
resto del perfil y sus permisos. No fuerza a encender servidores globalmente
deshabilitados. Rechaza IDs con puntos/comillas/espacios y overrides MCP previos
ambiguos. El archivo de configuración se fija por hash y se coteja antes de
lanzar. No modifica globales ni arranca MCP para preparar el paquete.

La serialización se verificó con Codex0.154 usando únicamente `mcp list --json`
y un `CODEX_HOME` temporal sin auth ni ejecutables MCP válidos: IDs simples y
`enabled=false` son aceptados; `mcp_servers={}` no elimina tablas heredadas y
las comillas incrustadas en IDs no sirven para este override. Revalidar con la
versión de destino al actualizar. La lista observada es responsabilidad del
operador: debe incluir las capas pertinentes del cwd/proyecto. No garantiza
desactivar servidores de plugins, políticas administradas o nuevos IDs no
inventariados. Es reducción de ruido de inicio, no una restricción de permisos
del agente. Referencia: [configuración oficial](https://learn.chatgpt.com/docs/config-file/config-reference)
y [MCP oficial](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

```text
python tests/test_pcrick_interactive.py -v
python tests/test_pcrick_job.py -v
```

Estas pruebas son offline. Verifican plan sin escrituras/dispatch, esquemas
exactos, JSON/XML con rutas Windows, inmutabilidad, SID/sesión/elevación, drift,
PIDs, replay delegado, timeout sin kill/close y argumentos MCP. La suite del
runner comprueba la deduplicación real mediante procesos de fixture. Una Task
real, la supervivencia después de desconectar el transporte y los resultados
de cada CLI se acreditan por separado antes de declarar una ruta operativa.
