"""
Analysis 1: Cross-Sectional Historical Attribution
Test whether supply is the dominant driver of historical rent growth.
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

OUTPUTS = Path(__file__).parent.parent / "outputs"
OUTPUTS.mkdir(exist_ok=True)


def run_analysis_1():
    print("\n=== ANALYSIS 1: Historical Attribution ===")
    _, cs, _, _ = load_all()

    reg_data = pd.DataFrame({
        "rent_growth":       cs["eff_rent_10yr"],
        "supply_growth":     cs["supply_hist_growth"],
        "employment_growth": cs["emp_10yr"],
        "pop_growth":        cs["pop_10yr"],
        "sale_price_growth": cs["sale_price_hist_growth"],
    }).dropna()

    print(f"\nRegression sample: {len(reg_data)} markets")
    print(reg_data.describe().to_string())

    # --- Correlation matrix ---
    print("\n--- Correlation Matrix ---")
    corr = reg_data.corr()
    print(corr.to_string())
    high_corr = []
    for i in range(len(corr.columns)):
        for j in range(i + 1, len(corr.columns)):
            r = corr.iloc[i, j]
            if abs(r) > 0.7:
                high_corr.append((corr.columns[i], corr.columns[j], r))
    if high_corr:
        print("\nHigh collinearity pairs (|r| > 0.7):")
        for a, b, r in high_corr:
            print(f"  {a} vs {b}: r={r:.3f}")
    else:
        print("\nNo pairs with |r| > 0.7")

    # --- VIF ---
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    import statsmodels.api as sm

    X_vif = reg_data.drop(columns="rent_growth")
    X_vif_c = X_vif.copy()
    X_vif_c.insert(0, "const", 1.0)
    vif_data = pd.DataFrame({
        "variable": X_vif.columns,
        "VIF": [variance_inflation_factor(X_vif_c.values, i + 1)
                for i in range(len(X_vif.columns))]
    })
    print("\n--- VIF ---")
    print(vif_data.to_string(index=False))
    high_vif = vif_data[vif_data["VIF"] > 5]

    # --- OLS HC3 ---
    y = reg_data["rent_growth"]
    X = sm.add_constant(reg_data.drop(columns="rent_growth"))
    model = sm.OLS(y, X).fit(cov_type="HC3")
    print("\n--- OLS (HC3) ---")
    print(model.summary().as_text())

    # --- Standardised ---
    reg_std = (reg_data - reg_data.mean()) / reg_data.std()
    y_std = reg_std["rent_growth"]
    X_std = sm.add_constant(reg_std.drop(columns="rent_growth"))
    model_std = sm.OLS(y_std, X_std).fit(cov_type="HC3")
    std_coefs = model_std.params.drop("const")
    std_tvals = model_std.tvalues.drop("const")
    std_pvals = model_std.pvalues.drop("const")
    coef_table = pd.DataFrame({
        "Std_Coef": std_coefs,
        "t_stat":   std_tvals,
        "p_value":  std_pvals,
        "abs_coef": std_coefs.abs(),
    }).sort_values("abs_coef", ascending=False)
    print("\n--- Standardised Coefficients ---")
    print(coef_table.drop(columns="abs_coef").to_string())
    dominant = coef_table.index[0]
    print(f"\nDominant driver: {dominant}")

    # --- LassoCV if VIF > 5 ---
    lasso_coefs = None
    if not high_vif.empty:
        print("\n--- LassoCV ---")
        from sklearn.linear_model import LassoCV
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X_sc = scaler.fit_transform(reg_data.drop(columns="rent_growth"))
        y_sc = (y - y.mean()) / y.std()
        lasso = LassoCV(cv=5, random_state=42, max_iter=10000)
        lasso.fit(X_sc, y_sc)
        lasso_coefs = pd.Series(lasso.coef_,
                                index=reg_data.drop(columns="rent_growth").columns)
        print(f"  Best alpha: {lasso.alpha_:.4f}")
        print(lasso_coefs.to_string())

    # --- Save results ---
    out_path = OUTPUTS / "analysis_1_results.txt"
    with open(out_path, "w") as f:
        f.write("=== ANALYSIS 1: HISTORICAL RENT GROWTH ATTRIBUTION ===\n\n")
        f.write(f"Regression sample: {len(reg_data)} markets\n\n")
        f.write("--- Descriptive Statistics ---\n")
        f.write(reg_data.describe().to_string() + "\n\n")
        f.write("--- Correlation Matrix ---\n")
        f.write(corr.to_string() + "\n\n")
        if high_corr:
            f.write("High collinearity pairs (|r| > 0.7):\n")
            for a, b, r in high_corr:
                f.write(f"  {a} vs {b}: r={r:.3f}\n")
            f.write("\n")
        f.write("--- VIF ---\n")
        f.write(vif_data.to_string(index=False) + "\n\n")
        f.write("--- OLS Regression (HC3) ---\n")
        f.write(model.summary().as_text() + "\n\n")
        f.write("--- Standardised Coefficients ---\n")
        f.write(coef_table.drop(columns="abs_coef").to_string() + "\n\n")
        f.write(f"Dominant driver: {dominant}\n")
        if lasso_coefs is not None:
            f.write("\n--- LassoCV Coefficients ---\n")
            f.write(lasso_coefs.to_string() + "\n")
    print(f"Results saved -> {out_path}")

    # --- Scatter plots ---
    def get_region(market):
        state = market.split(" - ")[-1].split()[0] if " - " in market else "XX"
        west  = {"CA","OR","WA","NV","AZ","UT","CO","ID","MT","WY","NM","HI","AK"}
        south = {"TX","FL","GA","NC","SC","VA","AL","MS","TN","KY","LA","AR","OK","WV","MD","DE","DC"}
        mwest = {"IL","OH","MI","IN","WI","MN","IA","MO","ND","SD","NE","KS"}
        ne    = {"NY","PA","NJ","CT","MA","RI","NH","VT","ME"}
        if state in west:  return "West"
        if state in south: return "South"
        if state in mwest: return "Midwest"
        if state in ne:    return "Northeast"
        return "Other"

    plot_data = reg_data.copy()
    plot_data["Region"] = plot_data.index.map(get_region)
    indep_vars = ["supply_growth", "employment_growth", "pop_growth", "sale_price_growth"]
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()
    region_colors = {"West":"#e74c3c","South":"#2ecc71","Midwest":"#3498db",
                     "Northeast":"#f39c12","Other":"#95a5a6"}
    for i, var in enumerate(indep_vars):
        ax = axes[i]
        for region, grp in plot_data.groupby("Region"):
            ax.scatter(grp[var], grp["rent_growth"], label=region,
                       color=region_colors.get(region,"gray"), alpha=0.7, s=40)
        m_, b_ = np.polyfit(plot_data[var].values, plot_data["rent_growth"].values, 1)
        xl = np.linspace(plot_data[var].min(), plot_data[var].max(), 100)
        ax.plot(xl, m_*xl + b_, "k--", linewidth=1, alpha=0.6)
        coef = model.params.get(var, np.nan)
        pval = model.pvalues.get(var, np.nan)
        ax.set_xlabel(var.replace("_"," ").title(), fontsize=10)
        ax.set_ylabel("10yr Rent Growth", fontsize=10)
        ax.set_title(f"{var.replace('_',' ').title()}\ncoef={coef:.3f} p={pval:.3f}", fontsize=10)
        if i == 0:
            ax.legend(fontsize=8)
    plt.suptitle("Historical Rent Growth vs Drivers (by Region)", fontsize=13, fontweight="bold")
    plt.tight_layout()
    scatter_path = OUTPUTS / "analysis_1_scatterplots.png"
    plt.savefig(scatter_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Scatter plot saved -> {scatter_path}")

    return coef_table.drop(columns="abs_coef")


if __name__ == "__main__":
    run_analysis_1()
