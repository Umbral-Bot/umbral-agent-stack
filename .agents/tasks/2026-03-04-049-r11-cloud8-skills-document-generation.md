---
id: "049"
title: "Skills Generación de Documentos — Word, PDF, PowerPoint, Excel con Python"
assigned_to: cursor-agent-cloud-8
branch: feat/cloud8-skills-document-generation
round: 11
status: done
created: 2026-03-04
---

## Objetivo

Investigar las mejores librerías Python open source para generar documentos profesionales (Word, PDF, PPT, Excel) y crear SKILL.md + handlers en el Worker para que Rick pueda generar documentos automáticamente.

## Librerías a investigar y documentar

| Librería | Formato | URL docs | Uso ideal |
|----------|---------|----------|-----------|
| `python-docx` | Word (.docx) | https://python-docx.readthedocs.io/ | Propuestas, informes, contratos con templates |
| `docxtpl` | Word (.docx) con Jinja2 | https://docxtpl.readthedocs.io/ | Templates Word con variables dinámicas |
| `fpdf2` | PDF | https://py-pdf.github.io/fpdf2/ | PDFs desde cero, portable, sin dependencias |
| `weasyprint` | PDF desde HTML/CSS | https://doc.courtbouillon.org/weasyprint/ | PDFs con diseño rico (CSS), ideal para cotizaciones |
| `reportlab` | PDF | https://docs.reportlab.com/ | PDFs complejos, tablas, gráficos, código de barras |
| `python-pptx` | PowerPoint (.pptx) | https://python-pptx.readthedocs.io/ | Presentaciones automáticas desde datos |
| `openpyxl` | Excel (.xlsx) | https://openpyxl.readthedocs.io/ | Reportes Excel, gráficos, tablas dinámicas |
| `pandoc` (pypandoc) | Markdown → cualquier formato | https://pypandoc.readthedocs.io/ | Convertir Markdown a Word/PDF/HTML/EPUB |

## Parte 1: Skill OpenClaw

Crear `openclaw/workspace-templates/skills/document-generation/SKILL.md`

El skill debe:
- Explicar qué librería usar según el formato y caso de uso
- Incluir snippets de código Python para casos comunes
- Triggers: "crear word", "generar pdf", "crear propuesta", "generar informe", "hacer presentación", "exportar excel"

### Tabla de decisión para el skill

```
¿Qué necesitás?
├── Word → python-docx (sin template) o docxtpl (con template .docx)
├── PDF simple → fpdf2 (sin CSS) o weasyprint (con HTML/CSS)
├── PDF complejo con tablas y gráficos → reportlab
├── PowerPoint → python-pptx
├── Excel → openpyxl
└── Markdown → cualquier cosa → pandoc/pypandoc
```

## Parte 2: Handler en el Worker

Crear `worker/tasks/document_generator.py` con:

### `document.create_word`

```python
# Input: {"template_path": "...", "output_path": "...", "data": {...}}
# O sin template: {"content": "...", "title": "...", "output_path": "..."}
# Output: {"ok": true, "path": "...", "size_bytes": ...}
```

Usar `docxtpl` si se pasa `template_path`, sino `python-docx` para crear desde cero.

### `document.create_pdf`

```python
# Input: {"html_content": "...", "output_path": "..."}  ← weasyprint
# O:     {"markdown_content": "...", "output_path": "..."}  ← pandoc → pdf
# Output: {"ok": true, "path": "...", "size_bytes": ...}
```

### `document.create_presentation`

```python
# Input: {"slides": [{"title": "...", "content": "...", "notes": "..."}], "output_path": "..."}
# Output: {"ok": true, "path": "...", "slide_count": ...}
```

### Registrar en `worker/tasks/__init__.py`:
```python
"document.create_word": handle_document_create_word,
"document.create_pdf": handle_document_create_pdf,
"document.create_presentation": handle_document_create_presentation,
```

## Parte 3: Templates de documentos de David

Crear templates base en `worker/templates/documents/`:

### `propuesta_bim.docx` (template Word)

Template para propuestas de consultoría BIM de David con:
- Portada: nombre proyecto, cliente, fecha, logo placeholder
- Secciones: Contexto, Alcance, Metodología, Entregables, Inversión, Cronograma, Condiciones
- Pie de página: datos de contacto de David

### `cotizacion_bim.docx` (template Word)

Template para cotizaciones con tabla de servicios, plazos y valores.

## Parte 4: Tests

Crear `tests/test_document_generator.py`:
- Test `document.create_word` genera archivo .docx
- Test `document.create_pdf` genera archivo .pdf
- Test `document.create_presentation` genera .pptx
- Test sin output_path → devuelve bytes en base64
- Test con template → sustituye variables correctamente

## Dependencias a agregar

En `worker/requirements.txt`:
```
python-docx>=1.1.0
docxtpl>=0.16.0
fpdf2>=2.7.0
weasyprint>=61.0
python-pptx>=0.6.23
openpyxl>=3.1.0
pypandoc>=1.13.0
```

## Instrucciones

```bash
git pull origin main
git checkout -b feat/cloud8-skills-document-generation

# Leer docs de cada librería
# Crear skill
# Crear handlers
# Crear templates base

python -m pytest tests/test_document_generator.py -v -p no:cacheprovider

git add .
git commit -m "feat: document generation — word, pdf, pptx handlers + skill + templates"
git push -u origin feat/cloud8-skills-document-generation
gh pr create \
  --title "feat: document generation — Word, PDF, PowerPoint con Python" \
  --body "handlers document.create_word/pdf/presentation + skill + templates propuesta/cotizacion BIM"
```

## Criterio de éxito

- `skills/document-generation/SKILL.md` válido con tabla de decisión + snippets
- 3 handlers funcionando: create_word, create_pdf, create_presentation
- Templates .docx de propuesta y cotización BIM
- Tests pasan
- Dependencias documentadas en requirements.txt

## Log

### [cursor-agent-cloud-8] 2026-03-04

**Archivos creados/modificados:**

- `openclaw/workspace-templates/skills/document-generation/SKILL.md` — Skill con tabla de decisión, snippets, documentación de 8 librerías
- `worker/tasks/document_generator.py` — 3 handlers: `document.create_word`, `document.create_pdf`, `document.create_presentation`
- `worker/tasks/__init__.py` — Registrados 3 handlers nuevos (total: 31)
- `worker/templates/documents/propuesta_bim.docx` — Template Word para propuestas BIM con Jinja2
- `worker/templates/documents/cotizacion_bim.docx` — Template Word para cotizaciones BIM con Jinja2
- `worker/requirements.txt` — Agregadas dependencias: python-docx, docxtpl, fpdf2, weasyprint, python-pptx, openpyxl
- `tests/test_document_generator.py` — 21 tests (20 passed, 1 skipped: weasyprint requiere libs de sistema)
- `scripts/create_docx_templates.py` — Script generador de templates .docx

**Tests:** 20 passed, 1 skipped (weasyprint HTML→PDF necesita Cairo/Pango instalados). Skill validation test también pasa.
