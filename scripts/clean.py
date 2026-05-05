import csv
import os
import pandas as pd

RAW_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')
CLEAN_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'clean')
INTER_DIR = os.path.join(CLEAN_DIR, 'intermediate')

os.makedirs(CLEAN_DIR, exist_ok=True)
os.makedirs(INTER_DIR, exist_ok=True)

ENCODING = 'latin-1'
CHUNK_SIZE = 200_000

# USPTO was founded in 1836 — any filing date outside this range is a
# confirmed data entry error, seen in profiling: 1074, 1096, 1298 etc
MIN_YEAR = 1836
MAX_YEAR = 2025

# Confirmed valid patent types from full-file value distribution profiling
VALID_PATENT_TYPES = {
    'utility', 'design', 'plant', 'reissue',
    'statutory invention registration', 'defensive publication'
}


# =============================================================================
# SHARED HELPERS
# =============================================================================

def get_reader(filename, usecols=None, engine='c', quoting=0):
    """
    Returns a chunked pandas reader for a raw TSV file.
    All files use latin-1 encoding and skip bad lines — both confirmed
    necessary during profiling. The abstract file needs the python engine
    and QUOTE_NONE due to buffer overflow and unescaped quotes in text.
    """
    path = os.path.join(RAW_DIR, filename)
    return pd.read_csv(
        path,
        sep='\t',
        dtype=str,
        encoding=ENCODING,
        keep_default_na=True,
        on_bad_lines='skip',
        engine=engine,
        quoting=quoting,
        usecols=usecols,
        chunksize=CHUNK_SIZE
    )


def write_chunk(df, path, write_header):
    """
    Appends a cleaned chunk to a CSV file.
    Header is only written on the first chunk to avoid duplicate headers.
    """
    df.to_csv(path, mode='a', index=False, header=write_header)


# =============================================================================
# PHASE 1 — CLEAN EACH FILE INDEPENDENTLY IN CHUNKS, WRITE TO INTERMEDIATE
# =============================================================================

def phase1_g_patent():
    """
    Cleans g_patent.tsv chunk by chunk.

    What we do per chunk:
    - Keep only rows with a valid patent_type — this simultaneously removes
      the ~281 fully corrupt rows and the binary garbage values seen in profiling
    - Remove withdrawn patents (withdrawn = 1) — 19,433 confirmed in profiling
    - Parse and format grant date
    - Output: patent_id, patent_type, patent_title, patent_date
    """
    print("\n[Phase 1] Cleaning g_patent.tsv...")
    out_path = os.path.join(INTER_DIR, 'g_patent_clean.csv')

    if os.path.exists(out_path):
        os.remove(out_path)

    reader = get_reader(
        'g_patent.tsv',
        usecols=['patent_id', 'patent_type', 'patent_date', 'patent_title', 'withdrawn']
    )

    total_in = 0
    total_out = 0
    first_chunk = True

    for chunk in reader:
        total_in += len(chunk)

        # Drop corrupt rows by filtering on known valid patent types
        chunk = chunk[chunk['patent_type'].isin(VALID_PATENT_TYPES)].copy()

        # Drop withdrawn patents — confirmed 19,433 rows in profiling
        chunk = chunk[chunk['withdrawn'].astype(str).str.strip() == '0'].copy()
        chunk = chunk.drop(columns=['withdrawn'])

        # Parse grant date — had zero nulls in profiling
        chunk['patent_date'] = pd.to_datetime(
            chunk['patent_date'], errors='coerce'
        ).dt.strftime('%Y-%m-%d')

        chunk = chunk.drop_duplicates(subset='patent_id')
        write_chunk(chunk, out_path, write_header=first_chunk)
        total_out += len(chunk)
        first_chunk = False

    print(f"  {total_in:,} rows in -> {total_out:,} rows out")


