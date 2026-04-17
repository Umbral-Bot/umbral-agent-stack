# 69 — Tournament Over Branches: Runbook Operativo

Runbook para operar, entender y extender `github.orchestrate_tournament` en el Umbral Agent Stack.

---

## 1. Qué es

Existen dos niveles de torneo:

| Handler | Qué hace | Toca Git |
|---------|----------|----------|
| `tournament.run` | Torneo LLM puro: discovery, develop, debate, judge. Produce texto comparativo y un veredicto. | No |
| `github.orchestrate_tournament` | Orquesta `tournament.run` y luego materializa cada enfoque en una rama Git con artefactos, código, validación, rejudge y eligibilidad. | Si |

`tournament.run` es la capa de razonamiento. `github.orchestrate_tournament` es la capa de ejecución que convierte ideas en ramas con código real.

---

## 2. Qué hace hoy

Flujo completo de `github.orchestrate_tournament`:

```
1. Preflight (SSH, token, worktree limpio)
2. tournament.run (discovery → develop → debate → judge) → verdict inicial
3. Por cada contestant:
   a. Crear rama rick/t/{id}/{a,b,c,...}
   b. Escribir artefacto de propuesta en .rick/tournaments/
   c. [opt-in] Generar código y commit (generate_code=true)
   d. [opt-in] Validar código (validation_mode)
4. [opt-in] Rejudge: segundo pase LLM con evidencia de código + validación
5. Eligibilidad: filtro que puede forzar ESCALATE si el winner no pasó validación
6. Cherry-pick del winner a rick/t/{id}/final
7. Retorno a rama base
8. Cleanup de sandbox (si pytest_target)
```

Cada paso que falla degrada en lugar de abortar. Un contestant con artefacto fallido sigue participando; un cherry-pick fallido deja la rama final vacía con error explícito.

---

## 3. Inputs operativos

Todos los parámetros de `input_data`:

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `challenge` | str | **requerido** | Descripción del assignment de desarrollo |
| `base` | str | `"main"` | Rama base para crear branches |
| `num_approaches` | int | `3` | Número de enfoques (2-5) |
| `approaches` | list[str] | auto | Nombres predefinidos; si se omite, LLM los descubre |
| `models` | list[str] | `["azure_foundry"]` | Modelos por contestant (rota si hay menos que num_approaches) |
| `judge_model` | str | primer modelo | Modelo para judge y rejudge |
| `debate_rounds` | int | `1` | Rondas de debate (0 para omitir) |
| `temperature` | float | `0.9` | Temperatura para desarrollo (diversidad) |
| `max_tokens` | int | `2048` | Presupuesto por llamada LLM |
| `generate_code` | bool | `false` | Habilita generación de código (Phase 2) |
| `target_file` | str | `null` | Archivo real del repo que cada contestant debe modificar. Requiere `generate_code=true`. Validado contra denylist de prefijos y allowlist de extensiones |
| `validation_mode` | str | `"none"` | Modo de validación: `none`, `python_compile`, `python_ast_lint`, `pytest_target` |
| `validation_timeout_s` | float | `20` (general) / `45` (pytest_target) | Timeout por contestant. Hard cap: 60s |
| `rejudge` | bool | `false` | Segundo pase LLM con evidencia real |

### target_file: reglas de validación

- Debe ser ruta relativa (no absoluta, no `..`)
- Prefijos denegados: `.git/`, `.github/`, `.rick/`, `.venv/`, `venv/`, `node_modules/`, `__pycache__/`
- Extensiones permitidas: `.py`, `.md`, `.txt`, `.json`, `.yaml`, `.yml`, `.toml`, `.ini`, `.cfg`, `.sh`

### validation_mode: modos disponibles

| Modo | Qué hace | Ejecuta código | Requiere Docker |
|------|----------|----------------|-----------------|
| `none` | Sin validación | No | No |
| `python_compile` | `python3 -m py_compile` | Minimamente (compilación) | No |
| `python_ast_lint` | `ast.parse` + `ast.NodeVisitor` estático | No | No |
| `pytest_target` | pytest dentro de Docker sandbox | Si (aislado) | Si |

---

## 4. Outputs operativos

Estructura del return cuando `ok: true`:

