# Runbook — VPS Hostinger SSH freeze (port 22 unreachable)

> Síntoma: `ssh rick@vps-umbral` queda en "Connection timed out" pero la VM en Hostinger figura `state=running`.
> Recurrencia observada: 3x en ~5 días (2026-05-04 commit `1d1c3c6` "VPS deploy + smoke pending (SSH timeout)", 2026-05-05 SSH freeze, 2026-05-06 **hypervisor network detach** confirmado — ver Incident 2026-05-06 abajo).
> Evidencia inicial Hostinger MCP/API: CPU 3-13 %, RAM ~2.8/8 GB, sin acciones reboot recientes → **descartado** crash hipervisor / OOM masivo.
> Hipótesis (orden de probabilidad post-2026-05-06): **hypervisor network detach** → sshd crash → fail2ban ban → ufw flap → kernel hung_task.

VM: `1431451` (`srv1431451.hstgr.cloud`, `187.77.60.169`, `2a02:4780:6e:2301::1`), Ubuntu 24.04 LTS.

## ⚠️ Lección 2026-05-06 (leer ANTES de aplicar las fases)

Si **dentro de la VM** (vía consola VNC del panel Hostinger) ocurre lo siguiente:

- `ping -c 3 <gateway>` → 100% packet loss, AUNQUE el gateway esté en la misma /24
- `curl https://api.ipify.org` → `HTTP:000` (timeout)
- `tcpdump -i eth0 'tcp port 22'` → **0 paquetes capturados** durante un probe externo
- pero `eth0` está UP con la IP correcta y `sshd` listening

→ **NO es problema de la VM**. Es un **detach a nivel hypervisor**: el vNIC de la VM perdió su binding al virtual switch de Hostinger. Ningún cambio en `iptables`/`ufw`/`/etc/ssh/sshd_config` lo va a arreglar. Tailscale **TAMPOCO sirve** como fallback porque también requiere outbound, que está muerto.

**Recovery comprobado**: `POST /virtual-machines/{id}/restart` vía Hostinger API. Re-attacha el vNIC al boot. Tiempo: ~11 segundos para que la action complete + ~60-90 s adicionales para boot completo. Ver Incident 2026-05-06 al final del archivo.

---

## Fase 0 — Confirmar el síntoma SIN reboot ciego

Antes de pedir reboot a Hostinger, **descartar** que sea un problema local de tu IP o de IPv4:

```powershell
# 1. ¿Puerto 22 alcanzable IPv4?
Test-NetConnection -ComputerName 187.77.60.169 -Port 22
# 2. ¿IPv6 funciona? (si sshd sigue vivo pero ufw/IP local bloquea v4)
ssh -6 -o ConnectTimeout=10 rick@2a02:4780:6e:2301::1 "uptime"
# 3. ¿Otro puerto del stack responde? Worker FastAPI si tienes túnel, o ping ICMP
ping 187.77.60.169
# 4. ¿Hostinger ve la VM viva? (API)
$h = @{ Authorization = "Bearer $env:HOSTINGER_API_TOKEN" }
Invoke-RestMethod "https://developers.hostinger.com/api/vps/v1/virtual-machines" -Headers $h |
  Where-Object { $_.id -eq 1431451 } | Select-Object state, hostname
# 5. CPU/RAM últimas horas — si están planos a 0 = kernel hung; si fluctúan = sshd/red, no kernel
$from = (Get-Date).ToUniversalTime().AddHours(-3).ToString("o")
$to   = (Get-Date).ToUniversalTime().ToString("o")
Invoke-RestMethod "https://developers.hostinger.com/api/vps/v1/virtual-machines/1431451/metrics?date_from=$from&date_to=$to" -Headers $h | ConvertTo-Json -Depth 4
# 6. Hostinger panel firewall — verificar que NO se haya colado una regla deny
Invoke-RestMethod "https://developers.hostinger.com/api/vps/v1/firewall" -Headers $h | ConvertTo-Json -Depth 4
# Si retorna [] o firewall_group_id es null → panel firewall NO es la causa.
# OJO: este endpoint NO refleja DDoS scrubbing ni null-routes a nivel edge Hostinger.
```

