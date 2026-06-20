#!/usr/bin/env python3
"""
run_pipeline.py - Orquestador del pipeline Medallion del NOC (SIN notebooks).

Ejecuta, desde un unico script de Python, todo el flujo de ingesta de datos:

    0. Crea (si no existen) los schemas bronze/silver/gold y el Volume landing_zone.
    1. Genera los tickets simulados con src/generar_datos.py  ->  CSV local.
    2. Sube el CSV al Volume de Unity Catalog (landing zone).
    3. Ejecuta el SQL Medallion en el SQL Warehouse:
         setup -> bronze (lee desde el Volume) -> silver -> gold
    4. Imprime los conteos de verificacion por capa.

-----------------------------------------------------------------------------
Configuracion (repo PRIVADO): credenciales HARDCODEADAS abajo.

  *** ADVERTENCIA DE SEGURIDAD ***
  Este archivo contiene un Personal Access Token de Databricks en texto plano.
  - Manten el repositorio PRIVADO en todo momento.
  - Si el token se filtra o el repo se vuelve publico, REVOCA el token de
    inmediato en Databricks (Settings -> Developer -> Access tokens) y genera
    uno nuevo.
  - Las variables de entorno (DATABRICKS_HOST / DATABRICKS_TOKEN /
    DATABRICKS_WAREHOUSE_ID), si estan definidas, TIENEN PRIORIDAD sobre los
    valores hardcodeados.
-----------------------------------------------------------------------------

Uso
    python pipeline/run_pipeline.py
    python pipeline/run_pipeline.py --n 5000 --semilla 7
    python pipeline/run_pipeline.py --skip-generate     # usa el CSV ya existente

Orden de ejecucion para el SERVING ENDPOINT:
    El serving (serving/deploy_serving_endpoint.py) sirve el modelo
    workspace.gold.modelo_decision_cuadrilla, que ENTRENA y REGISTRA el notebook
    notebooks/04_modelo.py. Por lo tanto: primero corre este pipeline, luego
    04_modelo.py (registra el modelo en Unity Catalog) y SOLO DESPUES despliega
    el serving endpoint.

Autor: Mario Daniel Enrique Perez Jimenez
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# =============================================================================
# Credenciales HARDCODEADAS (repo privado). REEMPLAZA por tus valores reales.
# Si defines las variables de entorno equivalentes, esas tienen prioridad.
# =============================================================================
DATABRICKS_HOST = "https://dbc-xxxxxxxx-xxxx.cloud.databricks.com"   # <-- REEMPLAZA
DATABRICKS_TOKEN = "dapiXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"            # <-- REEMPLAZA
DATABRICKS_WAREHOUSE_ID = "xxxxxxxxxxxxxxxx"                          # <-- REEMPLAZA (SQL Warehouse ID)

# Las env vars, si existen, mandan sobre lo hardcodeado.
HOST = os.environ.get("DATABRICKS_HOST") or DATABRICKS_HOST
TOKEN = os.environ.get("DATABRICKS_TOKEN") or DATABRICKS_TOKEN
WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID") or DATABRICKS_WAREHOUSE_ID

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

CSV_NAME = "sample_tickets.csv"
SQL_FILES = ("00_setup.sql", "01_bronze.sql", "02_silver.sql", "03_gold.sql")


def _client():
    """WorkspaceClient autenticado con el host/token hardcodeados (o env)."""
    from databricks.sdk import WorkspaceClient

    return WorkspaceClient(host=HOST, token=TOKEN)


def _run_sql(w, warehouse_id: str, statement: str, catalog: str):
    """Ejecuta una sentencia SQL en el warehouse y espera a que termine."""
    from databricks.sdk.service.sql import StatementState

    resp = w.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=statement,
        catalog=catalog,
        wait_timeout="50s",
    )
    terminal = {StatementState.SUCCEEDED, StatementState.FAILED,
                StatementState.CANCELED, StatementState.CLOSED}
    while resp.status and resp.status.state not in terminal:
        time.sleep(2)
        resp = w.statement_execution.get_statement(resp.statement_id)

    state = resp.status.state if resp.status else None
    if state != StatementState.SUCCEEDED:
        err = getattr(resp.status, "error", None)
        raise RuntimeError(f"SQL fallo ({state}): {err}\n--- sentencia ---\n{statement[:300]}")
    return resp


def _split_statements(sql_text: str):
    """Divide un archivo .sql en sentencias separadas por ';'."""
    return [s.strip() for s in sql_text.split(";") if s.strip()]


def _scalar(resp):
    """Devuelve el primer valor de la primera fila de un resultado."""
    if resp.result and resp.result.data_array:
        return resp.result.data_array[0][0]
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description="Orquestador Medallion NOC (script Python)")
    ap.add_argument("--n", type=int, default=int(os.getenv("N_TICKETS", "1500")))
    ap.add_argument("--semilla", type=int, default=int(os.getenv("SEMILLA", "42")))
    ap.add_argument("--catalogo", default=os.getenv("CATALOGO", "workspace"))
    ap.add_argument("--skip-generate", action="store_true",
                    help="No regenera el CSV; usa data/sample_tickets.csv existente")
    ap.add_argument("--skip-upload", action="store_true",
                    help="No sube el CSV al Volume (asume que ya esta alli)")
    args = ap.parse_args()

    warehouse_id = WAREHOUSE_ID
    if not warehouse_id or "xxxx" in warehouse_id:
        sys.exit("ERROR: define DATABRICKS_WAREHOUSE_ID (constante hardcodeada o variable de entorno).")

    volume_dir = f"/Volumes/{args.catalogo}/bronze/landing_zone"
    volume_path = f"{volume_dir}/{CSV_NAME}"
    local_csv = REPO_ROOT / "data" / CSV_NAME

    # 1) Generar la data simulada
    if args.skip_generate and local_csv.exists():
        print(f"[1/4] Omitida generacion; uso {local_csv}")
    else:
        from src.generar_datos import generar

        df = generar(n=args.n, semilla=args.semilla)
        local_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(local_csv, index=False)
        print(f"[1/4] Generados {len(df)} tickets -> {local_csv}")

    w = _client()

    # 2) Subir el CSV al Volume (landing zone)
    if args.skip_upload:
        print(f"[2/4] Omitida subida; asumo {volume_path} ya presente")
    else:
        with open(local_csv, "rb") as fh:
            w.files.upload(volume_path, fh, overwrite=True)
        print(f"[2/4] CSV subido al Volume: {volume_path}")

    # 3) Ejecutar el SQL Medallion (setup -> bronze<-Volume -> silver -> gold)
    sql_dir = REPO_ROOT / "sql"
    for archivo in SQL_FILES:
        texto = (sql_dir / archivo).read_text(encoding="utf-8")
        for stmt in _split_statements(texto):
            _run_sql(w, warehouse_id, stmt, args.catalogo)
        print(f"[3/4] Ejecutado {archivo}")

    # 4) Verificacion por capa
    print("[4/4] Verificacion de conteos:")
    for tabla in (
        f"{args.catalogo}.bronze.tickets_noc",
        f"{args.catalogo}.silver.tickets_noc",
        f"{args.catalogo}.gold.decision_cuadrilla",
    ):
        resp = _run_sql(w, warehouse_id, f"SELECT count(*) FROM {tabla}", args.catalogo)
        print(f"        {tabla}: {_scalar(resp)} filas")

    print("\nPipeline Medallion completado correctamente.")
    print("\nSIGUIENTE PASO para el serving endpoint:")
    print("  1) Ejecuta notebooks/04_modelo.py  -> entrena y REGISTRA el modelo")
    print("     workspace.gold.modelo_decision_cuadrilla en Unity Catalog.")
    print("  2) Luego: python serving/deploy_serving_endpoint.py")


if __name__ == "__main__":
    main()
