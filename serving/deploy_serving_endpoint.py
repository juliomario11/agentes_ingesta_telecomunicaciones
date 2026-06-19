#!/usr/bin/env python3
"""
deploy_serving_endpoint.py - Despliega el modelo como Serving Endpoint (online).

Crea (o actualiza) un endpoint de **Databricks Model Serving** que sirve el modelo
registrado en Unity Catalog `workspace.gold.modelo_decision_cuadrilla`, para
consumir la recomendacion (DESPACHAR_CUADRILLA / ESPERAR_AUTORRESTABLECIMIENTO /
TECNICO_URGENTE) en linea via REST. Cubre el requisito "Serving Endpoint" del
proyecto final.

-----------------------------------------------------------------------------
Requisitos
    pip install databricks-sdk

Entorno (NO se hardcodean credenciales):
    DATABRICKS_HOST     p.ej. https://dbc-xxxx.cloud.databricks.com
    DATABRICKS_TOKEN    Personal Access Token con permiso de Serving

Uso
    python serving/deploy_serving_endpoint.py                 # ultima version del modelo
    python serving/deploy_serving_endpoint.py --version 1
    python serving/deploy_serving_endpoint.py --endpoint noc-decision-cuadrilla

Despues de desplegar, consumir el endpoint (ejemplo):
    curl -s -X POST \
      "$DATABRICKS_HOST/serving-endpoints/noc-decision-cuadrilla/invocations" \
      -H "Authorization: Bearer $DATABRICKS_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"dataframe_records": [{"region":"ANDINA","tecnologia":"HFC", ...}]}'

Autor: Mario Daniel Enrique Perez Jimenez
"""
from __future__ import annotations

import argparse
import os
import sys

MODELO = "workspace.gold.modelo_decision_cuadrilla"
ENDPOINT = "noc-decision-cuadrilla"


def _ultima_version(w, modelo: str) -> str:
    versiones = [int(v.version) for v in w.model_versions.list(full_name=modelo)]
    if not versiones:
        sys.exit(f"ERROR: no hay versiones registradas del modelo {modelo}.")
    return str(max(versiones))


def main() -> None:
    ap = argparse.ArgumentParser(description="Desplegar Serving Endpoint del modelo NOC")
    ap.add_argument("--model", default=MODELO)
    ap.add_argument("--endpoint", default=ENDPOINT)
    ap.add_argument("--version", default=None, help="Version del modelo (default: la ultima)")
    ap.add_argument("--workload-size", default="Small")
    args = ap.parse_args()

    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.serving import (
        EndpointCoreConfigInput,
        ServedEntityInput,
    )

    w = WorkspaceClient()
    version = args.version or _ultima_version(w, args.model)

    served = ServedEntityInput(
        entity_name=args.model,
        entity_version=version,
        workload_size=args.workload_size,
        scale_to_zero_enabled=True,   # ahorra costo: se apaga sin trafico
    )

    existentes = {e.name for e in w.serving_endpoints.list()}
    if args.endpoint in existentes:
        w.serving_endpoints.update_config_and_wait(
            name=args.endpoint, served_entities=[served]
        )
        print(f"Endpoint ACTUALIZADO: {args.endpoint}  ->  {args.model} v{version}")
    else:
        w.serving_endpoints.create_and_wait(
            name=args.endpoint,
            config=EndpointCoreConfigInput(served_entities=[served]),
        )
        print(f"Endpoint CREADO: {args.endpoint}  ->  {args.model} v{version}")

    print(f"Invocacion: {os.getenv('DATABRICKS_HOST','<host>')}/serving-endpoints/{args.endpoint}/invocations")


if __name__ == "__main__":
    main()
