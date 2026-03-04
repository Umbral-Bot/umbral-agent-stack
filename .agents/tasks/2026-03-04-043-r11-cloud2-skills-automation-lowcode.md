---
id: "043"
title: "Skills Automatización Low-Code — Power Automate, Power Apps, Power BI, n8n, Make, Copilot Studio"
assigned_to: cursor-agent-cloud-2
branch: feat/cloud2-skills-automation
round: 11
status: assigned
created: 2026-03-04
---

## Objetivo

Buscar documentación oficial de cada herramienta de automatización y generar SKILL.md para que Rick pueda asistir en flujos, dashboards y bots.

## Herramientas a cubrir

| Skill | URL docs oficiales | Alcance |
|---|---|---|
| `power-automate` | https://learn.microsoft.com/power-automate/ | Flujos cloud, PAD (desktop), conectores, expresiones |
| `power-apps` | https://learn.microsoft.com/power-apps/ | Canvas apps, model-driven, fórmulas, conectores |
| `power-bi` | https://learn.microsoft.com/power-bi/ | DAX, Power Query (M), visualizaciones, datasets, API |
| `n8n` | https://docs.n8n.io/ | Workflows, nodos, credenciales, expresiones, self-hosted |
| `make-com` | https://www.make.com/en/help/ + https://developers.make.com/ | Escenarios, módulos, webhooks, routers, funciones |
| `copilot-studio` | https://learn.microsoft.com/microsoft-copilot-studio/ | Agentes conversacionales, topics, actions, API |

## Instrucciones

```bash
git pull origin main
git checkout -b feat/cloud2-skills-automation
```

Para cada skill:
1. Buscar documentación oficial en la URL indicada
2. Enfocar en: casos de uso comunes, expresiones/fórmulas clave, conectores disponibles, errores frecuentes
3. Crear en `openclaw/workspace-templates/skills/<nombre>/SKILL.md`
4. Frontmatter requerido:
   - `name`: slug en minúsculas con guiones
   - `description`: qué hace + triggers de activación ("use when...")
   - `metadata.openclaw.emoji`: emoji representativo
   - `metadata.openclaw.requires.env`: lista de env vars necesarias (puede ser vacía `[]`)

### Nota para Power BI y Power Automate

El usuario ya tiene documentación propia en `G:\Mi unidad\AI\IA Personalizadas\LLM-Mentor-Speckle-Dalux-PowerBI\04_dominio_power_bi.md`. Si podés leer ese archivo, combinar con la doc oficial para un skill más personalizado.

### Validar

```bash
python scripts/validate_skills.py
```

### Commit y PR

```bash
git add openclaw/workspace-templates/skills/
git commit -m "feat: skills automation lowcode — power-automate, power-apps, power-bi, n8n, make, copilot-studio"
git push -u origin feat/cloud2-skills-automation
gh pr create --title "feat: skills automatización — power platform, n8n, make, copilot studio" \
  --body "6 SKILL.md from official docs for automation and low-code tools"
```

## Criterio de éxito

- 6 SKILL.md creados con frontmatter YAML válido
- `python scripts/validate_skills.py` → exit 0
- Skills incluyen expresiones/fórmulas clave de cada plataforma
- Triggers claros en español e inglés
