---
name: rhinoceros-grasshopper
description: >-
  Scripting con RhinoCommon (.NET/Python), desarrollo de componentes Grasshopper,
  GhPython, y automatización en Rhinoceros 3D para arquitectura y fabricación digital.
  Use when "Rhino", "Grasshopper", "RhinoCommon", "GhPython", "componente GH",
  "script Rhino", "Python Rhino", "Rhino API", "NURBS scripting".
metadata:
  openclaw:
    emoji: "\U0001F98F"
    requires:
      env: []
---

# Rhinoceros / Grasshopper Skill — RhinoCommon y GhPython

Rick usa este skill para asistir con scripting en Rhino (RhinoCommon, RhinoScript), componentes de Grasshopper en Python (GhPython), y desarrollo de plugins con la API oficial de McNeel.

## RhinoCommon — Referencia rápida (Python)

### Acceso al documento activo (RhinoScript)

```python
import rhinoscriptsyntax as rs
import Rhino
import Rhino.Geometry as rg

# Documento activo
doc = Rhino.RhinoDoc.ActiveDoc

# Obtener objetos seleccionados
ids = rs.GetObjects("Seleccionar objetos", preselect=True)
```

### Geometría básica

```python
import Rhino.Geometry as rg

# Punto
pt = rg.Point3d(1.0, 2.0, 3.0)

# Línea
line = rg.Line(rg.Point3d(0,0,0), rg.Point3d(10,0,0))
curve = line.ToNurbsCurve()

# Plano
plane = rg.Plane(origin, x_axis, y_axis)

# Esfera
sphere = rg.Sphere(rg.Point3d.Origin, radius=5.0)
brep = sphere.ToBrep()

# Superficie NURBS
surface = rg.NurbsSurface.Create(degree_u=3, degree_v=3,
    rational=False, u_count=4, v_count=4)
```

### Operaciones booleanas

```python
# Unión booleana (Brep)
result = rg.Brep.CreateBooleanUnion([brep_a, brep_b], tolerance=0.001)

# Diferencia
result = rg.Brep.CreateBooleanDifference([brep_a], [brep_b], tolerance=0.001)

# Intersección
result = rg.Brep.CreateBooleanIntersection([brep_a], [brep_b], tolerance=0.001)
```

### Agregar objetos al documento

```python
import scriptcontext as sc

# Agregar curva al documento activo
guid = sc.doc.Objects.AddCurve(curve)

# Agregar superficie
guid = sc.doc.Objects.AddBrep(brep)

# Agregar punto
guid = sc.doc.Objects.AddPoint(pt)

# Agregar con atributos
attr = Rhino.DocObjects.ObjectAttributes()
attr.LayerIndex = layer_index
attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
attr.ObjectColor = System.Drawing.Color.Red
guid = sc.doc.Objects.AddCurve(curve, attr)
```

### Capas

```python
# Crear capa
layer_idx = sc.doc.Layers.Add("Mi Capa", System.Drawing.Color.Blue)

# Buscar capa por nombre
layer_idx = sc.doc.Layers.FindByFullPath("Parent::Child", -1)

# Cambiar capa de un objeto
obj = sc.doc.Objects.Find(guid)
obj.Attributes.LayerIndex = layer_idx
obj.CommitChanges()
```

## Grasshopper — GhPython Script

### Estructura del componente Python en GH

```python
# En un componente GhPython
# Las entradas se declaran en el panel del componente
# Por defecto hay: x, y (entradas), a (salida)

import Rhino.Geometry as rg
import ghpythonlib.components as ghcomp

# Las entradas del componente son variables directas
# Ejemplo con entradas 'puntos' y 'radio'
resultado = []
for pt in puntos:
    circle = rg.Circle(rg.Plane(pt, rg.Vector3d.ZAxis), radio)
    resultado.append(circle.ToNurbsCurve())

# Asignar a salida
a = resultado
```

### Acceso a Rhino doc desde GH

```python
import Rhino
import scriptcontext as sc

# En Grasshopper, el contexto es diferente
# Usar ghenv para acceder al componente
ghenv.Component.Name = "Mi Script"
ghenv.Component.NickName = "MS"
```

### Manejo de datos en GH

```python
# Convertir DataTree a lista de listas
import ghpythonlib.treehelpers as th

lista_de_listas = th.tree_to_list(IN_tree)
tree_de_salida = th.list_to_tree(lista_de_listas)
```

## Componente Grasshopper en C# (.NET)

