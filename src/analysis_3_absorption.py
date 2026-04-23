"""
Analysis 3: Supply Absorption Differential
Identify markets adding supply fast but tightening per-capita.
"""

import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.data_loader import load_all
from src.analysis_1_attribution import run_analysis_1
from src.analysis_2_forward_score import run_analysis_2

OUTPUTS = Path(__file__).parent.parent / "outputs"
OUTPUTS.mkdir(exist_ok=True)


def run_analysis_3(rank_dfs=None, growth_df=None):
    print("\n=== ANALYSIS 3: Supply Absorption Differential ===")
    panel, cs, summary_ranks, summary_sorted = load_all()

    if rank_dfs is None or growth_df is None:
        coef_table = run_analysis_1()
        rank_dfs, growth_df = run_analysis_2(coef_table)

    from src.data_loader import (
        load_supply_forward, load_forward_upp, load_population_growth_forward
    )

    supply_fwd  = load_supply_forward()
    upp_fwd     = load_forward_upp()
    pop_fwd     = load_population_growth_forward()

    # 5yr offset: index 19 (0-based from first col = 2025 Q2)
    off5 = 19

    def pct_change(df, off):
        base = df.iloc[:, 0]
        end  = df.iloc[:, min(off, df.shape[1]-1)]
        return ((end / base) - 1).rename(None)

    supply_growth_5yr = pct_change(supply_fwd, off5)
    pop_growth_5yr    = pct_change(pop_fwd,    off5)

    # UPP ratio change (absolute)
    upp_base = upp_fwd["upp_ratio"].iloc[:, 0]
    upp_end  = upp_fwd["upp_ratio"].iloc[:, min(off5, upp_fwd["upp_ratio"].shape[1]-1)]
    upp_change_5yr = (upp_end - upp_base).rename(None)

    # Absorption pressure: pop growth - supply growth
    absorption_pressure = pop_growth_5yr - supply_growth_5yr

    # Build table
    abs_df = pd.DataFrame({
        "Supply_Growth_5yr":    supply_growth_5yr,
        "UPP_Change_5yr":       upp_change_5yr,
        "Pop_Growth_5yr":       pop_growth_5yr,
        "Absorption_Pressure":  absorption_pressure,
    }).dropna()

    # Quadrant classification (medians as cutoffs)
    med_supply = abs_df["Supply_Growth_5yr"].median()
    med_upp    = abs_df["UPP_Change_5yr"].median()

    def classify(row):
        hi_supply = row["Supply_Growth_5yr"] >= med_supply
        upp_fall  = row["UPP_Change_5yr"] <= med_upp
        if hi_supply and upp_fall:     return "Q1_HighSupply_TightPerCap"
        if not hi_supply and upp_fall: return "Q2_LowSupply_TightPerCap"
        if not hi_supply and not upp_fall: return "Q3_LowSupply_Stagnant"
        return "Q4_HighSupply_Oversupply"

    abs_df["Quadrant"] = abs_df.apply(classify, axis=1)

    # Add empirical 5yr rank from Analysis 2
    rank5 = rank_dfs["5yr"]["composite_rank"].rename("Empirical_Rank_5yr")
    abs_df = abs_df.join(rank5, how="left")

    print("\nQuadrant distribution:")
    print(abs_df["Quadrant"].value_counts().to_string())
    print(f"\nMedian supply growth: {med_supply:.3f}")
    print(f"Median UPP change:    {med_upp:.4f}")

    # --- Scatter plot ---
    top30_idx = rank_dfs["5yr"].nsmallest(30, "composite_rank").index

    quad_colors = {
        "Q1_HighSupply_TightPerCap": "#2ecc71",
        "Q2_LowSupply_TightPerCap":  "#3498db",
        "Q3_LowSupply_Stagnant":     "#f39c12",
        "Q4_HighSupply_Oversupply":  "#e74c3c",
    }

    fig, ax = plt.subplots(figsize=(13, 9))
    for quad, grp in abs_df.groupby("Quadrant"):
        ax.scatter(grp["Supply_Growth_5yr"], grp["UPP_Change_5yr"],
                   color=quad_colors.get(quad, "gray"),
                   label=quad.replace("_", " "),
                   alpha=0.7, s=50)

    # Label top 30
    for m in top30_idx:
        if m in abs_df.index:
            row = abs_df.loc[m]
            short = m.split(" - ")[0]
            ax.annotate(short,
                        xy=(row["Supply_Growth_5yr"], row["UPP_Change_5yr"]),
                        fontsize=6.5, ha="center", va="bottom",
                        xytext=(0, 4), textcoords="offset points")

    ax.axvline(med_supply, color="k", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.axhline(med_upp,    color="k", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.set_xlabel("5yr Supply Growth Rate", fontsize=11)
    ax.set_ylabel("5yr UPP Change (units/person)", fontsize=11)
    ax.set_title("Supply vs UPP Change — Absorption Quadrant Map", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)

    # Quadrant labels
    xlim = ax.get_xlim(); ylim = ax.get_ylim()
    ax.text(xlim[1]*0.97, ylim[0]*1.02, "Q4: Oversupply Risk", ha="right", va="bottom",
            fontsize=8, color=quad_colors["Q4_HighSupply_Oversupply"], alpha=0.7)
    ax.text(xlim[0]*1.01, ylim[1]*0.98, "Q2: Natural Tightening", ha="left", va="top",
            fontsize=8, color=quad_colors["Q2_LowSupply_TightPerCap"], alpha=0.7)

    plt.tight_layout()
    scatter_path = OUTPUTS / "analysis_3_absorption_scatter.png"
    plt.savefig(scatter_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Scatter saved -> {scatter_path}")

    # --- Save table ---
    quad_path = OUTPUTS / "analysis_3_absorption_quadrants.csv"
    abs_df.reset_index().to_csv(quad_path, index=False)
    print(f"Quadrant table saved -> {quad_path}")

    print("\nQuadrant 1 markets (High Supply + Tightening per-capita):")
    q1 = abs_df[abs_df["Quadrant"]=="Q1_HighSupply_TightPerCap"].sort_values("Empirical_Rank_5yr")
    print(q1[["Supply_Growth_5yr","UPP_Change_5yr","Absorption_Pressure","Empirical_Rank_5yr"]].head(15).to_string())

    return abs_df


if __name__ == "__main__":
    run_analysis_3()
