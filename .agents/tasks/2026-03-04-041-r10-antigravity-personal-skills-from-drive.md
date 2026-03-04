---
id: "041"
title: "Personal Skills from Google Drive AI Folder"
assigned_to: antigravity
branch: feat/antigravity-personal-skills
round: 10
status: assigned
created: 2026-03-04
---

## Objetivo

Escanear la carpeta `G:\Mi unidad\AI` de David, identificar todo el contenido relevante para crear OpenClaw skills personalizados según su perfil profesional, y generar los skills prioritarios.

## Perfil profesional de David (resumen)

David Moreira es Arquitecto y Coordinador BIM certificado (buildingSMART, Autodesk ACI) con +10 años de experiencia en transformación digital del sector AECO (Arquitectura, Ingeniería, Construcción, Operación). Especialista en:

- **BIM**: Revit, ACC, Dynamo, Navisworks, Grasshopper, ISO 19650
- **Automatización**: Power Automate, Power Apps, Power BI, SharePoint
- **Programación visual**: Dynamo, Grasshopper 3D
- **IA aplicada a construcción**: LLMs personalizados, Citizen Developer
- **Herramientas específicas**: Speckle, Dalux, Rhinoceros 3D, CFD Autodesk
- **Docencia**: Master AEC 4.0 en Butic New School, TEDIvirtual
- **Consultoría**: BIM + IA para transformación digital

## Carpetas encontradas en `G:\Mi unidad\AI\IA Personalizadas\`

Cada carpeta contiene instrucciones de LLM personalizadas (.md) que David ya creó:

| Carpeta | Contenido | Prioridad |
|---------|-----------|-----------|
| `Consultor` | 11 archivos: perfil, catálogo servicios, propuestas, cotizaciones, objeciones | ALTA |
| `BIM Forum` | 13 archivos: ISO 19650 completa, guía redacción, glosario BIM | ALTA |
| `LLM-Mentor-Speckle-Dalux-PowerBI` | 10 archivos: dominios Speckle/Dalux/Power BI, integración | ALTA |
| `Linkedin` + `Linkedin 2` | Algoritmo LinkedIn, estrategias contenido, hooks, templates | MEDIA |
| `PowerFlow Coaching` | Marca personal, documentación, artículos | MEDIA |
| `Docente 1/2/3/4` | Material de cursos | MEDIA |
| `Marca Personal` | Branding | MEDIA |
| `Scraping Dynamo` | Asistente IA para Dynamo scripting | MEDIA |
| `Autodesk` | Documentación Autodesk | BAJA |
| `Grasshopper` | Programación visual | BAJA |
| `Make LLMs 1/2/3` | Guías para crear custom instructions | META |
| `Dalux` | AI Ready docs | BAJA |
| `Power BI` | AI Ready docs | BAJA |
| `Arquitectura y Robots` | Colaboración humano-robot | BAJA |

## Requisitos

### Paso 1: Escaneo y análisis

Crear `scripts/scan_drive_for_skills.py`:

1. Recorre `G:\Mi unidad\AI\IA Personalizadas\` recursivamente
2. Para cada subcarpeta con archivos .md:
   - Lee el contenido
   - Identifica: tema, dominio, cantidad de archivos, palabras totales
   - Clasifica prioridad (ALTA/MEDIA/BAJA) según relevancia al perfil
3. Genera reporte: `reports/drive-skills-scan.md`
   - Lista de carpetas encontradas
   - Skills potenciales identificados
   - Recomendaciones de priorización

### Paso 2: Crear skills prioritarios (ALTA)

Generar 3 skills directamente leyendo las instrucciones existentes:

#### 2a. `openclaw/workspace-templates/skills/consultor-bim/SKILL.md`

Fuente: `G:\Mi unidad\AI\IA Personalizadas\Consultor\` (11 archivos)

Debe incluir:
- Perfil profesional de David (extraído de `03_Perfil_David_Moreira.md`)
- Catálogo de servicios (de `04_Catalogo_Servicios.md`)
- Estructura de propuestas y cotizaciones (de `05_` y `06_`)
- Templates de respuesta a clientes (de `07_Templates_Respuestas.md`)
- Objeciones frecuentes y cómo manejarlas (de `09_`)
- Checklist de verificación (de `10_`)
- Anti-slop rules (de `02_Lista_Negra_Antislop.md`)
- Triggers: "propuesta comercial", "cotización", "cliente consultoría", "responder cliente", "servicios BIM"
- Env: ninguna adicional (es un skill de conocimiento)

#### 2b. `openclaw/workspace-templates/skills/bim-expert/SKILL.md`

Fuente: `G:\Mi unidad\AI\IA Personalizadas\BIM Forum\` (13 archivos)

Debe incluir:
- Glosario BIM completo (de `02_Glosario_BIM.md`)
- ISO 19650 partes 1-6 resumidas (de archivos `03_` a `09_`)
- Guía de redacción profesional BIM (de `10_`)
- Estructura de documentos tipo (de `11_`)
- Perspectiva e iniciativas (de `13_`)
- Triggers: "ISO 19650", "BIM", "estándar BIM", "gestión información", "plan ejecución BIM", "BEP"
- Env: ninguna adicional

IMPORTANTE: Los skills de OpenClaw no deben exceder ~3000 palabras. Resumí/comprimí el contenido de los 13 archivos manteniendo la esencia y las tablas/listas clave. No copies texto íntegro.

#### 2c. `openclaw/workspace-templates/skills/speckle-dalux-powerbi/SKILL.md`

Fuente: `G:\Mi unidad\AI\IA Personalizadas\LLM-Mentor-Speckle-Dalux-PowerBI\` (10 archivos)

Debe incluir:
- Dominio Speckle: API, streams, commits, objetos (de `02_`)
- Dominio Dalux: inspección, QA, campo (de `03_`)
- Dominio Power BI: DAX, visualización, connectors (de `04_`)
- Flujo de integración Speckle → Dalux → Power BI (de `05_`)
- Casos de uso prácticos (de `07_`)
- Triggers: "speckle", "dalux", "power bi", "dashboard BIM", "integración datos BIM"
- Env: ninguna adicional

### Paso 3: Validar

```bash
python scripts/validate_skills.py
```

Verificar que los 3 nuevos skills pasen la validación.

## Instrucciones

```bash
git pull origin main
git checkout -b feat/antigravity-personal-skills

# Paso 1: escanear
python scripts/scan_drive_for_skills.py

# Paso 2: crear los 3 skills leyendo los archivos fuente
# ... crear manualmente o con script ...

# Paso 3: validar
python scripts/validate_skills.py

git add .
git commit -m "feat: personal skills from drive — consultor, bim-expert, speckle-dalux-powerbi"
git push -u origin feat/antigravity-personal-skills
gh pr create --title "feat: personal skills from Google Drive AI folder" \
  --body "3 domain skills from David's custom instructions + drive scanner script"
```

## Criterio de éxito

- `scripts/scan_drive_for_skills.py` genera reporte legible
- 3 SKILL.md creados pasan `validate_skills.py`
- Skills son concisos (<3000 palabras cada uno)
- Contenido es útil para Rick (triggers relevantes, procedimientos accionables)
- No se rompen tests existentes
