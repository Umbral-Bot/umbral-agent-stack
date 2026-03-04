---
name: power-bi
description: >-
  Design Power BI reports and semantic models using DAX measures, Power Query (M)
  transformations, and REST API integrations for data analytics and business intelligence.
  Use when "power bi dax", "create measure power bi", "power query transform",
  "power bi report", "calculate dax", "power bi dataset", "time intelligence dax",
  "power bi embedded", "refresh dataset power bi", "M language power query".
metadata:
  openclaw:
    emoji: "\U0001F4CA"
    requires:
      env: []
---

# Power BI Skill

Rick puede asistir en el desarrollo de modelos semánticos, medidas DAX, transformaciones Power Query (M) y uso de la API REST de Power BI.

Documentación oficial: https://learn.microsoft.com/power-bi/

---

## Arquitectura de Power BI

```
Fuentes de datos (SQL, Excel, SharePoint, API, Dataverse…)
         ↓  Power Query (M) — ETL
    Modelo semántico (tablas, relaciones, jerarquías)
         ↓  DAX — medidas y columnas calculadas
    Visualizaciones (reportes, dashboards)
         ↓
    Power BI Service (publicación, actualización, compartir)
         ↓  API REST / Embedded
    Apps, portales, notificaciones
```

---

## DAX — Data Analysis Expressions

### Medidas vs Columnas calculadas

| Tipo | Se evalúa en | Se almacena | Uso |
|------|-------------|-------------|-----|
| **Medida** | Tiempo de consulta (contexto de filtro) | No (dinámica) | KPIs, totales, % |
| **Columna calculada** | Tiempo de carga (fila por fila) | Sí (en modelo) | Clasificaciones, textos, flags |

### Funciones de agregación

```dax
TotalVentas = SUM(Ventas[Monto])
VentasPromedio = AVERAGE(Ventas[Monto])
CountOrdenes = COUNT(Ventas[OrderID])
CountDistinct = DISTINCTCOUNT(Ventas[ClienteID])
MaxVenta = MAX(Ventas[Monto])
MinVenta = MIN(Ventas[Monto])
```

### CALCULATE — El corazón de DAX

`CALCULATE` modifica el contexto de filtro:

```dax
VentasRegionNorte = CALCULATE(
    SUM(Ventas[Monto]),
    Clientes[Region] = "Norte"
)

VentasAño2025 = CALCULATE(
    SUM(Ventas[Monto]),
    Fechas[Año] = 2025
)

// Múltiples filtros (AND implícito)
VentasActivosNorte = CALCULATE(
    SUM(Ventas[Monto]),
    Clientes[Region] = "Norte",
    Productos[Activo] = TRUE()
)
```

### ALL / ALLEXCEPT — Remover filtros

```dax
// % sobre total ignorando todos los filtros
PorcentajeTotal = DIVIDE(
    SUM(Ventas[Monto]),
    CALCULATE(SUM(Ventas[Monto]), ALL(Ventas))
)

// % sobre total ignorando solo el filtro de Producto (manteniendo otros)
PorcentajePorCategoria = DIVIDE(
    SUM(Ventas[Monto]),
    CALCULATE(SUM(Ventas[Monto]), ALLEXCEPT(Ventas, Productos[Categoria]))
)
```

### Inteligencia de tiempo (Time Intelligence)

```dax
// Requiere tabla de fechas marcada como "fecha" con fechas continuas
VentasAñoAnterior = CALCULATE(
    SUM(Ventas[Monto]),
    SAMEPERIODLASTYEAR(Fechas[Fecha])
)

VentasYTD = TOTALYTD(SUM(Ventas[Monto]), Fechas[Fecha])
VentasQTD = TOTALQTD(SUM(Ventas[Monto]), Fechas[Fecha])
VentasMTD = TOTALMTD(SUM(Ventas[Monto]), Fechas[Fecha])

// YoY Growth
CrecimientoYoY = DIVIDE(
    [TotalVentas] - [VentasAñoAnterior],
    [VentasAñoAnterior]
)

// Acumulado móvil 12 meses
Ventas12M = CALCULATE(
    SUM(Ventas[Monto]),
    DATESINPERIOD(Fechas[Fecha], LASTDATE(Fechas[Fecha]), -12, MONTH)
)
```

### FILTER y contexto de iteración

```dax
// SUMX: itera fila por fila
MargenTotal = SUMX(
    Ventas,
    Ventas[Precio] * Ventas[Cantidad] - Ventas[Costo] * Ventas[Cantidad]
)

// FILTER con condición compleja
VentasGrandes = CALCULATE(
    SUM(Ventas[Monto]),
    FILTER(Ventas, Ventas[Monto] > 10000)
)

// COUNTROWS con FILTER
ClientesConVentas = COUNTROWS(
    FILTER(Clientes, CALCULATE(SUM(Ventas[Monto])) > 0)
)
```

### Relaciones y RELATED

