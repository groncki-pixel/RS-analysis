"""
Data loading and cleaning module for Full_Market_Leveler.xlsx.
Exposes:
  - load_all()  -> (panel_df, cross_section_df, summary_ranks, summary_sorted)
  - DATA_FILE   path constant
"""

import re
import pandas as pd
import numpy as np
from pathlib import Path

DATA_FILE = Path(__file__).parent.parent / "data" / "Full_Market_Leveler.xlsx"

# ---------------------------------------------------------------------------
# Name normalisation
# ---------------------------------------------------------------------------

def normalize_name(name) -> str:
    if not isinstance(name, str):
        return str(name) if pd.notna(name) else ""
    name = name.strip()
    name = re.sub(r'\s*\(USA\)\s*$', '', name)
    name = re.sub(r'\s+USA\s*$', '', name)
    return name.strip()


# ---------------------------------------------------------------------------
# Low-level block parser
# ---------------------------------------------------------------------------

def _parse_block1(
    df_raw: pd.DataFrame,
    date_row: int = 0,
    first_data_row: int = 1,
    last_data_row: int = 150,
    market_col: int = 0,
    time_col_start: int = 1,
    max_time_col=None,
) -> pd.DataFrame:
    """
    Extract Block 1 (raw levels) from a raw sheet DataFrame.
    Returns DataFrame with market as index and quarter labels as columns.
    """
    header = df_raw.iloc[date_row, time_col_start:max_time_col].tolist()
    # Clean EST suffix from column names
    cols = [str(h).strip().replace(" EST", "") for h in header]

    data = df_raw.iloc[first_data_row: last_data_row + 1, :].copy()
    markets = data.iloc[:, market_col].apply(normalize_name)

    values = data.iloc[:, time_col_start:max_time_col].values

    out = pd.DataFrame(values, index=markets, columns=cols)
    out.index.name = "market"

    # Drop empty/NaN market rows
    out = out[out.index.notna() & (out.index != "") & (out.index != "nan") & (out.index != "None")]
    out = out.apply(pd.to_numeric, errors="coerce")
    return out


# ---------------------------------------------------------------------------
# Individual sheet loaders
# ---------------------------------------------------------------------------

def load_asking_rent() -> pd.DataFrame:
    df = pd.read_excel(DATA_FILE, sheet_name="Asking Rent", header=None)
    return _parse_block1(df, date_row=0, first_data_row=1, last_data_row=150,
                         market_col=0, time_col_start=1)


def load_effective_rent_forward() -> pd.DataFrame:
    """Market col=3, time cols start at 5."""
    df = pd.read_excel(DATA_FILE, sheet_name="Effective Rent-Forward", header=None)
    return _parse_block1(df, date_row=0, first_data_row=1, last_data_row=150,
                         market_col=3, time_col_start=5)


def load_forward_employment() -> pd.DataFrame:
    """Use only cols 0-41 (duplicate block starts at col 42)."""
    df = pd.read_excel(DATA_FILE, sheet_name="Forward Employment", header=None)
    df = df.iloc[:, :42]
    return _parse_block1(df, date_row=0, first_data_row=1, last_data_row=150,
                         market_col=0, time_col_start=1)


def load_supply_forward() -> pd.DataFrame:
    df = pd.read_excel(DATA_FILE, sheet_name="Supply Forward", header=None)
    return _parse_block1(df, date_row=0, first_data_row=1, last_data_row=150,
                         market_col=0, time_col_start=1)


def load_income_growth() -> pd.DataFrame:
    df = pd.read_excel(DATA_FILE, sheet_name="Income Growth", header=None)
    return _parse_block1(df, date_row=0, first_data_row=1, last_data_row=150,
                         market_col=0, time_col_start=1)


def load_population_growth_forward() -> pd.DataFrame:
    """Market col=3, time cols start at 5."""
    df = pd.read_excel(DATA_FILE, sheet_name="Population Growth Forward", header=None)
    return _parse_block1(df, date_row=0, first_data_row=1, last_data_row=150,
                         market_col=3, time_col_start=5)


