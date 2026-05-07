# Global Patent Intelligence Data Pipeline

A full data engineering pipeline that collects, cleans, stores, and analyzes
real-world USPTO patent data from the PatentsView Granted Patent Disambiguated
dataset. Built as part of a big data course project.

🌐 **Live Dashboard:** [patentpipeline.streamlit.app](https://patentpipeline.streamlit.app/)

---

## What This Pipeline Does

```
Raw TSV Files (USPTO PatentsView)
        ↓
notebooks/01_data_profile.ipynb  — Full data profiling before any cleaning decisions
        ↓
scripts/clean.py      — Two-phase chunked data cleaner
        ↓
scripts/load_db.py    — Loads clean CSVs into a SQLite database
        ↓
scripts/queries.py    — Runs 7 analytical SQL queries
        ↓
scripts/reports.py    — Generates console report, CSVs, and JSON
        ↓
dashboard.py          — Interactive Streamlit dashboard with insights
```

---

## Database Tables

| Table | Rows | Description |
|---|---|---|
| patents | 9,434,700 | Patent titles, abstracts, dates, types |
| inventors | 4,293,932 | Disambiguated inventor names and countries |
| companies | 572,495 | Disambiguated assignee/company names |
| relationships | 25,291,521 | Patent → inventor → company links |

---

## SQL Queries Covered

| Query | Description |
|---|---|
| Q1 | Top inventors by patent count |
| Q2 | Top companies by patent count |
| Q3 | Top countries by patent count with share percentage |
| Q4 | Patent trend by year (1836–2025) |
| Q5 | JOIN across patents, inventors, and companies |
| Q6 | CTE — country patent growth from 1990s to 2010s |
| Q7 | Window function — top 3 inventors ranked within each country |

---

## Dashboard & Insights

The project includes a fully deployed interactive Streamlit dashboard with two pages:

**Dashboard page:**
- Key metrics — total patents, top inventor, top company, top country
- Patent grants over time (area chart, 1976–2025)
- Top 20 inventors by patent count, coloured by country
- Top 20 companies by patent count
- World map of patents by country
- Country share pie chart
- Expandable raw data tables

**Insights & Analysis page** — five data-driven insights with charts, numbers, and interpretations:

1. **The 1970s Inflection Point** — why patent grants exploded in that decade and what it tells us about IP as a corporate strategy
2. **US Dominance — Commanding but Slowly Eroding** — the US holds 54.61% of all patents but Asia is closing the gap fast
3. **Peak Innovation? The Post-2019 Decline** — two competing explanations: data processing lag vs genuine slowdown
4. **The Prolific Inventor Phenomenon** — why Shunpei Yamazaki's 6,787 patents says more about institutional strategy than individual genius
5. **East Asia's Strategic Patent Buildout** — how state industrial policy drove one of the biggest transfers of technological leverage in history

---

## Project Structure

```
patent_pipeline/
├── data/
│   ├── raw/                        ← Downloaded TSV files (not on GitHub — too large)
│   └── clean/
│       ├── intermediate/           ← Phase 1 cleaned files
│       ├── clean_patents.csv
│       ├── clean_inventors.csv
│       ├── clean_companies.csv
│       └── clean_relationships.csv
├── database/
│   └── patents.db                  ← SQLite database (not on GitHub — too large)
├── notebooks/
│   └── 01_data_profile.ipynb       ← Full data profiling before cleaning
├── output/
│   ├── top_inventors.csv
│   ├── top_companies.csv
│   ├── country_trends.csv
│   ├── yearly_trends.csv
│   └── report.json
├── scripts/
│   ├── clean.py                    ← Two-phase chunked data cleaner
│   ├── load_db.py                  ← SQLite database loader
│   ├── queries.py                  ← All 7 SQL analytical queries
│   └── reports.py                  ← Console, CSV, and JSON report generator
├── sql/
│   └── schema.sql                  ← Database schema and indexes
├── dashboard.py                    ← Streamlit dashboard (deployed)
├── main.py                         ← Runs the full pipeline end to end
└── requirements.txt
```

---

## How to Reproduce

### 1. Clone the repository

```bash
git clone https://github.com/Joshua-Aryampa/patent_pipeline.git
cd patent_pipeline
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Download the raw data manually

The source files are too large for GitHub. Download these 6 files from:

👉 https://data.uspto.gov/bulkdata/datasets/pvgpatdis

| File |
|---|
| g_patent.tsv.zip |
| g_patent_abstract.tsv.zip |
| g_application.tsv.zip |
| g_inventor_disambiguated.tsv.zip |
| g_assignee_disambiguated.tsv.zip |
| g_location_disambiguated.tsv.zip |

Extract each zip file and place the resulting `.tsv` files into `data/raw/`.

### 5. Run the full pipeline

```bash
python main.py
```

This runs all four steps in order — cleaning, loading, querying, and reporting.
Total runtime is approximately 60–90 minutes depending on your machine.

### 6. Run individual steps

```bash
python scripts/clean.py      # Clean raw data only
python scripts/load_db.py    # Load database only
python scripts/queries.py    # Run SQL queries only
python scripts/reports.py    # Generate reports only
```

### 7. Run the dashboard locally

```bash
streamlit run dashboard.py
```

---

## Data Source

**PatentsView Granted Patent Disambiguated Data**
- Provider: USPTO Open Data Portal
- URL: https://data.uspto.gov/bulkdata/datasets/pvgpatdis
- Coverage: US granted patents from 1976 to present
- Reference: PV_grant_data_dictionary.pdf

---

## Key Findings

- **9.4 million** granted US patents in the dataset
- **Top inventor:** Shunpei Yamazaki (Japan) with 6,787 patents
- **Top company:** Samsung Display Co., Ltd. with 174,536 patents
- **Top country:** USA with 54.61% of all patents
- **Fastest growing:** India (+2,664%) and China (+1,896%) from 1990s to 2010s
- **Peak year:** 2019 with 388,456 patents granted

---

## Technical Notes

- All large files are processed in chunks of 200,000 rows to manage memory — no single file is ever fully loaded into RAM
- The cleaning pipeline runs in two phases: Phase 1 cleans each file independently in chunks; Phase 2 merges the clean intermediates into final output tables
- The abstract file (`g_patent_abstract.tsv`) requires the Python parser engine and `csv.QUOTE_NONE` due to buffer overflow on very long abstract text and unescaped quote characters inside the text
- Dates with impossible years (before 1836) are nullified — confirmed data entry errors found during profiling (e.g. 1074, 1298)
- SQLite indexes are dropped before bulk relationship inserts and rebuilt afterwards — significantly faster than maintaining indexes across 25M row-by-row inserts
- `latin-1` encoding used throughout — patent data contains multilingual inventor names that break UTF-8
- The dashboard reads entirely from pre-computed CSVs in `output/` — no database queries at runtime, loads in seconds

---

## Dependencies

| Package | Purpose |
|---|---|
| pandas | Data cleaning and transformation |
| sqlite3 | Database storage and queries (built into Python) |
| streamlit | Interactive dashboard |
| plotly | Charts and visualizations |
| pycountry | ISO-2 to ISO-3 country code conversion for world map |
| requests | HTTP utilities |
| tqdm | Progress bars |
