# Real Estate Market Selection Model — Analysis Instructions

## Project Context

We are building a data-driven market selection framework for an institutional real estate investment firm. The firm targets high-income renters across the top ~30-40 US MSAs. Their thesis: higher-income renters have the highest discretionary spending and spend heavily on brands and wellness, making them attractive tenants for institutional owners. The firm wants to identify which MSAs will outperform on rent growth over the next 3-10 years so they can acquire assets ahead of the curve.

The key insight from a prior Harvard study their partner commissioned: **inventory/supply is the dominant driver of rent growth**, more than employment, population, or income. We need to test this claim and build around it.

The final output must be investor-facing — directionally accurate, clearly defensible, not overfit.

---

## Data Source

Single Excel file: `Full_Market_Leveler.xlsx`

### CRITICAL DATA STRUCTURE NOTES

**Most sheets contain 3 row blocks of ~150 markets each, separated by blank rows:**
- Block 1 (rows 0-149): Raw dollar/unit levels
- Block 2 (rows ~153-302): Cumulative growth indices rebased to 1 at 2025 Q2
- Block 3 (rows ~305-454): Forward growth multipliers at 1/3/5/10yr horizons (only ~4 values per market, then market name repeats)

**You must parse Block 1 (the raw levels) for all time series analysis.** Blocks 2 and 3 are derived and useful for quick checks but not for regression.

**Market name formats vary across sheets:**
- Some use `"Akron - OH"`, others use `"Akron - OH USA"`, others `"Akron - OH (USA)"`
- You MUST normalize market names during data cleaning. Strip ` USA`, ` (USA)`, and any trailing whitespace to get a consistent join key.

### Sheet-by-Sheet Data Inventory

#### Forward Quarterly Series (2025 Q2 → 2035 Q2, ~40 quarters)
All of these have the 3-block structure. Use Block 1 only.

| Sheet | Variable | Unit | Notes |
|-------|----------|------|-------|
| `Asking Rent` | Asking rent per unit | $/unit | |
| `Effective Rent-Forward` | Effective rent per unit | $/unit | Has extra cols: Property Class Name, Slice, As Of, Geography Name, Concept Name before time cols. Time cols start at col index 5. |
| `Forward Employment` | Employment level | persons | Has a second block of columns starting at col 42 that appears to be a duplicate/alternate vintage. Use cols 0-41 only. Market names have `(USA)` suffix. |
| `Supply Forward` | Inventory units | units | |
| `Forward UPP` | Units per person (inventory) | units | First ~150 rows are inventory, there may be additional blocks for population and UPP ratio below. 762 total rows = likely 5 blocks. |
| `Income Growth` | Household income | $/year | Market names have `USA` suffix. |
| `Population Growth Forward` | Population level | persons | Has extra cols like Effective Rent: Property Class Name, Slice, As Of, Geography Name, Concept Name. Time cols start at col index 5. Market names have `USA` suffix. |
| `Forward Sale Price` | Sale price per unit | $/unit | Market names have `(USA)` suffix. |

#### Historical Quarterly Series
| Sheet | Variable | Time Range | Notes |
|-------|----------|------------|-------|
| `Supply Historical` | Inventory units | 2020 Q2 → 2025 Q1 (20 quarters) | Has Property Class Name, Slice, As Of, Geography Name, Concept Name cols. 3 blocks. Use Block 1. Market names have `USA` suffix. |
| `Historical Sale Price` | Sale price per unit | 2015 Q1 → 2025 Q1 (41 quarters) | 3 blocks. Market names have `(USA)` suffix. |
| `UPP Historical` | Combined sheet with 3 separate variable sections stacked: (1) Inventory units, (2) Population, (3) Units Per Person ratio | 2015 Q2 → 2035 Q2 (this sheet spans BOTH historical and forward!) | Header row is row index 2. Block 1 (Inventory): rows 3-152. Block 2 (Population): rows ~157-306. Block 3 (UPP ratio): rows ~311-460. 83 columns covering 2015-2035. |

#### Historical Summary Only (NOT quarterly series — just 5yr and 10yr growth multipliers)
| Sheet | Variable | Format |
|-------|----------|--------|
| `Effective Rent Historical` | 5yr growth multiplier + rank, 10yr growth multiplier + rank | Row 1 is header. Market in col 0 (5yr) and col 5 (10yr). Growth in col 1 and col 6. |
| `Historical Employment` | 5yr and 10yr growth multiplier + rank | Row 2 is header. Market in col 1 (5yr) and col 5 (10yr). Growth in col 2 and col 6. |
| `Historical Population Growth` | 5yr and 10yr growth multiplier + rank | Row 1 is header. Market in col 1 (5yr) and col 6 (10yr). Growth in col 2 and col 7. |

