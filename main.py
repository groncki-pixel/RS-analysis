"""
main.py — Run all analyses in sequence.
"""

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).parent))


def main():
    print("=" * 60)
    print("REAL ESTATE MARKET SELECTION MODEL")
    print("=" * 60)

    # Analysis 1: Historical attribution
    from src.analysis_1_attribution import run_analysis_1
    coef_table = run_analysis_1()

    # Analysis 2: Forward composite score
    from src.analysis_2_forward_score import run_analysis_2
    rank_dfs, growth_df = run_analysis_2(coef_table)

    # Analysis 3: Absorption differential
    from src.analysis_3_absorption import run_analysis_3
    absorption_df = run_analysis_3(rank_dfs, growth_df)

    # Analysis 4: Weight audit
    from src.analysis_4_weight_audit import run_analysis_4
    weight_comparison = run_analysis_4(coef_table)

    # Analysis 5: Trajectory analysis
    from src.analysis_5_trajectories import run_analysis_5
    traj_df = run_analysis_5()

    # Analysis 6: COVID flags
    from src.analysis_6_covid import run_analysis_6
    covid_df = run_analysis_6()

    # Synthesis
    from src.synthesis import run_synthesis
    final, master = run_synthesis()

    # --- Summary ---
    print("\n" + "=" * 60)
    print("ALL ANALYSES COMPLETE")
    print("=" * 60)

    outputs_dir = Path(__file__).parent / "outputs"
    output_files = list(outputs_dir.glob("*"))
    output_files = [f for f in output_files if not f.name.startswith(".")]
    print(f"\nOutput files ({len(output_files)}):")
    for f in sorted(output_files):
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name:<45} {size_kb:6.1f} KB")

    print("\n--- TOP 15 FINAL TARGET MARKETS ---")
    if final is not None:
        top15 = final.head(15)
        print(top15[["Final_Rank", "Empirical_Rank_5yr", "Quadrant",
                      "Trajectory_Score", "Rent_Growth_5yr_Ann"]].to_string())
    else:
        print("No final markets computed.")


if __name__ == "__main__":
    main()
