"""
QTL (Quality Tolerance Limit) calculation module.

Calculates site-level QTL metrics from SDTM datasets:
    QTL01 - Protocol Deviation Rate
    QTL02 - Early Discontinuation Rate
    QTL03 - Missing Primary Endpoint Rate
"""

import numpy as np
import pandas as pd

# QTL threshold definitions (mirrored from config/indicators.yaml)
QTL_DEFINITIONS = {
    "QTL01": {
        "indicator_id": "QTL01",
        "indicator_name": "Protocol Deviation Rate",
        "category": "Compliance",
        "description": "Percentage of subjects with at least one protocol deviation",
        "justification": "High deviation rate indicates site non-compliance and data quality risk",
        "unit": "%",
        "threshold_yellow": 5.0,
        "threshold_red": 10.0,
        "direction": "higher_is_worse",
    },
    "QTL02": {
        "indicator_id": "QTL02",
        "indicator_name": "Early Discontinuation Rate",
        "category": "Retention",
        "description": "Percentage of subjects who discontinued before study completion",
        "justification": "High dropout rate may introduce bias and compromise study integrity",
        "unit": "%",
        "threshold_yellow": 15.0,
        "threshold_red": 25.0,
        "direction": "higher_is_worse",
    },
    "QTL03": {
        "indicator_id": "QTL03",
        "indicator_name": "Missing Primary Endpoint Rate",
        "category": "Data Quality",
        "description": "Percentage of subjects with missing primary endpoint data",
        "justification": "Missing data may affect statistical analysis validity",
        "unit": "%",
        "threshold_yellow": 5.0,
        "threshold_red": 10.0,
        "direction": "higher_is_worse",
    },
}


def _determine_status(
    value: float,
    threshold_yellow: float,
    threshold_red: float,
    direction: str = "higher_is_worse",
) -> str:
    """
    Determine traffic-light status for an indicator value.

    Parameters
    ----------
    value : float
        Calculated metric value.
    threshold_yellow : float
        Yellow alert threshold.
    threshold_red : float
        Red alert threshold.
    direction : str
        "higher_is_worse" (default) - higher values are bad.
        "lower_is_worse"            - lower values are bad.

    Returns
    -------
    str: "Green", "Yellow", or "Red"
    """
    if direction == "lower_is_worse":
        if value < threshold_red:
            return "Red"
        elif value < threshold_yellow:
            return "Yellow"
        else:
            return "Green"
    else:  # higher_is_worse
        if value > threshold_red:
            return "Red"
        elif value > threshold_yellow:
            return "Yellow"
        else:
            return "Green"