#### Summary Sheet
Pre-computed ranking of all ~150 markets. Each market ranked 1-150 on each variable at Forward 1/3/5/10 year horizons, plus historical 5yr and 10yr for some variables. A weighted average rank is computed with weights: Effective Rent 0.2, Employment 0.1, Supply weight implied ~0.1, UPP 0.2, Income 0.1, Population 0.1, Sale Price 0.2. Total = 1.0.

The right side of the summary sheet contains a pre-sorted ranking table (Market, Weighted Avg, Rank).

---

## Analysis Plan

### SETUP: Data Ingestion & Cleaning (`src/data_loader.py`)

Build a single data loading module that:

1. Reads all sheets and extracts Block 1 (raw levels) for every quarterly series
2. Normalizes all market names to a consistent format (strip ` USA`, ` (USA)`, trim whitespace)
3. Handles the non-standard sheet structures:
   - Sheets with Property Class/Slice/As Of/Geography Name/Concept Name prefix columns (Effective Rent Forward, Supply Historical, Population Growth Forward): skip to the time series columns
   - Forward Employment: use only columns 0-41, ignore the duplicate block starting at column 42
   - UPP Historical: parse three separate variable sections (Inventory rows 3-152, Population rows ~157-306, UPP ratio rows ~311-460)
4. Computes quarterly growth rates (% change quarter-over-quarter) from all level series
5. Computes annualized growth rates (year-over-year % change, i.e., Q vs same Q prior year) where 4+ quarters of data exist
6. Outputs a single merged panel DataFrame: rows = (market, quarter), columns = all variables in both levels and growth rates
7. Also outputs a cross-sectional summary DataFrame: one row per market, columns = 5yr growth, 10yr growth for each variable (from the historical summary sheets), plus computed forward growth multipliers at 1/3/5/10yr horizons

Validate: final panel should have ~150 markets. Print market count and date range per variable to confirm alignment.

---

### ANALYSIS 1: Cross-Sectional Historical Attribution (`src/analysis_1_attribution.py`)

**Purpose:** Test whether supply is the dominant driver of historical rent growth (the Harvard study claim), and quantify which factors mattered most.

**Data used:** Cross-sectional summary — one row per market, using the historical summary growth multipliers.

**Dependent variable:** 10-year effective rent growth (multiplier from `Effective Rent Historical`)

**Independent variables:**
- 10-year employment growth (from `Historical Employment`)
- 10-year population growth (from `Historical Population Growth`)
- 10-year supply growth — compute from `Supply Historical` or `UPP Historical` inventory block (use the ratio of last quarter to first quarter available)
- 10-year sale price growth (from `Historical Sale Price` — last quarter / first quarter)

**Steps:**
1. Merge all historical growth variables into a single cross-section (N ≈ 150 markets)
2. Compute correlation matrix of all independent variables. Print it. Flag any pairs with |r| > 0.7
3. Compute VIF for each independent variable. Print. Flag any VIF > 5
4. Run OLS regression: rent_growth ~ supply_growth + employment_growth + population_growth + sale_price_growth
5. Use heteroskedasticity-robust standard errors (HC3)
6. Report: coefficients, robust standard errors, t-stats, p-values, R²
7. Run standardized coefficient version (z-score all variables first) so we can compare magnitudes directly — which variable has the largest standardized effect?
8. If multicollinearity is severe (VIF > 5 for any variable):
   a. Run Lasso with cross-validation (`LassoCV`) to identify which variables survive regularization
   b. Report which variables Lasso retains and their coefficient paths
9. Save all regression output to `outputs/analysis_1_results.txt`
10. Generate a scatter plot matrix (pairplot) of rent growth vs each independent variable, colored by region (derive region from state abbreviation in market name). Save to `outputs/analysis_1_scatterplots.png`

**Key question to answer:** Does supply growth have the largest (negative) standardized coefficient? If yes, the Harvard finding holds. If not, what dominates?

---

### ANALYSIS 2: Forward Composite Score with Empirical Weights (`src/analysis_2_forward_score.py`)

**Purpose:** Re-rank the top 30-40 markets using empirically derived weights from Analysis 1, instead of the arbitrary weights in the Summary Sheet.

**Data used:** Forward quarterly series (all sheets), plus coefficients from Analysis 1.

**Steps:**
1. For each market, compute forward growth rates at 1-year, 3-year, 5-year, and 10-year horizons for:
   - Effective rent (from `Effective Rent-Forward`)
   - Supply / inventory (from `Supply Forward`)
   - Employment (from `Forward Employment`)
   - Population (from `Population Growth Forward`)
   - Income (from `Income Growth`)
   - Sale price (from `Forward Sale Price`)
   
   Growth rate = (value at horizon quarter / value at first quarter) - 1

