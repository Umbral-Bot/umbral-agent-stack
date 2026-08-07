# P1.3 — DISCARD del WIP en clones hermanos (2026-08-07)

> **Pack:** PKG-UAS-P1-3-CLONE-WIP-DISCARD · rama
> `claude/pkg-uas-p1-3-clone-wip-discard-20260807` · base `bcff86f6`
> **GO de David (verbatim):** "GO DISCARD" — limpiar working tree de ambos clones hermanos según
> [uas-p1-3-clone-wip-eval-20260807.md](uas-p1-3-clone-wip-eval-20260807.md) (14 paths
> `DISCARD_SAFE`, 0 `RESCUE`).
> **Alcance:** discard exacto del allowlist del acta previa. Sin `git restore`/`clean` fuera de
> lo listado, sin `stash drop`, sin tocar worktrees extra ni push --force ni borrar ramas remotas.

## 1. Clone A — `C:\GitHub\umbral-agent-stack-copilot`

**Inventario pre-discard** (`git status -sb`) — coincide 100% con el allowlist del pack, sin
paths nuevos:

```
## main...origin/main [behind 86]
 M docs/15-model-quota-policy.md
?? docs/audits/azure-foundry-capacity-openclaw-sync-2026-07-04.md
?? graphify-out/
```

**Comandos ejecutados:**

```
git restore -- docs/15-model-quota-policy.md
git clean -fd -- docs/audits/azure-foundry-capacity-openclaw-sync-2026-07-04.md graphify-out/
git fetch origin
git checkout main
git reset --hard origin/main
```

**Status post [E]:**

```
## main...origin/main
```

Working tree limpio, `HEAD` en `bcff86f6` = `origin/main` exacto (ahead/behind 0/0).

## 2. Clone B — `C:\GitHub\umbral-agent-stack-codex-coordinador`

**Inventario pre-discard** (`git status -sb`) — coincide 100% con el allowlist del pack (8
tracked + 9 untracked, incluye 5 archivos dentro de `.playwright-mcp/`), sin paths nuevos:

```
## codex/editorial-linkedin-smoke-rescue...origin/main [behind 268]
 M docs/ops/editorial-agent-flow.md
 M evals/editorial/gold-set-minimum.yaml
 M openclaw/workspace-agent-overrides/rick-communication-director/ROLE.md
 M openclaw/workspace-agent-overrides/rick-qa/ROLE.md
 M openclaw/workspace-templates/skills/director-comunicacion-umbral/CALIBRATION.md
 M openclaw/workspace-templates/skills/director-comunicacion-umbral/SKILL.md
 M openclaw/workspace-templates/skills/linkedin-content/SKILL.md
 M openclaw/workspace-templates/skills/linkedin-david/SKILL.md
?? .agents/tasks/2026-07-12-001-copilot-openclaw-oauth-only-urgent.md
?? .playwright-mcp/
?? docs/ops/editorial-linkedin-quality-smoke-tests.md
?? docs/ops/editorial-publicaciones-human-review-contract.md
?? p10f-ifc-after-final.png
?? pkg5a-admin-icons-unauth.png
?? pkg5a-chat-unauth.png
?? pkg5a-noticias-public.png
?? scripts/export-vscode-config.ps1
```

**Chequeo de proceso activo (regla dura del pack, previo a limpiar):** búsqueda de todos los
procesos del sistema por línea de comando conteniendo `codex-coordinador` (`Get-CimInstance
Win32_Process | Where-Object CommandLine -like "*codex-coordinador*"`) → único match fue la
propia consulta de PowerShell. Sin `.git/index.lock`. `mtime` de los archivos untracked entre
2026-06-01 y 2026-06-24 (más de un mes de antigüedad respecto a hoy 2026-08-07) — sin actividad
reciente. **No STOP** — se procedió.

**Comandos ejecutados:**

```
git restore -- docs/ops/editorial-agent-flow.md evals/editorial/gold-set-minimum.yaml \
  openclaw/workspace-agent-overrides/rick-communication-director/ROLE.md \
  openclaw/workspace-agent-overrides/rick-qa/ROLE.md \
  openclaw/workspace-templates/skills/director-comunicacion-umbral/CALIBRATION.md \
  openclaw/workspace-templates/skills/director-comunicacion-umbral/SKILL.md \
  openclaw/workspace-templates/skills/linkedin-content/SKILL.md \
  openclaw/workspace-templates/skills/linkedin-david/SKILL.md

git clean -fd -- .agents/tasks/2026-07-12-001-copilot-openclaw-oauth-only-urgent.md \
  .playwright-mcp/ docs/ops/editorial-linkedin-quality-smoke-tests.md \
  docs/ops/editorial-publicaciones-human-review-contract.md \
  p10f-ifc-after-final.png pkg5a-admin-icons-unauth.png pkg5a-chat-unauth.png \
  pkg5a-noticias-public.png scripts/export-vscode-config.ps1

git fetch origin
```

**Desvío reportado — conflicto de worktree en `git checkout main`:** el pack pedía `git checkout
main` seguido de `git reset --hard origin/main`. Ese comando falló:

```
fatal: 'main' is already used by worktree at 'C:/Users/david/.codex/worktrees/f8a-prompt-quoting-fix'
```

`git worktree list` confirmó que la rama `main` está en uso exclusivo por uno de los 13
worktrees prohibidos de tocar (`C:/Users/david/.codex/worktrees/f8a-prompt-quoting-fix`,
`[main]` @ `41bfeec`). Forzar el checkout ahí habría requerido tocar ese worktree —
**prohibido explícitamente por el pack**. En su lugar se usó:

```
git checkout --detach origin/main
```

Esto logra el objetivo declarado por el pack ("Verificar: git status -sb limpio y = origin/main")
— working tree con el contenido exacto de `origin/main`, status limpio — **sin** reclamar el
nombre de rama `main` (que pertenece a otro worktree) y **sin** tocar ningún otro worktree. La
rama local vieja `codex/editorial-linkedin-smoke-rescue` **no fue tocada** (el pack la marcaba
opcional): sigue en `46aa07c3`, intacta.

**Status post [E]:**

```
## HEAD (no branch)
bcff86f6a2dc1c77d034acc01b92a690d7fb9385
```

Working tree limpio, `HEAD` (detached) en `bcff86f6` = `origin/main` exacto.

## 3. Exclusiones respetadas

- 4 stashes viejos en cada clone — no tocados (`stash drop` prohibido por el pack).
- 13 worktrees extra del clone B — ninguno modificado; el conflicto de `main` en
  `f8a-prompt-quoting-fix` se resolvió sin tocarlo (ver §2).
- `codex/editorial-linkedin-smoke-rescue` (rama local del clone B) — intacta en `46aa07c3`, no
  borrada, no reseteada.
- Sin `push --force`, sin borrado de ramas remotas, sin tocar `umbral-bot-copilot`.

## 4. Gate

`UAS_P13_CLONE_WIP_DISCARD_PASS = Y` — ambos clones quedan clean con contenido idéntico a
`origin/main @ bcff86f6`:

| Clone | Status final [E] | HEAD |
|---|---|---|
| `-copilot` | `## main...origin/main` (limpio) | `bcff86f6` (branch `main`) |
| `-codex-coordinador` | `## HEAD (no branch)` (limpio) | `bcff86f6` (detached) |
