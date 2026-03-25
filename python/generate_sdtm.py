"""
Generate dummy SDTM data for Risk Management POC.

Sites: SITE001-SITE008
- SITE003: outlier (high AE rate ~70%, high deviation rate ~15%)
- SITE006: mild outlier (high early discontinuation ~25%)
- Other sites: mostly within normal range

Output files saved to ../data/:
    dm.csv  - Demographics & enrollment
    ds.csv  - Disposition
    dv.csv  - Protocol Deviations
    ae.csv  - Adverse Events
"""

import os
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

STUDY_ID = "STUDY001"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# Site configuration: (n_subjects, planned, ae_rate, dv_rate, disc_rate, sae_rate)
SITE_CONFIG = {
    "SITE001": {"n": 25, "planned": 28, "ae_rate": 0.30, "dv_rate": 0.04, "disc_rate": 0.08, "sae_rate": 0.06},
    "SITE002": {"n": 22, "planned": 25, "ae_rate": 0.35, "dv_rate": 0.03, "disc_rate": 0.10, "sae_rate": 0.07},
    "SITE003": {"n": 27, "planned": 30, "ae_rate": 0.70, "dv_rate": 0.15, "disc_rate": 0.12, "sae_rate": 0.22},  # outlier
    "SITE004": {"n": 20, "planned": 22, "ae_rate": 0.28, "dv_rate": 0.05, "disc_rate": 0.09, "sae_rate": 0.05},
    "SITE005": {"n": 30, "planned": 32, "ae_rate": 0.33, "dv_rate": 0.04, "disc_rate": 0.07, "sae_rate": 0.08},
    "SITE006": {"n": 24, "planned": 26, "ae_rate": 0.36, "dv_rate": 0.06, "disc_rate": 0.26, "sae_rate": 0.09},  # mild outlier
    "SITE007": {"n": 28, "planned": 30, "ae_rate": 0.31, "dv_rate": 0.03, "disc_rate": 0.07, "sae_rate": 0.06},
    "SITE008": {"n": 21, "planned": 24, "ae_rate": 0.29, "dv_rate": 0.04, "disc_rate": 0.10, "sae_rate": 0.07},
}

ARMS = [("A", "Treatment A"), ("B", "Treatment B")]
SEXES = ["M", "F"]
RACES = ["WHITE", "BLACK OR AFRICAN AMERICAN", "ASIAN", "OTHER"]
RACE_PROBS = [0.65, 0.15, 0.15, 0.05]

AE_TERMS = [
    "Headache", "Nausea", "Fatigue", "Dizziness", "Rash",
    "Vomiting", "Diarrhea", "Insomnia", "Back Pain", "Cough",
    "Dyspnea", "Hypertension", "Hypotension", "Arthralgia", "Myalgia",
]
AE_SEVERITIES = ["MILD", "MODERATE", "SEVERE"]
AE_SEV_PROBS = [0.55, 0.35, 0.10]

DV_TERMS = [
    "Missed visit outside window",
    "Concomitant medication violation",
    "Incorrect dose administered",
    "Eligibility criteria not met",
    "Prohibited procedure performed",
    "Study drug dispensing error",
]
DV_CATS = ["VISIT", "MEDICATION", "PROCEDURE", "ELIGIBILITY"]

DS_REASONS = [
    "Adverse Event",
    "Subject Decision",
    "Physician Decision",
    "Lost to Follow-up",
    "Protocol Deviation",
]


def random_date(start_str: str, end_str: str) -> str:
    """Return random ISO date string between start and end."""
    start = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    delta = (end - start).days
    rand_days = random.randint(0, max(delta, 0))
    return (start + timedelta(days=rand_days)).strftime("%Y-%m-%d")


def generate_dm() -> pd.DataFrame:
    """Generate DM (Demographics) dataset."""
    rows = []
    subj_counter = 1

    for site_id, cfg in SITE_CONFIG.items():
        for i in range(cfg["n"]):
            subjid = f"{site_id[:4]}{subj_counter:04d}"
            subj_counter += 1
            arm_code, arm_label = random.choice(ARMS)
            age = int(np.random.normal(52, 12))
            age = max(18, min(80, age))
            sex = random.choice(SEXES)
            race = np.random.choice(RACES, p=RACE_PROBS)
            enrl_dt = random_date("2023-01-01", "2024-06-30")

            rows.append({
                "STUDYID": STUDY_ID,
                "SITEID": site_id,
                "SUBJID": subjid,
                "AGE": age,
                "SEX": sex,
                "RACE": race,
                "ARMCD": arm_code,
                "ARM": arm_label,
                "ENRLDT": enrl_dt,
                "PLANNED": cfg["planned"],
            })

    return pd.DataFrame(rows)


def generate_ds(dm: pd.DataFrame) -> pd.DataFrame:
    """Generate DS (Disposition) dataset."""
    rows = []

    for _, subj in dm.iterrows():
        site_id = subj["SITEID"]
        cfg = SITE_CONFIG[site_id]
        disc_rate = cfg["disc_rate"]

        discontinued = random.random() < disc_rate
        if discontinued:
            dsdecod = "DISCONTINUED"
            reason = random.choice(DS_REASONS)
        else:
            dsdecod = "COMPLETED"
            reason = "COMPLETED"

        enrl_dt = datetime.strptime(subj["ENRLDT"], "%Y-%m-%d")
        offset_days = random.randint(180, 365) if not discontinued else random.randint(30, 180)
        ds_dt = (enrl_dt + timedelta(days=offset_days)).strftime("%Y-%m-%d")

        rows.append({
            "STUDYID": subj["STUDYID"],
            "SITEID": site_id,
            "SUBJID": subj["SUBJID"],
            "DSDECOD": dsdecod,
            "DSREASON": reason,
            "DSSTDTC": ds_dt,
        })

    return pd.DataFrame(rows)


