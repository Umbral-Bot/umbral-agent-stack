# F2 evidence — Copilot CLI sandbox build & offline smoke

> **Fecha:** 2026-04-26
> **Branch:** `rick/copilot-cli-capability-design`
> **Worktree:** `/home/rick/umbral-agent-stack-copilot-cli`
> **Aprobación humana:** David, prompt 2026-04-26 18:59 — F2 autorizada
> con scope estricto (sandbox + smoke offline, sin token, sin host
> install, sin runtime change).

## Scope autorizado

✅ Build de imagen `umbral-sandbox-copilot-cli`
✅ Instalar Copilot CLI **dentro** del contenedor (no en host)
✅ Smoke offline sin token real
✅ Verificación de hardening
❌ Capability sigue **deshabilitada** (`enabled=false`, `RICK_COPILOT_CLI_ENABLED=false`)
❌ Sin red, sin token, sin runtime, sin Notion, sin gates, sin push

## Archivos creados

| Archivo | Propósito |
|---|---|
| `worker/sandbox/Dockerfile.copilot-cli` | Imagen base node:22.14-bookworm-slim + `@github/copilot@1.0.36` pinned |
| `worker/sandbox/copilot-cli-smoke` | Script de smoke offline ejecutado dentro del contenedor |
| `worker/sandbox/copilot-cli-wrapper` | Wrapper que falla CLOSED en `banned_subcommands` (substring match) |
| `worker/sandbox/refresh-copilot-cli.sh` | Build idempotente con tag determinista (sha256 sobre Dockerfile + smoke + wrapper) |
| `worker/sandbox/run-copilot-cli-smoke.sh` | Runner con flags de hardening completos |

## Versión de Copilot CLI

`@github/copilot@1.0.36` — confirmado contra `https://registry.npmjs.org/@github/copilot/latest` el 2026-04-26.

Pin explícito en `ARG COPILOT_CLI_VERSION=1.0.36`. Cualquier bump
requiere commit revisado.

## Build

```bash
$ bash worker/sandbox/refresh-copilot-cli.sh
refresh-copilot-cli.sh: building umbral-sandbox-copilot-cli:5abe3642c671
...
refresh-copilot-cli.sh: built umbral-sandbox-copilot-cli:5abe3642c671
TAG=5abe3642c671
```

- **Image:** `umbral-sandbox-copilot-cli:5abe3642c671`
- **Size:** ~234 MB
- **Manifest sha256:** `96455694a4504c2b4c2ba5ab11a0e16002f8ee719144504a4b4c96793c3cbeb3`
- **Base:** `node:22.14-bookworm-slim`
- **Runtime user:** `runner` (uid 10001 / gid 10001)
- **Workdir:** `/work` (read-only bind a runtime)

## Smoke offline — resultado

Comando: `bash worker/sandbox/run-copilot-cli-smoke.sh`

Flags aplicados (todos enforced):
```
--network=none
--read-only
--tmpfs /tmp:size=64m,mode=1777,exec,nosuid,nodev
--tmpfs /scratch:size=64m,mode=1777,nosuid,nodev
--tmpfs /home/runner/.cache:size=32m
--memory=1g --memory-swap=1g --cpus=1.0
--pids-limit=256
--cap-drop=ALL
--security-opt no-new-privileges
--security-opt seccomp=unconfined   # ver "Riesgo pendiente 1"
--user 10001:10001
--ipc=none
--mount type=bind,source=<repo>,target=/work,readonly
```

Resultado: **8/8 PASS**

```
[smoke] uid=10001 gid=10001 user=runner
[smoke]  PASS  uid is 10001 (non-root)
[smoke] copilot --version: GitHub Copilot CLI 1.0.36.
[smoke]  PASS  copilot binary present
[smoke]  PASS  no auth-related env vars leaked into smoke
[smoke]  PASS  DNS resolution blocked (expected under --network=none)
[smoke]  PASS  /work is read-only (write probe failed as expected)
[smoke]  PASS  /scratch is writable (tmpfs)
[smoke]  PASS  wrapper blocks 'git push'
[smoke]  PASS  wrapper blocks 'rm -rf'
[smoke] passes=8 fails=0
SMOKE_RESULT=ok
```

