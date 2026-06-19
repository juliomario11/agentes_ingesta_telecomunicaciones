CREATE OR REPLACE TABLE workspace.gold.decision_cuadrilla
COMMENT 'Gold - dataset de decision por ticket + agregados de sector + target. Linaje: workspace.silver.tickets_noc -> workspace.gold.decision_cuadrilla'
AS
WITH base AS (
  SELECT *,
    avg(CASE WHEN restablecio_autonomo THEN 1.0 ELSE 0.0 END) OVER (PARTITION BY cable_padre) AS pct_autorrestablecimiento_sector,
    count(*) OVER (PARTITION BY cable_padre) AS n_fallas_sector
  FROM workspace.silver.tickets_noc
)
SELECT
  ticket, region, ciudad, tecnologia,
  elementos_afectados, cantidad_nodos, cantidad_arpones,
  nodo_vip, impacto, urgencia, clientes_afectados,
  existe_en_cacti, fuente_monitoreo,
  fuente_voltaje, fuente_amperaje, flag_en_bateria, nodos_sector_en_bateria,
  correlacion_grafica_monitoreo, delta_correlacion_min, falla_simultanea_nodo_arpon,
  tiempo_resolucion_min, requiere_notificacion,
  cable_padre,
  round(pct_autorrestablecimiento_sector, 3) AS pct_autorrestablecimiento_sector,
  cast(n_fallas_sector AS int) AS n_fallas_sector,
  forma_resolucion,
  CASE WHEN falla_simultanea_nodo_arpon THEN 'TECNICO_URGENTE'
       WHEN flag_en_bateria AND nodos_sector_en_bateria >= 2 AND correlacion_grafica_monitoreo THEN 'ESPERAR_AUTORRESTABLECIMIENTO'
       ELSE 'DESPACHAR_CUADRILLA' END AS accion_recomendada
FROM base
