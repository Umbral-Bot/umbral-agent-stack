---
name: openclaw-vps-operator
description: Operar OpenClaw y el stack real en la VPS de Umbral. Úsala cuando la tarea toque gateway, openclaw.json, modelos, nodos, runtime, VPS, VM, health checks, deploys, fallbacks, runbooks, o cuando Claude necesite sacar el máximo provecho a OpenClaw sin inventar arquitectura.
---

# OpenClaw VPS Operator

## Objetivo

Dar a Claude un modo operativo experto para trabajar con el OpenClaw real instalado en la VPS de Umbral, usando la configuración viva, las runbooks del repo, y la documentación oficial actual como referencias primarias.

## Superficies canónicas

- Runtime/deploy reference: `/home/rick/umbral-agent-stack`
- Clean working copy: `/home/rick/umbral-agent-stack-main-clean`
- Notion governance reference: `/home/rick/notion-governance-git`
- Live OpenClaw config: `~/.openclaw/openclaw.json`
- Live env: `~/.config/openclaw/env`
- Live workspace: `~/.openclaw/workspace`

## Referencias oficiales mínimas

Usa como ancla oficial cuando el tema cambie rápido:

- `https://docs.openclaw.ai/`
- `https://docs.openclaw.ai/llms.txt`
- `https://docs.openclaw.ai/gateway/authentication`
- `https://docs.openclaw.ai/nodes`

En este repo, compleméntalo con:

- `docs/03-setup-vps-openclaw.md`
- `runbooks/runbook-openclaw-status.md`
- `runbooks/runbook-vm-openclaw-node.md`
- `docs/openclaw-rick-skill-y-modelos.md`
- `openclaw/workspace-templates/AGENTS.md`
- `openclaw/workspace-templates/HEARTBEAT.md`
- `openclaw/workspace-templates/TOOLS.md`

## Cuándo usar esta skill

Usa esta skill cuando la tarea implique cualquiera de estos frentes:

1. estado del gateway OpenClaw
2. configuración de `openclaw.json`
3. modelos, fallbacks y providers reales
4. runtime de Rick, workspace, sesiones o nodos
5. relación VPS ↔ VM ↔ OpenClaw
6. deploys o drift entre repo limpio y repo desplegado
7. necesidad de fallback cuando la VM no está
8. evaluación de qué debe vivir en VPS vs VM

## Flujo operativo recomendado

### 1. Declarar el alcance real

Antes de proponer cambios, deja explícito:

- qué puedes verificar en runtime desde la VPS
- qué puedes verificar solo en código
- si la VM está alcanzable o no
- si un provider está realmente vivo o solo definido en config

### 2. Cargar env solo cuando haga falta

En Bash:

```bash
set -a
source ~/.config/openclaw/env
set +a
```

No reescribas este archivo salvo instrucción explícita.

### 3. Leer primero el estado vivo

Checklist mínimo:

```bash
openclaw status --all
openclaw models status
bash scripts/vps/verify-openclaw.sh
redis-cli ping
curl -fsS http://127.0.0.1:8088/health || true
```

Si la tarea toca nodos/VM:

```bash
openclaw nodes status
openclaw devices list
curl -fsS "$WORKER_URL_VM/health" || true
curl -fsS "$WORKER_URL_VM_INTERACTIVE/health" || true
```

### 4. Inspeccionar la topología real antes de teorizar

Verifica siempre:

- `~/.openclaw/openclaw.json`
- `~/.config/openclaw/env`
- si Claude/Anthropic está deshabilitado
- si Azure/OpenAI/Kimi/Gemini están realmente configurados
- qué repo está desplegado y cuál es solo clean copy

### 5. Elegir bien la superficie de edición

- Si vas a diagnosticar runtime, lee `/home/rick/umbral-agent-stack`
- Si vas a editar código, usa `/home/rick/umbral-agent-stack-main-clean`
- No mezcles fixes en el repo desplegado salvo mandato explícito del usuario

### 6. Tratar la VM como recurso opcional

Regla operativa:

- VPS primero para research, Notion, Linear, QA, tests, deploys y análisis
- VM solo para browser/gui/windows/PAD o tareas que realmente dependan de Windows
- si la VM falla, diseña fallback o degradación elegante en vez de bloquear el sistema entero

### 7. Seguridad y acceso remoto

- No expongas OpenClaw públicamente por defecto
- Prefiere loopback + SSH tunnel o tailnet/Tailscale
- Usa auth explícita (`token` o `password`) para acceso remoto al gateway
- Si el gateway está en loopback, un node remoto debe usar túnel SSH + puerto local reenviado según la documentación oficial de nodes
- Si cambias auth o topología, recomienda `openclaw security audit --deep`

### 8. Salida esperada

Cuando cierres una tarea OpenClaw/VPS, deja claro:

- estado real verificado
- drift entre runtime y repo si existe
- qué vive en VPS y qué vive en VM
- si hay fallback o no
- qué bloqueos son de credencial/config y cuáles son bugs reales

## Antipatrones

- asumir que OpenClaw está “sin instalar” cuando ya está corriendo en esta VPS
- editar el repo desplegado por comodidad cuando existe `main-clean`
- asumir que un provider está activo solo porque aparece en JSON
- tratar la VM como dependencia obligatoria para todo
- proponer exponer el gateway a internet sin necesidad
- olvidar que este stack debe seguir avanzando aunque la VM no esté

## Skills y artefactos adyacentes que conviene reutilizar

- `openclaw/workspace-templates/skills/openclaw-gateway/SKILL.md`
- `openclaw/workspace-templates/skills/browser-automation-vm/SKILL.md`
- `openclaw/workspace-templates/skills/linear/SKILL.md`
- `openclaw/workspace-templates/skills/notion-workflow/SKILL.md`
- `openclaw/workspace-templates/skills/granola-pipeline/SKILL.md`
- `openclaw/workspace-templates/skills/system-interconnectivity-diagnostics/SKILL.md`
