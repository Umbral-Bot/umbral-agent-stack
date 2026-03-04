---
id: "038"
title: "Skills Validation + E2E Tests for New Tools"
assigned_to: code-claude
branch: feat/claude-skills-validation
round: 9
status: assigned
created: 2026-03-04
---

## Objetivo

1. Crear un validador que verifica que todos los SKILL.md tengan frontmatter YAML correcto.
2. Crear tests E2E para los nuevos handlers (figma, openclaw_proxy).
3. Verificar integridad entre TASK_HANDLERS y los skills del workspace.

## Contexto

- `openclaw/workspace-templates/skills/` — directorio de skills (figma ya existe, otros en progreso)
- `worker/tasks/__init__.py` — TASK_HANDLERS con todas las tasks
- `worker/tasks/figma.py` — 5 handlers nuevos sin tests E2E
- `worker/tasks/llm.py` — `_call_openclaw_proxy` recién agregado
- `scripts/e2e_validation.py` — suite E2E existente (agregar tests ahí)

## Requisitos

### 1. Script `scripts/validate_skills.py`

Validador de SKILL.md:

- Buscar recursivamente `openclaw/workspace-templates/skills/*/SKILL.md`
- Para cada skill, verificar:
  - Frontmatter YAML parseable (separado por `---`)
  - Campos requeridos presentes: `name`, `description`
  - `metadata.openclaw.emoji` presente
  - `metadata.openclaw.requires.env` es lista de strings
  - Nombre del directorio coincide con `name` del frontmatter
- Reporte: lista de skills OK y skills con errores
- Exit code 0 si todos pasan, 1 si hay errores

### 2. Tests `tests/test_skills_validation.py`

- Test que todos los SKILL.md existentes en el repo son válidos
- Test frontmatter con campo faltante → error detectado
- Test frontmatter con YAML inválido → error detectado
- Test consistencia nombre directorio vs frontmatter name

### 3. Tests `tests/test_figma_e2e.py` (o agregar a `scripts/e2e_validation.py`)

Tests E2E para Figma (requieren `FIGMA_API_KEY` real, se skip si no está):

- `figma.get_file` con file_key conocido → retorna ok + pages
- `figma.export_image` → retorna URLs de imagen
- `figma.list_comments` → retorna ok + count

Usar `@pytest.mark.skipif(not os.environ.get("FIGMA_API_KEY"), reason="FIGMA_API_KEY not set")`

### 4. Test de cobertura de skills

`tests/test_skills_coverage.py`:

- Leer todas las tasks de TASK_HANDLERS
- Leer todos los SKILL.md y extraer las tasks que mencionan
- Reportar tasks que NO tienen skill (coverage gap)
- Este test es informativo (warning), no falla

## Instrucciones

```bash
git pull origin main
git checkout -b feat/claude-skills-validation

# ... hacer cambios ...

python scripts/validate_skills.py
python -m pytest tests/test_skills_validation.py tests/test_skills_coverage.py -v -p no:cacheprovider

git add .
git commit -m "feat: skills validator + figma E2E + coverage report"
git push -u origin feat/claude-skills-validation
gh pr create --title "feat: skills validation, figma E2E, coverage report" --body "validate_skills.py + tests for SKILL.md integrity and task coverage"
```

## Criterio de éxito

- `python scripts/validate_skills.py` → exit 0 para skills existentes
- Tests de validación pasan
- Skills con frontmatter inválido son detectados
- Coverage report lista tasks sin skill
- No se rompen tests existentes
