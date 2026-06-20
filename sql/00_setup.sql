-- =============================================================================
-- 00_setup.sql  ·  Setup inicial de Unity Catalog para el pipeline Medallion NOC
-- Proyecto: agentes_ingesta_telecomunicaciones (NOC)
--
-- Crea (si no existen) los schemas bronze/silver/gold y el Volume de landing zone
-- ANTES de ejecutar 01_bronze.sql. Esto hace el pipeline reproducible desde cero
-- en un workspace limpio: sin esto, read_files / CREATE TABLE fallan porque el
-- schema o el Volume no existen todavia.
--
-- Linaje habilitado:
--   /Volumes/workspace/bronze/landing_zone/  (landing zone para sample_tickets.csv)
--
-- Autor: Mario Daniel Enrique Perez Jimenez
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS workspace.bronze
  COMMENT 'Capa Bronze - tickets crudos del NOC ingeridos desde el Volume landing_zone';

CREATE SCHEMA IF NOT EXISTS workspace.silver
  COMMENT 'Capa Silver - tickets NOC limpios + features';

CREATE SCHEMA IF NOT EXISTS workspace.gold
  COMMENT 'Capa Gold - dataset de decision por ticket + target + modelo registrado';

CREATE VOLUME IF NOT EXISTS workspace.bronze.landing_zone
  COMMENT 'Landing zone (Unity Catalog Volume) para el CSV crudo sample_tickets.csv';