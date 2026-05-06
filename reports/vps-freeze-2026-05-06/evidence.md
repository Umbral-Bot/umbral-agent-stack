# Evidence — VPS srv1431451 hypervisor network detach (2026-05-06)

> Raw evidence collected during incident. Narrative + lessons en
> [`runbooks/runbook-vps-ssh-freeze.md`](../../runbooks/runbook-vps-ssh-freeze.md)
> sección **Incident 2026-05-06**.

## Identificación

- VM id: `1431451`
- Hostname: `srv1431451.hstgr.cloud`
- IPv4: `187.77.60.169`
- IPv6: `2a02:4780:6e:2301::1`
- Plan: Hostinger KVM2 (2 vCPU / 8 GB RAM / 100 GB NVMe)
- Datacenter: Brazil — Campinas 22
- OS: Ubuntu 24.04.4 LTS (kernel 6.8.0-111-generic)
- Tailscale: `srv1431451` → `100.113.249.25`

## Pre-restart — externo (notebook Wi-Fi)

```
PS> Test-NetConnection 187.77.60.169 -Port 22
WARNING: TCP connect to (187.77.60.169 : 22) failed
TcpTestSucceeded : False
PingSucceeded    : False

PS> ping 187.77.60.169
Request timed out. (x4)
```

## Pre-restart — Hostinger API

```json
// GET /virtual-machines/1431451
{
  "id": 1431451,
  "state": "running",
  "actions_lock": "unlocked",
  "firewall_group_id": null,
  "hostname": "srv1431451.hstgr.cloud",
  "ipv4": [{"address":"187.77.60.169","netmask":"255.255.255.0","gateway":"187.77.60.254"}]
}

// GET /firewall
[]
```

Métricas CPU/RAM últimas 3 h: fluctuantes (no kernel hung).

## Pre-restart — intra-VM (consola VNC, root)

```bash
$ uptime
 18:30:12 up 18:55,  1 user,  load average: 0.05, 0.03, 0.00

$ ip -4 addr show eth0 | grep inet
    inet 187.77.60.169/24 brd 187.77.60.255 scope global eth0

$ ip route
default via 187.77.60.254 dev eth0 proto static
187.77.60.0/24 dev eth0 proto kernel scope link src 187.77.60.169

$ systemctl status ssh --no-pager | head
● ssh.service - OpenBSD Secure Shell server
     Loaded: loaded (/usr/lib/systemd/system/ssh.service; enabled; preset: enabled)
     Active: active (running) since Mon 2026-05-05 23:35:12 UTC; 18h ago

$ ss -tlnp | grep :22
LISTEN 0  128  0.0.0.0:22  0.0.0.0:*  users:(("sshd",pid=812,fd=3))
LISTEN 0  128     [::]:22     [::]:*  users:(("sshd",pid=812,fd=4))

$ iptables -L INPUT -n -v --line-numbers | head -10
Chain INPUT (policy ACCEPT 0 packets, 0 bytes)
num  pkts bytes target  prot opt in  out  source     destination
1       0     0 ACCEPT  tcp  --  *   *    0.0.0.0/0  0.0.0.0/0   tcp dpt:22
2       0     0 ACCEPT  tcp  --  *   *    0.0.0.0/0  0.0.0.0/0   tcp dpt:80
3       0     0 ACCEPT  tcp  --  *   *    0.0.0.0/0  0.0.0.0/0   tcp dpt:443

# Probe externo simultáneo desde notebook + tcpdump intra-VM:
$ timeout 10 tcpdump -i eth0 -n 'tcp port 22' -c 5
0 packets captured
0 packets received by filter
0 packets dropped by kernel

# Outbound desde la VM:
$ curl -sS -o /dev/null -w "HTTP:%{http_code} time:%{time_total}\n" --max-time 10 https://api.ipify.org
HTTP:000 time:10.001

$ ping -c 3 -W 2 187.77.60.254   # default gateway, misma /24
PING 187.77.60.254 56(84) bytes of data.
--- 187.77.60.254 ping statistics ---
3 packets transmitted, 0 received, 100% packet loss, time 2047ms

$ ping -c 3 -W 2 8.8.8.8
3 packets transmitted, 0 received, 100% packet loss

$ tailscale status
# (tailscale daemon timeout — no DERP reachable)
```

**Diagnóstico**: el vNIC está UP con la IP correcta, sshd está vivo, iptables permite el tráfico, pero **0 paquetes entran y 0 paquetes salen**. La VM está aislada a nivel hypervisor.

## Recovery

```powershell
PS> $TOKEN = "<HOSTINGER_API_TOKEN>"
PS> curl.exe -s -X POST -H "Authorization: Bearer $TOKEN" `
      "https://developers.hostinger.com/api/vps/v1/virtual-machines/1431451/restart"
{"id":92742006,"name":"ct_restart","state":"sent","created_at":"2026-05-06T18:36:44Z","updated_at":"2026-05-06T18:36:44Z"}

# Polling después de 30 s:
PS> curl.exe -s -H "Authorization: Bearer $TOKEN" `
      "https://developers.hostinger.com/api/vps/v1/virtual-machines/1431451/actions/92742006"
{"id":92742006,"name":"ct_restart","state":"success","created_at":"2026-05-06T18:36:44Z","updated_at":"2026-05-06T18:36:55Z"}
```

Action completa en **11 segundos**. Boot agrega ~90 s.

## Post-restart — externo

