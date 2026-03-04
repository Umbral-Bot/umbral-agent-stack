# Task R12 — Cloud 4: Skills Audit + Pytest + TOOLS.md sync

**Fecha:** 2026-03-04  
**Ronda:** 12  
**Agente:** Cursor Agent Cloud 4  
**Branch:** `feat/skills-audit-pytest`

---

## Contexto

Tras R11, el repo tiene **45 skills SKILL.md** y **37 Worker tasks** registradas. Se necesita una ronda de auditoría para:
1. Verificar que todas las skills tienen formato correcto y no hay errores
2. Detectar qué Worker tasks no tienen skill correspondiente
3. Ejecutar pytest y corregir cualquier test roto
4. Mantener el `board.md` actualizado

**Archivos de referencia:**
- `scripts/validate_skills.py` — validador existente (creado en R9)
- `tests/test_skills_validation.py` — tests del validador
- `openclaw/workspace-templates/skills/` — 45 skills a auditar
- `worker/tasks/__init__.py` — 37 tasks registradas
- `.agents/board.md` — estado del proyecto
- `openclaw/workspace-templates/TOOLS.md` — actualizado en esta misma sesión

---

## Tareas requeridas

### 1. Ejecutar y corregir `scripts/validate_skills.py`

El script existe. Ejecutarlo contra todos los skills:

```bash
python scripts/validate_skills.py openclaw/workspace-templates/skills/
```

**Para cada skill que falle:**
- Identificar el error (frontmatter faltante, campo incorrecto, etc.)
- Corregir el SKILL.md correspondiente

**Errores comunes a buscar:**
- `metadata.openclaw.emoji` faltante o valor incorrecto
- `name` no coincide con el nombre del directorio
- `description` vacía o muy corta (< 20 chars)
- `metadata.openclaw.requires.env` es lista de strings (no objetos)
- Caracteres Unicode en emoji que Python no serializa bien

Crear `reports/skills-audit-r12.md` con el resultado:
```markdown
# Skills Audit R12

**Fecha:** 2026-03-04  
**Total skills:** 45  
**OK:** X  
**Con errores:** Y  

## Errores encontrados y corregidos

| Skill | Error | Corrección |
|-------|-------|------------|
| ... | ... | ... |

## Skills sin errores
[lista]
```

---

### 2. `scripts/skills_coverage_report.py`

Script que compara las tasks en `worker/tasks/__init__.py` con los skills en `openclaw/workspace-templates/skills/` y detecta brechas.

```python
#!/usr/bin/env python3
"""
Genera reporte de cobertura: qué Worker tasks tienen skill y cuáles no.
Uso: python scripts/skills_coverage_report.py
"""
```

**Lógica:**
1. Leer `worker/tasks/__init__.py` → extraer todos los task names del dict `TASK_HANDLERS`
2. Leer `openclaw/workspace-templates/skills/*/SKILL.md` → extraer `name` del frontmatter
3. Comparar: qué tasks tienen skill, cuáles no
4. Imprimir tabla y guardar en `reports/skills-coverage-r12.md`

**Output esperado:**
```
✅ Tasks CON skill (X):
  - ping → ping
  - llm.generate → llm-generate
  ...

❌ Tasks SIN skill (Y):
  - composite.research_report
  - azure.audio.generate
  - windows.pad.run_flow
  ...

Cobertura: X/37 (Z%)
```

Para las tasks sin skill, intentar crear los SKILL.md faltantes de alta prioridad (ver punto 3).

---

### 3. Crear skills faltantes de alta prioridad

Basándose en el reporte de cobertura, crear SKILL.md para estas tasks que probablemente no tienen skill:

#### `openclaw/workspace-templates/skills/azure-audio/SKILL.md`

