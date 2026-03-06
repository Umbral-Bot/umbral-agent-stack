---
name: openclaw-gateway
description: >-
  Configurar sesiones, agentes y workspace en el Gateway OpenClaw dentro del
  Umbral Agent Stack. Incluye arquitectura Gateway, Pi integration, agents.list,
  bindings, Agent Loop, System Prompt, Context, Agent Workspace, OAuth, Presence,
  multi-agent routing y referencias oficiales. Use when "openclaw config",
  "agents.list", "workspace", "sessions", "bootstrap", "AGENTS.md SOUL.md",
  "auth-profiles", "context window", "compaction", "bindings".
metadata:
  openclaw:
    emoji: "\U0001F99E"
    requires:
      env: []
---

# OpenClaw Gateway — Sesiones, Agentes y Workspace

**Para Rick:** Usar este skill para configurar sesiones, agentes y workspace dentro del Gateway OpenClaw en el proyecto Umbral Agent Stack: arquitectura, `openclaw.json`, `agents.list`, bindings, Agent Loop, System Prompt, Context, workspace (bootstrap, git backup), OAuth, Presence e integración Pi. Incluye el contexto del repo (Control Plane VPS + Execution Plane VM, Worker, Redis, Notion).

Documentación oficial: https://docs.openclaw.ai/  
Índice completo: https://docs.openclaw.ai/llms.txt

---

## Cuándo usar esta skill

Usar esta skill cuando la tarea implique:

1. Crear o ajustar `~/.openclaw/openclaw.json` para uno o varios agentes.
2. Definir `workspace`, `agentDir`, `sessions`, `bindings` o `accountId`.
3. Enrutar mensajes por canal, cuenta, peer, guild, team o grupo.
4. Configurar múltiples cuentas en WhatsApp/Telegram/Discord/Slack.
5. Resolver mezcla accidental de sesiones, workspaces o credenciales.
6. Configurar sandbox por agente o restricciones de tools.
7. Auditar cómo se construye el contexto, system prompt y skills.
8. Diagnosticar por qué un mensaje llegó al agente equivocado.
9. Explicar `sessionKey`, `sessionId`, main session, compaction o queue modes.
10. Preparar **un gateway + varios agentes** o **varias cuentas por canal**.

---

## Reglas maestras (no omitir)

1. **Gateway único por host:** Un solo Gateway de larga vida por host; es el único que abre la sesión de WhatsApp. Clientes y nodos se conectan al mismo WebSocket. Canvas: `/__openclaw__/canvas/`, `/__openclaw__/a2ui/`.

2. **OpenClaw usa runtime embebido, no Pi CLI:** No ejecuta `pi` como subprocess ni RPC. Importa el SDK y crea sesiones con `createAgentSession()`. No consulta `~/.pi/agent` ni `<workspace>/.pi`. OpenClaw es dueño de session management, tool wiring, system prompt, discovery de skills, auth routing y failover.

3. **Un agente = un cerebro aislado:** Cada `agentId` debe tener workspace propio, agentDir propio, sessions propias, auth-profiles.json propio. **Nunca** reutilizar el mismo `agentDir` entre agentes (colisión de credenciales, sesiones y estado).

4. **El workspace NO es un sandbox duro:** Es el cwd por defecto de tools y contexto. Sin sandbox, las rutas absolutas pueden salir del workspace. Para aislamiento real usar `agents.defaults.sandbox` o `agents.list[].sandbox`. Con sandbox y `workspaceAccess` no `rw`, tools trabajan en workspace bajo `~/.openclaw/sandboxes`.

5. **Las sesiones persisten por agente:** Transcripciones en `~/.openclaw/agents/<agentId>/sessions/<SessionId>.jsonl`. SessionId lo elige OpenClaw y es estable. No se leen sesiones legacy Pi/Tau.

6. **Skills cargan por prioridad:** (1) `<workspace>/skills`, (2) `~/.openclaw/skills`, (3) bundled. En conflicto de nombre, **workspace gana**.

---

## Proyecto: Umbral Agent Stack (recordatorio)

Sistema multi-agente, multi-modelo: **Rick** (meta-orquestador) gestiona equipos de agentes AI en una arquitectura **split**:

```
David ──► Telegram/Notion ──► VPS (Control Plane 24/7) ──Tailscale──► VM Windows (Execution Plane)
                                    │                                         │
                                    ├── Rick (meta-orquestador)               ├── LangGraph runtime
                                    ├── ModelRouter → TeamRouter              ├── Worker FastAPI :8088
                                    ├── LiteLLM (5 LLMs)                      ├── PAD/RPA adapters
                                    └── Redis (cola+estado)                   └── Langfuse + ChromaDB
```

- **Control Plane (VPS Hostinger):** Rick + OpenClaw + Dispatcher + LiteLLM + Redis → 24/7. Puertos Gateway: 18789 (WS), 18791 (HTTP).
- **Execution Plane (VM Windows):** Worker + LangGraph + PAD/RPA + ChromaDB. Worker: `:8088` (headless), `:8089` (interactivo).
- **5 LLMs:** Claude Pro, ChatGPT Plus, Gemini Pro, Copilot Pro, Notion AI. **3 Equipos:** Marketing, Asesoría Personal, Mejora Continua.
- **Red:** Tailscale mesh; sin puertos públicos expuestos.

### Verificación rápida (VPS)

```bash
systemctl --user status openclaw
openclaw status --all
```

### Worker (VPS → VM)

Health: `curl http://WINDOWS_TAILSCALE_IP:8088/health`. Ejecutar tarea: `POST .../run` con `Authorization: Bearer WORKER_TOKEN`, body `{"task":"ping","input":{}}`. En Windows (dev): `$env:WORKER_TOKEN="..."; python -m uvicorn worker.app:app --host 0.0.0.0 --port 8088`. Desplegar servicio: `.\scripts\deploy-vm.ps1`.

### Worker + Notion (variables clave)

| Variable | Dónde | Uso |
|----------|-------|-----|
| `WORKER_TOKEN` | VPS + Windows | Bearer compartido |
| `WORKER_URL` | VPS | URL worker (ej. Tailscale IP:8088) |
| `NOTION_API_KEY` | VPS + Windows | Rick (Worker, poller, dashboard, Control Room) |
| `NOTION_CONTROL_ROOM_PAGE_ID` | VPS + Windows | Página comentarios Rick/Enlace |
| `NOTION_DASHBOARD_PAGE_ID` | VPS + Windows | Dashboard Rick |
| `REDIS_URL` | VPS | Cola Dispatcher |

Tasks en `/run`: `ping`, `notion.write_transcript`, `notion.add_comment`, `notion.poll_comments`, `notion.update_dashboard`, etc. Poller Notion (VPS): `python3 -m dispatcher.notion_poller` (por defecto XX:10). Equipos en `config/teams.yaml`. ModelRouter + cuotas en `config/quota_policy.yaml`.

