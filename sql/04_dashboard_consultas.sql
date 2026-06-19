-- =============================================================================
-- PROYECTO NOC TELECOMUNICACIONES - COLOMBIA
-- Dashboard de Recomendacion de Cuadrillas
-- Archivo: sql/04_dashboard_consultas.sql
--
-- Proposito: Consultas SQL que respaldan el dashboard del NOC. Cada consulta
-- corresponde a un KPI o visualizacion del notebook 05_dashboard.py.
-- Ejecutar sobre workspace.gold.decision_cuadrilla en un SQL Warehouse de
-- Databricks o como consultas de Databricks SQL Dashboard.
--
-- Autor: Mario Daniel Enrique Perez Jimenez
-- Fecha: 2026-06-18
-- =============================================================================


-- =============================================================================
-- KPI 1: Distribucion de accion_recomendada (conteo y porcentaje)
-- =============================================================================

-- titulo: Distribucion Global de Acciones Recomendadas
SELECT
    accion_recomendada,
    COUNT(ticket)                                                        AS cantidad,
    ROUND(COUNT(ticket) * 100.0 / SUM(COUNT(ticket)) OVER (), 2)         AS porcentaje
FROM workspace.gold.decision_cuadrilla
GROUP BY accion_recomendada
ORDER BY cantidad DESC;


-- =============================================================================
-- KPI 2a: Acciones por region
-- =============================================================================

-- titulo: Acciones Recomendadas por Region
SELECT
    region,
    accion_recomendada,
    COUNT(ticket)                                                        AS cantidad,
    ROUND(COUNT(ticket) * 100.0 / SUM(COUNT(ticket)) OVER (PARTITION BY region), 2) AS pct_dentro_region
FROM workspace.gold.decision_cuadrilla
GROUP BY region, accion_recomendada
ORDER BY region, cantidad DESC;


-- =============================================================================
-- KPI 2b: Acciones por tecnologia
-- =============================================================================

-- titulo: Acciones Recomendadas por Tecnologia (HFC vs GPON)
SELECT
    tecnologia,
    accion_recomendada,
    COUNT(ticket)                                                        AS cantidad,
    ROUND(COUNT(ticket) * 100.0 / SUM(COUNT(ticket)) OVER (PARTITION BY tecnologia), 2) AS pct_dentro_tecnologia
FROM workspace.gold.decision_cuadrilla
GROUP BY tecnologia, accion_recomendada
ORDER BY tecnologia, cantidad DESC;


-- =============================================================================
-- KPI 3: Porcentaje promedio de autorrestablecimiento por region
-- =============================================================================

-- titulo: Tasa de Autorrestablecimiento Promedio por Region
SELECT
    region,
    ROUND(AVG(pct_autorrestablecimiento_sector) * 100, 2)               AS pct_autorres_promedio,
    COUNT(ticket)                                                        AS total_tickets,
    SUM(CASE WHEN accion_recomendada = 'ESPERAR_AUTORRESTABLECIMIENTO'
             THEN 1 ELSE 0 END)                                         AS tickets_esperados
FROM workspace.gold.decision_cuadrilla
GROUP BY region
ORDER BY pct_autorres_promedio DESC;


-- =============================================================================
-- KPI 4a: Tiempo promedio de resolucion por accion recomendada
-- =============================================================================

-- titulo: Tiempo de Resolucion Promedio por Tipo de Accion (minutos)
SELECT
    accion_recomendada,
    ROUND(AVG(tiempo_resolucion_min), 1)                                 AS tiempo_prom_min,
    ROUND(PERCENTILE_APPROX(tiempo_resolucion_min, 0.5), 1)              AS tiempo_mediana_min,
    MIN(tiempo_resolucion_min)                                           AS tiempo_min,
    MAX(tiempo_resolucion_min)                                           AS tiempo_max,
    COUNT(ticket)                                                        AS n_tickets
FROM workspace.gold.decision_cuadrilla
GROUP BY accion_recomendada
ORDER BY tiempo_prom_min DESC;


-- =============================================================================
-- KPI 4b: Tiempo promedio de resolucion por tecnologia
-- =============================================================================

-- titulo: Tiempo de Resolucion Promedio por Tecnologia (minutos)
SELECT
    tecnologia,
    ROUND(AVG(tiempo_resolucion_min), 1)                                 AS tiempo_prom_min,
    ROUND(PERCENTILE_APPROX(tiempo_resolucion_min, 0.5), 1)              AS tiempo_mediana_min,
    COUNT(ticket)                                                        AS n_tickets
FROM workspace.gold.decision_cuadrilla
GROUP BY tecnologia
ORDER BY tiempo_prom_min DESC;


-- =============================================================================
-- KPI 5: Clientes afectados totales por region
-- =============================================================================

-- titulo: Impacto a Clientes por Region
SELECT
    region,
    SUM(clientes_afectados)                                              AS clientes_afectados_total,
    ROUND(AVG(clientes_afectados), 0)                                    AS clientes_afectados_promedio,
    MAX(clientes_afectados)                                              AS clientes_afectados_max,
    COUNT(ticket)                                                        AS n_tickets,
    ROUND(SUM(clientes_afectados) * 100.0 / SUM(SUM(clientes_afectados)) OVER (), 2) AS pct_del_total
FROM workspace.gold.decision_cuadrilla
GROUP BY region
ORDER BY clientes_afectados_total DESC;


-- =============================================================================
-- KPI 6: Notificaciones requeridas por grupo WhatsApp
-- =============================================================================

