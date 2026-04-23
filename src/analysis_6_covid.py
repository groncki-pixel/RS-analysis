"""
Analysis 6: COVID Distortion Flags
Identify markets with largest COVID-era dislocations in sale prices and supply.
"""

import sys
import warnings
import numpy as np
import pandas as pd
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.data_loader import load_all, load_historical_sale_price, load_supply_historical

OUTPUTS = Path(__file__).parent.parent / "outputs"
OUTPUTS.mkdir(exist_ok=True)


def _annualized_growth(start_val, end_val, n_years):
    """Annualised growth rate from multiplier."""
    if pd.isna(start_val) or pd.isna(end_val) or start_val <= 0:
        return np.nan
    if n_years <= 0:
        return np.nan
    return (end_val / start_val) ** (1 / n_years) - 1


def run_analysis_6():
    print("\n=== ANALYSIS 6: COVID Distortion Flags ===")

    sale_hist   = load_historical_sale_price()   # 2015Q1 -> 2025Q1, 41 qtrs
    supply_hist = load_supply_historical()        # 2020Q2 -> 2025Q1, 20 qtrs

    sale_cols   = sale_hist.columns.tolist()
    supply_cols = supply_hist.columns.tolist()

    print(f"Sale price range: {sale_cols[0]} -> {sale_cols[-1]}")
    print(f"Supply range: {supply_cols[0]} -> {supply_cols[-1]}")

    # --- Find column indices for key dates ---
    def find_col(cols, target):
        for i, c in enumerate(cols):
            if target in str(c):
                return i
        return None

    # Sale price: 2015Q1->2020Q1 (pre-COVID), 2020Q1->2022Q1 (COVID), 2022Q1->2025Q1 (post)
    sale_idx = {
        "2015Q1": find_col(sale_cols, "2015 Q1"),
        "2020Q1": find_col(sale_cols, "2020 Q1"),
        "2022Q1": find_col(sale_cols, "2022 Q1"),
        "2025Q1": find_col(sale_cols, "2025 Q1"),
    }
    print(f"\nSale price column indices: {sale_idx}")

    # Supply: 2020Q2->2022Q2, 2022Q2->2025Q1
    supply_idx = {
        "2020Q2": find_col(supply_cols, "2020 Q2"),
        "2022Q2": find_col(supply_cols, "2022 Q2"),
        "2025Q1": find_col(supply_cols, "2025 Q1"),
    }
    print(f"Supply column indices: {supply_idx}")

    records = {}

    for market in sale_hist.index:
        row = sale_hist.loc[market]

        def safe_val(idx):
            if idx is None:
                return np.nan
            try:
                v = row.iloc[idx]
                return float(v) if pd.notna(v) else np.nan
            except Exception:
                return np.nan

        pre_start = safe_val(sale_idx["2015Q1"])
        pre_end   = safe_val(sale_idx["2020Q1"])
        cov_end   = safe_val(sale_idx["2022Q1"])
        post_end  = safe_val(sale_idx["2025Q1"])

        pre_ann  = _annualized_growth(pre_start, pre_end, 5.0)
        cov_ann  = _annualized_growth(pre_end, cov_end, 2.0)
        post_ann = _annualized_growth(cov_end, post_end, 3.0)

        # Flag: COVID deviation > 2x pre-COVID trend (either direction)
        cov_flag = False
        if pd.notna(pre_ann) and pd.notna(cov_ann) and abs(pre_ann) > 0.001:
            ratio = cov_ann / pre_ann
            cov_flag = abs(ratio) > 2.0 or ratio < 0

        records[market] = {
            "PreCOVID_SalePrice_AnnGrowth": pre_ann,
            "COVID_SalePrice_AnnGrowth":    cov_ann,
            "PostCOVID_SalePrice_AnnGrowth": post_ann,
            "COVID_Deviation_Flag": cov_flag,
        }

    # --- Supply flags ---
    for market in supply_hist.index:
        row = supply_hist.loc[market]

        def safe_s(idx):
            if idx is None:
                return np.nan
            try:
                v = row.iloc[idx]
                return float(v) if pd.notna(v) else np.nan
            except Exception:
                return np.nan

        s_2020 = safe_s(supply_idx["2020Q2"])
        s_2022 = safe_s(supply_idx["2022Q2"])
        s_2025 = safe_s(supply_idx["2025Q1"])

        early_g = _annualized_growth(s_2020, s_2022, 2.0)
        late_g  = _annualized_growth(s_2022, s_2025, 2.75)

        # Flag: growth rate shifted dramatically (>1.5x change)
        shift_flag = False
        if pd.notna(early_g) and pd.notna(late_g) and abs(early_g) > 0.0001:
            ratio = late_g / early_g if early_g != 0 else np.nan
            if pd.notna(ratio):
                shift_flag = abs(ratio) > 1.5 or ratio < 0

        if market in records:
            records[market]["Supply_Early_Growth"] = early_g
            records[market]["Supply_Late_Growth"]  = late_g
            records[market]["Supply_Shift_Flag"]   = shift_flag
        else:
            records[market] = {
                "PreCOVID_SalePrice_AnnGrowth": np.nan,
                "COVID_SalePrice_AnnGrowth":    np.nan,
                "PostCOVID_SalePrice_AnnGrowth": np.nan,
                "COVID_Deviation_Flag": False,
                "Supply_Early_Growth": early_g,
                "Supply_Late_Growth":  late_g,
                "Supply_Shift_Flag":   shift_flag,
            }

    covid_df = pd.DataFrame.from_dict(records, orient="index")
    covid_df.index.name = "market"

    n_cov  = covid_df["COVID_Deviation_Flag"].sum()
    n_sup  = covid_df["Supply_Shift_Flag"].sum()
    print(f"\nCOVID sale-price deviation flags: {n_cov}")
    print(f"Supply shift flags: {n_sup}")

    print("\nTop COVID-flagged markets (sale price):")
    flagged = covid_df[covid_df["COVID_Deviation_Flag"] == True].sort_values(
        "COVID_SalePrice_AnnGrowth", ascending=False)
    print(flagged[["PreCOVID_SalePrice_AnnGrowth","COVID_SalePrice_AnnGrowth",
                   "PostCOVID_SalePrice_AnnGrowth"]].head(15).to_string())

    out_path = OUTPUTS / "analysis_6_covid_flags.csv"
    covid_df.reset_index().to_csv(out_path, index=False)
    print(f"\nCOVID flags saved -> {out_path}")

    return covid_df


if __name__ == "__main__":
    run_analysis_6()
