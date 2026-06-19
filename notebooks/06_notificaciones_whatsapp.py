# Databricks notebook source

# MAGIC %md
# MAGIC # NOC - Notificaciones WhatsApp (Simuladas)
# MAGIC
# MAGIC Este notebook gestiona las notificaciones automaticas del NOC hacia grupos de WhatsApp
# MAGIC de cada region. Lee la vista `gold.notificaciones_whatsapp` (o recalcula la logica
# MAGIC desde `gold.decision_cuadrilla`) y simula el envio de mensajes.
# MAGIC
# MAGIC **ADVERTENCIA DE SEGURIDAD:**
# MAGIC El envio real de mensajes via WhatsApp Business API o Twilio esta DESHABILITADO
# MAGIC en este notebook. La funcion `enviar_whatsapp()` solo imprime el mensaje en consola.
# MAGIC Para habilitar el envio real, seguir las instrucciones en la seccion de integracion
# MAGIC al final de este notebook y configurar las credenciales en Databricks Secrets.
# MAGIC
# MAGIC **NUNCA incluir tokens, API keys ni contrasenas directamente en el codigo.**

# COMMAND ----------

# Configuracion del widget de catalogo
dbutils.widgets.removeAll()
dbutils.widgets.text("catalogo", "workspace", "Catalogo")

catalogo = dbutils.widgets.get("catalogo")
print(f"Catalogo activo: {catalogo}")

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import StringType
import warnings
warnings.filterwarnings("ignore")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Carga de notificaciones
# MAGIC
# MAGIC Intentamos leer la vista `gold.notificaciones_whatsapp`. Si no existe (por ejemplo,
# MAGIC en un ambiente de desarrollo), recalculamos la logica directamente desde
# MAGIC `gold.decision_cuadrilla` usando PySpark.
# MAGIC
# MAGIC La logica de notificacion es:
# MAGIC - `nodo_vip = true`
# MAGIC - `clientes_afectados > 2000`
# MAGIC - `impacto IN ('Alto', 'Critico')`
# MAGIC - `urgencia IN ('Alta', 'Critica')`

# COMMAND ----------

def cargar_notificaciones(catalogo_name):
    """
    Intenta leer la vista gold.notificaciones_whatsapp.
    Si falla, recalcula la logica equivalente desde gold.decision_cuadrilla.
    """
    vista = f"{catalogo_name}.gold.notificaciones_whatsapp"
    tabla_base = f"{catalogo_name}.gold.decision_cuadrilla"

    try:
        df = spark.table(vista)
        print(f"Vista '{vista}' encontrada y cargada correctamente.")
        return df
    except Exception as e:
        print(f"Vista no encontrada: {e}")
        print(f"Recalculando logica desde '{tabla_base}'...")

    # Recalculo PySpark equivalente a la vista SQL
    df_base = spark.table(tabla_base)

    # Filtrar solo los que requieren notificacion
    df_notif = df_base.filter(F.col("requiere_notificacion") == True)

    # Derivar grupo_whatsapp
    df_notif = df_notif.withColumn(
        "grupo_whatsapp",
        F.concat(F.lit("GRP_NOC_"), F.col("region"))
    )

    # Construir motivo_notificacion concatenando las reglas que aplican
    df_notif = df_notif.withColumn(
        "motivo_notificacion",
        F.trim(
            F.concat_ws(
                " | ",
                F.when(F.col("nodo_vip") == True, F.lit("NODO_VIP")).otherwise(F.lit(None).cast(StringType())),
                F.when(
                    F.col("clientes_afectados") > 2000,
                    F.concat(F.lit("MAS_2000_CLIENTES("), F.col("clientes_afectados").cast(StringType()), F.lit(")"))
                ).otherwise(F.lit(None).cast(StringType())),
                F.when(
                    F.col("impacto").isin("Alto", "Critico"),
                    F.concat(F.lit("IMPACTO_"), F.upper(F.col("impacto")))
                ).otherwise(F.lit(None).cast(StringType())),
                F.when(
                    F.col("urgencia").isin("Alta", "Critica"),
                    F.concat(F.lit("URGENCIA_"), F.upper(F.col("urgencia")))
                ).otherwise(F.lit(None).cast(StringType())),
            )
        )
    )

    # Calcular prioridad
    df_notif = df_notif.withColumn(
        "prioridad",
        F.when(
            (F.col("accion_recomendada") == "TECNICO_URGENTE") |
            (F.col("impacto") == "Critico") |
            (F.col("urgencia") == "Critica"),
            F.lit("P1")
        ).when(
            (F.col("impacto") == "Alto") |
            (F.col("urgencia") == "Alta") |
            (F.col("nodo_vip") == True),
            F.lit("P2")
        ).otherwise(F.lit("P3"))
    )

    # Construir mensaje de texto listo para enviar
    df_notif = df_notif.withColumn(
        "mensaje",
        F.concat(
            F.lit("[NOC-"), F.col("prioridad"), F.lit("] "),
            F.lit("Ticket: "), F.col("ticket"), F.lit(" | "),
            F.lit("Ciudad: "), F.col("ciudad"), F.lit(" ("), F.col("region"), F.lit(") | "),
            F.lit("Tec: "), F.col("tecnologia"), F.lit(" | "),
            F.lit("Accion: "), F.col("accion_recomendada"), F.lit(" | "),
            F.lit("Clientes afectados: "), F.col("clientes_afectados").cast(StringType()), F.lit(" | "),
            F.lit("Impacto: "), F.col("impacto"), F.lit(" | "),
            F.lit("Urgencia: "), F.col("urgencia"), F.lit(" | "),
            F.lit("Motivo: "), F.col("motivo_notificacion"),
        )
    )

    # Seleccionar columnas finales
    columnas_finales = [
        "ticket", "grupo_whatsapp", "prioridad", "accion_recomendada",
        "region", "ciudad", "tecnologia", "clientes_afectados",
        "impacto", "urgencia", "nodo_vip", "flag_en_bateria",
        "n_fallas_sector", "tiempo_resolucion_min",
        "motivo_notificacion", "mensaje"
    ]

    df_final = df_notif.select(columnas_finales).orderBy(
        F.when(F.col("prioridad") == "P1", 1)
         .when(F.col("prioridad") == "P2", 2)
         .otherwise(3),
        F.col("clientes_afectados").desc()
    )

    print(f"Logica recalculada. Total notificaciones: {df_final.count():,}")
    return df_final


