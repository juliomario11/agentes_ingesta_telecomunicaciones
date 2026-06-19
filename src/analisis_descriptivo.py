#!/usr/bin/env python3
"""Análisis descriptivo / EDA reproducible del proyecto NOC (componente #5).

Reproduce el dataset canónico en pandas — bronze (``generar(1500, 42)``) ->
silver -> gold, idéntico a ``sql/02_silver.sql`` y ``sql/03_gold.sql`` — corre
el EDA y genera las 7 figuras (SVG vectorial) en ``docs/img/eda/``.

Equivalente local (sin Databricks) de ``notebooks/07_eda_analisis_descriptivo.py``.

Uso:
    python src/analisis_descriptivo.py
    python src/analisis_descriptivo.py --n 1500 --semilla 42

Autor: Mario Daniel Enrique Perez Jimenez.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Permite ejecutar tanto `python src/analisis_descriptivo.py` como import directo.
try:
    from src.generar_datos import generar
except ImportError:  # ejecutado desde dentro de src/
    from generar_datos import generar

REPO_ROOT = Path(__file__).resolve().parents[1]
IMG = REPO_ROOT / "docs" / "img" / "eda"

TARGET_ORDER = ["DESPACHAR_CUADRILLA", "ESPERAR_AUTORRESTABLECIMIENTO", "TECNICO_URGENTE"]
TARGET_COLOR = {
    "DESPACHAR_CUADRILLA": "#2563EB",
    "ESPERAR_AUTORRESTABLECIMIENTO": "#16A34A",
    "TECNICO_URGENTE": "#DC2626",
}
TARGET_SHORT = {
    "DESPACHAR_CUADRILLA": "DESPACHAR",
    "ESPERAR_AUTORRESTABLECIMIENTO": "ESPERAR",
    "TECNICO_URGENTE": "T. URGENTE",
}
INK, GRID = "#1e293b", "#e2e8f0"
plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white", "axes.edgecolor": GRID,
    "axes.labelcolor": INK, "text.color": INK, "xtick.color": INK, "ytick.color": INK,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "font.size": 11,
    "axes.titlesize": 13, "axes.titleweight": "bold",
})


def _style(ax):
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def _save(fig, name):
    fig.savefig(IMG / name, dpi=150, bbox_inches="tight")
    plt.close(fig)


def construir_gold(n: int, semilla: int) -> pd.DataFrame:
    """Reproduce bronze -> silver -> gold en pandas (idéntico al SQL del repo)."""
    bronze = generar(n=n, semilla=semilla)

    # SILVER (sql/02_silver.sql)
    s = bronze.copy()
    s["hora_caida"] = pd.to_datetime(s["hora_caida"])
    s["hora_restablecimiento"] = pd.to_datetime(s["hora_restablecimiento"])
    s["elementos_afectados"] = s["cantidad_nodos"] + s["cantidad_arpones"]
    s["impacto"] = s["impacto"].str.title()
    s["urgencia"] = s["urgencia"].str.title()
    s["flag_en_bateria"] = (
        (s["tecnologia"] == "HFC") & (s["fuente_voltaje"] > 0) & (s["fuente_voltaje"] < 50)
    )
    s["tiempo_resolucion_min"] = (
        (s["hora_restablecimiento"] - s["hora_caida"]).dt.total_seconds() // 60
    ).astype(int)
    s = s[
        s["ticket"].notna()
        & s["tecnologia"].isin(["HFC", "GPON"])
        & (s["hora_restablecimiento"] >= s["hora_caida"])
        & (s["fuente_voltaje"] >= 0)
        & (s["fuente_amperaje"] >= 0)
    ].copy()

    # GOLD (sql/03_gold.sql)
    grp = s.groupby("cable_padre")
    s["pct_autorrestablecimiento_sector"] = grp["restablecio_autonomo"].transform("mean").round(3)
    s["n_fallas_sector"] = grp["ticket"].transform("count").astype(int)
    s["accion_recomendada"] = np.where(
        s["falla_simultanea_nodo_arpon"], "TECNICO_URGENTE",
        np.where(
            s["flag_en_bateria"] & (s["nodos_sector_en_bateria"] >= 2) & s["correlacion_grafica_monitoreo"],
            "ESPERAR_AUTORRESTABLECIMIENTO", "DESPACHAR_CUADRILLA",
        ),
    )
    cols = [
        "ticket", "region", "ciudad", "tecnologia", "elementos_afectados", "cantidad_nodos",
        "cantidad_arpones", "nodo_vip", "impacto", "urgencia", "clientes_afectados",
        "existe_en_cacti", "fuente_monitoreo", "fuente_voltaje", "fuente_amperaje",
        "flag_en_bateria", "nodos_sector_en_bateria", "correlacion_grafica_monitoreo",
        "delta_correlacion_min", "falla_simultanea_nodo_arpon", "tiempo_resolucion_min",
        "requiere_notificacion", "cable_padre", "pct_autorrestablecimiento_sector",
        "n_fallas_sector", "forma_resolucion", "accion_recomendada",
    ]
    return s[cols].copy()


def graficar(gold: pd.DataFrame) -> None:
    IMG.mkdir(parents=True, exist_ok=True)
    vc = gold["accion_recomendada"].value_counts().reindex(TARGET_ORDER)
    pct = (vc / len(gold) * 100).round(2)

    # 1 - target
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    bars = ax.bar([TARGET_SHORT[k] for k in TARGET_ORDER], [vc[k] for k in TARGET_ORDER],
                  color=[TARGET_COLOR[k] for k in TARGET_ORDER], edgecolor="white", width=0.62)
    for b, k in zip(bars, TARGET_ORDER):
        ax.text(b.get_x() + b.get_width()/2, b.get_height() + 12,
                f"{vc[k]:,}\n({pct[k]:.1f}%)", ha="center", va="bottom", fontweight="bold")
    ax.set_ylabel("N.º de tickets"); ax.set_ylim(0, vc.max()*1.18)
    ax.set_title("Distribución del target · accion_recomendada (n=1.500)"); _style(ax)
    _save(fig, "01_target_distribucion.svg")

    # 2 - histogramas
    HIST = ["clientes_afectados", "elementos_afectados", "tiempo_resolucion_min",
            "delta_correlacion_min", "fuente_voltaje", "nodos_sector_en_bateria",
            "pct_autorrestablecimiento_sector", "n_fallas_sector"]
    fig, axes = plt.subplots(2, 4, figsize=(16, 7.5))
    for ax, c in zip(axes.ravel(), HIST):
        ax.hist(gold[c], bins=30, color="#4f46e5", edgecolor="white", alpha=0.9)
        ax.set_title(c, fontsize=11); ax.set_ylabel("frec."); _style(ax)
    fig.suptitle("Distribuciones de variables numéricas (Gold)", fontsize=15, fontweight="bold", y=1.01)
    fig.tight_layout(); _save(fig, "02_histogramas_numericas.svg")

    # 3 - categoricas
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    specs = [("region", "#0ea5e9"), ("tecnologia", "#8b5cf6"), ("impacto", "#f59e0b"), ("urgencia", "#ef4444")]
    orden = {"impacto": ["Bajo", "Medio", "Alto", "Critico"], "urgencia": ["Baja", "Media", "Alta", "Critica"]}
    for ax, (col, color) in zip(axes.ravel(), specs):
        vcc = gold[col].value_counts()
        if col in orden:
            vcc = vcc.reindex([x for x in orden[col] if x in vcc.index])
        bars = ax.bar(vcc.index.astype(str), vcc.values, color=color, edgecolor="white", width=0.7)
        for b, v in zip(bars, vcc.values):
            ax.text(b.get_x() + b.get_width()/2, b.get_height() + 4, f"{v}", ha="center", fontsize=9.5)
        ax.set_title(col); ax.set_ylabel("tickets"); _style(ax)
    fig.suptitle("Variables categóricas", fontsize=15, fontweight="bold", y=1.01)
    fig.tight_layout(); _save(fig, "03_categoricas.svg")

    # 4 - target por grupo
    ct_tec = pd.crosstab(gold["tecnologia"], gold["accion_recomendada"]).reindex(columns=TARGET_ORDER, fill_value=0)
    ct_reg = pd.crosstab(gold["region"], gold["accion_recomendada"]).reindex(columns=TARGET_ORDER, fill_value=0)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))
    for ax, ct, title in [(axes[0], ct_tec, "por tecnología"), (axes[1], ct_reg, "por región")]:
        p = ct.div(ct.sum(axis=1), axis=0) * 100
        bottom = np.zeros(len(p))
        for k in TARGET_ORDER:
            ax.bar(p.index.astype(str), p[k].values, bottom=bottom, color=TARGET_COLOR[k],
                   edgecolor="white", label=TARGET_SHORT[k], width=0.6)
            bottom += p[k].values
        ax.set_title(f"Composición del target {title}"); ax.set_ylabel("% de tickets"); ax.set_ylim(0, 100); _style(ax)
    axes[1].legend(loc="lower right", fontsize=9)
    fig.tight_layout(); _save(fig, "04_target_por_grupo.svg")

    # 5 - boxplots
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, col, logy, title in [
        (axes[0], "clientes_afectados", True, "Clientes afectados (escala log)"),
        (axes[1], "tiempo_resolucion_min", False, "Tiempo de resolución (min)"),
    ]:
        data = [gold.loc[gold.accion_recomendada == k, col].values for k in TARGET_ORDER]
        bp = ax.boxplot(data, patch_artist=True, widths=0.55,
                        medianprops=dict(color=INK, linewidth=1.6),
                        flierprops=dict(marker="o", markersize=3, alpha=0.35))
        for patch, k in zip(bp["boxes"], TARGET_ORDER):
            patch.set_facecolor(TARGET_COLOR[k]); patch.set_alpha(0.75); patch.set_edgecolor("white")
        ax.set_xticklabels([TARGET_SHORT[k] for k in TARGET_ORDER])
        if logy:
            ax.set_yscale("log")
        ax.set_title(title); _style(ax)
    fig.suptitle("Variables clave por clase del target", fontsize=15, fontweight="bold", y=1.02)
    fig.tight_layout(); _save(fig, "05_boxplots_por_target.svg")

    # 6 - correlacion
    NUM = ["clientes_afectados", "elementos_afectados", "cantidad_nodos", "cantidad_arpones",
           "fuente_voltaje", "fuente_amperaje", "nodos_sector_en_bateria", "delta_correlacion_min",
           "tiempo_resolucion_min", "pct_autorrestablecimiento_sector", "n_fallas_sector"]
    BOOL = ["nodo_vip", "existe_en_cacti", "flag_en_bateria", "correlacion_grafica_monitoreo",
            "falla_simultanea_nodo_arpon", "requiere_notificacion"]
    CORR = NUM + BOOL
    M = gold[CORR].astype(float).corr().values
    fig, ax = plt.subplots(figsize=(12.5, 10.5))
    n = len(CORR)
    im = ax.pcolormesh(M, cmap="RdBu_r", vmin=-1, vmax=1, edgecolors="white", linewidth=0.4)
    ax.set_xticks(np.arange(n) + 0.5); ax.set_yticks(np.arange(n) + 0.5)
    ax.set_xticklabels(CORR, rotation=55, ha="right", fontsize=9); ax.set_yticklabels(CORR, fontsize=9)
    ax.invert_yaxis(); ax.set_aspect("equal")
    for i in range(n):
        for j in range(n):
            if abs(M[i, j]) >= 0.15:
                ax.text(j + 0.5, i + 0.5, f"{M[i, j]:.2f}", ha="center", va="center",
                        fontsize=7.5, color="white" if abs(M[i, j]) > 0.55 else INK)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04).set_label("Correlación de Pearson")
    ax.set_title("Matriz de correlación · numéricas + booleanas (Gold)", pad=14); ax.grid(False)
    fig.tight_layout(); _save(fig, "06_correlacion.svg")

    # 7 - drivers
    drivers = [("falla_simultanea_nodo_arpon", "falla_simultanea\n_nodo_arpon"),
               ("flag_en_bateria", "flag_en_bateria"),
               ("correlacion_grafica_monitoreo", "correlacion_grafica\n_monitoreo")]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    for ax, (col, lab) in zip(axes, drivers):
        sub = pd.crosstab(gold[col], gold["accion_recomendada"], normalize="index").reindex(columns=TARGET_ORDER, fill_value=0) * 100
        bottom = np.zeros(len(sub))
        for k in TARGET_ORDER:
            ax.bar(["False", "True"], sub[k].values, bottom=bottom, color=TARGET_COLOR[k],
                   edgecolor="white", width=0.6, label=TARGET_SHORT[k])
            bottom += sub[k].values
        ax.set_title(lab, fontsize=11); ax.set_ylabel("% del target"); ax.set_ylim(0, 100); _style(ax)
    axes[-1].legend(loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=9)
    fig.suptitle("Cómo cada driver determina la decisión", fontsize=15, fontweight="bold", y=1.03)
    fig.tight_layout(); _save(fig, "07_drivers_target.svg")


def main() -> None:
    ap = argparse.ArgumentParser(description="EDA reproducible del proyecto NOC")
    ap.add_argument("--n", type=int, default=1500)
    ap.add_argument("--semilla", type=int, default=42)
    args = ap.parse_args()

    gold = construir_gold(args.n, args.semilla)

    vc = gold["accion_recomendada"].value_counts().reindex(TARGET_ORDER)
    print(f"Gold reproducido: {gold.shape[0]} filas x {gold.shape[1]} columnas")
    print(f"Nulos: {int(gold.isna().sum().sum())} | Tickets duplicados: {int(gold['ticket'].duplicated().sum())}")
    print("\nDistribucion del target:")
    for k in TARGET_ORDER:
        print(f"  {k:32s} {int(vc[k]):5d}  ({vc[k]/len(gold)*100:5.2f} %)")
    print(f"\nRatio de desbalance: {vc.max()/vc.min():.1f} : 1")

    graficar(gold)
    print(f"\n7 figuras generadas en: {IMG}")


if __name__ == "__main__":
    main()
