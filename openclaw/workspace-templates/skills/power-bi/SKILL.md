---
name: power-bi
description: >-
  Asistente para crear dashboards, medidas DAX, transformaciones Power Query (M)
  y publicar reportes con Microsoft Power BI Desktop y Power BI Service.
  Use when "power bi", "dax", "medida calculada", "power query", "M formula",
  "dashboard power bi", "visual power bi", "dataset", "informe power bi",
  "KPI power bi", "filtro dax", "tabla calculada", "reporte power bi".
metadata:
  openclaw:
    emoji: "\U0001F4CA"
    requires:
      env: []
---

# Power BI Skill

Rick usa este skill para guiar la creación de dashboards, modelos de datos, medidas DAX y transformaciones Power Query en Microsoft Power BI. Cubre tanto Power BI Desktop como Power BI Service.

Fuente oficial: https://learn.microsoft.com/power-bi/

---

## Arquitectura de Power BI

```
Origen de datos → Power Query (ETL) → Modelo de datos → DAX (métricas) → Visualizaciones → Power BI Service → Dashboards compartidos
```

| Componente | Herramienta | Función |
|------------|-------------|---------|
| Power BI Desktop | .pbix | Diseño de reportes (desarrollo) |
| Power BI Service | app.powerbi.com | Publicación, colaboración, actualizaciones |
| Power BI Mobile | iOS/Android | Consumo móvil |
| Power BI Report Builder | .rdl | Reportes paginados (estilo SSRS) |
| Power BI Embedded | API/SDK | Embeber reportes en apps propias |

---

## Tipos de cálculo

| Tipo | Lenguaje | Evaluación | Persiste en modelo |
|------|----------|------------|-------------------|
| **Medida (Measure)** | DAX | Al interactuar; respeta contexto filtro | No (calculada on-demand) |
| **Columna calculada** | DAX | Al refrescar; por fila | Sí (en tabla) |
| **Tabla calculada** | DAX | Al refrescar | Sí (tabla completa) |
| **Columna Power Query** | M | Al refrescar | Sí (pre-modelo) |
| **Visual Calculation** | DAX | Solo en visual; contexto visual | No |

---

## DAX — Fórmulas esenciales

### Agregaciones básicas

```dax
Ventas Total = SUM(Ventas[Monto])
Precio Promedio = AVERAGE(Productos[Precio])
Pedidos Count = COUNT(Pedidos[ID])
Clientes Distintos = DISTINCTCOUNT(Pedidos[ClienteID])
Max Venta = MAX(Ventas[Monto])
Min Venta = MIN(Ventas[Monto])
```

### CALCULATE — La función más importante

Modifica el contexto de filtro de una expresión.

```dax
// Ventas solo en 2025
Ventas 2025 = CALCULATE(SUM(Ventas[Monto]), Fechas[Año] = 2025)

// Ventas en región específica (ignorar filtro actual de región)
Ventas Norte = CALCULATE(SUM(Ventas[Monto]), ALL(Regiones), Regiones[Nombre] = "Norte")

// Ventas con múltiples condiciones
Ventas Premium Activas = CALCULATE(
    SUM(Ventas[Monto]),
    Productos[Categoria] = "Premium",
    Clientes[Estado] = "Activo"
)
```

### Time Intelligence (inteligencia de tiempo)

Requiere tabla de fechas marcada como "Date table" con columna Date continua.

```dax
// Año hasta la fecha
Ventas YTD = TOTALYTD(SUM(Ventas[Monto]), Fechas[Fecha])

// Trimestre hasta la fecha
Ventas QTD = TOTALQTD(SUM(Ventas[Monto]), Fechas[Fecha])

// Mes hasta la fecha
Ventas MTD = TOTALMTD(SUM(Ventas[Monto]), Fechas[Fecha])

// Mismo período año anterior
Ventas Año Anterior = CALCULATE(SUM(Ventas[Monto]), SAMEPERIODLASTYEAR(Fechas[Fecha]))

// Variación vs año anterior (%)
% Var Anual = DIVIDE(
    [Ventas Total] - [Ventas Año Anterior],
    [Ventas Año Anterior],
    0
)

// Media móvil 3 meses
Media Movil 3M = AVERAGEX(
    DATESINPERIOD(Fechas[Fecha], LASTDATE(Fechas[Fecha]), -3, MONTH),
    CALCULATE(SUM(Ventas[Monto]))
)
```

### FILTER, ALL, ALLEXCEPT