**Decisión:**
- Métricas vivas + IPv6 ssh OK → sshd_v4/ufw/fail2ban. Saltar a Fase 2 sin reboot.
- Métricas vivas + IPv6 ssh fail → sshd muerto, **O hypervisor network detach** (ver Fase 0bis). Intentar Fase 1A (rescue) antes de reboot.
- Métricas planas a 0 / no fluctúan → kernel hung. Fase 1B (reboot) directo, pero **snapshot primero**.
- VM `state != running` → reportar a Hostinger; no es bug nuestro.

## Fase 0bis — Diagnóstico INTRA-VM (vía consola VNC del panel Hostinger)

Si la Fase 0 no arroja una causa clara, abrir la **Consola del navegador** desde Hostinger panel (es el único acceso cuando SSH está caído) y correr COMO ROOT:

```bash
# A) sshd vivo y escuchando?
systemctl status ssh --no-pager | head -10
ss -tlnp | grep :22

# B) Inbound — ¿llegan paquetes al NIC en absoluto?
# (correr en una sesión, mientras desde afuera intentás `Test-NetConnection :22`)
timeout 10 tcpdump -i eth0 -n 'tcp port 22' -c 5
# 0 capturas → bloqueo UPSTREAM del NIC (firewall edge, null-route, hypervisor detach)
# capturas con SYN sin SYN-ACK → sshd o ufw del lado VM

# C) Outbound — ¿la VM puede salir a Internet?
curl -sS -o /dev/null -w "HTTP:%{http_code} time:%{time_total}\n" --max-time 5 https://api.ipify.org
# HTTP:200 → outbound OK. HTTP:000 timeout → outbound muerto.

# D) Gateway — ¿la VM ve su default gateway en su propia /24?
ip route | grep default
GW=$(ip route | awk '/default/ {print $3; exit}')
ping -c 3 -W 2 "$GW"
ping -c 3 -W 2 8.8.8.8
# Gateway en misma /24 con 100% loss + 8.8.8.8 también 100% loss
# → HYPERVISOR NETWORK DETACH. Saltar a Fase 1B (restart vía API). NO seguir tocando iptables.

# E) iptables INPUT counters
iptables -L INPUT -n -v --line-numbers | head -20
# Si la regla pos-1 ACCEPT tcp:22 tiene 0 hits durante el probe externo → confirma (B): no llegan paquetes.
```

### Tabla de decisión Fase 0bis

| Outbound | Inbound (tcpdump) | Gateway ping | Diagnóstico | Ir a |
|---|---|---|---|---|
| OK | 0 packets | OK | Firewall edge Hostinger / IP banned | Fase 1A + ticket |
| OK | SYN sin SYN-ACK | OK | sshd o ufw VM | Fase 1A `restart ssh` |
| **DEAD** | **0 packets** | **DEAD** | **Hypervisor network detach** | **Fase 1B (restart API)** |
| OK | OK con tráfico previo | OK | fail2ban baneo tu IP | Fase 1A `fail2ban-client unban` |

## Fase 1A — Recuperación SIN reboot (si hipervisor ve la VM viva)

```powershell
# 1. Snapshot defensivo (si no hay uno de hoy)
$h = @{ Authorization = "Bearer $env:HOSTINGER_API_TOKEN"; "Content-Type"="application/json" }
Invoke-RestMethod -Method Post "https://developers.hostinger.com/api/vps/v1/virtual-machines/1431451/snapshot" -Headers $h
# 2. Abrir VNC/Browser console desde panel Hostinger → loguear como rick → ejecutar:
#    sudo systemctl status ssh && sudo journalctl -u ssh -n 100
#    sudo systemctl restart ssh
#    sudo ufw status verbose
#    sudo fail2ban-client status sshd      # ver IPs baneadas
#    sudo fail2ban-client unban <tu-ip-publica>
# 3. Re-test SSH desde Windows.
```

## Fase 1B — Reboot controlado (último recurso O respuesta a hypervisor detach)

```powershell
# Snapshot OBLIGATORIO si no se hizo en 1A
$h = @{ Authorization = "Bearer $env:HOSTINGER_API_TOKEN"; "Content-Type"="application/json" }
Invoke-RestMethod -Method Post "https://developers.hostinger.com/api/vps/v1/virtual-machines/1431451/snapshot" -Headers $h
# Restart vía API (equivalente a botón panel)
$action = Invoke-RestMethod -Method Post "https://developers.hostinger.com/api/vps/v1/virtual-machines/1431451/restart" -Headers $h
$action  # ej: { id: 92742006, name: "ct_restart", state: "sent", created_at: "2026-05-06T18:36:44Z" }
# Polear estado de la action (~10-15 s para completar)
Start-Sleep -Seconds 30
Invoke-RestMethod "https://developers.hostinger.com/api/vps/v1/virtual-machines/1431451/actions/$($action.id)" -Headers $h |
  Select-Object id, name, state, created_at, updated_at
# state="success" → boot en curso. Esperar ~60-90 s adicionales.
# Re-test:
ping 187.77.60.169
Test-NetConnection 187.77.60.169 -Port 22
```

