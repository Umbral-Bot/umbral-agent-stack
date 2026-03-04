---
name: rhinoceros-grasshopper
description: >-
  Scripting con RhinoCommon, componentes Grasshopper y Python en Rhino/GH
  para modelado paramétrico, automatización y fabricación digital.
  Use when "Rhino", "Grasshopper", "GH script", "RhinoCommon", "Python Rhino",
  "componente Grasshopper", "modelado paramétrico", "Rhino Python",
  "algoritmo generativo", "script GH", "Rhino scripting".
metadata:
  openclaw:
    emoji: "\U0001F98F"
    requires:
      env: []
---

# Rhinoceros & Grasshopper Skill — Scripting y Modelado Paramétrico

Rick usa este skill para asistir con scripting en Rhino/GH, creación de componentes personalizados y automatización de geometría paramétrica.

## Ecosistema Rhino/Grasshopper

| Herramienta | Descripción |
|-------------|-------------|
| **Rhino 8** | Motor NURBS, CAD 3D profesional |
| **Grasshopper** | Visual programming integrado en Rhino |
| **RhinoCommon SDK** | API .NET de Rhino, accesible desde GH y scripts |
| **RhinoScriptSyntax** | API Python de alto nivel (similar a RhinoScript VBScript) |
| **Script Component (GH)** | Python 3, Python 2 (IronPython), C#, VB en Grasshopper |

## Python en Grasshopper — Script Component

El componente Script unificado de Rhino 8 soporta múltiples lenguajes.

### Acceder al Script Component

1. Pestaña **Maths** → panel **Script** → componente **Script**
2. O buscar "Script" en la barra de búsqueda de GH

### Estructura básica (Python 3)

```python
# Inputs: x, y definidos en el ZUI del componente
# Outputs: a, b, c... definidos en el ZUI

import rhinoscriptsyntax as rs
import Rhino.Geometry as rg

# Crear un punto
pt = rg.Point3d(x, y, 0)

# Crear una esfera
sphere = rg.Sphere(pt, 1.0)
brep = sphere.ToBrep()

# Output
a = brep
```

### ZUI — Agregar inputs/outputs dinámicamente

- Zoom in en el componente → aparecen botones "+" y "–"
- Clic "+" bajo Inputs para agregar un nuevo parámetro
- Clic derecho en el input → "Type hint" para tipar el parámetro (float, int, str, etc.)

## RhinoCommon — Objetos clave

| Namespace | Clases principales |
|-----------|-------------------|
| `Rhino.Geometry` | Point3d, Vector3d, Line, Curve, Surface, Brep, Mesh |
| `Rhino.Geometry.Intersect` | Intersection (curva-curva, curva-superficie, etc.) |
| `Rhino.Collections` | CurveList, Point3dList |
| `Rhino.DocObjects` | RhinoObject, Layer, ObjectAttributes |
| `Rhino.RhinoDoc` | Documento activo (add/delete objects) |

### Geometría básica

```python
import Rhino.Geometry as rg
import math

# Punto y vector
origin = rg.Point3d(0, 0, 0)
normal = rg.Vector3d(0, 0, 1)

# Plano
plane = rg.Plane(origin, normal)

# Curvas
line = rg.Line(rg.Point3d(0, 0, 0), rg.Point3d(10, 0, 0))
circle = rg.Circle(plane, 5.0)
arc = rg.Arc(circle, math.pi / 2)

# NURBS curve desde puntos
pts = [rg.Point3d(i, math.sin(i), 0) for i in range(10)]
nurbs = rg.NurbsCurve.Create(False, 3, pts)

# Superficie de revolución
surface = rg.RevSurface.Create(line.ToNurbsCurve(), rg.Line(origin, rg.Point3d(0, 10, 0)), 0, 2*math.pi)
```

### Operaciones booleanas (Brep)

```python
import Rhino.Geometry as rg

box_a = rg.Box(rg.Plane.WorldXY, rg.Interval(-5, 5), rg.Interval(-5, 5), rg.Interval(0, 10))
box_b = rg.Box(rg.Plane.WorldXY, rg.Interval(-3, 3), rg.Interval(-3, 3), rg.Interval(-1, 11))

brep_a = box_a.ToBrep()
brep_b = box_b.ToBrep()

# Diferencia booleana
result = rg.Brep.CreateBooleanDifference([brep_a], [brep_b], 0.001)
a = result
```