Aserciones verificadas:
1. ✅ uid 10001 (no root)
2. ✅ `copilot` binary presente y reporta versión 1.0.36
3. ✅ Sin tokens en env (`GITHUB_TOKEN`, `GH_TOKEN`, `COPILOT_GITHUB_TOKEN`, `GH_HOST` todos vacíos)
4. ✅ DNS bloqueado (`api.github.com` no resuelve bajo `--network=none`)
5. ✅ `/work` read-only (write probe falla)
6. ✅ `/scratch` writable (tmpfs)
7. ✅ Wrapper bloquea `git push` (exit 126, mensaje `BANNED_SUBCOMMAND`)
8. ✅ Wrapper bloquea `rm -rf` (exit 126, mensaje `BANNED_SUBCOMMAND`)

## Evidencia de no-impacto

| Aserción | Verificación |
|---|---|
| Host **NO** tiene Copilot CLI instalado | `which copilot` → no encontrado |
| Host **NO** tiene `gh` autenticado | `gh auth status` → "not logged into any GitHub hosts" |
| Host **NO** tiene `@github/copilot` global en npm | `npm ls -g --depth=0` → solo `clawhub`, `n8n`, `openclaw` |
| Runtime OpenClaw **intacto** | servicios `openclaw-gateway`, `openclaw-dispatcher`, `umbral-worker` no reiniciados ni tocados |
| Notion **no tocado** | sin tareas `notion.*` ejecutadas |
| Gates **no tocados** | sin escrituras a `evals/`, `tests/test_editorial_gold_set.py`, ni Notion CAND-* |
| Capability **deshabilitada** | `RICK_COPILOT_CLI_ENABLED=false` y `copilot_cli.enabled=false` siguen en repo |
| Token **no usado** | runner explícitamente no inyecta `COPILOT_GITHUB_TOKEN`; smoke verifica que el env esté vacío |
| `~/.openclaw/openclaw.json` | no modificado |
| Push autónomo | imagen no contiene `gh` CLI; `git push` bloqueado por wrapper Y por `--network=none` |

## Riesgos pendientes / TODO antes de F3

1. **`seccomp=default` falló al iniciar** en una primera prueba; el
   runner usa `seccomp=unconfined` provisional. Hay que generar un
   perfil seccomp custom (allowlist mínima para Node 22 + Copilot CLI)
   y reactivarlo en F3. Mientras tanto, las otras capas (cap-drop=ALL,
   no-new-privileges, network=none, read-only, uid 10001) siguen activas.
2. **Confirmar contra docs oficiales** qué token soporta Copilot CLI
   en modo no-interactivo (GitHub App user-to-server vs fine-grained
   PAT con `Copilot Requests`). Bloqueante para F3.
3. **Perfil de red `copilot-egress`** filtrado a `api.githubcopilot.com`
   + `api.github.com` está diseñado pero NO implementado todavía.
   Pendiente para cuando se necesite ejecución real de Copilot.
4. **Wrapper substring matching** es defensa-en-profundidad; en F3 hay
   que añadir `git push --force`, `git push -f`, `git push --force-with-lease`,
   `gh pr review`, `gh release` como entradas explícitas (aunque
   `git push` ya las cubre por substring).
5. **Persistencia de cache de Copilot:** la primera ejecución del
   binario despliega un bundle a `$HOME/.cache`. Bajo `--read-only`
   eso fallaba; el runner monta `/home/runner/.cache` como tmpfs
   (32 MB). Esto significa que el bundle se re-extrae en cada run —
   coste pequeño, pero a notar para perf en F4+.
6. **Tag de imagen** es determinista sobre `Dockerfile + smoke +
   wrapper`. Cualquier bump de `COPILOT_CLI_VERSION` cambia el
   contenido del Dockerfile y por tanto el tag — bien.

## Reproducibilidad

```bash
cd /home/rick/umbral-agent-stack-copilot-cli
git checkout rick/copilot-cli-capability-design
bash worker/sandbox/refresh-copilot-cli.sh --print
# umbral-sandbox-copilot-cli:5abe3642c671
bash worker/sandbox/refresh-copilot-cli.sh
bash worker/sandbox/run-copilot-cli-smoke.sh
# Esperado: SMOKE_RESULT=ok, 8/8 PASS
```

## Estado de capability tras F2

```
RICK_COPILOT_CLI_ENABLED        = false   (worker)
config/tool_policy.yaml :: copilot_cli.enabled = false
copilot_cli.missions            = {}
worker/tasks/copilot_cli.py     = (no existe — F3)
agente rick-tech                = (no existe — F5)
COPILOT_GITHUB_TOKEN en sandbox = (nunca inyectado en smoke)
```

