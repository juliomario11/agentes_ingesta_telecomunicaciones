# Databricks notebook source

# MAGIC %md
# MAGIC # Análisis Descriptivo / EDA - Decisión de Cuadrillas (NOC)
# MAGIC
# MAGIC **Componente #5 - Ciencia de datos.** Análisis exploratorio sobre las capas
# MAGIC `silver.tickets_noc` y `gold.decision_cuadrilla` del pipeline Medallion.
# MAGIC
# MAGIC Cubre: resumen del dataset, calidad (nulos/duplicados), distribución del *target* y
# MAGIC **desbalance de clases**, univariado (numéricas + categóricas), bivariado (target vs
# MAGIC tecnología/región), correlaciones y conclusiones para el modelado.
# MAGIC
# MAGIC > El detalle escrito con todas las cifras está en `docs/analisis_descriptivo.md`.
# MAGIC > Autor: Mario Daniel Enrique Perez Jimenez.

# COMMAND ----------

dbutils.widgets.removeAll()
dbutils.widgets.text("catalogo", "workspace", "Catalogo")
catalogo = dbutils.widgets.get("catalogo")
print(f"Catalogo activo: {catalogo}")

# COMMAND ----------

from pyspark.sql import functions as F
import matplotlib.pyplot as plt
import numpy as np
import warnings
warnings.filterwarnings("ignore")

TARGET_ORDER = ["DESPACHAR_CUADRILLA", "ESPERAR_AUTORRESTABLECIMIENTO", "TECNICO_URGENTE"]
TARGET_COLOR = {
    "DESPACHAR_CUADRILLA": "#2563EB",
    "ESPERAR_AUTORRESTABLECIMIENTO": "#16A34A",
    "TECNICO_URGENTE": "#DC2626",
}

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Carga y resumen del dataset (Gold)

# COMMAND ----------

gold = spark.table(f"{catalogo}.gold.decision_cuadrilla")
silver = spark.table(f"{catalogo}.silver.tickets_noc")

n = gold.count()
print(f"Gold: {n:,} filas x {len(gold.columns)} columnas")
print(f"Silver: {silver.count():,} filas x {len(silver.columns)} columnas")
gold.printSchema()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Calidad de datos: nulos y duplicados

# COMMAND ----------

# Conteo de nulos por columna
nulos = gold.select([
    F.sum(F.col(c).isNull().cast("int")).alias(c) for c in gold.columns
])
display(nulos)

