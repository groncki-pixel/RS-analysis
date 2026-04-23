"""
Analysis 5: Forward Rent Growth Trajectory Analysis
Identify markets where short-term vs long-term growth forecasts diverge.
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
from src.data_loader import load_all, load_effective_rent_forward

OUTPUTS = Path(__file__).parent.parent / "outputs"
OUTPUTS.mkdir(exist_ok=True)


def run_analysis_5():
    print("\n=== ANALYSIS 5: Rent Growth Trajectory Analysis ===")
    panel, cs, _, _ = load_all()

    eff_rent = load_effective_rent_forward()  # index=market, cols=quarters

    horizons = {"1yr": 3, "3yr": 11, "5yr": 19, "10yr": 39}

    records = {}
    for m in eff_rent.index:
        row = eff_rent.loc[m].dropna()
        if len(row) < 2:
            continue
        base = row.iloc[0]
        if pd.isna(base) or base == 0:
            continue

        rec = {}
        for h, off in horizons.items():
            if off < len(row):
                g = (row.iloc[off] / base) - 1
            else:
                g = (row.iloc[-1] / base) - 1
            rec[f"rent_growth_{h}"] = g

        # Annualised
        rec["rent_growth_3yr_ann"]  = (1 + rec["rent_growth_3yr"]) ** (1/3)  - 1
        rec["rent_growth_5yr_ann"]  = (1 + rec["rent_growth_5yr"]) ** (1/5)  - 1
        rec["rent_growth_10yr_ann"] = (1 + rec["rent_growth_10yr"]) ** (1/10) - 1

        records[m] = rec

    traj_df = pd.DataFrame.from_dict(records, orient="index")
    traj_df.index.name = "market"

    # Rank per horizon (ascending = lower rank = better growth)
    for h in horizons.keys():
        col = f"rent_growth_{h}"
        if col in traj_df.columns:
            traj_df[f"rank_{h}"] = traj_df[col].rank(ascending=False)

    traj_df["Trajectory_Score"] = traj_df["rank_10yr"] - traj_df["rank_1yr"]

    print("\nTop 10 'improving' markets (buy now — long-term rank >> short-term rank):")
    improving = traj_df.nsmallest(10, "Trajectory_Score")
    print(improving[["rank_1yr","rank_10yr","Trajectory_Score",
                      "rent_growth_1yr","rent_growth_5yr_ann","rent_growth_10yr_ann"]].to_string())

    print("\nTop 10 'fading' markets (already priced in):")
    fading = traj_df.nlargest(10, "Trajectory_Score")
    print(fading[["rank_1yr","rank_10yr","Trajectory_Score",
                  "rent_growth_1yr","rent_growth_5yr_ann","rent_growth_10yr_ann"]].to_string())

    # --- Scatter: 1yr rank vs 10yr rank ---
    fig, ax = plt.subplots(figsize=(11, 9))
    colors = traj_df["Trajectory_Score"]
    sc = ax.scatter(traj_df["rank_1yr"], traj_df["rank_10yr"],
                    c=colors, cmap="RdYlGn_r", alpha=0.7, s=50,
                    vmin=colors.quantile(0.05), vmax=colors.quantile(0.95))

    # Diagonal
    lim = max(traj_df["rank_1yr"].max(), traj_df["rank_10yr"].max())
    ax.plot([1, lim], [1, lim], "k--", linewidth=1, alpha=0.4, label="Same rank")

    # Label outliers (|traj score| > 30)
    outliers = traj_df[traj_df["Trajectory_Score"].abs() > 30]
    for m, row in outliers.iterrows():
        short = m.split(" - ")[0]
        ax.annotate(short, xy=(row["rank_1yr"], row["rank_10yr"]),
                    fontsize=7, ha="center", va="bottom",
                    xytext=(0, 4), textcoords="offset points")

    plt.colorbar(sc, ax=ax, label="Trajectory Score (positive=fading)")
    ax.set_xlabel("1-Year Rent Growth Rank (1=best)", fontsize=11)
    ax.set_ylabel("10-Year Rent Growth Rank (1=best)", fontsize=11)
    ax.set_title("Short vs Long-Term Rent Growth Trajectory", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)
    plt.tight_layout()
    scatter_path = OUTPUTS / "analysis_5_trajectory_scatter.png"
    plt.savefig(scatter_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\nTrajectory scatter saved -> {scatter_path}")

    # --- Growth curves for top 10 trajectory markets ---
    top10_traj = traj_df.nsmallest(10, "Trajectory_Score").index.tolist()

    fig, ax = plt.subplots(figsize=(13, 7))
    quarter_cols = eff_rent.columns.tolist()

    for m in top10_traj:
        if m not in eff_rent.index:
            continue
        row = eff_rent.loc[m].dropna()
        base = row.iloc[0]
        if base == 0:
            continue
        indexed = (row / base) * 100
        ax.plot(range(len(indexed)), indexed.values,
                linewidth=1.8, label=m.split(" - ")[0], alpha=0.85)

    # Pack background (all markets grey)
    for m in eff_rent.index[:30]:
        row = eff_rent.loc[m].dropna()
        if len(row) < 2 or row.iloc[0] == 0:
            continue
        indexed = (row / row.iloc[0]) * 100
        ax.plot(range(len(indexed)), indexed.values, color="gray",
                linewidth=0.5, alpha=0.15)

    n_qtrs = eff_rent.shape[1]
    ax.set_xticks([0, 3, 11, 19, 39])
    ax.set_xticklabels(["2025Q2", "1yr", "3yr", "5yr", "10yr"], fontsize=9)
    ax.set_xlabel("Horizon", fontsize=11)
    ax.set_ylabel("Effective Rent Index (100 = 2025 Q2)", fontsize=11)
    ax.set_title("Top 10 Trajectory Markets — Rent Growth Curves", fontsize=13, fontweight="bold")
    ax.legend(fontsize=8, loc="upper left", ncol=2)
    plt.tight_layout()
    curves_path = OUTPUTS / "analysis_5_growth_curves.png"
    plt.savefig(curves_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Growth curves saved -> {curves_path}")

    # --- Save CSV ---
    out = traj_df[["rank_1yr","rank_3yr","rank_5yr","rank_10yr","Trajectory_Score",
                   "rent_growth_1yr","rent_growth_5yr_ann","rent_growth_10yr_ann"]].copy()
    out.columns = ["Rank_1yr","Rank_3yr","Rank_5yr","Rank_10yr","Trajectory_Score",
                   "Rent_Growth_1yr","Rent_Growth_5yr_Ann","Rent_Growth_10yr_Ann"]
    out = out.sort_values("Trajectory_Score")
    traj_path = OUTPUTS / "analysis_5_trajectories.csv"
    out.reset_index().to_csv(traj_path, index=False)
    print(f"Trajectories saved -> {traj_path}")

    return traj_df


if __name__ == "__main__":
    run_analysis_5()