### Estructura repo

`client/`, `docs/`, `runbooks/`, `worker/` (app.py, config.py, notion_client.py, tasks/), `tests/`, `openclaw/` (templates, scripts), `scripts/`, `infra/`, `changelog/`. Docs clave: `docs/00-overview.md`, `01-architecture`, `14-codex-plan`, `15-model-quota`, `22-notion-dashboard`, `34-rick-github-token`, ADRs en `docs/adr/`.

---

## Qué es OpenClaw

OpenClaw es un **gateway self-hosted** que conecta WhatsApp, Telegram, Discord, iMessage y más con agentes de IA (por defecto Pi/pi-coding-agent). Un solo proceso Gateway en tu máquina o servidor actúa como puente. Requiere Node 22+, API key del proveedor y unos minutos de setup.

- **Self-hosted**: tus reglas, tus datos.
- **Multi-canal**: un Gateway sirve varios canales a la vez.
- **Multi-agente**: sesiones aisladas por agente, workspace o remitente.
- **Open source**: MIT.

---

## Arquitectura del Gateway

- Un **Gateway** de larga duración posee todas las superficies de mensajería (WhatsApp vía Baileys, Telegram vía grammY, Slack, Discord, Signal, iMessage, WebChat).
- Clientes (app macOS, CLI, web UI) se conectan por **WebSocket** al host configurado (por defecto `127.0.0.1:18789`).
- **Nodes** (macOS/iOS/Android/headless) se conectan con `role: node` y capacidades explícitas.
- Un Gateway por host; es el único que abre la sesión de WhatsApp.
- **Canvas** se sirve en el HTTP del Gateway: `/__openclaw__/canvas/`, `/__openclaw__/a2ui/` (mismo puerto, default 18789).

### Componentes y flujos

| Componente | Rol |
|------------|-----|
| **Gateway (daemon)** | Mantiene conexiones a proveedores; expone API WS tipada (requests, responses, server-push events); valida frames con JSON Schema; emite eventos `agent`, `chat`, `presence`, `health`, `heartbeat`, `cron`. |
| **Clients** (mac app / CLI / web admin) | Una conexión WS por cliente; envían requests (`health`, `status`, `send`, `agent`, `system-presence`); se suscriben a eventos (`tick`, `agent`, `presence`, `shutdown`). |
| **Nodes** | Se conectan al mismo WS con `role: node`; identidad de dispositivo en `connect`; pairing por dispositivo; exponen comandos `canvas.*`, `camera.*`, `screen.record`, `location.get`. |
| **WebChat** | UI estática que usa la API WS del Gateway para historial y envío; en remoto usa el mismo túnel SSH/Tailscale. |

### Ciclo de conexión (cliente)

1. Cliente → Gateway: `req:connect` → Gateway responde `res (ok)` o error y cierre.
2. Payload `hello-ok` incluye snapshot: presence + health.
3. Gateway emite `event:presence`, `event:tick`.
4. Cliente → Gateway: `req:agent` → Gateway responde `res:agent` ack `{runId, status:"accepted"}`, luego `event:agent` (streaming), luego `res:agent` final `{runId, status, summary}`.

### Wire protocol (resumen)

- Transporte: WebSocket, frames de texto con JSON.
- El primer frame **debe** ser `connect`; si no es JSON o no es connect, cierre.
- Tras handshake: requests `{type:"req", id, method, params}` → `{type:"res", id, ok, payload|error}`; events `{type:"event", event, payload, seq?, stateVersion?}`.
- Si `OPENCLAW_GATEWAY_TOKEN` (o `--token`): `connect.params.auth.token` debe coincidir o el socket se cierra.
- **Idempotency keys** obligatorios para métodos con efectos (`send`, `agent`); el servidor mantiene caché de dedupe de corta duración.
- Nodes deben incluir `role: "node"` más caps/commands/permissions en `connect`.

### Pairing y confianza local

- Todos los clientes WS (operadores + nodes) envían **identidad de dispositivo** en `connect`.
- Nuevos device IDs requieren aprobación de pairing; el Gateway emite un **device token** para conexiones posteriores.
- Conexiones **locales** (loopback o tailnet del host) pueden auto-aprobarse.
- Todo connect debe firmar el nonce `connect.challenge`; la firma v3 ata `platform` + `deviceFamily`; el gateway fija metadata al reconnectar y exige re-pairing si cambia.
- La auth del gateway (`gateway.auth.*`) aplica a todas las conexiones, locales o remotas.

### Acceso remoto

- Preferido: Tailscale o VPN.
- Alternativa: túnel SSH `ssh -N -L 18789:127.0.0.1:18789 user@host`. Mismo handshake y token sobre el túnel.
- TLS + pinning opcional en setups remotos.

### Operación e invariantes

- **Inicio:** `openclaw gateway` (foreground, logs a stdout).
- **Salud:** `health` por WS (también en `hello-ok`).
- **Supervisión:** launchd/systemd para auto-restart.

**Invariantes:** Exactamente un Gateway controla una sola sesión Baileys por host. Handshake obligatorio; los eventos no se reenvían; los clientes deben refrescar ante huecos.

---

## Configuración: `~/.openclaw/openclaw.json`

Formato **JSON5** (comentarios y comas finales permitidos). Todos los campos son opcionales.

### Índice de secciones principales

| Sección | Uso |
|--------|-----|
| `channels` | WhatsApp, Telegram, Discord, Slack, etc.; DM/group policies, `allowFrom`, `groups`, `modelByChannel` |
| `agents` | `agents.defaults` (workspace, model, sandbox, tools) y **`agents.list`** (lista de agentes) |
| `bindings` | Enrutar mensajes entrantes a un `agentId` por canal, cuenta, peer |
| `messages` | `groupChat.historyLimit`, etc. |
| `commands` | Comandos nativos, texto, bash, config, debug |
| `tools` | profile, allow/deny, elevated, loopDetection, sessions, subagents |
| `gateway` | bind, auth, rateLimit, http, controlUi |

---

## `agents.list` (varios agentes)

Para definir **múltiples agentes** en un mismo Gateway:

