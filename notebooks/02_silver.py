# Databricks notebook source
# MAGIC %md
# MAGIC # 🥈 02 · Silver — Limpieza + features + calidad de datos
# MAGIC
# MAGIC Lee Bronze, aplica reglas de calidad y deriva features.
# MAGIC
# MAGIC **Linaje:** `workspace.bronze.tickets_noc` ➜ **`workspace.silver.tickets_noc`**

# COMMAND ----------

dbutils.widgets.text("catalogo", "workspace")
CATALOGO = dbutils.widgets.get("catalogo")

# COMMAND ----------

from pyspark.sql import functions as F

bronze = spark.table(f"{CATALOGO}.bronze.tickets_noc")
print("Filas leidas de bronze:", bronze.count())

# COMMAND ----------

# MAGIC %md
# MAGIC ## Calidad de datos (Data Quality expectations)
# MAGIC - `ticket` no nulo · tecnología válida · tiempos coherentes · voltaje/amperaje ≥ 0

# COMMAND ----------

silver = (
    bronze
    .filter(F.col("ticket").isNotNull())
    .filter(F.col("tecnologia").isin("HFC", "GPON"))
    .filter(F.col("hora_restablecimiento") >= F.col("hora_caida"))
    .filter((F.col("fuente_voltaje") >= 0) & (F.col("fuente_amperaje") >= 0))
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Features derivadas
# MAGIC - `elementos_afectados`, normalización de texto, `flag_en_bateria` (desde el voltaje),
# MAGIC   y `tiempo_resolucion_min` recalculado desde las marcas de tiempo.

# COMMAND ----------

silver = (
    silver
    .withColumn("elementos_afectados", F.col("cantidad_nodos") + F.col("cantidad_arpones"))
    .withColumn("impacto", F.initcap(F.col("impacto")))
    .withColumn("urgencia", F.initcap(F.col("urgencia")))
    .withColumn(
        "flag_en_bateria",
        (F.col("tecnologia") == "HFC")
        & (F.col("fuente_voltaje") > 0)
        & (F.col("fuente_voltaje") < 50),
    )
    .withColumn(
        "tiempo_resolucion_min",
        ((F.unix_timestamp("hora_restablecimiento") - F.unix_timestamp("hora_caida")) / 60).cast("int"),
    )
    .select(
        "ticket", "region", "departamento", "ciudad", "territorialidad", "tecnologia",
        "cantidad_nodos", "cantidad_arpones", "elementos_afectados",
        "cmts", "olt", "interfaz", "cable_padre", "cable_hijo", "nodo_vip",
        "impacto", "urgencia", "clientes_afectados", "existe_en_cacti", "fuente_monitoreo",
        "fuente_voltaje", "fuente_amperaje", "flag_en_bateria", "nodos_sector_en_bateria",
        "correlacion_grafica_monitoreo", "delta_correlacion_min", "falla_simultanea_nodo_arpon",
        "restablecio_autonomo", "forma_resolucion", "solucion_aplicada",
        "hora_caida", "hora_restablecimiento", "tiempo_resolucion_min",
        "requiere_notificacion", "grupo_whatsapp",
    )
)

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOGO}.silver")

(
    silver.write
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{CATALOGO}.silver.tickets_noc")
)

spark.sql(
    f"COMMENT ON TABLE {CATALOGO}.silver.tickets_noc IS "
    f"'Silver - tickets NOC limpios + features. Linaje desde bronze.tickets_noc.'"
)

# COMMAND ----------

display(spark.table(f"{CATALOGO}.silver.tickets_noc").limit(20))
