# Task R15 — Bitácora: Asegurar "En pocas palabras" en cada página

**Fecha:** 2026-03-05  
**Ronda:** 15  
**Agente:** Cursor Agent Cloud  
**Branch:** `feat/bitacora-en-pocas-palabras`

---

## Contexto

La task 064 pide añadir en cada página de la Bitácora una sección **"En pocas palabras"** (resumen amigable para no técnicos) al inicio del contenido. El enriquecimiento (task 063) puede haber añadido detalle técnico y diagramas, pero la Bitácora sigue siendo dura si falta ese resumen en lenguaje simple.

**Objetivo:** Asegurar que **todas** las páginas de la base de datos Bitácora tengan, como primer bloque visible, la sección "En pocas palabras" con 2–4 oraciones en español para perfiles no técnicos. Sin jerga; qué se hizo y para qué sirve.

**Database ID Bitácora:** `85f89758684744fb9f14076e7ba0930e`

---

## Tareas requeridas

1. **Reutilizar o extender** el script de enriquecimiento (`scripts/enrich_bitacora_pages.py` o el que use `notion.enrich_bitacora_page`):
   - Listar todas las páginas de la Bitácora.
   - Para cada página, comprobar si ya tiene un bloque con título "En pocas palabras" (o "Resumen para todos") al inicio.
   - Si **no** lo tiene: generar el texto amigable a partir del Título y del Detalle actual (reescrito en lenguaje no técnico) e insertar ese bloque como **primer** hijo de la página (API: append block children al page_id).

2. **Generación del texto** — Para cada entrada, producir 2–4 oraciones que expliquen:
   - Qué se logró (en términos de resultado o beneficio).
   - Para qué sirve (opcional).
   Evitar: nombres de archivos, APIs, PRs, workers, stacks. Si hace falta un término técnico, explicarlo en una frase entre paréntesis.

3. **Orden** — La estructura interna de cada página debe quedar:
   1. "En pocas palabras" (siempre primero).
   2. Resto del contenido (resumen técnico, diagramas, tablas) debajo.

4. **Idioma** — Todo en español.

5. **Ejecución** — Ejecutar el script contra la Bitácora real (con NOTION_API_KEY y NOTION_BITACORA_DB_ID) y verificar en Notion que al menos las páginas principales tienen la sección visible al abrirlas.

---

## Criterios de éxito

- [ ] Todas las páginas de la Bitácora tienen la sección "En pocas palabras" (o "Resumen para todos") al inicio.
- [ ] El texto es comprensible para alguien no técnico.
- [ ] No se elimina contenido existente; solo se añade o se asegura esta sección.
- [ ] PR abierto a `main` (con script y/o cambios documentados).