**Si el restart fija un hypervisor network detach** (caso 2026-05-06): la VM vuelve con red en ~90 s y Tailscale auto-reconecta.

**Si NO lo fija**: abrir ticket Hostinger inmediatamente con esta evidencia (NO seguir reintentando):
- VM id, IPv4
- `state=running` antes y después del restart
- Salida intra-VM: `eth0` UP con IP correcta, gateway en misma /24 inalcanzable, `tcpdump 0 packets`, outbound `HTTP:000`
- Action id del restart y su `state=success`
- Pregunta explícita al soporte: *"¿se aplicó DDoS scrubbing, null-route, suspensión de IP, o el vNIC quedó desbindeado del virtual switch? El panel firewall está vacío y la VM está sana internamente."*

## Fase 2 — Forensia post-incidente (correr en los primeros 30 min tras recuperar SSH)

```bash
ssh vps-umbral
# A) Timeline kernel
sudo journalctl -k --since "-3h" | grep -Ei "hung_task|oom|panic|BUG|watchdog|soft lockup|nmi|i/o error|nvme|ufw" | head -100
sudo dmesg -T | tail -300
# B) Auth/SSH
sudo journalctl -u ssh --since "-3h" -n 300
sudo journalctl -u fail2ban --since "-3h" -n 300
sudo grep -E "Failed|Accepted|sshd" /var/log/auth.log | tail -100
sudo fail2ban-client status sshd
# C) Sistema
uptime; last reboot | head; who -b
free -h; df -h; df -i
systemctl --failed
ss -tlnp | grep -E ':22|:8088|:18789'
# D) Procesos pesados
top -b -n 1 -o %MEM | head -25
top -b -n 1 -o %CPU | head -25
# E) Cron / timers que pudieron disparar el evento
systemctl list-timers --all | head -30
crontab -l 2>/dev/null; sudo crontab -l 2>/dev/null
# F) Persistir journald si no lo está (clave para que el PRÓXIMO freeze sea diagnosticable)
grep -E "^Storage" /etc/systemd/journald.conf
# Si dice "auto" o no hay línea: sudo sed -i 's/^#*Storage=.*/Storage=persistent/' /etc/systemd/journald.conf && sudo systemctl restart systemd-journald
```

Guardar todo a archivo en el repo:
```bash
mkdir -p ~/umbral-agent-stack/reports/vps-freeze-$(date +%F)
{ echo "=== uptime ==="; uptime; echo "=== last reboot ==="; last reboot|head;
  echo "=== journal kernel 3h ==="; sudo journalctl -k --since "-3h";
  echo "=== ssh 3h ==="; sudo journalctl -u ssh --since "-3h";
  echo "=== fail2ban 3h ==="; sudo journalctl -u fail2ban --since "-3h";
  echo "=== failed units ==="; systemctl --failed;
  echo "=== top mem ==="; top -b -n1 -o %MEM | head -25;
} > ~/umbral-agent-stack/reports/vps-freeze-$(date +%F)/evidence.txt
```

## Fase 3 — Hardening (tras 2da o 3ra recurrencia con root cause confirmado)

| Causa identificada | Acción |
|---|---|
| `sshd` crashea | Crear drop-in `/etc/systemd/system/ssh.service.d/restart.conf` con `[Service]\nRestart=always\nRestartSec=5s` |
| `fail2ban` te banea | Whitelist IP/CIDR de Chile en `/etc/fail2ban/jail.local` (`ignoreip = ...`) |
| OOM (improbable según métricas actuales) | Añadir 2 GB swap + `MemoryHigh=` en units `umbral-worker`, `openclaw-dispatcher`, `openclaw-gateway` |
| Disco lleno | `journalctl --vacuum-size=500M`, audit `du -sh ~/.cache /var/log /tmp` |
| Kernel hung_task | Apt upgrade kernel + reportar a Hostinger con journal |
| Fugas en gateway npm | Restart-on-RSS hint vía systemd `MemoryMax=1G` |

