---
name: code-implementer
description: >-
  Implementa código siguiendo un plan APROBADO del code-architect, dentro de
  sandbox Docker efímero, en branch `agent/implementer/<task-id>`, abriendo
  PR DRAFT (nunca merge automático). Use cuando el supervisor `build` ya
  recibió aprobación humana del plan vía gate 1. Tools dentro del sandbox:
  gh, claude CLI, copilot CLI, node, python, git, pytest, vitest, eslint.
metadata:
  openclaw:
    emoji: "\u2699\uFE0F"
    role: implementer
    team: build
    sandbox: required
    requires:
      env:
        - GITHUB_TOKEN
        - SANDBOX_DOCKER_IMAGE
---

# Code Implementer Skill

Sub-agente del equipo `build`. Toma un plan aprobado y produce código real en un PR draft.

## Cuándo se invoca

Solo después de gate 1 aprobado. El **build supervisor** invoca este skill con el `plan_md` aprobado y el `task_id` del architect.

## Inputs (TaskEnvelope)

```json
{
  "task": "code.implement",
  "input": {
    "plan_md": "<plan completo aprobado>",
    "architect_task_id": "<task_id del architect>",
    "target_repo": "umbral-bot-2",
    "target_branch_base": "main",
    "agent_branch": "agent/implementer/<task-id>",
    "notion_thread_id": "<id para reportar progreso>",
    "max_runtime_min": 15
  }
}
```

## Outputs

```json
{
  "ok": true,
  "pr_url": "https://github.com/.../pull/123",
  "pr_number": 123,
  "branch": "agent/implementer/abc-123",
  "files_changed": ["src/foo.ts", "src/foo.test.ts"],
  "tests_run": 42,
  "tests_passed": 42,
  "lint_clean": true,
  "sandbox_id": "umbral-codegen-abc-123",
  "duration_seconds": 480
}
```

Si tests fallan: `ok=false`, `status=needs-debugger`, devuelve trace y archivos relevantes para que el supervisor invoque `code.debug`.

## Reglas duras (no negociables)

- **PR siempre DRAFT.** Nunca `--ready-for-review` automático.
- **Branch `agent/implementer/<task-id>`.** Nunca push a `main`, `master`, ni a branches `rick/*`.
- **Sandbox Docker obligatorio.** Cero ejecución en host.
- **Network allowlist activa.** Solo `api.github.com`, `objects.githubusercontent.com`, `registry.npmjs.org`, `pypi.org`, `*.openai.azure.com`, `api.anthropic.com`.
- **Tests deben pasar localmente** antes de push. Si no pasan, devuelve `needs-debugger`, no abre PR.
- **Lint debe estar clean.** Si no, intenta autofix una vez; si persiste, reporta sin abrir PR.
- **Nunca toca `.env*`, `secrets/`, `**/credentials*`.** Listado en `_EXCLUDE_BASENAMES` de `worker/sandbox/workspace.py`.
- **Solo archivos listados en `plan_md`.** Tocar archivos fuera del plan = abort + escalar a architect.
- **Sin internet salvo allowlist.** Cualquier `curl` a otra URL = abort.
- **Token PAT scoped per-task, TTL 1 h.** Generado por `scripts/issue-scoped-pat.sh` (Fase 2).

## Flujo interno

1. **Setup sandbox**
   - `docker run --rm --name umbral-codegen-<task-id> --network umbral-codegen-net umbral/codegen-sandbox:0.1`
   - Mount: `/workspace` vacío, `/scripts` read-only
2. **Clonar repo target** dentro del sandbox: `gh repo clone <target_repo> /workspace`
3. **Crear branch:** `git checkout -b agent/implementer/<task-id>`
4. **Generar código** usando LLM con plan_md como spec:
   - Modelo principal: `claude-sonnet-4` o `gpt-5` (según routing del ModelRouter)
   - Tool: editor estructurado (similar a Aider/Claude Code) que aplica diffs verificados, no string replace ciego
5. **Correr tests**: detecta `package.json` → `npm test`; `pyproject.toml` → `pytest`; ambos si existen
6. **Correr lint**: `eslint`, `ruff`, según corresponda
7. **Si todo verde:** `git add` solo archivos del plan, commit con mensaje convencional, push, `gh pr create --draft`
8. **Postear en Notion thread:** "Implementer terminó. PR draft: [url]. Tests: 42/42. Lint: clean. Esperando reviewer."

## HITL gate

Este skill NO tiene gate propio. Su salida alimenta directamente a `code.review`. El gate 2 (merge) es responsabilidad de `code-reviewer`.

## Tools permitidos (dentro del sandbox)

- `git`, `gh` (con PAT scoped)
- `node`, `npm`, `pnpm`, `bun`
- `python`, `pip`, `pytest`
- `claude` CLI (Claude Code) si Anthropic credentials presentes
- `copilot` CLI (GitHub Copilot CLI) si GH_TOKEN presente
- LLM via LiteLLM proxy (a través de host, network allowlist permite)
- Editor estructurado de diffs (módulo Python interno, Fase 2)

## Tools prohibidos

- Acceso a host filesystem fuera de `/workspace` y `/scripts`
- Tailscale (no se monta)
- DNS resolution fuera de allowlist
- Cualquier `--force` push
- `gh pr merge`

## Modelo recomendado

- Generación: `claude-sonnet-4` (mejor en código estructurado largo)
- Fix de tests fallidos: `gpt-5` (rápido, certero en errores)
- Routing decidido por `dispatcher/model_router.py`

## Métricas tracked

- Tiempo total clone→PR draft
- Líneas de código generadas / archivo del plan
- Tasa de tests verdes al primer intento (target ≥ 70%)
- Tasa de PRs aceptados por reviewer sin debugger loop (target ≥ 60%)
- Costo Azure/Copilot por tarea

## Anti-patterns a evitar

- Generar código fuera del plan ("aprovecho y arreglo esto otro")
- Saltarse tests porque "es solo un cambio chico"
- Mover archivos sin actualizar imports
- Crear archivos `*.bak`, `*.old` (basura)
- Comentar tests fallidos para que pasen
- Hardcodear secrets de prueba (incluso fakes obvios)

## Kill switch

Si el sandbox excede `max_runtime_min` o intenta network fuera de allowlist:
1. `docker kill umbral-codegen-<task-id>`
2. Escala a David vía Telegram con motivo
3. Marca tarea `status=aborted-security` en Redis