```dax
// Porcentaje sobre total general (ignora todos los filtros)
% del Total = DIVIDE([Ventas Total], CALCULATE([Ventas Total], ALL(Ventas)))

// Porcentaje del total de la categoría (ignora filtro de producto, mantiene categoría)
% de Categoría = DIVIDE(
    [Ventas Total],
    CALCULATE([Ventas Total], ALLEXCEPT(Productos, Productos[Categoria]))
)

// Ranking
Ranking Producto = RANKX(ALL(Productos), [Ventas Total], , DESC)
```

### Iteradores (X functions)

```dax
// Sumar campo calculado fila a fila
Margen Total = SUMX(Ventas, Ventas[Monto] - Ventas[Costo])

// Promedio ponderado
Precio Pond = DIVIDE(
    SUMX(Ventas, Ventas[Cantidad] * Ventas[PrecioUnitario]),
    SUM(Ventas[Cantidad])
)
```

### Variables en DAX

```dax
Variación % =
VAR VentasActual = [Ventas Total]
VAR VentasAnterior = [Ventas Año Anterior]
VAR Diferencia = VentasActual - VentasAnterior
RETURN
    IF(
        VentasAnterior = 0,
        BLANK(),
        DIVIDE(Diferencia, VentasAnterior)
    )
```

### Segmentación dinámica con SWITCH

```dax
Categoría Cliente =
SWITCH(
    TRUE(),
    [Ventas Total] >= 100000, "Premium",
    [Ventas Total] >= 50000, "Alto",
    [Ventas Total] >= 10000, "Medio",
    "Básico"
)
```

---

## Power Query (M) — Transformaciones

### Estructura básica de una consulta M

```
let
    Origen = Excel.Workbook(File.Contents("C:\datos.xlsx"), null, true),
    Hoja1 = Origen{[Item="Hoja1",Kind="Sheet"]}[Data],
    Encabezados = Table.PromoteHeaders(Hoja1, [PromoteAllScalars=true]),
    TiposCambiados = Table.TransformColumnTypes(Encabezados,{
        {"Fecha", type date},
        {"Monto", type number},
        {"Estado", type text}
    }),
    Filtradas = Table.SelectRows(TiposCambiados, each [Estado] <> "Cancelado")
in
    Filtradas
```

### Transformaciones frecuentes

```
// Filtrar filas
Table.SelectRows(tabla, each [Columna] > 100)
Table.SelectRows(tabla, each [Nombre] <> null and [Nombre] <> "")

// Agregar columna personalizada
Table.AddColumn(tabla, "Margen", each [Precio] - [Costo])
Table.AddColumn(tabla, "AñoMes", each Date.Year([Fecha]) * 100 + Date.Month([Fecha]))

// Renombrar columnas
Table.RenameColumns(tabla, {{"old_name", "NuevoNombre"}, {"otro", "Otro2"}})

// Eliminar columnas
Table.RemoveColumns(tabla, {"ColInutil", "ColTemp"})

// Pivotear
Table.Pivot(tabla, List.Distinct(tabla[Categoría]), "Categoría", "Monto", List.Sum)

// Unpivotear (normalizar)
Table.UnpivotOtherColumns(tabla, {"ID", "Fecha"}, "Atributo", "Valor")

// Agrupar y agregar
Table.Group(tabla, {"Region"}, {{"TotalVentas", each List.Sum([Monto]), type number}})

// Combinar tablas (merge = JOIN)
Table.NestedJoin(tabla1, "ClienteID", tabla2, "ID", "DatosCliente", JoinKind.LeftOuter)

// Expandir tabla anidada
Table.ExpandTableColumn(tabla, "DatosCliente", {"Nombre", "Ciudad"})

// Texto
Text.Upper([Campo])
Text.Trim([Campo])
Text.Start([Campo], 5)
Text.Contains([Campo], "valor")
Text.Replace([Campo], "viejo", "nuevo")
```

---

## Modelo de datos — Buenas prácticas

### Relaciones

- Preferir relaciones **1:N** (tabla dimensión → tabla hechos)
- Evitar relaciones **N:N** directas; usar tabla puente
- Dirección de filtro: **Single** en la mayoría de casos; **Both** solo si necesario
- Marcar tabla de fechas como **Date Table** (Modeling > Mark as date table)

### Tabla de fechas

```dax
Fechas =
CALENDAR(DATE(2020, 1, 1), DATE(2026, 12, 31))
```

