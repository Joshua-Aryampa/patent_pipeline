# Global Patent Intelligence Data Pipeline

A full data engineering pipeline that collects, cleans, stores, and analyzes
real-world USPTO patent data from the PatentsView Granted Patent Disambiguated
dataset. Built as part of a big data course project.

---

## What This Pipeline Does

```
Raw TSV Files (USPTO PatentsView)
        ↓
scripts/clean.py      — Cleans and structures the raw data into CSVs
        ↓
scripts/load_db.py    — Loads clean CSVs into a SQLite database
        ↓
scripts/queries.py    — Runs 7 analytical SQL queries
        ↓
scripts/reports.py    — Generates console report, CSVs, and JSON
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
├── main.py                         ← Runs the full pipeline end to end
└── requirements.txt
```

---

## How to Reproduce

### 1. Clone the repository

```bash
git clone <your-repo-url>
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

---

## Data Source

**PatentsView Granted Patent Disambiguated Data**
- Provider: USPTO Open Data Portal
- URL: https://data.uspto.gov/bulkdata/datasets/pvgpatdis
- Coverage: US granted patents from 1976 to present
- Reference: PV_grant_data_dictionary.pdf (included in repo)

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

- All large files are processed in chunks of 200,000 rows to manage memory
- The abstract file uses Python engine + `csv.QUOTE_NONE` due to unescaped
  quotes and very long lines exceeding the C parser buffer
- Dates with impossible years (before 1836) are nullified — confirmed data
  entry errors in old records (e.g. 1074, 1298 found in profiling)
- SQLite indexes are dropped before bulk relationship inserts and rebuilt
  afterwards for significantly faster load performance
- `latin-1` encoding used throughout — patent data contains multilingual
  inventor names that break UTF-8

---

## Dependencies

| Package | Purpose |
|---|---|
| pandas | Data cleaning and transformation |
| sqlite3 | Database storage and queries (built into Python) |
| jupyter | Data profiling notebook |
| requests | HTTP downloads |
| tqdm | Progress bars |
