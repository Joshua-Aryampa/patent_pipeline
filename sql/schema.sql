-- PatentsView Database Schema
-- SQLite — all tables follow the assignment specification exactly

-- Drop tables if they exist so the script is safe to re-run
DROP TABLE IF EXISTS relationships;
DROP TABLE IF EXISTS inventors;
DROP TABLE IF EXISTS companies;
DROP TABLE IF EXISTS patents;

-- Core patents table
-- year is stored as INTEGER for efficient trend queries (Q4)
-- filing_date and grant_date stored as TEXT in ISO format YYYY-MM-DD
-- SQLite has no native DATE type but sorts ISO strings correctly
CREATE TABLE patents (
    patent_id       TEXT PRIMARY KEY,
    title           TEXT,
    abstract        TEXT,
    filing_date     TEXT,
    grant_date      TEXT,
    year            INTEGER,
    patent_type     TEXT
);

-- Inventors table
-- country is the disambiguated country code (e.g. US, CN, DE)
-- inventor_id is the disambiguated ID from PatentsView
CREATE TABLE inventors (
    inventor_id     TEXT PRIMARY KEY,
    name            TEXT,
    country         TEXT
);

-- Companies (assignees) table
-- company_id is the disambiguated assignee ID from PatentsView
-- assignee_type codes: 2=US Corp, 3=Foreign Corp, 4=US Individual etc
CREATE TABLE companies (
    company_id      TEXT PRIMARY KEY,
    name            TEXT,
    assignee_type   INTEGER
);

-- Relationships table — links patents to inventors and companies
-- This is effectively a junction table enabling the JOIN queries
-- Both inventor_id and company_id can be NULL (unassigned patents)
CREATE TABLE relationships (
    patent_id       TEXT,
    inventor_id     TEXT,
    company_id      TEXT,
    FOREIGN KEY (patent_id)   REFERENCES patents(patent_id),
    FOREIGN KEY (inventor_id) REFERENCES inventors(inventor_id),
    FOREIGN KEY (company_id)  REFERENCES companies(company_id)
);

-- Indexes on columns used heavily in WHERE clauses and JOINs
-- Without these, queries on 25M+ row tables would be extremely slow
CREATE INDEX IF NOT EXISTS idx_patents_year        ON patents(year);
CREATE INDEX IF NOT EXISTS idx_patents_type        ON patents(patent_type);
CREATE INDEX IF NOT EXISTS idx_inventors_country   ON inventors(country);
CREATE INDEX IF NOT EXISTS idx_inventors_name      ON inventors(name);
CREATE INDEX IF NOT EXISTS idx_companies_name      ON companies(name);
CREATE INDEX IF NOT EXISTS idx_rel_patent_id       ON relationships(patent_id);
CREATE INDEX IF NOT EXISTS idx_rel_inventor_id     ON relationships(inventor_id);
CREATE INDEX IF NOT EXISTS idx_rel_company_id      ON relationships(company_id);