```dax
// RELATED: traer valor de tabla relacionada (lado "1" de la relación)
ColCategoria = RELATED(Productos[Categoria])

// RELATEDTABLE: contar filas relacionadas
NumOrdenesPorCliente = COUNTROWS(RELATEDTABLE(Ordenes))

// USERELATIONSHIP: activar relación inactiva
VentasEnvio = CALCULATE(
    SUM(Ventas[Monto]),
    USERELATIONSHIP(Ventas[FechaEnvio], Fechas[Fecha])
)
```

### Variables en DAX (VAR / RETURN)
```dax
MargenConVar =
VAR TotalIngresos = SUM(Ventas[Monto])
VAR TotalCostos = SUM(Ventas[Costo])
VAR Margen = DIVIDE(TotalIngresos - TotalCostos, TotalIngresos)
RETURN
    FORMAT(Margen, "0.0%")
```

### Funciones de texto y lógica

```dax
// Texto
NombreCompleto = Empleados[Nombre] & " " & Empleados[Apellido]
Iniciales = LEFT(Empleados[Nombre], 1) & LEFT(Empleados[Apellido], 1)
FORMAT(Ventas[Monto], "$ #,##0")

// Lógica
Clasificacion =
    IF(Ventas[Monto] > 100000, "A",
       IF(Ventas[Monto] > 50000, "B", "C"))

// SWITCH (equivalente a CASE)
Categoria =
    SWITCH(Productos[Tipo],
        "Electrónica", "Tech",
        "Ropa", "Fashion",
        "Alimentos", "Food",
        "Otros"
    )
```

### Columnas calculadas (Calculated Columns)
A diferencia de las medidas, se calculan en tiempo de refresh:
```dax
-- En tabla Ventas
Categoria Precio =
IF(
    Ventas[Monto] > 1000, "Alto",
    IF(Ventas[Monto] > 500, "Medio", "Bajo")
)

## Power Query (M) — Transformaciones

Power Query usa el lenguaje M (funcional, sensible a mayúsculas):

### Estructura básica

```m
let
    Origen = Csv.Document(File.Contents("C:\ventas.csv"), [Delimiter=","]),
    EncabezadoPromovido = Table.PromoteHeaders(Origen, [PromoteAllScalars=true]),
    TiposCambiados = Table.TransformColumnTypes(EncabezadoPromovido, {
        {"Fecha", type date},
        {"Monto", type number},
        {"ID", Int64.Type}
    }),
    Filtrado = Table.SelectRows(TiposCambiados, each [Monto] > 0),
    Resultado = Filtrado
in
    Resultado