df_notificaciones = cargar_notificaciones(catalogo)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Vista general de notificaciones pendientes
# MAGIC Muestra todas las notificaciones ordenadas por prioridad (P1 > P2 > P3)
# MAGIC y por cantidad de clientes afectados.

# COMMAND ----------

print(f"Total de notificaciones a enviar: {df_notificaciones.count():,}")
display(df_notificaciones)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Agregados: notificaciones por grupo WhatsApp
# MAGIC Cuantos mensajes debe recibir cada grupo regional del NOC y el nivel de criticidad.

# COMMAND ----------

df_por_grupo = (
    df_notificaciones
    .groupBy("grupo_whatsapp")
    .agg(
        F.count("ticket").alias("n_notificaciones"),
        F.sum("clientes_afectados").alias("clientes_total"),
        F.sum(F.when(F.col("prioridad") == "P1", 1).otherwise(0)).alias("n_p1"),
        F.sum(F.when(F.col("prioridad") == "P2", 1).otherwise(0)).alias("n_p2"),
        F.sum(F.when(F.col("prioridad") == "P3", 1).otherwise(0)).alias("n_p3"),
        F.sum(F.when(F.col("nodo_vip") == True, 1).otherwise(0)).alias("n_vip"),
    )
    .orderBy(F.col("n_notificaciones").desc())
)

display(df_por_grupo)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Agregados: notificaciones por prioridad
# MAGIC Resumen de la urgencia global de la cola de notificaciones del NOC.

# COMMAND ----------

df_por_prioridad = (
    df_notificaciones
    .groupBy("prioridad")
    .agg(
        F.count("ticket").alias("n_tickets"),
        F.round(F.avg("clientes_afectados"), 0).cast("int").alias("clientes_prom"),
        F.sum("clientes_afectados").alias("clientes_total"),
        F.first("mensaje").alias("ejemplo_mensaje"),
    )
    .orderBy("prioridad")
)

display(df_por_prioridad)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Funcion `enviar_whatsapp` (SIMULADA)
# MAGIC
# MAGIC La funcion `enviar_whatsapp(grupo, mensaje)` esta en modo SIMULACION:
# MAGIC solo imprime el mensaje en la consola de Databricks. No realiza ningun
# MAGIC llamado real a APIs externas.
# MAGIC
# MAGIC **El bloque de integracion real esta completamente comentado al final
# MAGIC de este notebook.**

# COMMAND ----------