def phase1_g_patent_abstract():
    """
    Cleans g_patent_abstract.tsv chunk by chunk.

    What we do per chunk:
    - Uses python engine + QUOTE_NONE — confirmed necessary in profiling
      due to buffer overflow on long abstracts and unescaped quotes in text
    - Column names come through with surrounding quotes e.g. '"patent_id"'
      because QUOTE_NONE reads the header literally — stripped on first chunk
    - 1,752,340 nulls (17.74%) in abstract — genuine absence in older patents,
      filled with empty string
    - Output: patent_id, patent_abstract
    """
    print("\n[Phase 1] Cleaning g_patent_abstract.tsv...")
    out_path = os.path.join(INTER_DIR, 'g_patent_abstract_clean.csv')

    if os.path.exists(out_path):
        os.remove(out_path)

    reader = get_reader(
        'g_patent_abstract.tsv',
        engine='python',
        quoting=csv.QUOTE_NONE
    )

    total_in = 0
    total_out = 0
    first_chunk = True

    for chunk in reader:
        total_in += len(chunk)

        # Strip surrounding quotes from column names — artifact of QUOTE_NONE
        # reading the quoted TSV header literally
        chunk.columns = [c.strip('"') for c in chunk.columns]

        # Some cell values also have surrounding quotes — strip those too
        for col in chunk.columns:
            if chunk[col].dtype == object:
                chunk[col] = chunk[col].str.strip('"')

        # 17.74% null abstracts are real absences in old records — empty string
        chunk['patent_abstract'] = chunk['patent_abstract'].fillna('')

        chunk = chunk[['patent_id', 'patent_abstract']].drop_duplicates(subset='patent_id')
        write_chunk(chunk, out_path, write_header=first_chunk)
        total_out += len(chunk)
        first_chunk = False

    print(f"  {total_in:,} rows in -> {total_out:,} rows out")


def phase1_g_application():
    """
    Cleans g_application.tsv chunk by chunk.

    What we do per chunk:
    - ~6,988 fully corrupt rows dropped via dropna on patent_id
    - Impossible filing years (1074, 1096, 1298 etc) confirmed in profiling —
      validated against MIN_YEAR/MAX_YEAR and nullified
    - Year extracted from filing_date for trend analysis (assignment Q4)
    - Output: patent_id, filing_date, year
    """
    print("\n[Phase 1] Cleaning g_application.tsv...")
    out_path = os.path.join(INTER_DIR, 'g_application_clean.csv')

    if os.path.exists(out_path):
        os.remove(out_path)

    reader = get_reader(
        'g_application.tsv',
        usecols=['patent_id', 'filing_date']
    )

    total_in = 0
    total_out = 0
    first_chunk = True

    for chunk in reader:
        total_in += len(chunk)

        # Drop the ~6,988 fully corrupt rows — patent_id is null in those
        chunk = chunk.dropna(subset=['patent_id']).copy()

        # Parse filing date and nullify impossible years
        chunk['filing_date'] = pd.to_datetime(chunk['filing_date'], errors='coerce')
        invalid = (
            chunk['filing_date'].notna() &
            (~chunk['filing_date'].dt.year.between(MIN_YEAR, MAX_YEAR))
        )
        chunk.loc[invalid, 'filing_date'] = pd.NaT

        # Extract year — kept as string for CSV, will cast in load step
        chunk['year'] = chunk['filing_date'].dt.year
        chunk['filing_date'] = chunk['filing_date'].dt.strftime('%Y-%m-%d')

        chunk = chunk.drop_duplicates(subset='patent_id')
        write_chunk(chunk, out_path, write_header=first_chunk)
        total_out += len(chunk)
        first_chunk = False

    print(f"  {total_in:,} rows in -> {total_out:,} rows out")


