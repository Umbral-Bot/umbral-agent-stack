---
id: "2026-03-24-014"
title: "PCRick: persistencia real del node OpenClaw en la VM"
status: blocked
assigned_to: codex
created_by: codex
priority: high
sprint: R23
created_at: 2026-03-24T10:33:00-03:00
updated_at: 2026-03-24T10:33:00-03:00
---

## Objetivo
Dejar la ruta correcta y reproducible para que `PCRick` vuelva a quedar conectado como node persistente de OpenClaw en la VM Windows, sin rediseñar la topologia Hyper-V ni abrir el gateway VPS mas de lo necesario.

## Contexto
- En la VPS, `openclaw devices list` muestra `PCRick` ya **paired** con rol `node`.
- `openclaw nodes status` muestra `PCRick` como **paired · disconnected**.
- El gateway VPS actual corre en `loopback` (`ws://127.0.0.1:18789`), por lo que la documentacion oficial de OpenClaw indica que un node remoto no debe apuntarle directo; debe usar un tunel SSH local o cambiar la topologia del gateway.
- Desde esta sesion no hay acceso administrativo efectivo a la VM:
  - Hyper-V devuelve falta de permisos;
  - `100.109.16.40:8088/8089`, `192.168.101.72:8088` y `172.29.127.130:8088` no responden desde el host.

## Criterios de aceptacion
- [x] Existe un script reproducible en `scripts/vm/` para instalar el tunel SSH persistente y el `openclaw node install` oficial en la VM.
- [x] El runbook de node VM queda alineado con la topologia real del gateway en loopback.
- [x] Queda asentado en docs/board que `PCRick` hoy esta paired pero disconnected y que falta ejecucion manual en la VM para cerrar.
- [x] Se explicita la unica intervencion humana pendiente sin inventar cambios de red adicionales.

## Log
### [codex] 2026-03-24 10:33
La evidencia viva en VPS muestra:

- `openclaw devices list` -> `PCRick` ya existe como device `paired` con rol `node`;
- `openclaw nodes status` -> `Known: 1 · Paired: 1 · Connected: 0`, `PCRick` = `paired · disconnected`.

Hallazgo clave: el runbook viejo apuntaba el node remoto directo a `srv1431451:18789`, pero la documentacion oficial de OpenClaw indica que, con gateway en `loopback`, el node remoto debe conectarse via tunel SSH local (`127.0.0.1:<port>`) o cambiar la topologia del gateway. Desde esta sesion no hay acceso efectivo a la VM para ejecutar la instalacion final, asi que el cierre quedara bloqueado solo en la ejecucion manual de ese script en Windows.

### [codex] 2026-03-24 10:46
Trabajo repo-side completado:

- nuevo script reproducible en `scripts/vm/install_openclaw_node_stack.ps1`
  - instala un servicio NSSM `openclaw-node-tunnel`
  - levanta un tunel SSH local `127.0.0.1:18790 -> VPS 127.0.0.1:18789`
  - corre `openclaw node install --host 127.0.0.1 --port 18790 --display-name PCRick --force`
  - reinicia el node y deja comandos de verificacion
- runbook corregido en `runbooks/runbook-vm-openclaw-node.md`
- setup general actualizado en `docs/03-setup-vps-openclaw.md`
- follow-up diagnostico actualizado en `docs/audits/openclaw-rick-response-followup-2026-03-24.md`

Bloqueo residual exacto:

- falta ejecutar el script dentro de la VM Windows;
- desde esta sesion no hay permisos Hyper-V ni reachability host->VM suficientes para correrlo remotamente;
- no hace falta redisenar Hyper-V ni agregar routers virtuales; solo correr el instalador en `PCRick` y luego verificar en la VPS que pase de `paired · disconnected` a `connected`.

Validacion repo-side:

- parser PowerShell OK para `scripts/vm/install_openclaw_node_stack.ps1`
- `openclaw status --all` en VPS confirma que el gateway sigue en `loopback`
- `openclaw devices list` / `openclaw nodes status` confirman que `PCRick` ya esta paired y solo falta reconexion persistente

### [codex] 2026-03-24 18:25
Primer intento vivo en la VM:

- la VM volvio a arrancar y pudo hacer `git pull origin main`;
- `openclaw node --help` confirma que el CLI instalado en Windows soporta `node install`;
- se genero una clave SSH local `id_ed25519` y se autorizo en `~/.ssh/authorized_keys` de la VPS;
- el servicio `openclaw-node-tunnel` quedo `SERVICE_RUNNING`, pero `127.0.0.1:18790` seguia sin responder.

Hallazgo nuevo:

- el script original no fijaba `-i <key>` ni `UserKnownHostsFile`, por lo que el servicio NSSM quedaba con identidad SSH ambigua;
- ademas, el primer intento se lanzo con el placeholder `TU_TOKEN_REAL_DEL_GATEWAY`, asi que el `node install` no podia cerrarse correctamente aunque el tunel subiera.

Accion repo-side adicional:

- `scripts/vm/install_openclaw_node_stack.ps1` ahora fuerza:
  - `-i $env:USERPROFILE\.ssh\id_ed25519`
  - `-o BatchMode=yes`
  - `-o IdentitiesOnly=yes`
  - `-o UserKnownHostsFile=...`
- el script ahora hace una prueba SSH no interactiva antes de reinstalar el servicio de tunel;
- el runbook `runbooks/runbook-vm-openclaw-node.md` fue actualizado para incluir esa precondicion.

Bloqueo residual exacto:

- rerun del script en la VM con el parche nuevo;
- obtencion del `GatewayToken` real desde la VPS;
- verificacion final en la VPS de que `PCRick` pase de `paired · disconnected` a `connected`.