```json5
{
  "agents": {
    "list": [
      {
        "id": "main",
        "default": true,
        "name": "Main Agent",
        "workspace": "~/.openclaw/workspace",
        "agentDir": "~/.openclaw/agents/main/agent",
        "model": "anthropic/claude-opus-4-6",
        "params": { "cacheRetention": "none" },
        "identity": {
          "name": "Samantha",
          "emoji": "🦥",
          "avatar": "avatars/samantha.png"
        },
        "groupChat": { "mentionPatterns": ["@openclaw"] },
        "sandbox": { "mode": "off" },
        "subagents": { "allowAgents": ["*"] },
        "tools": {
          "profile": "coding",
          "allow": ["browser"],
          "deny": ["canvas"]
        }
      },
      {
        "id": "work",
        "workspace": "~/.openclaw/workspace-work",
        "agentDir": "~/.openclaw/agents/work/agent"
      }
    ]
  },
  "bindings": [
    { "agentId": "main", "match": { "channel": "whatsapp", "accountId": "personal" } },
    { "agentId": "work", "match": { "channel": "whatsapp", "accountId": "biz" } }
  ]
}
```

- **`id`**: obligatorio, identificador estable del agente.
- **`default`**: si hay varios, el primero con `default: true` gana; si ninguno, el primero de la lista es el default.
- **`model`**: string (solo primary) u objeto `{ primary, fallbacks }`.
- **`params`**: se fusionan con `agents.defaults.models` (ej. `cacheRetention`, `temperature`, `maxTokens`).
- **`identity`**: nombre, emoji, avatar; `ackReaction` y `mentionPatterns` se pueden derivar de emoji/name.
- **`groupChat.mentionPatterns`**: patrones regex para activar al agente en grupos (ej. `["@openclaw", "openclaw"]`).

### Bindings (routing)

Orden de coincidencia (**most-specific wins**):

1. `match.peer` (DM/grupo/canal exacto)
2. `match.parentPeer` (herencia de thread)
3. `match.guildId` + roles (Discord por rol)
4. `match.guildId` (Discord)
5. `match.teamId` (Slack)
6. `match.accountId` para el canal
7. Coincidencia a nivel canal (`accountId: "*"`)
8. Fallback al agente por defecto (`agents.list[].default` o primera entrada; default id: `main`)

Si varios bindings coinciden en el mismo nivel, gana el primero en orden de config. Si un binding tiene varios campos (`peer` + `guildId`), todos son obligatorios (AND). Un binding sin `accountId` solo coincide con la cuenta por defecto; usar `accountId: "*"` para fallback en todo el canal.

### Qué es “un agente”

Cada agente es un **cerebro aislado** con:

- **Workspace** (archivos, AGENTS.md/SOUL.md/USER.md, notas, reglas de persona).
- **State directory** (`agentDir`) para auth profiles, model registry y config por agente.
- **Session store** (historial + estado de routing) en `~/.openclaw/agents/<agentId>/sessions`.

Auth es **por agente**; cada uno lee `~/.openclaw/agents/<agentId>/agent/auth-profiles.json`. No reutilizar `agentDir` entre agentes (colisiones de auth/sesión). Para compartir creds, copiar `auth-profiles.json` al otro agentDir. Skills: por agente en `workspace/skills/`; compartidos en `~/.openclaw/skills`.

### Rutas rápidas (paths)

| Qué | Ruta |
|-----|------|
| Config | `~/.openclaw/openclaw.json` (o `OPENCLAW_CONFIG_PATH`) |
| State dir | `~/.openclaw` (o `OPENCLAW_STATE_DIR`) |
| Workspace | `~/.openclaw/workspace` o `~/.openclaw/workspace-<agentId>` |
| Agent dir | `~/.openclaw/agents/<agentId>/agent` (o `agents.list[].agentDir`) |
| Sessions | `~/.openclaw/agents/<agentId>/sessions` |

### Modo un solo agente (default)

Sin tocar nada: `agentId` = `main`, sesiones `agent:main:<mainKey>`, workspace `~/.openclaw/workspace`, state `~/.openclaw/agents/main/agent`.

### Asistente de agentes

```bash
openclaw agents add work          # crea workspace + agentDir + sesiones
openclaw agents list --bindings  # ver agentes y bindings
```

Luego añadir bindings en config (o que el wizard los añada). Reiniciar y verificar: `openclaw gateway restart`, `openclaw channels status --probe`.

### Conceptos

- **agentId:** un “cerebro” (workspace, auth por agente, session store).
- **accountId:** una cuenta de canal (ej. WhatsApp "personal" vs "biz").
- **binding:** enruta mensajes entrantes a un `agentId` por (channel, accountId, peer) y opcionalmente guild/team.
- Los chats directos colapsan a `agent:<agentId>:<mainKey>` (sesión “main” del agente).

### Ejemplos multi-agente

- **Varios números WhatsApp:** `channels.whatsapp.accounts`: `personal`, `biz`; bindings `agentId: "home"` → `accountId: "personal"`, `agentId: "work"` → `accountId: "biz"`. Opcional override por peer: un grupo concreto a un agente con `match.peer: { kind: "group", id: "..." }`.
- **WhatsApp chat rápido + Telegram deep work:** dos agentes (ej. `chat` con Sonnet, `opus` con Opus); bindings `chat` → whatsapp, `opus` → telegram.
- **Un DM de WhatsApp a Opus:** binding con `match.peer: { kind: "direct", id: "+15551234567" }` a `opus`; debajo el binding channel-wide a `chat`.
- **Agente “family” en un grupo WhatsApp:** un agente con `tools.allow`/`tools.deny` restrictivos, `sandbox.mode: "all"`, `groupChat.mentionPatterns`; binding por `match.peer: { kind: "group", id: "120363...@g.us" }`.
- **Sandbox y tools por agente (v2026.1.6+):** `agents.list[].sandbox` (mode, scope, docker.setupCommand) y `agents.list[].tools` (allow, deny). `tools.elevated` es global y por remitente, no por agente.

### Ejemplos de routing (copiar/pegar)

**Un agente por canal (WhatsApp vs Telegram):**
```json5
{
  agents: {
    list: [
      { id: "chat", workspace: "~/.openclaw/workspace-chat" },
      { id: "opus", workspace: "~/.openclaw/workspace-opus" }
    ]
  },
  bindings: [
    { agentId: "chat", match: { channel: "whatsapp" } },
    { agentId: "opus", match: { channel: "telegram" } }
  ]
}
```

**Un peer específico a otro agente (resto al default):**
```json5
{
  bindings: [
    { agentId: "opus", match: { channel: "whatsapp", peer: { kind: "direct", id: "+15551234567" } } },
    { agentId: "chat", match: { channel: "whatsapp" } }
  ]
}
```

**Dos cuentas WhatsApp, dos agentes:**
```json5
{
  agents: {
    list: [
      { id: "home", default: true, workspace: "~/.openclaw/workspace-home", agentDir: "~/.openclaw/agents/home/agent" },
      { id: "work", workspace: "~/.openclaw/workspace-work", agentDir: "~/.openclaw/agents/work/agent" }
    ]
  },
  bindings: [
    { agentId: "home", match: { channel: "whatsapp", accountId: "personal" } },
    { agentId: "work", match: { channel: "whatsapp", accountId: "biz" } }
  ],
  channels: {
    whatsapp: {
      accounts: { personal: {}, biz: {} }
    }
  }
}
```

