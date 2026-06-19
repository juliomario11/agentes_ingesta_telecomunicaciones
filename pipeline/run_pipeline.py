#!/usr/bin/env python3
"""
run_pipeline.py - Orquestador del pipeline Medallion del NOC (SIN notebooks).

Ejecuta, desde un unico script de Python, todo el flujo de ingesta de datos:

    1. Genera los tickets simulados con src/generar_datos.py  ->  CSV local.
    2. Sube el CSV al Volume de Unity Catalog (landing zone).
    3. Ejecuta el SQL Medallion en el SQL Warehouse:
         bronze (lee desde el Volume) -> silver -> gold
    4. Imprime los conteos de verificacion por capa.

Asi se cumple el requisito del curso: la ingesta NO necesita correr notebooks
de Jupyter; un script de Python la automatiza de principio a fin.

-----------------------------------------------------------------------------
Requisitos
    pip install -r requirements.txt          # incluye databricks-sdk

Configuracion por variables de entorno (NO se hardcodean credenciales):
    DATABRICKS_HOST            p.ej. https://dbc-xxxx.cloud.databricks.com
    DATABRICKS_TOKEN          Personal Access Token de Databricks
    DATABRICKS_WAREHOUSE_ID   id del SQL Warehouse (Serverless) que ejecuta el SQL

Opcionales:
    CATALOGO   (default: workspace)
    N_TICKETS  (default: 1500)
    SEMILLA    (default: 42)

Uso
    python pipeline/run_pipeline.py
    python pipeline/run_pipeline.py --n 5000 --semilla 7
    python pipeline/run_pipeline.py --skip-generate     # usa el CSV ya existente

Autor: Mario Daniel Enrique Perez Jimenez
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

CSV_NAME = "sample_tickets.csv"
SQL_FILES = ("01_bronze.sql", "02_silver.sql", "03_gold.sql")


def _client():
    """WorkspaceClient autenticado por entorno (DATABRICKS_HOST / DATABRICKS_TOKEN)."""
    from databricks.sdk import WorkspaceClient

    return WorkspaceClient()


def _run_sql(w, warehouse_id: str, statement: str, catalog: str):
    """Ejecuta una sentencia SQL en el warehouse y espera a que termine."""
    from databricks.sdk.service.sql import StatementState

    resp = w.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=statement,
        catalog=catalog,
        wait_timeout="50s",
    )
    # Si sigue en ejecucion tras el wait inicial, hacemos polling.
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
    """Divide un archivo .sql en sentencias (estos archivos no usan ';' internos)."""
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

    warehouse_id = os.environ.get("DATABRICKS_WAREHOUSE_ID")
    if not warehouse_id:
        sys.exit("ERROR: define DATABRICKS_WAREHOUSE_ID (id del SQL Warehouse).")

    volume_dir = f"/Volumes/{args.catalogo}/bronze/landing_zone"
    volume_path = f"{volume_dir}/{CSV_NAME}"
    local_csv = REPO_ROOT / "data" / CSV_NAME

    # 1) Generar la data simulada -------------------------------------------------
    if args.skip_generate and local_csv.exists():
        print(f"[1/4] Omitida generacion; uso {local_csv}")
    else:
        from src.generar_datos import generar

        df = generar(n=args.n, semilla=args.semilla)
        local_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(local_csv, index=False)
        print(f"[1/4] Generados {len(df)} tickets -> {local_csv}")

    w = _client()

    # 2) Subir el CSV al Volume (landing zone) -----------------------------------
    if args.skip_upload:
        print(f"[2/4] Omitida subida; asumo {volume_path} ya presente")
    else:
        with open(local_csv, "rb") as fh:
            w.files.upload(volume_path, fh, overwrite=True)
        print(f"[2/4] CSV subido al Volume: {volume_path}")

    # 3) Ejecutar el SQL Medallion (bronze<-Volume -> silver -> gold) ------------
    sql_dir = REPO_ROOT / "sql"
    for archivo in SQL_FILES:
        texto = (sql_dir / archivo).read_text(encoding="utf-8")
        for stmt in _split_statements(texto):
            _run_sql(w, warehouse_id, stmt, args.catalogo)
        print(f"[3/4] Ejecutado {archivo}")

    # 4) Verificacion por capa ----------------------------------------------------
    print("[4/4] Verificacion de conteos:")
    for tabla in (
        f"{args.catalogo}.bronze.tickets_noc",
        f"{args.catalogo}.silver.tickets_noc",
        f"{args.catalogo}.gold.decision_cuadrilla",
    ):
        resp = _run_sql(w, warehouse_id, f"SELECT count(*) FROM {tabla}", args.catalogo)
        print(f"        {tabla}: {_scalar(resp)} filas")

    print("\nPipeline Medallion completado correctamente.")


if __name__ == "__main__":
    main()