def enviar_whatsapp(grupo: str, mensaje: str, modo: str = "simulacion") -> dict:
    """
    Envia (o simula el envio de) un mensaje a un grupo de WhatsApp del NOC.

    Parametros
    ----------
    grupo   : str  Identificador del grupo, p.ej. 'GRP_NOC_COSTA'
    mensaje : str  Texto del mensaje a enviar (una sola linea)
    modo    : str  'simulacion' (default) imprime; 'produccion' llamaria a la API real.

    Retorna
    -------
    dict con status, grupo y preview del mensaje.
    """
    if modo != "produccion":
        # MODO SIMULACION: solo imprime, no llama ningun servicio externo
        print(f"[SIMULACION] --> Grupo: {grupo}")
        print(f"                 Mensaje: {mensaje[:120]}{'...' if len(mensaje) > 120 else ''}")
        return {"status": "simulado", "grupo": grupo, "mensaje_preview": mensaje[:80]}

    # MODO PRODUCCION: este bloque nunca se ejecuta en el notebook actual
    # Ver seccion de integracion al final del notebook.
    raise NotImplementedError(
        "El modo produccion no esta habilitado. "
        "Descomenta el bloque de integracion y configura Databricks Secrets."
    )


# Prueba de la funcion simulada
print("=== PRUEBA DE FUNCION SIMULADA ===")
resultado = enviar_whatsapp(
    grupo="GRP_NOC_COSTA",
    mensaje="[NOC-P1] Ticket: T-00123 | Ciudad: Barranquilla (COSTA) | Tec: HFC | Accion: TECNICO_URGENTE | Clientes: 4500 | Impacto: Critico"
)
print(f"Resultado: {resultado}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Ejecucion simulada del envio masivo
# MAGIC
# MAGIC Itera sobre las notificaciones de mayor prioridad y simula el envio.
# MAGIC Solo se procesan las P1 en este ejemplo para no saturar el log.
# MAGIC
# MAGIC **ADVERTENCIA:** En produccion, agregar control de rate-limiting, deduplicacion
# MAGIC de mensajes y registro de envios en una tabla Delta de auditoria.

# COMMAND ----------

# Recolectar solo las P1 para la simulacion (limitar a 10 filas en el ejemplo)
notificaciones_p1 = (
    df_notificaciones
    .filter(F.col("prioridad") == "P1")
    .select("ticket", "grupo_whatsapp", "prioridad", "mensaje")
    .limit(10)
    .collect()
)

print(f"=== ENVIO SIMULADO - PRIORIDAD P1 ({len(notificaciones_p1)} tickets) ===\n")

resultados_envio = []
for fila in notificaciones_p1:
    resultado = enviar_whatsapp(
        grupo=fila["grupo_whatsapp"],
        mensaje=fila["mensaje"],
        modo="simulacion"
    )
    resultados_envio.append({
        "ticket": fila["ticket"],
        "grupo": fila["grupo_whatsapp"],
        "prioridad": fila["prioridad"],
        "status": resultado["status"],
    })
    print()

print(f"\nResumen: {len(resultados_envio)} mensajes simulados.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Integracion con API real (BLOQUE DESHABILITADO)
# MAGIC
# MAGIC El siguiente bloque muestra COMO se integraria con:
# MAGIC - **WhatsApp Business Cloud API** (Meta) via HTTP
# MAGIC - **Twilio** via su SDK Python
# MAGIC
# MAGIC Para habilitar en produccion:
# MAGIC 1. Crear un Databricks Secret Scope: `databricks secrets create-scope --scope noc-whatsapp`
# MAGIC 2. Guardar las credenciales:
# MAGIC    - `databricks secrets put --scope noc-whatsapp --key whatsapp_token`
# MAGIC    - `databricks secrets put --scope noc-whatsapp --key whatsapp_phone_id`
# MAGIC    - O para Twilio: `--key twilio_account_sid`, `--key twilio_auth_token`, `--key twilio_from_number`
# MAGIC 3. Descomentar el bloque de codigo de abajo y cambiar `modo="simulacion"` a `modo="produccion"`.
# MAGIC
# MAGIC **NUNCA escribir tokens o contrasenas directamente en el codigo del notebook.**

# COMMAND ----------

# BLOQUE DE INTEGRACION REAL - COMPLETAMENTE COMENTADO POR SEGURIDAD
#
# ============================================================================
# OPCION A: WhatsApp Business Cloud API (Meta)
# ============================================================================
#
# import requests
#
# def enviar_whatsapp_real_meta(grupo_id_externo: str, mensaje: str) -> dict:
#     """
#     Envia un mensaje de texto via WhatsApp Business Cloud API (Meta).
#     Requiere: token de acceso y phone_number_id en Databricks Secrets.
#     """
#     # Leer credenciales desde Databricks Secrets (NUNCA hardcodear)
#     token      = dbutils.secrets.get(scope="noc-whatsapp", key="whatsapp_token")
#     phone_id   = dbutils.secrets.get(scope="noc-whatsapp", key="whatsapp_phone_id")
#
#     url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
#     headers = {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/json",
#     }
#     payload = {
#         "messaging_product": "whatsapp",
#         "to": grupo_id_externo,   # numero E.164 o ID del grupo segun config
#         "type": "text",
#         "text": {"body": mensaje},
#     }
#     response = requests.post(url, json=payload, headers=headers, timeout=10)
#     response.raise_for_status()
#     return response.json()
#
#
# ============================================================================
# OPCION B: Twilio WhatsApp API
# ============================================================================
#
# from twilio.rest import Client as TwilioClient
#
# def enviar_whatsapp_real_twilio(numero_destino: str, mensaje: str) -> dict:
#     """
#     Envia un mensaje via Twilio WhatsApp API.
#     Requiere: account_sid, auth_token y numero origen en Databricks Secrets.
#     """
#     account_sid  = dbutils.secrets.get(scope="noc-whatsapp", key="twilio_account_sid")
#     auth_token   = dbutils.secrets.get(scope="noc-whatsapp", key="twilio_auth_token")
#     from_number  = dbutils.secrets.get(scope="noc-whatsapp", key="twilio_from_number")
#
#     client = TwilioClient(account_sid, auth_token)
#     message = client.messages.create(
#         from_=f"whatsapp:{from_number}",
#         to=f"whatsapp:{numero_destino}",
#         body=mensaje,
#     )
#     return {"sid": message.sid, "status": message.status}
#
#
# ============================================================================
# TABLA DE AUDITORIA DE ENVIOS (recomendada para produccion)
# ============================================================================
#
# from pyspark.sql.types import StructType, StructField, StringType
# import datetime
#
# def registrar_envio_auditoria(ticket, grupo, prioridad, status, error_msg=None):
#     """Guarda un registro de cada envio en una tabla Delta de auditoria."""
#     registro = [(
#         ticket,
#         grupo,
#         prioridad,
#         status,
#         error_msg or "",
#         datetime.datetime.utcnow().isoformat(),
#     )]
#     schema = StructType([
#         StructField("ticket",        StringType(), True),
#         StructField("grupo",         StringType(), True),
#         StructField("prioridad",     StringType(), True),
#         StructField("status_envio",  StringType(), True),
#         StructField("error_msg",     StringType(), True),
#         StructField("ts_envio_utc",  StringType(), True),
#     ])
#     df_reg = spark.createDataFrame(registro, schema)
#     df_reg.write.mode("append").format("delta").saveAsTable(
#         f"{catalogo}.gold.auditoria_envios_whatsapp"
#     )

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Notas finales para el equipo de operaciones
# MAGIC
# MAGIC ### Habilitacion del envio real
# MAGIC 1. Solicitar al administrador de Databricks la creacion del Secret Scope `noc-whatsapp`.
# MAGIC 2. Cargar las credenciales de la API elegida (Meta o Twilio).
# MAGIC 3. Descomentar la funcion correspondiente en la seccion anterior.
# MAGIC 4. Cambiar el parametro `modo` en la llamada a `enviar_whatsapp()` de
# MAGIC    `"simulacion"` a `"produccion"`.
# MAGIC 5. Probar primero con un unico ticket de prioridad baja antes de habilitar el envio masivo.
# MAGIC
# MAGIC ### Programacion automatica (Jobs)
# MAGIC - Este notebook puede programarse como un **Databricks Job** con trigger
# MAGIC   por schedule (ej. cada 15 minutos) o por arrival de nuevos datos en la tabla gold.
# MAGIC - Configurar alertas de fallo del job via email o Slack en la seccion Notifications del job.
# MAGIC
# MAGIC ### Rate limiting y deduplicacion
# MAGIC - WhatsApp Business API tiene limites de mensajes por segundo segun el tier de cuenta.
# MAGIC - Implementar la tabla `gold.auditoria_envios_whatsapp` para evitar enviar el mismo
# MAGIC   ticket dos veces si el job se ejecuta solapado.
# MAGIC - Usar `LEFT ANTI JOIN` contra la tabla de auditoria antes de enviar.
# MAGIC
# MAGIC ### Conformidad y privacidad
# MAGIC - Los mensajes de operaciones de red no contienen datos personales de usuarios finales,
# MAGIC   solo informacion tecnica de tickets NOC.
# MAGIC - Verificar con el area legal que el uso de WhatsApp Business para comunicaciones
# MAGIC   internas de operaciones cumple con la politica de uso aceptable de la empresa.
