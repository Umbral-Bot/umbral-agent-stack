# Runbook: OpenClaw node persistente en la VM (PCRick)

## Objetivo

Dejar `PCRick` conectado de forma persistente como node de OpenClaw en la VM Windows, usando la topologia correcta para el gateway actual de la VPS.

## Estado real hoy

En la VPS:

- `openclaw devices list` muestra `PCRick` ya **paired** con rol `node`.
- `openclaw nodes status` lo muestra **paired · disconnected**.

Eso significa que el pairing base ya existe. Lo que falta no es aprobar otro device por defecto, sino volver a levantar el node host de la VM de manera persistente.

## Hallazgo clave

El gateway de la VPS corre en `loopback` (`ws://127.0.0.1:18789`).

Segun la documentacion oficial actual de OpenClaw, cuando el gateway remoto esta en loopback, un node remoto **no** debe apuntarle directo por `--host srv1431451... --port 18789`. En ese caso la ruta correcta es:

1. crear un tunel SSH desde la VM hacia la VPS;
2. exponer un puerto local en la VM, por ejemplo `127.0.0.1:18790`;
3. correr `openclaw node install` apuntando a ese extremo local.

Referencia oficial:

- [Nodes - OpenClaw](https://docs.openclaw.ai/nodes)
  - `openclaw node run --host 127.0.0.1 --port 18790 ...` detras de SSH tunnel para gateways en loopback
  - `openclaw node install ...` para servicio persistente

## Prerequisitos en la VM

- `openclaw` en PATH (`openclaw --version`)
- `ssh.exe` en PATH (`ssh -V`)
- `nssm` en PATH (`nssm version`)
- acceso SSH desde la VM hacia la VPS (`rick@187.77.60.169` o el target que corresponda)
- clave SSH local en `C:\Users\Rick\.ssh\id_ed25519` (o pasar otra ruta via parametro)
- token del gateway de OpenClaw en la VPS

Antes del instalador, conviene dejar validado esto:

```powershell
ssh rick@187.77.60.169 exit
```

Si pide password, primero hay que autorizar la clave publica de la VM en `~/.ssh/authorized_keys` de la VPS.

## Script recomendado

Usar el script del repo:

- [install_openclaw_node_stack.ps1](../scripts/vm/install_openclaw_node_stack.ps1)

Este script hace dos cosas:

1. instala un servicio NSSM `openclaw-node-tunnel` que mantiene:
   - `127.0.0.1:18790` en la VM -> `127.0.0.1:18789` en la VPS
2. ejecuta el CLI oficial:
   - `openclaw node install --host 127.0.0.1 --port 18790 --display-name PCRick --force`
   - luego `openclaw node restart`

## Ejecucion

En la VM, con PowerShell:

```powershell
cd C:\GitHub\umbral-agent-stack
powershell -ExecutionPolicy Bypass -File .\scripts\vm\install_openclaw_node_stack.ps1 `
  -GatewayToken "TU_TOKEN_REAL_DEL_GATEWAY" `
  -GatewaySshTarget "rick@187.77.60.169" `
  -DisplayName "PCRick"
```

Si tu acceso SSH a la VPS usa otro hostname o usuario, cambia `-GatewaySshTarget`.
Si la clave no esta en `C:\Users\Rick\.ssh\id_ed25519`, agrega:

```powershell
  -SshKeyPath "C:\ruta\clave_ed25519" `
  -KnownHostsPath "C:\ruta\known_hosts"
```

## Verificacion en la VM

```powershell
nssm status openclaw-node-tunnel
openclaw node status
Get-Content C:\openclaw-worker\openclaw-node-tunnel-stderr.log -Tail 20
```

Lo esperable:

- el tunel queda escuchando en `127.0.0.1:18790`
- `openclaw node status` deja el servicio instalado

## Verificacion en la VPS

```bash
openclaw devices list
openclaw nodes status
```

Escenarios:

1. Si `PCRick` ya estaba paired, deberia pasar de:
   - `paired · disconnected`
   a
   - `connected`
2. Si el node reinstala con una nueva solicitud de pairing, aprobar:

```bash
openclaw devices approve <requestId>
openclaw nodes status
```

## Que no hacer

- no volver a apuntar el node remoto directo a `srv1431451:18789` mientras el gateway siga en loopback;
- no abrir mas routers virtuales ni redisenar Hyper-V para este problema;
- no asumir que `Tailscale off` en la VPS invalida OpenClaw, porque la ruta canonica actual sigue siendo loopback + tuneles.

## Si falla

1. Revisar que la VM tenga salida SSH hacia la VPS:

```powershell
ssh rick@187.77.60.169 exit
```

2. Revisar el tunel:

```powershell
Test-NetConnection 127.0.0.1 -Port 18790
Get-Content C:\openclaw-worker\openclaw-node-tunnel-stdout.log -Tail 20
Get-Content C:\openclaw-worker\openclaw-node-tunnel-stderr.log -Tail 20
```

3. Revisar el servicio del node:

```powershell
openclaw node status
openclaw node restart
```

4. En la VPS, volver a mirar:

```bash
openclaw devices list
openclaw nodes status
```

## Bloqueo actual

Desde esta sesion de Codex no hay acceso administrativo efectivo a la VM, asi que la instalacion final sigue pendiente de ejecucion manual dentro de Windows. El trabajo repo-side ya queda preparado; la unica intervencion humana pendiente es correr el script en `PCRick` y validar la reconexion del node.