```
{
  ok: true,
  tournament_id: "a03ed652",          # 8-hex, identifica ramas y artefactos
  challenge: "...",
  base: "main",
  contestants: [                       # uno por enfoque
    {
      id: 1,
      approach: "Approach A",
      branch: "rick/t/a03ed652/a",
      proposal_excerpt: "...",         # primeros 500 chars
      artifact: {                      # propuesta escrita en .rick/tournaments/
        path: ".rick/tournaments/...",
        written: true,
        commit: { ok, commit_sha, ... }
      },
      code_change: {                   # null si generate_code=false
        attempted: true,
        mode: "target_file"|"sandbox",
        target_file: "worker/tasks/auth.py",
        path: "worker/tasks/auth.py",  # ruta final escrita
        written: true,
        parse_error: null,             # error de parsing del FILE block LLM
        commit: { ok, commit_sha, ... }
      },
      validation: {                    # resultado de validación
        ran: true, mode: "python_ast_lint",
        passed: true,                  # bool, no rc numérico
        duration_ms: 150,
        log_tail: "...",               # últimas 20 líneas / 2000 chars
        error: null
      }
    }
  ],
  verdict: {                           # veredicto efectivo (puede venir de rejudge)
    text: "...",
    winner_id: 2,                      # int, o null si ESCALATE
    escalate: false
  },
  verdict_initial: {                   # null si rejudge no corrió; otherwise el veredicto original
    text, winner_id, escalate
  },
  rejudge: {
    ran: true/false,
    text, winner_id, escalate,
    override_attempt: true/false,      # si el rejudge intentó cambiar winner
    duration_ms, model_used, error
  },
  eligibility: {
    enforced: true/false,
    mode: "python_ast_lint",
    passed_ids: [1, 3],
    failed_ids: [2],
    not_ran_ids: [],
    winner_id_before: 2,
    winner_id_after: 1,                # o null si forced_escalate
    forced_escalate: false,
    reason: "..."
  },
  final_branch: "rick/t/a03ed652/final",  # null si ESCALATE
  final_result: {                          # null si ESCALATE
    cherry_picked: true,
    pushed: true,
    from_commit_sha: "abc123",
    from_contestant_id: 2,
    error: null
  },
  branches_created: ["rick/t/.../a", "rick/t/.../b", "rick/t/.../c", "rick/t/.../final"],
  meta: {
    total_llm_calls: 8,
    total_duration_ms: 45000,
    models_used: ["gpt-5.4"],
    generate_code: true,
    target_file: "worker/tasks/auth.py",
    validation_mode: "python_ast_lint",
    validation_timeout_s: 20,
    rejudge: true,
    pytest_target: {                   # null si validation_mode != pytest_target
      ok, image_ref, resolved_target, allowlist_size, workspace_prepared, error
    }
  }
}
```

### Cómo leer el resultado

1. **Empezar por `ok`**. Si `false`, leer `error` y `preflight` (si existe).
2. **`verdict.escalate`**: si `true`, no hay winner y no hay `final_branch`. Escalar a David.
3. **`eligibility.forced_escalate`**: si `true`, el winner original no era elegible. Mismo efecto que ESCALATE.
4. **`verdict_initial` vs `verdict`**: si `rejudge.ran` es `true`, `verdict` es el resultado del rejudge y `verdict_initial` guarda el original.
5. **`final_result.cherry_picked`**: si `false` con `error`, la rama final existe pero está vacía.
6. **Por contestant**: revisar `validation.passed` para saber quién sobrevivió la validación.

---

## 5. Guardrails

| Guardrail | Implementación |
|-----------|----------------|
| Nunca push a main | `_validate_branch_name()` rechaza ramas protegidas; preflight verifica |
| Nunca merge de PRs | No existe handler de merge en todo el codebase |
| Rick centraliza Git/GitHub | Todos los handlers `github.*` operan bajo identidad de Rick (SSH + PAT) |
| Contestants sin acceso a gh | Sandbox Docker corre con `--network=none`, sin token, sin CLI, user no-root (10001) |
| Nunca git add -A | `commit_and_push` requiere lista explícita de files |
| Prefijo rick/ obligatorio | Todas las ramas creadas empiezan con `rick/t/` |
| Worktree limpio | `_ensure_clean_worktree()` antes de operaciones de rama |
| Timeout de validación | Hard cap 60s por contestant; nunca extensible |
| target_file restringido | Denylist de prefijos + allowlist de extensiones |

### ESCALATE

Significa que el juez no pudo elegir (trade-offs genuinos y cercanos) o que la eligibilidad lo forzó. En ambos casos:

