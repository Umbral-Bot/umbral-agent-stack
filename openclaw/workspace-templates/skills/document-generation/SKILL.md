---
name: document-generation
description: >-
  Generate professional documents (Word, PDF, PowerPoint, Excel) from templates
  or from scratch using Python. Use when "crear word", "generar pdf",
  "crear propuesta", "generar informe", "hacer presentación", "exportar excel",
  "generar cotización", "crear documento".
metadata:
  openclaw:
    emoji: "\U0001F4C4"
    requires:
      env: []
      packages:
        - python-docx
        - docxtpl
        - fpdf2
        - python-pptx
---

# Document Generation Skill

Rick puede generar documentos profesionales en múltiples formatos: Word (.docx), PDF, PowerPoint (.pptx) y Excel (.xlsx).

## Tabla de decisión

```
¿Qué necesitás generar?
├── Word (.docx)
│   ├── Con template .docx existente → docxtpl (Jinja2 en Word)
│   └── Desde cero (programático) → python-docx
├── PDF
│   ├── Desde HTML/CSS (diseño rico) → weasyprint
│   ├── Simple sin dependencias de sistema → fpdf2
│   └── Desde Markdown → pypandoc
├── PowerPoint (.pptx) → python-pptx
├── Excel (.xlsx) → openpyxl
└── Markdown → cualquier formato → pypandoc
```

## Librerías

| Librería | Formato | Cuándo usar |
|----------|---------|-------------|
| `python-docx` | Word (.docx) | Crear documentos Word desde cero con headings, párrafos, tablas |
| `docxtpl` | Word (.docx) | Templates Word con variables Jinja2 (`{{ variable }}`) |
| `fpdf2` | PDF | PDFs simples, portable, sin dependencias de sistema |
| `weasyprint` | PDF | PDFs con diseño rico desde HTML/CSS |
| `reportlab` | PDF | PDFs complejos con tablas, gráficos, códigos de barra |
| `python-pptx` | PowerPoint (.pptx) | Presentaciones automáticas desde datos |
| `openpyxl` | Excel (.xlsx) | Reportes Excel, gráficos, tablas dinámicas |
| `pypandoc` | Multi-formato | Convertir Markdown a Word/PDF/HTML/EPUB |

## Tasks disponibles

### 1. Crear documento Word

Task: `document.create_word`

#### Con template (docxtpl)

```json
{
  "template_path": "worker/templates/documents/propuesta_bim.docx",
  "output_path": "/tmp/propuesta_acme.docx",
  "data": {
    "proyecto": "Torre Acme",
    "cliente": "Acme Corp",
    "fecha": "2026-03-04"
  }
}
```

#### Sin template (python-docx)

```json
{
  "title": "Informe de Avance",
  "content": "## Resumen\n\nEl proyecto avanza según lo planeado.\n\n## Siguiente fase\n\n- Modelado 3D\n- Coordinación MEP",
  "output_path": "/tmp/informe_avance.docx"
}
```

#### Parámetros

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `template_path` | str | no | Ruta al template .docx con variables Jinja2 |
| `output_path` | str | no | Ruta de salida. Si se omite, retorna base64 |
| `data` | dict | sí (con template) | Variables para renderizar el template |
| `title` | str | no | Título del documento (sin template) |
| `content` | str | no | Contenido en texto plano o markdown simplificado |

#### Respuesta

```json
{
  "ok": true,
  "path": "/tmp/propuesta_acme.docx",
  "size_bytes": 45230
}
```

### 2. Crear PDF

Task: `document.create_pdf`

#### Desde HTML (weasyprint)

```json
{
  "html_content": "<h1>Cotización</h1><table>...</table>",
  "output_path": "/tmp/cotizacion.pdf"
}
```

#### Desde texto plano (fpdf2)

```json
{
  "text_content": "Informe de diagnóstico BIM\n\nFecha: 2026-03-04\n...",
  "title": "Diagnóstico BIM",
  "output_path": "/tmp/diagnostico.pdf"
}
```

#### Parámetros

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `html_content` | str | no | HTML para convertir a PDF via weasyprint |
| `text_content` | str | no | Texto plano para PDF via fpdf2 |
| `title` | str | no | Título del PDF (usado con text_content) |
| `output_path` | str | no | Ruta de salida. Si se omite, retorna base64 |

