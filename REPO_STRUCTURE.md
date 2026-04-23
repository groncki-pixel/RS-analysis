# Repo Structure

```
re-market-model/
├── README.md                          # Project overview, how to run
├── ANALYSIS_INSTRUCTIONS.md           # The full analysis spec (this doc)
├── requirements.txt                   # pandas, numpy, scikit-learn, statsmodels, matplotlib, seaborn, openpyxl
├── main.py                            # Runs all analyses in sequence
├── data/
│   └── Full_Market_Leveler.xlsx       # Raw CoStar export — never modify this file
├── src/
│   ├── __init__.py
│   ├── data_loader.py                 # All data ingestion, cleaning, normalization
│   ├── analysis_1_attribution.py      # Historical rent growth attribution
│   ├── analysis_2_forward_score.py    # Forward composite ranking
│   ├── analysis_3_absorption.py       # Supply absorption differential
│   ├── analysis_4_weight_audit.py     # Summary Sheet weight audit
│   ├── analysis_5_trajectories.py     # Rent growth trajectory divergence
│   ├── analysis_6_covid.py            # COVID distortion flags
│   └── synthesis.py                   # Combine all into final market selection
└── outputs/                           # All generated files go here
    ├── .gitkeep
    ├── analysis_1_results.txt
    ├── analysis_1_scatterplots.png
    ├── analysis_2_market_rankings.csv
    ├── analysis_2_top30_markets.csv
    ├── analysis_3_absorption_scatter.png
    ├── analysis_3_absorption_quadrants.csv
    ├── analysis_4_weight_comparison.csv
    ├── analysis_5_trajectory_scatter.png
    ├── analysis_5_growth_curves.png
    ├── analysis_5_trajectories.csv
    ├── analysis_6_covid_flags.csv
    ├── final_target_markets.csv
    └── master_market_table.csv
```

## Key rules
- `data/` holds raw inputs only. Never write to it.
- `outputs/` holds all generated files. Gitignore the CSVs and PNGs if you want, but keep `.gitkeep`.
- Every script in `src/` should be runnable standalone (`python -m src.analysis_1_attribution`) but `main.py` runs them all in order.
- `data_loader.py` is imported by every analysis script. It should expose clean DataFrames, not require each script to re-parse Excel.
