---
id: "046"
title: "Skills Librerías Open Source — moviepy, diagrams, Pillow, manim, playwright, ffmpeg-python, svgwrite"
assigned_to: cursor-agent-cloud-5
branch: feat/cloud5-skills-opensource
round: 11
status: done
created: 2026-03-04
---

## Objetivo

Descubrir y documentar librerías Python open source que David no conoce pero que le serían muy útiles en su trabajo como consultor BIM/IA. Rick podrá asistir con estas herramientas cuando las necesite.

## Librerías a cubrir

| Skill | URL docs oficiales | Descripción |
|---|---|---|
| `moviepy` | https://moviepy-tburrows13.readthedocs.io/ + https://zulko.github.io/moviepy/ | Edición de video con Python: cortar, unir, agregar texto, música, efectos. Como Premiere Pro pero en código. |
| `diagrams-python` | https://diagrams.mingrammer.com/ | Diagramas de arquitectura como código (cloud, sistemas, BIM workflows). Genera PNG/SVG desde Python. |
| `pillow-imaging` | https://pillow.readthedocs.io/ + https://imageio.readthedocs.io/ | Manipulación de imágenes: resize, crop, filtros, generación, compositing, batch processing. |
| `manim` | https://docs.manim.community/ | Animaciones matemáticas y técnicas con Python (como los videos de 3Blue1Brown). Útil para presentaciones técnicas. |
| `playwright-python` | https://playwright.dev/python/ | Automatización de browsers: web scraping avanzado, testing, capturas, interacción con páginas web. |
| `ffmpeg-python` | https://kkroening.github.io/ffmpeg-python/ + https://ffmpeg.org/documentation.html | Procesamiento de video/audio: conversión de formatos, extracción de frames, subtítulos, compresión. |
| `svgwrite` | https://svgwrite.readthedocs.io/ + https://cairosvg.org/ | Generar SVG programáticamente: diagramas técnicos, planos esquemáticos, infografías vectoriales. |

## Contexto

David es Arquitecto y Consultor BIM con experiencia en modelado paramétrico y automatización. Estas librerías le serían útiles para:
- **moviepy/ffmpeg**: Crear videos de presentaciones de proyectos, tutoriales de cursos
- **diagrams**: Documentar flujos BIM, arquitecturas de sistemas, workflows de proyectos
- **pillow**: Procesar imágenes de renders, planos, presentaciones en batch
- **manim**: Crear animaciones técnicas para sus clases en Butic/TEDIvirtual
- **playwright**: Automatizar scraping de datos de proyectos, precios, normativas
- **svgwrite**: Generar diagramas técnicos vectoriales desde datos BIM

## Instrucciones

```bash
git pull origin main
git checkout -b feat/cloud5-skills-opensource
```

Para cada librería:
1. Buscar docs oficiales y README en GitHub
2. Enfocar en: instalación, uso básico, casos de uso prácticos para sector AEC/consultoría
3. Incluir snippets de código Python en el skill (son librerías, el código ES el procedimiento)
4. Para cada skill, proponer 2-3 casos de uso específicos para David (consultoría BIM, docencia, marketing)

### Ejemplo de snippet en skill

```markdown
## Casos de uso

### 1. Crear video resumen de proyecto
```python
from moviepy.editor import *
clips = [ImageClip(f, duration=3) for f in sorted(glob("renders/*.png"))]
video = concatenate_videoclips(clips, method="compose")
video.write_videofile("resumen_proyecto.mp4", fps=24)
```
```

### Validar

```bash
python scripts/validate_skills.py
```

### Commit y PR

```bash
git add openclaw/workspace-templates/skills/
git commit -m "feat: skills open source libs — moviepy, diagrams, pillow, manim, playwright, ffmpeg, svgwrite"
git push -u origin feat/cloud5-skills-opensource
gh pr create --title "feat: skills librerías open source — video, diagramas, imágenes, animaciones, scraping" \
  --body "7 SKILL.md de librerías Python open source útiles para consultoría BIM/IA"
```

## Criterio de éxito

- 7 SKILL.md creados con frontmatter YAML válido
- `python scripts/validate_skills.py` → exit 0
- Cada skill incluye al menos 2 snippets de código Python
- Casos de uso orientados al perfil de David (BIM, docencia, consultoría)
- Librerías son las versiones actuales (2025/2026)

## Log

- 2026-03-04: cursor-agent-cloud-5 crea rama `feat/cloud5-skills-opensource`
- 2026-03-04: Buscadas docs oficiales de las 7 librerías (moviepy 2.x, diagrams 0.24.4, Pillow, manim Community, playwright-python, ffmpeg-python, svgwrite 1.4.3)
- 2026-03-04: Creados 7 SKILL.md en `openclaw/workspace-templates/skills/`
- 2026-03-04: `python scripts/validate_skills.py` → exit 0 (20/20 OK)
- 2026-03-04: PR creado en rama `feat/cloud5-skills-opensource`