```yaml
---
name: azure-audio
description: >-
  Generar audio TTS (text-to-speech) con Azure OpenAI Realtime API.
  Usa cuando el usuario diga "generar audio", "texto a voz", "TTS",
  "audio Azure", "sintetizar voz", "narrar texto".
metadata:
  openclaw:
    emoji: "🔊"
    requires:
      env:
        - AZURE_OPENAI_ENDPOINT
        - AZURE_OPENAI_KEY
---
```

Incluir: parámetros, voces disponibles, formatos de salida, ejemplos de uso.

#### `openclaw/workspace-templates/skills/composite/SKILL.md`

```yaml
---
name: composite
description: >-
  Ejecutar tareas compuestas: investigación web + generación de reporte
  completo en Notion. Usa cuando el usuario pida "investigar y reportar",
  "research report", "reporte de investigación", "buscar y resumir".
metadata:
  openclaw:
    emoji: "📊"
    requires:
      env:
        - GOOGLE_CSE_KEY
        - NOTION_API_KEY
---
```

#### `openclaw/workspace-templates/skills/windows/SKILL.md`

Verificar si existe y está actualizado. Si falta, crear con cobertura de:
- `windows.pad.run_flow`
- `windows.open_notepad`  
- `windows.fs.*` (todos los filesystem tasks)
- Variables requeridas, ejemplos de uso

---

### 4. Ejecutar pytest y corregir fallos

```bash
python -m pytest tests/ -v --tb=short 2>&1 | head -100
```

**Corregir cualquier test que falle.** Los fallos más probables son:
- Tests que asumen tasks específicos en `TASK_HANDLERS` pero no se actualizaron con los nuevos
- Tests de `validate_skills.py` que fallen con los nuevos skills
- Tests de `test_tools_inventory.py` si el endpoint existe

**Documentar en `reports/pytest-r12.md`:**
```markdown
# Pytest Report R12

**Total tests:** X  
**Passed:** Y  
**Failed:** Z  

## Tests corregidos
| Test | Error original | Fix aplicado |
|------|---------------|--------------|
| ... | ... | ... |
```

---

### 5. Actualizar `reports/drive-skills-scan.md`

El reporte fue generado en R10. Actualizar con estado actual:
- Marcar como "✅ Implementado" los skills que ya existen
- Marcar como "🔲 Pendiente" los que faltan

---

### 6. Actualizar `.agents/board.md`

Agregar sección de R12 con estado de los 4 nuevos agentes:

```markdown
## Round 12 — 2026-03-04

| # | Agente | Branch | Estado | Entregables |
|---|--------|--------|--------|-------------|
| 050 | Cloud 1 | feat/google-calendar-gmail | pending | Google Calendar + Gmail handlers |
| 051 | Cloud 2 | feat/granola-vm-service | pending | Granola Windows service installer |
| 052 | Cloud 3 | feat/bim-skills-ifc-speckle | pending | IFC skill + Speckle mejorado + templates |
| 053 | Cloud 4 | feat/skills-audit-pytest | in_progress | Audit 45 skills + pytest + cobertura |
```

---

## Convenciones del proyecto

- **Sin romper tests:** Si corriges un skill, no rompas los tests existentes
- **Rama:** crear `feat/skills-audit-pytest` y abrir PR a `main`
- **No borrar skills:** Solo corregir formato/contenido, nunca eliminar un skill existente
- **Reporte legible:** Los archivos en `reports/` deben ser markdown bien formateados

## Criterios de éxito

- [ ] `scripts/validate_skills.py` ejecutado — todos los 45 skills pasan validación
- [ ] `reports/skills-audit-r12.md` generado
- [ ] `scripts/skills_coverage_report.py` implementado y ejecutado
- [ ] `reports/skills-coverage-r12.md` generado  
- [ ] Skills faltantes de alta prioridad creados (azure-audio, composite, windows si faltan)
- [ ] `pytest tests/ -v` ejecutado — 0 fallos (corregir los que haya)
- [ ] `reports/pytest-r12.md` generado
- [ ] `.agents/board.md` actualizado con R12
- [ ] PR abierto a `main`
