# Databricks notebook source
# MAGIC %md
# MAGIC # 🤖 04 · Modelo — Clasificación de la acción (scikit-learn + MLflow)
# MAGIC
# MAGIC Lee `workspace.gold.decision_cuadrilla`, entrena un clasificador multiclase
# MAGIC (`DESPACHAR_CUADRILLA` / `ESPERAR_AUTORRESTABLECIMIENTO` / `TECNICO_URGENTE`),
# MAGIC lo evalúa y lo registra en **MLflow / Unity Catalog**.
# MAGIC
# MAGIC Se prioriza el **recall de `DESPACHAR_CUADRILLA`** (no dejar fallas reales sin atender).
# MAGIC
# MAGIC **Linaje:** `workspace.gold.decision_cuadrilla` ➜ modelo en MLflow.

# COMMAND ----------

dbutils.widgets.text("catalogo", "workspace")
CATALOGO = dbutils.widgets.get("catalogo")

# COMMAND ----------

import pandas as pd
import mlflow
import mlflow.sklearn
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, recall_score

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cargar la capa Gold

# COMMAND ----------

pdf = spark.table(f"{CATALOGO}.gold.decision_cuadrilla").toPandas()
print("Registros:", len(pdf))

TARGET = "accion_recomendada"

num_cols = [
    "elementos_afectados", "cantidad_nodos", "cantidad_arpones", "clientes_afectados",
    "fuente_voltaje", "fuente_amperaje", "nodos_sector_en_bateria",
    "delta_correlacion_min", "tiempo_resolucion_min",
    "pct_autorrestablecimiento_sector", "n_fallas_sector",
]
cat_cols = ["region", "tecnologia", "impacto", "urgencia", "fuente_monitoreo"]
bool_cols = [
    "nodo_vip", "existe_en_cacti", "flag_en_bateria",
    "correlacion_grafica_monitoreo", "falla_simultanea_nodo_arpon", "requiere_notificacion",
]

for c in bool_cols:
    pdf[c] = pdf[c].astype(int)

X = pdf[num_cols + bool_cols + cat_cols]
y = pdf[TARGET]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42, stratify=y
)
print("Train:", X_train.shape, " Test:", X_test.shape)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pipeline de preprocesamiento + modelo
# MAGIC `class_weight="balanced"` para compensar el desbalance (DESPACHAR domina).

# COMMAND ----------

preprocesador = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(), num_cols),
        ("bool", "passthrough", bool_cols),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
    ]
)

modelo = Pipeline(
    steps=[
        ("pre", preprocesador),
        ("clf", RandomForestClassifier(
            n_estimators=300, max_depth=12,
            class_weight="balanced", random_state=42, n_jobs=-1,
        )),
    ]
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Entrenar, evaluar y registrar en MLflow

# COMMAND ----------

# Registro de modelos en Unity Catalog
try:
    mlflow.set_registry_uri("databricks-uc")
except Exception as e:
    print("No se pudo fijar registry UC:", e)

mlflow.sklearn.autolog(log_models=False)

with mlflow.start_run(run_name="rf_decision_cuadrilla") as run:
    modelo.fit(X_train, y_train)
    y_pred = modelo.predict(X_test)

    etiquetas = sorted(y.unique())
    reporte = classification_report(y_test, y_pred, output_dict=True)
    recall_despachar = recall_score(
        y_test, y_pred, labels=["DESPACHAR_CUADRILLA"], average="macro"
    )

    mlflow.log_metric("recall_DESPACHAR_CUADRILLA", recall_despachar)
    mlflow.log_metric("accuracy", reporte["accuracy"])
    mlflow.log_metric("f1_macro", reporte["macro avg"]["f1-score"])

    print("Recall DESPACHAR_CUADRILLA:", round(recall_despachar, 4))
    print("\n", classification_report(y_test, y_pred))
    print("Matriz de confusion (orden:", etiquetas, ")")
    print(confusion_matrix(y_test, y_pred, labels=etiquetas))

    # Registrar el modelo en Unity Catalog (catalogo.esquema.modelo)
    try:
        mlflow.sklearn.log_model(
            modelo,
            artifact_path="model",
            registered_model_name=f"{CATALOGO}.gold.modelo_decision_cuadrilla",
        )
        print("\nModelo registrado en Unity Catalog como "
              f"{CATALOGO}.gold.modelo_decision_cuadrilla")
    except Exception as e:
        mlflow.sklearn.log_model(modelo, artifact_path="model")
        print("\nModelo logueado (registro en UC omitido):", e)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Importancia de variables

# COMMAND ----------

import numpy as np

nombres = (
    num_cols
    + bool_cols
    + list(modelo.named_steps["pre"].named_transformers_["cat"].get_feature_names_out(cat_cols))
)
importancias = modelo.named_steps["clf"].feature_importances_
imp = (
    pd.DataFrame({"feature": nombres, "importancia": importancias})
    .sort_values("importancia", ascending=False)
    .head(20)
)
display(imp)

# COMMAND ----------

# MAGIC %md
# MAGIC > ⚠️ **Nota metodológica:** el `target` se deriva de reglas determinísticas sobre
# MAGIC > estas mismas señales (daño multielemento, energía en batería + correlación de
# MAGIC > monitoreo), por lo que el modelo aprende la regla casi perfectamente y las
# MAGIC > métricas serán muy altas. Es lo esperado con datos **simulados**; en un escenario
# MAGIC > real las etiquetas tendrían ruido y el modelo aportaría más valor predictivo.
