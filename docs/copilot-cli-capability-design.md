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

**Decisión D3 (David, 2026-04-26) + verificación F2.5 contra docs oficiales:** preferencia de credencial:
- ✅ usar variable de entorno **`COPILOT_GITHUB_TOKEN`** inyectada al
  contenedor en runtime (NO al host)
- ❌ NO usar `GH_TOKEN` (precedencia 2 en Copilot CLI; lo evitamos para
  no mezclar superficies y para no habilitar accidentalmente `gh`)
- ❌ NO usar `GITHUB_TOKEN` (precedencia 3; mismo motivo)
- ❌ NO depender de `gh auth login`
- ❌ NO escribir credenciales a `~/.copilot/config.json`
- ❌ NO usar PAT clásico (`ghp_*`) — **explícitamente no soportado por
  Copilot CLI según `copilot login --help`**

**Confirmación oficial F2.5** (extracto literal de `copilot login --help`
ejecutado dentro de la imagen `umbral-sandbox-copilot-cli:6940cf0f274d`,
versión `@github/copilot@1.0.36`):

> *"Copilot CLI will use an authentication token found in environment
> variables. The following are checked in order of precedence:
> `COPILOT_GITHUB_TOKEN`, `GH_TOKEN`, `GITHUB_TOKEN`. Supported token
> types include fine-grained personal access tokens (v2 PATs) with the
> "Copilot Requests" permission, OAuth tokens from the GitHub Copilot
> CLI app, and OAuth tokens from the GitHub CLI (gh) app. Classic
> personal access tokens (`ghp_`) are not supported."*

