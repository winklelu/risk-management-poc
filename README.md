# Clinical Trial Risk Management Dashboard

A Proof-of-Concept (POC) interactive risk management tool for clinical trials, built with Python, Shiny for Python, and Quarto.

## Live Demo

> After GitHub Pages deployment, your app will be accessible at:
> `https://<your-username>.github.io/<repo-name>/`

---

## Project Structure

```
Risk_Management/
├── config/
│   └── indicators.yaml        # QTL/KRI definitions & thresholds
├── data/                      # Generated SDTM dummy data & summary
│   ├── dm.csv / ds.csv / dv.csv / ae.csv
│   └── risk_summary.csv
├── python/
│   ├── generate_sdtm.py       # Dummy SDTM data generator
│   ├── calc_qtl.py            # QTL metric calculations
│   ├── calc_kri.py            # KRI metric calculations
│   └── pipeline.py            # End-to-end data pipeline
├── shiny/
│   ├── app.py                 # Shiny dashboard (3 tabs)
│   ├── data/                  # Data bundle for Shinylive
│   ├── config/                # Config bundle for Shinylive
│   ├── www/styles.css
│   └── requirements.txt
└── quarto/
    └── risk_report.qmd        # Dynamic Quarto HTML report
```

## Indicators

| ID | Type | Name | Yellow | Red |
|----|------|------|--------|-----|
| QTL01 | QTL | Protocol Deviation Rate | >5% | >10% |
| QTL02 | QTL | Early Discontinuation Rate | >15% | >25% |
| QTL03 | QTL | Missing Primary Endpoint Rate | >5% | >10% |
| KRI01 | KRI | Adverse Event Rate | >40% | >60% |
| KRI02 | KRI | Serious Adverse Event Rate | >10% | >20% |
| KRI03 | KRI | Enrollment Rate Achievement | <80% | <60% |
| KRI04 | KRI | Query Resolution Rate | <85% | <70% |

---

## Local Setup

### 1. Install dependencies

```bash
pip install shiny plotly pandas numpy pyyaml
```

### 2. Generate data

```bash
cd python
python pipeline.py
```

### 3. Run Shiny dashboard

```bash
cd shiny
shiny run app.py
```

Open `http://127.0.0.1:8000` in your browser.

### 4. Render Quarto report (requires [Quarto CLI](https://quarto.org/docs/get-started/))

```bash
cd quarto
quarto render risk_report.qmd
```

---

## Deploy to GitHub Pages (Shinylive)

### Step 1 — Create a GitHub repository

```bash
cd /path/to/Risk_Management
git init
git add .
git commit -m "Initial commit: Risk Management POC"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

### Step 2 — Enable GitHub Pages

1. Go to your repository → **Settings** → **Pages**
2. Under **Source**, select **GitHub Actions**
3. Save

### Step 3 — Trigger deployment

Push any commit to `main`. The GitHub Action (`.github/workflows/deploy.yml`) will:
1. Generate SDTM data via `pipeline.py`
2. Export a Shinylive static bundle
3. Deploy to GitHub Pages automatically

The live URL will appear in **Settings → Pages** after deployment (~2 minutes).

---

## Dashboard Features

| Feature | Description |
|---------|-------------|
| **Summary Tab** | Heatmap (Site × Indicator), stat cards, site risk table |
| **QTL Details Tab** | Bar chart with threshold lines, detail table, indicator description |
| **KRI Details Tab** | Same as QTL, focused on KRI indicators |
| **Filters** | Category / Indicator / Site — all tabs have independent filters |
| **Tooltips** | Hover on indicators to see description & justification |
| **Outlier Sites** | SITE003 (red AE), SITE004 (red deviation) for demo purposes |
