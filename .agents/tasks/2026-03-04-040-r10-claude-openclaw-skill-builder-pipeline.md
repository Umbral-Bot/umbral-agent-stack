---
id: "040"
title: "Automated Skill Builder Pipeline from Documentation"
assigned_to: code-claude
branch: feat/claude-skill-builder-pipeline
round: 10
status: assigned
created: 2026-03-04
---

## Objetivo

Crear un script/pipeline automatizado que tome documentación de una API o herramienta y genere un SKILL.md válido para el workspace de OpenClaw. Esto permite que cualquier agente (Codex, Antigravity, Copilot, Cursor) pueda crear skills de forma estandarizada.

## Contexto

- Ya existen 10 skills en `openclaw/workspace-templates/skills/`
- `scripts/validate_skills.py` valida frontmatter YAML (tarea 038)
- El formato está bien definido en `openclaw/workspace-templates/skills/figma/SKILL.md`
- David tiene una carpeta `G:\Mi unidad\AI\IA Personalizadas\` con múltiples custom instructions de LLMs que ya creó manualmente. El pipeline debería poder convertir esas instrucciones en skills de OpenClaw.

## Requisitos

### 1. Script `scripts/build_skill.py`

Pipeline que genera un SKILL.md a partir de inputs:

```bash
# Desde un archivo de instrucciones existente
python scripts/build_skill.py \
  --name "consultor-bim" \
  --source "G:\Mi unidad\AI\IA Personalizadas\Consultor" \
  --output "openclaw/workspace-templates/skills/consultor-bim/SKILL.md"

# Desde una URL de documentación
python scripts/build_skill.py \
  --name "speckle" \
  --url "https://speckle.guide/dev/" \
  --output "openclaw/workspace-templates/skills/speckle/SKILL.md"

# Desde un archivo Markdown suelto
python scripts/build_skill.py \
  --name "dynamo-scripting" \
  --source "G:\Mi unidad\AI\IA Personalizadas\Scraping Dynamo\instrucciones.md" \
  --output "openclaw/workspace-templates/skills/dynamo-scripting/SKILL.md"
```

El script debe:

1. **Leer el input** — directorio (concatena todos los .md/.txt), archivo, o URL
2. **Extraer metadata** — nombre, descripción, triggers, herramientas requeridas
3. **Generar frontmatter YAML** — con `name`, `description`, `metadata.openclaw.emoji`, `metadata.openclaw.requires.env`
4. **Generar body Markdown** — secciones: objetivo, procedimientos, ejemplos, referencias
5. **Validar** — ejecutar `validate_skills.py` sobre el resultado
6. **Escribir** — crear directorio + SKILL.md

Si la fuente es un directorio con varios .md, debe:
- Leer `00_Indice*.md` o `01_Instrucciones*.md` primero para entender la estructura
- Concatenar el resto en orden numérico
- Resumir/comprimir si el contenido total excede 4000 palabras (los skills deben ser concisos)

### 2. Template engine

En `scripts/templates/skill_template.md`:

```markdown
---
name: {{name}}
description: >-
  {{description}}
metadata:
  openclaw:
    emoji: "{{emoji}}"
    requires:
      env:
{{env_vars}}
---

# {{title}}

{{body}}

## Procedimientos

{{procedures}}

## Referencias

{{references}}
```

### 3. Tests `tests/test_skill_builder.py`

- Test genera SKILL.md desde directorio con varios .md
- Test genera SKILL.md desde archivo único
- Test resultado pasa `validate_skills.py`
- Test con directorio vacío → error claro
- Test con --url (mock de requests.get)
- Test que el output no excede 5000 palabras

### 4. Integración con LLM (opcional pero recomendado)

Si `GOOGLE_API_KEY` está configurado, usar `llm.generate` (gemini_flash) para:
- Generar una descripción concisa a partir del contenido fuente
- Seleccionar emoji apropiado
- Extraer triggers relevantes
- Comprimir contenido largo en procedimientos concisos

Si no hay API key, usar heurísticas simples (primeras líneas como descripción, etc.)

## Instrucciones

```bash
git pull origin main
git checkout -b feat/claude-skill-builder-pipeline

# ... implementar ...

python -m pytest tests/test_skill_builder.py -v -p no:cacheprovider

# Test con datos reales (opcional):
python scripts/build_skill.py --name test-consultor \
  --source "G:\Mi unidad\AI\IA Personalizadas\Consultor" \
  --output /tmp/test-skill/SKILL.md
python scripts/validate_skills.py /tmp/test-skill/SKILL.md

git add .
git commit -m "feat: automated skill builder pipeline from documentation"
git push -u origin feat/claude-skill-builder-pipeline
gh pr create --title "feat: skill builder pipeline — generate SKILL.md from docs" \
  --body "scripts/build_skill.py + template + tests. Converts existing documentation into OpenClaw skills."
```

## Criterio de éxito

- `python scripts/build_skill.py --name X --source DIR --output Y` genera SKILL.md válido
- El output pasa `python scripts/validate_skills.py`
- Al menos 5 tests pasan
- No se rompen tests existentes