#### Respuesta

```json
{
  "ok": true,
  "path": "/tmp/cotizacion.pdf",
  "size_bytes": 128400
}
```

### 3. Crear presentación PowerPoint

Task: `document.create_presentation`

```json
{
  "slides": [
    {"title": "Proyecto Torre Acme", "content": "Consultoría BIM integral", "notes": "Slide de portada"},
    {"title": "Alcance", "content": "- Modelado 3D\n- Coordinación MEP\n- Detección de interferencias"},
    {"title": "Cronograma", "content": "Fase 1: 4 semanas\nFase 2: 6 semanas"}
  ],
  "output_path": "/tmp/presentacion_acme.pptx"
}
```

#### Parámetros

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `slides` | list | sí | Lista de slides con `title`, `content`, `notes` (opcional) |
| `output_path` | str | no | Ruta de salida. Si se omite, retorna base64 |

#### Respuesta

```json
{
  "ok": true,
  "path": "/tmp/presentacion_acme.pptx",
  "slide_count": 3,
  "size_bytes": 35600
}
```

## Templates disponibles

| Template | Ruta | Descripción |
|----------|------|-------------|
| Propuesta BIM | `worker/templates/documents/propuesta_bim.docx` | Propuesta de consultoría BIM con portada, alcance, metodología, inversión |
| Cotización BIM | `worker/templates/documents/cotizacion_bim.docx` | Cotización con tabla de servicios, plazos y valores |

### Variables de propuesta_bim.docx

```
{{ proyecto }}, {{ cliente }}, {{ fecha }}, {{ contexto }},
{{ alcance }}, {{ metodologia }}, {{ entregables }},
{{ inversion }}, {{ cronograma }}, {{ condiciones }}
```

### Variables de cotizacion_bim.docx

```
{{ proyecto }}, {{ cliente }}, {{ fecha }}, {{ referencia }},
{{ servicios }} (lista: nombre, descripcion, plazo, valor),
{{ subtotal }}, {{ iva }}, {{ total }}, {{ vigencia }}, {{ notas }}
```

## Snippets rápidos

### Word desde cero (python-docx)

```python
from docx import Document

doc = Document()
doc.add_heading("Título del Informe", 0)
doc.add_paragraph("Resumen ejecutivo del proyecto.")
doc.add_heading("Alcance", level=1)
doc.add_paragraph("Modelado 3D LOD 300", style="List Bullet")
doc.add_paragraph("Coordinación MEP", style="List Bullet")
table = doc.add_table(rows=1, cols=3)
table.style = "Table Grid"
hdr = table.rows[0].cells
hdr[0].text, hdr[1].text, hdr[2].text = "Fase", "Plazo", "Valor"
doc.save("informe.docx")
```

### Word con template (docxtpl)

```python
from docxtpl import DocxTemplate

tpl = DocxTemplate("propuesta_bim.docx")
tpl.render({
    "proyecto": "Torre Acme",
    "cliente": "Acme Corp",
    "fecha": "2026-03-04",
    "alcance": "Modelado 3D LOD 300 + Coordinación MEP",
})
tpl.save("propuesta_acme.docx")
```

### PDF simple (fpdf2)

```python
from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.set_font("helvetica", size=16)
pdf.cell(text="Título del Documento")
pdf.ln(10)
pdf.set_font("helvetica", size=12)
pdf.multi_cell(w=0, text="Contenido del documento...")
pdf.output("documento.pdf")
```

### PowerPoint (python-pptx)

```python
from pptx import Presentation

prs = Presentation()
for slide_data in slides:
    layout = prs.slide_layouts[1]  # Title + Content
    slide = prs.slides.add_slide(layout)
    slide.shapes.title.text = slide_data["title"]
    slide.placeholders[1].text = slide_data["content"]
prs.save("presentacion.pptx")
```

## Notas

- Todos los handlers aceptan `output_path` opcional. Sin él, retornan el archivo en base64.
- Los templates .docx usan sintaxis Jinja2: `{{ variable }}`, `{% for item in lista %}`.
- Para PDFs con diseño complejo (CSS), usar `html_content` con weasyprint.
- Para PDFs simples sin dependencias de sistema, usar `text_content` con fpdf2.
