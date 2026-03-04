---
name: navisworks
description: >-
  Automatización de Autodesk Navisworks: clash detection, reportes, API .NET/COM,
  exportación NWC/NWD y coordinación BIM. Use when "Navisworks", "clash detection",
  "NWC", "NWD", "clash report", "Navisworks API", "coordinación Navisworks",
  "TimeLiner", "exportar NWC", "interference check".
metadata:
  openclaw:
    emoji: "\U0001F50D"
    requires:
      env: []
---

# Navisworks Skill — Clash Detection y API

Rick usa este skill para asistir con automatización de Navisworks, scripting con la API .NET/COM, configuración de clash detection y generación de reportes de coordinación BIM.

## Conceptos clave

| Término | Descripción |
|---------|-------------|
| **NWC** | Navisworks Cache — exportado desde Revit/Rhino; se actualiza automáticamente |
| **NWD** | Navisworks Document — archivo consolidado con modelos y resultados |
| **NWF** | Navisworks File — archivo de referencia que enlaza modelos externos |
| **Clash Detective** | Módulo de detección de interferencias entre modelos |
| **TimeLiner** | Módulo de simulación 4D (cronograma + modelo) |
| **Animator** | Módulo de animación de objetos del modelo |
| **Clash Test** | Una prueba de colisión entre dos grupos de selección |
| **Clash Result** | Resultado individual de colisión con estado, comentarios, imagen |

## Exportar NWC desde Revit

### Desde Revit (exportación manual)

1. Ir a **File → Export → NWC**
2. Configurar opciones:
   - **Coordinates:** Shared (para coordenadas compartidas entre disciplinas)
   - **Export Scope:** Entire Model o Current View
   - **Convert Element Properties:** Activado para exportar parámetros

### Exportar NWC con Revit API (automatizado)

```python
# IronPython en pyRevit o Dynamo
from Autodesk.Revit.DB import NavisworksExportOptions, NavisworksExportScope, Transaction
import clr
clr.AddReference('RevitAPI')

options = NavisworksExportOptions()
options.ExportScope = NavisworksExportScope.Model
options.Coordinates = NavisworksCoordinates.Shared
options.ConvertElementProperties = True
options.ExportLinks = False
options.ExportParts = True
options.DivideFileIntoLevels = False

doc.Export(r"C:\Coordinacion\NWC", "Estructura.nwc", options)
```

## Navisworks API (.NET / COM)

### Referencia de assemblies

```
Autodesk.Navisworks.Api.dll        — API principal
Autodesk.Navisworks.Clash.dll      — Clash Detective
Autodesk.Navisworks.Timeliner.dll  — TimeLiner
```

### Abrir un archivo NWD con la API

```csharp
using Autodesk.Navisworks.Api;
using Autodesk.Navisworks.Api.Application;

// Inicializar la aplicación
using (var nwApp = new Application())
{
    nwApp.OpenFile(@"C:\Coordinacion\modelo.nwd");
    Document doc = nwApp.ActiveDocument;

    // Acceder al modelo
    ModelItemCollection allItems = doc.Models.CreateCollectionFromRootItems();
    Console.WriteLine($"Items en modelo: {allItems.Count}");
}
```

### Clash Detective por API

```csharp
using Autodesk.Navisworks.Api.Clash;

ClashDetective clashDetective = doc.GetClash();

// Crear nueva prueba de clash
ClashTest test = clashDetective.Tests.Add();
test.Name = "Estructura vs MEP";
test.Type = ClashType.Hard;  // Hard, HardConservative, Clearance, Duplicate
test.Tolerance = 0.001;      // Tolerancia en metros

// Configurar selección A (ej: elementos de capa "Estructura")
// y selección B (ej: elementos de capa "MEP")
// ... (configuración por ModelItem selección)

// Ejecutar prueba
test.TestAgainstSelf = false;
clashDetective.RunTest(test);

// Leer resultados
foreach (ClashResult result in test.Children.OfType<ClashResult>())
{
    Console.WriteLine($"Clash: {result.DisplayName}, Status: {result.Status}");
    Console.WriteLine($"  Punto: {result.Center}");
    Console.WriteLine($"  Elem A: {result.CompositeItem1?.DisplayName}");
    Console.WriteLine($"  Elem B: {result.CompositeItem2?.DisplayName}");
}
```