**Telegram: dos bots, dos agentes:**
```json5
{
  agents: {
    list: [
      { id: "main", workspace: "~/.openclaw/workspace-main" },
      { id: "alerts", workspace: "~/.openclaw/workspace-alerts" }
    ]
  },
  bindings: [
    { agentId: "main", match: { channel: "telegram", accountId: "default" } },
    { agentId: "alerts", match: { channel: "telegram", accountId: "alerts" } }
  ],
  channels: {
    telegram: {
      accounts: {
        default: { botToken: "123456:ABC...", dmPolicy: "pairing" },
        alerts: { botToken: "987654:XYZ...", dmPolicy: "allowlist", allowFrom: ["tg:123456789"] }
      }
    }
  }
}
```

### Compaction

La compactación de sesión (reducir contexto) se aplica automáticamente en overflow; también hay compactación manual vía API/SDK. Ver docs de Session Management / Compaction.

---

## Canales: DM y grupos

- **DM policy**: `pairing` (default), `allowlist`, `open`, `disabled`.
- **Group policy**: `allowlist` (default), `open`, `disabled`.
- **Mention gating**: por defecto los grupos requieren mención; patrones en `agents.list[].groupChat.mentionPatterns`.
- **Self-chat**: incluir tu número en `allowFrom` (ej. WhatsApp); solo responde a patrones de texto.

Ejemplo Telegram mínimo:

```json5
{
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "your-bot-token",
      "dmPolicy": "pairing",
      "allowFrom": ["tg:123456789"],
      "groups": { "*": { "requireMention": true } }
    }
  }
}
```

---

## Integración Pi (pi-coding-agent)

OpenClaw usa el SDK Pi **embebido**: importa e instancia `AgentSession` con `createAgentSession()` (no subproceso ni RPC). Esto da:

- Control del ciclo de vida y eventos de sesión.
- Inyección de herramientas (mensajería, sandbox, acciones por canal).
- System prompt por canal/contexto.
- Persistencia de sesión con branching/compaction.
- Rotación de perfiles de auth y failover.
- Cambio de modelo por proveedor.

### Paquetes Pi

- `pi-ai`: Model, streamSimple, tipos de mensaje, APIs de proveedor.
- `pi-agent-core`: loop del agente, ejecución de tools, tipos AgentMessage.
- `pi-coding-agent`: createAgentSession, SessionManager, AuthStorage, ModelRegistry, tools built-in.
- `pi-tui`: UI de terminal (modo TUI local de OpenClaw).

### Flujo típico

1. **runEmbeddedPiAgent()** recibe sessionId, sessionKey, sessionFile, workspaceDir, config, prompt, provider, model, timeoutMs, runId, onBlockReply, etc.
2. **createAgentSession()** con cwd, agentDir, authStorage, modelRegistry, model, tools, sessionManager, resourceLoader.
3. **subscribeEmbeddedPiSession()** para eventos (message_start/end/update, tool_execution_*, turn_*, agent_*, compaction).
4. **session.prompt(effectivePrompt, { images })**: el SDK ejecuta el loop (LLM, tools, streaming).

### Sesiones

- Archivos JSONL con estructura de árbol (id/parentId).
- SessionManager maneja persistencia; directorio típico: `~/.openclaw/agents/<agentId>/sessions/`.
- Compaction automática en overflow de contexto; manual vía `compactEmbeddedPiSessionDirect()`.

### Tool pipeline (Pi)

1. **Base:** pi codingTools (read, bash, edit, write).  
2. **Reemplazos:** OpenClaw sustituye bash por exec/process; read/edit/write adaptados a sandbox.  
3. **OpenClaw:** messaging, browser, canvas, sessions, cron, gateway, etc.  
4. **Por canal:** Discord/Telegram/Slack/WhatsApp actions.  
5. **Policy:** filtrado por profile, provider, agent, group, sandbox.  
6. **Schema:** normalización para Gemini/OpenAI.  
7. **AbortSignal:** tools envueltas para respetar cancelación.

`pi-agent-core` AgentTool tiene firma distinta a `ToolDefinition` de pi-coding-agent; el adapter en `pi-tool-definition-adapter.ts` mapea `execute(toolCallId, params, signal, onUpdate)`. `splitSdkTools()` devuelve `builtInTools: []`, `customTools: toToolDefinitions(tools)` (OpenClaw overridea todo).

### System prompt (Pi)

Se construye en `buildAgentSystemPrompt()` (system-prompt.ts): Tooling, Tool Call Style, Safety, CLI reference, Skills, Docs, Workspace, Sandbox, Messaging, Reply Tags, Voice, Silent Replies, Heartbeats, Runtime, Memory/Reactions si aplica, contexto extra. Se aplica tras crear sesión con `applySystemPromptOverrideToSession(session, systemPromptOverride)`.

### Sesión Pi: cache, history, compaction

- **SessionManager** se cachea (`session-manager-cache.ts`) para no re-parsear; `guardSessionManager()` para seguridad en tool results.  
- **History:** `limitHistoryTurns()` según tipo de canal (DM vs group).  
- **Compaction:** automática en overflow; manual `compactEmbeddedPiSessionDirect()`. Extensiones: `compaction-safeguard`, `context-pruning` (cache-TTL).

### Auth y modelo (Pi)

Auth store por agente: `ensureAuthProfileStore(agentDir)`, `resolveAuthProfileOrder()`. Rotación en fallo: `markAuthProfileFailure()`, `advanceAuthProfile()`. Modelo: `resolveModel(provider, modelId, agentDir, config)` → ModelRegistry + AuthStorage. **Failover:** `FailoverError` dispara fallback de modelo si está configurado.

### Streaming y errores (Pi)

- **Block chunking:** `EmbeddedBlockChunker`.  
- **Tags:** strip `<think>`/`<thinking>`, extraer `<final>`.  
- **Reply directives:** `[[media:url]]`, `[[voice]]`, `[[reply:id]]`.  
- **Errores:** `isContextOverflowError`, `isCompactionFailureError`, `isAuthAssistantError`, `isRateLimitAssistantError`, `isFailoverAssistantError`, `classifyFailoverReason`. Thinking level fallback con `pickFallbackThinkingLevel`.

### Diferencias vs Pi CLI

| Aspecto | Pi CLI | OpenClaw Embedded |
|--------|--------|--------------------|
| Invocación | comando `pi` / RPC | SDK createAgentSession() |
| Tools | coding tools por defecto | Suite OpenClaw (messaging, browser, sessions, etc.) |
| System prompt | AGENTS.md + prompts | Dinámico por canal/contexto |
| Sesiones | ~/.pi/agent/sessions/ | ~/.openclaw/agents/<agentId>/sessions/ |
| Auth | Una credencial | Multi-perfil con rotación |

