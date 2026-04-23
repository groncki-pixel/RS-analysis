"""
Analysis 2: Forward Composite Score with Empirical Weights
Re-rank markets using coefficients from Analysis 1 instead of arbitrary weights.
"""

import sys
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.data_loader import load_all
from src.analysis_1_attribution import run_analysis_1

OUTPUTS = Path(__file__).parent.parent / "outputs"
OUTPUTS.mkdir(exist_ok=True)


def run_analysis_2(coef_table=None):
    print("\n=== ANALYSIS 2: Forward Composite Score ===")
    panel, cs, summary_ranks, summary_sorted = load_all()

    if coef_table is None:
        coef_table = run_analysis_1()

    # --- Empirical weights from Analysis 1 standardised coefficients ---
    # Variables available in forward data:
    # eff_rent_fwd, supply_fwd, employment_fwd, pop_fwd, income_fwd, sale_price_fwd
    # Map Analysis 1 variable names to forward variable names
    var_map = {
        "supply_growth":     "supply_fwd",
        "employment_growth": "employment_fwd",
        "pop_growth":        "pop_fwd",
        "sale_price_growth": "sale_price_fwd",
    }

    # We also include eff_rent and income as additional forward variables
    # For eff_rent: use the absolute std coef magnitude proxy (treat same sign as sale price for rent)
    # For income: no direct historical variable, assign small weight equal to pop

    # Get abs coefs for the mapped variables
    abs_coefs = {}
    for hist_var, fwd_var in var_map.items():
        if hist_var in coef_table.index:
            abs_coefs[fwd_var] = abs(coef_table.loc[hist_var, "Std_Coef"])

    # Add eff_rent (use sale_price as proxy) and income (use pop proxy)
    abs_coefs["eff_rent"] = abs_coefs.get("sale_price_fwd", 0.1)
    abs_coefs["income_fwd"] = abs_coefs.get("pop_fwd", 0.05)

    total_w = sum(abs_coefs.values())
    weights = {k: v / total_w for k, v in abs_coefs.items()}

    print("\nEmpirical weights:")
    for k, w in sorted(weights.items(), key=lambda x: -x[1]):
        print(f"  {k}: {w:.4f}")

    horizons = {"1yr": 3, "3yr": 11, "5yr": 19, "10yr": 39}

    # Compute forward growth rates for each variable/horizon
    from src.data_loader import (
        load_asking_rent, load_effective_rent_forward, load_forward_employment,
        load_supply_forward, load_income_growth, load_population_growth_forward,
        load_forward_sale_price, load_forward_upp, _fwd_growth
    )

    eff_rent_fwd = load_effective_rent_forward()
    emp_fwd      = load_forward_employment()
    supply_fwd   = load_supply_forward()
    income       = load_income_growth()
    pop_fwd      = load_population_growth_forward()
    sale_fwd     = load_forward_sale_price()

    records = {}  # market -> dict of growth rates

    all_markets = set(eff_rent_fwd.index)

    for market in all_markets:
        rec = {"market": market}
        for h, off in horizons.items():
            def _g(df, m):
                if m not in df.index:
                    return np.nan
                row = df.loc[m]
                base = row.iloc[0]
                end  = row.iloc[min(off, len(row)-1)]
                if pd.isna(base) or base == 0:
                    return np.nan
                return end / base - 1

            rec[f"eff_rent_{h}"]     = _g(eff_rent_fwd, market)
            rec[f"employment_{h}"]   = _g(emp_fwd, market)
            rec[f"supply_{h}"]       = _g(supply_fwd, market)
            rec[f"income_{h}"]       = _g(income, market)
            rec[f"pop_{h}"]          = _g(pop_fwd, market)
            rec[f"sale_price_{h}"]   = _g(sale_fwd, market)
        records[market] = rec

    growth_df = pd.DataFrame.from_dict(records, orient="index")
    growth_df.index.name = "market"

    # --- Rank per horizon ---
    rank_dfs = {}
    for h in horizons.keys():
        rd = pd.DataFrame(index=growth_df.index)
        # Higher = better for rent, employment, income, pop, sale_price
        for v in ["eff_rent", "employment", "income", "pop", "sale_price"]:
            col = f"{v}_{h}"
            if col in growth_df.columns:
                rd[v] = growth_df[col].rank(ascending=False)
        # Supply: invert — LOWEST supply growth = best rank
        sc = f"supply_{h}"
        if sc in growth_df.columns:
            rd["supply_fwd"] = growth_df[sc].rank(ascending=True)

        # Composite weighted rank
        rank_vars = {
            "eff_rent":    "eff_rent",
            "supply_fwd":  "supply_fwd",
            "employment_fwd": "employment",
            "pop_fwd":     "pop",
            "income_fwd":  "income",
            "sale_price_fwd": "sale_price",
        }
        composite = pd.Series(0.0, index=rd.index)
        w_total = 0
        for wkey, rkey in rank_vars.items():
            if rkey in rd.columns and wkey in weights:
                composite += rd[rkey] * weights[wkey]
                w_total += weights[wkey]
        if w_total > 0:
            composite /= w_total

        rd["composite_score"] = composite
        rd["composite_rank"]  = composite.rank()
        rank_dfs[h] = rd

    # --- Compare to Summary Sheet ---
    print("\n--- Spearman Rank Correlation vs Summary Sheet ---")
    for h in horizons.keys():
        rd = rank_dfs[h]
        merged = rd[["composite_rank"]].join(
            summary_ranks[f"eff_rent_f5"].rename("ss_rank"), how="inner"
        )
        # Use Summary Sheet weighted avg rank
        merged = rd[["composite_rank"]].join(
            summary_ranks["weighted_avg"].rename("ss_weighted"), how="inner"
        )
        merged["ss_rank"] = merged["ss_weighted"].rank()
        if merged.dropna().shape[0] >= 5:
            rho, pval = spearmanr(merged["composite_rank"].dropna(),
                                  merged["ss_rank"].dropna())
            print(f"  {h}: Spearman rho={rho:.3f} p={pval:.3f}")

    # 5yr focus
    rd5 = rank_dfs["5yr"].copy()
    rd5.columns = [f"rank_{c}" if c not in ["composite_score","composite_rank"] else c
                   for c in rd5.columns]

    # Add Summary Sheet rank
    ss_rank = summary_ranks["weighted_avg"].rank().rename("ss_rank_5yr")
    rd5 = rd5.join(ss_rank, how="left")
    rd5["ss_empirical_diff_5yr"] = rd5["ss_rank_5yr"] - rd5["composite_rank"]

    edge_markets = rd5["ss_empirical_diff_5yr"].abs().nlargest(20)
    print("\nTop 'edge' markets where ranks diverge by 10+:")
    big_diff = rd5[rd5["ss_empirical_diff_5yr"].abs() >= 10]
    print(big_diff[["composite_rank","ss_rank_5yr","ss_empirical_diff_5yr"]]
          .sort_values("ss_empirical_diff_5yr", key=abs, ascending=False)
          .head(15).to_string())

    # --- Output: market rankings CSV ---
    out = pd.DataFrame(index=growth_df.index)
    for h in horizons.keys():
        out[f"Empirical_Rank_{h}"] = rank_dfs[h]["composite_rank"]
    out["Summary_Sheet_Rank"] = summary_ranks["weighted_avg"].rank()
    out["Rank_Difference_5yr"] = out["Summary_Sheet_Rank"] - out["Empirical_Rank_5yr"]
    out = out.sort_values("Empirical_Rank_5yr")

    rank_path = OUTPUTS / "analysis_2_market_rankings.csv"
    out.reset_index().to_csv(rank_path, index=False)
    print(f"\nMarket rankings saved -> {rank_path}")

    # --- Top 30 by 5yr empirical rank ---
    top30_idx = rank_dfs["5yr"].nsmallest(30, "composite_rank").index
    top30 = out.loc[top30_idx].copy()
    for h in horizons.keys():
        for v in ["eff_rent","supply","employment","income","pop","sale_price"]:
            col = f"{v}_{h}"
            if col in growth_df.columns:
                top30[f"growth_{v}_{h}"] = growth_df.loc[top30_idx, col]
    top30_path = OUTPUTS / "analysis_2_top30_markets.csv"
    top30.reset_index().to_csv(top30_path, index=False)
    print(f"Top 30 saved -> {top30_path}")

    print("\nTop 30 markets (5yr empirical rank):")
    print(top30[["Empirical_Rank_5yr","Empirical_Rank_10yr","Summary_Sheet_Rank"]]
          .head(30).to_string())

    return rank_dfs, growth_df


if __name__ == "__main__":
    run_analysis_2()