def load_forward_sale_price() -> pd.DataFrame:
    df = pd.read_excel(DATA_FILE, sheet_name="Forward Sale Price", header=None)
    df = df.iloc[:, :42]  # drop blank trailing col
    return _parse_block1(df, date_row=0, first_data_row=1, last_data_row=150,
                         market_col=0, time_col_start=1)


def load_supply_historical() -> pd.DataFrame:
    """Market col=3, time cols start at 5."""
    df = pd.read_excel(DATA_FILE, sheet_name="Supply Historical", header=None)
    return _parse_block1(df, date_row=0, first_data_row=1, last_data_row=150,
                         market_col=3, time_col_start=5)


def load_historical_sale_price() -> pd.DataFrame:
    df = pd.read_excel(DATA_FILE, sheet_name="Historical Sale Price", header=None)
    return _parse_block1(df, date_row=0, first_data_row=1, last_data_row=150,
                         market_col=0, time_col_start=1)


def load_upp_historical() -> dict:
    """
    Three stacked variable sections:
      Inventory : rows 3-152  (time header at row 2)
      Population: rows 157-306 (time header at row 156)
      UPP ratio : rows 311-460 (time header at row 2, same cols)
    """
    df = pd.read_excel(DATA_FILE, sheet_name="UPP Historical", header=None)

    inv = _parse_block1(df, date_row=2, first_data_row=3, last_data_row=152,
                        market_col=0, time_col_start=1)

    pop = _parse_block1(df, date_row=156, first_data_row=157, last_data_row=306,
                        market_col=0, time_col_start=1)

    # UPP ratio: row 310 header has NaN for times; reuse row 2 for time labels
    upp = _parse_block1(df, date_row=2, first_data_row=311, last_data_row=460,
                        market_col=0, time_col_start=1)

    return {"inventory": inv, "population": pop, "upp_ratio": upp}


def load_forward_upp() -> dict:
    """
    Block 1 (inventory): rows 1-150,    header row 0
    Block 2 (population): rows 154-303, header row 153
    Block 3 (UPP ratio):  rows 307-456, header row 306
    """
    df = pd.read_excel(DATA_FILE, sheet_name="Forward UPP", header=None)

    inv = _parse_block1(df, date_row=0, first_data_row=1, last_data_row=150,
                        market_col=0, time_col_start=1)

    pop = _parse_block1(df, date_row=153, first_data_row=154, last_data_row=303,
                        market_col=0, time_col_start=1)

    upp = _parse_block1(df, date_row=306, first_data_row=307, last_data_row=456,
                        market_col=0, time_col_start=1)

    return {"inventory": inv, "population": pop, "upp_ratio": upp}


# ---------------------------------------------------------------------------
# Historical summary sheets
# ---------------------------------------------------------------------------

def load_effective_rent_historical() -> pd.DataFrame:
    df = pd.read_excel(DATA_FILE, sheet_name="Effective Rent Historical", header=None)
    data = df.iloc[2:].copy()
    out = pd.DataFrame({
        "market":        data.iloc[:, 0].apply(normalize_name),
        "eff_rent_5yr":  pd.to_numeric(data.iloc[:, 1], errors="coerce"),
        "eff_rent_10yr": pd.to_numeric(data.iloc[:, 6], errors="coerce"),
    })
    out = out[out["market"].notna() & (out["market"] != "") & (out["market"] != "nan")]
    return out.set_index("market")


def load_historical_employment() -> pd.DataFrame:
    df = pd.read_excel(DATA_FILE, sheet_name="Historical Employment", header=None)
    data = df.iloc[3:].copy()
    out = pd.DataFrame({
        "market":   data.iloc[:, 1].apply(normalize_name),
        "emp_5yr":  pd.to_numeric(data.iloc[:, 2], errors="coerce"),
        "emp_10yr": pd.to_numeric(data.iloc[:, 6], errors="coerce"),
    })
    out = out[out["market"].notna() & (out["market"] != "") & (out["market"] != "nan")]
    return out.set_index("market")