---

## Agent Loop (flujo del agente)

El loop es una **única ejecución serializada por sesión**: intake → ensamblado de contexto → inferencia modelo → ejecución de tools → streaming de respuestas → persistencia.

### Puntos de entrada

- **Gateway RPC:** `agent` y `agent.wait`.  
- **CLI:** comando `agent`.

### Flujo (alto nivel)

1. **agent RPC** valida params, resuelve sesión (sessionKey/sessionId), persiste metadata, devuelve `{ runId, acceptedAt }` de inmediato.  
2. **agentCommand** ejecuta el agente: resuelve model + thinking/verbose, carga snapshot de skills, llama `runEmbeddedPiAgent`, emite lifecycle end/error si el loop no lo hace.  
3. **runEmbeddedPiAgent:** serializa runs por cola por-sesión + global; resuelve model + auth y construye sesión Pi; se suscribe a eventos Pi y hace stream de deltas assistant/tool; aplica timeout → abort si se excede; devuelve payloads + usage.  
4. **subscribeEmbeddedPiSession** traduce eventos pi-agent-core a stream OpenClaw: tool → `stream: "tool"`, assistant → `stream: "assistant"`, lifecycle → `stream: "lifecycle"` (phase: start|end|error).  
5. **agent.wait** usa `waitForAgentJob`: espera lifecycle end/error para runId; devuelve `{ status: ok|error|timeout, startedAt, endedAt, error? }`.

### Colas y concurrencia

Los runs se serializan por **session key** (lane por sesión) y opcionalmente por lane global. Así se evitan carreras tool/sesión y el historial queda consistente. Los canales eligen queue mode (collect/steer/followup) que alimentan este sistema. Ver Command Queue.

### Preparación sesión + workspace

Se resuelve y crea workspace; en sandbox puede redirigirse a sandbox workspace root. Se cargan skills (o snapshot); se inyectan en env y prompt. Se resuelven archivos bootstrap/contexto y se inyectan en el system prompt report. Se adquiere write lock de sesión; se abre y prepara SessionManager antes del streaming.

### Hooks (puntos de interceptación)

- **Internal (Gateway hooks):** `agent:bootstrap` (antes de cerrar system prompt; añadir/quitar archivos bootstrap). Command hooks: `/new`, `/reset`, `/stop`, etc.  
- **Plugin hooks:** `before_model_resolve`, `before_prompt_build` (prependContext, systemPrompt, appendSystemContext), `before_agent_start`, `agent_end`, `before_compaction`/`after_compaction`, `before_tool_call`/`after_tool_call`, `tool_result_persist`, `message_received`/`message_sending`/`message_sent`, `session_start`/`session_end`, `gateway_start`/`gateway_stop`.

### Timeouts y fin anticipado

- **agent.wait** default 30s (solo la espera); param `timeoutMs` lo sobreescribe.  
- **Runtime:** `agents.defaults.timeoutSeconds` (default 600); se aplica en timer de abort de runEmbeddedPiAgent.  
- **Fin anticipado:** timeout de agente (abort), AbortSignal (cancel), desconexión Gateway o timeout RPC, timeout de agent.wait (no detiene al agente).

---

## Agent Runtime (workspace, bootstrap, skills)

OpenClaw corre un **único runtime de agente embebido** (derivado de pi-mono). No hay proceso pi-coding-agent separado; la gestión de sesiones, discovery y tools es de OpenClaw.

### Workspace (obligatorio)

- Un **workspace** por agente (`agents.defaults.workspace` o `agents.list[].workspace`) es el **cwd** del agente para tools y contexto.
- Recomendado: `openclaw setup` para crear `~/.openclaw/openclaw.json` si falta e inicializar los archivos del workspace.
- Si sandbox está activo, sesiones no-main pueden usar workspaces por sesión bajo `agents.defaults.sandbox.workspaceRoot`.

### Archivos bootstrap (inyectados)

Dentro del workspace, OpenClaw espera estos archivos editables:

| Archivo | Uso |
|---------|-----|
| **AGENTS.md** | Instrucciones operativas + “memoria” |
| **SOUL.md** | Persona, límites, tono |
| **TOOLS.md** | Notas de herramientas (imsg, sag, convenciones) |
| **BOOTSTRAP.md** | Ritual de primer arranque (se borra tras completar) |
| **IDENTITY.md** | Nombre del agente, vibe, emoji |
| **USER.md** | Perfil de usuario y dirección preferida |

En el **primer turno** de una sesión nueva, OpenClaw inyecta el contenido de estos archivos en el contexto. Archivos vacíos se omiten; archivos grandes se recortan con un marcador. Si falta un archivo, se inyecta una línea “missing file”. Para desactivar la creación de bootstrap (workspaces pre-poblados): `agents.defaults.skipBootstrap: true`.

### Tools built-in

Las tools core (read, exec, edit, write y herramientas de sistema) están siempre disponibles según la tool policy. `apply_patch` es opcional y gated por `tools.exec.applyPatch`. TOOLS.md no controla qué tools existen; es guía de uso.

### Skills (tres orígenes)

Se cargan en este orden (workspace gana en conflicto de nombre):

1. **Bundled** (incluidos en la instalación)
2. **Managed/local:** `~/.openclaw/skills`
3. **Workspace:** `<workspace>/skills`

Pueden restringirse por config/env (ver Skills en Gateway configuration).

### Sesiones y pi-mono

- **Sesiones:** JSONL en `~/.openclaw/agents/<agentId>/sessions/<sessionId>.jsonl`. El session ID es estable y lo elige OpenClaw. No se usan carpetas legacy Pi/Tau.
- **Pi-mono:** OpenClaw reutiliza partes de pi-mono (modelos, tools), pero la gestión de sesiones, discovery y wiring de tools es de OpenClaw. No hay runtime “pi-coding-agent” separado; no se consultan `~/.pi/agent` ni `<workspace>/.pi`.

### Steering y streaming

- **Queue mode:** Con `steer`, los mensajes entrantes se inyectan en el run actual; la cola se revisa tras cada tool call; si hay mensaje encolado, el resto de tool calls del mensaje assistant actual se omiten (“Skipped due to queued user message.”) y luego se inyecta el mensaje de usuario. Con `followup` o `collect`, los mensajes se retienen hasta que termine el turno y luego arranca un nuevo turno con los payloads encolados.
- **Block streaming:** Los bloques de respuesta se envían al completarse; por defecto `agents.defaults.blockStreamingDefault: "off"`. Límite vía `agents.defaults.blockStreamingBreak` (text_end vs message_end), chunking con `blockStreamingChunk`, coalesce con `blockStreamingCoalesce`. En canales no-Telegram hace falta `*.blockStreaming: true` para block replies.