**La capability NO está activa.** Para activarla se requiere:
- F3 (task implementada, `enabled=false`)
- F4 (missions definidas, smoke con token contra entorno controlado)
- F5 (agente `rick-tech` con contrato propio)
- F6 (aprobación explícita de David + flip de ambos flags + restart worker)

---

## F2.5 — Hardening cierre y auth confirmation (2026-04-26 PM)

### Scope autorizado

✅ Resolver problema de `seccomp` o documentar bloqueo
✅ Confirmar oficialmente modelo de auth no-interactivo de Copilot CLI
✅ Extender deny-list explícita para variantes de force push
✅ Diseñar (sin activar) perfil `copilot-egress`
✅ Actualizar docs/evidence
❌ Sin activar capability, sin token real, sin runtime, sin Notion

### F2.5.1 — Seccomp resuelto

**Causa raíz:** Docker 29.2.1 interpreta `--security-opt seccomp=default`
como un path a archivo (que no existe). El default profile se aplica
**omitiendo** la flag por completo. Verificado:

```
docker run ... --security-opt seccomp=default ...
  → docker: opening seccomp profile (default) failed: open default: no such file or directory

docker run ... (sin seccomp flag) ...
  → /proc/self/status :: Seccomp = 2   (filter mode)

docker run ... --security-opt seccomp=unconfined ...
  → /proc/self/status :: Seccomp = 0   (sin filtro)
```

**Decisión D9:** `run-copilot-cli-smoke.sh` ahora omite la flag seccomp
para que se aplique el default profile. El smoke verifica
`Seccomp = 2` en `/proc/self/status` como aserción de hardening.
**No se requiere perfil custom todavía** — el default de Docker es
suficiente para Node 22 + Copilot CLI 1.0.36 y bloquea ~44 syscalls
peligrosos (mount, ptrace, kexec, reboot, etc.).

Si en F3+ se necesita un perfil más estrecho (eliminando p.ej.
`unshare`, `clone3`, `setrlimit`), se generará y commiteará en
`worker/sandbox/seccomp-copilot-cli.json` y se referenciará desde el
runner. Por ahora **no es bloqueante**.

### F2.5.2 — Auth model confirmado

Ejecutado dentro de la imagen `umbral-sandbox-copilot-cli:6940cf0f274d`:

```
$ copilot login --help
Authenticate with Copilot via OAuth device flow.
...
Alternatively, Copilot CLI will use an authentication token found in
environment variables. This method is most suitable for "headless" use
such as automation. The following are checked in order of precedence:
COPILOT_GITHUB_TOKEN, GH_TOKEN, GITHUB_TOKEN. See `copilot help
environment` for more info.

Supported token types include fine-grained personal access tokens (v2
PATs) with the "Copilot Requests" permission, OAuth tokens from the
GitHub Copilot CLI app, and OAuth tokens from the GitHub CLI (gh) app.

Classic personal access tokens (ghp_) are not supported.
```

Cross-check oficial: [docs.github.com — Installing GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/set-up/install-copilot-cli)

**Conclusión (registrada en design §5.4 + §9 D3):**
- ✅ Variable: `COPILOT_GITHUB_TOKEN` (precedencia 1, evita conflictos
  con `gh`)
- ✅ Token: fine-grained PAT v2 con único permiso `Copilot Requests`
- ❌ Classic PAT (`ghp_*`): no soportado oficialmente
- ❌ `GH_TOKEN` / `GITHUB_TOKEN`: técnicamente soportados pero los
  evitamos para mantener separación de superficies
- ❌ `gh auth login` y `~/.copilot/config.json`: no usar (config
  persistente fuera de EnvironmentFile)

GitHub App user-to-server **no se confirmó como soportado** explícitamente
para Copilot CLI no-interactivo en docs oficiales. Si en el futuro se
documenta, migrar.

### F2.5.3 — Deny-list extendida y testeada

`config/tool_policy.yaml :: copilot_cli.banned_subcommands` y
`worker/sandbox/copilot-cli-wrapper` actualizados con todas las
variantes explícitas (53 patrones banned, ver design §5.2).

Nuevo script `worker/sandbox/test-copilot-cli-wrapper.sh` ejecuta
batería offline:

