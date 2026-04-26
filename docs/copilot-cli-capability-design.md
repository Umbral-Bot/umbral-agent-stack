# Rick × GitHub Copilot CLI — Capability Design (F1)

> **Status:** DRAFT — Fase 1 (design only). No code, no install, no runtime
> change in this PR. Sets the contract every later phase must follow.
>
> **Branch:** `rick/copilot-cli-capability-design`
> **Owner:** rick-orchestrator (design), David (approval gate)

## 1. Goal

Permitir que Rick/OpenClaw **delegue** tareas técnicas acotadas al
**GitHub Copilot CLI** (`@github/copilot`) ejecutándose en la VPS,
**sin** ampliar el blast radius del stack ni habilitar publicación,
merge, push, mutación de Notion, o cualquier acción irreversible sin
intervención humana explícita.

El objetivo **no** es exponer una shell agéntica. Es ofrecer un canal
auditado, sandboxeado y con allowlist por *misión* para tareas como
"investigar este módulo", "explicar este test que falla", "proponer un
diff de lint" — donde el output se materializa como **artifact** que un
humano (o un agente con permisos explícitos) revisa antes de cualquier
side-effect.

## 2. Scope explícito

### In scope (este diseño)
- Arquitectura de capability gate, allowlist policy, sandbox de
  ejecución, identity/secrets, output gate.
- Set inicial de *missions* (templates) **read-only**.
- Contrato de la futura task `copilot_cli.run` del Worker.
- Roadmap de fases con dependencias y criterios de aceptación.

### Out of scope (NO en F1)
- Instalar `@github/copilot` (host o sandbox).
- Cambiar `tool_policy.yaml` con valores efectivos (solo stub disabled
  en F1, y aun así en commit separado tras aprobación de este diseño).
- Crear el agente `rick-tech` (F5).
- Cualquier ejecución contra Copilot CLI.
- Cambios en Notion, Linear, gates, publicaciones.

## 3. Restricciones absolutas (heredadas)

- ❌ No `git push`, `gh pr create/merge/comment` desde la task.
- ❌ No mutación de Notion / Linear / Kanban desde la task.
- ❌ No comandos destructivos (`rm -rf`, `truncate`, `chmod -R`).
- ❌ No exposición de tokens en logs, errores, ni artifacts.
- ❌ No checkout de ramas protegidas (`main`, `master`).
- ❌ No widening de scopes del token GitHub App.
- ❌ No bypass del feature flag — sin flag, la task no se registra.

## 4. Estado runtime verificado (2026-04-26)

- Host: VPS `srv1431451`, user `rick`, Ubuntu 24 / kernel 6.8.
- `gh` CLI **v2.45.0 instalado, NO autenticado**.
- `copilot` CLI **NO instalado**.
- `node v24.14.0`, `npm 11.9.0` disponibles.
- Servicios `systemctl --user` activos:
  - `openclaw-gateway.service` v2026.3.2 (PID 1000650).
  - `openclaw-dispatcher.service`.
  - `umbral-worker.service` (uvicorn `127.0.0.1:8088`).
- `copilot_agent/agent.py` existe pero usa `github-copilot-sdk` Python
  con BYOK Azure — **no** el CLI de terminal objetivo aquí.
- Patrones reutilizables ya en repo:
  - `worker/sandbox/` (Dockerfile rootless, `cap-drop=ALL`,
    `--network=none`, read-only mount, tmpfs, uid 10001) — base ideal.
  - `worker/tasks/github.py` (token redaction, protected-branch guards,
    sanitización de stderr) — patrón de ejecución segura.
  - `worker/tool_policy.py` + `config/tool_policy.yaml` — patrón de
    allowlist por nombre.
  - `infra/auth_lifecycle.py` — patrón de rotación de credenciales.

## 5. Arquitectura: 5 capas de guardrail

Cada capa es **independiente** y **off-by-default**. Una capa no
puede sustituir a otra: las cinco deben pasar para que una invocación
proceda.

