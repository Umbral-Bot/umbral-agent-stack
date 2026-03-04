---
name: power-bi
description: >-
  Crear reportes y dashboards analíticos con Microsoft Power BI usando DAX, Power Query (M)
  y visualizaciones. Conectar fuentes de datos, modelar relaciones y publicar en el servicio Power BI.
  Use when "power bi report", "dax formula", "power query", "dashboard power bi",
  "medida calculada", "calculated measure", "power bi dataset", "modelado datos power bi",
  "visual power bi", "power bi service", "refresh power bi", "kpi power bi",
  "relaciones power bi", "slicer", "tabla dinámica power bi".
metadata:
  openclaw:
    emoji: "\U0001F4CA"
    requires:
      env: []
---

# Power BI Skill

Rick puede asistir en la creación de modelos de datos, medidas DAX, transformaciones Power Query y reportes en Power BI Desktop y Power BI Service.

## Arquitectura de Power BI

```
Fuentes de datos (SQL, Excel, SharePoint, API, Dataverse...)
    ↓ Power Query (ETL — transformar y limpiar datos)
Modelo semántico (tablas, relaciones, jerarquías)
    ↓ DAX (métricas y columnas calculadas)
Visualizaciones (reportes interactivos)
    ↓ Power BI Service (publicar, compartir, actualizar)
Dashboards (pines de visuales clave)
```

## DAX — Data Analysis Expressions

### Medidas básicas (Measures)
Las medidas se calculan en tiempo de query según el contexto de filtro.

```dax
-- Suma simple
Total Ventas = SUM(Ventas[Monto])

-- Promedio
Precio Promedio = AVERAGE(Productos[Precio])

-- Conteo de filas
Total Pedidos = COUNTROWS(Pedidos)

-- Conteo de valores únicos
Clientes Únicos = DISTINCTCOUNT(Ventas[ClienteID])

-- Medida condicional
Ventas Activas = CALCULATE(SUM(Ventas[Monto]), Clientes[Activo] = TRUE)
```

### CALCULATE — la función más importante de DAX
```dax
-- Modificar contexto de filtro
Ventas Argentina = CALCULATE([Total Ventas], Paises[Pais] = "Argentina")

-- Múltiples filtros
Ventas Premium AR = CALCULATE(
    [Total Ventas],
    Paises[Pais] = "Argentina",
    Productos[Categoria] = "Premium"
)

-- Eliminar filtro (ALL)
Total General = CALCULATE([Total Ventas], ALL(Ventas))

-- Eliminar filtro de una columna
Ventas Sin Filtro País = CALCULATE([Total Ventas], ALL(Paises[Pais]))
```

### Funciones de fecha y time intelligence
```dax
-- Año hasta la fecha
Ventas YTD = TOTALYTD([Total Ventas], Calendario[Fecha])

-- Mes hasta la fecha
Ventas MTD = TOTALMTD([Total Ventas], Calendario[Fecha])

-- Comparación con período anterior
Ventas Año Anterior = CALCULATE([Total Ventas], SAMEPERIODLASTYEAR(Calendario[Fecha]))

-- Variación vs año anterior
Var % YoY = DIVIDE([Total Ventas] - [Ventas Año Anterior], [Ventas Año Anterior], 0)

-- Desplazamiento de período
Ventas Mes Pasado = CALCULATE([Total Ventas], DATEADD(Calendario[Fecha], -1, MONTH))

-- Rango de fechas dinámico
Ventas Últimos 30 Días = CALCULATE(
    [Total Ventas],
    DATESINPERIOD(Calendario[Fecha], MAX(Calendario[Fecha]), -30, DAY)
)
```

### Funciones de iteración (X-functions)
```dax
-- Suma iterando sobre tabla
Margen Total = SUMX(Ventas, Ventas[Monto] - Ventas[Costo])

-- Promedio iterando
Margen Promedio = AVERAGEX(Productos, Productos[Precio] - Productos[Costo])

-- Filtrar y contar con iteración
Pedidos Rentables = COUNTX(FILTER(Pedidos, Pedidos[Margen] > 0), Pedidos[ID])
```

