# Databricks notebook source

# MAGIC %md
# MAGIC # Dashboard NOC - Recomendacion de Cuadrillas
# MAGIC
# MAGIC Este notebook genera los KPIs y visualizaciones para el dashboard del Centro de Operaciones de Red (NOC)
# MAGIC de telecomunicaciones. Lee la tabla `gold.decision_cuadrilla` y calcula metricas clave de:
# MAGIC - Distribucion de acciones recomendadas
# MAGIC - Comportamiento por region y tecnologia
# MAGIC - Tiempos de resolucion
# MAGIC - Alertas y notificaciones por grupo WhatsApp
# MAGIC
# MAGIC **Como conectar a Databricks SQL Dashboard o Power BI:**
# MAGIC - En Databricks SQL: crear un SQL Warehouse, luego ir a Dashboards > New Dashboard y agregar
# MAGIC   visualizaciones basadas en las consultas SQL del archivo `sql/04_dashboard_consultas.sql`.
# MAGIC - En Power BI: usar el conector nativo "Databricks" (Get Data > Databricks), apuntar al
# MAGIC   cluster/warehouse y conectar directamente a `workspace.gold.decision_cuadrilla`.

# COMMAND ----------

# Configuracion del widget de catalogo
dbutils.widgets.removeAll()
dbutils.widgets.text("catalogo", "workspace", "Catalogo")

catalogo = dbutils.widgets.get("catalogo")
print(f"Catalogo activo: {catalogo}")

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import warnings
warnings.filterwarnings("ignore")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Carga de datos
# MAGIC Lee la tabla principal `gold.decision_cuadrilla` y deriva la columna `grupo_whatsapp`
# MAGIC concatenando el prefijo `GRP_NOC_` con la region (ya que la columna no existe en gold
# MAGIC pero se puede derivar directamente).

# COMMAND ----------

tabla = f"{catalogo}.gold.decision_cuadrilla"
df = spark.table(tabla)

# Derivar grupo_whatsapp ya que no existe en gold
df = df.withColumn("grupo_whatsapp", F.concat(F.lit("GRP_NOC_"), F.col("region")))

print(f"Total de tickets cargados: {df.count():,}")
df.printSchema()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. KPI 1 - Distribucion de accion_recomendada (conteo y porcentaje)
# MAGIC Muestra cuantos tickets terminan en cada accion recomendada y el porcentaje sobre el total.
# MAGIC Util para evaluar la carga operativa del NOC.

# COMMAND ----------

total_tickets = df.count()

df_acciones = (
    df.groupBy("accion_recomendada")
    .agg(F.count("ticket").alias("cantidad"))
    .withColumn("porcentaje", F.round(F.col("cantidad") / total_tickets * 100, 2))
    .orderBy(F.col("cantidad").desc())
)

display(df_acciones)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Grafico 1 - Distribucion de acciones recomendadas (matplotlib)

# COMMAND ----------

df_acc_pd = df_acciones.toPandas()

fig, ax = plt.subplots(figsize=(8, 5))
colores = ["#E74C3C", "#F39C12", "#27AE60"]
bars = ax.barh(
    df_acc_pd["accion_recomendada"],
    df_acc_pd["cantidad"],
    color=colores[: len(df_acc_pd)],
    edgecolor="white",
)
for bar, pct in zip(bars, df_acc_pd["porcentaje"]):
    ax.text(
        bar.get_width() + 0.5,
        bar.get_y() + bar.get_height() / 2,
        f"{pct}%",
        va="center",
        fontsize=10,
    )
ax.set_xlabel("Cantidad de tickets", fontsize=11)
ax.set_title("Distribucion de Acciones Recomendadas - NOC", fontsize=13, fontweight="bold")
ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
plt.tight_layout()
plt.savefig("/tmp/acciones_recomendadas.png", dpi=120)
plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. KPI 2 - Acciones por region y por tecnologia
# MAGIC Tabla cruzada region x accion_recomendada. Permite identificar regiones con mayor
# MAGIC presion operativa (muchos TECNICO_URGENTE o DESPACHAR_CUADRILLA).

# COMMAND ----------

df_region_accion = (
    df.groupBy("region", "accion_recomendada")
    .agg(F.count("ticket").alias("cantidad"))
    .orderBy("region", "accion_recomendada")
)

