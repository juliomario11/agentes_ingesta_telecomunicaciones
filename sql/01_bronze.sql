CREATE OR REPLACE TABLE workspace.bronze.tickets_noc
COMMENT 'Bronze - tickets crudos del NOC (simulados). Proyecto agentes_ingesta_telecomunicaciones. Logica replicada de src/generar_datos.py'
AS
WITH geo AS (
  SELECT (row_number() OVER (ORDER BY region, ciudad)) - 1 AS gi, region, departamento, ciudad
  FROM (VALUES
    ('COSTA','Atlantico','Barranquilla'),
    ('COSTA','Bolivar','Cartagena'),
    ('COSTA','Magdalena','Santa Marta'),
    ('COSTA','Cordoba','Monteria'),
    ('ANDINA','Antioquia','Medellin'),
    ('ANDINA','Caldas','Manizales'),
    ('ANDINA','Risaralda','Pereira'),
    ('ANDINA','Valle del Cauca','Cali'),
    ('ORIENTE','Santander','Bucaramanga'),
    ('ORIENTE','Norte de Santander','Cucuta'),
    ('ORIENTE','Boyaca','Tunja'),
    ('BOGOTA','Cundinamarca','Bogota'),
    ('BOGOTA','Cundinamarca','Soacha'),
    ('BOGOTA','Cundinamarca','Chia'),
    ('SUR','Narino','Pasto'),
    ('SUR','Huila','Neiva'),
    ('SUR','Cauca','Popayan'),
    ('SUR','Tolima','Ibague')
  ) AS g(region, departamento, ciudad)
),
r AS (
  SELECT
    id,
    cast(floor(rand(1)*18) as int) AS gi,
    rand(2) AS u_tec, rand(3) AS u_nodos, rand(4) AS u_arpones,
    rand(5) AS u_cmts, rand(6) AS u_olt, rand(7) AS u_if1, rand(8) AS u_if2,
    rand(9) AS u_cp, rand(10) AS u_chf, rand(11) AS u_chn,
    rand(12) AS u_corte, rand(13) AS u_volt, rand(14) AS u_amp, rand(15) AS u_nsec,
    rand(16) AS u_falla, rand(17) AS u_corr, rand(18) AS u_delta,
    rand(19) AS u_vip, rand(20) AS u_imp, rand(21) AS u_urg,
    rand(22) AS u_clib, rand(23) AS u_clim, rand(24) AS u_dur,
    rand(25) AS u_cd, rand(26) AS u_ch, rand(27) AS u_cm,
    rand(28) AS u_terr, rand(29) AS u_desc, rand(30) AS u_itsm, rand(31) AS u_wo,
    rand(32) AS u_tecid, rand(33) AS u_adj, rand(34) AS u_cacti, rand(35) AS u_sol
  FROM range(0, 1500)
),
g_geo AS (
  SELECT geo.region, geo.departamento, geo.ciudad, r.*
  FROM r JOIN geo ON geo.gi = r.gi
),
g_tec AS (
  SELECT *, CASE WHEN u_tec < 0.55 THEN 'HFC' ELSE 'GPON' END AS tecnologia
  FROM g_geo
),
g_a AS (
  SELECT *,
    CASE WHEN tecnologia='HFC' THEN cast(floor(u_nodos*8) as int)+1 ELSE 0 END AS cantidad_nodos,
    CASE WHEN tecnologia='GPON' THEN cast(floor(u_arpones*12) as int)+1 ELSE 0 END AS cantidad_arpones,
    CASE WHEN tecnologia='HFC' THEN concat('CMTS_', substr(region,1,3),'_', lpad(cast(cast(floor(u_cmts*29) as int)+1 as string),2,'0')) ELSE '' END AS cmts,
    CASE WHEN tecnologia='GPON' THEN concat('OLT_', substr(region,1,3),'_', lpad(cast(cast(floor(u_olt*29) as int)+1 as string),2,'0')) ELSE '' END AS olt,
    concat('GE0/', cast(cast(floor(u_if1*8) as int) as string), '/', cast(cast(floor(u_if2*48) as int) as string)) AS interfaz,
    concat('CP_', substr(region,1,3),'_', lpad(cast(cast(floor(u_cp*59) as int)+1 as string),3,'0')) AS cable_padre,
    CASE WHEN u_chf < 0.5 THEN concat('CH_', lpad(cast(cast(floor(u_chn*199) as int)+1 as string),3,'0')) ELSE '' END AS cable_hijo,
    (u_corte < 0.22) AS corte_electrico_sector,
    (u_falla < 0.06) AS falla_simultanea_nodo_arpon,
    (u_vip < 0.12) AS nodo_vip,
    CASE WHEN tecnologia='HFC' THEN 'CACTI' ELSE 'ZABBIX' END AS fuente_monitoreo,
    element_at(array('Urbano','Rural','Periurbano'), cast(floor(u_terr*3) as int)+1) AS territorialidad,
    element_at(array('Perdida de senal en el sector','Degradacion de potencia optica','Intermitencia en el servicio','Caida total del elemento de red','Alta tasa de errores en la interfaz','Sin comunicacion con el elemento'), cast(floor(u_desc*6) as int)+1) AS descripcion,
    concat('INC', cast(cast(floor(u_itsm*9000000) as int)+1000000 as string)) AS itsm_servicenow,
    concat('WO-', cast(cast(floor(u_wo*900000) as int)+100000 as string)) AS workorder_salesforce,
    concat('TEC_', lpad(cast(cast(floor(u_tecid*119) as int)+1 as string),3,'0')) AS tecnico_asignado,
    cast(floor(u_adj*6) as int) AS adjuntos,
    (tecnologia='HFC' AND u_cacti < 0.9) AS existe_en_cacti,
    concat('GRP_NOC_', region) AS grupo_whatsapp,
    to_timestamp('2026-01-01 00:00:00') + make_interval(0,0,0, cast(floor(u_cd*150) as int), cast(floor(u_ch*24) as int), cast(floor(u_cm*60) as int), 0) AS hora_caida
  FROM g_tec
),
g_energy AS (
  SELECT *,
    CASE WHEN tecnologia='HFC' THEN (CASE WHEN corte_electrico_sector THEN round(40+u_volt*7,2) ELSE round(52+u_volt*4,2) END) ELSE 0.0 END AS fuente_voltaje,
    CASE WHEN tecnologia='HFC' THEN (CASE WHEN corte_electrico_sector THEN round(0.5+u_amp*2.5,2) ELSE round(4+u_amp*5,2) END) ELSE 0.0 END AS fuente_amperaje,
    (tecnologia='HFC' AND corte_electrico_sector) AS flag_en_bateria,
    CASE WHEN (tecnologia='HFC' AND corte_electrico_sector) THEN cast(floor(u_nsec * greatest(1, cantidad_nodos+1)) as int)+2 ELSE 0 END AS nodos_sector_en_bateria
  FROM g_a
),
g_corr AS (
  SELECT *,
    CASE WHEN corte_electrico_sector AND NOT falla_simultanea_nodo_arpon THEN (u_corr < 0.85) ELSE (u_corr < 0.15) END AS correlacion_grafica_monitoreo
  FROM g_energy
),
g_tgt AS (
  SELECT *,
    CASE WHEN correlacion_grafica_monitoreo THEN cast(floor(u_delta*8) as int) ELSE cast(floor(u_delta*220) as int)+20 END AS delta_correlacion_min,
    CASE WHEN falla_simultanea_nodo_arpon THEN 'TECNICO_URGENTE'
         WHEN flag_en_bateria AND nodos_sector_en_bateria>=2 AND correlacion_grafica_monitoreo THEN 'ESPERAR_AUTORRESTABLECIMIENTO'
         ELSE 'DESPACHAR_CUADRILLA' END AS accion_recomendada,
    CASE WHEN falla_simultanea_nodo_arpon THEN 'TECNICO_URGENTE'
         WHEN flag_en_bateria AND nodos_sector_en_bateria>=2 AND correlacion_grafica_monitoreo THEN 'AUTORRESTABLECIMIENTO'
         ELSE 'CUADRILLA' END AS forma_resolucion,
    (NOT falla_simultanea_nodo_arpon AND flag_en_bateria AND nodos_sector_en_bateria>=2 AND correlacion_grafica_monitoreo) AS restablecio_autonomo
  FROM g_corr
),
g_dur AS (
  SELECT *,
    CASE forma_resolucion
      WHEN 'AUTORRESTABLECIMIENTO' THEN cast(floor(u_dur*80) as int)+10
      WHEN 'TECNICO_URGENTE' THEN cast(floor(u_dur*240) as int)+60
      ELSE cast(floor(u_dur*435) as int)+45 END AS tiempo_resolucion_min,
    CASE WHEN falla_simultanea_nodo_arpon THEN (CASE WHEN u_imp<0.7 THEN 'Critico' ELSE 'Alto' END)
         WHEN nodo_vip THEN (CASE WHEN u_imp<0.2 THEN 'Critico' WHEN u_imp<0.7 THEN 'Alto' ELSE 'Medio' END)
         ELSE element_at(array('Bajo','Medio','Alto','Critico'), cast(floor(u_imp*4) as int)+1) END AS impacto,
    CASE WHEN falla_simultanea_nodo_arpon THEN (CASE WHEN u_urg<0.7 THEN 'Critica' ELSE 'Alta' END)
         WHEN nodo_vip THEN (CASE WHEN u_urg<0.2 THEN 'Critica' WHEN u_urg<0.7 THEN 'Alta' ELSE 'Media' END)
         ELSE element_at(array('Baja','Media','Alta','Critica'), cast(floor(u_urg*4) as int)+1) END AS urgencia,
    CASE WHEN falla_simultanea_nodo_arpon
         THEN cast(((cast(floor(u_clib*550) as int)+50) * greatest(1, cantidad_nodos+cantidad_arpones)) * (2+u_clim*2) as int)
         ELSE (cast(floor(u_clib*550) as int)+50) * greatest(1, cantidad_nodos+cantidad_arpones) END AS clientes_afectados
  FROM g_tgt
),
g_fin AS (
  SELECT *,
    hora_caida + make_interval(0,0,0,0,0, tiempo_resolucion_min, 0) AS hora_restablecimiento,
    (nodo_vip OR clientes_afectados>2000 OR impacto IN ('Alto','Critico') OR urgencia IN ('Alta','Critica')) AS requiere_notificacion,
    concat(descripcion, ' (', tecnologia, ') en ', ciudad) AS resumen,
    CASE forma_resolucion
      WHEN 'AUTORRESTABLECIMIENTO' THEN element_at(array('Servicio restablecido al normalizarse la energia comercial del sector','Falla externa de energia; elemento volvio solo sin intervencion','Recuperacion automatica confirmada en grafica de monitoreo'), cast(floor(u_sol*3) as int)+1)
      WHEN 'CUADRILLA' THEN element_at(array('Cuadrilla reemplazo conector danado','Empalme de fibra reparado en sitio','Cambio de tarjeta en el elemento','Reconfiguracion de la interfaz afectada'), cast(floor(u_sol*4) as int)+1)
      ELSE element_at(array('Tecnico urgente por caida masiva de NODOS y ARPONES','Atencion prioritaria por dano grave multielemento','Despliegue urgente: afectacion simultanea HFC y GPON'), cast(floor(u_sol*3) as int)+1) END AS solucion_aplicada
  FROM g_dur
)
SELECT
  concat('TKT-', lpad(cast(id+1 as string),6,'0')) AS ticket,
  region, departamento, ciudad, territorialidad,
  itsm_servicenow, workorder_salesforce,
  cast(clientes_afectados as int) AS clientes_afectados,
  tecnologia,
  cast(cantidad_nodos as int) AS cantidad_nodos,
  cast(cantidad_arpones as int) AS cantidad_arpones,
  cmts, olt, interfaz, cable_padre, cable_hijo,
  nodo_vip, impacto, urgencia, grupo_whatsapp,
  descripcion, resumen, tecnico_asignado,
  'Diagnostico inicial registrado' AS avances,
  cast(adjuntos as int) AS adjuntos,
  existe_en_cacti,
  cast(fuente_voltaje as double) AS fuente_voltaje,
  cast(fuente_amperaje as double) AS fuente_amperaje,
  flag_en_bateria,
  cast(nodos_sector_en_bateria as int) AS nodos_sector_en_bateria,
  forma_resolucion, restablecio_autonomo,
  hora_caida, hora_restablecimiento,
  fuente_monitoreo, correlacion_grafica_monitoreo,
  cast(delta_correlacion_min as int) AS delta_correlacion_min,
  falla_simultanea_nodo_arpon, solucion_aplicada,
  cast(tiempo_resolucion_min as int) AS tiempo_resolucion_min,
  requiere_notificacion, accion_recomendada
FROM g_fin