### Variables en DAX (VAR / RETURN)
```dax
Rentabilidad % =
VAR TotalVentas = SUM(Ventas[Monto])
VAR TotalCosto = SUM(Ventas[Costo])
VAR Margen = TotalVentas - TotalCosto
RETURN
    DIVIDE(Margen, TotalVentas, 0)
```

### Funciones de filtro y lookup
```dax
-- Buscar valor relacionado
Categoría Producto = RELATED(Productos[Categoria])

-- Buscar en cualquier dirección (LOOKUPVALUE)
Precio = LOOKUPVALUE(Productos[Precio], Productos[SKU], Ventas[SKU])

-- Rank (clasificación)
Ranking Cliente = RANKX(ALL(Clientes), [Total Ventas], , DESC, Dense)

-- Calcular sobre tabla virtual
Top 3 Clientes =
CALCULATE(
    [Total Ventas],
    TOPN(3, ALL(Clientes[Nombre]), [Total Ventas])
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

-- Concatenar
Nombre Completo = Empleados[Nombre] & " " & Empleados[Apellido]

-- Edad
Edad = DATEDIFF(Clientes[FechaNacimiento], TODAY(), YEAR)
```

## Power Query (M) — ETL y Transformación

### Estructura básica de un paso M
```m
let
    Origen = Excel.Workbook(File.Contents("C:\datos.xlsx"), null, true),
    Hoja1 = Origen{[Item="Ventas",Kind="Sheet"]}[Data],
    EncabezadosPromovidos = Table.PromoteHeaders(Hoja1, [PromoteAllScalars=true]),
    TiposAsignados = Table.TransformColumnTypes(EncabezadosPromovidos, {
        {"Fecha", type date},
        {"Monto", type number},
        {"Cliente", type text}
    })
in
    TiposAsignados
```

