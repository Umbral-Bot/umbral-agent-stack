# Task R17 — Implementar 9 funciones Notion para Bitácora (Claude)

**Fecha:** 2026-03-06  
**Ronda:** 17  
**Agente:** Claude (claude-code)  
**Branch:** `claude/090-implementar-notion-bitacora` ← trabaja solo en esta rama. **Pull de main antes.**

---

## Objetivo

Implementar las **9 funciones** que documenta `docs/bitacora-scripts.md`: 6 en `worker/notion_client.py` y 3 en el módulo que use `notion.py` (o donde indique el doc), para que los scripts `enrich_bitacora_pages.py` y `add_resumen_amigable.py` puedan ejecutarse sin skip. Tarea de **solución acotada**, no de búsqueda.

---

## Tareas

1. **Pull y rama:** `git checkout main && git pull origin main`. Crear rama: `git checkout -b claude/090-implementar-notion-bitacora`.

2. **Leer la especificación:** Abrir `docs/bitacora-scripts.md` y localizar la lista de las 9 funciones con firma exacta y orden de implementación. Si el doc no está en main aún, usar los scripts `scripts/enrich_bitacora_pages.py` y `scripts/add_resumen_amigable.py` y los tests `tests/test_notion_enrich_bitacora.py` para inferir nombres, parámetros y comportamiento.

3. **Implementar:** Añadir las 6 funciones en `worker/notion_client.py` y las 3 restantes donde corresponda (p. ej. `worker/tasks/notion.py` o el módulo que importen los scripts). Mantener el estilo y patrones del código existente (Notion API, manejo de errores). No cambiar la firma documentada.

4. **Tests:** Ejecutar `pytest tests/test_notion_enrich_bitacora.py -v`. Corregir hasta que los 34 tests pasen (o documentar en el PR si algún test requiere configuración externa). Ejecutar `pytest tests/ -q` y asegurar 0 failed.

5. **PR:** Abrir un único PR desde `claude/090-implementar-notion-bitacora` a main. Título: "feat(R17-090): implementar 9 funciones Notion para scripts Bitácora". En la descripción listar las funciones añadidas.

---

## Criterios de éxito

- [ ] Las 9 funciones implementadas según spec (o inferida de scripts/tests).
- [ ] `pytest tests/test_notion_enrich_bitacora.py` pasando (o máximo skips documentados).
- [ ] `pytest tests/` en verde. PR abierto a main.

---

## Restricciones

- No tocar dispatcher, CI ni otros handlers. Solo notion_client y el módulo notion necesario para los scripts de Bitácora.