- No se crea `final_branch`
- Rick debe presentar la tabla comparativa a David
- David decide manualmente qué enfoque usar (o descartar todos)

### Todos fallan validación

Si `validation_mode != "none"` y ningún contestant tiene `validation.passed == true`:

- Se fuerza `ESCALATE` independientemente de lo que dijo el juez
- `eligibility.forced_escalate = true`
- `eligibility.reason` explica por qué

### Winner no elegible

Si el juez eligió contestant 2 pero solo contestants 1 y 3 pasaron validación:

- Se fuerza `ESCALATE` (el filtro no elige un nuevo winner)
- `eligibility.winner_id_before = 2`, `eligibility.winner_id_after = null`
- `eligibility.forced_escalate = true`

---

## 6. Operación normal

### Lanzar un smoke test

Smoke mínimo (sin código, solo ramas + artefactos):

```json
{
  "task": "github.orchestrate_tournament",
  "input": {
    "challenge": "Smoke test: proponer 2 enfoques para refactorizar el logger del worker",
    "num_approaches": 2,
    "debate_rounds": 1
  }
}
```

Smoke con código + validación:

```json
{
  "task": "github.orchestrate_tournament",
  "input": {
    "challenge": "Mejorar el manejo de errores en worker/tasks/github.py",
    "num_approaches": 2,
    "generate_code": true,
    "target_file": "worker/tasks/github.py",
    "validation_mode": "python_ast_lint",
    "rejudge": true
  }
}
```

Smoke con pytest_target (requiere imagen Docker):

```json
{
  "task": "github.orchestrate_tournament",
  "input": {
    "challenge": "Refactorizar test_env_loader para mayor claridad",
    "num_approaches": 2,
    "generate_code": true,
    "target_file": "tests/test_env_loader.py",
    "validation_mode": "pytest_target",
    "validation_target": "tests/test_env_loader.py",
    "rejudge": true
  }
}
```

### Interpretar un resultado

1. Verificar `ok: true`
2. Revisar `verdict.escalate` — si `true`, revisar la tabla en `verdict.text`
3. Revisar `eligibility` — si `forced_escalate`, explicar a David por qué
4. Si hay `final_branch`, inspeccionar: `git log rick/t/{id}/final --oneline -5`
5. Revisar `meta.total_duration_ms` para ver si los tiempos son razonables

### Limpiar ramas rick/t/*

Después de revisar el resultado y cerrar (o descartar):

```bash
# Ver ramas del torneo
git branch -r | grep "rick/t/${TOURNAMENT_ID}"

# Eliminar remotas
git push origin --delete rick/t/${TOURNAMENT_ID}/a
git push origin --delete rick/t/${TOURNAMENT_ID}/b
git push origin --delete rick/t/${TOURNAMENT_ID}/c
git push origin --delete rick/t/${TOURNAMENT_ID}/final

# Eliminar locales
git branch -D rick/t/${TOURNAMENT_ID}/a
git branch -D rick/t/${TOURNAMENT_ID}/b
git branch -D rick/t/${TOURNAMENT_ID}/c
git branch -D rick/t/${TOURNAMENT_ID}/final

# Limpieza masiva (todas las ramas de torneo)
git branch -r | grep "rick/t/" | sed 's|origin/||' | xargs -I{} git push origin --delete {}
git branch | grep "rick/t/" | xargs git branch -D
```

### Qué revisar si algo falla

1. **`ok: false`** → leer `error`. Los mensajes son específicos.
2. **Preflight failed** → `preflight` en el output dice exactamente qué.
3. **Contestant sin código** → `code_change` es `null` si `generate_code=false`, o tiene `commit.ok: false` si el LLM no generó un FILE block válido.
4. **Validación failed** → `validation.log_tail` tiene las últimas 20 líneas / 2000 chars del output.
5. **Cherry-pick failed** → `final_result.error` explica la causa (commit vacío, conflicto, etc.).

---

## 7. Troubleshooting

### Docker sandbox / pytest_target

```bash
# Verificar que Docker funciona
docker info >/dev/null 2>&1 && echo "OK" || echo "Docker no disponible"

# Verificar imagen sandbox
bash worker/sandbox/refresh.sh --print
# Muestra el tag esperado (sha256 de pyproject.toml). Si no existe:
bash worker/sandbox/refresh.sh
# Construye la imagen. Con --force reconstruye aunque exista.

# Inspeccionar imagen
docker image inspect umbral-sandbox-pytest:$(bash worker/sandbox/refresh.sh --print) >/dev/null 2>&1 && echo "OK"
```