### Transformaciones frecuentes
```m
// Filtrar filas
Table.SelectRows(tabla, each [Activo] = true and [Monto] > 0)

// Agregar columna personalizada
Table.AddColumn(tabla, "Margen", each [Precio] - [Costo], type number)

// Cambiar tipo
Table.TransformColumnTypes(tabla, {{"Fecha", type date}, {"ID", Int64.Type}})

// Reemplazar valores
Table.ReplaceValue(tabla, null, "Sin datos", Replacer.ReplaceValue, {"Descripcion"})

// Eliminar columnas
Table.RemoveColumns(tabla, {"ColumnaInutil1", "ColumnaInutil2"})

// Renombrar columnas
Table.RenameColumns(tabla, {{"old_name", "NuevoNombre"}, {"id", "ID"}})

// Agrupar y agregar
Table.Group(tabla, {"Region"}, {
    {"Total", each List.Sum([Monto]), type number},
    {"Conteo", each Table.RowCount(_), Int64.Type}
})

// Combinar tablas (Merge = JOIN)
Table.NestedJoin(Ventas, {"ProductoID"}, Productos, {"ID"}, "Detalle", JoinKind.LeftOuter)

// Expandir columna de tabla anidada
Table.ExpandTableColumn(tabla, "Detalle", {"Nombre", "Categoria"})

// Dividir columna
Table.SplitColumn(tabla, "NombreCompleto", Splitter.SplitTextByDelimiter(" "), {"Nombre", "Apellido"})

// Pivot y Unpivot
Table.Pivot(tabla, List.Distinct(tabla[Mes]), "Mes", "Ventas", List.Sum)
Table.UnpivotOtherColumns(tabla, {"ID", "Producto"}, "Atributo", "Valor")
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

## Modelo de datos — Buenas prácticas

### Relaciones
- Preferir modelo estrella (Star Schema): tabla de hechos + tablas de dimensiones
- Relaciones 1:N (uno a muchos) son las más comunes y eficientes
- Evitar relaciones bidireccionales (many-to-many) salvo cuando sea necesario
- Tabla `Calendario` (DimDate) siempre activa, marcada como tabla de fecha

### Tabla Calendario mínima
```dax
Calendario = 
ADDCOLUMNS(
    CALENDAR(DATE(2020,1,1), DATE(2026,12,31)),
    "Año", YEAR([Date]),
    "Mes", MONTH([Date]),
    "Nombre Mes", FORMAT([Date], "MMMM"),
    "Trimestre", "Q" & QUARTER([Date]),
    "Semana", WEEKNUM([Date]),
    "Día Semana", FORMAT([Date], "dddd"),
    "Es Fin de Semana", IF(WEEKDAY([Date], 2) > 5, TRUE, FALSE)
)
```

## Visualizaciones principales

| Visual | Uso ideal |
|--------|-----------|
| Gráfico de barras/columnas | Comparar categorías |
| Gráfico de líneas | Tendencias en el tiempo |
| Tarjeta (Card) | KPI único (Total ventas, % crecimiento) |
| Tabla / Matriz | Datos detallados, tablas pivot |
| Mapa | Datos geográficos |
| Gráfico de dispersión | Correlación entre variables |
| Embudo (Funnel) | Conversión por etapas |
| Medidor (Gauge) | Progreso hacia meta |
| Slicer | Filtros interactivos para el usuario |
| Segmentación de datos por rango | Filtro de fechas / rangos numéricos |

## Publicación y actualización en Power BI Service

### Actualización programada
- Dataflow o dataset: programar refresh en servicio
- Para fuentes on-premises: instalar Power BI Gateway (modo personal o estándar)
- Máximo de refreshes diarios: 8 (licencia Pro), 48 (Premium)

### Seguridad a nivel de fila (RLS)
```dax
-- En Power BI Desktop: Modelado → Administrar roles
[Vendedor] = USERNAME()       -- Para RLS estática
[Region] = LOOKUPVALUE(Usuarios[Region], Usuarios[Email], USERPRINCIPALNAME())
```

### API de Power BI (REST)
```
GET  /v1.0/myorg/groups           -- Listar workspaces
GET  /v1.0/myorg/datasets         -- Listar datasets
POST /v1.0/myorg/datasets/{id}/refreshes  -- Trigger refresh
GET  /v1.0/myorg/reports          -- Listar reportes
POST /v1.0/myorg/groups/{wid}/datasets/{did}/rows  -- Push data (streaming)
```

Autenticación: OAuth2 con Azure AD (scope: `https://analysis.windows.net/powerbi/api/.default`)

## Errores frecuentes

| Error | Causa | Solución |
|-------|-------|----------|
| `A circular dependency was detected` | DAX referencias circulares | Revisar columnas calculadas que se referencian entre sí |
| `The column X doesn't exist in the table` | Nombre de columna incorrecto | Verificar nombres exactos (case-sensitive en M) |
| `Relationship not active` | Varias relaciones entre mismas tablas | Usar `USERELATIONSHIP()` en CALCULATE |
| Datos incorrectos en visual | Relación activa en dirección equivocada | Revisar cardinalidad y dirección de filtro |
| Refresh falla en servicio | Gateway no disponible o credenciales expiradas | Verificar gateway online y renovar credenciales |
| `Expression.SyntaxError` en M | Error de sintaxis en Power Query | Revisar mayúsculas/minúsculas y comillas |
| Performance lenta | Medidas no optimizadas, joins costosos | Usar variables en DAX; evitar FILTER sobre grandes tablas |

## Documentación oficial

- DAX reference: https://learn.microsoft.com/dax/
- Power Query M: https://learn.microsoft.com/powerquery-m/
- Power BI Desktop: https://learn.microsoft.com/power-bi/fundamentals/desktop-getting-started
- Power BI Service: https://learn.microsoft.com/power-bi/fundamentals/power-bi-service-overview
- API REST: https://learn.microsoft.com/rest/api/power-bi/
