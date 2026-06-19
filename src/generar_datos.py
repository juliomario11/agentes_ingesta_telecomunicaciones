"""Generador de datos simulados de tickets del NOC.

No existe data publica de este dominio, por lo que se simulan tickets con
patrones realistas para las dos tecnologias de acceso:

- HFC : CMTS -> INTERFAZ -> NODO  (monitoreo en CACTI, fuentes de respaldo)
- GPON: OLT  -> INTERFAZ -> ARPON (monitoreo en ZABBIX)

Logica clave del target (accion_recomendada):
- falla_simultanea_nodo_arpon=True (tumba NODOS y ARPONES a la vez) -> TECNICO_URGENTE
- en bateria + varios nodos del sector en bateria + correlacion en
  Cacti/Zabbix (caida vista casi a la misma hora) -> ESPERAR_AUTORRESTABLECIMIENTO
- resto -> DESPACHAR_CUADRILLA

Uso:
    python src/generar_datos.py            # genera 1000 tickets
    python src/generar_datos.py --n 5000   # genera 5000 tickets

Guarda el resultado en data/sample_tickets.csv
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEMILLA = 42

# Macro-regiones de Colombia con departamentos/ciudades coherentes.
REGIONES = {
    "COSTA": [
        ("Atlantico", "Barranquilla"),
        ("Bolivar", "Cartagena"),
        ("Magdalena", "Santa Marta"),
        ("Cordoba", "Monteria"),
    ],
    "ANDINA": [
        ("Antioquia", "Medellin"),
        ("Caldas", "Manizales"),
        ("Risaralda", "Pereira"),
        ("Valle del Cauca", "Cali"),
    ],
    "ORIENTE": [
        ("Santander", "Bucaramanga"),
        ("Norte de Santander", "Cucuta"),
        ("Boyaca", "Tunja"),
    ],
    "BOGOTA": [
        ("Cundinamarca", "Bogota"),
        ("Cundinamarca", "Soacha"),
        ("Cundinamarca", "Chia"),
    ],
    "SUR": [
        ("Narino", "Pasto"),
        ("Huila", "Neiva"),
        ("Cauca", "Popayan"),
        ("Tolima", "Ibague"),
    ],
}

TERRITORIALIDADES = ["Urbano", "Rural", "Periurbano"]
IMPACTOS = ["Bajo", "Medio", "Alto", "Critico"]
URGENCIAS = ["Baja", "Media", "Alta", "Critica"]

DESCRIPCIONES_FALLA = [
    "Perdida de senal en el sector",
    "Degradacion de potencia optica",
    "Intermitencia en el servicio",
    "Caida total del elemento de red",
    "Alta tasa de errores en la interfaz",
    "Sin comunicacion con el elemento",
]

SOLUCIONES = {
    "AUTORRESTABLECIMIENTO": [
        "Servicio restablecido al normalizarse la energia comercial del sector",
        "Falla externa de energia; elemento volvio solo sin intervencion",
        "Recuperacion automatica confirmada en grafica de monitoreo",
    ],
    "CUADRILLA": [
        "Cuadrilla reemplazo conector danado",
        "Empalme de fibra reparado en sitio",
        "Cambio de tarjeta en el elemento",
        "Reconfiguracion de la interfaz afectada",
    ],
    "TECNICO_URGENTE": [
        "Tecnico urgente por caida masiva de NODOS y ARPONES",
        "Atencion prioritaria por dano grave multielemento",
        "Despliegue urgente: afectacion simultanea HFC y GPON",
    ],
}


def _texto(rng: np.random.Generator, opciones: list[str]) -> str:
    return str(rng.choice(opciones))


def generar(n: int = 1000, semilla: int = SEMILLA) -> pd.DataFrame:
    """Genera un DataFrame de ``n`` tickets simulados del NOC."""
    rng = np.random.default_rng(semilla)
    base_dt = datetime(2026, 1, 1)
    regiones = list(REGIONES.keys())
    filas = []

    for i in range(n):
        region = str(rng.choice(regiones))
        departamento, ciudad = REGIONES[region][rng.integers(len(REGIONES[region]))]
        tecnologia = str(rng.choice(["HFC", "GPON"], p=[0.55, 0.45]))

        # Cantidades de elementos por tecnologia.
        if tecnologia == "HFC":
            cantidad_nodos = int(rng.integers(1, 9))
            cantidad_arpones = 0
            cmts = f"CMTS_{region[:3]}_{rng.integers(1, 30):02d}"
            olt = ""
            fuente_monitoreo = "CACTI"
        else:
            cantidad_nodos = 0
            cantidad_arpones = int(rng.integers(1, 13))
            cmts = ""
            olt = f"OLT_{region[:3]}_{rng.integers(1, 30):02d}"
            fuente_monitoreo = "ZABBIX"

        interfaz = f"GE0/{rng.integers(0, 8)}/{rng.integers(0, 48)}"
        cable_padre = f"CP_{region[:3]}_{rng.integers(1, 60):03d}"
        # Algunos nodos cuelgan de un cable hijo, otros no.
        cable_hijo = (
            f"CH_{rng.integers(1, 200):03d}" if rng.random() < 0.5 else ""
        )

        # --- Senal de energia (solo HFC tiene fuente de respaldo real) ---
        # Corte electrico de sector: pone varios nodos del sector en bateria.
        corte_electrico_sector = bool(rng.random() < 0.22)
        if tecnologia == "HFC":
            if corte_electrico_sector:
                fuente_voltaje = float(round(rng.uniform(40.0, 47.0), 2))
                fuente_amperaje = float(round(rng.uniform(0.5, 3.0), 2))
                flag_en_bateria = True
                nodos_sector_en_bateria = int(rng.integers(2, max(3, cantidad_nodos + 3)))
            else:
                fuente_voltaje = float(round(rng.uniform(52.0, 56.0), 2))
                fuente_amperaje = float(round(rng.uniform(4.0, 9.0), 2))
                flag_en_bateria = False
                nodos_sector_en_bateria = 0
        else:
            # GPON: sin fuente de respaldo modelada aqui.
            fuente_voltaje = 0.0
            fuente_amperaje = 0.0
            flag_en_bateria = False
            nodos_sector_en_bateria = 0

        # --- Dano grave que tumba NODOS y ARPONES al tiempo ---
        falla_simultanea_nodo_arpon = bool(rng.random() < 0.06)

        # --- Correlacion con grafica de monitoreo (Cacti/Zabbix) ---
        # Si hubo corte electrico de sector, lo normal es ver la caida y la
        # recuperacion casi a la misma hora en la grafica de monitoreo.
        if corte_electrico_sector and not falla_simultanea_nodo_arpon:
            correlacion_grafica_monitoreo = bool(rng.random() < 0.85)
        else:
            correlacion_grafica_monitoreo = bool(rng.random() < 0.15)
        delta_correlacion_min = (
            int(rng.integers(0, 8)) if correlacion_grafica_monitoreo else int(rng.integers(20, 240))
        )

        # --- Target y desenlace historico ---
        if falla_simultanea_nodo_arpon:
            accion = "TECNICO_URGENTE"
            forma_resolucion = "TECNICO_URGENTE"
            restablecio_autonomo = False
        elif flag_en_bateria and nodos_sector_en_bateria >= 2 and correlacion_grafica_monitoreo:
            accion = "ESPERAR_AUTORRESTABLECIMIENTO"
            forma_resolucion = "AUTORRESTABLECIMIENTO"
            restablecio_autonomo = True
        else:
            accion = "DESPACHAR_CUADRILLA"
            forma_resolucion = "CUADRILLA"
            restablecio_autonomo = False

        # --- Tiempos ---
        hora_caida = base_dt + timedelta(
            days=int(rng.integers(0, 150)),
            hours=int(rng.integers(0, 24)),
            minutes=int(rng.integers(0, 60)),
        )
        if forma_resolucion == "AUTORRESTABLECIMIENTO":
            dur_min = int(rng.integers(10, 90))
        elif forma_resolucion == "TECNICO_URGENTE":
            dur_min = int(rng.integers(60, 300))
        else:
            dur_min = int(rng.integers(45, 480))
        hora_restablecimiento = hora_caida + timedelta(minutes=dur_min)

        # --- Impacto / urgencia (mas altos si es grave o VIP) ---
        nodo_vip = bool(rng.random() < 0.12)
        if falla_simultanea_nodo_arpon:
            impacto = str(rng.choice(["Alto", "Critico"], p=[0.3, 0.7]))
            urgencia = str(rng.choice(["Alta", "Critica"], p=[0.3, 0.7]))
        elif nodo_vip:
            impacto = str(rng.choice(["Medio", "Alto", "Critico"], p=[0.3, 0.5, 0.2]))
            urgencia = str(rng.choice(["Media", "Alta", "Critica"], p=[0.3, 0.5, 0.2]))
        else:
            impacto = _texto(rng, IMPACTOS)
            urgencia = _texto(rng, URGENCIAS)

        # --- Clientes afectados (escalan con elementos y gravedad) ---
        elementos = max(1, cantidad_nodos + cantidad_arpones)
        base_clientes = int(rng.integers(50, 600)) * elementos
        if falla_simultanea_nodo_arpon:
            base_clientes = int(base_clientes * rng.uniform(2.0, 4.0))
        clientes_afectados = int(base_clientes)

        # --- Regla de notificacion a WhatsApp ---
        requiere_notificacion = bool(
            nodo_vip
            or clientes_afectados > 2000
            or impacto in ("Alto", "Critico")
            or urgencia in ("Alta", "Critica")
        )

        descripcion = _texto(rng, DESCRIPCIONES_FALLA)
        filas.append(
            {
                "ticket": f"TKT-{i + 1:06d}",
                "region": region,
                "departamento": departamento,
                "ciudad": ciudad,
                "territorialidad": _texto(rng, TERRITORIALIDADES),
                "itsm_servicenow": f"INC{rng.integers(1_000_000, 9_999_999)}",
                "workorder_salesforce": f"WO-{rng.integers(100000, 999999)}",
                "clientes_afectados": clientes_afectados,
                "tecnologia": tecnologia,
                "cantidad_nodos": cantidad_nodos,
                "cantidad_arpones": cantidad_arpones,
                "cmts": cmts,
                "olt": olt,
                "interfaz": interfaz,
                "cable_padre": cable_padre,
                "cable_hijo": cable_hijo,
                "nodo_vip": nodo_vip,
                "impacto": impacto,
                "urgencia": urgencia,
                "grupo_whatsapp": f"GRP_NOC_{region}",
                "descripcion": descripcion,
                "resumen": f"{descripcion} ({tecnologia}) en {ciudad}",
                "tecnico_asignado": f"TEC_{rng.integers(1, 120):03d}",
                "avances": "Diagnostico inicial registrado",
                "adjuntos": int(rng.integers(0, 6)),
                "existe_en_cacti": bool(tecnologia == "HFC" and rng.random() < 0.9),
                "fuente_voltaje": fuente_voltaje,
                "fuente_amperaje": fuente_amperaje,
                "flag_en_bateria": flag_en_bateria,
                "nodos_sector_en_bateria": nodos_sector_en_bateria,
                "forma_resolucion": forma_resolucion,
                "restablecio_autonomo": restablecio_autonomo,
                "hora_caida": hora_caida,
                "hora_restablecimiento": hora_restablecimiento,
                "fuente_monitoreo": fuente_monitoreo,
                "correlacion_grafica_monitoreo": correlacion_grafica_monitoreo,
                "delta_correlacion_min": delta_correlacion_min,
                "falla_simultanea_nodo_arpon": falla_simultanea_nodo_arpon,
                "solucion_aplicada": _texto(rng, SOLUCIONES[forma_resolucion]),
                "tiempo_resolucion_min": dur_min,
                "requiere_notificacion": requiere_notificacion,
                "accion_recomendada": accion,
            }
        )

    return pd.DataFrame(filas)


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera tickets simulados del NOC")
    parser.add_argument("--n", type=int, default=1000, help="Numero de tickets a generar")
    parser.add_argument("--semilla", type=int, default=SEMILLA, help="Semilla aleatoria")
    parser.add_argument(
        "--salida",
        type=str,
        default="data/sample_tickets.csv",
        help="Ruta del CSV de salida",
    )
    args = parser.parse_args()

    df = generar(n=args.n, semilla=args.semilla)
    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(salida, index=False)

    print(f"Generados {len(df)} tickets -> {salida}")
    print("\nDistribucion del target (accion_recomendada):")
    print(df["accion_recomendada"].value_counts())
    print("\nTickets por region:")
    print(df["region"].value_counts())
    print(f"\nRequieren notificacion WhatsApp: {int(df['requiere_notificacion'].sum())}")


if __name__ == "__main__":
    main()
