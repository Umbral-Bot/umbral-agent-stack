---
name: big-data-python
description: >-
  Process and analyze large datasets with Pandas, Polars and Dask in Python.
  Covers DataFrames, lazy evaluation, groupby, joins, I/O and performance.
  Use when "pandas dataframe", "polars", "dask", "big data python",
  "csv processing", "data analysis", "etl pipeline", "large dataset".
metadata:
  openclaw:
    emoji: "\U0001F4CA"
    requires:
      env: []
---

# Big Data Python Skill

Procesar y analizar datasets grandes con Pandas, Polars y Dask. Comparación práctica entre las tres librerías con ejemplos equivalentes.

## Requisitos

No requiere variables de entorno. Solo paquetes Python:

```bash
pip install pandas polars dask[complete] pyarrow
```

## Pandas vs Polars vs Dask

| Aspecto | Pandas | Polars | Dask |
|---------|--------|--------|------|
| **Lenguaje base** | C/Cython | Rust | Python (wraps Pandas) |
| **Evaluación** | Eager | Lazy + Eager | Lazy |
| **Multithreading** | No (GIL) | Sí (automático) | Sí (distribuido) |
| **Memoria** | NumPy arrays | Apache Arrow | Particiones Pandas |
| **Datasets grandes** | Hasta ~10 GB | Hasta ~100 GB | Hasta ~100 TB |
| **Velocidad** | Baseline | 5-30x más rápido | Similar a Pandas por partición |
| **Ecosistema** | Gigante (scikit-learn, matplotlib) | Creciendo rápido | Compatible con Pandas |

### Cuándo usar cada uno

- **Pandas**: datasets < 1 GB, prototyping, integración con ML/viz
- **Polars**: datasets 1-100 GB, pipelines de producción, performance crítica
- **Dask**: datasets > RAM, computación distribuida, clusters

## 1. Pandas — Referencia rápida

```python
import pandas as pd

df = pd.read_csv("ventas.csv")
df = pd.read_parquet("ventas.parquet")

df.head()
df.info()
df.describe()

# Filtrar
activos = df[df["status"] == "active"]

# Groupby
resumen = df.groupby("region").agg(
    total=("monto", "sum"),
    promedio=("monto", "mean"),
    conteo=("monto", "count"),
).reset_index()

# Join
merged = pd.merge(ventas, clientes, on="client_id", how="left")

# Nuevas columnas
df["margen"] = df["ingreso"] - df["costo"]
df["year"] = pd.to_datetime(df["fecha"]).dt.year

# Guardar
df.to_parquet("resultado.parquet", index=False)
df.to_csv("resultado.csv", index=False)
```

### Operaciones de texto y fechas

```python
df["nombre_upper"] = df["nombre"].str.upper()
df["fecha"] = pd.to_datetime(df["fecha_str"], format="%Y-%m-%d")
df["mes"] = df["fecha"].dt.month
```

## 2. Polars — La alternativa rápida

### Eager API (similar a Pandas)

```python
import polars as pl

df = pl.read_csv("ventas.csv")
df = pl.read_parquet("ventas.parquet")

df.head()
df.schema
df.describe()

# Filtrar
activos = df.filter(pl.col("status") == "active")

# Groupby
resumen = df.group_by("region").agg(
    pl.col("monto").sum().alias("total"),
    pl.col("monto").mean().alias("promedio"),
    pl.col("monto").count().alias("conteo"),
)

# Join
merged = ventas.join(clientes, on="client_id", how="left")

# Nuevas columnas
df = df.with_columns(
    (pl.col("ingreso") - pl.col("costo")).alias("margen"),
    pl.col("fecha").str.to_date("%Y-%m-%d").dt.year().alias("year"),
)

# Guardar
df.write_parquet("resultado.parquet")
df.write_csv("resultado.csv")
```

### Lazy API (optimización automática)

```python
result = (
    pl.scan_parquet("ventas.parquet")       # no lee aún
    .filter(pl.col("monto") > 1000)         # predicate pushdown
    .group_by("region")
    .agg(pl.col("monto").sum().alias("total"))
    .sort("total", descending=True)
    .collect()                               # ejecuta el plan optimizado
)
```