Agregar columnas: Año, Trimestre, Mes, Semana, DíaSemana, EsFeriado, EsFinDeSemana.

### Performance

- Ocultar columnas de clave foránea en reportes
- Usar medidas en lugar de columnas calculadas cuando sea posible
- Reducir cardinalidad: agrupar valores de alta cardinalidad
- Evitar bidirectional filters salvo necesidad
- Usar `DIVIDE()` en lugar de `/` para manejar división por cero
- Crear tabla de parámetros para inputs dinámicos

---

## Visualizaciones principales

| Visual | Mejor para |
|--------|-----------|
| **Bar / Column chart** | Comparar categorías |
| **Line chart** | Tendencias temporales |
| **Pie / Donut** | Proporciones (máx 5 categorías) |
| **Card** | KPI único (número destacado) |
| **Multi-row card** | Múltiples KPIs |
| **Table / Matrix** | Datos tabulares; matrix para crosstab |
| **Slicer** | Filtros interactivos para usuario |
| **Map / Filled map** | Datos geográficos |
| **Scatter chart** | Correlaciones entre métricas |
| **Waterfall** | Acumulación positiva/negativa |
| **Funnel** | Conversión por etapas |
| **Gauge** | KPI vs objetivo |
| **Decomposition tree** | Análisis causa-raíz interactivo |
| **Q&A visual** | Consultas en lenguaje natural |

---

## Power BI Service — Funciones clave

| Función | Descripción |
|---------|-------------|
| **Workspace** | Espacio de colaboración; compartir reportes y datasets |
| **App** | Bundle de reportes y dashboards para usuarios finales |
| **Scheduled Refresh** | Actualización automática del dataset (hasta 8x/día en Premium) |
| **Row-Level Security (RLS)** | Filtros de datos por rol de usuario |
| **Dataflow** | ETL reutilizable en la nube (Power Query en Service) |
| **Goals (Scorecards)** | OKR y seguimiento de métricas |
| **Embedding** | Embeber reportes en apps con Power BI Embedded |

### RLS — Row-Level Security

```dax
// En tabla Vendedores — filtro por usuario logueado
[Email] = USERPRINCIPALNAME()

// Con LOOKUPVALUE para jerarquía de gerentes
[Region] IN
    CALCULATETABLE(
        VALUES(Regiones[Nombre]),
        FILTER(Vendedores, [Email] = USERPRINCIPALNAME())
    )
```

---

## API de Power BI REST

Base URL: `https://api.powerbi.com/v1.0/myorg/`

```
GET  /reports                         → listar reportes
GET  /datasets                        → listar datasets
POST /datasets/{id}/refreshes         → disparar actualización
GET  /datasets/{id}/refreshes         → historial de actualizaciones
POST /groups/{workspaceId}/imports    → publicar .pbix
GET  /reports/{reportId}/pages        → páginas del reporte
```

Autenticación: OAuth 2.0 con Azure AD. Registrar app en portal.azure.com, solicitar permisos `Report.Read.All`, `Dataset.ReadWrite.All`.

---

## Errores frecuentes y soluciones

| Error | Causa | Solución |
|-------|-------|---------|
| `A circular dependency was detected` | Columna calculada se referencia a sí misma | Revisar cadena de columnas calculadas |
| `The column ... was not found` | Nombre de columna incorrecto en DAX | Verificar nombre exacto con comillas simples: `Tabla[Columna]` |
| `Relationship not found` | Visual usa tablas sin relación | Crear relación o usar CROSSFILTER/TREATAS |
| `Formula.Firewall` en Power Query | Privacidad de datos bloqueando combinación | Ir a Opciones > Privacidad > Ignorar niveles de privacidad |
| Dataset no actualiza | Credenciales caducadas o fuente offline | Actualizar credenciales en Settings > Data source credentials |
| Visual muestra BLANK | Medida devuelve vacío | Agregar `+ 0` o `IF(ISBLANK(...), 0, ...)` |
| Rendimiento lento | Demasiadas columnas calculadas o visuals | Usar DAX Studio + VertiPaq Analyzer para profiling |

---

## Referencias

- Documentación oficial: https://learn.microsoft.com/power-bi/
- Referencia DAX: https://dax.guide/ y https://learn.microsoft.com/dax/
- Power Query M: https://learn.microsoft.com/powerquery-m/
- API REST: https://learn.microsoft.com/rest/api/power-bi/
- DAX Studio (herramienta gratuita): https://daxstudio.org/
- Comunidad: https://community.fabric.microsoft.com/