2. For each horizon (1/3/5/10yr), rank markets 1-150 on each variable
   - For supply growth: INVERT the ranking — markets with LOWEST supply growth get the best (lowest) rank, since supply growth hurts rents
   
3. Compute a weighted average rank using the STANDARDIZED COEFFICIENTS from Analysis 1 as weights:
   - Normalize the absolute values of the standardized coefficients to sum to 1
   - These are your empirical weights
   - Apply them to produce a composite score per market per horizon

4. Compare your empirically-weighted ranking to the Summary Sheet's ranking:
   - Merge the two rankings
   - Compute Spearman rank correlation between your ranking and theirs at each horizon
   - Identify markets where your ranking differs by 10+ positions — these are the "edge" markets where the arbitrary weights mislead

5. Produce output table: `outputs/analysis_2_market_rankings.csv`
   Columns: Market, Empirical_Rank_1yr, Empirical_Rank_3yr, Empirical_Rank_5yr, Empirical_Rank_10yr, Summary_Sheet_Rank, Rank_Difference_5yr

6. Produce a second table: `outputs/analysis_2_top30_markets.csv`
   Top 30 markets by 5-year empirical rank, with all component ranks and growth rates

---

### ANALYSIS 3: Supply Absorption Differential (`src/analysis_3_absorption.py`)

**Purpose:** Identify which markets are adding supply fastest but still tightening on a per-capita basis — the absorption story. This is the core of Michael's thesis.

**Data used:** 
- `Supply Forward` (inventory levels)
- `Forward UPP` or `UPP Historical` (which contains forward data too — units per person)
- `Population Growth Forward` (population levels)

**Steps:**
1. For each market, compute:
   - Forward supply growth rate (1yr, 3yr, 5yr, 10yr): % change in inventory units
   - Forward UPP change (1yr, 3yr, 5yr, 10yr): change in units-per-person ratio
   - Forward population growth rate (same horizons)
   - Implied absorption rate: if supply is growing at X% but UPP is flat or falling, population growth is absorbing the new units. Compute: `absorption_pressure = population_growth_rate - supply_growth_rate`. Positive means demand is outpacing supply.

2. Create a 2x2 classification at the 5-year horizon:
   - **Quadrant 1 (Best):** High supply growth + UPP falling (market is absorbing fast) — these are the targets
   - **Quadrant 2:** Low supply growth + UPP falling (naturally tightening, but may lack assets to buy)
   - **Quadrant 3:** Low supply growth + UPP rising (stagnant market)
   - **Quadrant 4 (Worst):** High supply growth + UPP rising (oversupply risk)
   
   Use median supply growth and median UPP change as the cutoffs.

3. Generate scatter plot: x-axis = 5yr supply growth rate, y-axis = 5yr UPP change. Color by quadrant. Label the top 30 markets from Analysis 2. Save to `outputs/analysis_3_absorption_scatter.png`

4. Save classification table: `outputs/analysis_3_absorption_quadrants.csv`
   Columns: Market, Supply_Growth_5yr, UPP_Change_5yr, Pop_Growth_5yr, Absorption_Pressure, Quadrant, Empirical_Rank_5yr (from Analysis 2)

---

### ANALYSIS 4: Summary Sheet Weight Audit (`src/analysis_4_weight_audit.py`)

**Purpose:** Show that the Summary Sheet's arbitrary weights (0.2/0.1/0.1/0.2/0.1/0.1/0.2) are not empirically justified, and quantify how much the ranking changes with correct weights.

**Steps:**
1. Extract the Summary Sheet rankings and the stated weights
2. Recompute the weighted average using the empirical weights from Analysis 1
3. For each market, compute:
   - Original weighted rank (from Summary Sheet)
   - Empirically-weighted rank
   - Difference
4. Identify the 10 markets that IMPROVE the most under empirical weights (these are markets the current methodology underrates)
5. Identify the 10 markets that DECLINE the most (these are markets the current methodology overrates)
6. Save: `outputs/analysis_4_weight_comparison.csv`

---

### ANALYSIS 5: Forward Rent Growth Trajectory Analysis (`src/analysis_5_trajectories.py`)

**Purpose:** Identify markets where short-term and long-term rent growth forecasts diverge — these are the "get in before the curve" opportunities.

**Data used:** Forward effective rent series (quarterly, 10 years)