### Model refs

En config (`agents.defaults.model`, `agents.defaults.models`) los refs se parsean partiendo por el primer `/`. Usar **provider/model** (ej. `anthropic/claude-sonnet-4-5`). Si el model ID lleva `/` (estilo OpenRouter), incluir prefijo (ej. `openrouter/moonshotai/kimi-k2`). Sin prefijo, OpenClaw lo trata como alias o modelo del provider por defecto.

### Config mínima

Como mínimo: `agents.defaults.workspace` y (muy recomendado) `channels.whatsapp.allowFrom` (o el canal que uses).

---

## System Prompt (OpenClaw)

OpenClaw construye un **system prompt propio** por run (no usa el default de pi-coding-agent). Secciones fijas y compactas:

| Sección | Contenido |
|---------|-----------|
| Tooling | Lista de tools actual + descripciones cortas |
| Safety | Recordatorio guardrails (evitar power-seeking, bypass) |
| Skills | Cómo cargar skill instructions on-demand (lista disponible) |
| OpenClaw Self-Update | config.apply, update.run |
| Workspace | Cwd (agents.defaults.workspace) |
| Documentation | Ruta a docs OpenClaw (repo o npm) y cuándo leerlas |
| Workspace Files (injected) | Indica que los bootstrap files van debajo |
| Sandbox | Si está activo: rutas, elevated exec |
| Current Date & Time | Tiempo usuario (timezone, format) |
| Reply Tags | Sintaxis opcional por provider |
| Heartbeats | Prompt y ack |
| Runtime | host, OS, node, model, repo root, thinking level |
| Reasoning | Nivel de visibilidad + hint /reasoning |

Las guardrails en el prompt son **advisory**; para enforcement real usar tool policy, exec approvals, sandbox, allowlists.

### Modos de prompt

- **full (default):** todas las secciones.  
- **minimal:** sub-agentes; omite Skills, Memory Recall, Self-Update, Model Aliases, User Identity, Reply Tags, Messaging, Silent Replies, Heartbeats; mantiene Tooling, Safety, Workspace, Sandbox, Date/Time, Runtime, contexto inyectado.  
- **none:** solo línea de identidad base.

### Inyección bootstrap (Project Context)

