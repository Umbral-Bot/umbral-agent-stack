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
