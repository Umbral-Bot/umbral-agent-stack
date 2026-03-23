# PR Workflow — Umbral Agent Stack

Flujo completo de trabajo desde issue Linear hasta merge en main.
Convenciones del repo: branch names en kebab-case, commits en Conventional Commits.

## Flujo estándar

### 1. Crear branch desde issue Linear
```bash
# Formato: claude/<issue-id>-<descripcion-corta>
# Ejemplo para UMB-77:
git checkout main && git pull origin main
git checkout -b claude/umb-77-model-routing-config
```

### 2. Implementar y commitear
```bash
# Revisar estado antes de commitear
git status
git diff

# Commitear con formato Conventional Commits
git add <archivos-específicos>
git commit -m "fix(dispatcher): configure claude_* providers in model router

Closes UMB-77

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

### 3. Correr tests antes de push
```bash
python -m pytest tests/ -q --tb=short
# Para el área específica que modificaste:
python -m pytest tests/test_dispatcher.py tests/test_intent_classifier.py -v
```

### 4. Push y PR
```bash
git push -u origin claude/umb-77-model-routing-config

gh pr create --base main \
  --title "fix(dispatcher): configure claude_* providers for model routing" \
  --body "$(cat <<'EOF'
## Summary
- Configures missing claude_pro, claude_opus, claude_haiku providers in Worker
- Closes routing drift identified in UMB-77
- Adds validation tests for provider availability

## Test plan
- [ ] `pytest tests/test_dispatcher.py -v` — passes
- [ ] `pytest tests/test_dispatcher_resilience.py -v` — passes
- [ ] E2E manual: tarea coding → confirm routes to claude_pro

Closes UMB-77

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

## Convenciones de naming

### Branches
- `claude/<issue-id>-<descripcion>` — trabajo de Claude Code
- `feat/<descripcion>` — features
- `fix/<descripcion>` — bugfixes
- `chore/<descripcion>` — maintenance

### Commit types
- `feat` — nueva funcionalidad
- `fix` — bugfix
- `chore` — mantenimiento, config
- `docs` — solo documentación
- `test` — solo tests
- `refactor` — refactoring sin cambio de comportamiento

### Scopes comunes del repo
- `dispatcher` — dispatcher/
- `worker` — worker/
- `client` — client/
- `config` — config/
- `vps` — scripts/vps/
- `vm` — scripts/vm/
- `openclaw` — openclaw/
- `skills` — openclaw/workspace-templates/skills/
- `tests` — tests/
- `settings` — .claude/settings

## Merge strategy
- Siempre merge via PR, nunca direct push a main
- Squash merge para branches con muchos commits de WIP
- Rebase merge para branches limpias

## Post-merge
```bash
git checkout main && git pull origin main
# Limpiar branch local
git branch -d claude/umb-77-model-routing-config
```

## Archivos de referencia
- `AGENTS.md` — Protocolo de coordinación inter-agentes
- `docs/28-rick-github-workflow.md` — Workflow GitHub para Rick
