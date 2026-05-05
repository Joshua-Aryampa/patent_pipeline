import os
import sqlite3
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'patents.db')


def get_connection():
    """Opens a read-only style connection — we're only querying here."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


def run_query(conn, sql, params=None):
    """
    Runs a SQL query and returns the results as a pandas DataFrame.
    Using pandas here makes it easy to display results cleanly and
    reuse the same DataFrames in the reports step later.
    """
    return pd.read_sql_query(sql, conn, params=params)


# =============================================================================
# Q1 — TOP INVENTORS
# Who has the most patents?
# We count distinct patents per inventor by joining through relationships.
# =============================================================================

Q1 = """
SELECT
    i.inventor_id,
    i.name,
    i.country,
    COUNT(DISTINCT r.patent_id) AS patent_count
FROM inventors i
JOIN relationships r ON i.inventor_id = r.inventor_id
GROUP BY i.inventor_id, i.name, i.country
ORDER BY patent_count DESC
LIMIT 20
"""

# =============================================================================
# Q2 — TOP COMPANIES
# Which companies own the most patents?
# Same pattern as Q1 but joining through companies.
# =============================================================================

Q2 = """
SELECT
    c.company_id,
    c.name,
    COUNT(DISTINCT r.patent_id) AS patent_count
FROM companies c
JOIN relationships r ON c.company_id = r.company_id
GROUP BY c.company_id, c.name
ORDER BY patent_count DESC
LIMIT 20
"""

# =============================================================================
# Q3 — TOP COUNTRIES
# Which countries produce the most patents?
# We count distinct patents per country via the inventor-relationships link.
# A patent is attributed to a country if any of its inventors is from there.
# =============================================================================

Q3 = """
SELECT
    i.country,
    COUNT(DISTINCT r.patent_id) AS patent_count,
    ROUND(
        COUNT(DISTINCT r.patent_id) * 100.0 /
        (SELECT COUNT(*) FROM patents),
        2
    ) AS share_pct
FROM inventors i
JOIN relationships r ON i.inventor_id = r.inventor_id
WHERE i.country != 'UNKNOWN'
GROUP BY i.country
ORDER BY patent_count DESC
LIMIT 20
"""

# =============================================================================
# Q4 — TRENDS OVER TIME
# How many patents are granted each year?
# Straightforward aggregation on the year column in patents.
# =============================================================================

Q4 = """
SELECT
    year,
    COUNT(*) AS patent_count
FROM patents
WHERE year IS NOT NULL
  AND year BETWEEN 1836 AND 2025
GROUP BY year
ORDER BY year ASC
"""

# =============================================================================
# Q5 — JOIN QUERY
# Combine patents with their inventors and companies in one result set.
# Shows a sample of 25 patents with full context — title, inventor, company.
# =============================================================================

Q5 = """
SELECT
    p.patent_id,
    p.title,
    p.year,
    p.patent_type,
    i.name       AS inventor_name,
    i.country    AS inventor_country,
    c.name       AS company_name
FROM patents p
JOIN relationships r  ON p.patent_id   = r.patent_id
JOIN inventors i      ON r.inventor_id = i.inventor_id
JOIN companies c      ON r.company_id  = c.company_id
WHERE p.year IS NOT NULL
ORDER BY p.year DESC
LIMIT 25
"""

# =============================================================================
# Q6 — CTE QUERY (WITH statement)
# Breaks a complex question into readable steps.
# Question: Which countries have seen the most growth in patents
# between the 1990s and the 2010s?
# Step 1 CTE: count patents per country per decade
# Step 2 CTE: pivot into 1990s and 2010s columns
# Final: compute growth and rank
# =============================================================================

Q6 = """
WITH patents_per_country_decade AS (
    -- Count distinct patents per country per decade
    SELECT
        i.country,
        CASE
            WHEN p.year BETWEEN 1990 AND 1999 THEN '1990s'
            WHEN p.year BETWEEN 2010 AND 2019 THEN '2010s'
        END AS decade,
        COUNT(DISTINCT r.patent_id) AS patent_count
    FROM patents p
    JOIN relationships r ON p.patent_id   = r.patent_id
    JOIN inventors i     ON r.inventor_id = i.inventor_id
    WHERE p.year BETWEEN 1990 AND 1999
       OR p.year BETWEEN 2010 AND 2019
    AND i.country != 'UNKNOWN'
    GROUP BY i.country, decade
),
pivoted AS (
    -- Pivot the decade rows into two columns side by side
    SELECT
        country,
        SUM(CASE WHEN decade = '1990s' THEN patent_count ELSE 0 END) AS patents_1990s,
        SUM(CASE WHEN decade = '2010s' THEN patent_count ELSE 0 END) AS patents_2010s
    FROM patents_per_country_decade
    GROUP BY country
)
-- Compute absolute and percentage growth, filter countries with
-- meaningful 1990s baseline to avoid division noise
SELECT
    country,
    patents_1990s,
    patents_2010s,
    (patents_2010s - patents_1990s) AS absolute_growth,
    ROUND(
        (patents_2010s - patents_1990s) * 100.0 / patents_1990s,
        1
    ) AS growth_pct