```
┌─────────────────────────────────────────────────────────────────┐
│ L1 Capability gate     env flag RICK_COPILOT_CLI_ENABLED=false  │
├─────────────────────────────────────────────────────────────────┤
│ L2 Allowlist policy    config/tool_policy.yaml :: copilot_cli   │
│                        - missions[]                              │
│                        - max_tokens, max_wall_sec                │
│                        - max_files_touched                       │
│                        - banned_subcommands[]                    │
├─────────────────────────────────────────────────────────────────┤
│ L3 Sandbox de ejecución  Docker rootless, derivado de            │
│                          worker/sandbox/Dockerfile               │
│   --network=<filtered>   solo api.githubcopilot.com + api.github │
│   --read-only            repo bind RO; scratch en tmpfs writable │
│   --cap-drop=ALL         no-new-privileges, seccomp default      │
│   --user 10001:10001     sin uid 0                               │
│   --memory/--cpus/--pids límites duros                           │
│   sin git/gh push        binarios filtrados o wrapper bloquea    │
├─────────────────────────────────────────────────────────────────┤
│ L4 Identity & secrets   GitHub App token READ-ONLY a este repo   │
│                         systemd EnvironmentFile (no en repo)     │
│                         rotación vía infra/auth_lifecycle.py     │
│                         redaction _SENSITIVE_PATTERNS en logs    │
├─────────────────────────────────────────────────────────────────┤
│ L5 Output gate          La task NUNCA invoca push/merge/comment  │
│                         Output: structured result + patch artifact│
│                         + audit log. Materialización = paso       │
│                         humano explícito vía github.commit_and_   │
│                         push existente.                           │
└─────────────────────────────────────────────────────────────────┘
```

### 5.1 L1 — Capability gate

Variable de entorno `RICK_COPILOT_CLI_ENABLED` (`true`/`false`,
default `false`). Cargada por systemd `EnvironmentFile` del
`umbral-worker.service`.

- Si `false`: `worker/tasks/copilot_cli.py` registra la task pero
  responde `{"ok": false, "error": "capability_disabled"}` antes de
  cualquier I/O.
- Cambiar el flag requiere edit de `EnvironmentFile` + restart
  explícito del worker. No se puede flippear vía request.

### 5.2 L2 — Allowlist policy

Nuevo bloque en `config/tool_policy.yaml`:

```yaml
copilot_cli:
  enabled: false                  # mirror del flag L1; defensa-en-prof.
  default_max_wall_sec: 120
  default_max_tokens: 8000
  default_max_files_touched: 0    # 0 = read-only por mission default
  banned_subcommands:
    - "git push"
    - "git remote add"
    - "gh pr create"
    - "gh pr merge"
    - "gh pr comment"
    - "gh auth"
    - "gh secret"
    - "rm -rf"
    - "chmod -R"
  missions: {}                    # vacío hasta F4
```

`worker/tool_policy.py` ganará helpers `is_mission_allowed(name)`,
`get_mission_limits(name)`, `get_banned_subcommands()`. Una invocación
sin mission válida es rechazada antes de tocar el sandbox.

### 5.3 L3 — Sandbox

Nueva imagen `umbral-sandbox-copilot-cli`, hermana de
`umbral-sandbox-pytest`. Reutiliza el patrón de hardening:

- `FROM node:22-slim` (Copilot CLI requiere Node ≥ 22).
- Instala `@github/copilot` global durante el `docker build`. La host
  VPS **no** lo instala.
- `useradd -u 10001 -m -s /usr/sbin/nologin runner`.
- Repo se monta `--mount type=bind,source=<ws>,target=/work,readonly`,
  igual que pytest. Las missions que necesiten escribir un patch lo
  hacen en `/scratch` (tmpfs) y el runner copia el patch a
  `artifacts/copilot-cli/<mission_id>/` *después* de validarlo.
- Red: política inicial **`--network=none`**. Para missions que sí
  necesiten Copilot remoto, se usa una red Docker custom con egress
  filtrado a `api.githubcopilot.com:443` y `api.github.com:443` (vía
  `--dns` + `iptables` rules en compose, documentado en F2).
- `--cap-drop=ALL`, `--security-opt no-new-privileges`,
  `--security-opt seccomp=default`, `--read-only`,
  `--tmpfs /tmp:size=64m,exec,nosuid,nodev`,
  `--tmpfs /scratch:size=64m`, `--memory=1g --cpus=1.0
  --pids-limit=256 --ipc=none`.
- Sin `git push` posible: el binario `git` permanece pero el wrapper
  del runner setea `GIT_TERMINAL_PROMPT=0` y `core.askpass=/bin/false`,
  y la red filtrada bloquea cualquier remote real.

### 5.4 L4 — Identity & secrets

