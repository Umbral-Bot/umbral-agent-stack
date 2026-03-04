---
name: navisworks
description: >-
  API de Autodesk Navisworks para clash detection, revisión de modelos federados,
  exportación NWC/NWD y automatización mediante APS o .NET SDK.
  Use when "Navisworks", "clash detection", "NWC", "NWD", "coordinación BIM",
  "detección de colisiones", "Navisworks API", "modelo federado",
  "Clash Detective", "TimeLiner", "NWF", "exportar NWC".
metadata:
  openclaw:
    emoji: "\U0001F50D"
    requires:
      env:
        - APS_CLIENT_ID
        - APS_CLIENT_SECRET
---

# Navisworks Skill — Clash Detection, Revisión y API

Rick usa este skill para asistir con Navisworks: clash detection automatizado, exportación de modelos, y scripting con la API .NET o APS.

## Formatos de archivo

| Formato | Descripción |
|---------|-------------|
| **NWD** | Navisworks Document — modelo publicado con toda la data |
| **NWC** | Navisworks Cache — generado automáticamente por CAD apps (Revit, AutoCAD) |
| **NWF** | Navisworks File — referencia archivos fuente (no embebe geometría) |

**Jerarquía:** NWF referencia NWC/NWD → federar modelos en NWF → publicar como NWD.

## Clash Detective — Conceptos clave

| Concepto | Descripción |
|----------|-------------|
| **Test** | Configuración de un clash: selección A vs B, tipo, tolerancia |
| **Clash** | Colisión individual detectada entre dos objetos |
| **Status** | New → Active → Reviewed → Approved → Resolved |
| **Grouping** | Agrupar clashes por tipo, nivel, disciplina |
| **Hard clash** | Intersección física de geometría |
| **Clearance clash** | Dentro de distancia mínima (buffer) |
| **Duplicate clash** | Clashes iguales detectados dos veces |

## API .NET — Modos de uso

| Modo | Descripción |
|------|-------------|
| **Plug-in** | DLL cargado dentro de Navisworks |
| **Automation** | Control de Navisworks desde app externa (COM/interop) |
| **Embedded Control** | Visor NWD integrado en app .NET |

### Plug-in básico

```csharp
using Autodesk.Navisworks.Api;
using Autodesk.Navisworks.Api.Plugins;

[Plugin("MyPlugin", "MYCO", DisplayName = "Mi Plugin")]
[AddInPlugin(AddInLocation.Export)]
public class MyPlugin : AddInPlugin
{
    public override int Execute(params string[] parameters)
    {
        // Documento activo
        Document doc = Application.ActiveDocument;
        
        // Árbol de modelo
        ModelItemCollection rootItems = doc.Models.RootItems;
        
        // Iteración sobre ítems
        foreach (ModelItem item in rootItems.DescendantsAndSelf)
        {
            Console.WriteLine(item.DisplayName);
        }
        
        return 0;
    }
}
```

### Automation — Abrir NWD y exportar datos

```csharp
// Modo Automation (desde app externa)
using Autodesk.Navisworks.Api.Automation;

var app = new NavisworksApplication();
app.OpenFile(@"C:\models\federated.nwf");

Document doc = app.Document;

// Acceder a clash tests
var clashPlugin = doc.GetClash();
// Iterar tests y resultados...

app.Dispose();
```

### Clash Detection — Leer resultados via API

```csharp
// Requiere referencia a Autodesk.Navisworks.Api.Clash
using Autodesk.Navisworks.Api.Clash;

Document doc = Application.ActiveDocument;
ClashResultsData clashData = doc.GetClash().TestsData;

foreach (ClashTest test in clashData.Tests)
{
    Console.WriteLine($"Test: {test.DisplayName} | Clashes: {test.ClashResults.Count}");
    
    foreach (ClashResult result in test.ClashResults)
    {
        Console.WriteLine($"  Clash: {result.DisplayName} | Status: {result.Status}");
        Console.WriteLine($"  Item1: {result.CompositeItem1.DisplayName}");
        Console.WriteLine($"  Item2: {result.CompositeItem2.DisplayName}");
        Console.WriteLine($"  Punto: {result.Center}");
    }
}
```

## Exportar NWD con API (Navisworks 2026)

Navisworks 2026 introduce `NwdExportOptions` para control granular de exportación.