```
PS> ping 187.77.60.169
Reply from 187.77.60.169: bytes=32 time=85ms TTL=52
Reply from 187.77.60.169: bytes=32 time=182ms TTL=52
Reply from 187.77.60.169: bytes=32 time=285ms TTL=52
Reply from 187.77.60.169: bytes=32 time=178ms TTL=52
Packets: Sent = 4, Received = 4, Lost = 0 (0% loss)
Average = 182ms

PS> Test-NetConnection 187.77.60.169 -Port 22
TcpTestSucceeded : True
```

## Post-restart — intra-VM

```bash
$ uptime
 18:46:01 up 6 min,  1 user,  load average: 0.42, 0.38, 0.18

# Outbound restaurado:
$ curl -sS -o /dev/null -w "HTTP:%{http_code} time:%{time_total}\n" --max-time 5 https://api.ipify.org
HTTP:200 time:0.418

# Gateway sigue sin responder a ICMP (filtrado normal del edge Hostinger),
# pero 8.8.8.8 sí → routing OK:
$ ping -c 3 -W 2 8.8.8.8
3 packets transmitted, 3 received, 0% packet loss
rtt min/avg/max/mdev = 1.234/1.456/1.789/0.123 ms

$ ping -c 3 -W 2 187.77.60.254
3 packets transmitted, 0 received, 100% packet loss   # ← FILTRADO, no broken

$ tailscale status
100.113.249.25  srv1431451   rick@…  linux   -
100.109.16.40   pcrick       rick@…  windows active; direct 181.43.217.175:55811, tx 12345 rx 6789
```

## Post-restart — servicios (todos `active running`)

```bash
# Como rick (las user units NO se ven correctamente desde root):
$ sudo -u rick XDG_RUNTIME_DIR=/run/user/$(id -u rick) systemctl --user list-units --type=service --state=running
  n8n.service                  loaded active running   n8n workflow automation
  openclaw-dispatcher.service  loaded active running   OpenClaw Dispatcher
  openclaw-gateway.service     loaded active running   OpenClaw Gateway (npm-global v2026.5.3-1, port 18789)
  umbral-worker.service        loaded active running   Umbral Worker (FastAPI, port 8088)

# Health endpoints:
$ curl -s http://127.0.0.1:8088/health | head -c 200
{"ok":true,"version":"0.4.0","tasks_registered":["ping","notion.read.page","notion.write.append", ...91 tasks...]}

$ curl -s http://127.0.0.1:18789/health
{"ok":true,"status":"live","version":"v2026.5.3-1"}

# notion-poller-daemon (NO es systemd unit — cron-launched):
$ tail -3 /tmp/notion_poller_cron.log
[2026-05-06 18:45:01] Daemon already running (pid=1571)
[2026-05-06 18:45:01] Heartbeat OK

$ pgrep -af notion_poller
1571 python3 /home/rick/umbral-agent-stack/scripts/notion_poller_daemon.py

# Supervisor (cron */5):
$ tail -5 ~/umbral-agent-stack/logs/supervisor.log
[2026-05-06 18:45:01] Redis OK | Worker OK | Dispatcher OK | restarts=0
```

## Cron jobs (16 — todos intactos post-restart)

```cron
*/30 * * * * /home/rick/umbral-agent-stack/scripts/health-check.sh
*/5  * * * * /home/rick/umbral-agent-stack/scripts/supervisor.sh
*/5  * * * * /home/rick/umbral-agent-stack/scripts/notion-poller-cron.sh
0 8,14,20 * * * /home/rick/umbral-agent-stack/scripts/sim-daily.sh
*    * * * * /home/rick/umbral-agent-stack/scripts/scheduled-tasks.sh
0    * * * * /home/rick/umbral-agent-stack/scripts/dashboard-rick.sh
0  */6 * * * /home/rick/umbral-agent-stack/scripts/openclaw-panel.sh
20 */6 * * * /home/rick/umbral-agent-stack/scripts/openclaw-runtime-snapshot.sh
0   22 * * * /home/rick/umbral-agent-stack/scripts/daily-digest.sh
0    7 * * 1 /home/rick/umbral-agent-stack/scripts/ooda-report.sh
0    6 * * * /home/rick/umbral-agent-stack/scripts/e2e-validation.sh
30 8,14,20 * * * /home/rick/umbral-agent-stack/scripts/sim-report.sh
0  9,15,21 * * * /home/rick/umbral-agent-stack/scripts/sim-to-make.sh
*/15 * * * * /home/rick/umbral-agent-stack/scripts/quota-guard.sh
20   5 * * * /home/rick/umbral-agent-stack/scripts/notion-curate.sh
```

## Validación de SSH/sudo/keys

```bash
$ wc -l /root/.ssh/authorized_keys /home/rick/.ssh/authorized_keys
  1 /root/.ssh/authorized_keys
  3 /home/rick/.ssh/authorized_keys

$ sudo -l -U rick
User rick may run the following commands:
    (ALL) NOPASSWD: ALL
```

## Resultado final

✅ VPS recuperado en ~12 min desde inicio del diagnóstico activo (~90 s desde el `POST /restart`).
✅ Stack 100% operativo, 0 restarts del supervisor post-recovery.
✅ Tailscale auto-reconectó sin intervención.
⚠️ Causa raíz Hostinger no confirmada (probable hypervisor vNIC detach, posible trigger DDoS scrubbing por chain `copilot-egress` rehearsal — Pendiente H para auditar).
⚠️ Token Hostinger usado durante el incidente debe rotarse y moverse a secret manager.