Si `pytest_target` falla con rc=125: el container no logró iniciar. Posibles causas:
- Imagen no existe → `refresh.sh`
- Permisos de Docker → verificar que el usuario puede ejecutar `docker run`
- tmpfs bajo bind mount read-only → ya resuelto en PR #215

### Test allowlist (pytest_target)

Solo tests listados en `worker/sandbox/test_allowlist.txt` pueden usarse como `validation_target`. Archivos actuales:

- `tests/test_tournament_handler.py`
- `tests/test_github_tournament.py`
- `tests/test_github.py`
- `tests/test_alert_manager.py`
- `tests/test_env_loader.py`

Para agregar un test: verificar que pasa end-to-end en main, que no requiere network, y que cabe en el timeout.

### Worktree sucio

```bash
git status --porcelain --untracked-files=no
```

Si hay cambios staged/modified, el preflight rechaza la operación. Untracked files se toleran (están en `.gitignore` o son `docs/audits/`).

Resolución: commit o stash los cambios antes de lanzar el torneo.

### Preflight fallido

El preflight verifica: SSH, token, repo, rama, worktree limpio, remote accesible. Leer el campo `error` del output. Causas comunes:

- `GITHUB_TOKEN` no definido o expirado (expira 2027-03-03)
- SSH deploy key revocada
- Remote no accesible (GitHub caido, DNS)
- Worktree con cambios uncommitted

```bash
# Diagnóstico rápido
ssh -T git@github.com
source ~/.config/openclaw/env && GH_TOKEN=$GITHUB_TOKEN gh auth status
git status --porcelain --untracked-files=no
git fetch origin
```

### CI roja preexistente

Todos los PRs muestran FAILURE por `ModuleNotFoundError: No module named 'copilot'` en `tests/test_copilot_agent.py`. No está relacionado con torneos ni con ningún PR reciente. CI no es gate para merge actualmente.

### Divergencia local del clone VPS (ahead 45+)

El clone en la VPS tiene ~45+ commits locales ahead de origin/main por reconciliación histórica. Esto es conocido y no es un problema:

- `git pull --ff-only` falla → usar `git merge origin/main --no-edit` en su lugar
- Nunca force-push desde la VPS
- Para PRs, crear ramas limpias desde `origin/main` y cherry-pick

---

## 8. Extensión futura

| Qué ampliar | Dónde tocar |
|-------------|-------------|
| Agregar test al allowlist de pytest | `worker/sandbox/test_allowlist.txt` — verificar que pasa en main primero |
| Nuevo modo de validación | `_VALIDATION_MODES` en `github_tournament.py` (~L932), agregar handler `_run_<mode>_validation()`, extender `_run_contestant_validation()` |
| Cambiar política de eligibilidad | `_apply_eligibility_policy()` en `github_tournament.py` — actualmente: winner debe estar en el pool de passed, o ESCALATE |
| Actualizar skill de Rick | `openclaw/workspace-templates/skills/github-ops/SKILL.md` — sección "Orquestar torneo sobre ramas" |
| Integración Copilot para torneos | No disponible actualmente. Política en `docs/34-rick-github-token-setup.md` § 8 |
| Más extensiones de target_file | `_validate_target_file()` en `github_tournament.py` — allowlist de extensiones (~L394) |
| Aumentar max contestants | `_LABEL_LETTERS` (~L161) tiene 5 labels (a-e); para más, extender la cadena |
| Timeout más largo | `_VALIDATION_MAX_TIMEOUT_S` (~L955) es el hard cap (60s); cambiar requiere evaluar impacto en worker |

---

## Referencias

- Handler principal: `worker/tasks/github_tournament.py`
- Handlers github base: `worker/tasks/github.py`
- Sandbox: `worker/sandbox/` (Dockerfile, refresh.sh, workspace.py, test_allowlist.txt)
- Skill github-ops: `openclaw/workspace-templates/skills/github-ops/SKILL.md`
- Skill tournament (LLM puro): `openclaw/workspace-templates/skills/tournament/SKILL.md`
- Política GitHub/Copilot: `docs/34-rick-github-token-setup.md`
- Runbook operativo general: `docs/62-operational-runbook.md` (§ 7.0.1)
- Workflow de PRs: `docs/28-rick-github-workflow.md`
