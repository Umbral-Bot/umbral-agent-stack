# Runbook: Apagar telemetría Anthropic

**Status:** v1 — escrito 2026-05-06 por Copilot Chat (notion-governance) como cierre parcial de O9 del Plan Q2-2026.
**Owner:** David (ejecución manual; sin automatización).
**Scope:** quitar telemetría/data-collection en superficies Anthropic instaladas en el tarro y en VPS. **NO toca** Codex/OpenAI/GitHub Copilot.

---

## 1. Por qué (criterio C2 de R4 del plan)

El plan declara O9 como **kill switch L4 de R4 (riesgo de exposición de datos)**. La telemetría Anthropic puede enviar partes de prompts/outputs a servidores Anthropic para mejora de producto. En el contexto de Umbral (Notion live, transcripciones Granola con datos de clientes, código propietario en `umbral-agent-stack`), esto es **inaceptable por defecto**.

Mantenemos Codex/OpenAI/Copilot porque (a) están autorizados explícitamente, (b) cubren el flujo principal, (c) no hay decisión de removerlos.

---

## 2. Superficies a apagar

### 2.1. Claude Desktop (tarro Windows)

Ruta config: `%APPDATA%\Claude\config.json` (Windows) o `~/Library/Application Support/Claude/config.json` (macOS).

```json
{
  "telemetry": {
    "enabled": false
  },
  "analytics": {
    "enabled": false
  }
}
```

Verificar en UI: `Settings → Privacy → Send anonymous usage data` = OFF.

Validación:
```powershell
# Tarro Windows:
Get-Content "$env:APPDATA\Claude\config.json" | Select-String "telemetry|analytics"
```

### 2.2. Claude Code (CLI / VS Code extension)

#### CLI (`claude-code` o `claude` binary)

```bash
# Variables de entorno globales (agregar a ~/.bashrc o ~/.zshrc en VPS, $PROFILE en tarro):
export DISABLE_TELEMETRY=1
export DISABLE_AUTOUPDATER=0    # mantener auto-update OK
export DO_NOT_TRACK=1
```

Algunas versiones soportan flag explícito:
```bash
claude --no-telemetry <prompt>
```

#### VS Code extension

`settings.json` (workspace o user):
```json
{
  "telemetry.telemetryLevel": "off",
  "claude.telemetry.enabled": false,
  "claude.analytics.enabled": false
}
```

### 2.3. MCPs Anthropic-side

Algunos MCPs (filesystem, github, etc.) pueden tener telemetría propia. Auditar:
```bash
# Listar MCPs activos:
ls -la ~/.config/claude/mcp/ 2>/dev/null
ls -la "$env:APPDATA\Claude\mcp" 2>$null    # Windows
```

Por cada MCP encontrado:
- Buscar `telemetry`/`analytics`/`tracking` en su config.
- Apagar explícitamente.

### 2.4. Variables de entorno globales (defensivas)

Agregar a `~/.bashrc` (VPS) y `$PROFILE` (tarro PowerShell):

```bash
# Anti-telemetry hard kill:
export ANTHROPIC_TELEMETRY=0
export DISABLE_TELEMETRY=1
export DO_NOT_TRACK=1
export TELEMETRY_DISABLED=1
```

PowerShell tarro (`$PROFILE`):
```powershell
$env:ANTHROPIC_TELEMETRY = "0"
$env:DISABLE_TELEMETRY = "1"
$env:DO_NOT_TRACK = "1"
$env:TELEMETRY_DISABLED = "1"
```

---

## 3. NO tocar

- GitHub Copilot (Chat, CLI, extensión) → autorizado.
- Codex / OpenAI / Azure OpenAI → autorizado.
- VS Code telemetry settings que afecten otras extensiones (revisar selectivamente, no apagar all).
- Cursor (si instalado) → decisión separada.

---

## 4. Validación post-apagado

### 4.1. Network audit (manual, opcional)

Durante una sesión Claude Desktop / Claude Code:
```bash
# VPS:
sudo tcpdump -i any -nn 'host telemetry.anthropic.com or host events.anthropic.com or host stats.anthropic.com' &
# Ejecutar 5 prompts. Esperado: 0 paquetes capturados.
```

### 4.2. Config diff

```bash
# Tarro:
diff ~/.claude/config.json.bak ~/.claude/config.json
# Esperado: solo cambios de telemetry/analytics.
```

---

## 5. Checklist ejecución

- [ ] Backup configs: `cp ~/.claude/config.json ~/.claude/config.json.bak.$(date +%F)`.
- [ ] Apagar Claude Desktop UI Settings → Privacy.
- [ ] Editar `config.json` Claude Desktop.
- [ ] Apagar Claude Code CLI (env vars).
- [ ] Apagar Claude Code VS Code extension settings.
- [ ] Auditar MCPs Anthropic-side.
- [ ] Setear env vars defensivas en `~/.bashrc` y `$PROFILE`.
- [ ] Reiniciar Claude Desktop y VS Code para que tomen settings.
- [ ] Validación opcional: tcpdump 5 min sin tráfico a `*.anthropic.com` excepto API calls reales.

---

## 6. Estado del cierre O9

Este runbook + `runbook-copilot-cli-via-ssh-from-tarro.md` cierran el **componente documental** de O9. **Falta:**

- [ ] Ejecución real del checklist sección 5 (David, ~30 min).
- [ ] Test 1 prompt desde tarro hacia worker remoto vía SSH (validación pattern Copilot CLI vía SSH).
- [ ] Decisión: ¿quién dispara el SSH para tournaments? → ya respondido en `runbook-copilot-cli-via-ssh-from-tarro.md` sección 4 (David, paralelo a Rick).

**Tras ejecución:** marcar O9 ✅ en `notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md` línea 525.
