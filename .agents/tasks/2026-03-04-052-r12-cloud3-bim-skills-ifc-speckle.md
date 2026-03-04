# Task R12 — Cloud 3: BIM Skills — IFC, Speckle y Document Templates

**Fecha:** 2026-03-04  
**Ronda:** 12  
**Agente:** Cursor Agent Cloud 3  
**Branch:** `feat/bim-skills-ifc-speckle`

---

## Contexto

En R11, Cloud 1 creó skills para Revit, Dynamo, Rhino/Grasshopper, Navisworks, ACC/BIM360 y KUKA robots. Cloud 8 creó handlers para generar documentos Word/PDF/PPT con plantillas BIM básicas.

**Brechas identificadas:**
1. Faltan skills para herramientas BIM fundamentales: **IFC/IfcOpenShell**, **Speckle** (viewer + API), **Dalux** (field BIM)
2. Las plantillas Word/DOCX en `worker/templates/documents/` fueron generadas como binarios vacíos — necesitan contenido real
3. Falta el skill de `ifc-python` que es central para interoperabilidad BIM open source

**Archivos de referencia:**
- `openclaw/workspace-templates/skills/revit/SKILL.md` — ejemplo de skill BIM de calidad
- `openclaw/workspace-templates/skills/acc-bim360/SKILL.md` — ejemplo con API keys
- `openclaw/workspace-templates/skills/consultor-bim/SKILL.md` — skill del perfil profesional
- `openclaw/workspace-templates/skills/speckle-dalux-powerbi/SKILL.md` — versión básica de Speckle/Dalux existente (mejorar)
- `worker/tasks/document_generator.py` — handlers de documentos (ya implementados)
- `scripts/create_docx_templates.py` — script que genera las plantillas binarias

---

## Tareas requeridas

### 1. `openclaw/workspace-templates/skills/ifc-python/SKILL.md`

Skill para trabajo con archivos IFC usando IfcOpenShell y herramientas open source.

**YAML frontmatter:**
```yaml
---
name: ifc-python
description: >-
  Leer, modificar y exportar archivos IFC con IfcOpenShell. Extrae elementos,
  propiedades, geometría y metadatos de modelos BIM. Usa cuando el usuario diga
  "IFC", "IfcOpenShell", "modelo IFC", "propiedades IFC", "exportar IFC",
  "leer IFC", "interoperabilidad BIM", "open BIM".
metadata:
  openclaw:
    emoji: "🏗️"
    requires:
      env: []
---
```

**Contenido del skill (secciones):**
- Instalación y setup (pip install ifcopenshell)
- Abrir y explorar un modelo IFC (schema, elementos por tipo)
- Extraer propiedades de elementos (IfcPropertySet, IfcPropertySingleValue)
- Filtrar elementos por tipo (IfcWall, IfcDoor, IfcSpace, etc.)
- Exportar a CSV/JSON para análisis
- Modificar propiedades y guardar IFC
- Integración con `llm.generate` para análisis de modelos
- Integración con `windows.fs.*` para leer IFC desde VM
- Ejemplo completo: "extraer áreas de todos los espacios de un IFC"

---

### 2. Mejorar `openclaw/workspace-templates/skills/speckle-dalux-powerbi/SKILL.md`

El skill actual es básico. Reescribirlo con:

**YAML frontmatter:**
```yaml
---
name: speckle-dalux-powerbi
description: >-
  Gestionar modelos BIM en Speckle (viewer 3D, streams, commits), revisar
  incidencias en Dalux Field, y conectar datos BIM a Power BI. Usa cuando
  el usuario diga "Speckle", "Dalux", "incidencias campo", "BIM viewer",
  "Power BI BIM", "stream BIM", "modelo en la nube".
metadata:
  openclaw:
    emoji: "🌐"
    requires:
      env:
        - SPECKLE_TOKEN
---
```

**Secciones a incluir:**
- **Speckle:** API REST (streams, commits, objects), Speckle Manager, connectors
- **Speckle Python SDK:** enviar/recibir objetos, Base objects
- **Dalux:** tipos de incidencias (Punch Items), flujo de QA/QC en campo
- **Power BI + Speckle:** connector oficial, crear reportes de avance
- Ejemplos de integración con `research.web` para documentación

