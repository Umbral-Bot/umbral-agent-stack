---
name: dynamo
description: >-
  Programación visual y scripting en Dynamo BIM: nodos, Python, DesignScript,
  automatización de Revit y best practices de scripting paramétrico.
  Use when "Dynamo", "nodo Dynamo", "Python Dynamo", "script Dynamo",
  "programación visual BIM", "automatizar con Dynamo", "Dynamo Revit",
  "DesignScript", "parámetro Dynamo", "Dynamo player".
metadata:
  openclaw:
    emoji: "\U0001F300"
    requires:
      env: []
---

# Dynamo Skill — Programación Visual BIM

Rick usa este skill para asistir con programación visual en Dynamo, scripting Python dentro de nodos, y automatización de Revit mediante flujos Dynamo.

## Arquitectura de Dynamo

| Componente | Función |
|------------|---------|
| **Nodos** | Unidades de operación con inputs/outputs |
| **Wires** | Conexiones de datos entre nodos |
| **Code Block** | Expresiones DesignScript inline |
| **Python Node** | Script Python dentro del grafo |
| **Custom Node** | Agrupación reutilizable de nodos |
| **Dynamo Player** | Ejecución sin abrir el editor Dynamo |

## Lenguajes disponibles

| Lenguaje | Uso |
|----------|-----|
| **DesignScript** | Nodos nativos y Code Blocks |
| **Python 3** | Python Node (IronPython en Dynamo <3.x, CPython en 3.x) |

## Python Node — Estructura base

```python
# IN[0], IN[1]... son los inputs conectados al nodo
input_data = IN[0]
multiplier = IN[1]

# Procesamiento
result = []
for item in input_data:
    result.append(item * multiplier)

# OUT es el output del nodo
OUT = result
```

### Imports comunes

```python
# Acceso a la API de Revit
import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitServices")
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager
from Autodesk.Revit.DB import *

# Documento activo
doc = DocumentManager.Instance.CurrentDBDocument

# Geometría de ProtoGeometry
clr.AddReference("ProtoGeometry")
from Autodesk.DesignScript.Geometry import *

# Operaciones de lista
import DSCore
from DSCore import List as DSList
```

### Modificar el modelo (Transaction en Dynamo)

```python
import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitServices")
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager
from Autodesk.Revit.DB import *

doc = DocumentManager.Instance.CurrentDBDocument
elements = IN[0]  # Elementos Revit pasados desde nodo Select

TransactionManager.Instance.EnsureInTransaction(doc)

results = []
for elem in elements:
    param = elem.LookupParameter("Comments")
    if param:
        param.Set("Revisado por Dynamo")
        results.append(elem.Id.IntegerValue)

TransactionManager.Instance.TransactionTaskDone()
OUT = results
```

## DesignScript — Code Block

```
// Rango numérico
0..10..2;            // [0, 2, 4, 6, 8, 10]

// Lista de puntos
pts = Point.ByCoordinates(0..5, 0, 0);

// Replicación (lacing)
Line.ByStartPointEndPoint(pts<1>, pts<2>);

// Función definida en Code Block
def scale(val, factor) { return val * factor; };
scale(IN[0], 2.5);
```

## Bibliotecas clave

| Biblioteca | Import | Contenido |
|------------|--------|-----------|
| ProtoGeometry | `Autodesk.DesignScript.Geometry` | Point, Line, Surface, Solid, Arc, NurbsCurve |
| DSCoreNodes | `DSCore` | Color, DateTime, List, Math, String |
| DSOffice | `DSOffice` | Lectura/escritura Excel |
| Revit API | `Autodesk.Revit.DB` | Toda la API de Revit |
| RevitServices | `RevitServices` | DocumentManager, TransactionManager |

## Patrones comunes

### Seleccionar elementos por categoría y filtrar