- Crear GitHub App "Umbral Copilot CLI Runner" con permisos
  **Contents: Read** sobre `Umbral-Bot/umbral-agent-stack` únicamente.
  Sin `Contents: Write`, sin `Pull requests`, sin `Issues`, sin
  `Workflows`.
- Token instalado vía `EnvironmentFile` de systemd:
  `/etc/umbral/copilot-cli.env`, `chmod 600`, owner `rick`.
- Rotación: extender `infra/auth_lifecycle.py` con entry
  `copilot_cli_github_app` que revalida cada N días.
- Redaction: extender `_SENSITIVE_PATTERNS` de `worker/tasks/github.py`
  para incluir tokens del GitHub App (formato `ghs_...`). Aplicar a
  todo log, error y artifact escrito por la task.

### 5.5 L5 — Output gate

Contrato de la task `copilot_cli.run`:

```
INPUT  { mission: str, params: dict, dry_run: bool=true }
OUTPUT {
  ok: bool,
  mission: str,
  mission_run_id: str,        # uuid4
  result_text: str,           # resumen del Copilot CLI
  tool_calls: list,           # qué herramientas internas usó
  patch_path: str | null,     # ruta relativa al artifact si aplica
  audit_log_path: str,        # siempre, append-only
  metrics: { wall_sec, tokens_used, files_touched }
}
```

La task **no** acepta input que mapee directamente a un comando shell.
Solo acepta `mission` (debe existir en allowlist) + `params`
tipados por la mission. La construcción del comando pasa al runner
interno, no al caller.

## 6. Set inicial de missions (todas read-only, F4)

| Mission | Side effect | Output |
|---|---|---|
| `research` | Ninguno | `result_text` + `audit_log` |
| `lint-suggest` | Patch en `/scratch` → artifact | `patch_path` |
| `test-explain` | Ninguno | `result_text` + `audit_log` |
| `runbook-draft` | Markdown en `/scratch` → artifact | `patch_path` |

Ninguna mission de F4 escribe en `/work` (RO). Ninguna ejecuta `git
push` o `gh pr *`. La materialización es **siempre** un paso humano
posterior.

## 7. Fases

| Fase | Entregable | Bloquea a | Aprobación |
|---|---|---|---|
| **F1** | Este doc + plan + (post-aprobación) policy stub disabled + flag en `.env.example` | F2 | David revisa diseño |
| **F2** | Imagen sandbox `umbral-sandbox-copilot-cli` + smoke offline | F3 | David revisa Dockerfile |
| **F3** | `worker/tasks/copilot_cli.py` con guards, sin missions registradas | F4 | David revisa task |
| **F4** | Mission templates + smoke `research` end-to-end (flag aún `false` en prod) | F5 | David revisa missions |
| **F5** | `rick-tech` ROLE.md (o extensión `rick-delivery`) + dispatcher routing | F6 | David revisa rol |
| **F6** | Activación `RICK_COPILOT_CLI_ENABLED=true` en producción | — | **David explícito** |

## 8. Criterios de aceptación de F1 (esta PR)

- [x] Diseño de 5 capas documentado.
- [x] Estado runtime verificado y registrado.
- [x] Restricciones absolutas explícitas.
- [x] Mission set inicial declarado.
- [x] Roadmap por fases con dependencias.
- [ ] Plan de session sembrado en SQL (todos + deps). _(hecho fuera del repo)_
- [ ] PR draft a main, sin merge.

## 9. Decisiones pendientes (requieren input de David)

1. **Mission set inicial**: ¿las cuatro missions de §6 son las
   correctas o agregar/quitar alguna? (p.ej. `repo-tour`, `dep-audit`).
2. **Red del sandbox**: ¿`--network=none` estricto en F2 (más seguro,
   missions sin LLM remoto) o egress filtrado desde el inicio?
3. **GitHub App vs PAT clásico**: confirmar que App con read-only es
   el modelo deseado, no un PAT scoped del usuario `rick`.
4. **Ubicación del flag**: ¿`/etc/umbral/copilot-cli.env` aceptable, o
   integrarlo en el `EnvironmentFile` existente del worker?
5. **`rick-tech` vs extensión de `rick-delivery`**: ¿agente nuevo o
   capability adicional sobre el rol existente?

---

> **Próximo paso si este diseño se aprueba:** completar F1 con commit
> separado del policy stub (`enabled: false`) y la entrada en
> `.env.example`, abrir PR draft a main. **No se ejecuta nada de F2+
> sin aprobación explícita de cada fase.**
