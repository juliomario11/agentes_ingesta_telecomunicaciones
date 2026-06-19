# SQL — Pipeline Medallion (NOC)

Equivalente en **SQL puro** del pipeline de `notebooks/`. Sirve para ejecutar
directamente en el **SQL Editor** de Databricks (sobre el warehouse), sin clúster.
El código vive en la rama **`main`**.

| Archivo | Crea |
|---|---|
| `01_bronze.sql` | `workspace.bronze.tickets_noc` — **ingiere el CSV crudo desde el Volume** (`/Volumes/workspace/bronze/landing_zone/sample_tickets.csv`), alineado con la arquitectura *landing zone → bronze* |
| `02_silver.sql` | `workspace.silver.tickets_noc` — limpieza + features + calidad |
| `03_gold.sql` | `workspace.gold.decision_cuadrilla` — agregados por sector + target |
| `pipeline_noc_medallion.sql` | Todo en uno **100 % SQL** que **genera** los datos sintéticamente (sin Volume) + consultas de verificación |

## Ejecución

1. Si usas `01_bronze.sql`, primero sube `data/sample_tickets.csv` a `/Volumes/workspace/bronze/landing_zone/`.
2. Databricks → **SQL Editor** (con el warehouse seleccionado).
3. Pega el archivo y ejecuta en orden: **bronze → silver → gold**.
4. Es **idempotente** (`CREATE OR REPLACE`) y **no toca** las tablas `credit_risk`.

> La carpeta `notebooks/` hace lo mismo en PySpark (vía clúster) y `pipeline/run_pipeline.py`
> lo orquesta desde un solo script de Python. Esta carpeta `sql/` es la vía por warehouse
> y el respaldo versionado de los queries.