dup = n - gold.select("ticket").distinct().count()
print(f"Tickets duplicados: {dup}")
print(f"Total nulos (todas las columnas): "
      f"{nulos.toPandas().sum(axis=1).iloc[0]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Variable objetivo: distribución y desbalance de clases
# MAGIC La *accuracy* es engañosa con este desbalance: priorizar **recall/F1 por clase**.

# COMMAND ----------

df_t = (
    gold.groupBy("accion_recomendada")
    .agg(F.count("ticket").alias("cantidad"))
    .withColumn("porcentaje", F.round(F.col("cantidad") / n * 100, 2))
    .orderBy(F.col("cantidad").desc())
)
display(df_t)

t_pd = df_t.toPandas().set_index("accion_recomendada").reindex(TARGET_ORDER)
ratio = t_pd["cantidad"].max() / t_pd["cantidad"].min()
print(f"Ratio de desbalance (mayoritaria : minoritaria) = {ratio:.1f} : 1")

fig, ax = plt.subplots(figsize=(8.5, 4.6))
bars = ax.bar(TARGET_ORDER, t_pd["cantidad"], color=[TARGET_COLOR[k] for k in TARGET_ORDER],
              edgecolor="white", width=0.62)
for b, k in zip(bars, TARGET_ORDER):
    ax.text(b.get_x() + b.get_width()/2, b.get_height(),
            f"{int(t_pd['cantidad'][k]):,}\n({t_pd['porcentaje'][k]:.1f}%)",
            ha="center", va="bottom", fontweight="bold")
ax.set_title("Distribucion del target (accion_recomendada)", fontweight="bold")
ax.set_ylabel("N. de tickets")
plt.xticks(rotation=12)
plt.tight_layout(); plt.savefig("/tmp/01_target.png", dpi=150); plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Univariado - estadísticos de variables numéricas

# COMMAND ----------

NUM = ["clientes_afectados", "elementos_afectados", "cantidad_nodos", "cantidad_arpones",
       "fuente_voltaje", "fuente_amperaje", "nodos_sector_en_bateria",
       "delta_correlacion_min", "tiempo_resolucion_min",
       "pct_autorrestablecimiento_sector", "n_fallas_sector"]
display(gold.select(NUM).summary(
    "mean", "stddev", "min", "25%", "50%", "75%", "max"))

# COMMAND ----------

# Histogramas de variables numericas clave (a pandas: 1500 filas es seguro)
pdf = gold.toPandas()
HIST = ["clientes_afectados", "elementos_afectados", "tiempo_resolucion_min",
        "delta_correlacion_min", "fuente_voltaje", "nodos_sector_en_bateria",
        "pct_autorrestablecimiento_sector", "n_fallas_sector"]
fig, axes = plt.subplots(2, 4, figsize=(16, 7.5))
for ax, c in zip(axes.ravel(), HIST):
    ax.hist(pdf[c], bins=30, color="#4f46e5", edgecolor="white")
    ax.set_title(c, fontsize=10)
fig.suptitle("Distribuciones numericas (Gold)", fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/02_hist.png", dpi=150); plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Univariado - categóricas y banderas booleanas

# COMMAND ----------

for c in ["region", "tecnologia", "impacto", "urgencia", "fuente_monitoreo"]:
    print(f"--- {c} ---")
    display(gold.groupBy(c).count().orderBy(F.col("count").desc()))

# COMMAND ----------

BOOL = ["nodo_vip", "existe_en_cacti", "flag_en_bateria",
        "correlacion_grafica_monitoreo", "falla_simultanea_nodo_arpon", "requiere_notificacion"]
df_bool = gold.select([F.round(F.avg(F.col(b).cast("int")) * 100, 2).alias(b) for b in BOOL])
display(df_bool)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Bivariado - target por tecnología y por región
# MAGIC Hallazgo clave: `ESPERAR_AUTORRESTABLECIMIENTO` no ocurre en GPON (la batería de respaldo
# MAGIC solo se modela en HFC).

# COMMAND ----------

display(gold.groupBy("tecnologia", "accion_recomendada").count().orderBy("tecnologia"))
display(gold.groupBy("region", "accion_recomendada").count().orderBy("region"))

# Boxplots de clientes (log) y tiempo por clase del target
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
for ax, col, logy, title in [
    (axes[0], "clientes_afectados", True, "Clientes afectados (log)"),
    (axes[1], "tiempo_resolucion_min", False, "Tiempo de resolucion (min)"),
]:
    data = [pdf.loc[pdf.accion_recomendada == k, col].values for k in TARGET_ORDER]
    bp = ax.boxplot(data, patch_artist=True, labels=["DESPACHAR", "ESPERAR", "T.URGENTE"])
    for patch, k in zip(bp["boxes"], TARGET_ORDER):
        patch.set_facecolor(TARGET_COLOR[k]); patch.set_alpha(0.75)
    if logy: ax.set_yscale("log")
    ax.set_title(title, fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/05_box.png", dpi=150); plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Verificación de drivers deterministas del target

# COMMAND ----------

p_tec = gold.filter("falla_simultanea_nodo_arpon = true") \
    .agg(F.avg((F.col("accion_recomendada") == "TECNICO_URGENTE").cast("int"))).collect()[0][0]
p_esp = gold.filter(
    "flag_en_bateria = true AND nodos_sector_en_bateria >= 2 AND correlacion_grafica_monitoreo = true "
    "AND falla_simultanea_nodo_arpon = false"
).agg(F.avg((F.col("accion_recomendada") == "ESPERAR_AUTORRESTABLECIMIENTO").cast("int"))).collect()[0][0]
print(f"P(TECNICO_URGENTE | falla_simultanea)      = {p_tec:.3f}")
print(f"P(ESPERAR | bateria & nodos>=2 & correlac.) = {p_esp:.3f}")
print("=> El target es una regla logica determinista sobre 3 banderas.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Correlaciones (numéricas + booleanas)

# COMMAND ----------

CORR = NUM + BOOL
corr = pdf[CORR].astype(float).corr()
fig, ax = plt.subplots(figsize=(12.5, 10.5))
im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
ax.set_xticks(range(len(CORR))); ax.set_yticks(range(len(CORR)))
ax.set_xticklabels(CORR, rotation=55, ha="right", fontsize=8)
ax.set_yticklabels(CORR, fontsize=8)
for i in range(len(CORR)):
    for j in range(len(CORR)):
        if abs(corr.values[i, j]) >= 0.15:
            ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center", fontsize=7)
fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
ax.set_title("Matriz de correlacion (Gold)", fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/06_corr.png", dpi=150); plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Conclusiones para el modelado
# MAGIC
# MAGIC 1. **Evitar fuga de información:** no usar `forma_resolucion` / `restablecio_autonomo` como features (de ahí se deriva el target).
# MAGIC 2. **Desbalance 12,5 : 1** → `class_weight="balanced"`; reportar recall/F1 por clase (priorizar `TECNICO_URGENTE`).
# MAGIC 3. **`ESPERAR` es exclusivo de HFC** → la tecnología y las señales de energía son features de primer orden.
# MAGIC 4. **Features más informativas:** `falla_simultanea_nodo_arpon`, `flag_en_bateria`, `correlacion_grafica_monitoreo`, `nodos_sector_en_bateria`, `fuente_voltaje`.
# MAGIC 5. **`region` y `clientes_afectados`** aportan poco al target pero son clave para priorización / SLA.
# MAGIC 6. Como el target es determinista sobre datos simulados, las métricas serán muy altas (esperado); en producción las etiquetas tendrían ruido.