def phase1_g_inventor_disambiguated():
    """
    Cleans g_inventor_disambiguated.tsv chunk by chunk.

    What we do per chunk:
    - 24,037,380 rows — chunking is essential here
    - Drop 540 rows with null last name — nameless records have no value
    - Fill 684 null first names with '' — some inventors only have a last name
    - Build full name by combining first + last
    - Keep location_id for the merge with g_location in phase 2
    - Output: patent_id, inventor_id, name, location_id
    """
    print("\n[Phase 1] Cleaning g_inventor_disambiguated.tsv...")
    out_path = os.path.join(INTER_DIR, 'g_inventor_disambiguated_clean.csv')

    if os.path.exists(out_path):
        os.remove(out_path)

    reader = get_reader(
        'g_inventor_disambiguated.tsv',
        usecols=[
            'patent_id', 'inventor_id',
            'disambig_inventor_name_first',
            'disambig_inventor_name_last',
            'location_id'
        ]
    )

    total_in = 0
    total_out = 0
    first_chunk = True

    for chunk in reader:
        total_in += len(chunk)

        # Drop the 540 rows with no last name — confirmed in profiling
        chunk = chunk.dropna(subset=['disambig_inventor_name_last']).copy()

        # Fill null first names — 684 nulls confirmed, some inventors only
        # have a last name on record
        chunk['disambig_inventor_name_first'] = (
            chunk['disambig_inventor_name_first'].fillna('')
        )

        chunk['name'] = (
            chunk['disambig_inventor_name_first'] + ' ' +
            chunk['disambig_inventor_name_last']
        ).str.strip()

        chunk = chunk[['patent_id', 'inventor_id', 'name', 'location_id']]
        chunk = chunk.drop_duplicates()
        write_chunk(chunk, out_path, write_header=first_chunk)
        total_out += len(chunk)
        first_chunk = False

    print(f"  {total_in:,} rows in -> {total_out:,} rows out")


def phase1_g_assignee_disambiguated():
    """
    Cleans g_assignee_disambiguated.tsv chunk by chunk.

    What we do per chunk:
    - 8,747,138 rows — chunked
    - 98.18% have null individual name fields — organizations dominate
    - 87,333 rows have null org name — those are individual assignees
    - assignee_type is float64 due to 25,901 nulls — cast to Int64
    - One corrupt binary value in assignee_type handled by pd.to_numeric
    - Output: patent_id, company_id, name, assignee_type
    """
    print("\n[Phase 1] Cleaning g_assignee_disambiguated.tsv...")
    out_path = os.path.join(INTER_DIR, 'g_assignee_disambiguated_clean.csv')

    if os.path.exists(out_path):
        os.remove(out_path)

    reader = get_reader(
        'g_assignee_disambiguated.tsv',
        usecols=[
            'patent_id', 'assignee_id',
            'disambig_assignee_organization',
            'disambig_assignee_individual_name_first',
            'disambig_assignee_individual_name_last',
            'assignee_type'
        ]
    )

    total_in = 0
    total_out = 0
    first_chunk = True

    for chunk in reader:
        total_in += len(chunk)

        org = chunk['disambig_assignee_organization'].fillna('').str.strip()
        first = chunk['disambig_assignee_individual_name_first'].fillna('').str.strip()
        last = chunk['disambig_assignee_individual_name_last'].fillna('').str.strip()
        individual = (first + ' ' + last).str.strip()

        # Prefer org name — 98.18% of rows have one
        # Fall back to individual name for the remaining 1.82%
        chunk['name'] = org.where(org != '', individual)

        # Drop the small number of rows where neither could be resolved
        chunk = chunk[chunk['name'].notna() & (chunk['name'] != '')].copy()

        # assignee_type is float64 due to nulls — coerce handles the one
        # binary garbage value by turning it into NaN
        chunk['assignee_type'] = pd.to_numeric(
            chunk['assignee_type'], errors='coerce'
        ).astype('Int64')

        chunk = chunk.rename(columns={'assignee_id': 'company_id'})
        chunk = chunk[['patent_id', 'company_id', 'name', 'assignee_type']]
        chunk = chunk.drop_duplicates()
        write_chunk(chunk, out_path, write_header=first_chunk)
        total_out += len(chunk)
        first_chunk = False

    print(f"  {total_in:,} rows in -> {total_out:,} rows out")


