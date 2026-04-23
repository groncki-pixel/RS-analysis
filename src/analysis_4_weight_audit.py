"""
Analysis 4: Summary Sheet Weight Audit
Show that arbitrary weights differ from empirical weights and quantify the effect.
"""

import sys
import warnings
import numpy as np
import pandas as pd
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.data_loader import load_all
from src.analysis_1_attribution import run_analysis_1

OUTPUTS = Path(__file__).parent.parent / "outputs"
OUTPUTS.mkdir(exist_ok=True)


def run_analysis_4(coef_table=None):
    print("\n=== ANALYSIS 4: Summary Sheet Weight Audit ===")
    panel, cs, summary_ranks, summary_sorted = load_all()

    if coef_table is None:
        coef_table = run_analysis_1()

    # --- Summary Sheet weights (stated) ---
    # From row 1: Effective Rent 0.2, Employment 0.1, Supply ~0.1, UPP 0.2, Income 0.1, Pop 0.1, Sale Price 0.2
    # The column layout (from summary_ranks):
    # eff_rent_f5, emp_f5, supply_f5, upp_f5, income_f5, pop_f5, sale_f5
    ss_weights = {
        "eff_rent_f5":  0.20,
        "emp_f5":       0.10,
        "supply_f5":    0.10,
        "upp_f5":       0.20,
        "income_f5":    0.10,
        "pop_f5":       0.10,
        "sale_f5":      0.20,
    }
    print("\nSummary Sheet stated weights:")
    for k, v in ss_weights.items():
        print(f"  {k}: {v:.2f}")

    # --- Empirical weights from Analysis 1 ---
    var_map_emp = {
        "supply_growth":     "supply_f5",
        "employment_growth": "emp_f5",
        "pop_growth":        "pop_f5",
        "sale_price_growth": "sale_f5",
    }
    abs_coefs = {}
    for hist_var, rank_col in var_map_emp.items():
        if hist_var in coef_table.index:
            abs_coefs[rank_col] = abs(coef_table.loc[hist_var, "Std_Coef"])

    # Assign proxies for missing variables
    abs_coefs["eff_rent_f5"] = abs_coefs.get("sale_f5", 0.1)
    abs_coefs["upp_f5"]      = abs_coefs.get("supply_f5", 0.05)
    abs_coefs["income_f5"]   = abs_coefs.get("pop_f5", 0.02)

    total_w = sum(abs_coefs.values())
    emp_weights = {k: v / total_w for k, v in abs_coefs.items()}

    print("\nEmpirical weights (normalised):")
    for k, v in sorted(emp_weights.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v:.4f}")

    # --- Use Summary Sheet rank columns for recomputing scores ---
    rank_cols = list(ss_weights.keys())
    available_cols = [c for c in rank_cols if c in summary_ranks.columns]

    print(f"\nUsing rank columns: {available_cols}")
    working = summary_ranks[available_cols].dropna()
    print(f"Markets with complete rank data: {len(working)}")

    # Recompute original weighted score using SS weights
    def compute_score(df, weights):
        score = pd.Series(0.0, index=df.index)
        total = 0
        for col, w in weights.items():
            if col in df.columns:
                score += df[col] * w
                total += w
        if total > 0:
            score /= total
        return score

    orig_score = compute_score(working, ss_weights)
    emp_score  = compute_score(working, emp_weights)

    orig_rank = orig_score.rank()
    emp_rank  = emp_score.rank()

    comparison = pd.DataFrame({
        "Original_Rank":   orig_rank,
        "Empirical_Rank":  emp_rank,
        "Rank_Difference": emp_rank - orig_rank,
    }).sort_values("Original_Rank")

    print("\n--- Top 10 markets IMPROVING under empirical weights ---")
    improving = comparison.nsmallest(10, "Rank_Difference")
    print(improving.to_string())

    print("\n--- Top 10 markets DECLINING under empirical weights ---")
    declining = comparison.nlargest(10, "Rank_Difference")
    print(declining.to_string())

    out_path = OUTPUTS / "analysis_4_weight_comparison.csv"
    comparison.reset_index().to_csv(out_path, index=False)
    print(f"\nWeight comparison saved -> {out_path}")

    return comparison


if __name__ == "__main__":
    run_analysis_4()