```csharp
using Autodesk.Navisworks.Api;

Document doc = Application.ActiveDocument;

// Opciones de exportación NWD
var exportOpts = new NwdExportOptions
{
    ExcludeHidden = true,           // No exportar objetos ocultos
    EmbedTextures = true,           // Incrustar texturas
    EmbedDatabase = false,          // No incrustar propiedades (IP)
    EmbedReCapData = false
};

// Exportar
doc.SaveFile(@"C:\output\model.nwd", exportOpts);
```

## Exportar NWC desde Revit

El plugin de Navisworks para Revit genera NWC directamente.

```python
# pyRevit script
from Autodesk.Revit.DB import NavisworksExportOptions, NavisworksExportScope
from pyrevit import revit

doc = revit.doc
export_path = r"C:\exports"

opts = NavisworksExportOptions()
opts.ExportScope = NavisworksExportScope.Model
opts.Coordinates = NavisworksCoordinates.Shared
opts.ExportElementIds = True
opts.ExportRoomAsAttribute = True

doc.Export(export_path, "modelo.nwc", opts)
```

## Propiedades de modelo — Lectura

```csharp
// Acceder a propiedades de un ModelItem
foreach (ModelItem item in rootItems.DescendantsAndSelf)
{
    foreach (PropertyCategory cat in item.PropertyCategories)
    {
        foreach (DataProperty prop in cat.Properties)
        {
            var val = prop.Value;
            Console.WriteLine($"{cat.DisplayName} | {prop.DisplayName}: {val}");
        }
    }
}
```

## TimeLiner — Simulación 4D

```csharp
// Acceder a TimeLiner (simulación de construcción)
Document doc = Application.ActiveDocument;
TimelinerData timeliner = doc.GetTimeliner().SimulationData;

foreach (TimelinerTask task in timeliner.Tasks)
{
    Console.WriteLine($"Tarea: {task.DisplayName}");
    Console.WriteLine($"  Inicio: {task.PlannedStartDate} | Fin: {task.PlannedEndDate}");
    Console.WriteLine($"  Estado: {task.Status}");
}
```

## Workflow típico BIM con Navisworks

1. **Exportar NWC** desde cada disciplina (Revit, Autocad MEP, etc.)
2. **Federar** en NWF (agregar archivos NWC al modelo maestro)
3. **Configurar Clash Tests** (Arq vs Estructura, Estructura vs MEP, etc.)
4. **Ejecutar tests** y exportar reporte HTML/XML
5. **Distribuir** reporte a equipos en ACC Issues
6. **Actualizar NWC** → re-ejecutar tests → verificar resolución

## Reporte de clashes — Exportación

Navisworks permite exportar reportes en:
- **HTML** (más usado para distribución)
- **XML** (programático, parseable)
- **CSV** (para Excel/Power BI)

```csharp
// Exportar reporte XML de clash test
ClashTest test = clashData.Tests[0];
test.ExportClashReport(@"C:\reports\clash_report.xml",
                       ClashReportFormat.Xml);
```

## Ejemplos de uso con Rick

- **Rick: "Automatizá la exportación de todos los modelos Revit a NWC"** → pyRevit batch script con NavisworksExportOptions.
- **Rick: "Leé el reporte XML de Navisworks y convertilo a tabla Excel"** → Python `xml.etree.ElementTree` + `openpyxl`.
- **Rick: "Cuántos clashes activos hay en el modelo federado?"** → API .NET: `ClashTest.ClashResults.Count(r => r.Status == ClashResultStatus.Active)`.
- **Rick: "Cómo configuro un clash test entre estructura y MEP vía API?"** → `ClashTest.AddSelectionA/B` con `ModelItemCollection`.

## Recursos oficiales

- APS Navisworks Overview: https://aps.autodesk.com/developer/overview/navisworks
- Navisworks 2026 SDK: descargable desde el portal APS
- Navisworks API Forum: https://forums.autodesk.com/t5/navisworks-api-forum/
- Developer Blog (2026 NwdExportOptions): https://blog.autodesk.io/navisworks-api-introducing-nwdexportoptions-in-navisworks-2026/
- Clash Detective Help: https://help.autodesk.com/view/NAV/2026/

## Notas

- El SDK de Navisworks se instala por defecto con Navisworks Manage y Simulate.
- Para Automation mode, Navisworks Manage debe estar instalado en la máquina.
- NWF referencia archivos relativos; al mover el proyecto, actualizar las rutas.
- Navisworks 2026 agrega `NwdExportOptions` como nueva API para control de exportación.
- Para APS/cloud: usar `APS_CLIENT_ID` y `APS_CLIENT_SECRET` para autenticación.
