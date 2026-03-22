---
id: "018"
title: "Notion Result Poster — Smart Reply con composite.research_report"
assigned_to: antigravity
status: done
updated_at: "2026-03-22T19:04:21-03:00"
branch: feat/antigravity-notion-result-poster
priority: critical
round: 4
---

# Notion Result Poster — Respuestas completas en Notion

## Problema
El smart_reply de Claude Code ya hace research + LLM. Pero las respuestas se postean
como texto plano corto. Cuando el resultado es un informe de mercado completo
(composite.research_report), necesitamos:
1. Postear el informe formateado en Notion (no solo un comment)
2. Crear una página hija en la Control Room con el reporte completo
3. Referenciar esa página en el comment de respuesta

## Tu tarea

### A. Nuevo task handler notion.create_report_page
Crear en `worker/tasks/notion.py` un nuevo handler `notion.create_report_page`:

```python
def handle_notion_create_report_page(input_data):
    """
    Crea una página hija en la Control Room con el reporte completo.

    Input:
        parent_page_id: str — ID de la página padre (Control Room)
        title: str — título del reporte
        content: str — contenido en markdown
        sources: list[dict] — fuentes utilizadas (url, title)
        metadata: dict — fecha, topic, team, etc.

    Output:
        page_id: str
        page_url: str
        ok: bool
    """
```

### B. Integrar en smart_reply.py
Modificar `dispatcher/smart_reply.py`:
- Cuando el resultado del composite.research_report sea largo (>500 chars),
  llamar a `notion.create_report_page` para crear una página hija
- El comment de respuesta debe incluir el link a la página:
  `Rick: Informe completo disponible → [Ver reporte](url)`

### C. Formato Notion del reporte
La página debe tener:
- Título: "SIM Report: {topic} — {fecha}"
- Sección "Resumen ejecutivo" (texto del LLM)
- Sección "Fuentes" (lista de URLs con títulos)
- Sección "Queries utilizadas"
- Propiedad de metadatos (Status: done, Team: marketing, etc.)

### D. Convertir Markdown a bloques Notion
Crear helper `worker/tasks/notion_markdown.py`:
- Convierte texto markdown simple a bloques Notion API
- Soporta: párrafos, headers (# ## ###), bullets (- *), bold (**texto**)
- Sin dependencias externas (solo stdlib)

### E. Tests
Crear `tests/test_notion_report_page.py`:
- Test: handle_notion_create_report_page hace llamada correcta a Notion API
- Test: markdown simple se convierte a bloques Notion
- Test: headers se convierten a heading_1/2/3
- Test: bullets se convierten a bulleted_list_item
- Test: smart_reply crea página para respuestas largas
- Test: smart_reply usa comment para respuestas cortas

## Archivos relevantes
- `worker/tasks/notion.py` — agregar handler (referencia de funciones existentes)
- `worker/notion_client.py` — cliente Notion, funciones de API (EXTENDER aquí)
- `dispatcher/smart_reply.py` — integrar lógica de página
- `worker/config.py` — NOTION_CONTROL_ROOM_PAGE_ID

## Log

### [codex] 2026-03-22 19:04 -03:00
Regularizacion administrativa por UMB-132. Esta tarea quedo como arrastre historico y ya no representa trabajo vivo; se cierra el archivo para alinearlo con el board y el estado real del repo.
