---
name: revit
description: >-
  Asistir con la API de Autodesk Revit para automatización con Python (pyRevit/IronPython),
  scripting de Dynamo, creación de familias y gestión de parámetros.
  Use when "Revit API", "pyRevit", "script Revit", "automatizar Revit",
  "parámetros Revit", "familia Revit", "filtrar elementos Revit", "Revit Python".
metadata:
  openclaw:
    emoji: "\U0001F3E2"
    requires:
      env: []
---

# Revit Skill — API, pyRevit y Automatización

Rick usa este skill para asistir con scripting en Revit, uso de la Revit API en Python/IronPython, automatización con pyRevit y consultas sobre la estructura de datos del modelo BIM.

## Referencia rápida de la API

### Acceso al documento activo (IronPython/pyRevit)

```python
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import *

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
```

### Transacciones (obligatorias para modificar el modelo)

```python
t = Transaction(doc, "Nombre de la transacción")
t.Start()
# ... modificaciones ...
t.Commit()
```

### Filtrar elementos por categoría

```python
# Todos los muros
collector = FilteredElementCollector(doc)\
    .OfCategory(BuiltInCategory.OST_Walls)\
    .WhereElementIsNotElementType()\
    .ToElements()

# Por clase de elemento
rooms = FilteredElementCollector(doc)\
    .OfClass(SpatialElement)\
    .ToElements()

# Con filtro de parámetro
rule = ParameterFilterRuleFactory.CreateEqualsRule(
    ElementId(BuiltInParameter.ELEM_LEVEL_PARAM),
    level_id
)
param_filter = ElementParameterFilter(rule)
filtered = FilteredElementCollector(doc)\
    .WherePasses(param_filter)\
    .ToElements()
```

### Leer y escribir parámetros

```python
# Leer parámetro por nombre
element = doc.GetElement(ElementId(12345))
param = element.LookupParameter("Comentarios")
value = param.AsString()  # o .AsDouble(), .AsInteger()

# Escribir parámetro (dentro de Transaction)
param.Set("Nuevo valor")

# Parámetro compartido por GUID
shared_param = element.get_Parameter(
    Guid("xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
)
```

### Crear elementos

```python
# Crear muro por línea
line = Line.CreateBound(XYZ(0, 0, 0), XYZ(10, 0, 0))
wall_type = doc.GetElement(wall_type_id)
level = doc.GetElement(level_id)
wall = Wall.Create(doc, line, wall_type.Id, level.Id, 3.0, 0.0, False, False)

# Colocar familia (FamilyInstance)
family_symbol = doc.GetElement(symbol_id)
if not family_symbol.IsActive:
    family_symbol.Activate()
    doc.Regenerate()
instance = doc.Create.NewFamilyInstance(
    XYZ(0, 0, 0), family_symbol,
    Structure.StructuralType.NonStructural
)
```

### Vistas y hojas

```python
# Obtener todas las vistas de plano
views = FilteredElementCollector(doc)\
    .OfClass(ViewPlan)\
    .ToElements()

# Vistas en hoja
sheet = doc.GetElement(sheet_id)
viewports = FilteredElementCollector(doc)\
    .OfClass(Viewport)\
    .ToElements()
vp_on_sheet = [v for v in viewports if v.SheetId == sheet.Id]
```

### Exportar a IFC/NWC

```python
# Exportar IFC
options = IFCExportOptions()
options.FileVersion = IFCVersion.IFC2x3CV2
doc.Export(export_path, "modelo.ifc", options)

# Exportar NWC (Navisworks)
nwc_options = NavisworksExportOptions()
nwc_options.ExportScope = NavisworksExportScope.Model
doc.Export(export_path, "modelo.nwc", nwc_options)
```

## pyRevit — Estructura de extensión

```
mi_extension.extension/
  mi_panel.panel/
    Mi_Herramienta.pushbutton/
      script.py          # Código principal
      icon.png           # Ícono 32x32
      bundle.yaml        # Metadata (title, tooltip)
```

`bundle.yaml` mínimo:
```yaml
title: Mi Herramienta
tooltip: Descripción de la herramienta
```

`script.py` mínimo:
```python
# -*- coding: utf-8 -*-
from pyrevit import revit, DB, script

doc = revit.doc
output = script.get_output()
output.print_md("## Resultado")
```

## Dynamo desde Revit API

### Acceso a nodos desde Python en Dynamo

```python
# En un nodo Python de Dynamo
import clr
clr.AddReference('RevitNodes')
import Revit
clr.ImportExtensions(Revit.Elements)
clr.ImportExtensions(Revit.GeometryConversion)

clr.AddReference('RevitServices')
import RevitServices
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager

doc = DocumentManager.Instance.CurrentDBDocument
TransactionManager.Instance.EnsureInTransaction(doc)
# ... modificaciones ...
TransactionManager.Instance.TransactionTaskDone()
```

## Categorías BuiltInCategory más usadas en AEC

| Nombre | BuiltInCategory |
|--------|----------------|
| Muros | `OST_Walls` |
| Puertas | `OST_Doors` |
| Ventanas | `OST_Windows` |
| Pisos | `OST_Floors` |
| Techos | `OST_Roofs` |
| Habitaciones | `OST_Rooms` |
| MEP Tuberías | `OST_PipeCurves` |
| Estructura Columnas | `OST_StructuralColumns` |

## Errores comunes

| Error | Causa | Solución |
|-------|-------|----------|
| `InvalidOperationException` al modificar | Falta Transaction | Envolver en `t.Start() / t.Commit()` |
| `NullReferenceException` en parámetro | Parámetro no existe en ese tipo | Verificar con `LookupParameter` ≠ None |
| Familia no se coloca | `FamilySymbol` no activa | Llamar `symbol.Activate()` antes |
| Modelo regenerado stale | Cambios sin regenerar | Llamar `doc.Regenerate()` |

## Links oficiales

- [Revit API Docs](https://www.revitapidocs.com/) — Referencia completa de clases y métodos
- [APS Revit Overview](https://aps.autodesk.com/developer/overview/revit) — SDK y ejemplos
- [pyRevit Docs](https://pyrevitlabs.notion.site/) — Guía de extensiones pyRevit
- [Revit Developer Guide](https://help.autodesk.com/view/RVT/2025/ENU/?guid=Revit_API_Revit_API_Developers_Guide_html) — Guía oficial Autodesk
