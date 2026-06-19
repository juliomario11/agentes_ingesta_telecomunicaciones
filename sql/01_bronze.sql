-- =============================================================================
-- 01_bronze.sql  ·  Landing zone (Volume)  ->  Bronze
-- Proyecto: agentes_ingesta_telecomunicaciones (NOC)
--
-- Ingesta de la capa BRONZE: lee el CSV CRUDO desde el Volume de Unity Catalog
-- (landing zone) y lo materializa SIN transformar en workspace.bronze.tickets_noc.
-- Esto realiza el flujo de la arquitectura:  Fuente -> Landing zone (Volume) -> Bronze.
--
-- Linaje:
--   /Volumes/workspace/bronze/landing_zone/sample_tickets.csv  ->  workspace.bronze.tickets_noc
--
-- El CSV lo produce src/generar_datos.py y lo deja en el Volume el orquestador
-- pipeline/run_pipeline.py (tambien puede subirse manualmente al Volume).
--
-- Nota: la version "todo en SQL" que GENERA los datos de forma sintetica (sin
-- depender del Volume) se conserva como respaldo en sql/pipeline_noc_medallion.sql.
--
-- Autor: Mario Daniel Enrique Perez Jimenez
-- =============================================================================

CREATE OR REPLACE TABLE workspace.bronze.tickets_noc
COMMENT 'Bronze - tickets crudos del NOC ingeridos desde el Volume landing_zone (sample_tickets.csv). Proyecto agentes_ingesta_telecomunicaciones.'
AS
WITH raw AS (
  SELECT *
  FROM read_files(
    '/Volumes/workspace/bronze/landing_zone/sample_tickets.csv',
    format      => 'csv',
    header      => true,
    inferSchema => false      -- leemos como string y casteamos explicitamente abajo
  )
)
SELECT
  CAST(ticket                        AS STRING)    AS ticket,
  CAST(region                        AS STRING)    AS region,
  CAST(departamento                  AS STRING)    AS departamento,
  CAST(ciudad                        AS STRING)    AS ciudad,
  CAST(territorialidad               AS STRING)    AS territorialidad,
  CAST(itsm_servicenow               AS STRING)    AS itsm_servicenow,
  CAST(workorder_salesforce          AS STRING)    AS workorder_salesforce,
  CAST(clientes_afectados            AS INT)       AS clientes_afectados,
  CAST(tecnologia                    AS STRING)    AS tecnologia,
  CAST(cantidad_nodos                AS INT)       AS cantidad_nodos,
  CAST(cantidad_arpones              AS INT)       AS cantidad_arpones,
  CAST(cmts                          AS STRING)    AS cmts,
  CAST(olt                           AS STRING)    AS olt,
  CAST(interfaz                      AS STRING)    AS interfaz,
  CAST(cable_padre                   AS STRING)    AS cable_padre,
  CAST(cable_hijo                    AS STRING)    AS cable_hijo,
  CAST(nodo_vip                      AS BOOLEAN)   AS nodo_vip,
  CAST(impacto                       AS STRING)    AS impacto,
  CAST(urgencia                      AS STRING)    AS urgencia,
  CAST(grupo_whatsapp                AS STRING)    AS grupo_whatsapp,
  CAST(descripcion                   AS STRING)    AS descripcion,
  CAST(resumen                       AS STRING)    AS resumen,
  CAST(tecnico_asignado              AS STRING)    AS tecnico_asignado,
  CAST(avances                       AS STRING)    AS avances,
  CAST(adjuntos                      AS INT)       AS adjuntos,
  CAST(existe_en_cacti               AS BOOLEAN)   AS existe_en_cacti,
  CAST(fuente_voltaje                AS DOUBLE)    AS fuente_voltaje,
  CAST(fuente_amperaje               AS DOUBLE)    AS fuente_amperaje,
  CAST(flag_en_bateria               AS BOOLEAN)   AS flag_en_bateria,
  CAST(nodos_sector_en_bateria       AS INT)       AS nodos_sector_en_bateria,
  CAST(forma_resolucion              AS STRING)    AS forma_resolucion,
  CAST(restablecio_autonomo          AS BOOLEAN)   AS restablecio_autonomo,
  CAST(hora_caida                    AS TIMESTAMP) AS hora_caida,
  CAST(hora_restablecimiento         AS TIMESTAMP) AS hora_restablecimiento,
  CAST(fuente_monitoreo              AS STRING)    AS fuente_monitoreo,
  CAST(correlacion_grafica_monitoreo AS BOOLEAN)   AS correlacion_grafica_monitoreo,
  CAST(delta_correlacion_min         AS INT)       AS delta_correlacion_min,
  CAST(falla_simultanea_nodo_arpon   AS BOOLEAN)   AS falla_simultanea_nodo_arpon,
  CAST(solucion_aplicada             AS STRING)    AS solucion_aplicada,
  CAST(tiempo_resolucion_min         AS INT)       AS tiempo_resolucion_min,
  CAST(requiere_notificacion         AS BOOLEAN)   AS requiere_notificacion,
  CAST(accion_recomendada            AS STRING)    AS accion_recomendada
FROM raw;