**Steps:**
1. For each market, compute:
   - 1-year forward rent growth rate
   - 3-year forward rent growth rate (annualized)
   - 5-year forward rent growth rate (annualized)
   - 10-year forward rent growth rate (annualized)

2. Compute `trajectory_score = rank_10yr - rank_1yr`
   - A large NEGATIVE trajectory score means the market ranks much better long-term than short-term → "buy now before it shows up"
   - A large POSITIVE score means short-term outperformance that fades → "already priced in"

3. Plot: x-axis = 1yr rank, y-axis = 10yr rank. Diagonal line = same rank. Markets below the diagonal are improving over time. Label outliers. Save to `outputs/analysis_5_trajectory_scatter.png`

4. Also plot the actual rent growth time series (quarterly levels, indexed to 100 at 2025 Q2) for the top 10 trajectory markets — show their growth curves diverging from the pack over time. Save to `outputs/analysis_5_growth_curves.png`

5. Save: `outputs/analysis_5_trajectories.csv`
   Columns: Market, Rank_1yr, Rank_3yr, Rank_5yr, Rank_10yr, Trajectory_Score, Rent_Growth_1yr, Rent_Growth_5yr_Ann, Rent_Growth_10yr_Ann

---

### ANALYSIS 6: COVID Distortion Flags (`src/analysis_6_covid.py`)

**Purpose:** Identify which markets had the largest COVID-era dislocations in sale prices and supply, so we know where historical data will be misleading when we build the full panel model later.

**Data used:**
- `Historical Sale Price` (2015 Q1 → 2025 Q1)
- `Supply Historical` (2020 Q2 → 2025 Q1)
- `UPP Historical` inventory block (2015 Q2 → present)

**Steps:**
1. For sale prices:
   - Compute the pre-COVID trend (2015 Q1 → 2020 Q1) annualized growth rate per market
   - Compute COVID-period growth (2020 Q1 → 2022 Q1)
   - Compute post-COVID growth (2022 Q1 → 2025 Q1)
   - Flag markets where COVID-period growth deviated from pre-COVID trend by more than 2x (either direction)

2. For supply:
   - Supply historical only goes back to 2020 Q2, so we can't compare pre-COVID
   - Instead compute: growth rate 2020 Q2 → 2022 Q2 vs 2022 Q2 → 2025 Q1
   - Flag markets where the growth rate shifted dramatically between periods

3. Save: `outputs/analysis_6_covid_flags.csv`
   Columns: Market, PreCOVID_SalePrice_AnnGrowth, COVID_SalePrice_AnnGrowth, PostCOVID_SalePrice_AnnGrowth, COVID_Deviation_Flag, Supply_Early_Growth, Supply_Late_Growth, Supply_Shift_Flag

---

### SYNTHESIS: Final Market Selection Report (`src/synthesis.py`)

**Purpose:** Combine all analyses into a single investor-facing output.

**Steps:**
1. Load outputs from Analyses 1-6
2. Create a master table with one row per market and columns from all analyses:
   - Empirical composite rank (from Analysis 2) at 5yr and 10yr horizons
   - Absorption quadrant (from Analysis 3)
   - Trajectory score (from Analysis 5)
   - COVID distortion flags (from Analysis 6)
3. Apply filters to get the final target list:
   - Must be in top 40 by empirical composite rank (5yr)
   - Must be in Quadrant 1 or 2 for absorption (not oversupplied)
   - COVID distortion flag is informational, not exclusionary
4. Rank the surviving markets by a combined score: 0.6 * empirical_rank_5yr + 0.2 * absorption_pressure_rank + 0.2 * trajectory_score_rank
5. Save final ranked list: `outputs/final_target_markets.csv`
6. Save full master table: `outputs/master_market_table.csv`

---

## Technical Requirements

- Python 3.10+
- Dependencies: pandas, numpy, scikit-learn, statsmodels, matplotlib, seaborn, openpyxl
- All outputs go to `outputs/` directory
- Each analysis script should be independently runnable
- Include a `main.py` that runs all analyses in sequence
- Print clear progress messages and key findings to stdout as each analysis runs
- Handle missing data gracefully — if a market is missing from one sheet, exclude it from that analysis but keep it in others
- Use `random_state=42` for any stochastic methods (Lasso CV, etc.)

## What This Analysis Does NOT Cover (Waiting on Additional Data)

These require data we don't have yet. Do NOT attempt them:
- Full panel regression or Bayesian hierarchical model (need historical quarterly rent/employment/population series)
- High-income renter migration analysis (need Bloomberg/Census income distribution by zip)
- Zip code level analysis (Phase 2, no data yet)
- Construction pipeline / permitted-but-not-delivered units (need separate data source)
- Net absorption data (need CoStar absorption series)