def calc_qtl01(dm: pd.DataFrame, dv: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate QTL01: Protocol Deviation Rate per site.

    Formula: n_subjects_with_dv / n_enrolled * 100

    Parameters
    ----------
    dm : pd.DataFrame
        DM dataset with columns SITEID, SUBJID.
    dv : pd.DataFrame
        DV dataset with columns SITEID, SUBJID.

    Returns
    -------
    pd.DataFrame with columns: SITEID, value, n_numerator, n_denominator, status
    """
    defn = QTL_DEFINITIONS["QTL01"]

    n_enrolled = dm.groupby("SITEID")["SUBJID"].nunique().reset_index(name="n_enrolled")

    if len(dv) > 0:
        n_with_dv = dv.groupby("SITEID")["SUBJID"].nunique().reset_index(name="n_with_dv")
    else:
        n_with_dv = pd.DataFrame(columns=["SITEID", "n_with_dv"])

    result = n_enrolled.merge(n_with_dv, on="SITEID", how="left")
    result["n_with_dv"] = result["n_with_dv"].fillna(0).astype(int)
    result["value"] = (result["n_with_dv"] / result["n_enrolled"] * 100).round(2)
    result["n_numerator"] = result["n_with_dv"]
    result["n_denominator"] = result["n_enrolled"]
    result["status"] = result["value"].apply(
        lambda v: _determine_status(v, defn["threshold_yellow"], defn["threshold_red"], defn["direction"])
    )

    for key in ["indicator_id", "indicator_name", "category", "threshold_yellow", "threshold_red"]:
        result[key] = defn[key]

    return result[["SITEID", "indicator_id", "indicator_name", "category", "value",
                   "threshold_yellow", "threshold_red", "status", "n_numerator", "n_denominator"]]


def calc_qtl02(dm: pd.DataFrame, ds: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate QTL02: Early Discontinuation Rate per site.

    Formula: n_discontinued / n_enrolled * 100

    Parameters
    ----------
    dm : pd.DataFrame
        DM dataset with columns SITEID, SUBJID.
    ds : pd.DataFrame
        DS dataset with columns SITEID, SUBJID, DSDECOD.

    Returns
    -------
    pd.DataFrame with columns: SITEID, value, n_numerator, n_denominator, status
    """
    defn = QTL_DEFINITIONS["QTL02"]

    n_enrolled = dm.groupby("SITEID")["SUBJID"].nunique().reset_index(name="n_enrolled")

    discontinued = ds[ds["DSDECOD"] == "DISCONTINUED"]
    n_disc = discontinued.groupby("SITEID")["SUBJID"].nunique().reset_index(name="n_discontinued")

    result = n_enrolled.merge(n_disc, on="SITEID", how="left")
    result["n_discontinued"] = result["n_discontinued"].fillna(0).astype(int)
    result["value"] = (result["n_discontinued"] / result["n_enrolled"] * 100).round(2)
    result["n_numerator"] = result["n_discontinued"]
    result["n_denominator"] = result["n_enrolled"]
    result["status"] = result["value"].apply(
        lambda v: _determine_status(v, defn["threshold_yellow"], defn["threshold_red"], defn["direction"])
    )

    for key in ["indicator_id", "indicator_name", "category", "threshold_yellow", "threshold_red"]:
        result[key] = defn[key]

    return result[["SITEID", "indicator_id", "indicator_name", "category", "value",
                   "threshold_yellow", "threshold_red", "status", "n_numerator", "n_denominator"]]


def calc_qtl03(dm: pd.DataFrame, random_seed: int = 42) -> pd.DataFrame:
    """
    Calculate QTL03: Missing Primary Endpoint Rate per site.

    Formula: n_missing_endpoint / n_enrolled * 100

    Since primary endpoint data is simulated, a random 3-8% missing rate
    is applied per subject, with a fixed random seed for reproducibility.

    Parameters
    ----------
    dm : pd.DataFrame
        DM dataset with columns SITEID, SUBJID.
    random_seed : int
        Seed for reproducibility (default: 42).

    Returns
    -------
    pd.DataFrame with columns: SITEID, value, n_numerator, n_denominator, status
    """
    defn = QTL_DEFINITIONS["QTL03"]
    rng = np.random.default_rng(random_seed)

    dm_copy = dm[["SITEID", "SUBJID"]].copy()
    # Simulate missingness: each subject has a 3-8% chance of missing endpoint
    missing_prob = rng.uniform(0.03, 0.08, size=len(dm_copy))
    dm_copy["missing_flag"] = (rng.random(size=len(dm_copy)) < missing_prob).astype(int)

    n_enrolled = dm_copy.groupby("SITEID")["SUBJID"].nunique().reset_index(name="n_enrolled")
    n_missing = dm_copy.groupby("SITEID")["missing_flag"].sum().reset_index(name="n_missing")

    result = n_enrolled.merge(n_missing, on="SITEID", how="left")
    result["n_missing"] = result["n_missing"].fillna(0).astype(int)
    result["value"] = (result["n_missing"] / result["n_enrolled"] * 100).round(2)
    result["n_numerator"] = result["n_missing"]
    result["n_denominator"] = result["n_enrolled"]
    result["status"] = result["value"].apply(
        lambda v: _determine_status(v, defn["threshold_yellow"], defn["threshold_red"], defn["direction"])
    )

    for key in ["indicator_id", "indicator_name", "category", "threshold_yellow", "threshold_red"]:
        result[key] = defn[key]

    return result[["SITEID", "indicator_id", "indicator_name", "category", "value",
                   "threshold_yellow", "threshold_red", "status", "n_numerator", "n_denominator"]]


def calc_all_qtl(dm: pd.DataFrame, ds: pd.DataFrame, dv: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all QTL metrics and return a combined DataFrame.

    Parameters
    ----------
    dm : pd.DataFrame  DM dataset
    ds : pd.DataFrame  DS dataset
    dv : pd.DataFrame  DV dataset

    Returns
    -------
    pd.DataFrame with columns:
        SITEID, indicator_id, indicator_name, category, value,
        threshold_yellow, threshold_red, status, n_numerator, n_denominator
    """
    qtl01 = calc_qtl01(dm, dv)
    qtl02 = calc_qtl02(dm, ds)
    qtl03 = calc_qtl03(dm)

    combined = pd.concat([qtl01, qtl02, qtl03], ignore_index=True)
    combined["indicator_type"] = "QTL"

    return combined.sort_values(["SITEID", "indicator_id"]).reset_index(drop=True)


if __name__ == "__main__":
    import os
    DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

    dm = pd.read_csv(os.path.join(DATA_DIR, "dm.csv"))
    ds = pd.read_csv(os.path.join(DATA_DIR, "ds.csv"))
    dv = pd.read_csv(os.path.join(DATA_DIR, "dv.csv"))

    result = calc_all_qtl(dm, ds, dv)
    print(result.to_string(index=False))