### Mesh — Análisis y procesamiento

```python
import Rhino.Geometry as rg

mesh = x  # Input: Mesh desde GH

# Normales de vértices
mesh.Normals.ComputeNormals()

# Weld edges (suavizar)
mesh.Weld(math.pi)

# Estadísticas
area = rg.AreaMassProperties.Compute(mesh).Area
vertex_count = mesh.Vertices.Count

a = area
b = vertex_count
```

## RhinoScriptSyntax — API de alto nivel

```python
import rhinoscriptsyntax as rs

# Seleccionar objeto
obj_id = rs.GetObject("Seleccioná una curva", rs.filter.curve)

# Propiedades
length = rs.CurveLength(obj_id)
domain = rs.CurveDomain(obj_id)

# Dividir curva
pts = rs.DivideCurve(obj_id, 10)  # 10 puntos equidistantes

# Crear superficie desde borde
srf = rs.AddPlanarSrf([obj_id])

print(f"Longitud: {length:.2f} | Puntos: {len(pts)}")
```

## Componentes Grasshopper — Patrones comunes

### Data Tree en Python

```python
import Grasshopper as gh
from Grasshopper.Kernel.Data import GH_Path
from Grasshopper import DataTree
import Rhino.Geometry as rg

# IN[0] es un DataTree
input_tree = x  # tipo: DataTree[object]

output_tree = DataTree[rg.Point3d]()

for i, branch in enumerate(input_tree.Branches):
    path = GH_Path(i)
    for item in branch:
        # Transformar cada punto
        moved = rg.Point3d(item.X + 1, item.Y, item.Z)
        output_tree.Add(moved, path)

a = output_tree
```

### Acceso al documento Rhino desde GH

```python
import Rhino
import scriptcontext as sc

doc = sc.doc  # Documento Rhino activo

# Agregar objeto al documento
pt = rg.Point3d(0, 0, 0)
guid = doc.Objects.AddPoint(pt)

# Acceder a capas
layer_idx = doc.Layers.FindByFullPath("Default", False)
```

## Crear Custom Component (.ghpy / C#)

Para componentes publicables, usar la clase `GH_Component` en C# o en Python con `ghpythonlib`:

```python
# Grasshopper Python Component heredando GH_Component (avanzado)
# Ver: https://developer.rhino3d.com/guides/grasshopper/
```

## Herramientas complementarias

| Plugin | Función |
|--------|---------|
| **Pufferfish** | Morphing y arrays paramétricos |
| **Weaverbird** | Subdivisión de mesh |
| **Lunchbox** | Paneles, estructuras, data management |
| **Kangaroo** | Física y simulación |
| **Human** | UI y display avanzado |

## Ejemplos de uso con Rick

- **Rick: "Creá una grilla de paneles hexagonales adaptada a una superficie"** → Grasshopper: divide surface + Python polygon generator.
- **Rick: "Script Python para leer puntos de una curva y exportarlos a CSV"** → `rs.DivideCurve` + `csv` module.
- **Rick: "Generá un componente GH que reciba un Brep y devuelva el centro de masa"** → `rg.VolumeMassProperties.Compute`.
- **Rick: "Cómo accedo al documento Rhino desde dentro de Grasshopper"** → `import scriptcontext as sc; doc = sc.doc`.

## Recursos oficiales

- Rhino Developer Docs: https://developer.rhino3d.com/
- Grasshopper Guides: https://developer.rhino3d.com/guides/grasshopper/
- Python en GH: https://developer.rhino3d.com/guides/scripting/scripting-gh-python/
- RhinoCommon API: https://developer.rhino3d.com/api/rhinocommon/
- Discourse (foro): https://discourse.mcneel.com/

## Notas

- Rhino 8 usa Python 3 (CPython) en el Script Component; Rhino 7 usaba IronPython 2.7.
- El ZUI (Zoomable User Interface) permite agregar inputs/outputs al Script Component haciendo zoom.
- `rhinoscriptsyntax` es un wrapper de alto nivel sobre `RhinoCommon`; para control total, usar `Rhino.Geometry`.
- Los plugins de Grasshopper se instalan desde PackageManager (`_TestPackageManager`) o Food4Rhino.
