---
id: "047"
title: "Skills Personales desde Google Drive — Docente AEC4.0, LinkedIn Content, Marca Personal DM"
assigned_to: cursor-agent-cloud-6
branch: feat/cloud6-skills-personal-drive
round: 11
status: done
created: 2026-03-04
---

## Objetivo

Leer las instrucciones de LLM personalizadas que David ya tiene en Google Drive y convertirlas en 3 OpenClaw skills usando el pipeline existente.

## Perfil de David (contexto)

Arquitecto, Coordinador BIM, Consultor en Transformación Digital. Docente del Master AEC 4.0 en Butic New School y TEDIvirtual. Ponente internacional. Especialista en Dynamo, Revit API, Grasshopper, y IA aplicada a construcción.

## Skills a crear desde archivos locales

### 1. `docente-aec40`

**Fuente:** `G:\Mi unidad\AI\IA Personalizadas\Docente 1\` + `Docente 3\` (los más completos)

Archivos clave a leer:
- `Docente 1\00.2_Indice_Master.md` — índice general
- `Docente 1\02_Guia Tecnica.md` — tendencias tecnológicas, IA y orquestación BIM
- `Docente 1\03_Dynamo API BP.md` — buenas prácticas Dynamo y scripting Python
- `Docente 1\04_Revit API BP.md` — uso avanzado API Revit desde Dynamo/Python
- `Docente 1\05_Guia pedagogica.md` — metodologías Citizen Developer
- `Docente 3\12_Conceptos_Clave v2.0.md` — conceptos fundamentales
- `Docente 3\13_Ejemplos_Prompts v2.0.md` — ejemplos de prompts

Skill debe cubrir:
- Cómo preparar material de clase para programación BIM
- Best practices de Dynamo y Python en Revit
- Metodología Citizen Developer
- Diseño instruccional para cursos AEC 4.0
- Triggers: "preparar clase", "material docente", "dynamo scripting", "revit python", "citizen developer"

### 2. `linkedin-david`

**Fuente:** `G:\Mi unidad\AI\IA Personalizadas\Linkedin 2\` (11 archivos)

Archivos a leer (leer todos en orden numérico):
- `01_` a `10_` + checklist

Skill debe cubrir:
- Algoritmo LinkedIn 2025 específico para consultores BIM/AEC
- Formatos de contenido que mejor funcionan para David
- Hooks y aperturas de alto impacto
- Templates de posts para: proyectos BIM, reflexiones IA, docencia, logros
- Anti-patterns y lista negra de frases genéricas
- Triggers: "publicar linkedin", "post linkedin", "contenido semana", "redactar linkedin"

### 3. `marca-personal-david`

**Fuente:** `G:\Mi unidad\AI\IA Personalizadas\Marca Personal\` (5 archivos)

Skill debe cubrir:
- Propuesta de valor única de David: "Arquitecto + BIM + IA + Citizen Developer"
- Narrativa profesional en distintos formatos
- Posicionamiento en sector AECO latinoamericano
- Bio para diferentes contextos (presentaciones, web, LinkedIn, ponencias)
- Triggers: "bio profesional", "presentarme", "propuesta de valor", "marca personal"

## Instrucciones

```bash
git pull origin main
git checkout -b feat/cloud6-skills-personal-drive
```

### Proceso para cada skill

1. Leer todos los archivos `.md` en las carpetas indicadas
2. Identificar la información más accionable y relevante
3. Condensar a máximo 3000 palabras por skill (eliminar redundancias, conservar procedimientos y ejemplos)
4. Crear `openclaw/workspace-templates/skills/<nombre>/SKILL.md`
5. Asegurarse de que el frontmatter tenga:
   - `name`: slug exacto indicado arriba
   - `description`: incluir triggers claros ("Use when...")
   - `metadata.openclaw.emoji`: emoji representativo
   - `metadata.openclaw.requires.env`: `[]` (estos skills son de conocimiento, no requieren API)

### Validar

```bash
python scripts/validate_skills.py
```

Verificar que los 3 nuevos skills pasen sin errores.

### Commit y PR

```bash
git add openclaw/workspace-templates/skills/
git commit -m "feat: personal skills from drive — docente-aec40, linkedin-david, marca-personal-david"
git push -u origin feat/cloud6-skills-personal-drive
gh pr create \
  --title "feat: personal skills from Drive — docente AEC4.0, linkedin, marca personal" \
  --body "3 SKILL.md condensados desde 35+ archivos de instrucciones LLM de David en Google Drive"
```

## Criterio de éxito

- 3 SKILL.md creados con frontmatter YAML válido
- `python scripts/validate_skills.py` → exit 0
- Cada skill < 3000 palabras (conciso pero completo)
- Contenido personalizado al perfil de David (no genérico)
- Triggers en español
