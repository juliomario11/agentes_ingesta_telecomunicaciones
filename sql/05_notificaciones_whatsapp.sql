-- =============================================================================
-- PROYECTO NOC TELECOMUNICACIONES - COLOMBIA
-- Vista de Notificaciones WhatsApp
-- Archivo: sql/05_notificaciones_whatsapp.sql
--
-- Proposito: Crea la vista workspace.gold.notificaciones_whatsapp con todos
-- los tickets que requieren notificacion activa al NOC. Incluye el grupo
-- WhatsApp derivado de la region, el motivo de notificacion construido
-- dinamicamente, la prioridad (P1/P2/P3) y un mensaje listo para enviar.
--
-- Reglas de notificacion (ya precalculadas en requiere_notificacion):
--   - nodo_vip = true
--   - clientes_afectados > 2000
--   - impacto IN ('Alto', 'Critico')
--   - urgencia IN ('Alta', 'Critica')
--
-- Prioridad:
--   P1: accion = TECNICO_URGENTE  O  impacto = 'Critico'  O  urgencia = 'Critica'
--   P2: impacto = 'Alto'  O  urgencia = 'Alta'  O  nodo_vip = true
--   P3: resto (clientes > 2000 sin otro criterio mayor)
--
-- Autor: Mario Daniel Enrique Perez Jimenez
-- Fecha: 2026-06-18
-- =============================================================================

CREATE OR REPLACE VIEW workspace.gold.notificaciones_whatsapp AS

WITH base AS (
    SELECT
        ticket,
        region,
        ciudad,
        tecnologia,
        elementos_afectados,
        cantidad_nodos,
        cantidad_arpones,
        nodo_vip,
        impacto,
        urgencia,
        clientes_afectados,
        fuente_monitoreo,
        flag_en_bateria,
        tiempo_resolucion_min,
        requiere_notificacion,
        cable_padre,
        n_fallas_sector,
        accion_recomendada,
        -- Derivar grupo WhatsApp (no existe en gold, se construye desde region)
        CONCAT('GRP_NOC_', region)                                       AS grupo_whatsapp
    FROM workspace.gold.decision_cuadrilla
    WHERE requiere_notificacion = true
),

con_motivo AS (
    SELECT
        *,
        -- Construir motivo_notificacion: concatena todas las reglas que se cumplen
        TRIM(
            CONCAT_WS(' | ',
                CASE WHEN nodo_vip = true
                     THEN 'NODO_VIP'
                     ELSE NULL END,
                CASE WHEN clientes_afectados > 2000
                     THEN CONCAT('MAS_2000_CLIENTES(', CAST(clientes_afectados AS STRING), ')')
                     ELSE NULL END,
                CASE WHEN impacto IN ('Alto', 'Critico')
                     THEN CONCAT('IMPACTO_', UPPER(impacto))
                     ELSE NULL END,
                CASE WHEN urgencia IN ('Alta', 'Critica')
                     THEN CONCAT('URGENCIA_', UPPER(urgencia))
                     ELSE NULL END
            )
        )                                                                AS motivo_notificacion
    FROM base
),

con_prioridad AS (
    SELECT
        *,
        -- Calcular prioridad segun criticidad de la accion e impacto
        CASE
            WHEN accion_recomendada = 'TECNICO_URGENTE'
              OR impacto = 'Critico'
              OR urgencia = 'Critica'
              THEN 'P1'
            WHEN impacto = 'Alto'
              OR urgencia = 'Alta'
              OR nodo_vip = true
              THEN 'P2'
            ELSE 'P3'
        END                                                              AS prioridad
    FROM con_motivo
)

SELECT
    ticket,
    grupo_whatsapp,
    prioridad,
    accion_recomendada,
    region,
    ciudad,
    tecnologia,
    clientes_afectados,
    impacto,
    urgencia,
    nodo_vip,
    flag_en_bateria,
    n_fallas_sector,
    tiempo_resolucion_min,
    motivo_notificacion,
    -- Mensaje listo para enviar por WhatsApp (una sola linea, sin saltos)
    CONCAT(
        '[NOC-', prioridad, '] ',
        'Ticket: ', ticket, ' | ',
        'Ciudad: ', ciudad, ' (', region, ') | ',
        'Tec: ', tecnologia, ' | ',
        'Accion: ', accion_recomendada, ' | ',
        'Clientes afectados: ', CAST(clientes_afectados AS STRING), ' | ',
        'Impacto: ', impacto, ' | ',
        'Urgencia: ', urgencia, ' | ',
        'Motivo: ', motivo_notificacion
    )                                                                    AS mensaje
FROM con_prioridad
ORDER BY
    CASE prioridad WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 ELSE 3 END,
    clientes_afectados DESC;


-- =============================================================================
-- CONSULTAS DE VERIFICACION (ejecutar individualmente para validar la vista)
-- =============================================================================

-- Verificacion 1: conteo total y distribucion por grupo WhatsApp
/*
SELECT
    grupo_whatsapp,
    COUNT(*)                                                             AS n_notificaciones,
    SUM(clientes_afectados)                                              AS clientes_total,
    SUM(CASE WHEN prioridad = 'P1' THEN 1 ELSE 0 END)                   AS n_p1,
    SUM(CASE WHEN prioridad = 'P2' THEN 1 ELSE 0 END)                   AS n_p2,
    SUM(CASE WHEN prioridad = 'P3' THEN 1 ELSE 0 END)                   AS n_p3
FROM workspace.gold.notificaciones_whatsapp
GROUP BY grupo_whatsapp
ORDER BY n_notificaciones DESC;
*/

-- Verificacion 2: distribucion por prioridad con ejemplos de mensaje
/*
SELECT
    prioridad,
    COUNT(*)                                                             AS n_tickets,
    ROUND(AVG(clientes_afectados), 0)                                    AS clientes_prom,
    SUM(CASE WHEN nodo_vip = true THEN 1 ELSE 0 END)                     AS n_vip,
    FIRST(mensaje)                                                       AS ejemplo_mensaje
FROM workspace.gold.notificaciones_whatsapp
GROUP BY prioridad
ORDER BY prioridad;
*/

-- Verificacion 3: muestra los primeros 20 mensajes para revision manual
/*
SELECT
    ticket,
    grupo_whatsapp,
    prioridad,
    motivo_notificacion,
    mensaje
FROM workspace.gold.notificaciones_whatsapp
ORDER BY prioridad, clientes_afectados DESC
LIMIT 20;
*/
