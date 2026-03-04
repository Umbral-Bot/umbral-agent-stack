---
id: "042"
title: "Skills BIM/AEC Apps — Revit, Dynamo, Rhino, Grasshopper, Navisworks, ACC, KukaPRC, Robots"
assigned_to: cursor-agent-cloud-1
branch: feat/cloud1-skills-bim-aec
round: 11
status: done
created: 2026-03-04
completed: 2026-03-04
pr: "https://github.com/Umbral-Bot/umbral-agent-stack/pull/52"
---

## Log

- 2026-03-04: 6 SKILL.md creados con documentación oficial
- `python scripts/validate_skills.py` → 19 skills OK (exit 0)
- PR #52: https://github.com/Umbral-Bot/umbral-agent-stack/pull/52

## Objetivo

Buscar documentación oficial de cada herramienta listada y generar un SKILL.md optimizado para el workspace de OpenClaw de Rick. Cada skill debe permitir a Rick asistir con esa herramienta específica.

## Herramientas a cubrir

| Skill | URL docs oficiales | Alcance |
|---|---|---|
| `revit` | https://aps.autodesk.com/developer/overview/revit + https://www.revitapidocs.com/ | API Python/Dynamo, automatización, scripting en Revit |
| `dynamo` | https://dynamobim.org/learn/ + https://primer2.dynamobim.org/ | Programación visual, nodos, Python en Dynamo, best practices |
| `rhinoceros-grasshopper` | https://developer.rhino3d.com/ + https://www.grasshopper3d.com/ | Scripting RhinoCommon, componentes GH, Python en Rhino |
| `navisworks` | https://aps.autodesk.com/developer/overview/navisworks | Clash detection, reportes, API, NWC/NWD |
| `acc-bim360` | https://aps.autodesk.com/developer/overview/bim-360 | Autodesk Construction Cloud API, issues, RFIs, submittals |
| `kuka-robots-grasshopper` | https://www.food4rhino.com/en/app/kukaprc + https://www.grasshopper3d.com/group/robots | KukaPRC plugin, Robots plugin, fabricación digital, toolpath |

## Instrucciones

```bash
git pull origin main
git checkout -b feat/cloud1-skills-bim-aec
```

Para cada skill:
1. Buscar documentación oficial en la URL indicada
2. Leer secciones clave: getting started, API reference, examples, best practices
3. Usar `scripts/build_skill.py` como referencia de estructura o crear manualmente
4. Crear en `openclaw/workspace-templates/skills/<nombre>/SKILL.md`
5. Cada SKILL.md debe tener:
   - Frontmatter YAML válido (name, description, metadata.openclaw.emoji, metadata.openclaw.requires.env)
   - Sección de comandos/procedimientos accionables
   - Ejemplos de uso con Rick
   - Links a docs oficiales

### Formato de referencia

Ver `openclaw/workspace-templates/skills/figma/SKILL.md` como ejemplo.

### Validar

```bash
python scripts/validate_skills.py
```

Todos los nuevos skills deben pasar sin errores.

### Commit y PR

```bash
git add openclaw/workspace-templates/skills/
git commit -m "feat: skills for BIM/AEC tools — revit, dynamo, rhino, navisworks, acc, kuka"
git push -u origin feat/cloud1-skills-bim-aec
gh pr create --title "feat: skills BIM/AEC — revit, dynamo, rhino, grasshopper, navisworks, acc, kuka" \
  --body "6 SKILL.md from official documentation for BIM/AEC toolchain"
```

## Criterio de éxito

- 6 SKILL.md creados con frontmatter YAML válido
- Triggers relevantes para cada herramienta
- `python scripts/validate_skills.py` → exit 0
- Skills son concisos (<3000 palabras cada uno)
- Contenido extraído de documentación oficial actualizada
