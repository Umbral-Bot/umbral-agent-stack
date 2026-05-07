# Runbook: Copilot CLI desde tarro vía SSH

**Status:** v1 — escrito 2026-05-06 por Copilot Chat (notion-governance) como cierre parcial de O9 del Plan Q2-2026.
**Owner:** David + Copilot Chat (pareja humano-agente).
**Pattern:** lanzar Copilot CLI (`copilot`) en VPS desde una sesión local de VS Code → terminal SSH, manteniendo input/output bidireccional para ejecutar tournaments y tareas multi-agente sin cargar la máquina local.

---

## 1. Por qué este pattern

El **tarro** (laptop personal de David) es para edición, browser, Notion, Granola. La **VPS** (`rick@<vps>`) tiene CPU/RAM/red para ejecutar Copilot CLI con sandboxes Docker rootless (PR #324, F8B). Ejecutar Copilot CLI directamente en el tarro:

1. Compite por CPU con Notion + browser + IDE.
2. No tiene acceso al sandbox Docker rootless + nft de la VPS.
3. Pierde la trazabilidad ops_log (`~/.config/umbral/ops_log.jsonl` vive en VPS).
4. No puede coordinar con Rick / OpenClaw nativos (corren en VPS).

**Solución:** sesión `ssh -t` interactiva con TTY desde terminal de VS Code en tarro, ejecutar `copilot` remoto, recibir streaming en local.

---

## 2. Pre-requisitos (verificar una vez)

### 2.1. SSH config local (tarro, `~/.ssh/config` Windows)

```
Host vps-umbral
  HostName <vps-ip-or-domain>
  User rick
  IdentityFile ~/.ssh/id_ed25519_umbral
  ServerAliveInterval 60
  ServerAliveCountMax 3
  RequestTTY yes
```

Test:
```powershell
ssh vps-umbral "echo ok && whoami && pwd"
```
Esperado: `ok\nrick\n/home/rick`.

### 2.2. Copilot CLI instalado en VPS

```bash
ssh vps-umbral "which copilot && copilot --version"
```
Si no está: instalar siguiendo `gh.io/copilot-cli` (npm global o binary). Ver runbook complementario `runbook-copilot-cli-install.md` (TODO crear si no existe).

### 2.3. GitHub auth en VPS

```bash
ssh vps-umbral "gh auth status"
```
Esperado: `Logged in to github.com as <user> (oauth_token)` con scopes Copilot. Si falla → `gh auth login --web` y completar device flow desde browser local.

### 2.4. Sandbox Docker rootless + nft activo

```bash
ssh vps-umbral "docker ps && systemctl --user status docker"
```
Si Plan A activo: `docker ps` debe responder. Si pivote a Plan B (bubblewrap), ver registry `agents-canonical.yaml :: sandbox_runtime_open_question.plan_b`.

---

## 3. Lanzar sesión interactiva

### 3.1. Modo simple (un prompt one-shot)

Desde terminal VS Code en tarro:
```powershell
ssh -t vps-umbral "cd /home/rick/umbral-agent-stack && copilot 'analizá worker/tasks/granola.py y proponé refactor para reducir longitud'"
```

### 3.2. Modo sesión continua (recomendado para tournaments)

```powershell
ssh -t vps-umbral
# Ya dentro de la VPS:
cd /home/rick/umbral-agent-stack
copilot
# Sesión interactiva — cada prompt se envía, output streamea de vuelta al tarro.
```

Salir: `Ctrl+D` o `exit`. La sesión Copilot termina al cerrar SSH.

### 3.3. Modo background con `tmux` (para tournaments largos)

```powershell
ssh -t vps-umbral
tmux new -s copilot-tournament
copilot
# Detach: Ctrl+B, D
# Reattach desde tarro otro día:
ssh -t vps-umbral "tmux attach -t copilot-tournament"
```

---

## 4. Coordinación con Rick (¿quién dispara el SSH?)

**Decisión de diseño 2026-05-06:** David dispara el SSH manualmente desde el tarro **mientras** Rick ejecuta sus tareas autónomas en paralelo (publishing, monitoring, etc.). Copilot CLI en VPS es un canal **paralelo** a Rick, no subordinado.

- Copilot CLI vía SSH = trabajo de plataforma / desarrollo / tournaments (David coordinando con Copilot Chat).
- Rick = operaciones autónomas (publishing, daily reports, smart replies).
- Ambos comparten VPS pero no comparten estado de sesión.
- Si un tournament requiere coordinación con Rick → mailbox `.agents/mailbox/` (no en sesión Copilot CLI).

**Anti-pattern:** Rick lanzando Copilot CLI por su cuenta. Rick es agente OpenClaw, no orquesta sesiones humano-agente.

---

## 5. Métricas y trazabilidad

Cada sesión Copilot CLI vía SSH genera:
- `~/.config/umbral/ops_log.jsonl` en VPS (eventos `copilot.session.*` si está instrumentado).
- Comandos shell quedan en `~/.bash_history` de VPS.

Para tournaments formales, capturar inicio/fin manualmente:
```bash
echo '{"event":"copilot.tournament.start","ts":"'$(date -u +%FT%TZ)'","issue":"<id>","lanes":<n>}' >> ~/.config/umbral/ops_log.jsonl
# ... ejecutar tournament ...
echo '{"event":"copilot.tournament.end","ts":"'$(date -u +%FT%TZ)'","issue":"<id>","prs":[<urls>]}' >> ~/.config/umbral/ops_log.jsonl
```

---

## 6. Test mínimo (validación del pattern)

```powershell
# Desde tarro:
ssh -t vps-umbral "cd /home/rick/umbral-agent-stack && copilot 'di hola y mostrá pwd'"
```

Esperado:
1. SSH conecta sin password (key-based).
2. Copilot responde con saludo + `/home/rick/umbral-agent-stack`.
3. Output llega al terminal de VS Code en tarro sin lag perceptible (>2s = revisar `ServerAliveInterval`).
4. `Ctrl+C` corta la sesión limpiamente.

---

## 7. Troubleshooting

| Síntoma | Causa probable | Fix |
|---|---|---|
| `Pseudo-terminal will not be allocated` | falta `-t` | usar `ssh -t` |
| Output cortado mid-stream | SSH timeout | `ServerAliveInterval 60` en `~/.ssh/config` |
| `copilot: command not found` | no instalado en VPS | `npm i -g @githubnext/github-copilot-cli` o binary |
| `gh auth required` | sesión expirada | `gh auth login --web` desde VPS |
| Sandbox Docker no arranca | servicio caído | `systemctl --user start docker` o ver `agents-canonical.yaml` Plan B |
| Tarro pierde sesión | red local inestable | usar `tmux` (sección 3.3) |

---

## 8. Pendiente (referenciado desde plan O9)

- [ ] Telemetría Anthropic off (Claude Desktop/Code/MCPs). **NO está en este runbook** — ver `docs/runbooks/anthropic-telemetry-off.md` cuando se cree.
- [ ] Wrapper script `tarro-copilot.ps1` que encapsule el pattern sección 3.2 (futuro).
- [ ] Instrumentación automática `ops_log` `copilot.session.*` (futuro, post-O7.0 spike).

---

**Cierra parcialmente:** O9 del Plan Q2-2026 (`notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md` línea 525).
**Pendiente para cierre total O9:** runbook telemetría Anthropic off + ejecución del flip de flags.
