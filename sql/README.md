# SQL — Pipeline Medallion (NOC)

Equivalente en **SQL puro** del pipeline de `notebooks/`. Sirve para ejecutar
directamente en el **SQL Editor** de Databricks (sobre el warehouse), sin clúster.

| Archivo | Crea |
|---|---|
| `01_bronze.sql` | `workspace.bronze.tickets_noc` — genera 1.500 tickets simulados con SQL nativo (réplica de `src/generar_datos.py`) |
| `02_silver.sql` | `workspace.silver.tickets_noc` — limpieza + features + calidad |
| `03_gold.sql` | `workspace.gold.decision_cuadrilla` — agregados por sector + target |
| `pipeline_noc_medallion.sql` | Todo en uno (bronze + silver + gold + consultas de verificación) |

## Ejecución

1. Databricks → **SQL Editor** (con el warehouse seleccionado).
2. Pega el archivo y ejecuta en orden: **bronze → silver → gold**.
3. Es **idempotente** (`CREATE OR REPLACE`) y **no toca** las tablas `credit_risk`.

> La carpeta `notebooks/` hace lo mismo en PySpark (vía clúster). Esta carpeta `SQL/`
> es la vía alternativa por warehouse y el respaldo versionado de los queries.