```

### Transformaciones comunes

```m
// Filtrar filas
Table.SelectRows(tabla, each [Status] = "Active")
Table.SelectRows(tabla, each [Fecha] >= #date(2025, 1, 1))

// Agregar columna calculada
Table.AddColumn(tabla, "Margen", each [Precio] - [Costo], type number)

// Transformar columna existente
Table.TransformColumns(tabla, {{"Nombre", Text.Upper, type text}})

// Renombrar columnas
Table.RenameColumns(tabla, {{"old_name", "NuevoNombre"}})

// Eliminar columnas
Table.RemoveColumns(tabla, {"ColSobrante1", "ColSobrante2"})

// Quitar duplicados
Table.Distinct(tabla, {"ClienteID"})

// Ordenar
Table.Sort(tabla, {{"Fecha", Order.Descending}})

// Agrupar y agregar
Table.Group(tabla, {"Region"}, {
    {"TotalVentas", each List.Sum([Monto]), type number},
    {"NumOrdenes", each Table.RowCount(_), type number}
})

// Join (Merge)
Table.NestedJoin(ventas, "ProductoID", productos, "ID", "ProductoDetalle", JoinKind.LeftOuter)
Table.ExpandTableColumn(tablaMerge, "ProductoDetalle", {"Nombre", "Categoria"})

// Columna condicional
Table.AddColumn(tabla, "Segmento", each
    if [Monto] > 100000 then "Premium"
    else if [Monto] > 50000 then "Standard"
    else "Basic"
)

// Dividir columna por delimitador
Table.SplitColumn(tabla, "NombreCompleto", Splitter.SplitTextByDelimiter(" ", QuoteStyle.Csv), {"Nombre", "Apellido"})

// Extraer texto
Table.TransformColumns(tabla, {{"Email", each Text.BeforeDelimiter(_, "@")}})
```

### Parámetros M

```m
// Definir parámetro en interfaz o en código
FechaInicio = #date(2025, 1, 1) meta [IsParameterQuery=true, Type="Date"]
```

### Conectar a API REST en Power Query
```m
let
    Url = "https://api.ejemplo.com/datos?page=1",
    Headers = [#"Authorization" = "Bearer TOKEN", #"Content-Type" = "application/json"],
    Respuesta = Web.Contents(Url, [Headers = Headers]),
    Json = Json.Document(Respuesta),
    Tabla = Table.FromList(Json[items], Splitter.SplitByNothing()),
    Expandida = Table.ExpandRecordColumn(Tabla, "Column1", {"id", "nombre", "valor"})
in
    Expandida
```

## Fuentes de datos compatibles

| Categoría | Ejemplos |
|-----------|----------|
| Archivos | Excel, CSV, JSON, XML, PDF, SharePoint Folder |
| Bases de datos | SQL Server, Azure SQL, PostgreSQL, MySQL, Oracle |
| Online Services | SharePoint, Dataverse, Dynamics 365, Salesforce |
| Azure | Azure Blob, Azure Data Lake, Synapse, Cosmos DB |
| APIs | OData, Web (REST), GraphQL (via Web) |
| Power Platform | Power BI Datasets, Dataflows, Dataverse |

## API REST de Power BI

### Autenticación

```python
# OAuth2 con service principal
import requests
token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
response = requests.post(token_url, data={
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scope": "https://analysis.windows.net/powerbi/api/.default"
})
access_token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {access_token}"}
```

### Endpoints clave

```
GET  /v1.0/myorg/groups                              # Listar workspaces
GET  /v1.0/myorg/groups/{groupId}/reports            # Reportes en workspace
GET  /v1.0/myorg/groups/{groupId}/datasets           # Datasets en workspace
POST /v1.0/myorg/groups/{groupId}/datasets/{id}/refreshes  # Disparar refresh
GET  /v1.0/myorg/groups/{groupId}/datasets/{id}/refreshes  # Estado del refresh
POST /v1.0/myorg/groups/{groupId}/datasets/{id}/rows  # Push data a streaming dataset
DELETE /v1.0/myorg/groups/{groupId}/datasets/{id}/rows # Limpiar streaming dataset
GET  /v1.0/myorg/groups/{groupId}/reports/{reportId}/pages  # Páginas del reporte
POST /v1.0/myorg/groups/{groupId}/reports/{reportId}/ExportTo  # Exportar reporte PDF/PPTX
```

---

## Modelado de datos — Mejores prácticas

### Tabla de fechas
```dax
// Crear con DAX
FechasTable = 
ADDCOLUMNS(
    CALENDAR(DATE(2020,1,1), DATE(2030,12,31)),
    "Año", YEAR([Date]),
    "Mes", MONTH([Date]),
    "NombreMes", FORMAT([Date], "MMMM"),
    "Trimestre", "Q" & QUARTER([Date]),
    "Semana", WEEKNUM([Date]),
    "DiaSemana", WEEKDAY([Date]),
    "EsFinDeSemana", WEEKDAY([Date], 2) >= 6
)
```

### Esquema estrella
- Una tabla de **hechos** (Ventas, Ordenes, Transacciones) en el centro.
- Tablas de **dimensiones** (Clientes, Productos, Fechas, Ubicaciones) alrededor.
- Relaciones de **muchos a uno** (muchos hechos → un registro de dimensión).
- Evitar relaciones muchos-a-muchos; usar tabla puente si es necesario.

## Errores frecuentes

| Error | Causa | Solución |
|-------|-------|----------|
| `A circular dependency was detected` | Medida o columna se referencia a sí misma | Revisar cadena de referencias DAX |
| `MdxScript error` | Filtro ambiguo en medida | Usar `KEEPFILTERS()` o revisar el contexto con `ALLSELECTED()` |
| `The column X of table Y was not found` | Nombre de columna incorrecto | Verificar nombre exacto (DAX es case-sensitive en columnas) |
| `Expression.Error: We couldn't convert X to Number` | Tipo de dato incorrecto en M | Agregar `Table.TransformColumnTypes` con el tipo correcto |
| `DataSource.Error` | Credenciales expiradas o fuente inaccesible | Re-autenticar en Power BI Service → Configuración del dataset |
| `Refresh failed: Privacy levels` | Combinación de fuentes sin permitir | En opciones de Power BI Desktop, deshabilitar niveles de privacidad o configurarlos |
| `Cannot load model` | Modelo demasiado grande para importación | Usar modo DirectQuery o Composite Model |
| `Time intelligence requires continuous date table` | Tabla fechas con huecos | Asegurar que la tabla de fechas cubra todas las fechas del rango de datos |

---

## Casos de uso típicos

- Dashboard ejecutivo de ventas con comparativo YoY y YTD por región y categoría.
- Modelo de análisis de cohortes de clientes (retención, churn).
- Reporte de KPIs de construcción (Speckle/Dalux → Power Query → Power BI).
- Actualización automática de dataset vía API REST desde Python/n8n/Power Automate.
- Embedding de reportes en portal web de cliente con Row-Level Security (RLS).
- Análisis de datos de Dataverse (model-driven apps + Power BI integrado).

## Documentación oficial

## Referencias

- Documentación oficial: https://learn.microsoft.com/power-bi/
- Referencia DAX: https://learn.microsoft.com/dax/dax-function-reference
- Power Query M: https://learn.microsoft.com/powerquery-m/
- Power BI REST API: https://learn.microsoft.com/rest/api/power-bi/
- Patrones DAX avanzados: https://www.daxpatterns.com/
