---
name: github-ops
description: >-
  Operate Git and GitHub from the VPS: branches, commits, pushes, and pull requests.
  Use when "create branch", "commit and push", "open PR", "github preflight",
  "orchestrate tournament branches", "check git status", "push to GitHub",
  or "branch cleanup".
metadata:
  openclaw:
    emoji: "\U0001F4BB"
    requires:
      env:
        - GITHUB_TOKEN
---

# GitHub Ops Skill

Rick gestiona operaciones Git y GitHub desde la VPS usando SSH (deploy key) para git y un PAT fine-grained (`GITHUB_TOKEN`) para la API de GitHub.

## Requisitos

- **SSH deploy key** (`id_ed25519_umbral`): para `git fetch`, `git push`, `git pull`. Configurada en el repo como deploy key con write access.
- **`GITHUB_TOKEN`**: PAT fine-grained (cuenta `UmbralBIM`) con permisos Contents:Read, Pull requests:RW, Metadata:Read. Usado por `gh` CLI y los handlers de API.
- **`gh` CLI**: v2.45.0+ instalado en la VPS.

## Identidad

- **Commits**: aparecen como `Rick (AI Orchestrator) <rick.asistente@gmail.com>` (identidad git de la VPS).
- **PRs y comentarios en GitHub**: aparecen como **UmbralBIM** (dueño del PAT).
- Solo los commits son atribuibles a Rick por identidad propia.

## Tasks disponibles

### 1. Preflight

Task: `github.preflight`

```json
{
  "repo_path": "/home/rick/umbral-agent-stack"
}
```

Valida que SSH, token, repo y worktree estén listos antes de cualquier operación.

#### Respuesta

```json
{
  "ok": true,
  "ssh": true,
  "token": true,
  "token_user": "UmbralBIM",
  "repo_path": "/home/rick/umbral-agent-stack",
  "branch": "main",
  "clean": true,
  "remote_reachable": true
}
```

Si algo falla, `ok: false` con el campo `error` indicando el bloqueante exacto.

### 2. Crear rama

Task: `github.create_branch`

```json
{
  "branch_name": "rick/feature-name",
  "base": "main"
}
```

#### Parámetros

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `branch_name` | str | sí | Debe empezar con `rick/` |
| `base` | str | no | Rama base (default: `"main"`) |

#### Respuesta

```json
{
  "ok": true,
  "branch": "rick/feature-name",
  "base": "main"
}
```

### 3. Commit y push

Task: `github.commit_and_push`

```json
{
  "message": "feat: add new validation mode",
  "files": ["worker/tasks/github_tournament.py", "tests/test_github_tournament.py"],
  "branch_name": "rick/feature-name"
}
```

#### Parámetros

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `message` | str | sí | Mensaje de commit |
| `files` | list[str] | sí | Lista explícita de archivos. **Nunca** se ejecuta `git add -A` |
| `branch_name` | str | no | Verificación de seguridad: confirma que HEAD coincide |

#### Respuesta

```json
{
  "ok": true,
  "branch": "rick/feature-name",
  "commit_sha": "abc123...",
  "files_changed": 2,
  "files": ["worker/tasks/github_tournament.py", "tests/test_github_tournament.py"],
  "pushed": true
}
```

### 4. Abrir PR

Task: `github.open_pr`

```json
{
  "title": "feat: add validation mode X",
  "body": "Adds X validation for tournament contestants.",
  "branch_name": "rick/feature-name",
  "base": "main",
  "bridge_item_name": "Slice X",
  "linear_issue_id": "uuid-optional"
}
```

#### Parámetros

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `title` | str | sí | Título del PR |
| `body` | str | no | Descripción del PR |
| `branch_name` | str | no | Rama head (se resuelve de HEAD si se omite) |
| `base` | str | no | Rama base (default: `"main"`) |
| `bridge_item_name` | str | no | Nombre para item de puente en Notion (activa trazabilidad Notion) |
| `linear_issue_id` | str | no | UUID de issue en Linear (activa comentario en Linear) |

#### Respuesta

```json
{
  "ok": true,
  "pr_url": "https://github.com/Umbral-Bot/umbral-agent-stack/pull/N",
  "pr_number": 42,
  "branch": "rick/feature-name",
  "title": "feat: add validation mode X"
}
```

### 5. Orquestar torneo sobre ramas

Task: `github.orchestrate_tournament`

```json
{
  "topic": "Refactor auth middleware",
  "target_file": "worker/tasks/auth.py",
  "num_contestants": 3,
  "model": "gpt-5.4",
  "validation_mode": "python_ast_lint",
  "validation_target": "tests/test_auth.py",
  "auto_apply_winner": true
}
```

Compone el flujo completo: preflight → tournament.run → ramas por concursante → artefactos → cambios de código → validación → rejudge → eligibilidad → cherry-pick → rama final.

## Flujos típicos

### Flujo estándar: rama → commit → PR

1. `github.preflight` — verificar que todo está listo
2. `github.create_branch` — crear `rick/<feature>`
3. (hacer cambios en archivos)
4. `github.commit_and_push` — commit explícito + push
5. `github.open_pr` — abrir PR hacia `main`

### Flujo de torneo

1. `github.preflight`
2. `github.orchestrate_tournament` — ejecuta todo el pipeline
3. Revisar resultado, cherry-pick si `auto_apply_winner: false`
4. `github.open_pr` — abrir PR con el resultado del torneo

### Limpieza post-merge

Después de que David mergea un PR:
```bash
git fetch --prune origin
git branch -d rick/<feature>  # local
```

Las ramas remotas se eliminan al mergear el PR en GitHub.

## Guardrails

| Regla | Cómo se aplica |
|-------|----------------|
| **Nunca push a main** | `_validate_branch_name()` rechaza ramas protegidas |
| **Nunca merge de PRs** | No existe handler de merge. Rick abre PRs; David los mergea |
| **Nunca `git add -A`** | `commit_and_push` requiere lista explícita de `files` |
| **Prefijo `rick/`** | Branch name validation lo exige |
| **Worktree limpio** | `_ensure_clean_worktree()` verifica antes de operaciones de rama |
| **Token requerido para API** | `open_pr` falla con `ok: false` si falta `GITHUB_TOKEN` |
| **SSH para git, PAT para API** | Git usa remote SSH; solo `gh` recibe `GH_TOKEN` |
| **Contestants sin acceso a gh** | Sandbox Docker corre con `--network=none`, sin token, sin CLI |

## Copilot

`gh copilot` **no está instalado** actualmente en la VPS. Si se instala en el futuro:

- Solo Rick lo usará de forma centralizada; contestants nunca tienen acceso.
- Uso limitado a `gh copilot suggest` y `gh copilot explain` (asistencia local).
- Para tareas de alto poder (code review, generación masiva), preferir Cursor con David.
- Monitorear créditos: si David indica límite, desactivar inmediatamente.

## Notas

- El remote del repo apunta a SSH: `git@github.com:Umbral-Bot/umbral-agent-stack.git`.
- El PAT expira 2027-03-03. `preflight` detecta token expirado.
- Branch protection en `main` impide push directo y merge sin aprobación.
- Todas las tasks se encolan vía Dispatcher → Redis → Worker.
- Documentación de referencia: `docs/28-rick-github-workflow.md`, `docs/34-rick-github-token-setup.md`.
