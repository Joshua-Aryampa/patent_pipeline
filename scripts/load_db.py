import os
import sqlite3
import pandas as pd

CLEAN_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'clean')
DB_DIR = os.path.join(os.path.dirname(__file__), '..', 'database')
DB_PATH = os.path.join(DB_DIR, 'patents.db')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), '..', 'sql', 'schema.sql')

os.makedirs(DB_DIR, exist_ok=True)

CHUNK_SIZE = 200_000


def get_connection():
    """
    Opens a connection to the SQLite database with settings tuned
    for bulk loading large datasets efficiently.
    WAL mode allows reads and writes to happen concurrently.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA cache_size = -64000")
    conn.execute("PRAGMA temp_store = MEMORY")
    return conn


def apply_schema(conn):
    """
    Reads schema.sql and executes it against the database.
    The schema drops and recreates all tables so this script
    is safe to re-run from scratch.
    """
    print("  Applying schema...")
    with open(SCHEMA_PATH, 'r') as f:
        schema = f.read()
    conn.executescript(schema)
    conn.commit()
    print("  Schema applied.")


def to_sqlite_rows(df, columns):
    """
    Converts a DataFrame to a list of plain Python tuples safe for SQLite.

    The core problem: pandas' Int64 NA and Float64 NA are not the same as
    Python None. SQLite's Python driver only accepts None for NULL values.
    Converting the DataFrame to object dtype first forces all NA variants
    (pd.NA, pd.NaT, float NaN, Int64 NA) to become Python None.
    """
    return [
        tuple(None if pd.isna(v) else v for v in row)
        for row in df[columns].astype(object).itertuples(index=False, name=None)
    ]


def load_patents(conn):
    """
    Loads clean_patents.csv into the patents table in chunks.
    year is cast to Int64 first then handled by to_sqlite_rows.
    """
    print("\n  Loading patents...")
    path = os.path.join(CLEAN_DIR, 'clean_patents.csv')
    total = 0

    for chunk in pd.read_csv(path, dtype=str, chunksize=CHUNK_SIZE):
        chunk['year'] = pd.to_numeric(chunk['year'], errors='coerce').astype('Int64')

        rows = to_sqlite_rows(chunk, [
            'patent_id', 'title', 'abstract',
            'filing_date', 'grant_date', 'year', 'patent_type'
        ])

        conn.executemany(
            """INSERT OR IGNORE INTO patents
               (patent_id, title, abstract, filing_date, grant_date, year, patent_type)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            rows
        )
        conn.commit()
        total += len(rows)

        if total % 1_000_000 == 0:
            print(f"    ...{total:,} patents inserted")

    print(f"  Done — {total:,} patents loaded")


def load_inventors(conn):
    """
    Loads clean_inventors.csv into the inventors table.
    inventor_id is PRIMARY KEY — INSERT OR IGNORE handles cross-chunk
    duplicates where the same inventor appears on multiple patents.
    """
    print("\n  Loading inventors...")
    path = os.path.join(CLEAN_DIR, 'clean_inventors.csv')
    total = 0

    for chunk in pd.read_csv(path, dtype=str, chunksize=CHUNK_SIZE):
        chunk = chunk.drop_duplicates(subset='inventor_id')

        rows = to_sqlite_rows(chunk, ['inventor_id', 'name', 'country'])

        conn.executemany(
            """INSERT OR IGNORE INTO inventors (inventor_id, name, country)
               VALUES (?, ?, ?)""",
            rows
        )
        conn.commit()
        total += len(rows)

        if total % 2_000_000 == 0:
            print(f"    ...{total:,} inventors inserted")

    print(f"  Done — {total:,} inventor records loaded")


def load_companies(conn):
    """
    Loads clean_companies.csv into the companies table.
    company_id is PRIMARY KEY — INSERT OR IGNORE handles duplicates.
    assignee_type cast to Int64 then safely converted by to_sqlite_rows.
    """
    print("\n  Loading companies...")
    path = os.path.join(CLEAN_DIR, 'clean_companies.csv')
    total = 0

    for chunk in pd.read_csv(path, dtype=str, chunksize=CHUNK_SIZE):
        chunk = chunk.drop_duplicates(subset='company_id')
        chunk['assignee_type'] = pd.to_numeric(
            chunk['assignee_type'], errors='coerce'
        ).astype('Int64')

        rows = to_sqlite_rows(chunk, ['company_id', 'name', 'assignee_type'])

        conn.executemany(
            """INSERT OR IGNORE INTO companies (company_id, name, assignee_type)
               VALUES (?, ?, ?)""",
            rows
        )
        conn.commit()
        total += len(rows)

        if total % 1_000_000 == 0:
            print(f"    ...{total:,} companies inserted")

    print(f"  Done — {total:,} company records loaded")


def load_relationships(conn):
    """
    Loads clean_relationships.csv into the relationships table.
    Indexes are dropped before bulk insert and rebuilt at the end —
    this is significantly faster than maintaining them row by row
    across 25M inserts.
    """
    print("\n  Loading relationships...")
    print("  Dropping indexes for faster bulk insert...")

    conn.executescript("""
        DROP INDEX IF EXISTS idx_rel_patent_id;
        DROP INDEX IF EXISTS idx_rel_inventor_id;
        DROP INDEX IF EXISTS idx_rel_company_id;
    """)

    path = os.path.join(CLEAN_DIR, 'clean_relationships.csv')
    total = 0

    for chunk in pd.read_csv(path, dtype=str, chunksize=CHUNK_SIZE):
        rows = to_sqlite_rows(chunk, ['patent_id', 'inventor_id', 'company_id'])

        conn.executemany(
            """INSERT INTO relationships (patent_id, inventor_id, company_id)
               VALUES (?, ?, ?)""",
            rows
        )
        conn.commit()
        total += len(rows)

        if total % 5_000_000 == 0:
            print(f"    ...{total:,} relationships inserted")

    print(f"  Done — {total:,} relationship records loaded")

    print("  Rebuilding relationship indexes...")
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_rel_patent_id   ON relationships(patent_id);
        CREATE INDEX IF NOT EXISTS idx_rel_inventor_id ON relationships(inventor_id);
        CREATE INDEX IF NOT EXISTS idx_rel_company_id  ON relationships(company_id);
    """)
    conn.commit()
    print("  Indexes rebuilt.")


def verify(conn):
    """
    Quick row count check after loading.
    Confirms the database matches what we loaded from the CSVs.
    """
    print("\n  Verifying row counts...")
    for table in ['patents', 'inventors', 'companies', 'relationships']:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"    {table}: {count:,} rows")


def main():
    print("=" * 60)
    print("  PatentsView Database Loader")
    print(f"  Database: {DB_PATH}")
    print("=" * 60)

    conn = get_connection()

    try:
        apply_schema(conn)
        load_patents(conn)
        load_inventors(conn)
        load_companies(conn)
        load_relationships(conn)
        verify(conn)
    finally:
        conn.close()

    print("\n" + "=" * 60)
    print("  Database loaded successfully.")
    print(f"  File: {DB_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
