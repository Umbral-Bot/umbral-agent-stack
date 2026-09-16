# Borrador técnico (no publicado) — service-child-group-anchor vs. procesos que cierran fds al iniciar

Estado: borrador interno, generado durante T2 (2026-09-16). No se envió a
ningún repositorio externo ni se abrió issue/PR upstream. Documenta la causa
raíz y una posible corrección en el propio OpenClaw, para que quien mantenga
esa dependencia decida si vale la pena proponerla upstream.

## Contexto

`node_modules/openclaw/dist/process/supervisor/service-child-group-anchor.js`
supervisa un proceso raíz mediante un descriptor de linaje adicional
(`lineageFd`, típicamente fd 3). Si el descriptor se cierra mientras el
proceso raíz sigue vivo, `markLineageClosed()` espera
`LINEAGE_EXIT_OBSERVATION_MS` (100ms) y, si el proceso raíz no ha salido en
ese lapso, asume que el linaje se perdió y manda `SIGTERM` a todo el grupo
(`requestCleanup("lineage-lost")` → `process.kill(0, "SIGTERM")`).

Esto es correcto para su caso objetivo (detectar un subárbol que escapó de
la supervisión, p. ej. vía `setsid`/doble fork). Pero produce un falso
positivo cuando el proceso raíz mismo (no un descendiente evasor) hace
`exec()` hacia un binario que cierra por hábito sus descriptores heredados
"desconocidos" al iniciar — `ssh`/OpenSSH es un ejemplo real y confirmado
(ver `docs/pcrick-job-adapter.md` y la evidencia de T2). El proceso sigue
bajo supervisión real (mismo PID, mismo grupo, sin evasión), pero el
supervisor no puede distinguir ambos casos solo con el cierre del fd.

## Mitigación aplicada en este repo (sin tocar OpenClaw)

`scripts/vm/pcrick_ssh_dispatch.py`: nunca deja que el proceso raíz haga
`exec` hacia `ssh`; lo lanza como hijo real (`subprocess.Popen`, sin
`setsid`) y permanece vivo hasta que `ssh` termina. El fd de linaje del
proceso raíz (el wrapper) se mantiene abierto durante toda la vida real de
`ssh`, así que el cierre solo ocurre cuando el wrapper sale de verdad,
coincidiendo con el resultado real — sin necesitar ningún cambio en
OpenClaw.

## Posible corrección upstream (no implementada, solo propuesta)

Si en algún momento se quiere corregir esto en el propio
`service-child-group-anchor`, una opción sin debilitar la protección contra
evasión sería: en vez de decidir "linaje perdido" únicamente por el cierre
del fd + el proceso raíz seguir vivo, comprobar además si el **PID del
proceso raíz sigue siendo miembro del mismo grupo de procesos que el
anchor** (`readProcessGroupMembers`, ya existe en el mismo archivo para otro
propósito) antes de declarar SIGTERM. Un `exec()` en el propio proceso raíz
conserva PID y PGID; una evasión real vía `setsid`/doble fork los cambia.
Esto permitiría distinguir "el mismo proceso decidió cerrar un fd que no
usa" de "un descendiente se escapó del grupo", sin ampliar la ventana de
100ms (que sigue siendo útil contra timing real de evasión) ni requerir que
cada comando conozca este detalle de implementación.

No se implementó ni se propuso formalmente upstream; queda como nota para
quien decida si amerita el esfuerzo frente al costo de mantener
`pcrick_ssh_dispatch.py` como mitigación local.
