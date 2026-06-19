# Notebooks — Pipeline Medallion (NOC)

Pipeline ejecutable del proyecto, en PySpark sobre Databricks + Unity Catalog.

## Orden de ejecución

| # | Notebook | Entrada | Salida |
|---|---|---|---|
| 1 | `01_bronze.py` | `src/generar_datos.py` | `workspace.bronze.tickets_noc` |
| 2 | `02_silver.py` | `bronze.tickets_noc` | `workspace.silver.tickets_noc` |
| 3 | `03_gold.py` | `silver.tickets_noc` | `workspace.gold.decision_cuadrilla` |
| 4 | `04_modelo.py` | `gold.decision_cuadrilla` | Modelo en MLflow / Unity Catalog |

## Parámetros (widgets)

- `catalogo` (default `workspace`) — catálogo de Unity Catalog donde se crean los esquemas `bronze`, `silver`, `gold`.
- `01_bronze.py` además: `n_tickets` (default `1500`) y `semilla` (default `42`).

## Cómo correrlo

1. En Databricks: **New → Git folder** apuntando a este repo (rama `feature_pipeline_medallion`).
2. Adjunta un clúster (o serverless) a cada notebook.
3. Ejecuta en orden `01 → 02 → 03 → 04`.

> El linaje `bronze → silver → gold → modelo` queda registrado en Unity Catalog
> (criterio de mayor peso en la evaluación).