def load_historical_population() -> pd.DataFrame:
    df = pd.read_excel(DATA_FILE, sheet_name="Historical Population Growth", header=None)
    data = df.iloc[2:].copy()
    out = pd.DataFrame({
        "market":   data.iloc[:, 1].apply(normalize_name),
        "pop_5yr":  pd.to_numeric(data.iloc[:, 2], errors="coerce"),
        "pop_10yr": pd.to_numeric(data.iloc[:, 7], errors="coerce"),
    })
    out = out[out["market"].notna() & (out["market"] != "") & (out["market"] != "nan")]
    return out.set_index("market")


def load_summary_sheet():
    """
    Returns (summary_ranks, summary_sorted):
      summary_ranks: one row per market with all rank columns
      summary_sorted: pre-sorted ranking table from right side of sheet
    """
    df = pd.read_excel(DATA_FILE, sheet_name="Summary Sheet", header=None)

    data = df.iloc[3:, :].copy()
    data = data.reset_index(drop=True)

    markets = data.iloc[:, 0].apply(normalize_name)

    col_map = {
        "ask_rent_f1": 1, "ask_rent_f3": 2, "ask_rent_f5": 3, "ask_rent_f10": 4,
        "eff_rent_f1": 5, "eff_rent_f3": 6, "eff_rent_f5": 7, "eff_rent_f10": 8,
        "emp_hist_10yr": 9, "emp_hist_5yr": 10,
        "emp_f1": 11, "emp_f3": 12, "emp_f5": 13, "emp_f10": 14,
        "supply_hist5": 15, "supply_f1": 16, "supply_f3": 17, "supply_f5": 18, "supply_f10": 19,
        "upp_hist10": 20, "upp_f5": 21, "upp_f10": 22,
        "income_f1": 23, "income_f3": 24, "income_f5": 25, "income_f10": 26,
        "pop_hist_10yr": 27, "pop_hist_5yr": 28,
        "pop_f1": 29, "pop_f3": 30, "pop_f5": 31, "pop_f10": 32,
        "sale_hist1": 33, "sale_hist3": 34, "sale_hist5": 35, "sale_hist10": 36,
        "sale_f1": 37, "sale_f3": 38, "sale_f5": 39, "sale_f10": 40,
        "simple_avg": 41, "weighted_avg": 42,
    }

    main_table = pd.DataFrame({"market": markets})
    for name, col in col_map.items():
        if col < data.shape[1]:
            main_table[name] = pd.to_numeric(data.iloc[:, col].values, errors="coerce")

    main_table = main_table[
        main_table["market"].notna() &
        (main_table["market"] != "") &
        (main_table["market"] != "nan")
    ].set_index("market")

    # Pre-sorted ranking: cols 45=Market, 46=Weighted Avg, 47=Rank
    sorted_markets = data.iloc[:, 45].apply(normalize_name)
    sorted_tbl = pd.DataFrame({
        "market":       sorted_markets,
        "weighted_avg": pd.to_numeric(data.iloc[:, 46], errors="coerce"),
        "rank":         pd.to_numeric(data.iloc[:, 47], errors="coerce"),
    })
    sorted_tbl = sorted_tbl[
        sorted_tbl["market"].notna() &
        (sorted_tbl["market"] != "") &
        (sorted_tbl["market"] != "nan") &
        sorted_tbl["rank"].notna()
    ].set_index("market")

    return main_table, sorted_tbl


# ---------------------------------------------------------------------------
# Quarter conversion
# ---------------------------------------------------------------------------

def _quarter_to_period(q: str):
    q = str(q).strip().replace(" EST", "")
    parts = q.split()
    if len(parts) == 2 and parts[1].startswith("Q"):
        try:
            return pd.Period(f"{parts[0]}Q{parts[1][1]}", freq="Q")
        except Exception:
            pass
    return pd.NaT