```python
import clr
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory

doc = IN[0]  # Dynamo puede pasar el doc como input

walls = FilteredElementCollector(doc)\
          .OfCategory(BuiltInCategory.OST_Walls)\
          .WhereElementIsNotElementType()\
          .ToElements()

# Filtrar muros con ancho > 0.3m (convertido a feet)
threshold = 0.3 / 0.3048
thick_walls = [w for w in walls
               if w.Width > threshold]

OUT = thick_walls
```

### Leer y escribir parámetros en batch

```python
# IN[0]: lista de elementos, IN[1]: nombre param, IN[2]: valor
elements = IN[0]
param_name = IN[1]
new_value = IN[2]

clr.AddReference("RevitServices")
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager

doc = DocumentManager.Instance.CurrentDBDocument
TransactionManager.Instance.EnsureInTransaction(doc)

for elem in elements:
    p = elem.LookupParameter(param_name)
    if p and not p.IsReadOnly:
        p.Set(new_value)

TransactionManager.Instance.TransactionTaskDone()
OUT = [e.Id.IntegerValue for e in elements]
```

## Best Practices

### Cuándo usar Python en lugar de nodos visuales

- Iteraciones con lógica condicional compleja
- Recursión o bucles anidados
- Acceso a bibliotecas externas (pandas, openpyxl)
- Operaciones batch sobre cientos de elementos
- Validaciones con múltiples condiciones

### Naming conventions

```python
# Bueno: nombre descriptivo con tipo
wall_elements = IN[0]
param_name_str = IN[1]

# Evitar: nombres crípticos
x = IN[0]
p = IN[1]

# Aliases para imports largos
from Autodesk.Revit.DB import BuiltInParameter as BIP
from Autodesk.Revit.DB import BuiltInCategory as BIC
```

### Gestión de memoria (ProtoGeometry)

```python
# Los objetos de ProtoGeometry son "unmanaged"
# Usar Dispose() cuando sea posible
pt = Point.ByCoordinates(0, 0, 0)
# ... usar pt ...
pt.Dispose()

# O usar with statement si el objeto lo soporta
```

## Dynamo Player

Permite ejecutar scripts sin abrir el editor. Rick puede:
1. Abrir Dynamo Player desde Revit ribbon → Manage → Visual Programming
2. Seleccionar script `.dyn`
3. Completar inputs expuestos (IsInput=true)
4. Hacer clic en Run

Para exponer un input: clic derecho en nodo → "Is Input".

## Ejemplos de uso con Rick

- **Rick: "Numerá todas las puertas secuencialmente por nivel"** → Python Node con FilteredElementCollector + sort por nivel + set Mark.
- **Rick: "Generá una grilla de puntos cada 3m en X e Y"** → Code Block con `0..width..3` y `Point.ByCoordinates`.
- **Rick: "Leé una planilla Excel y actualizá parámetros en Revit"** → DSOffice.Excel.ReadFromFile + Python Node con LookupParameter.
- **Rick: "Creá un script Dynamo para exportar datos de habitaciones a CSV"** → FilteredElementCollector OST_Rooms + Python con csv module.

## Recursos oficiales

- Dynamo Primer v2: https://primer2.dynamobim.org/
- Dynamo Primer v1 (Python): https://primer.dynamobim.org/10_Custom-Nodes/10-4_Python.html
- Scripting Strategies: https://primer.dynamobim.org/13_Best-Practice/13-1_Scripting-Strategies.html
- Dynamo GitHub: https://github.com/DynamoDS/Dynamo
- Dynamo Forum: https://forum.dynamobim.com/

## Notas

- Dynamo Sandbox es la versión standalone (sin Revit); Dynamo for Revit se abre desde dentro de Revit.
- Dynamo 3.x usa CPython 3.x (nodo Python 3); versiones anteriores usaban IronPython 2.7.
- Los grafos Dynamo se guardan como `.dyn` (JSON internamente).
- ProtoGeometry crea objetos unmanaged: liberarlos con `Dispose()` en scripts pesados.
