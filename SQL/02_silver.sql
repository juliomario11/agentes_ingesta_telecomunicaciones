CREATE OR REPLACE TABLE workspace.silver.tickets_noc
COMMENT 'Silver - tickets NOC limpios + features. Linaje: workspace.bronze.tickets_noc -> workspace.silver.tickets_noc'
AS
SELECT
  ticket, region, departamento, ciudad, territorialidad,
  tecnologia,
  cantidad_nodos, cantidad_arpones,
  (cantidad_nodos + cantidad_arpones) AS elementos_afectados,
  cmts, olt, interfaz, cable_padre, cable_hijo,
  nodo_vip,
  initcap(impacto) AS impacto,
  initcap(urgencia) AS urgencia,
  clientes_afectados,
  existe_en_cacti,
  fuente_monitoreo,
  fuente_voltaje, fuente_amperaje,
  (tecnologia = 'HFC' AND fuente_voltaje > 0 AND fuente_voltaje < 50) AS flag_en_bateria,
  nodos_sector_en_bateria,
  correlacion_grafica_monitoreo,
  delta_correlacion_min,
  falla_simultanea_nodo_arpon,
  restablecio_autonomo,
  forma_resolucion,
  solucion_aplicada,
  hora_caida, hora_restablecimiento,
  cast((unix_timestamp(hora_restablecimiento) - unix_timestamp(hora_caida)) / 60 AS int) AS tiempo_resolucion_min,
  requiere_notificacion,
  grupo_whatsapp
FROM workspace.bronze.tickets_noc
WHERE ticket IS NOT NULL
  AND tecnologia IN ('HFC','GPON')
  AND hora_restablecimiento >= hora_caida
  AND fuente_voltaje >= 0
  AND fuente_amperaje >= 0