def phase1_g_location_disambiguated():
    """
    Cleans g_location_disambiguated.tsv — loaded fully since it's only 9MB.

    What we do:
    - disambig_state: 68.16% null — expected for non-US locations, kept as-is
    - disambig_country: only 10 nulls in 99,369 rows — very reliable
    - county/state_fips/county_fips: US-only fields not needed for our analysis
    - Output: location_id, disambig_country (everything needed for country join)
    """
    print("\n[Phase 1] Cleaning g_location_disambiguated.tsv...")
    out_path = os.path.join(INTER_DIR, 'g_location_disambiguated_clean.csv')

    # At 9MB this is the only file safe to load fully in one shot
    path = os.path.join(RAW_DIR, 'g_location_disambiguated.tsv')
    df = pd.read_csv(
        path,
        sep='\t',
        dtype=str,
        encoding=ENCODING,
        keep_default_na=True,
        on_bad_lines='skip',
        usecols=['location_id', 'disambig_country']
    )

    print(f"  Loaded {len(df):,} rows")

    # Standardise country to uppercase for consistent grouping in SQL queries
    df['disambig_country'] = df['disambig_country'].str.upper().str.strip()

    df = df.drop_duplicates(subset='location_id')
    df.to_csv(out_path, index=False)
    print(f"  Saved {len(df):,} location records")


# =============================================================================
# PHASE 2 — MERGE CLEAN INTERMEDIATE FILES INTO FINAL OUTPUT TABLES
# =============================================================================

def phase2_build_patents():
    """
    Merges g_patent_clean + g_patent_abstract_clean + g_application_clean
    into the final clean_patents.csv.

    We merge in chunks of g_patent_clean against the two smaller files
    which are loaded fully — they're much smaller after phase 1 cleaning
    and column reduction. This keeps peak memory usage low.
    """
    print("\n[Phase 2] Building clean_patents.csv...")

    abstracts = pd.read_csv(
        os.path.join(INTER_DIR, 'g_patent_abstract_clean.csv'),
        dtype=str
    )
    applications = pd.read_csv(
        os.path.join(INTER_DIR, 'g_application_clean.csv'),
        dtype=str
    )

    out_path = os.path.join(CLEAN_DIR, 'clean_patents.csv')
    if os.path.exists(out_path):
        os.remove(out_path)

    reader = pd.read_csv(
        os.path.join(INTER_DIR, 'g_patent_clean.csv'),
        dtype=str,
        chunksize=CHUNK_SIZE
    )

    total = 0
    first_chunk = True

    for chunk in reader:
        # Merge abstract and filing date onto each chunk of patents
        chunk = chunk.merge(abstracts, on='patent_id', how='left')
        chunk = chunk.merge(applications, on='patent_id', how='left')

        chunk = chunk.rename(columns={
            'patent_title': 'title',
            'patent_abstract': 'abstract',
            'patent_date': 'grant_date'
        })

        chunk['abstract'] = chunk['abstract'].fillna('')
        chunk = chunk[[
            'patent_id', 'title', 'abstract',
            'filing_date', 'grant_date', 'year', 'patent_type'
        ]]
        chunk = chunk.drop_duplicates(subset='patent_id')
        write_chunk(chunk, out_path, write_header=first_chunk)
        total += len(chunk)
        first_chunk = False

    print(f"  Saved {total:,} patents -> clean_patents.csv")