-- titulo: Notificaciones Pendientes por Grupo WhatsApp del NOC
SELECT
    CONCAT('GRP_NOC_', region)                                           AS grupo_whatsapp,
    region,
    COUNT(ticket)                                                        AS n_notificaciones,
    SUM(clientes_afectados)                                              AS clientes_afectados_total,
    SUM(CASE WHEN impacto = 'Critico' THEN 1 ELSE 0 END)                AS n_criticos,
    SUM(CASE WHEN nodo_vip = true THEN 1 ELSE 0 END)                    AS n_vip
FROM workspace.gold.decision_cuadrilla
WHERE requiere_notificacion = true
GROUP BY region
ORDER BY n_notificaciones DESC;


-- =============================================================================
-- KPI 6 ampliado: Desglose de motivos de notificacion por region
-- =============================================================================

-- titulo: Motivos de Notificacion por Region
SELECT
    region,
    COUNT(ticket)                                                        AS total_notificaciones,
    SUM(CASE WHEN nodo_vip = true THEN 1 ELSE 0 END)                    AS por_nodo_vip,
    SUM(CASE WHEN clientes_afectados > 2000 THEN 1 ELSE 0 END)          AS por_clientes_gt_2000,
    SUM(CASE WHEN impacto IN ('Alto','Critico') THEN 1 ELSE 0 END)      AS por_impacto_alto_critico,
    SUM(CASE WHEN urgencia IN ('Alta','Critica') THEN 1 ELSE 0 END)     AS por_urgencia_alta_critica
FROM workspace.gold.decision_cuadrilla
WHERE requiere_notificacion = true
GROUP BY region
ORDER BY total_notificaciones DESC;


-- =============================================================================
-- KPI 7: Top 10 sectores (cable_padre) por numero de fallas
-- =============================================================================

-- titulo: Top 10 Sectores con Mayor Recurrencia de Fallas
SELECT
    cable_padre,
    MAX(n_fallas_sector)                                                 AS max_fallas_sector,
    COUNT(ticket)                                                        AS n_tickets,
    SUM(clientes_afectados)                                              AS clientes_afectados_total,
    ROUND(AVG(tiempo_resolucion_min), 1)                                 AS tiempo_prom_resolucion_min,
    COLLECT_SET(region)[0]                                               AS region_principal
FROM workspace.gold.decision_cuadrilla
GROUP BY cable_padre
ORDER BY max_fallas_sector DESC
LIMIT 10;


-- =============================================================================
-- KPI Adicional: Distribucion de impacto
-- =============================================================================

-- titulo: Distribucion de Nivel de Impacto de Tickets
SELECT
    impacto,
    COUNT(ticket)                                                        AS cantidad,
    ROUND(COUNT(ticket) * 100.0 / SUM(COUNT(ticket)) OVER (), 2)         AS porcentaje
FROM workspace.gold.decision_cuadrilla
GROUP BY impacto
ORDER BY
    CASE impacto
        WHEN 'Critico' THEN 1
        WHEN 'Alto'    THEN 2
        WHEN 'Medio'   THEN 3
        ELSE 4
    END;


-- =============================================================================
-- KPI Adicional: Distribucion de urgencia
-- =============================================================================

-- titulo: Distribucion de Nivel de Urgencia de Tickets
SELECT
    urgencia,
    COUNT(ticket)                                                        AS cantidad,
    ROUND(COUNT(ticket) * 100.0 / SUM(COUNT(ticket)) OVER (), 2)         AS porcentaje
FROM workspace.gold.decision_cuadrilla
GROUP BY urgencia
ORDER BY
    CASE urgencia
        WHEN 'Critica' THEN 1
        WHEN 'Alta'    THEN 2
        WHEN 'Media'   THEN 3
        ELSE 4
    END;


-- =============================================================================
-- KPI Adicional: Tickets en bateria por region (riesgo de corte electrico)
-- =============================================================================

-- titulo: Tickets con Nodos en Bateria por Region
SELECT
    region,
    COUNT(ticket)                                                        AS n_tickets,
    SUM(CASE WHEN flag_en_bateria = true THEN 1 ELSE 0 END)             AS n_en_bateria,
    ROUND(AVG(nodos_sector_en_bateria), 1)                              AS prom_nodos_en_bateria,
    SUM(CASE WHEN flag_en_bateria = true THEN clientes_afectados ELSE 0 END) AS clientes_en_riesgo_bateria
FROM workspace.gold.decision_cuadrilla
GROUP BY region
ORDER BY n_en_bateria DESC;


-- =============================================================================
-- Resumen ejecutivo: una sola fila con los KPIs principales
-- =============================================================================

-- titulo: Resumen Ejecutivo NOC - Metricas Globales
SELECT
    COUNT(ticket)                                                        AS total_tickets,
    SUM(CASE WHEN requiere_notificacion = true THEN 1 ELSE 0 END)        AS total_con_notificacion,
    SUM(clientes_afectados)                                              AS total_clientes_afectados,
    ROUND(AVG(tiempo_resolucion_min), 1)                                 AS tiempo_resolucion_prom_min,
    SUM(CASE WHEN accion_recomendada = 'TECNICO_URGENTE' THEN 1 ELSE 0 END) AS total_tecnico_urgente,
    SUM(CASE WHEN accion_recomendada = 'DESPACHAR_CUADRILLA' THEN 1 ELSE 0 END) AS total_despachar,
    SUM(CASE WHEN accion_recomendada = 'ESPERAR_AUTORRESTABLECIMIENTO' THEN 1 ELSE 0 END) AS total_esperar,
    SUM(CASE WHEN nodo_vip = true THEN 1 ELSE 0 END)                    AS total_nodos_vip,
    ROUND(AVG(pct_autorrestablecimiento_sector) * 100, 2)               AS pct_autorres_global
FROM workspace.gold.decision_cuadrilla;
