import json
import os
import sqlite3
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'patents.db')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def run_query(conn, sql):
    return pd.read_sql_query(sql, conn)


# =============================================================================
# DATA FETCHING
# Each function fetches exactly what the report needs — no more.
# =============================================================================

def fetch_total_patents(conn):
    return conn.execute("SELECT COUNT(*) FROM patents").fetchone()[0]


def fetch_top_inventors(conn, limit=20):
    return run_query(conn, f"""
        SELECT
            i.name,
            i.country,
            COUNT(DISTINCT r.patent_id) AS patent_count
        FROM inventors i
        JOIN relationships r ON i.inventor_id = r.inventor_id
        GROUP BY i.inventor_id, i.name, i.country
        ORDER BY patent_count DESC
        LIMIT {limit}
    """)


def fetch_top_companies(conn, limit=20):
    return run_query(conn, f"""
        SELECT
            c.name,
            COUNT(DISTINCT r.patent_id) AS patent_count
        FROM companies c
        JOIN relationships r ON c.company_id = r.company_id
        GROUP BY c.company_id, c.name
        ORDER BY patent_count DESC
        LIMIT {limit}
    """)


def fetch_country_trends(conn, limit=20):
    return run_query(conn, f"""
        SELECT
            i.country,
            COUNT(DISTINCT r.patent_id)                              AS patent_count,
            ROUND(
                COUNT(DISTINCT r.patent_id) * 100.0 /
                (SELECT COUNT(*) FROM patents), 2
            )                                                        AS share_pct
        FROM inventors i
        JOIN relationships r ON i.inventor_id = r.inventor_id
        WHERE i.country != 'UNKNOWN'
        GROUP BY i.country
        ORDER BY patent_count DESC
        LIMIT {limit}
    """)


def fetch_yearly_trends(conn):
    return run_query(conn, """
        SELECT year, COUNT(*) AS patent_count
        FROM patents
        WHERE year IS NOT NULL
          AND year BETWEEN 1836 AND 2025
        GROUP BY year
        ORDER BY year ASC
    """)


# =============================================================================
# CONSOLE REPORT
# Printed to terminal — formatted to match the assignment example exactly
# =============================================================================

def print_console_report(total, inventors_df, companies_df, countries_df):
    width = 55

    print("\n" + "=" * width)
    print(" PATENT REPORT".center(width))
    print("=" * width)

    print(f"\n  Total Patents: {total:,}")

    print(f"\n  Top Inventors:")
    for i, row in inventors_df.head(10).iterrows():
        print(f"    {i + 1}. {row['name']} ({row['country']}) — {row['patent_count']:,}")

    print(f"\n  Top Companies:")
    for i, row in companies_df.head(10).iterrows():
        print(f"    {i + 1}. {row['name']} — {row['patent_count']:,}")

    print(f"\n  Top Countries:")
    for i, row in countries_df.head(10).iterrows():
        print(f"    {i + 1}. {row['country']} — {row['patent_count']:,} ({row['share_pct']}%)")

    print("\n" + "=" * width)


# =============================================================================
# CSV EXPORTS
# The three files the assignment explicitly requires
# =============================================================================

def export_csvs(inventors_df, companies_df, countries_df, yearly_df):
    inventors_path = os.path.join(OUTPUT_DIR, 'top_inventors.csv')
    inventors_df.to_csv(inventors_path, index=False)
    print(f"  Saved top_inventors.csv ({len(inventors_df)} rows)")

    companies_path = os.path.join(OUTPUT_DIR, 'top_companies.csv')
    companies_df.to_csv(companies_path, index=False)
    print(f"  Saved top_companies.csv ({len(companies_df)} rows)")

    countries_path = os.path.join(OUTPUT_DIR, 'country_trends.csv')
    countries_df.to_csv(countries_path, index=False)
    print(f"  Saved country_trends.csv ({len(countries_df)} rows)")

    yearly_path = os.path.join(OUTPUT_DIR, 'yearly_trends.csv')
    yearly_df.to_csv(yearly_path, index=False)
    print(f"  Saved yearly_trends.csv ({len(yearly_df)} rows)")


# =============================================================================
# JSON REPORT
# Structured summary matching the assignment's example format exactly
# =============================================================================

def export_json(total, inventors_df, companies_df, countries_df):
    report = {
        "total_patents": total,
        "top_inventors": [
            {
                "name": row["name"],
                "country": row["country"],
                "patents": int(row["patent_count"])
            }
            for _, row in inventors_df.head(10).iterrows()
        ],
        "top_companies": [
            {
                "name": row["name"],
                "patents": int(row["patent_count"])
            }
            for _, row in companies_df.head(10).iterrows()
        ],
        "top_countries": [
            {
                "country": row["country"],
                "patents": int(row["patent_count"]),
                "share": float(row["share_pct"])
            }
            for _, row in countries_df.head(10).iterrows()
        ]
    }

    json_path = os.path.join(OUTPUT_DIR, 'report.json')
    with open(json_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"  Saved report.json")

    return report


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 55)
    print("  PatentsView Report Generator")
    print("=" * 55)

    conn = get_connection()

    try:
        print("\nFetching data from database...")
        total           = fetch_total_patents(conn)
        inventors_df    = fetch_top_inventors(conn)
        companies_df    = fetch_top_companies(conn)
        countries_df    = fetch_country_trends(conn)
        yearly_df       = fetch_yearly_trends(conn)

        # Console report
        print_console_report(total, inventors_df, companies_df, countries_df)

        # CSV exports
        print("\nExporting CSV files...")
        export_csvs(inventors_df, companies_df, countries_df, yearly_df)

        # JSON report
        print("\nExporting JSON report...")
        export_json(total, inventors_df, companies_df, countries_df)

    finally:
        conn.close()

    print("\n" + "=" * 55)
    print("  All reports saved to output/")
    print("=" * 55)


if __name__ == "__main__":
    main()
