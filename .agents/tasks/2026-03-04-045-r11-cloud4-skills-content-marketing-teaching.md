---
id: "045"
title: "Skills Contenido, Docencia y Marketing — LinkedIn, Marca Personal, Marketing Digital, Notion"
assigned_to: cursor-agent-cloud-4
branch: feat/cloud4-skills-content
round: 11
status: assigned
created: 2026-03-04
---

## Objetivo

Crear skills de habilidades blandas, marketing y herramientas de productividad para que Rick pueda asistir a David en comunicación profesional, docencia y marketing digital.

## Skills a crear

### 1. `linkedin-content`

**Fuente principal (local):** `G:\Mi unidad\AI\IA Personalizadas\Linkedin 2\` (11 archivos .md sobre algoritmo LinkedIn 2025, estrategias, hooks, engagement, formatos, templates, checklist)

**Fuente secundaria (web):** https://www.linkedin.com/help/linkedin/ + blogs de LinkedIn sobre algoritmo 2025

Skill debe cubrir:
- Algoritmo de LinkedIn 2025 (qué prioriza, qué penaliza)
- Estrategias de contenido para consultores BIM/AEC
- Formatos que mejor funcionan (carrusel, texto, video, newsletter)
- Hooks de apertura de alto engagement
- Checklist pre-publicación
- Anti-patrones (lo que NO hacer)
- Triggers: "publicar en linkedin", "post linkedin", "contenido linkedin", "newsletter linkedin"

### 2. `marca-personal`

**Fuente principal (local):** `G:\Mi unidad\AI\IA Personalizadas\Marca Personal\` (5 archivos)

**Fuente secundaria:** https://www.hubspot.com/personal-branding + blogs de marca personal AEC

Skill debe cubrir:
- Narrativa y propuesta de valor única (David: Arquitecto + BIM + IA + Citizen Developer)
- Posicionamiento estratégico en sector AECO
- Bio profesional en distintos formatos (Twitter/X, LinkedIn, web, presentaciones)
- Estrategia de contenidos para marca personal
- Triggers: "marca personal", "bio profesional", "propuesta de valor", "posicionamiento"

### 3. `marketing-digital`

**Fuente:** https://blog.hubspot.com/ + https://neilpatel.com/blog/ + https://moz.com/learn/seo

Skill debe cubrir:
- SEO básico (on-page, keywords, meta descriptions)
- Email marketing (asuntos, CTAs, secuencias)
- Funnel de ventas para consultores
- Métricas clave (CTR, CAC, LTV, ROI)
- Herramientas gratuitas recomendadas
- Triggers: "marketing digital", "seo", "email marketing", "funnel", "captación clientes"

### 4. `notion-workflow`

**Fuente:** https://developers.notion.com/ + https://www.notion.so/help/

Skill debe cubrir:
- API de Notion (bases de datos, páginas, bloques)
- Automatizaciones nativas de Notion
- Templates útiles para consultores
- Integración con Make/n8n via webhook
- Comandos frecuentes de la API
- Triggers: "notion database", "crear página notion", "automatizar notion", "notion API"
- Env vars: `NOTION_API_KEY`

## Instrucciones

```bash
git pull origin main
git checkout -b feat/cloud4-skills-content
```

Para los skills locales (linkedin-content, marca-personal):
1. Leer archivos en `G:\Mi unidad\AI\IA Personalizadas\Linkedin 2\` y `Marca Personal\`
2. Condensar el contenido a <3000 palabras por skill
3. Complementar con búsqueda web si algo está desactualizado

Para los skills web (marketing-digital, notion-workflow):
1. Buscar en las URLs indicadas
2. Enfocarse en lo más accionable y práctico

### Validar

```bash
python scripts/validate_skills.py
```

### Commit y PR

```bash
git add openclaw/workspace-templates/skills/
git commit -m "feat: skills content marketing teaching — linkedin, marca-personal, marketing-digital, notion"
git push -u origin feat/cloud4-skills-content
gh pr create --title "feat: skills contenido/marketing — linkedin, marca personal, marketing digital, notion" \
  --body "4 SKILL.md: 2 desde archivos locales Google Drive + 2 desde documentación oficial web"
```

## Criterio de éxito

- 4 SKILL.md creados con frontmatter YAML válido
- `python scripts/validate_skills.py` → exit 0
- Skills linkedin y marca-personal usan el material propio de David como base
- Triggers en español
