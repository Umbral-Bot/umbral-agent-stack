# VM tailnet operational recovery - 2026-03-15

## Summary

- Root cause was **not** a dead VM.
- `pcrick` stayed alive on the Hyper-V internal network at `192.168.101.72`.
- The failure was the guest network path after host reboot:
  - internal worker ports `8088` / `8089`: reachable from host
  - Tailscale IP `100.109.16.40`: unreachable from host/VPS
  - outbound web from the guest: degraded/broken
  - `tailscale status` inside guest: `logged out`, last login error against `controlplane.tailscale.com` over IPv6

## Evidence

- Host to guest internal IP:
  - `192.168.101.72:8088` -> reachable
  - `192.168.101.72:8089` -> reachable
- Host/VPS to tailnet IP:
  - `100.109.16.40:22/8088/8089` -> timeout
- Guest route table:
  - default route via `192.168.96.1`
- Guest outbound:
  - `browser.navigate(https://www.google.com/)` timed out repeatedly
- Guest Tailscale:
  - after guest reboot, `tailscale status` reported `logged out`
  - last login error referenced IPv6 reachability to the coordination server

## Recovery applied

### 1. Low-risk resets attempted

- Restarted host `SharedAccess` and `WinNat`
- Renewed guest IP
- Rebooted guest cleanly

These steps improved guest liveness, but did **not** fully restore:
- guest outbound web
- guest tailnet reachability by service ports

### 2. Operational workaround implemented

To restore stack operability without waiting for a full guest network repair:

- Started a reverse SSH tunnel from host `tarro` to VPS `srv1431451`
- Forwarded VPS localhost ports:
  - `28022` -> guest `22`
  - `28088` -> guest `8088`
  - `28089` -> guest `8089`

### 3. VPS reconfiguration

Updated `/home/rick/.config/openclaw/env`:

- `WORKER_URL_VM=http://127.0.0.1:28088`
- `WORKER_URL_VM_INTERACTIVE=http://127.0.0.1:28089`
- `WORKER_URL_VM_GUI=http://127.0.0.1:28089`

Then:

- restarted `openclaw-gateway.service`
- restarted `dispatcher.service` as a single clean instance
- refreshed `Dashboard Rick`

## Validation

- VPS health checks:
  - `http://127.0.0.1:28088/health` -> `200`
  - `http://127.0.0.1:28089/health` -> `200`
- Dispatcher log:
  - `Local=http://127.0.0.1:8088`
  - `VM=http://127.0.0.1:28088`
  - `VM_GUI=http://127.0.0.1:28089`
- GUI smoke through VPS path:
  - `gui.desktop_status` -> `ok`
- Dashboard refresh:
  - `Dashboard Rick` regenerated successfully

## Residual issue

This is an **operational recovery**, not a full guest-network fix.

Still pending:

- `pcrick` own Tailscale path remains unhealthy
- guest outbound web is still degraded/broken
- guest Tailscale session is logged out and needs a dedicated network repair/auth recovery

## Durable hardening added

Added repo scripts:

- `scripts/vm/start_vm_reverse_tunnel.ps1`
- `scripts/vm/ensure_vm_reverse_tunnel.ps1`
- `scripts/vm/start_vm_reverse_tunnel.bat`
- `scripts/vm/install_vm_reverse_tunnel_startup.ps1`

Purpose:

- recreate the reverse tunnel automatically on host startup/login
- validate tunnel health and recreate it if the SSH process survives but the forward dies
- avoid manual recovery next time the host reboots before the guest NAT/Tailscale path is fully repaired

## Host-side deployment

- Installed startup shortcut on host `tarro`:
  - `C:\Users\david\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\StartVmReverseTunnel.lnk`
- Validated that the new script detects an existing tunnel and does not spawn duplicates.