Cross-check con [docs.github.com/en/copilot/how-tos/set-up/install-copilot-cli](https://docs.github.com/en/copilot/how-tos/set-up/install-copilot-cli):
> *"You can also authenticate using a fine-grained personal access
> token with the 'Copilot Requests' permission enabled."*

**Modelo elegido:** fine-grained PAT v2 con permiso único `Copilot
Requests` (sin `Contents: Write`, sin `Pull requests`, sin `Issues`).
Si más adelante GitHub libera tokens de GitHub App user-to-server con
soporte de Copilot CLI no-interactivo, migrar a esos.

**Decisión D4 (David, 2026-04-26):** EnvironmentFile separados:
- `/etc/umbral/copilot-cli.env` — config no-secreta (flag, límites)
- `/etc/umbral/copilot-cli-secrets.env` — secretos (`COPILOT_GITHUB_TOKEN`)
- owner `rick`, `chmod 600`, jamás commiteado, jamás impreso en logs
- rotación documentada por separado en F5

**Defensa adicional:**
- Redaction extendido en `_SENSITIVE_PATTERNS` para tokens
  `ghs_*`, `ghu_*`, `github_pat_*`, `gho_*`, `ghp_*`.
- Aplicar a TODO log, error, artifact escrito por la task.

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

## 7. Fases (roadmap completo F1→F9)

> **Dirección estratégica (David, 2026-04-26):** el objetivo final NO es
> quedarse en read-only. La autonomía de Rick × Copilot CLI debe crecer
> en volumen y utilidad, con límites claros de mutación y aprobación
> humana por fase. Cada fase desbloquea capacidades adicionales solo si
> la anterior pasó la revisión.

| Fase | Entregable | Mutación permitida | Aprobación |
|---|---|---|---|
| **F1** | Design doc + plan + policy/env stub disabled | ninguna | David ✅ (2026-04-26) |
| **F2** | Imagen sandbox `umbral-sandbox-copilot-cli` + smoke offline + hardening evidence | ninguna (host intacto) | David ✅ (2026-04-26) |
| **F3** | `worker/tasks/copilot_cli.py` con guards, registrada pero `enabled=false` | ninguna | David |
| **F4** | Mission templates read-only/artifact-only activables en entorno controlado | artifacts en `artifacts/copilot-cli/` | David |
| **F5** | Agente `rick-tech` (NUEVO, no extender `rick-delivery`) con contrato propio: permisos, memoria, logs, límites, handoffs | ninguna nueva | David |
| **F6** | Activación productiva limitada: flag global ON pero scope estrecho | runs Copilot reales, output read-only | David explícito |
| **F7** | Write-limited bajo policy: missions pueden escribir a rutas allowlisted del repo (sin push) | escritura local en branch | David |
| **F8** | PR-draft-limited bajo policy: la task puede crear branches y PR **draft**, sin merge ni comment | branch + PR draft | David |
| **F9** | Autonomía por lotes: budget, dashboard de créditos vs valor, rollback, revisión humana asíncrona | batch missions con presupuesto duro | David |

### 7.1 Mission set extendido

**Aprobadas en F1 (read-only, target F4):**
- `research`, `lint-suggest`, `test-explain`, `runbook-draft`

**Candidatas para F4/F5 (read-only/artifact-only):**
- `repo-tour` — recorrido estructurado del repo, output markdown
- `dep-audit` — auditoría de dependencias, output report
- `pr-review-draft` — review en draft, NUNCA comentado al PR
- `implementation-plan` — plan de implementación, output markdown
- `patch-proposal` — diff propuesto como artifact
- `branch-plan` — plan de ramas + commits sin ejecutar
- `codemod-plan` — plan de codemod sin ejecutar

**Regla:** En F2/F3 ninguna mission ejecuta autonomía real. En F4 son
read-only/artifact-only. En F7+ algunas pueden evolucionar a
write-limited si pasan revisión y eval.

### 7.2 Autonomía por lotes y créditos (F9 design seed)

Diseñado desde F2 para no bloquear escala futura:

- **batches**: lista de missions ejecutadas en serie/paralelo bajo un
  `batch_id`, cada mission con su mission_run_id propio.
- **presupuesto**: por corrida (`max_tokens`, `max_wall_sec`,
  `max_files_touched`) y por batch (`max_total_tokens`, `max_runs`).
- **tracking**: `reports/copilot-cli/<YYYY-MM>/credits-usage.jsonl`
  append-only con `{batch_id, mission, tokens, wall_sec, ok, value_tag}`.
- **artifacts**: `artifacts/copilot-cli/<batch_id>/<mission_run_id>/`
  con patch + audit log + result.json.
- **ranking**: futuro evaluador puntúa outputs (utilidad, calidad,
  riesgo) para alimentar policy.
- **dashboard semanal**: reporte "créditos usados vs valor producido".
- **rollback**: cada artifact incluye reverse-patch o branch
  descartable.
- **revisión humana asíncrona**: cola de approvals para missions
  write-limited / PR-draft.

## 8. Criterios de aceptación de F1 (esta PR)

- [x] Diseño de 5 capas documentado.
- [x] Estado runtime verificado y registrado.
- [x] Restricciones absolutas explícitas.
- [x] Mission set inicial declarado.
- [x] Roadmap por fases con dependencias.
- [ ] Plan de session sembrado en SQL (todos + deps). _(hecho fuera del repo)_
- [ ] PR draft a main, sin merge.

## 9. Decisiones aprobadas (David, 2026-04-26)

| # | Decisión | Aprobada |
|---|---|---|
| D1 | Mission set inicial: `research`, `lint-suggest`, `test-explain`, `runbook-draft` | ✅ |
| D1bis | Candidatas F4/F5: `repo-tour`, `dep-audit`, `pr-review-draft`, `implementation-plan`, `patch-proposal`, `branch-plan`, `codemod-plan` | ✅ |
| D2 | Sandbox F2 con `--network=none`, perfil `copilot-egress` filtrado solo para fases posteriores | ✅ |
| D3 | Credencial vía `COPILOT_GITHUB_TOKEN` inyectada al contenedor; **confirmado por docs oficiales (`copilot login --help`):** precedencia `COPILOT_GITHUB_TOKEN > GH_TOKEN > GITHUB_TOKEN`, soporta fine-grained PAT con `Copilot Requests`, OAuth de Copilot CLI app, OAuth de gh CLI app. **Classic PAT (`ghp_`) NO soportado.** En este stack: NO `GH_TOKEN`, NO `GITHUB_TOKEN`, NO `gh auth login`, NO config.json | ✅ |
| D4 | EnvironmentFiles separados `/etc/umbral/copilot-cli.env` + `/etc/umbral/copilot-cli-secrets.env`, owner `rick`, chmod 600 | ✅ |
| D5 | Agente nuevo `rick-tech` (o `rick-technical-operator`), NO extender `rick-delivery` | ✅ |
| D6 | F2 autorizada: build sandbox + Copilot CLI dentro del contenedor + smoke offline + verificación de hardening, sin activar capability, sin token real, sin instalar en host | ✅ |
| D7 | Roadmap F1→F9 con dirección de autonomía progresiva (read-only → artifact-only → write-limited → PR-draft-limited → batch autónomo) | ✅ |
| D8 | Diseño de batches/budget/tracking/artifacts/ranking/dashboard de créditos desde F2 | ✅ |
| D9 (F2.5) | Seccomp: usar perfil default de Docker (omitir `--security-opt seccomp`); smoke verifica `Seccomp=2` en `/proc/self/status` | ✅ |
| D10 (F2.5) | Deny-list explícita extendida con todas las variantes de `git push`, `gh pr/release/repo/secret/auth/api/workflow`, `gh ssh-key/gpg-key`, fork bomb, sudo, etc. | ✅ |

## 10. Egress profile design (DESIGN ONLY — NOT ACTIVATED)

> **Status:** diseño F2.5; activación pendiente para F6+. Mientras tanto
> el sandbox corre con `--network=none` estricto y **no** se permite
> egress real.

### 10.1 Endpoints permitidos (mínimos)

| Host | Puerto | Propósito |
|---|---|---|
| `api.githubcopilot.com` | 443 | Endpoint principal de Copilot API |
| `api.individual.githubcopilot.com` | 443 | Plan individual |
| `api.business.githubcopilot.com` | 443 | Plan Business |
| `api.enterprise.githubcopilot.com` | 443 | Plan Enterprise |
| `api.github.com` | 443 | API REST (auth, repo metadata) |
| `copilot-proxy.githubusercontent.com` | 443 | Streaming proxy |

**Todo lo demás bloqueado por defecto.** Ningún wildcard. Ningún DNS
abierto. Ningún access a registries de paquetes en runtime (paquetes ya
están en la imagen).

### 10.2 Cómo se aplicará (F6+)

Capas en serie, cada una falla CLOSED:

1. **Red Docker dedicada** `copilot-egress` (driver bridge).
2. **iptables/nftables** en host: en la cadena `DOCKER-USER`, drop por
   defecto para esa red, permit explícito a las IPs resueltas de los
   hosts de §10.1, refrescadas vía cron + DNS resolver controlado.
3. **DNS interno fijo**: el contenedor usa `--dns 1.1.1.1` ó un resolver
   propio que solo resuelve los hosts allowlisted.
4. **HTTP(S) proxy egress** opcional con allowlist por SNI (F8+ si se
   necesita inspección).
5. **Wrapper en contenedor**: aún con red, el wrapper sigue bloqueando
   `git push`, `gh pr *`, etc. Doble defensa.

### 10.3 Auditoría

- `reports/copilot-cli/egress/<YYYY-MM>/<batch_id>.jsonl` — append-only
  log de cada conexión (timestamp, host, sni, bytes_sent, bytes_recv,
  duration_ms, batch_id, mission_run_id).
- Conteo por host vs allowlist al final de cada batch.
- Alarma en dispatcher si conteo de bloqueos > umbral.

### 10.4 Cómo se apaga

- `config/tool_policy.yaml :: copilot_cli.egress.activated` debe ser
  `true` (default `false`).
- `RICK_COPILOT_CLI_ENABLED=true` (worker).
- `COPILOT_EGRESS_ACTIVATED=true` (variable separada para apagar la red
  sin tocar la capability).
- Apagado: cualquiera de las tres en `false` → vuelve a `--network=none`.

### 10.5 Por qué NO red abierta

- Copilot CLI puede sugerir cualquier `curl` arbitrario. Sin allowlist,
  un prompt injection en un README malicioso podría exfiltrar secretos
  del entorno.
- La red allowlisted limita el blast radius incluso si el wrapper falla
  y aunque el modelo decida ejecutar comandos creativos.
- El runner Docker en F2 ya prueba que `--network=none` funciona; el
  perfil `copilot-egress` es la mínima superficie adicional necesaria
  para que Copilot pueda llamar a su backend.

### 10.6 Estado actual

- ⚠️ Diseñado en `config/tool_policy.yaml :: copilot_cli.egress`
  (`activated: false`, endpoints listados, audit_log path documentado).
- ❌ NO implementado: no existen reglas iptables/nftables, no existe
  red Docker `copilot-egress`, no hay DNS resolver dedicado.
- ❌ NO se ejecuta Copilot CLI con red real — todos los tests F2/F2.5
  son `--network=none`.



| # | Decisión | Aprobada |
|---|---|---|
| D1 | Mission set inicial: `research`, `lint-suggest`, `test-explain`, `runbook-draft` | ✅ |
| D1bis | Candidatas F4/F5: `repo-tour`, `dep-audit`, `pr-review-draft`, `implementation-plan`, `patch-proposal`, `branch-plan`, `codemod-plan` | ✅ |
| D2 | Sandbox F2 con `--network=none`, perfil `copilot-egress` filtrado solo para fases posteriores | ✅ |
| D3 | Credencial vía `COPILOT_GITHUB_TOKEN` inyectada al contenedor; preferencia GitHub App user-to-server, fallback fine-grained PAT con `Copilot Requests`. NO `GH_TOKEN`, NO `GITHUB_TOKEN`, NO `gh auth login`, NO config.json, NO PAT clásico | ✅ |
| D4 | EnvironmentFiles separados `/etc/umbral/copilot-cli.env` + `/etc/umbral/copilot-cli-secrets.env`, owner `rick`, chmod 600 | ✅ |
| D5 | Agente nuevo `rick-tech` (o `rick-technical-operator`), NO extender `rick-delivery` | ✅ |
| D6 | F2 autorizada: build sandbox + Copilot CLI dentro del contenedor + smoke offline + verificación de hardening, sin activar capability, sin token real, sin instalar en host | ✅ |
| D7 | Roadmap F1→F9 con dirección de autonomía progresiva (read-only → artifact-only → write-limited → PR-draft-limited → batch autónomo) | ✅ |
| D8 | Diseño de batches/budget/tracking/artifacts/ranking/dashboard de créditos desde F2 | ✅ |
| D9 | F2.5 hardening: seccomp default profile activo, deny-list explícita 53 patrones, egress diseñado pero no activado | ✅ |
| D10 | Auth oficial confirmada: `COPILOT_GITHUB_TOKEN` + fine-grained PAT v2 con `Copilot Requests` (PAT clásico NO soportado) | ✅ |
| D11 | F3: registrar task `copilot_cli.run` con triple-gate, audit JSONL append-only, dry-run permanente (`phase_blocks_real_execution: true`), 17/17 tests verdes — capability sigue disabled | ✅ |
| D12 | F4: definir contratos de las 4 missions (`research`, `lint-suggest`, `test-explain`, `runbook-draft`) como `dry_run_artifact_only` con `max_files_touched: 0`, `network: none`, `requires_human_materialization: true`; audit dir gitignorado; capability sigue disabled | ✅ |
| D13 | F5: scaffold del agente `rick-tech` separado de `rick-delivery`; ROLE.md declara `copilot_cli.run` como única superficie de Copilot CLI, sin permisos de publish/merge/PR/comment/Notion; capability sigue disabled | ✅ |
| D14 | F6 step 1: agregar flag `RICK_COPILOT_CLI_EXECUTE` (default false) + constante `_REAL_EXECUTION_IMPLEMENTED=False` (hard guard, code-only); documentar EnvironmentFile layout `/etc/umbral/copilot-cli{,-secrets}.env` (mode 0600, owner rick); capability sigue disabled, token no provisionado, subprocess no invocado | ✅ |
| D15 | F6 step 2: artifacts de repo bajo `infra/systemd/`, `infra/env/` + verifier `scripts/verify_copilot_cli_env_contract.py` (chequea owner/mode, separación de variables, rechaza classic PAT, no imprime tokens); `/etc/umbral/*` NO creado, systemd live NO tocado, capability sigue disabled | ✅ |
| D16 | F6 step 3: artifacts de diseño bajo `infra/networking/` (nft template + resolver design note) + verifier `scripts/verify_copilot_egress_contract.py` (parity policy↔artifact, default deny, no live commands uncommented, no DNS por defecto); `nftables`/`iptables`/Docker network NO tocados, `copilot_cli.egress.activated` sigue false | ✅ |


---

## 11. Estado por fase

| Fase | Estado | Detalle |
|---|---|---|
| F1 | ✅ done | design + policy stub + .env.example |
| F2 | ✅ done | sandbox image + offline smoke 8/8 |
| F2.5 | ✅ done | seccomp default + deny-list 53 + wrapper tests 60/60 + auth confirmada |
| **F3** | **✅ done** | **task `copilot_cli.run` registrada, triple-gate, audit JSONL, 17/17 tests, sin ejecución real** |
| **F4** | **✅ done** | **contratos de las 4 missions en YAML; `dry_run_artifact_only`; reports/copilot-cli/ gitignored; 39/39 tests** |
| **F5** | **✅ done** | **agente `rick-tech` con ROLE.md/HEARTBEAT.md propios; rick-delivery untouched; 55/55 tests** |
| **F6.step1** | **✅ done** | **flag `RICK_COPILOT_CLI_EXECUTE` + constante `_REAL_EXECUTION_IMPLEMENTED=False` + EnvironmentFile contract documentado; 63/63 tests; sin activación** |
| **F6.step2** | **✅ done** | **artifacts `infra/systemd/`, `infra/env/`, verifier `scripts/verify_copilot_cli_env_contract.py`; 74/74 tests; `/etc/umbral/*` no creado, systemd live no tocado** |
| **F6.step3** | **✅ done** | **artifacts `infra/networking/copilot-egress.nft.example` + `copilot-egress-resolver.md`, verifier `scripts/verify_copilot_egress_contract.py`; 86/86 tests; `nftables`/`iptables`/Docker network no tocados, egress sigue desactivado** |
| F6.step4+ | ⏸ pending approval | resolver implementation (dry-run), live nft apply, operation scoping enforcement, real subprocess wiring |
| F7–F9 | ⏸ blocked | write-limited / PR-draft-limited / batch autónomo |

---

> **Próximo paso si F3 se aprueba:** F4 = poblar el bloque
> `copilot_cli.missions` con las 4 misiones, mantener `enabled: false`,
> agregar mission-template tests. **F3 no ejecuta Copilot real ni
> requiere token.**