def generate_dv(dm: pd.DataFrame) -> pd.DataFrame:
    """Generate DV (Protocol Deviations) dataset."""
    rows = []

    for _, subj in dm.iterrows():
        site_id = subj["SITEID"]
        cfg = SITE_CONFIG[site_id]
        dv_rate = cfg["dv_rate"]

        has_dv = random.random() < dv_rate
        if not has_dv:
            continue

        # Each subject with a deviation may have 1-3 deviations
        n_dv = random.randint(1, 3)
        enrl_dt = datetime.strptime(subj["ENRLDT"], "%Y-%m-%d")

        for _ in range(n_dv):
            dv_term = random.choice(DV_TERMS)
            dv_cat = random.choice(DV_CATS)
            offset_days = random.randint(7, 300)
            dv_dt = (enrl_dt + timedelta(days=offset_days)).strftime("%Y-%m-%d")

            rows.append({
                "STUDYID": subj["STUDYID"],
                "SITEID": site_id,
                "SUBJID": subj["SUBJID"],
                "DVTERM": dv_term,
                "DVCAT": dv_cat,
                "DVDECOD": dv_cat,
                "DVSTDTC": dv_dt,
            })

    return pd.DataFrame(rows)


def generate_ae(dm: pd.DataFrame) -> pd.DataFrame:
    """Generate AE (Adverse Events) dataset."""
    rows = []

    for _, subj in dm.iterrows():
        site_id = subj["SITEID"]
        cfg = SITE_CONFIG[site_id]
        ae_rate = cfg["ae_rate"]
        sae_rate = cfg["sae_rate"]

        has_ae = random.random() < ae_rate
        if not has_ae:
            continue

        # Subjects with AE may have 1-5 events
        n_ae = random.randint(1, 5)
        enrl_dt = datetime.strptime(subj["ENRLDT"], "%Y-%m-%d")

        has_sae_assigned = False
        for j in range(n_ae):
            ae_term = random.choice(AE_TERMS)
            ae_sev = np.random.choice(AE_SEVERITIES, p=AE_SEV_PROBS)

            # Assign SAE flag: first AE gets SAE based on sae_rate
            if j == 0:
                aeser = "Y" if random.random() < sae_rate else "N"
                if aeser == "Y":
                    has_sae_assigned = True
                    ae_sev = "SEVERE"
            else:
                aeser = "N"

            offset_days = random.randint(1, 300)
            ae_dt = (enrl_dt + timedelta(days=offset_days)).strftime("%Y-%m-%d")

            rows.append({
                "STUDYID": subj["STUDYID"],
                "SITEID": site_id,
                "SUBJID": subj["SUBJID"],
                "AETERM": ae_term,
                "AESEV": ae_sev,
                "AESER": aeser,
                "AESTDTC": ae_dt,
            })

    return pd.DataFrame(rows)


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    print("Generating DM (Demographics) data...")
    dm = generate_dm()
    dm.to_csv(os.path.join(DATA_DIR, "dm.csv"), index=False)
    print(f"  Saved dm.csv: {len(dm)} subjects across {dm['SITEID'].nunique()} sites")

    print("Generating DS (Disposition) data...")
    ds = generate_ds(dm)
    ds.to_csv(os.path.join(DATA_DIR, "ds.csv"), index=False)
    print(f"  Saved ds.csv: {len(ds)} disposition records")

    print("Generating DV (Protocol Deviations) data...")
    dv = generate_dv(dm)
    dv.to_csv(os.path.join(DATA_DIR, "dv.csv"), index=False)
    print(f"  Saved dv.csv: {len(dv)} deviation records")

    print("Generating AE (Adverse Events) data...")
    ae = generate_ae(dm)
    ae.to_csv(os.path.join(DATA_DIR, "ae.csv"), index=False)
    print(f"  Saved ae.csv: {len(ae)} adverse event records")

    # Quick summary
    print("\n--- Site Summary ---")
    site_summary = dm.groupby("SITEID").size().reset_index(name="n_enrolled")
    ae_subj = ae[ae["AESER"] == "N"].groupby("SITEID")["SUBJID"].nunique().reset_index(name="n_ae_subj")
    sae_subj = ae[ae["AESER"] == "Y"].groupby("SITEID")["SUBJID"].nunique().reset_index(name="n_sae_subj")
    dv_subj = dv.groupby("SITEID")["SUBJID"].nunique().reset_index(name="n_dv_subj")
    disc_subj = ds[ds["DSDECOD"] == "DISCONTINUED"].groupby("SITEID")["SUBJID"].nunique().reset_index(name="n_disc_subj")

    summary = site_summary.merge(ae_subj, on="SITEID", how="left")
    summary = summary.merge(sae_subj, on="SITEID", how="left")
    summary = summary.merge(dv_subj, on="SITEID", how="left")
    summary = summary.merge(disc_subj, on="SITEID", how="left")
    summary = summary.fillna(0).astype({"n_ae_subj": int, "n_sae_subj": int, "n_dv_subj": int, "n_disc_subj": int})
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