### Exportar reporte HTML de clashes

```csharp
// Con API de reporte
ClashTest test = clashDetective.Tests["Estructura vs MEP"];
test.ExportReport(
    @"C:\Coordinacion\Reportes\clash_report.html",
    ClashReportFormat.HtmlTabular
);
```

## Clash Detection — Configuración recomendada

### Tipos de prueba

| Tipo | Uso |
|------|-----|
| **Hard** | Intersección geométrica real (más común) |
| **Hard Conservative** | Usa bounding box; menos preciso pero más rápido |
| **Clearance** | Distancia mínima entre objetos (ej: 50mm de holgura) |
| **Duplicate** | Detectar elementos duplicados |

### Flujo de trabajo estándar

1. **Exportar NWC** de cada disciplina (Estructura, Arquitectura, MEP, etc.)
2. **Crear NWF o NWD** adjuntando todos los NWC
3. **Configurar Clash Tests** por pares de disciplina:
   - Estructura vs. MEP (Mecánico, Eléctrico, Plomería)
   - Arquitectura vs. Estructura
   - MEP Mecánico vs. MEP Eléctrico
4. **Ejecutar todos los tests** (Run All Tests)
5. **Agrupar resultados** por zona o disciplina
6. **Exportar reporte** HTML/XML
7. **Asignar clashes** a responsables con comentarios y fecha límite
8. **Revisar en reunión BIM** semanal
9. **Marcar clashes resueltos** como Approved o Resolved

### Estados de un clash

| Estado | Significado |
|--------|-------------|
| **New** | Detectado por primera vez |
| **Active** | En revisión / pendiente de resolución |
| **Reviewed** | Revisado pero no resuelto |
| **Approved** | Aceptado como condición existente |
| **Resolved** | Corregido en el modelo fuente |

## TimeLiner — 4D BIM

```
1. Importar cronograma (CSV, Microsoft Project, Primavera P6)
2. Vincular tareas del cronograma con conjuntos de selección del modelo
3. Configurar tipo de tarea: Construction, Demolish, Temporary
4. Reproducir simulación 4D
5. Exportar video de simulación
```

### Estructura CSV para importar

```csv
Tarea,Inicio,Fin,Tipo
"Excavación",01/03/2025,15/03/2025,Construction
"Cimentación",16/03/2025,10/04/2025,Construction
"Estructura Nivel 1",11/04/2025,30/04/2025,Construction
```

## Scripts de automatización (COM desde Python)

```python
import win32com.client

# Abrir Navisworks via COM (requiere Navisworks instalado)
nw = win32com.client.Dispatch("Navisworks.Application.2025")
nw.Visible = True
nw.OpenFile(r"C:\Coordinacion\modelo.nwd")

doc = nw.ActiveDocument
clash = doc.GetClash()

# Ejecutar todos los tests
for test in clash.Tests:
    test.Run()
    print(f"Test: {test.Name} — {test.ClashResultCount} clashes")

nw.Quit()
```

## Errores comunes

| Error | Causa | Solución |
|-------|-------|----------|
| NWC desactualizado | Modelo Revit modificado después del export | Re-exportar NWC desde Revit |
| Clashes en coordenadas incorrectas | Coordenadas locales vs. compartidas | Usar **Shared Coordinates** en todos los NWC |
| Muchos falsos positivos | Tolerancia muy pequeña | Ajustar tolerancia a 0.01m–0.05m |
| Clash test no corre | Selección A o B vacía | Verificar que los conjuntos de selección tienen elementos |

## Links oficiales

- [APS Navisworks Overview](https://aps.autodesk.com/developer/overview/navisworks) — SDK y API docs
- [Navisworks Developer Guide](https://help.autodesk.com/view/NAV/2025/ENU/?guid=Nav_API_navisworks_api_html) — Referencia completa
- [Navisworks Help](https://help.autodesk.com/view/NAV/2025/ENU/) — Guía de usuario oficial