FROM pivoted
WHERE patents_1990s > 100
ORDER BY growth_pct DESC
LIMIT 20
"""

# =============================================================================
# Q7 — RANKING QUERY (window functions)
# Rank inventors within each country by their patent count.
# Uses RANK() window function — inventors with the same count get the same rank.
# =============================================================================

Q7 = """
WITH inventor_counts AS (
    SELECT
        i.inventor_id,
        i.name,
        i.country,
        COUNT(DISTINCT r.patent_id) AS patent_count
    FROM inventors i
    JOIN relationships r ON i.inventor_id = r.inventor_id
    WHERE i.country != 'UNKNOWN'
    GROUP BY i.inventor_id, i.name, i.country
),
ranked AS (
    SELECT
        inventor_id,
        name,
        country,
        patent_count,
        RANK() OVER (
            PARTITION BY country
            ORDER BY patent_count DESC
        ) AS country_rank
    FROM inventor_counts
)
-- Return the top 3 inventors per country for the top 10 countries by volume
SELECT
    r.country,
    r.country_rank,
    r.name,
    r.patent_count
FROM ranked r
WHERE r.country IN (
    SELECT country
    FROM inventor_counts
    GROUP BY country
    ORDER BY SUM(patent_count) DESC
    LIMIT 10
)
AND r.country_rank <= 3
ORDER BY r.country, r.country_rank
"""


def run_all(conn):
    """Runs all 7 queries and returns results as a dictionary of DataFrames."""
    print("Running queries...\n")

    results = {}

    print("Q1 — Top 20 Inventors by Patent Count")
    results['q1_top_inventors'] = run_query(conn, Q1)
    print(results['q1_top_inventors'].to_string(index=False))

    print("\nQ2 — Top 20 Companies by Patent Count")
    results['q2_top_companies'] = run_query(conn, Q2)
    print(results['q2_top_companies'].to_string(index=False))

    print("\nQ3 — Top 20 Countries by Patent Count")
    results['q3_countries'] = run_query(conn, Q3)
    print(results['q3_countries'].to_string(index=False))

    print("\nQ4 — Patent Trends by Year")
    results['q4_trends'] = run_query(conn, Q4)
    print(results['q4_trends'].to_string(index=False))

    print("\nQ5 — Sample JOIN: Patents with Inventors and Companies")
    results['q5_join'] = run_query(conn, Q5)
    print(results['q5_join'].to_string(index=False))

    print("\nQ6 — CTE: Country Patent Growth from 1990s to 2010s")
    results['q6_cte'] = run_query(conn, Q6)
    print(results['q6_cte'].to_string(index=False))

    print("\nQ7 — Window Function: Top 3 Inventors Ranked Within Each Country")
    results['q7_ranked'] = run_query(conn, Q7)
    print(results['q7_ranked'].to_string(index=False))

    return results


def main():
    print("=" * 60)
    print("  PatentsView SQL Analysis")
    print("=" * 60)

    conn = get_connection()
    try:
        results = run_all(conn)
    finally:
        conn.close()

    print("\n" + "=" * 60)
    print("  All queries completed.")
    print("=" * 60)

    return results


if __name__ == "__main__":
    main()