Se recortan y añaden bajo "Project Context": AGENTS.md, SOUL.md, TOOLS.md, IDENTITY.md, USER.md, HEARTBEAT.md, BOOTSTRAP.md (solo workspace nuevo), MEMORY.md/memory.md si existen. **Todos** se inyectan cada turno → consumen tokens; mantenerlos breves. memory/*.md diarios no se inyectan; se accede con tools memory_search/memory_get. Límite por archivo: `agents.defaults.bootstrapMaxChars` (default 20000). Límite total: `agents.defaults.bootstrapTotalMaxChars` (default 150000). Truncación: marcador + opcional aviso (`bootstrapPromptTruncationWarning`: off|once|always). Sub-agentes solo inyectan AGENTS.md y TOOLS.md. Hook `agent:bootstrap` puede mutar archivos inyectados.

### Tiempo en el prompt

Solo se incluye **timezone** (sin reloj dinámico) para estabilidad de cache. Para hora actual el agente debe usar `session_status` (incluye timestamp). Config: `agents.defaults.userTimezone`, `agents.defaults.timeFormat` (auto|12|24).

### Skills en el prompt

Se inyecta lista compacta (name, description, location). El prompt indica al modelo que use `read` para cargar el SKILL.md en esa ruta (workspace, managed o bundled). Formato tipo `<available_skills><skill><name>...</name><description>...</description><location>...</location></skill></available_skills>`.

---

## Context (ventana del modelo)

**Context** = todo lo que OpenClaw envía al modelo en un run; está acotado por la context window (límite de tokens). Incluye: system prompt (OpenClaw), historial de conversación, tool calls/results, adjuntos.

### Comandos de inspección

- `/status` — vista rápida “qué tan llena está la ventana” + ajustes de sesión.  
- `/context list` — qué se inyecta + tamaños aproximados (por archivo y totales).  
- `/context detail` — desglose: por archivo, por schema de tool, por skill, tamaño system prompt.  
- `/usage tokens` — footer de uso por reply.  
- `/compact` — resumir historial antiguo para liberar ventana.

### Qué cuenta en la ventana

System prompt (todas las secciones), historial, tool calls + results, adjuntos/transcripts, resúmenes de compaction/pruning, wrappers del provider.

### Skills y tools: dos costes

- **Skills:** el prompt incluye **solo la lista** (name+description+location); las instrucciones no van por defecto; el modelo debe hacer `read` del SKILL.md cuando haga falta.  
- **Tools:** (1) texto de la lista en el prompt (“Tooling”); (2) **schemas JSON** de las tools, que se envían al modelo y cuentan aunque no se vean como texto. `/context detail` desglosa los schemas más grandes.

### Sesiones, compaction y pruning

El historial normal persiste en el transcript hasta compactar/prune. Compaction persiste un resumen en el transcript y mantiene mensajes recientes. Pruning quita tool results viejos del prompt en memoria para ese run pero no reescribe el transcript.

---

## Agent Workspace (detalle y backup)

El workspace es el **hogar del agente**: único cwd para file tools y contexto. Es distinto de `~/.openclaw/` (config, credenciales, sesiones). Por defecto es cwd, **no** sandbox duro; paths relativos se resuelven al workspace, pero paths absolutos pueden llegar a otras rutas del host si no hay sandbox.

### Ubicación por defecto

- Default: `~/.openclaw/workspace`.  
- Si `OPENCLAW_PROFILE` no es `"default"`: `~/.openclaw/workspace-<profile>`.  
- Override en openclaw.json: `agent: { workspace: "~/.openclaw/workspace" }`.  
- `openclaw onboard` / `configure` / `setup` crean el workspace y plantillas bootstrap si faltan. Para no crear bootstrap: `agent: { skipBootstrap: true }`.

### Mapa de archivos del workspace

| Archivo | Uso |
|---------|-----|
| AGENTS.md | Instrucciones operativas y uso de memoria |
| SOUL.md | Persona, tono, límites |
| USER.md | Quién es el usuario y cómo dirigirse |
| IDENTITY.md | Nombre del agente, vibe, emoji (bootstrap ritual) |
| TOOLS.md | Notas sobre tools locales; no controla disponibilidad |
| HEARTBEAT.md | Checklist opcional para heartbeat (breve) |
| BOOT.md | Checklist opcional al reinicio del gateway (hooks) |
| BOOTSTRAP.md | Ritual primer arranque (solo workspace nuevo; borrar tras completar) |
| memory/YYYY-MM-DD.md | Memoria diaria (un archivo por día) |
| MEMORY.md | Memoria a largo plazo (solo sesión main/privada) |
| skills/ | Skills específicos del workspace |
| canvas/ | UI Canvas para nodes (ej. canvas/index.html) |

Si falta un archivo se inyecta marcador “missing file”. Límites de inyección: `bootstrapMaxChars`, `bootstrapTotalMaxChars`. `openclaw setup` puede recrear defaults sin sobrescribir existentes.

### Qué NO está en el workspace

Viven en `~/.openclaw/` y no deben commitearse con el workspace: `openclaw.json`, `credentials/`, `agents/<agentId>/sessions/`, `skills/` (managed). Migrar sesiones o config por separado.

### Git backup (recomendado, repo privado)

1. **Inicializar:** `cd ~/.openclaw/workspace && git init`, `git add AGENTS.md SOUL.md TOOLS.md IDENTITY.md USER.md HEARTBEAT.md memory/`, `git commit -m "Add agent workspace"`.  
2. **Remote:** crear repo privado (GitHub/GitLab sin README), `git remote add origin <url>`, `git push -u origin main`.  
3. **Ongoing:** `git add .`, `git commit -m "Update memory"`, `git push`.  
No commitear secretos; usar placeholders. `.gitignore` sugerido: `.DS_Store`, `.env`, `**/*.key`, `**/*.pem`, `**/secrets*`.

### Mover workspace a otra máquina

Clonar el repo en la ruta deseada; poner `agents.defaults.workspace` en openclaw.json; `openclaw setup --workspace <path>` para seed de archivos faltantes. Copiar `~/.openclaw/agents/<agentId>/sessions/` aparte si se necesitan sesiones.

---

## OAuth y almacenamiento de auth

OpenClaw soporta OAuth “subscription” (p. ej. OpenAI Codex) y API keys. **Token sink:** auth-profiles.json es el único lugar de lectura para reducir invalidaciones al tener varios clientes (OpenClaw + Codex CLI, etc.).

### Dónde se guarda

- **Por agente:** `~/.openclaw/agents/<agentId>/agent/auth-profiles.json` (OAuth + API keys + refs).  
- Legacy: `auth.json` en el mismo agentDir (se migra); `~/.openclaw/credentials/oauth.json` (solo import, luego auth-profiles).  
- Respetan `$OPENCLAW_STATE_DIR`.

### Anthropic setup-token (subscription)

`openclaw models auth setup-token --provider anthropic` (o pegar token: `paste-token`). Verificar: `openclaw models status`. Uso fuera de Claude Code puede estar restringido por Anthropic; ver política actual.

### OpenAI Codex (ChatGPT OAuth)

Flujo PKCE: authorize → callback 127.0.0.1:1455 o pegar redirect URL → exchange token; se guarda access, refresh, expires, accountId. Wizard: onboard → auth openai-codex.

### Múltiples cuentas

- **Recomendado:** agentes separados (`openclaw agents add work`, `agents add personal`) con auth y bindings por agente.  
- **Avanzado:** varios perfiles en un mismo agente en auth-profiles.json; orden global con config `auth.order`; override por sesión: `/model Opus@anthropic:work`. Ver perfiles: `openclaw channels list --json` (auth[]).

---

## Presence (estado del Gateway y clientes)

**Presence** = vista best-effort del Gateway y de los clientes conectados (mac app, WebChat, CLI, nodes). Se usa para la pestaña Instances de la app macOS y visibilidad del operador.

### Campos

instanceId (recomendado estable), host, ip, version, deviceFamily/modelIdentifier, mode (ui, webchat, cli, backend, node, …), lastInputSeconds, reason, ts.

### Origen de las entradas

1. **Gateway self:** entrada propia al arranque.  
2. **WebSocket connect:** cada cliente que hace connect obtiene una entrada. Los CLI one-off (`mode: cli`) no se muestran para no saturar.  
3. **system-event beacons:** clientes envían beacons periódicos (host, IP, lastInputSeconds).  
4. **Nodes (role: node):** mismo flujo que el resto de clientes.

### Merge y TTL

Se keyean por presence key; lo ideal es `connect.client.instanceId` estable. Keys case-insensitive. TTL: entradas > 5 min se eliminan. Máximo 200 entradas (las más viejas se descartan). Conexiones por túnel (loopback) pueden verse como 127.0.0.1; se ignora IP loopback para no sobrescribir la reportada por el cliente.

---

## Workspace y skills (resumen)

- **Workspace** por agente: `~/.openclaw/workspace` (o `agents.list[].workspace`). Contiene IDENTITY.md, SOUL.md, AGENTS.md, TOOLS.md.
- **Skills** por agente en `workspace/skills/`; compartidos en `~/.openclaw/skills`; bundled en la instalación.
- **Agent dir**: `~/.openclaw/agents/<agentId>/agent` — auth, model registry, config por agente.

---

## Control UI y puertos

- **Local**: http://127.0.0.1:18789/ (WS) y HTTP para Control UI.
- **Remoto**: Tailscale o túnel SSH (`ssh -N -L 18789:127.0.0.1:18789 user@host`).
- Dashboard: chat, config, sesiones, nodos.

---

## Procedimiento recomendado: configurar agentes, sesiones y workspace

1. **Definir single-agent vs multi-agent:** Single cuando una sola persona/identidad, un workspace, una política. Multi cuando identidades separadas, workspaces separados, auth/sesiones aisladas, distintas cuentas por canal o política de sandbox/tools.

2. **Crear agentes aislados:** `openclaw agents add work`, `openclaw agents add personal`. Verificar: `openclaw agents list --bindings`.

3. **Crear o revisar workspaces:** Cada agente con workspace propio, bootstrap files mínimos (AGENTS.md, SOUL.md, IDENTITY.md, USER.md, TOOLS.md), `skills/` si aplica.

4. **Configurar auth por agente:** `openclaw models auth login --provider <id>`, `setup-token`/`paste-token` para Anthropic, `openclaw models status`. Preferir API key en producción Anthropic.

5. **Crear cuentas por canal:** `openclaw channels login --channel whatsapp --account personal` (y `biz` si aplica). Telegram/Discord: un bot/token por cuenta.

6. **Configurar bindings:** En openclaw.json, primero los más específicos (peer/grupo), luego accountId, al final los generales por canal.

7. **Reiniciar y validar:** `openclaw gateway restart`, `openclaw agents list --bindings`, `openclaw channels status --probe`.

8. **Probar routing y aislamiento:** Comprobar que el mensaje va al agentId correcto, transcript en el directorio esperado, workspace correcto, sin mezcla de auth ni respuestas entre cuentas.

---

## Diagnóstico rápido: errores típicos y causa probable

| Síntoma | Revisar | Corrección |
|--------|---------|------------|
| Se mezclaron respuestas o sesiones | ¿Dos agentes comparten agentDir? ¿Binding cae al default por falta de accountId? ¿Se esperaba aislamiento por persona en el mismo agente? | workspace y agentDir únicos por agente; bindings explícitos; un agente por persona si el DM split requiere aislamiento real. |
| El mensaje llegó al agente equivocado | Orden de bindings, presencia de accountId, peer correcto (direct/group, id exacto), binding general antes que específico. | Reordenar bindings (específico → general), fijar accountId y peer. |
| No encuentro sesiones de un agente | Directorio `~/.openclaw/agents/<agentId>/sessions`, que el agentId coincida, que el mensaje realmente enrute a ese agente. | Verificar routing y que el agente reciba mensajes. |
| El prompt está demasiado pesado | TOOLS.md, MEMORY.md o bootstrap largos; exceso de skills list; schemas de tools pesadas (browser, exec). | `/context list` y `/context detail`; acortar bootstrap; compactar si hace falta. |
| Sandbox no aísla como esperaba | mode "all" o política equivalente; scope del sandbox; tool denegada pero permitida por config. | Recordar que workspace solo no aísla rutas absolutas; revisar agents.list[].sandbox y tools. |
| OAuth se pisa entre herramientas | Misma cuenta en OpenClaw y otra app/CLI; refresh token invalidado. | Usar agentes separados o perfiles separados; no compartir cuenta OAuth. |
| Duplicados en Presence | connect.client.instanceId inestable; beacons sin mismo instanceId; reconexión sin metadata consistente. | Enviar instanceId estable en connect y en beacons. |

---

## Checklist antes de proponer cambios

Antes de sugerir configuración, comprobar: (1) ¿Single-agent o multi-agent? (2) ¿Cada agente tiene workspace único? (3) ¿Cada agente tiene agentDir único? (4) ¿Cuentas múltiples por canal? (5) ¿Bindings ordenados de específico a general? (6) ¿accountId explícito donde corresponde? (7) ¿Aislamiento lógico o fuerte? (8) ¿Hace falta sandbox real? (9) ¿Auth aislada por agente o por profile? (10) ¿DM split por persona? Si sí, ¿un agente por persona? (11) ¿Bootstrap files cortos para no inflar contexto? (12) ¿Skill en workspace, managed o bundled?

---

## Procedimiento de respuesta para el asistente

Al ayudar con agentes/sesiones/workspace en OpenClaw: (1) Identificar nivel: gateway, agent routing, workspace, sessions, auth, sandbox, context/prompt. (2) Explicar el modelo correcto antes de tocar config. (3) Proponer cambios mínimos y explícitos en openclaw.json. (4) Separar claramente workspace, agentDir, sessions, bindings, accounts, auth profiles. (5) Validar con comandos concretos. (6) Incluir riesgos si hay mezcla de credenciales, reuse de agentDir o bindings ambiguos. (7) No asumir que Pi CLI o ~/.pi/agent participan en el runtime de OpenClaw.

---

## Plantilla de validación operativa

Tras aplicar cambios, ejecutar:

```bash
openclaw agents list --bindings
openclaw channels status --probe
openclaw models status
openclaw gateway restart
```

Verificar manualmente: mensaje de prueba por cada canal/cuenta; transcript creado en el sessions/ correcto; workspace correcto activo; modelo/auth correcto; ausencia de cross-talk entre agentes.

---

## Referencias rápidas de documentación

- [Gateway Architecture](https://docs.openclaw.ai/concepts/architecture.md)
- [Configuration Reference](https://docs.openclaw.ai/gateway/configuration-reference.md) — campo a campo de openclaw.json
- [Configuration](https://docs.openclaw.ai/gateway/configuration.md)
- [Multi-Agent Routing](https://docs.openclaw.ai/concepts/multi-agent.md)
- [Pi Integration Architecture](https://docs.openclaw.ai/pi.md)
- [Channels](https://docs.openclaw.ai/channels/index.md) — WhatsApp, Telegram, Discord, etc.
- [CLI Reference](https://docs.openclaw.ai/cli/index.md) — gateway, config, agents, channels, nodes
- [Skills](https://docs.openclaw.ai/tools/skills.md), [Skills Config](https://docs.openclaw.ai/tools/skills-config.md)
- [Help / Troubleshooting](https://docs.openclaw.ai/help/index.md)

Para listar todas las páginas disponibles: https://docs.openclaw.ai/llms.txt

---

## Integración con Umbral Agent Stack (resumen)

El **Gateway OpenClaw** (Rick) corre en la VPS en 18789/18791; su workspace es `~/.openclaw/workspace` (AGENTS.md, SOUL.md, TOOLS.md, IDENTITY.md). El **Worker** (FastAPI) y el **Dispatcher** (Redis) son independientes: Rick encola tareas (notion.*, linear.*, etc.) en Redis y el Worker (VPS o VM por Tailscale) las ejecuta. Config del Gateway: `~/.openclaw/openclaw.json`; variables de entorno: `~/.config/openclaw/env` (VPS). Para arquitectura completa, variables y tasks, ver sección **Proyecto: Umbral Agent Stack** al inicio de este skill.

---

## Desplegar este skill en la VPS (para Rick)

Para que Rick tenga este skill disponible en su workspace:

- **En la VPS (Linux):** ya estás en el servidor; usa rutas Unix y `python3` si hace falta. No uses `c:\` ni `python`. Ejecutar:
  ```bash
  cd ~/umbral-agent-stack && git pull origin main
  mkdir -p ~/.openclaw/workspace/skills
  cp -r openclaw/workspace-templates/skills/openclaw-gateway ~/.openclaw/workspace/skills/
  ls ~/.openclaw/workspace/skills/openclaw-gateway/SKILL.md
  ```
- **Desde tu PC (Windows):** `python scripts/sync_skills_to_vps.py --execute` (requiere `VPS_HOST` o `--vps-host`). O solo este skill: `scp -r openclaw/workspace-templates/skills/openclaw-gateway USUARIO@VPS:~/.openclaw/workspace/skills/`

Asignación de modelos por agente (Vertex vs AI Foundry): ver `docs/openclaw-rick-skill-y-modelos.md` en el repo.

---

## Regla final

**Nunca mezclar** estos tres conceptos sin intención explícita:

- **workspace** = contexto operativo y cwd por defecto.
- **agentDir** = estado del agente, auth profiles, model registry y config por agente.
- **sessions** = transcripciones persistentes por agente.

Si cualquiera de esos tres se comparte entre agentes sin diseño explícito, el sistema deja de estar realmente aislado.