def phase2_build_inventors():
    """
    Merges g_inventor_disambiguated_clean + g_location_disambiguated_clean
    into the final clean_inventors.csv.

    Location file is small (99K rows) so we load it fully and merge
    against chunks of the inventor file.
    """
    print("\n[Phase 2] Building clean_inventors.csv...")

    locations = pd.read_csv(
        os.path.join(INTER_DIR, 'g_location_disambiguated_clean.csv'),
        dtype=str
    )

    out_path = os.path.join(CLEAN_DIR, 'clean_inventors.csv')
    if os.path.exists(out_path):
        os.remove(out_path)

    reader = pd.read_csv(
        os.path.join(INTER_DIR, 'g_inventor_disambiguated_clean.csv'),
        dtype=str,
        chunksize=CHUNK_SIZE
    )

    total = 0
    first_chunk = True

    for chunk in reader:
        # Left join — inventors with no location_id (0.69%) keep their row
        # but their country becomes null, labelled UNKNOWN below
        chunk = chunk.merge(locations, on='location_id', how='left')

        chunk = chunk.rename(columns={'disambig_country': 'country'})
        chunk['country'] = chunk['country'].fillna('UNKNOWN').str.upper().str.strip()

        chunk = chunk[['patent_id', 'inventor_id', 'name', 'country']]
        chunk = chunk.drop_duplicates()
        write_chunk(chunk, out_path, write_header=first_chunk)
        total += len(chunk)
        first_chunk = False

    print(f"  Saved {total:,} inventor records -> clean_inventors.csv")


def phase2_build_companies():
    """
    Renames g_assignee_disambiguated_clean to clean_companies.csv.
    No further merging needed — all required columns are already present
    from phase 1.
    """
    print("\n[Phase 2] Building clean_companies.csv...")

    out_path = os.path.join(CLEAN_DIR, 'clean_companies.csv')
    if os.path.exists(out_path):
        os.remove(out_path)

    reader = pd.read_csv(
        os.path.join(INTER_DIR, 'g_assignee_disambiguated_clean.csv'),
        dtype=str,
        chunksize=CHUNK_SIZE
    )

    total = 0
    first_chunk = True

    for chunk in reader:
        chunk = chunk.drop_duplicates()
        write_chunk(chunk, out_path, write_header=first_chunk)
        total += len(chunk)
        first_chunk = False

    print(f"  Saved {total:,} company records -> clean_companies.csv")


def phase2_build_relationships():
    """
    Builds clean_relationships.csv by reading inventors and companies
    in chunks and extracting patent_id -> inventor_id and
    patent_id -> company_id links, then merging them.

    Both files are read fully here since after phase 1 cleaning they only
    carry the columns we need — much smaller than the raw source files.
    We deduplicate the links before the merge to keep the output manageable.
    """
    print("\n[Phase 2] Building clean_relationships.csv...")

    print("  Reading inventor links...")
    inv_links = pd.read_csv(
        os.path.join(CLEAN_DIR, 'clean_inventors.csv'),
        dtype=str,
        usecols=['patent_id', 'inventor_id']
    ).drop_duplicates()

    print("  Reading company links...")
    comp_links = pd.read_csv(
        os.path.join(CLEAN_DIR, 'clean_companies.csv'),
        dtype=str,
        usecols=['patent_id', 'company_id']
    ).drop_duplicates()

    print("  Merging...")
    relationships = inv_links.merge(comp_links, on='patent_id', how='outer')
    relationships = relationships.dropna(
        subset=['inventor_id', 'company_id'], how='all'
    )
    relationships = relationships.drop_duplicates()

    out_path = os.path.join(CLEAN_DIR, 'clean_relationships.csv')
    relationships.to_csv(out_path, index=False)
    print(f"  Saved {len(relationships):,} relationship records -> clean_relationships.csv")


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 60)
    print("  PatentsView Data Cleaner — Two-Phase Chunked Pipeline")
    print("=" * 60)

    print("\n===== PHASE 1: Clean each file independently =====")
    phase1_g_patent()
    phase1_g_patent_abstract()
    phase1_g_application()
    phase1_g_inventor_disambiguated()
    phase1_g_assignee_disambiguated()
    phase1_g_location_disambiguated()

    print("\n===== PHASE 2: Merge into final output tables =====")
    phase2_build_patents()
    phase2_build_inventors()
    phase2_build_companies()
    phase2_build_relationships()

    print("\n" + "=" * 60)
    print("  Done. Final files saved to data/clean/")
    print("  Intermediate files saved to data/clean/intermediate/")
    print("=" * 60)


if __name__ == "__main__":
    main()