---

### 3. Nuevo skill: `openclaw/workspace-templates/skills/bim-coordination/SKILL.md`

Skill para coordinación BIM y clash detection.

**YAML frontmatter:**
```yaml
---
name: bim-coordination
description: >-
  Coordinar modelos multidisciplinarios BIM: clash detection, federación de
  modelos, BCF (BIM Collaboration Format), NWD/NWC en Navisworks. Usa cuando
  el usuario diga "clash detection", "interferencias", "coordinación BIM",
  "BCF", "federar modelos", "NWD", "Navisworks Manage".
metadata:
  openclaw:
    emoji: "⚙️"
    requires:
      env: []
---
```

**Secciones:**
- Flujo de coordinación BIM (modelado → exportación NWC → federación NWD → clash → BCF)
- BCF: formato de issues, workflow entre plataformas
- Navisworks API (COM) para automatizar clash reports
- IFC Federation con IfcOpenShell
- Herramientas: Navisworks, Autodesk Construction Cloud, Trimble Connect
- Integración con `notion.upsert_task` para rastrear issues de coordinación
- Integración con `linear.create_issue` para escalamiento de clashes críticos

---

### 4. Regenerar plantillas BIM con contenido real

El script `scripts/create_docx_templates.py` existe pero genera templates básicos. Actualizarlo para crear plantillas con **contenido real de consultoría BIM**:

#### `worker/templates/documents/propuesta_bim.docx`

Estructura con secciones reales:
1. Portada (logo placeholder, cliente, fecha, versión)
2. Resumen Ejecutivo
3. Alcance de servicios BIM (subsecciones por LOD: 200, 300, 400)
4. Metodología (tabla de entregables por fase: Diseño / Construcción / Operación)
5. Equipo propuesto (tabla: Rol | Perfil | Horas)
6. Cronograma (tabla: Etapa | Duración | Hito)
7. Honorarios (tabla con totales)
8. Condiciones Generales
9. Firma y aceptación

Usar `python-docx` para generar con estilos, tablas, encabezados y pie de página.

#### `worker/templates/documents/cotizacion_bim.docx`

Estructura:
1. Encabezado empresa
2. Datos del cliente
3. Objeto de la cotización
4. Detalle de ítems (tabla: Item | Descripción | Hrs | Valor Unit. | Total)
5. Subtotal / IVA / Total
6. Validez y condiciones de pago
7. Firma

---

### 5. Tests

Crear `tests/test_bim_skills.py` con tests de validación:

- `test_ifc_skill_has_required_frontmatter`
- `test_speckle_skill_has_speckle_token_env`
- `test_bim_coordination_skill_no_env_required`
- `test_all_new_skills_have_description`
- `test_all_new_skills_have_emoji`
- `test_propuesta_template_exists_and_has_content`
- `test_cotizacion_template_exists_and_has_content`
- `test_propuesta_template_has_sections` (leer con python-docx y verificar títulos)
- `test_cotizacion_template_has_table`

---

## Convenciones del proyecto

- **Skills:** seguir formato exacto de `openclaw/workspace-templates/skills/revit/SKILL.md`
- **Plantillas Word:** usar `python-docx` para generarlas programáticamente (no archivos binarios estáticos)
- **Script:** `scripts/create_docx_templates.py` debe ser ejecutable directamente (`python scripts/create_docx_templates.py`) y regenerar las plantillas
- **Rama:** crear `feat/bim-skills-ifc-speckle` y abrir PR a `main`

## Criterios de éxito

- [x] `openclaw/workspace-templates/skills/ifc-python/SKILL.md` — completo con ejemplos
- [x] `openclaw/workspace-templates/skills/speckle-dalux-powerbi/SKILL.md` — mejorado
- [x] `openclaw/workspace-templates/skills/bim-coordination/SKILL.md` — nuevo
- [x] `scripts/create_docx_templates.py` — actualizado para generar templates con contenido real
- [x] `worker/templates/documents/propuesta_bim.docx` — regenerado con estructura BIM completa
- [x] `worker/templates/documents/cotizacion_bim.docx` — regenerado con tabla de ítems
- [x] `tests/test_bim_skills.py` — 13 tests (9+ requeridos)
- [x] PR abierto a `main` — PR #62
