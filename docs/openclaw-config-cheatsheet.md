# OpenClaw — Cheatsheet de configuración

> Resumen de patrones útiles para `openclaw.json`.  
> Origen: skill openclaw-expert (Drive: `AI/IA Personalizadas/Skills/openclaw-expert`).  
> Para Rick: usar cuando tengas que razonar sobre bindings, sesiones, sandbox o tools.

---

## 1. Secure DM mode (varios usuarios en DMs)

Evita que todos los usuarios compartan el mismo contexto. Aísla por canal + remitente.

```json5
{ "session": { "dmScope": "per-channel-peer" } }
```

Variantes: `main` (un solo usuario), `per-peer`, `per-channel-peer`, `per-account-channel-peer`.

---

## 2. Multi-agente mínimo (2 workspaces)

```json5
{
  "agents": {
    "list": [
      { "id": "home", "workspace": "~/.openclaw/workspace-home" },
      { "id": "work", "workspace": "~/.openclaw/workspace-work" }
    ]
  },
  "bindings": [
    { "agentId": "work", "match": { "channel": "telegram" } },
    { "agentId": "home", "match": { "channel": "whatsapp" } }
  ]
}
```

---

## 3. Sandbox por defecto (solo sesiones no-main)

```json5
{
  "agents": {
    "defaults": {
      "sandbox": {
        "mode": "non-main",
        "scope": "session",
        "workspaceAccess": "none"
      }
    }
  }
}
```

---

## 4. Restricción de tools (deny gana)

```json5
{
  "tools": {
    "deny": ["browser", "canvas", "nodes", "cron"]
  }
}
```

---

## 5. Override por agente (solo lectura)

```json5
{
  "agents": {
    "list": [
      {
        "id": "public",
        "sandbox": { "mode": "all", "scope": "agent", "workspaceAccess": "none" },
        "tools": {
          "allow": ["read", "session_status"],
          "deny": ["exec", "write", "edit", "apply_patch"]
        }
      }
    ]
  }
}
```

---

## Árbol de decisión rápido

| Objetivo | Solución |
|----------|----------|
| Separar memoria/persona por completo | **Multi-agent** (un `agentId` por “cerebro”). |
| Dos números/cuentas en el mismo canal | `accountId` + bindings por cuenta. |
| DMs de varias personas en la misma cuenta | `session.dmScope: "per-channel-peer"` (o `per-account-channel-peer`). |
| Varios agentes respondan al mismo mensaje | Evaluar **broadcast groups** (experimental). |
| Flujos con aprobaciones explícitas | Evaluar **lobster**. |
| Programas markdown con subagentes y control de flujo | Evaluar **openprose** (`.prose`). |

---

## Reglas de trabajo (openclaw-expert)

1. **Aterrizar el escenario:** canal(es), cuentas, ¿un usuario o multiusuario?, ¿un agente o varios?
2. **Responder con receta:** explicación corta + snippet JSON5 + comandos CLI + verificación.
3. **Aislamiento y seguridad:** en DMs de más de una persona, recomendar secure DM; en públicos, sandbox + allow/deny de tools.
4. **Modelo mental:** *Agente* = workspace + agentDir + sesiones + auth. *Cuenta* = un login en un canal. *Binding* = (channel, accountId, peer) → agentId.
5. **No inventar:** si falta un dato, proponer 2 opciones y pedir el dato mínimo.

---

## Referencias en el skill original (Drive)

- `references/architecture.md` — piezas, paths, workspace.
- `references/multi-agent-routing.md` — bindings, accountId, peer, ejemplos.
- `references/sessions-and-memory.md` — dmScope, session keys, mantenimiento.
- `references/tools.md` — allow/deny, exec, sessions_*, gateway, cron.
- `references/sandboxing.md` — mode, scope, workspaceAccess, elevated.
- `references/orchestration.md` — openprose, lobster, sessions_spawn.
- `references/plugins-and-skills.md` — precedencia, ClawHub.
