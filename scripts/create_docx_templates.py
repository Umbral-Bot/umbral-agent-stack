"""One-off script to create the .docx templates for BIM proposals and quotes.

Run once: python scripts/create_docx_templates.py
Generates:
  - worker/templates/documents/propuesta_bim.docx
  - worker/templates/documents/cotizacion_bim.docx
"""

import os
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "worker", "templates", "documents")


def create_propuesta_bim():
    doc = Document()

    style = doc.styles["Normal"]
    font = style.font
    font.name = "Calibri"
    font.size = Pt(11)

    # --- Cover page ---
    for _ in range(4):
        doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("[Logo]")
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

    doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("PROPUESTA DE CONSULTORÍA BIM")
    run.bold = True
    run.font.size = Pt(24)
    run.font.color.rgb = RGBColor(0x1A, 0x47, 0x7A)

    doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("{{ proyecto }}")
    run.font.size = Pt(18)
    run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Preparado para: {{ cliente }}")
    run.font.size = Pt(14)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Fecha: {{ fecha }}")
    run.font.size = Pt(12)

    doc.add_page_break()

    # --- Sections ---
    sections = [
        ("1. Contexto", "{{ contexto }}"),
        ("2. Alcance", "{{ alcance }}"),
        ("3. Metodología", "{{ metodologia }}"),
        ("4. Entregables", "{{ entregables }}"),
        ("5. Inversión", "{{ inversion }}"),
        ("6. Cronograma", "{{ cronograma }}"),
        ("7. Condiciones Generales", "{{ condiciones }}"),
    ]

    for heading, placeholder in sections:
        h = doc.add_heading(heading, level=1)
        for run in h.runs:
            run.font.color.rgb = RGBColor(0x1A, 0x47, 0x7A)
        doc.add_paragraph(placeholder)
        doc.add_paragraph()

    # --- Footer info ---
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("─" * 40)
    run.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("David — Consultoría BIM & Tecnología")
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("contacto@umbral.dev | umbral.dev")
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

    out = os.path.join(TEMPLATES_DIR, "propuesta_bim.docx")
    doc.save(out)
    print(f"Created: {out}")


def create_cotizacion_bim():
    doc = Document()

    style = doc.styles["Normal"]
    font = style.font
    font.name = "Calibri"
    font.size = Pt(11)

    # --- Header ---
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run("COTIZACIÓN")
    run.bold = True
    run.font.size = Pt(20)
    run.font.color.rgb = RGBColor(0x1A, 0x47, 0x7A)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run("Ref: {{ referencia }}")
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    doc.add_paragraph()

    # --- Client info ---
    table_info = doc.add_table(rows=3, cols=2)
    table_info.alignment = WD_TABLE_ALIGNMENT.LEFT
    cells = [
        ("Proyecto:", "{{ proyecto }}"),
        ("Cliente:", "{{ cliente }}"),
        ("Fecha:", "{{ fecha }}"),
    ]
    for i, (label, value) in enumerate(cells):
        row = table_info.rows[i]
        row.cells[0].text = label
        row.cells[1].text = value
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(11)

    doc.add_paragraph()

    # --- Services table header ---
    doc.add_heading("Detalle de Servicios", level=1)

    p = doc.add_paragraph()
    run = p.add_run("{%tr for servicio in servicios %}")
    run.font.size = Pt(1)
    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    table = doc.add_table(rows=2, cols=4)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    headers = ["Servicio", "Descripción", "Plazo", "Valor"]
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.bold = True
                run.font.size = Pt(10)

    row_data = [
        "{{ servicio.nombre }}",
        "{{ servicio.descripcion }}",
        "{{ servicio.plazo }}",
        "{{ servicio.valor }}",
    ]
    for i, val in enumerate(row_data):
        table.rows[1].cells[i].text = val

    p = doc.add_paragraph()
    run = p.add_run("{%tr endfor %}")
    run.font.size = Pt(1)
    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    doc.add_paragraph()

    # --- Totals ---
    t_totals = doc.add_table(rows=3, cols=2)
    t_totals.alignment = WD_TABLE_ALIGNMENT.RIGHT
    totals = [
        ("Subtotal:", "{{ subtotal }}"),
        ("IVA:", "{{ iva }}"),
        ("TOTAL:", "{{ total }}"),
    ]
    for i, (label, value) in enumerate(totals):
        t_totals.rows[i].cells[0].text = label
        t_totals.rows[i].cells[1].text = value
        for cell in t_totals.rows[i].cells:
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    doc.add_paragraph()

    # --- Conditions ---
    doc.add_heading("Condiciones", level=2)
    doc.add_paragraph("Vigencia de la cotización: {{ vigencia }}")
    doc.add_paragraph("{{ notas }}")

    doc.add_paragraph()

    # --- Footer ---
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("David — Consultoría BIM & Tecnología | contacto@umbral.dev")
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

    out = os.path.join(TEMPLATES_DIR, "cotizacion_bim.docx")
    doc.save(out)
    print(f"Created: {out}")


if __name__ == "__main__":
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    create_propuesta_bim()
    create_cotizacion_bim()
    print("Done!")
