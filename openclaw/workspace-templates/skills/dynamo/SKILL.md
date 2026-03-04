---
name: dynamo
description: >-
  Programación visual con Dynamo BIM: nodos, grafos, Python Script, Zero-Touch,
  integración con Revit y best practices. Use when "Dynamo", "grafo Dynamo",
  "nodo Dynamo", "Python Dynamo", "automatizar con Dynamo", "Dynamo Revit",
  "script visual BIM", "Zero-Touch Dynamo".
metadata:
  openclaw:
    emoji: "\U0001F300"
    requires:
      env: []
---

# Dynamo Skill — Programación Visual BIM

Rick usa este skill para asistir con grafos de Dynamo, nodos personalizados, scripting Python dentro de Dynamo y la integración con Revit.

## Conceptos clave

| Concepto | Descripción |
|----------|-------------|
| **Grafo (.dyn)** | Archivo JSON que describe el flujo de nodos |
| **Nodo** | Unidad de cómputo con entradas y salidas |
| **Wire (hilo)** | Conexión entre salida de un nodo y entrada de otro |
| **Lista** | Estructura de datos fundamental; casi todo es lista |
| **Lacing** | Control de cómo se combinan listas (Shortest, Longest, Cross Product) |
| **Design Script** | Lenguaje textual alternativo a nodos visuales |
| **Zero-Touch** | Nodos creados desde C# sin configuración extra |

## Estructura del grafo

### Organización recomendada (izquierda a derecha)

```
[Inputs] → [Proceso: Recolectar] → [Proceso: Transformar] → [Outputs / Watch]
```

- Usar **Group** (Ctrl+G) para agrupar nodos por función.
- Agregar **Note** con descripción al inicio del grafo.
- Usar **Input nodes** (Integer Slider, Number Slider, String, Boolean) para parámetros configurables.

## Nodos esenciales de Revit

### Colección de elementos

```
All Elements of Category    → Colecta por categoría (Walls, Doors, etc.)
All Elements of Type        → Por tipo específico
Select Model Element        → Selección manual interactiva
Element.GetParameterValueByName → Leer parámetro por nombre
```

### Modificación de parámetros

```
Element.SetParameterValueByName(element, paramName, value)
```

Requiere que Dynamo esté en modo **Automatic** o ejecutar manualmente.

### Geometría

```
BoundingBox.ByGeometry    → BBox de elemento
Element.Faces             → Caras de sólido
Geometry.Translate        → Trasladar geometría
Surface.PointAtParameter  → Punto en superficie por UV
```

## Python Script en Dynamo

### Estructura base del nodo Python

```python
# Python 3 (Dynamo 2.13+) — CPython
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

# Entradas: siempre IN[0], IN[1], ...
elementos = IN[0]  # puede ser lista o valor único

# Procesar
resultados = []
TransactionManager.Instance.EnsureInTransaction(doc)

for elem in elementos:
    # Obtener elemento nativo de Revit
    elem_native = elem.InternalElement
    param = elem_native.LookupParameter("Comentarios")
    if param:
        param.Set("Procesado por Dynamo")
    resultados.append(elem_native.Id.IntegerValue)

TransactionManager.Instance.TransactionTaskDone()

# Salida: siempre asignar a OUT
OUT = resultados
```

### Importar módulos adicionales

```python
import sys
sys.path.append(r"C:\Users\usuario\AppData\Roaming\Python\Python310\site-packages")
import pandas as pd  # si está instalado
```

### Manejo de listas aplanadas

```python
# Aplanar lista de listas
def flatten(lst):
    result = []
    for item in lst:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result

elementos_flat = flatten(IN[0]) if isinstance(IN[0], list) else [IN[0]]
```

## Lacing — Control de listas

| Lacing | Comportamiento |
|--------|---------------|
| **Shortest** | Itera hasta que la lista más corta se agota |
| **Longest** | Repite el último elemento de listas más cortas |
| **Cross Product** | Combinación de todos con todos (n × m) |

Se configura haciendo clic derecho en el nodo → Lacing.

## Design Script (lenguaje textual)

```
// Crear rango
nums = 0..10..1;          // [0, 1, 2, ..., 10]
odds = 1..10..#5;         // 5 valores entre 1 y 10

// Operaciones en lista
doubled = nums * 2;

// Definir función
def sumar(a, b) { return = a + b; }
resultado = sumar(3, 4);  // 7

// Replication guide (equivalente a lacing)
resultado = suma(lista1<1>, lista2<2>);  // Cross product
```

## Zero-Touch — Nodo personalizado en C#

### Estructura mínima

```csharp
using Autodesk.DesignScript.Runtime;

namespace MiNamespace
{
    public static class MiNodo
    {
        /// <summary>Descripción del nodo.</summary>
        /// <param name="valor">Descripción input.</param>
        /// <returns name="resultado">Descripción output.</returns>
        public static double Duplicar(double valor)
        {
            return valor * 2;
        }
    }
}
```

Compilar como DLL y colocar en `%AppData%\Dynamo\Dynamo Revit\<version>\packages\MiPaquete\bin\`.

## Paquetes útiles para AEC

| Paquete | Función principal |
|---------|------------------|
| **Clockwork** | Nodos Revit extendidos (parámetros, vistas, sheets) |
| **Rhythm** | Automatización de tareas Revit complejas |
| **archilab** | Herramientas para Revit y Dynamo |
| **Data-Shapes** | UI personalizada en grafos (formularios, selección) |
| **MEPover** | Nodos para sistemas MEP |
| **Orchid** | Manejo de familias y parámetros compartidos |

## Buenas prácticas

- **Siempre** usar `TransactionManager` en Python al modificar el modelo.
- Agrupar operaciones en pocas transacciones para mejor rendimiento.
- Usar **Watch** para inspeccionar listas antes de modificar elementos.
- Usar **Python Script** solo cuando los nodos visuales no sean suficientes.
- Guardar el grafo en formato `.dyn` y versionar con Git.
- Documentar con **Notes** y **Groups** el propósito de cada sección.
- Evitar grafos con más de 100 nodos; dividir en sub-grafos con `Custom Nodes`.

## Errores comunes

| Error | Causa | Solución |
|-------|-------|----------|
| `Warning: Null value` | Elemento no encontrado o parámetro vacío | Validar con `== null` antes de procesar |
| Grafo no actualiza | Modo Manual activo | Cambiar a Automatic o presionar Run |
| `TransactionException` | Transaction anidada o no cerrada | Usar `EnsureInTransaction` y `TaskDone` |
| Lista plana cuando se espera lista de listas | Lacing incorrecto | Ajustar lacing o usar `List.Create` |

## Links oficiales

- [Dynamo Primer 2.0](https://primer2.dynamobim.org/) — Guía completa de aprendizaje
- [Dynamo Learn](https://dynamobim.org/learn/) — Recursos y tutoriales oficiales
- [Dynamo GitHub](https://github.com/DynamoDS/Dynamo) — Código fuente y issues
- [Zero-Touch Guide](https://primer2.dynamobim.org/6_custom_nodes_and_packages/6-3_packages) — Crear paquetes y nodos