display(df_region_accion)

# COMMAND ----------

df_tec_accion = (
    df.groupBy("tecnologia", "accion_recomendada")
    .agg(F.count("ticket").alias("cantidad"))
    .orderBy("tecnologia", "accion_recomendada")
)

display(df_tec_accion)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. KPI 3 - Porcentaje promedio de autorrestablecimiento por region
# MAGIC Indica la madurez de la red en cada region: mayor porcentaje significa que la red
# MAGIC se recupera sola con mas frecuencia, reduciendo la necesidad de enviar cuadrillas.

# COMMAND ----------

df_autorres = (
    df.groupBy("region")
    .agg(
        F.round(F.avg("pct_autorrestablecimiento_sector") * 100, 2).alias(
            "pct_autorres_promedio"
        ),
        F.count("ticket").alias("total_tickets"),
    )
    .orderBy(F.col("pct_autorres_promedio").desc())
)

display(df_autorres)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Grafico 2 - % Autorrestablecimiento promedio por region

# COMMAND ----------

df_ar_pd = df_autorres.toPandas()

fig, ax = plt.subplots(figsize=(8, 4))
ax.bar(
    df_ar_pd["region"],
    df_ar_pd["pct_autorres_promedio"],
    color="#2980B9",
    edgecolor="white",
)
ax.set_ylabel("% Autorrestablecimiento promedio", fontsize=11)
ax.set_title("Autorrestablecimiento Promedio por Region", fontsize=13, fontweight="bold")
ax.set_ylim(0, 100)
for i, v in enumerate(df_ar_pd["pct_autorres_promedio"]):
    ax.text(i, v + 1, f"{v}%", ha="center", fontsize=10)
plt.tight_layout()
plt.savefig("/tmp/autorrestablecimiento_region.png", dpi=120)
plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. KPI 4 - Tiempo promedio de resolucion por accion y por tecnologia
# MAGIC Muestra el tiempo medio (en minutos) que tarda cada tipo de accion en resolverse,
# MAGIC discriminado tambien por tecnologia (HFC vs GPON).

# COMMAND ----------

df_tiempo_accion = (
    df.groupBy("accion_recomendada")
    .agg(
        F.round(F.avg("tiempo_resolucion_min"), 1).alias("tiempo_prom_min"),
        F.round(F.expr("percentile_approx(tiempo_resolucion_min, 0.5)"), 1).alias(
            "tiempo_mediana_min"
        ),
        F.count("ticket").alias("n_tickets"),
    )
    .orderBy("accion_recomendada")
)

display(df_tiempo_accion)

# COMMAND ----------

df_tiempo_tec = (
    df.groupBy("tecnologia")
    .agg(
        F.round(F.avg("tiempo_resolucion_min"), 1).alias("tiempo_prom_min"),
        F.round(F.expr("percentile_approx(tiempo_resolucion_min, 0.5)"), 1).alias(
            "tiempo_mediana_min"
        ),
        F.count("ticket").alias("n_tickets"),
    )
    .orderBy("tecnologia")
)

display(df_tiempo_tec)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. KPI 5 - Clientes afectados totales por region
# MAGIC Suma total de clientes impactados agrupada por region. Metrica critica para
# MAGIC priorizar la atencion y cumplir ANS (SLA) con los clientes corporativos y masivos.

# COMMAND ----------

df_clientes_region = (
    df.groupBy("region")
    .agg(
        F.sum("clientes_afectados").alias("clientes_afectados_total"),
        F.avg("clientes_afectados").alias("clientes_afectados_promedio"),
        F.max("clientes_afectados").alias("clientes_afectados_max"),
        F.count("ticket").alias("n_tickets"),
    )
    .withColumn(
        "clientes_afectados_promedio",
        F.round(F.col("clientes_afectados_promedio"), 0).cast("int"),
    )
    .orderBy(F.col("clientes_afectados_total").desc())
)

display(df_clientes_region)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. KPI 6 - Notificaciones requeridas por grupo WhatsApp
# MAGIC Conteo de tickets que requieren notificacion (`requiere_notificacion = true`)
# MAGIC agrupados por grupo WhatsApp derivado de la region.
# MAGIC **Reglas de notificacion:** nodo_vip = true, O clientes_afectados > 2000,
# MAGIC O impacto IN ('Alto','Critico'), O urgencia IN ('Alta','Critica').

