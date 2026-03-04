---
name: revit
description: >-
  Scripting, automatización y acceso a la API de Autodesk Revit mediante .NET,
  pyRevit y Autodesk Platform Services (APS) Revit Automation API.
  Use when "Revit API", "automatizar Revit", "pyRevit", "script Revit",
  "exportar RVT", "familia Revit", "parámetros Revit", "APS Revit",
  "modelo Revit", "elementos Revit Python".
metadata:
  openclaw:
    emoji: "\U0001F3DB"
    requires:
      env:
        - APS_CLIENT_ID
        - APS_CLIENT_SECRET
---

# Revit Skill — API, pyRevit y APS Automation

Rick usa este skill para asistir con scripting en Revit, automatización de workflows BIM y acceso a la Revit Automation API de Autodesk Platform Services.

## Modalidades de acceso

| Modalidad | Lenguaje | Contexto |
|-----------|----------|---------|
| **Revit API (.NET)** | C# / VB.NET | Addin dentro de Revit |
| **pyRevit** | Python (IronPython/CPython) | Script en Revit desktop |
| **APS Revit Automation API** | REST / Python SDK | Cloud sin instalación Revit |
| **Dynamo** | DesignScript / Python | Visual programming en Revit |

## Revit API (.NET) — Conceptos clave

### Objetos principales

| Objeto | Descripción |
|--------|-------------|
| `UIApplication` | Punto de entrada. Acceso a UI y sesión activa |
| `Application` | Motor Revit. Acceso a documentos y config |
| `Document` | Archivo RVT abierto. Contiene todos los elementos |
| `Element` | Unidad base. Paredes, puertas, vistas, familias, etc. |
| `FilteredElementCollector` | Query sobre elementos del modelo |
| `Transaction` | Agrupa cambios al modelo (obligatorio para writes) |

### Patrón básico de script

```csharp
// C# Addin
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
{
    Document doc = commandData.Application.ActiveUIDocument.Document;
    
    using (Transaction tx = new Transaction(doc, "Nombre operación"))
    {
        tx.Start();
        // Modificaciones al modelo aquí
        tx.Commit();
    }
    return Result.Succeeded;
}
```

### pyRevit — Python en Revit

pyRevit permite ejecutar Python directamente en Revit sin compilar un addin.

```python
# pyRevit script
from pyrevit import revit, DB, forms

doc = revit.doc
uidoc = revit.uidoc

# Colector de elementos
walls = DB.FilteredElementCollector(doc)\
          .OfClass(DB.Wall)\
          .WhereElementIsNotElementType()\
          .ToElements()

for wall in walls:
    param = wall.get_Parameter(DB.BuiltInParameter.WALL_ATTR_WIDTH_PARAM)
    print(f"Muro: {wall.Id} | Ancho: {param.AsDouble():.3f} ft")
```

### FilteredElementCollector — Patrones comunes

```python
# Todas las puertas (instancias)
doors = DB.FilteredElementCollector(doc)\
          .OfCategory(DB.BuiltInCategory.OST_Doors)\
          .WhereElementIsNotElementType()\
          .ToElements()

# Todos los tipos de familia
family_symbols = DB.FilteredElementCollector(doc)\
                   .OfClass(DB.FamilySymbol)\
                   .ToElements()

# Elementos en vista activa
active_view = uidoc.ActiveView
elems_in_view = DB.FilteredElementCollector(doc, active_view.Id)\
                  .WhereElementIsNotElementType()\
                  .ToElements()
```

### Parámetros — Lectura y escritura

```python
# Leer parámetro por nombre
wall = walls[0]
mark = wall.LookupParameter("Mark")
if mark:
    print(mark.AsString())

# Escribir parámetro (dentro de Transaction)
with revit.Transaction("Set Mark"):
    mark.Set("Muro-001")

# Parámetros predefinidos (BuiltInParameter)
level_id = wall.get_Parameter(DB.BuiltInParameter.WALL_BASE_CONSTRAINT).AsElementId()
level = doc.GetElement(level_id)
print(f"Nivel base: {level.Name}")
```

## APS Revit Automation API — Cloud

La Revit Automation API permite procesar archivos RVT en la nube sin Revit instalado.

### Autenticación (2-legged OAuth)

```python
import requests

def get_token(client_id: str, client_secret: str) -> str:
    resp = requests.post(
        "https://developer.api.autodesk.com/authentication/v2/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
            "scope": "data:read data:write"
        }
    )
    return resp.json()["access_token"]
```

### Flujo típico: Extraer datos de RVT

1. Subir RVT a OSS (Object Storage Service)
2. Crear Activity con el Appbundle de Revit Engine
3. Enviar WorkItem con parámetros
4. Descargar resultado (JSON, IFC, NWC, etc.)

```python
# Crear WorkItem (Design Automation v3)
workitem = {
    "activityId": "revit.ExtractData+prod",
    "arguments": {
        "rvtFile": {"url": f"urn:adsk.objects:os.object:{bucket}/{file_key}"},
        "result": {"url": f"urn:adsk.objects:os.object:{bucket}/output.json",
                   "verb": "put"}
    }
}
resp = requests.post(
    "https://developer.api.autodesk.com/da/us-east/v3/workitems",
    json=workitem,
    headers={"Authorization": f"Bearer {token}"}
)
```

## Exportación de modelos

| Formato | Uso | API |
|---------|-----|-----|
| NWC | Navisworks clash detection | `NavisworksExportOptions` |
| IFC | Interoperabilidad abierta | `IFCExportOptions` |
| DWG | AutoCAD | `DWGExportOptions` |
| PDF | Documentación | `PDFExportOptions` (Revit 2022+) |

```python
# Exportar a NWC (pyRevit)
from Autodesk.Revit.DB import NavisworksExportOptions

opts = NavisworksExportOptions()
opts.ExportScope = DB.NavisworksExportScope.Model
doc.Export(export_path, "model.nwc", opts)
```

## Ejemplos de uso con Rick

- **Rick: "Listame todas las puertas con su nivel y marca"** → Script FilteredElementCollector con OST_Doors, lee Level y Mark.
- **Rick: "Exporta el modelo a NWC automáticamente"** → pyRevit script con NavisworksExportOptions.
- **Rick: "Crea un WorkItem APS para extraer datos del RVT en la nube"** → Usa APS Design Automation v3 REST API.
- **Rick: "Genera un report de parámetros de muros en Excel"** → Colector de Wall + pandas/openpyxl.

## Recursos oficiales

- API Reference 2026: https://www.revitapidocs.com/2026/
- APS Developer Portal: https://aps.autodesk.com/developer/overview/revit
- APS Design Automation: https://aps.autodesk.com/apis-and-services/revit-automation-api
- pyRevit: https://github.com/pyrevitlabs/pyRevit
- The Building Coder Blog: https://thebuildingcoder.typepad.com/

## Notas

- La Revit API nativa es .NET; Python se accede vía pyRevit (IronPython) o scripts en Dynamo.
- Todos los cambios al modelo requieren una `Transaction` activa.
- APS Design Automation necesita `APS_CLIENT_ID` y `APS_CLIENT_SECRET` con scopes `data:read data:write`.
- El SDK de Revit 2026 está disponible en el portal APS para descarga.
