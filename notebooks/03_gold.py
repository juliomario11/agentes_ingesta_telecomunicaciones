# Databricks notebook source
# MAGIC %md
# MAGIC # 🥇 03 · Gold — Dataset de decisión + agregados + target
# MAGIC
# MAGIC Un registro por ticket con features finales, agregados por sector y el **target**
# MAGIC `accion_recomendada`.
# MAGIC
# MAGIC **Linaje:** `workspace.silver.tickets_noc` ➜ **`workspace.gold.decision_cuadrilla`**

# COMMAND ----------

dbutils.widgets.text("catalogo", "workspace")
CATALOGO = dbutils.widgets.get("catalogo")

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

silver = spark.table(f"{CATALOGO}.silver.tickets_noc")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Agregados por sector (cable padre) y target
# MAGIC La regla de negocio (simulada) define el target a partir de las señales de energía,
# MAGIC monitoreo y daño multielemento.

# COMMAND ----------

w_sector = Window.partitionBy("cable_padre")

gold = (
    silver
    .withColumn(
        "pct_autorrestablecimiento_sector",
        F.round(F.avg(F.col("restablecio_autonomo").cast("double")).over(w_sector), 3),
    )
    .withColumn("n_fallas_sector", F.count(F.lit(1)).over(w_sector).cast("int"))
    .withColumn(
        "accion_recomendada",
        F.when(F.col("falla_simultanea_nodo_arpon"), F.lit("TECNICO_URGENTE"))
        .when(
            F.col("flag_en_bateria")
            & (F.col("nodos_sector_en_bateria") >= 2)
            & F.col("correlacion_grafica_monitoreo"),
            F.lit("ESPERAR_AUTORRESTABLECIMIENTO"),
        )
        .otherwise(F.lit("DESPACHAR_CUADRILLA")),
    )
    .select(
        "ticket", "region", "ciudad", "tecnologia",
        "elementos_afectados", "cantidad_nodos", "cantidad_arpones",
        "nodo_vip", "impacto", "urgencia", "clientes_afectados",
        "existe_en_cacti", "fuente_monitoreo",
        "fuente_voltaje", "fuente_amperaje", "flag_en_bateria", "nodos_sector_en_bateria",
        "correlacion_grafica_monitoreo", "delta_correlacion_min", "falla_simultanea_nodo_arpon",
        "tiempo_resolucion_min", "requiere_notificacion",
        "cable_padre", "pct_autorrestablecimiento_sector", "n_fallas_sector",
        "forma_resolucion", "accion_recomendada",
    )
)

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOGO}.gold")

(
    gold.write
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{CATALOGO}.gold.decision_cuadrilla")
)

spark.sql(
    f"COMMENT ON TABLE {CATALOGO}.gold.decision_cuadrilla IS "
    f"'Gold - dataset de decision por ticket + target. Linaje desde silver.tickets_noc.'"
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verificación — distribución del target

# COMMAND ----------

display(
    spark.table(f"{CATALOGO}.gold.decision_cuadrilla")
    .groupBy("accion_recomendada").count().orderBy("count", ascending=False)
)
