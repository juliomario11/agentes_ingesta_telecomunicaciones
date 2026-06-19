# Databricks notebook source
# MAGIC %md
# MAGIC # 🥉 01 · Bronze — Ingesta de tickets crudos del NOC
# MAGIC
# MAGIC Genera el histórico simulado de tickets reutilizando `src/generar_datos.py`
# MAGIC y lo escribe **tal cual** (sin transformar) en `workspace.bronze.tickets_noc`
# MAGIC (Delta + Unity Catalog).
# MAGIC
# MAGIC **Linaje:** `src/generar_datos.py` ➜ **`workspace.bronze.tickets_noc`**

# COMMAND ----------

# MAGIC %md
# MAGIC ## Parámetros

# COMMAND ----------

dbutils.widgets.text("catalogo", "workspace")
dbutils.widgets.text("n_tickets", "1500")
dbutils.widgets.text("semilla", "42")

CATALOGO = dbutils.widgets.get("catalogo")
N = int(dbutils.widgets.get("n_tickets"))
SEMILLA = int(dbutils.widgets.get("semilla"))
print(f"Catalogo={CATALOGO}  N={N}  semilla={SEMILLA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Importar el generador desde `src/`
# MAGIC En un Git folder, agregamos la raíz del repo a `sys.path` para poder importar `src`.

# COMMAND ----------

import os, sys


def _agregar_raiz_repo():
    """Agrega la raiz del repo a sys.path (el notebook vive en notebooks/)."""
    candidatos = []
    try:
        ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
        nb_path = ctx.notebookPath().get()
        repo_rel = os.path.dirname(os.path.dirname(nb_path))
        candidatos.append("/Workspace" + repo_rel)
    except Exception:
        pass
    candidatos += [os.path.abspath(".."), os.path.abspath(".")]
    for c in candidatos:
        if c and c not in sys.path:
            sys.path.insert(0, c)


_agregar_raiz_repo()
from src.generar_datos import generar

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generar la data simulada y cargarla a Bronze

# COMMAND ----------

pdf = generar(n=N, semilla=SEMILLA)
print(f"Generados {len(pdf)} tickets · {pdf.shape[1]} columnas")

# pandas -> Spark DataFrame
sdf = spark.createDataFrame(pdf)

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOGO}.bronze")

(
    sdf.write
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{CATALOGO}.bronze.tickets_noc")
)

spark.sql(
    f"COMMENT ON TABLE {CATALOGO}.bronze.tickets_noc IS "
    f"'Bronze - tickets crudos del NOC (simulados). Proyecto agentes_ingesta_telecomunicaciones.'"
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verificación

# COMMAND ----------

df_bronze = spark.table(f"{CATALOGO}.bronze.tickets_noc")
print("Filas en bronze.tickets_noc:", df_bronze.count())

display(
    df_bronze.groupBy("accion_recomendada").count().orderBy("count", ascending=False)
)

# COMMAND ----------

display(df_bronze.limit(20))