```
[wrapper-test] image=umbral-sandbox-copilot-cli:6940cf0f274d
[wrapper-test] banned cases: 53/53 PASS (every variant returns exit 126
  with BANNED_SUBCOMMAND marker)
[wrapper-test] allowed cases: 7/7 PASS (git status/log/diff/fetch,
  ls/cat/echo never blocked)
[wrapper-test] passes=60 fails=0
WRAPPER_TEST_RESULT=ok
```

### F2.5.4 — Egress profile diseñado (NO activado)

Ver design §10 completo. Resumen:
- Perfil `copilot-egress` diseñado en `config/tool_policy.yaml`
  (`activated: false`).
- 6 endpoints permitidos (api.githubcopilot.com + variantes plan +
  api.github.com + copilot-proxy.githubusercontent.com).
- Capas en serie planificadas: red Docker dedicada + nftables DOCKER-USER
  + DNS resolver allowlist + wrapper en contenedor (defensa en
  profundidad).
- Audit log path declarado: `reports/copilot-cli/egress/<YYYY-MM>/<batch_id>.jsonl`.
- Apagado por triple flag (`copilot_cli.egress.activated`,
  `RICK_COPILOT_CLI_ENABLED`, `COPILOT_EGRESS_ACTIVATED`).
- **Estado actual:** `--network=none` estricto, sin reglas iptables, sin
  red Docker creada. F2/F3/F4 permanecen en red cero.

### F2.5.5 — Re-build + tests

Image cambió por modificación de smoke + wrapper (tag determinista re-calculado):
- Antes: `umbral-sandbox-copilot-cli:5abe3642c671`
- Después: `umbral-sandbox-copilot-cli:6940cf0f274d`
- Manifest cambió por hash determinista sobre `Dockerfile.copilot-cli +
  copilot-cli-smoke + copilot-cli-wrapper`.

Resultados:
- `bash worker/sandbox/run-copilot-cli-smoke.sh` → **11/11 PASS**
  (3 nuevas: seccomp filter mode, no_new_privs=1, CapEff=0)
- `bash worker/sandbox/test-copilot-cli-wrapper.sh` → **60/60 PASS**

### F2.5.6 — No-impacto verificado (re-check)

| Aserción | Verificación |
|---|---|
| Host **NO** tiene Copilot CLI | `which copilot` → no encontrado |
| Host **NO** tiene `gh` autenticado | `gh auth status` → "not logged in" |
| Host **NO** tiene `@github/copilot` global | `npm ls -g --depth=0` → solo `clawhub`, `n8n`, `openclaw` |
| Runtime intacto | `systemctl --user is-active openclaw-gateway openclaw-dispatcher umbral-worker` → `active active active` |
| Capability sigue disabled | `RICK_COPILOT_CLI_ENABLED=false`, `copilot_cli.enabled=false` |
| Token real **no usado** | smoke explícitamente verifica env vacío |
| Notion / gates / `~/.openclaw/openclaw.json` | no tocados |
| Whitespace | `git diff --check` → ok |

### F2.5.7 — F3 ¿desbloqueada?

✅ **Sí**, condicional a:
1. ✅ Seccomp resuelto (default profile activo y verificado)
2. ✅ Auth model confirmado (`COPILOT_GITHUB_TOKEN` + fine-grained PAT v2 con `Copilot Requests`)
3. ✅ Deny-list explícita + testeada (60/60)
4. ✅ Egress diseñado (no activado — F3 sigue en `--network=none`)

**Riesgos remanentes registrados como TODO en F3, no bloqueantes:**
- Perfil seccomp custom más estrecho (opcional; default ya cubre lo
  esencial)
- Implementación física de red `copilot-egress` (recién en F6+)
- Cache de Copilot se re-extrae cada run (perf, no seguridad)

### F2.5.8 — Reproducibilidad

```bash
cd /home/rick/umbral-agent-stack-copilot-cli
git checkout rick/copilot-cli-capability-design
bash worker/sandbox/refresh-copilot-cli.sh --print
# umbral-sandbox-copilot-cli:6940cf0f274d
bash worker/sandbox/refresh-copilot-cli.sh
bash worker/sandbox/run-copilot-cli-smoke.sh    # → 11/11 PASS
bash worker/sandbox/test-copilot-cli-wrapper.sh # → 60/60 PASS
```