### Estructura mínima de plugin

```csharp
using Grasshopper.Kernel;
using Rhino.Geometry;

public class MiComponente : GH_Component
{
    public MiComponente()
        : base("Mi Componente", "MiComp",
               "Descripción", "Categoría", "Subcategoría") { }

    protected override void RegisterInputParams(GH_InputParamManager pManager)
    {
        pManager.AddPointParameter("Punto", "P", "Punto de entrada", GH_ParamAccess.item);
        pManager.AddNumberParameter("Radio", "R", "Radio de la esfera", GH_ParamAccess.item, 1.0);
    }

    protected override void RegisterOutputParams(GH_OutputParamManager pManager)
    {
        pManager.AddBrepParameter("Sólido", "S", "Esfera generada", GH_ParamAccess.item);
    }

    protected override void SolveInstance(IGH_DataAccess DA)
    {
        Point3d pt = Point3d.Origin;
        double radio = 1.0;
        if (!DA.GetData(0, ref pt)) return;
        DA.GetData(1, ref radio);

        var sphere = new Sphere(pt, radio);
        DA.SetData(0, sphere.ToBrep());
    }

    public override Guid ComponentGuid => new Guid("xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx");
}
```

## Transformaciones geométricas

```python
import Rhino.Geometry as rg

# Transformación de traslación
xform_move = rg.Transform.Translation(rg.Vector3d(10, 0, 0))
brep.Transform(xform_move)

# Rotación (ángulo en radianes)
import math
xform_rot = rg.Transform.Rotation(math.pi / 4, rg.Vector3d.ZAxis, rg.Point3d.Origin)
brep.Transform(xform_rot)

# Escala uniforme
xform_scale = rg.Transform.Scale(rg.Point3d.Origin, 2.0)
brep.Transform(xform_scale)

# Proyección a plano
xform_proj = rg.Transform.PlanarProjection(rg.Plane.WorldXY)
```

## Análisis de superficies

```python
# Punto en superficie por parámetros UV
u, v = 0.5, 0.5
pt = surface.PointAt(u, v)
normal = surface.NormalAt(u, v)

# Closest point
ok, u, v = surface.ClosestPoint(query_point)
if ok:
    closest = surface.PointAt(u, v)

# Rango de dominio
u_domain = surface.Domain(0)  # u
v_domain = surface.Domain(1)  # v
```

## Herramientas de fabricación digital desde Rhino/GH

| Flujo | Herramienta | Descripción |
|-------|-------------|-------------|
| CNC | RhinoCAM, VisualCAM | Generación de toolpaths para fresado |
| Corte láser | Nesting (plugins) | Optimización de piezas planas |
| Robot industrial | KukaPRC, Robots (GH) | Programación de robots desde GH |
| Impresión 3D | Slicer4Rhino, Grasshopper | Preparación de geometría |
| Panelización | Lunchbox, Paneling Tools | División de superficies en paneles |

## Plugins esenciales para AEC

| Plugin | Función |
|--------|---------|
| **Ladybug Tools** | Análisis climático, radiación solar, viento |
| **Karamba3D** | Análisis estructural (FEM) |
| **Kangaroo** | Simulación física, optimización de formas |
| **Human** | Interfaz, display avanzado, manejo de datos |
| **Pufferfish** | Morphing, transiciones, blending de geometría |
| **Lunchbox** | Panelización, estructuras, grillas |
| **Clipper** | Operaciones booleanas 2D de polilíneas |

## Errores comunes

| Error | Causa | Solución |
|-------|-------|----------|
| `None` en salida GH | Operación geométrica fallida | Verificar tolerancias y validez de geometría |
| Componente naranja | Advertencia no fatal | Revisar mensaje; puede continuar |
| Componente rojo | Error fatal | Revisar entradas y typos en Python |
| `IsValid = False` en Brep | Sólido mal construido | Usar `Brep.IsValid` + `Brep.Repair()` |

## Links oficiales

- [McNeel Developer Docs](https://developer.rhino3d.com/) — RhinoCommon, Grasshopper SDK, guías
- [RhinoCommon API](https://developer.rhino3d.com/api/rhinocommon/) — Referencia completa de clases
- [Grasshopper Developer](https://developer.rhino3d.com/guides/grasshopper/) — Guías para componentes
- [RhinoPython Guides](https://developer.rhino3d.com/guides/rhinopython/) — Python en Rhino
- [Food4Rhino](https://www.food4rhino.com/) — Repositorio de plugins
