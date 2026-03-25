"""
Risk Management Pipeline

Main pipeline script that:
1. Loads SDTM data from ../data/
2. Calculates QTL metrics via calc_qtl.py
3. Calculates KRI metrics via calc_kri.py
4. Combines results into risk_summary.csv saved to ../data/
5. Prints summary statistics

Usage:
    cd python && python pipeline.py
    -- or --
    python /path/to/pipeline.py
"""

import os
import sys

import pandas as pd

# Allow running from any directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
sys.path.insert(0, SCRIPT_DIR)

from calc_qtl import calc_all_qtl
from calc_kri import calc_all_kri


def load_sdtm_data(data_dir: str) -> dict[str, pd.DataFrame]:
    """
    Load all SDTM CSV files from the data directory.

    Parameters
    ----------
    data_dir : str
        Path to the directory containing dm.csv, ds.csv, dv.csv, ae.csv.

    Returns
    -------
    dict with keys 'dm', 'ds', 'dv', 'ae' mapping to DataFrames.
    """
    datasets = {}
    file_map = {
        "dm": "dm.csv",
        "ds": "ds.csv",
        "dv": "dv.csv",
        "ae": "ae.csv",
    }

    for key, filename in file_map.items():
        filepath = os.path.join(data_dir, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"Required SDTM file not found: {filepath}\n"
                "Run generate_sdtm.py first to create the data files."
            )
        datasets[key] = pd.read_csv(filepath)
        print(f"  Loaded {filename}: {len(datasets[key])} rows")

    return datasets


def run_pipeline() -> pd.DataFrame:
    """
    Execute the full risk management calculation pipeline.

    Returns
    -------
    pd.DataFrame: Combined risk summary with all QTL and KRI results.
    """
    print("=" * 60)
    print("  Clinical Trial Risk Management Pipeline")
    print("=" * 60)

    # Step 1: Load SDTM data
    print("\n[Step 1] Loading SDTM data...")
    data = load_sdtm_data(DATA_DIR)
    dm = data["dm"]
    ds = data["ds"]
    dv = data["dv"]
    ae = data["ae"]

    print(f"\n  Study: {dm['STUDYID'].iloc[0]}")
    print(f"  Sites: {dm['SITEID'].nunique()}")
    print(f"  Total subjects enrolled: {dm['SUBJID'].nunique()}")

    # Step 2: Calculate QTL metrics
    print("\n[Step 2] Calculating QTL metrics...")
    qtl_results = calc_all_qtl(dm, ds, dv)
    n_qtl_red = (qtl_results["status"] == "Red").sum()
    n_qtl_yellow = (qtl_results["status"] == "Yellow").sum()
    print(f"  QTL records: {len(qtl_results)}")
    print(f"  Red alerts: {n_qtl_red}  |  Yellow alerts: {n_qtl_yellow}")

    # Step 3: Calculate KRI metrics
    print("\n[Step 3] Calculating KRI metrics...")
    kri_results = calc_all_kri(dm, ae)
    n_kri_red = (kri_results["status"] == "Red").sum()
    n_kri_yellow = (kri_results["status"] == "Yellow").sum()
    print(f"  KRI records: {len(kri_results)}")
    print(f"  Red alerts: {n_kri_red}  |  Yellow alerts: {n_kri_yellow}")

    # Step 4: Combine results
    print("\n[Step 4] Combining QTL and KRI results...")
    risk_summary = pd.concat([qtl_results, kri_results], ignore_index=True)
    risk_summary["snapshot_date"] = pd.Timestamp.today().strftime("%Y-%m-%d")

    # Step 5: Save to CSV
    output_path = os.path.join(DATA_DIR, "risk_summary.csv")
    risk_summary.to_csv(output_path, index=False)
    print(f"  Saved risk_summary.csv: {len(risk_summary)} records")
    print(f"  Output: {output_path}")

    # Step 6: Print summary statistics
    print_summary(risk_summary)

    return risk_summary


def print_summary(risk_summary: pd.DataFrame) -> None:
    """Print a formatted summary of risk metrics."""
    print("\n" + "=" * 60)
    print("  RISK SUMMARY STATISTICS")
    print("=" * 60)

    total_sites = risk_summary["SITEID"].nunique()
    total_indicators = risk_summary["indicator_id"].nunique()

    sites_red = risk_summary[risk_summary["status"] == "Red"]["SITEID"].nunique()
    sites_yellow = risk_summary[risk_summary["status"] == "Yellow"]["SITEID"].nunique()
    sites_green = total_sites - sites_red - (
        risk_summary[
            (risk_summary["status"] == "Yellow") & ~risk_summary["SITEID"].isin(
                risk_summary[risk_summary["status"] == "Red"]["SITEID"]
            )
        ]["SITEID"].nunique()
    )

    print(f"\n  Total Sites:       {total_sites}")
    print(f"  Total Indicators:  {total_indicators}")
    print(f"  Sites w/ Red:      {sites_red}")
    print(f"  Sites w/ Yellow:   {sites_yellow}")

    print("\n  --- Status Breakdown by Indicator ---")
    status_pivot = risk_summary.groupby(["indicator_id", "indicator_name", "status"]).size().unstack(
        fill_value=0
    ).reset_index()

    for col in ["Red", "Yellow", "Green"]:
        if col not in status_pivot.columns:
            status_pivot[col] = 0

    status_pivot = status_pivot[["indicator_id", "indicator_name", "Red", "Yellow", "Green"]]
    print(status_pivot.to_string(index=False))

    print("\n  --- Site Risk Overview ---")
    site_risk = risk_summary.groupby("SITEID").agg(
        n_red=("status", lambda x: (x == "Red").sum()),
        n_yellow=("status", lambda x: (x == "Yellow").sum()),
        n_green=("status", lambda x: (x == "Green").sum()),
    ).reset_index()

    site_risk["overall_risk"] = site_risk.apply(
        lambda r: "Red" if r["n_red"] > 0 else ("Yellow" if r["n_yellow"] > 0 else "Green"),
        axis=1,
    )

    print(site_risk.to_string(index=False))
    print("\n" + "=" * 60)


if __name__ == "__main__":
    # Check if SDTM data exists; if not, generate it first
    dm_path = os.path.join(DATA_DIR, "dm.csv")
    if not os.path.exists(dm_path):
        print("SDTM data not found. Generating dummy data first...\n")
        import generate_sdtm
        generate_sdtm.main()
        print()

    run_pipeline()