## Fase 4 — Watchdog automático (post-2da recurrencia)

Cron desde **otro host** (tu Windows o un GitHub Action) que cada 10 min:
1. `Test-NetConnection 187.77.60.169 -Port 22`. Si falla 3 veces consecutivas →
2. Hostinger API `GET /virtual-machines/1431451` para confirmar `state=running`. Si running →
3. POST `/snapshot` (si no hay uno de hoy). Luego POST `/restart`.
4. Notificar Notion DB "Alertas del Supervisor" + Telegram bot.

Script base: `scripts/vps/watchdog-ssh.ps1` (TBD — crear cuando este runbook se aplique 3ra vez).

## Cross-refs

- Roadmap: `notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md` §O8i (primer SSH timeout, PR #296)
- Skill: `.agents/skills/vps-deploy-after-edit/SKILL.md`
- Memoria user: `agent-boundaries.md`, `cross-repo-handoff-rules.md` (regla "VPS Reality Check")
- Incidente OpenClaw SPLIT 2026-05-04 (relacionado por contexto, no por causa): roadmap §O14.2

## Bitácora de incidentes

| Fecha | Síntoma | Diagnóstico | Acción | Root cause |
|---|---|---|---|---|
| 2026-05-04 | SSH timeout durante deploy F7 rehearsal | (no investigado) | Reboot panel Hostinger | TBD (probable hypervisor) |
| 2026-05-05 | SSH timeout 2da vez; Hostinger MCP confirma VM running, CPU 3-13%, RAM 2.8/8 GB | Hipervisor sano externamente; intra-VM no investigado | Reboot | TBD |
| 2026-05-06 | SSH timeout ~14 h tras reboot del 05; VM running, métricas vivas, panel firewall vacío | **Hypervisor network detach** confirmado intra-VM (gateway/8.8.8.8 unreachable, tcpdump 0 packets, outbound HTTP:000) | `POST /restart` API → action `92742006` `ct_restart` `success` en 11 s; ~90 s después red OK, SSH OK, Tailscale auto-reconnect, todos los servicios `active` | **Hypervisor vNIC detach** (causa raíz Hostinger no confirmada — posible DDoS scrubbing o null-route por rehearsal F7 copilot-egress) |

---

## Incident 2026-05-06 — Hypervisor network detach (FULL DETAIL)

### Timeline (UTC)

| Hora | Evento |
|---|---|
| 2026-05-05 ~23:30 | Último reboot conocido (post-rehearsal F7 copilot-cli policy gate). |
| 2026-05-06 ~00:00 | SSH deja de responder. Notebook (Wi-Fi 10.18.138.70 → IP pública móvil) sin acceso. Tailscale tampoco responde. |
| 2026-05-06 14:00 | Inicio del incidente desde Copilot Chat. Diagnóstico iterativo. |
| 2026-05-06 18:30 | Confirmado: `tcpdump -i eth0 -n 'tcp port 22' -c 5` captura 0 paquetes durante probe externo. Bloqueo upstream del NIC. |
| 2026-05-06 18:35 | Confirmado intra-VM: `ping 187.77.60.254` (gateway en misma /24) → 100% loss; `ping 8.8.8.8` → 100% loss; `curl https://api.ipify.org` → `HTTP:000`. **Hypervisor network detach diagnosticado.** |
| 2026-05-06 18:36:44 | `POST /virtual-machines/1431451/restart` vía Hostinger API → action `92742006` `ct_restart` `state=sent`. |
| 2026-05-06 18:36:55 | Action `92742006` `state=success` (11 s). |
| 2026-05-06 18:42 | SSH responde, ping OK (latencia 85-285 ms, TTL 52), `Test-NetConnection -Port 22` `TcpTestSucceeded:True`. |
| 2026-05-06 18:43 | Login `root@187.77.60.169` (con root password Hostinger). `uptime` confirma 6 min de boot. |
| 2026-05-06 18:46 | Verificación intra-VM: outbound OK (HTTP:200, gateway sigue sin responder a ICMP — filtrado normal del edge Hostinger; routing OK porque 8.8.8.8 sí responde). |

### Estado pre-restart (evidencia recolectada)

**Externo (notebook Wi-Fi):**
```
ping 187.77.60.169 → 4/4 timeout
Test-NetConnection -Port 22 → TcpTestSucceeded:False
```

**Hostinger API:**
```
GET /virtual-machines/1431451 → state=running, firewall_group_id=null, actions_lock=unlocked
GET /firewall → []
```

**Intra-VM (consola VNC del panel Hostinger, root):**
```
$ ip -4 addr show eth0 | grep inet
    inet 187.77.60.169/24 brd 187.77.60.255 scope global eth0
$ ip route | grep default
default via 187.77.60.254 dev eth0
$ ping -c 3 -W 2 187.77.60.254
3 packets transmitted, 0 received, 100% packet loss
$ ping -c 3 -W 2 8.8.8.8
3 packets transmitted, 0 received, 100% packet loss
$ curl -sS -o /dev/null -w "HTTP:%{http_code} time:%{time_total}\n" --max-time 10 https://api.ipify.org
HTTP:000 time:10.000
$ timeout 10 tcpdump -i eth0 -n 'tcp port 22' -c 5
0 packets captured
$ systemctl status ssh --no-pager
active (running) since ...  # sshd vivo, escuchando :22
$ ss -tlnp | grep :22
LISTEN 0 128 0.0.0.0:22 ...
$ iptables -L INPUT -n -v --line-numbers | head -10
# pos-1 ACCEPT tcp dpt:22 → 0 hits durante todo el incidente
```

### Acción recovery (literal)

```powershell
# PowerShell desde C:\GitHub\notion-governance
$TOKEN = "XC0EJT3mE9xKmunSd2L84DmnOYG2naBRgQrKzKG736754dda"  # ⚠️ rotar después del incidente
curl.exe -s -X POST -H "Authorization: Bearer $TOKEN" `
  "https://developers.hostinger.com/api/vps/v1/virtual-machines/1431451/restart"
# Output: {"id":92742006,"name":"ct_restart","state":"sent","created_at":"2026-05-06T18:36:44Z","updated_at":"2026-05-06T18:36:44Z"}

Start-Sleep -Seconds 30
curl.exe -s -H "Authorization: Bearer $TOKEN" `
  "https://developers.hostinger.com/api/vps/v1/virtual-machines/1431451/actions/92742006" |
  ConvertFrom-Json | Select-Object id, name, state, created_at, updated_at
# Output: id=92742006, name=ct_restart, state=success, created_at=18:36:44Z, updated_at=18:36:55Z
```

### Estado post-restart (todos los servicios verificados)

| Componente | Estado | Cómo se verificó |
|---|---|---|
| eth0 + outbound | ✅ | `curl https://api.ipify.org` → HTTP:200 time:0.42s |
| Gateway 187.77.60.254 ICMP | ⚠️ filtrado (normal) | Ping no responde pero 8.8.8.8 sí → routing OK |
| Tailscale | ✅ direct | `tailscale status` → `pcrick … active; direct 181.43.217.175:55811` |
| SSH público | ✅ | `Test-NetConnection :22` desde notebook |
| `umbral-worker.service` | ✅ active | `curl http://127.0.0.1:8088/health` → `{"ok":true,"version":"0.4.0","tasks_registered":[...91 tasks...]}` |
| `openclaw-dispatcher.service` | ✅ active | `systemctl --user status` |
| `openclaw-gateway.service` (npm-global) | ✅ active | `curl http://127.0.0.1:18789/health` → `{"ok":true,"status":"live"}` |
| `n8n.service` | ✅ active | pid 977, `node /home/rick/.npm-global/bin/n8n start` |
| `notion-poller-daemon` | ✅ (NO es systemd unit) | Lanzado por cron `*/5 * * * * notion-poller-cron.sh`; `/tmp/notion_poller_cron.log` muestra `Daemon started (pid=1571)` |
| `supervisor.sh` (cron */5) | ✅ | Redis/Worker/Dispatcher OK, 0 restarts |
| iptables INPUT | ✅ limpio | Regla duplicada SSH pos-1 desapareció con el restart (era ephemeral) |
| Tailscale (otros nodos) | parcial | `tarro` offline 43d (pre-existente, no relacionado) |
| Telegram bot | ✅ | Vive dentro de n8n workflows, no es proceso separado |

### Causa raíz (probable, NO confirmada por Hostinger)

**Hypervisor vNIC detach**: el virtual NIC de la VM perdió su binding al virtual switch del nodo Hostinger. La VM siguió corriendo (CPU/RAM normales), pero todo paquete que enviaba se perdía en el hypervisor antes de salir, y todo paquete entrante se descartaba antes de llegar al NIC virtual.

**Trigger candidato a investigar (Pendiente H)**: la branch `rick/copilot-cli-f7-policy-gate-rehearsal-evidence` (chain `copilot-egress` con reglas de iptables agresivas) corrió en paralelo y pudo haber gatillado detección DDoS de Hostinger / null-route automático que se levantó solo durante el restart. El `firewall_group_id=null` y `/firewall` vacío confirman que **NO** fue una regla del panel — habría sido una mitigación a nivel edge no expuesta vía API.

### Lecciones operacionales (críticas)

1. **`tcpdump 0 paquetes en eth0` + `INPUT pos-1 ACCEPT con 0 hits`** = bloqueo **upstream del NIC**. NO es iptables, NO es ufw, NO es sshd. Dejar de tocar el VM.
2. **VM no puede pingear su propio default gateway dentro de su /24** = hypervisor network detach. Restart es el primer recurso.
3. **Tailscale NO es un fallback válido cuando el outbound está muerto.** Tailscale necesita conectarse a sus coordination servers (DERP). Si el hypervisor detacha el vNIC, Tailscale muere también. Usar VNC del panel Hostinger como único acceso de emergencia.
4. **Hostinger API `/firewall` y `firewall_group_id` solo reflejan panel firewall.** No exponen DDoS scrubbing, null-routes, ni binding del vNIC. Que retornen `[]` / `null` NO descarta bloqueo a nivel edge.
5. **`POST /virtual-machines/{id}/restart` es la primera acción reversible** ante un detach sospechado. La action completa en ~10-15 s; el boot completo agrega ~60-90 s.
6. **`uptime` shell siempre gana sobre métricas API.** El campo `uptime` de la API de métricas Hostinger puede lagear.
7. **Token MCP**: literal en `mcp.json` funciona; `${env:VAR}` substitution falla intermitentemente. Bypass directo con `curl.exe -H "Authorization: Bearer <literal>"` siempre funciona y es más rápido cuando el incidente está en curso.
8. **Kodee (chat de Hostinger)**: solo informativo, NO ejecuta acciones de soporte. Ir directo al ticket si el restart no fija el detach.
9. **El root password del VPS Hostinger** está en el panel (Configuración → Contraseña root). Si lo perdiste, `POST /virtual-machines/{id}/root-password` con `{"password":"NUEVO"}`.
10. **Servicios "could not be found"** cuando consultás `systemctl --user` como root → son user units de `rick`. Usar: `sudo -u rick XDG_RUNTIME_DIR=/run/user/$(id -u rick) systemctl --user status <unit>`.
11. **`notion-poller-daemon` NO es systemd unit**, es un daemon plain levantado por cron. Su presencia se verifica por log `/tmp/notion_poller_cron.log` o `pgrep -f notion_poller`, no por `systemctl`.
12. **Health check del repo asume rutas `/home/rick/...`**. Correrlo como root da falsos FAIL (`/root/umbral-agent-stack/...` no existe). Siempre `sudo -u rick bash health-check.sh`.

### Anti-patterns observados (no repetir)

- ❌ Iterar 3 horas sobre `iptables -F`, `ufw reset`, `sshd restart` cuando `tcpdump` ya había confirmado 0 paquetes en eth0.
- ❌ Pedir a Tailscale que "salve" el incidente cuando el outbound estaba muerto.
- ❌ Asumir que `firewall_group_id=null` significa "no hay bloqueo Hostinger". El edge tiene protecciones que NO están en esa API.
- ❌ Reboot ciego sin antes correr Fase 0bis. El restart fue acertado **esta vez** porque hubo evidencia de detach; rebootear ciego en otros casos pierde estado y no diagnostica.

### Cross-refs del incidente

- Evidencia raw: [`reports/vps-freeze-2026-05-06/`](../reports/vps-freeze-2026-05-06/)
- Changelog: [`changelog/2026-05-06.md`](../changelog/2026-05-06.md)
- Branch a auditar (Pendiente H): `rick/copilot-cli-f7-policy-gate-rehearsal-evidence` — verificar si la rehearsal del chain `copilot-egress` correlaciona temporalmente con el detach.
- Token Hostinger usado durante el incidente: `XC0EJT3mE9xKmunSd2L84DmnOYG2naBRgQrKzKG736754dda` → **rotar** post-incidente y mover a secret manager (NO dejar en `mcp.json` literal).