def _wide_to_long(df: pd.DataFrame, variable: str) -> pd.DataFrame:
    long = df.reset_index().melt(id_vars="market", var_name="quarter_str", value_name=variable)
    long["quarter"] = long["quarter_str"].apply(_quarter_to_period)
    long = long.drop(columns="quarter_str")
    return long[long["quarter"].notna()][["market", "quarter", variable]]


# ---------------------------------------------------------------------------
# Growth helper
# ---------------------------------------------------------------------------

def _compute_growth_ratio(df_wide: pd.DataFrame) -> pd.Series:
    """last non-NaN value / first non-NaN value for each market row."""
    def ratio(row):
        vals = row.dropna()
        if len(vals) < 2:
            return np.nan
        return vals.iloc[-1] / vals.iloc[0]
    return df_wide.apply(ratio, axis=1)


def _fwd_growth(df_wide: pd.DataFrame, col_idx: int) -> pd.Series:
    """(value at col_idx) / (value at col 0) - 1."""
    if col_idx >= df_wide.shape[1]:
        col_idx = df_wide.shape[1] - 1
    base = df_wide.iloc[:, 0]
    end  = df_wide.iloc[:, col_idx]
    return (end / base - 1).rename(None)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def load_all():
    """
    Returns
    -------
    panel         : long-format (market, quarter, variables...)
    cross_section : one row per market with growth rates
    summary_ranks : Summary Sheet rank table
    summary_sorted: pre-sorted ranking from Summary Sheet right panel
    """
    print("Loading sheets from Excel...")

    ask_rent     = load_asking_rent()
    eff_rent_fwd = load_effective_rent_forward()
    emp_fwd      = load_forward_employment()
    supply_fwd   = load_supply_forward()
    income       = load_income_growth()
    pop_fwd      = load_population_growth_forward()
    sale_fwd     = load_forward_sale_price()
    supply_hist  = load_supply_historical()
    sale_hist    = load_historical_sale_price()
    upp_hist     = load_upp_historical()
    upp_fwd      = load_forward_upp()
    eff_rent_hist   = load_effective_rent_historical()
    emp_hist_cs     = load_historical_employment()
    pop_hist_cs     = load_historical_population()
    summary_ranks, summary_sorted = load_summary_sheet()

    print("  All sheets loaded. Building panel...")

    # --- Panel ---
    pieces = [
        _wide_to_long(ask_rent,          "asking_rent"),
        _wide_to_long(eff_rent_fwd,      "eff_rent"),
        _wide_to_long(emp_fwd,           "employment"),
        _wide_to_long(supply_fwd,        "supply_fwd"),
        _wide_to_long(income,            "income"),
        _wide_to_long(pop_fwd,           "population_fwd"),
        _wide_to_long(sale_fwd,          "sale_price_fwd"),
        _wide_to_long(supply_hist,       "supply_hist"),
        _wide_to_long(sale_hist,         "sale_price_hist"),
        _wide_to_long(upp_hist["inventory"],  "upp_inv_hist"),
        _wide_to_long(upp_hist["population"], "upp_pop_hist"),
        _wide_to_long(upp_hist["upp_ratio"],  "upp_ratio_hist"),
        _wide_to_long(upp_fwd["inventory"],   "upp_inv_fwd"),
        _wide_to_long(upp_fwd["population"],  "upp_pop_fwd"),
        _wide_to_long(upp_fwd["upp_ratio"],   "upp_ratio_fwd"),
    ]

    panel = pieces[0]
    for p in pieces[1:]:
        panel = panel.merge(p, on=["market", "quarter"], how="outer")

    panel = panel.sort_values(["market", "quarter"]).reset_index(drop=True)

    # Growth rates
    lvars = [
        "asking_rent", "eff_rent", "employment", "supply_fwd", "income",
        "population_fwd", "sale_price_fwd", "supply_hist", "sale_price_hist",
        "upp_inv_hist", "upp_ratio_hist", "upp_inv_fwd", "upp_ratio_fwd",
    ]
    for v in lvars:
        if v not in panel.columns:
            continue
        panel[f"{v}_qoq"] = panel.groupby("market")[v].pct_change()
        panel[f"{v}_yoy"] = panel.groupby("market")[v].pct_change(4)

    # --- Cross-section ---
    cs = eff_rent_hist.copy()
    cs = cs.join(emp_hist_cs, how="outer")
    cs = cs.join(pop_hist_cs, how="outer")

    cs["supply_hist_growth"]     = _compute_growth_ratio(supply_hist)
    cs["sale_price_hist_growth"] = _compute_growth_ratio(sale_hist)
    cs["upp_inv_hist_growth"]    = _compute_growth_ratio(upp_hist["inventory"])

    # Forward growth horizons (quarter offsets from first col, 0-based)
    # 2025 Q2 is col 0; 1yr≈4q offset=3; 3yr≈12q offset=11; 5yr≈20q offset=19; 10yr≈40q offset=39
    horizons = {"1yr": 3, "3yr": 11, "5yr": 19, "10yr": 39}

    for h, off in horizons.items():
        cs[f"eff_rent_fwd_{h}"]     = _fwd_growth(eff_rent_fwd, off)
        cs[f"employment_fwd_{h}"]   = _fwd_growth(emp_fwd,      off)
        cs[f"supply_fwd_{h}"]       = _fwd_growth(supply_fwd,   off)
        cs[f"income_fwd_{h}"]       = _fwd_growth(income,       off)
        cs[f"pop_fwd_{h}"]          = _fwd_growth(pop_fwd,      off)
        cs[f"sale_price_fwd_{h}"]   = _fwd_growth(sale_fwd,     off)
        cs[f"upp_ratio_fwd_{h}"]    = _fwd_growth(upp_fwd["upp_ratio"], off)
        # UPP absolute change
        base = upp_fwd["upp_ratio"].iloc[:, 0]
        end_col = min(off, upp_fwd["upp_ratio"].shape[1] - 1)
        cs[f"upp_ratio_change_{h}"] = upp_fwd["upp_ratio"].iloc[:, end_col] - base

    cs.index.name = "market"
    print(f"  Panel: {panel.shape}  Cross-section: {cs.shape}")
    return panel, cs, summary_ranks, summary_sorted


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    panel, cs, summary_ranks, summary_sorted = load_all()

    markets = panel["market"].unique()
    print(f"\n=== VALIDATION ===")
    print(f"Markets loaded: {len(markets)}")

    print("\nDate range per variable:")
    for v in ["asking_rent", "eff_rent", "employment", "supply_fwd", "income",
              "population_fwd", "sale_price_fwd", "supply_hist", "sale_price_hist",
              "upp_inv_hist", "upp_ratio_hist"]:
        if v not in panel.columns:
            print(f"  {v}: NOT FOUND")
            continue
        sub = panel[panel[v].notna()]
        if sub.empty:
            print(f"  {v}: no data")
            continue
        print(f"  {v}: {sub['quarter'].min()} -> {sub['quarter'].max()} ({sub['market'].nunique()} markets)")

    print("\nSample markets (first 3):")
    for m in sorted(markets)[:3]:
        sub = panel[panel["market"] == m][
            ["quarter", "asking_rent", "eff_rent", "supply_fwd", "employment"]
        ].dropna(how="all").head(4)
        print(f"\n  {m}")
        print(sub.to_string(index=False))

    print("\nCross-section columns:", cs.columns.tolist())
    print("\nCross-section sample (3 markets):")
    print(cs[["eff_rent_5yr", "eff_rent_10yr", "supply_hist_growth",
              "eff_rent_fwd_5yr", "supply_fwd_5yr"]].head(3).to_string())

    print("\nSummary sorted top 10:")
    print(summary_sorted.head(10).to_string())
