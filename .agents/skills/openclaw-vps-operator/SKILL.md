---
name: openclaw-vps-operator
description: "Operar OpenClaw runtime desde la VPS de forma segura, trazable y reversible. Usar cuando la tarea toque ~/.openclaw/openclaw.json, openclaw-gateway.service, aliases, modelos, smoke gateway, journalctl --user, backup, patch, restart, rollback, o cualquier acción runtime sobre OpenClaw en la VPS de Umbral. NO usar para Azure, Foundry, Notion, n8n, RRSS, O16.2, ni desde Windows local."
---

# Skill: openclaw-vps-operator

## Propósito

Operar el runtime de OpenClaw en la VPS de Umbral (Hostinger, Ubuntu 24.04,
usuario `rick`) de forma **segura, trazable y reversible**. Esta skill cubre
las acciones autorizadas sobre `~/.openclaw/openclaw.json` y el servicio
`openclaw-gateway.service` ejecutado vía `systemctl --user`.

Esta skill NO cubre:

- Azure / Azure OpenAI / Foundry (eso es Copilot Windows).
- Notion productivo, n8n, RRSS, O16.2.
- Docker, GHCR, gestión de puertos o firewall.
- Operación desde Windows local.

Si la superficie no es VPS, abortar y devolver a Coordinador de Agentes.

## Preflight obligatorio

Antes de cualquier escritura, confirmar y dejar registrado:

1. `hostname` y `whoami` muestran VPS y usuario `rick`.
2. `~/umbral-agent-stack` existe y es un repo git limpio (o el cambio en
   curso está autorizado).
3. `~/.openclaw/openclaw.json` existe.
4. `systemctl --user is-active openclaw-gateway` devuelve `active`.
5. Existe directorio de evidencia `~/.coord-ag-evidence/<task>/`.
6. Backup planificado: `~/.coord-ag-evidence/<task>/openclaw.json.bak`.
7. Autorización explícita de David citada textualmente en la evidencia.

Si cualquiera falla → STOP y reportar.

## Operaciones permitidas (con autorización explícita por operación)

- **Lectura de config sin exponer keys**:

  ```bash
  python3 -c "import json; d=json.load(open('$HOME/.openclaw/openclaw.json')); \
    print(sorted(d.keys()))"
  ```

- **Backup previo a cualquier patch**:

  ```bash
  mkdir -p ~/.coord-ag-evidence/<task>
  cp -a ~/.openclaw/openclaw.json \
        ~/.coord-ag-evidence/<task>/openclaw.json.bak
  ```

- **Diff propuesto antes de aplicar** (mostrar al Coordinador / David, no
  aplicar hasta tener go).

- **Validación JSON post-patch**:

  ```bash
  python3 -c "import json,sys; json.load(open(sys.argv[1]))" \
    ~/.openclaw/openclaw.json
  ```

- **Restart con autorización explícita**:

  ```bash
  systemctl --user restart openclaw-gateway
  systemctl --user is-active openclaw-gateway
  ```

- **Lectura de logs sin exponer secretos**:

  ```bash
  journalctl --user -u openclaw-gateway --since "5 min ago" --no-pager \
    | grep -vE 'sk-|ghp_|github_pat_|AZURE_OPENAI_API_KEY|OPENCLAW_GATEWAY_TOKEN|client_secret|refresh_token|NOTION_API_KEY'
  ```

- **Smoke test de alias** (sin imprimir tokens en stdout):

  ```bash
  # Ejemplo, NO imprimir Authorization header:
  curl -fsS -o /tmp/smoke.json -w "%{http_code}\n" \
    -H "Authorization: Bearer $OPENCLAW_GATEWAY_TOKEN" \
    http://127.0.0.1:<port>/health
  ```

- **Rollback** (ver sección dedicada).

## Operaciones PROHIBIDAS sin autorización explícita

- Cualquier `restart`, `reload`, `enable` o `disable` de servicios.
- Editar `~/.openclaw/openclaw.json` u otros archivos de config.
- Cambiar el default global de modelo.
- Borrar modelos / aliases existentes.
- Abrir puertos, cambiar firewall, modificar nginx, ufw, iptables.
- Instalar paquetes (apt / pip / npm), globales o de usuario.
- Tocar Azure, Foundry, Notion, n8n, RRSS, O16.2, Docker, GHCR.
- Imprimir cualquier secreto en logs, evidencia o respuestas.

## Evidencia

Cada ejecución deja:

```
~/.coord-ag-evidence/<task>/<YYYY-MM-DD-HHMM>-evidence.txt
```

Contenido mínimo:

- Comandos ejecutados (sin valores secretos).
- Outputs relevantes (recortar líneas que parezcan keys).
- Diff aplicado (si aplica).
- Estado de servicio antes y después.
- Resultado: PASS / PARTIAL / FAIL.
- Próxima acción sugerida.

## Rollback documentado

1. Restaurar backup:

   ```bash
   cp -a ~/.coord-ag-evidence/<task>/openclaw.json.bak \
         ~/.openclaw/openclaw.json
   ```

2. Validar JSON:

   ```bash
   python3 -c "import json,sys; json.load(open(sys.argv[1]))" \
     ~/.openclaw/openclaw.json
   ```

3. Restart con autorización:

   ```bash
   systemctl --user restart openclaw-gateway
   ```

4. Health check mínimo:

   ```bash
   systemctl --user is-active openclaw-gateway
   journalctl --user -u openclaw-gateway --since "1 min ago" --no-pager | tail -50
   ```

5. Reportar resultado a Coordinador de Agentes con path de evidencia.

## Stop conditions

- No estás en la VPS (hostname o repo no coincide).
- Falta `~/.openclaw/openclaw.json`.
- No existe backup previo y se pide aplicar patch.
- Falta autorización explícita y citable de David.
- El patch tocaría el default global sin autorización.
- JSON queda inválido tras patch (rollback inmediato).
- Gateway no levanta tras restart (rollback inmediato).
- Logs muestran auth/secrets en claro (escalar a David, no commitear).
- Drift entre lo que pidió Coordinador y el estado real del runtime.

## Notas de uso

- Esta skill es invocada principalmente por el custom agent
  **Operador OpenClaw VPS** (`.github/agents/operador-openclaw-vps.agent.md`).
- También puede leerse manualmente como runbook por David o por otro agente
  con autorización equivalente.
- No reemplaza a `.agents/skills/vps-deploy-after-edit/SKILL.md`, que cubre
  deploys de código de servicios (worker, dispatcher, etc.). Esta skill cubre
  específicamente la config y el runtime de OpenClaw.