# COMMAND ----------

df_notif_grupo = (
    df.filter(F.col("requiere_notificacion") == True)
    .groupBy("grupo_whatsapp")
    .agg(
        F.count("ticket").alias("n_notificaciones"),
        F.sum("clientes_afectados").alias("clientes_afectados_total"),
    )
    .orderBy(F.col("n_notificaciones").desc())
)

display(df_notif_grupo)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. KPI 7 - Top 10 sectores (cable_padre) por numero de fallas
# MAGIC Identifica los sectores de red con mayor recurrencia de fallas.
# MAGIC Estos sectores deben ser priorizados para mantenimiento preventivo o inversion en red.

# COMMAND ----------

df_top_sectores = (
    df.groupBy("cable_padre")
    .agg(
        F.max("n_fallas_sector").alias("max_fallas_sector"),
        F.count("ticket").alias("n_tickets"),
        F.sum("clientes_afectados").alias("clientes_afectados_total"),
        F.first("region").alias("region"),
    )
    .orderBy(F.col("max_fallas_sector").desc())
    .limit(10)
)

display(df_top_sectores)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. KPI Adicional - Distribucion de impacto y urgencia
# MAGIC Vision general de la criticidad de los tickets procesados.

# COMMAND ----------

df_impacto = (
    df.groupBy("impacto")
    .agg(F.count("ticket").alias("cantidad"))
    .withColumn("porcentaje", F.round(F.col("cantidad") / total_tickets * 100, 2))
    .orderBy(
        F.when(F.col("impacto") == "Critico", 1)
        .when(F.col("impacto") == "Alto", 2)
        .when(F.col("impacto") == "Medio", 3)
        .otherwise(4)
    )
)

df_urgencia = (
    df.groupBy("urgencia")
    .agg(F.count("ticket").alias("cantidad"))
    .withColumn("porcentaje", F.round(F.col("cantidad") / total_tickets * 100, 2))
    .orderBy(
        F.when(F.col("urgencia") == "Critica", 1)
        .when(F.col("urgencia") == "Alta", 2)
        .when(F.col("urgencia") == "Media", 3)
        .otherwise(4)
    )
)

display(df_impacto)
display(df_urgencia)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Resumen ejecutivo
# MAGIC Tabla resumen de los KPIs mas importantes para el reporte gerencial del NOC.

# COMMAND ----------

df_resumen = spark.createDataFrame(
    [
        (
            "Total tickets",
            str(df.count()),
        ),
        (
            "Tickets con notificacion requerida",
            str(df.filter(F.col("requiere_notificacion") == True).count()),
        ),
        (
            "Total clientes afectados",
            str(df.agg(F.sum("clientes_afectados")).collect()[0][0]),
        ),
        (
            "Tiempo resolucion promedio (min)",
            str(
                round(
                    df.agg(F.avg("tiempo_resolucion_min")).collect()[0][0], 1
                )
            ),
        ),
        (
            "Tickets TECNICO_URGENTE",
            str(
                df.filter(
                    F.col("accion_recomendada") == "TECNICO_URGENTE"
                ).count()
            ),
        ),
    ],
    ["KPI", "Valor"],
)

display(df_resumen)

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Instrucciones para Databricks SQL Dashboard
# MAGIC
# MAGIC 1. Ir a **Databricks SQL > Dashboards > + New Dashboard**.
# MAGIC 2. Agregar visualizaciones usando las consultas del archivo `sql/04_dashboard_consultas.sql`.
# MAGIC 3. Cada consulta puede convertirse en un widget de tipo tabla, barra, torta o metrica.
# MAGIC 4. Usar filtros de parametros para filtrar por `region` o `tecnologia` interactivamente.
# MAGIC
# MAGIC ## Instrucciones para Power BI
# MAGIC
# MAGIC 1. Abrir Power BI Desktop > **Get Data > Databricks**.
# MAGIC 2. Ingresar el Server Hostname y HTTP Path del SQL Warehouse.
# MAGIC 3. Conectar al catalogo `workspace`, esquema `gold`, tabla `decision_cuadrilla`.
# MAGIC 4. Crear medidas DAX equivalentes a los KPIs calculados en este notebook.
# MAGIC 5. Publicar en Power BI Service con actualizacion programada via gateway o Direct Query.
