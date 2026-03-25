"""
KRI (Key Risk Indicator) calculation module.

Calculates site-level KRI metrics from SDTM datasets:
    KRI01 - Adverse Event Rate
    KRI02 - Serious Adverse Event Rate
    KRI03 - Enrollment Rate Achievement
    KRI04 - Query Resolution Rate
"""

import numpy as np
import pandas as pd

# KRI threshold definitions (mirrored from config/indicators.yaml)
KRI_DEFINITIONS = {
    "KRI01": {
        "indicator_id": "KRI01",
        "indicator_name": "Adverse Event Rate",
        "category": "Safety",
        "description": "Percentage of subjects experiencing at least one adverse event",
        "justification": "Elevated AE rate may signal safety concerns requiring immediate review",
        "unit": "%",
        "threshold_yellow": 40.0,
        "threshold_red": 60.0,
        "direction": "higher_is_worse",
    },
    "KRI02": {
        "indicator_id": "KRI02",
        "indicator_name": "Serious Adverse Event Rate",
        "category": "Safety",
        "description": "Percentage of subjects experiencing at least one serious adverse event",
        "justification": "SAEs require expedited reporting and may indicate patient safety risk",
        "unit": "%",
        "threshold_yellow": 10.0,
        "threshold_red": 20.0,
        "direction": "higher_is_worse",
    },
    "KRI03": {
        "indicator_id": "KRI03",
        "indicator_name": "Enrollment Rate Achievement",
        "category": "Enrollment",
        "description": "Percentage of planned enrollment achieved at each site",
        "justification": "Under-enrollment may delay study completion and compromise statistical power",
        "unit": "%",
        "threshold_yellow": 80.0,
        "threshold_red": 60.0,
        "direction": "lower_is_worse",
    },
    "KRI04": {
        "indicator_id": "KRI04",
        "indicator_name": "Query Resolution Rate",
        "category": "Data Quality",
        "description": "Percentage of open queries resolved within 30 days",
        "justification": "Unresolved queries indicate data management issues and delay database lock",
        "unit": "%",
        "threshold_yellow": 85.0,
        "threshold_red": 70.0,
        "direction": "lower_is_worse",
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


def calc_kri01(dm: pd.DataFrame, ae: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate KRI01: Adverse Event Rate per site.

    Formula: n_subjects_with_ae / n_enrolled * 100

    Parameters
    ----------
    dm : pd.DataFrame  DM dataset with columns SITEID, SUBJID
    ae : pd.DataFrame  AE dataset with columns SITEID, SUBJID

    Returns
    -------
    pd.DataFrame with site-level KRI01 results
    """
    defn = KRI_DEFINITIONS["KRI01"]

    n_enrolled = dm.groupby("SITEID")["SUBJID"].nunique().reset_index(name="n_enrolled")

    if len(ae) > 0:
        n_with_ae = ae.groupby("SITEID")["SUBJID"].nunique().reset_index(name="n_with_ae")
    else:
        n_with_ae = pd.DataFrame(columns=["SITEID", "n_with_ae"])

    result = n_enrolled.merge(n_with_ae, on="SITEID", how="left")
    result["n_with_ae"] = result["n_with_ae"].fillna(0).astype(int)
    result["value"] = (result["n_with_ae"] / result["n_enrolled"] * 100).round(2)
    result["n_numerator"] = result["n_with_ae"]
    result["n_denominator"] = result["n_enrolled"]
    result["status"] = result["value"].apply(
        lambda v: _determine_status(v, defn["threshold_yellow"], defn["threshold_red"], defn["direction"])
    )

    for key in ["indicator_id", "indicator_name", "category", "threshold_yellow", "threshold_red"]:
        result[key] = defn[key]

    return result[["SITEID", "indicator_id", "indicator_name", "category", "value",
                   "threshold_yellow", "threshold_red", "status", "n_numerator", "n_denominator"]]


def calc_kri02(dm: pd.DataFrame, ae: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate KRI02: Serious Adverse Event Rate per site.

    Formula: n_subjects_with_sae / n_enrolled * 100

    Parameters
    ----------
    dm : pd.DataFrame  DM dataset with columns SITEID, SUBJID
    ae : pd.DataFrame  AE dataset with columns SITEID, SUBJID, AESER

    Returns
    -------
    pd.DataFrame with site-level KRI02 results
    """
    defn = KRI_DEFINITIONS["KRI02"]

    n_enrolled = dm.groupby("SITEID")["SUBJID"].nunique().reset_index(name="n_enrolled")

    if len(ae) > 0:
        sae = ae[ae["AESER"] == "Y"]
        n_with_sae = sae.groupby("SITEID")["SUBJID"].nunique().reset_index(name="n_with_sae")
    else:
        n_with_sae = pd.DataFrame(columns=["SITEID", "n_with_sae"])

    result = n_enrolled.merge(n_with_sae, on="SITEID", how="left")
    result["n_with_sae"] = result["n_with_sae"].fillna(0).astype(int)
    result["value"] = (result["n_with_sae"] / result["n_enrolled"] * 100).round(2)
    result["n_numerator"] = result["n_with_sae"]
    result["n_denominator"] = result["n_enrolled"]
    result["status"] = result["value"].apply(
        lambda v: _determine_status(v, defn["threshold_yellow"], defn["threshold_red"], defn["direction"])
    )

    for key in ["indicator_id", "indicator_name", "category", "threshold_yellow", "threshold_red"]:
        result[key] = defn[key]

    return result[["SITEID", "indicator_id", "indicator_name", "category", "value",
                   "threshold_yellow", "threshold_red", "status", "n_numerator", "n_denominator"]]


def calc_kri03(dm: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate KRI03: Enrollment Rate Achievement per site.

    Formula: n_enrolled / n_planned * 100

    The PLANNED column in DM contains site-level planned enrollment.

    Parameters
    ----------
    dm : pd.DataFrame  DM dataset with columns SITEID, SUBJID, PLANNED

    Returns
    -------
    pd.DataFrame with site-level KRI03 results
    """
    defn = KRI_DEFINITIONS["KRI03"]

    site_data = dm.groupby("SITEID").agg(
        n_enrolled=("SUBJID", "nunique"),
        n_planned=("PLANNED", "first"),
    ).reset_index()

    site_data["value"] = (site_data["n_enrolled"] / site_data["n_planned"] * 100).round(2)
    site_data["n_numerator"] = site_data["n_enrolled"]
    site_data["n_denominator"] = site_data["n_planned"]
    site_data["status"] = site_data["value"].apply(
        lambda v: _determine_status(v, defn["threshold_yellow"], defn["threshold_red"], defn["direction"])
    )

    for key in ["indicator_id", "indicator_name", "category", "threshold_yellow", "threshold_red"]:
        site_data[key] = defn[key]

    return site_data[["SITEID", "indicator_id", "indicator_name", "category", "value",
                       "threshold_yellow", "threshold_red", "status", "n_numerator", "n_denominator"]]


def calc_kri04(dm: pd.DataFrame, random_seed: int = 42) -> pd.DataFrame:
    """
    Calculate KRI04: Query Resolution Rate per site.

    Formula: n_resolved_queries / n_total_queries * 100

    Since query data is not in standard SDTM, this metric is simulated.
    Sites with known data issues (SITE003, SITE006) get lower resolution rates.

    Parameters
    ----------
    dm : pd.DataFrame  DM dataset with columns SITEID, SUBJID
    random_seed : int  Seed for reproducibility (default: 42)

    Returns
    -------
    pd.DataFrame with site-level KRI04 results
    """
    defn = KRI_DEFINITIONS["KRI04"]
    rng = np.random.default_rng(random_seed)

    n_enrolled = dm.groupby("SITEID")["SUBJID"].nunique().reset_index(name="n_enrolled")

    # Simulate query counts: ~3-8 queries per subject
    # Simulate resolution rates based on site characteristics
    SITE_QUERY_RESOLUTION = {
        "SITE001": (0.88, 0.04),  # mean, std
        "SITE002": (0.90, 0.03),
        "SITE003": (0.65, 0.05),  # outlier - low resolution rate
        "SITE004": (0.92, 0.03),
        "SITE005": (0.89, 0.03),
        "SITE006": (0.78, 0.04),  # mild outlier
        "SITE007": (0.91, 0.03),
        "SITE008": (0.87, 0.04),
    }

    rows = []
    for _, row in n_enrolled.iterrows():
        site_id = row["SITEID"]
        n_subj = row["n_enrolled"]

        # Total queries proportional to enrollment
        n_total = int(n_subj * rng.uniform(3, 8))

        # Resolution rate
        mean_rate, std_rate = SITE_QUERY_RESOLUTION.get(site_id, (0.88, 0.04))
        rate = float(np.clip(rng.normal(mean_rate, std_rate), 0.0, 1.0))
        n_resolved = int(n_total * rate)

        value = round(n_resolved / n_total * 100, 2) if n_total > 0 else 0.0
        status = _determine_status(value, defn["threshold_yellow"], defn["threshold_red"], defn["direction"])

        rows.append({
            "SITEID": site_id,
            "indicator_id": defn["indicator_id"],
            "indicator_name": defn["indicator_name"],
            "category": defn["category"],
            "value": value,
            "threshold_yellow": defn["threshold_yellow"],
            "threshold_red": defn["threshold_red"],
            "status": status,
            "n_numerator": n_resolved,
            "n_denominator": n_total,
        })

    return pd.DataFrame(rows)


def calc_all_kri(dm: pd.DataFrame, ae: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all KRI metrics and return a combined DataFrame.

    Parameters
    ----------
    dm : pd.DataFrame  DM dataset
    ae : pd.DataFrame  AE dataset

    Returns
    -------
    pd.DataFrame with columns:
        SITEID, indicator_id, indicator_name, category, value,
        threshold_yellow, threshold_red, status, n_numerator, n_denominator
    """
    kri01 = calc_kri01(dm, ae)
    kri02 = calc_kri02(dm, ae)
    kri03 = calc_kri03(dm)
    kri04 = calc_kri04(dm)

    combined = pd.concat([kri01, kri02, kri03, kri04], ignore_index=True)
    combined["indicator_type"] = "KRI"

    return combined.sort_values(["SITEID", "indicator_id"]).reset_index(drop=True)


if __name__ == "__main__":
    import os
    DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

    dm = pd.read_csv(os.path.join(DATA_DIR, "dm.csv"))
    ae = pd.read_csv(os.path.join(DATA_DIR, "ae.csv"))

    result = calc_all_kri(dm, ae)
    print(result.to_string(index=False))
