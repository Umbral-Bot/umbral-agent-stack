# Task R14 — Skills coverage para tareas de una sola palabra (ping, etc.)

**Fecha:** 2026-03-04  
**Ronda:** 14  
**Agente:** Antigravity / Code Claude / Cursor Agent Cloud  
**Branch:** `feat/skills-coverage-single-word`

---

## Contexto

`tests/test_skills_coverage.py` marca que la tarea `ping` no tiene skill. Existe `openclaw/workspace-templates/skills/ping/SKILL.md` pero el reporte no la detecta.

La causa: `_extract_task_names_from_skill()` usa un regex que solo matchea nombres con punto (`task.subtask`):

```python
r"\b([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+)\b"
```

Tareas como `ping`, `research.web` (esta sí coincide), etc. Las de una sola palabra nunca matchean.

**Objetivo:** Que el reporte de coverage detecte correctamente skills para tareas de una palabra (p. ej. `ping`) y elimine falsos positivos.

---

## Tareas requeridas

1. **Ajustar la lógica de mapeo** — En `tests/test_skills_coverage.py`, además del regex actual, considerar el `skill_name` del directorio: si el skill se llama `ping` y existe la task `ping` en TASK_HANDLERS, considerarla cubierta.

2. **Mapeo explícito skill_name → task** — Añadir lógica: para cada `skill_name` (nombre del directorio del skill), si `skill_name` está en TASK_HANDLERS, añadirlo a `covered_tasks`. También si el skill_name con reemplazo de `-` por `.` coincide (ej: `llm-generate` → `llm.generate`).

3. **Actualizar `scripts/skills_coverage_report.py`** — Si existe, aplicar la misma lógica para que el script de reporte sea consistente.

4. **Verificar** — Tras los cambios, `pytest tests/test_skills_coverage.py -v` no debe mostrar `ping` como task sin skill (si existe `skills/ping/SKILL.md`).

---

## Criterios de éxito

- [ ] La tarea `ping` se considera cubierta cuando existe `skills/ping/SKILL.md`
- [ ] No se introducen falsos positivos para otras tasks
- [ ] `scripts/skills_coverage_report.py` (si existe) actualizado de forma consistente
- [ ] PR abierto a `main`