La lazy API aplica automáticamente:
- **Predicate pushdown**: filtra antes de leer todo el archivo
- **Projection pushdown**: solo lee las columnas necesarias
- **Paralelización**: distribuye entre todos los cores de CPU

### Streaming (datasets más grandes que RAM)

```python
result = (
    pl.scan_parquet("huge_dataset.parquet")
    .filter(pl.col("year") == 2026)
    .group_by("category")
    .agg(pl.col("revenue").sum())
    .collect(engine="streaming")  # procesa en batches
)
```

## 3. Dask — Computación distribuida

```python
import dask.dataframe as dd
from dask.distributed import Client

client = Client()  # cluster local automático

df = dd.read_parquet("s3://bucket/ventas/*.parquet")

# API idéntica a Pandas
result = (
    df[df["monto"] > 1000]
    .groupby("region")
    .agg({"monto": "sum"})
    .compute()  # materializa el resultado (devuelve Pandas DF)
)
```

### Con cluster distribuido

```python
from dask.distributed import Client

client = Client("scheduler-address:8786")

df = dd.read_parquet("s3://bucket/data/")
result = df.groupby("category").mean().compute()
```

## 4. Conversión entre librerías

```python
# Pandas → Polars
polars_df = pl.from_pandas(pandas_df)

# Polars → Pandas
pandas_df = polars_df.to_pandas()

# Pandas → Dask
dask_df = dd.from_pandas(pandas_df, npartitions=4)

# Dask → Pandas
pandas_df = dask_df.compute()

# Polars ↔ Arrow
arrow_table = polars_df.to_arrow()
polars_df = pl.from_arrow(arrow_table)
```

## 5. Ejemplo completo — Pipeline ETL

### Con Polars (recomendado para producción)

```python
import polars as pl

pipeline = (
    pl.scan_parquet("raw/ventas_2026_*.parquet")
    .filter(pl.col("status") != "cancelled")
    .with_columns(
        (pl.col("price") * pl.col("quantity")).alias("total"),
        pl.col("date").str.to_date("%Y-%m-%d").alias("fecha"),
    )
    .with_columns(
        pl.col("fecha").dt.month().alias("mes"),
        pl.col("fecha").dt.year().alias("año"),
    )
    .group_by(["región", "mes"])
    .agg(
        pl.col("total").sum().alias("ingresos"),
        pl.col("total").mean().alias("ticket_promedio"),
        pl.len().alias("transacciones"),
    )
    .sort(["región", "mes"])
    .collect()
)

pipeline.write_parquet("processed/resumen_mensual.parquet")
print(pipeline)
```

### Equivalente en Pandas

```python
import pandas as pd
import glob

files = glob.glob("raw/ventas_2026_*.parquet")
df = pd.concat([pd.read_parquet(f) for f in files])

df = df[df["status"] != "cancelled"]
df["total"] = df["price"] * df["quantity"]
df["fecha"] = pd.to_datetime(df["date"])
df["mes"] = df["fecha"].dt.month
df["año"] = df["fecha"].dt.year

resumen = (
    df.groupby(["región", "mes"])
    .agg(
        ingresos=("total", "sum"),
        ticket_promedio=("total", "mean"),
        transacciones=("total", "count"),
    )
    .reset_index()
    .sort_values(["región", "mes"])
)

resumen.to_parquet("processed/resumen_mensual.parquet", index=False)
print(resumen)
```

## Formatos de archivo recomendados

| Formato | Lectura | Escritura | Notas |
|---------|---------|-----------|-------|
| **Parquet** | Rápido | Rápido | Columnar, compresión, ideal para analytics |
| **CSV** | Lento | Lento | Universal, debugging |
| **JSON** | Lento | Lento | APIs, datos anidados |
| **Arrow IPC** | Muy rápido | Muy rápido | Inter-proceso, zero-copy |

## Notas

- Polars es la opción recomendada para nuevos proyectos con datasets medianos-grandes.
- Pandas sigue siendo el estándar cuando se necesita integración con scikit-learn, matplotlib, seaborn.
- Parquet es siempre preferible sobre CSV para datos tabulares.
- Dask es necesario solo para datasets que no caben en RAM o para clusters.
- Docs: https://pandas.pydata.org/docs/ | https://docs.pola.rs/ | https://docs.dask.org/
