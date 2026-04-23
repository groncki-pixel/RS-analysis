"""
Synthesis: Final Market Selection Report
Combines all analyses into investor-facing output.
"""

import sys
import warnings
import numpy as np
import pandas as pd
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.data_loader import load_all

OUTPUTS = Path(__file__).parent.parent / "outputs"
OUTPUTS.mkdir(exist_ok=True)


def run_synthesis():
    print("\n=== SYNTHESIS: Final Market Selection ===")

    # --- Load analysis outputs ---
    def load_csv(name, index_col="market"):
        path = OUTPUTS / name
        if not path.exists():
            print(f"  WARNING: {name} not found")
            return None
        df = pd.read_csv(path)
        if index_col in df.columns:
            df = df.set_index(index_col)
        return df

    rankings    = load_csv("analysis_2_market_rankings.csv")
    absorption  = load_csv("analysis_3_absorption_quadrants.csv")
    trajectories = load_csv("analysis_5_trajectories.csv")
    covid       = load_csv("analysis_6_covid_flags.csv")

    if any(df is None for df in [rankings, absorption, trajectories, covid]):
        print("ERROR: Missing analysis outputs. Run all analyses first.")
        return None

    # --- Rename / standardise ---
    rankings = rankings[["Empirical_Rank_5yr", "Empirical_Rank_10yr",
                          "Summary_Sheet_Rank", "Rank_Difference_5yr"]].copy()

    absorption = absorption[["Quadrant", "Supply_Growth_5yr", "UPP_Change_5yr",
                              "Absorption_Pressure"]].copy()

    traj_cols = ["Trajectory_Score", "Rank_1yr", "Rank_10yr",
                 "Rent_Growth_1yr", "Rent_Growth_5yr_Ann", "Rent_Growth_10yr_Ann"]
    trajectories = trajectories[[c for c in traj_cols if c in trajectories.columns]].copy()

    covid_cols = ["COVID_Deviation_Flag", "Supply_Shift_Flag",
                  "PreCOVID_SalePrice_AnnGrowth", "COVID_SalePrice_AnnGrowth"]
    covid = covid[[c for c in covid_cols if c in covid.columns]].copy()

    # --- Merge into master table ---
    master = rankings.copy()
    master = master.join(absorption, how="left")
    master = master.join(trajectories, how="left")
    master = master.join(covid, how="left")

    print(f"\nMaster table: {master.shape} ({master.index.nunique()} markets)")

    # --- Filter: top 40 by empirical 5yr rank ---
    top40 = master[master["Empirical_Rank_5yr"] <= 40].copy()
    print(f"\nMarkets in top 40 empirical rank: {len(top40)}")

    # --- Filter: Quadrant 1 or 2 (not oversupplied) ---
    good_quads = ["Q1_HighSupply_TightPerCap", "Q2_LowSupply_TightPerCap"]
    top40_filtered = top40[top40["Quadrant"].isin(good_quads)].copy()
    print(f"After absorption filter (Q1 or Q2): {len(top40_filtered)}")

    # --- Rank for combined score ---
    # 0.6 * empirical_rank_5yr + 0.2 * absorption_pressure_rank + 0.2 * trajectory_score_rank
    top40_filtered = top40_filtered.copy()

    # Absorption pressure rank: higher pressure = better = lower rank
    top40_filtered["absorption_pressure_rank"] = (
        top40_filtered["Absorption_Pressure"].rank(ascending=False)
    )
    # Trajectory score rank: lower trajectory score = better = lower rank
    top40_filtered["trajectory_score_rank"] = (
        top40_filtered["Trajectory_Score"].rank(ascending=True)
    )

    top40_filtered["Combined_Score"] = (
        0.6 * top40_filtered["Empirical_Rank_5yr"] +
        0.2 * top40_filtered["absorption_pressure_rank"] +
        0.2 * top40_filtered["trajectory_score_rank"]
    )
    top40_filtered["Final_Rank"] = top40_filtered["Combined_Score"].rank()
    top40_filtered = top40_filtered.sort_values("Final_Rank")

    print(f"\nFinal target markets: {len(top40_filtered)}")
    print("\nTop 20 final target markets:")
    disp_cols = ["Final_Rank", "Empirical_Rank_5yr", "Quadrant", "Trajectory_Score",
                 "Rent_Growth_5yr_Ann", "COVID_Deviation_Flag"]
    disp_cols = [c for c in disp_cols if c in top40_filtered.columns]
    print(top40_filtered[disp_cols].head(20).to_string())

    # --- Save ---
    final_path = OUTPUTS / "final_target_markets.csv"
    top40_filtered.reset_index().to_csv(final_path, index=False)
    print(f"\nFinal target markets saved -> {final_path}")

    master_path = OUTPUTS / "master_market_table.csv"
    master.reset_index().to_csv(master_path, index=False)
    print(f"Master table saved -> {master_path}")

    return top40_filtered, master


if __name__ == "__main__":
    run_synthesis()
