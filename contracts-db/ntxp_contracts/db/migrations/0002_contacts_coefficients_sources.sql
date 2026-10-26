-- NTXP Master Contracts — migration 0002
-- Adds what a contract record needs beyond the log row: award status and
-- pricebook, coefficient tiers (normal / non-normal hours, per region), named
-- contacts, and the evidence each fact came from. Also widens the jobs cache so
-- a job can carry its number, dates, payments and why it was linked to a contract.

ALTER TABLE contracts ADD COLUMN status TEXT;       -- awarded|tentative|pending-execution|expired|lost|unknown
ALTER TABLE contracts ADD COLUMN pricebook TEXT;    -- RSMeans | Gordian ezIQC | BNI | ...

-- Coefficient tiers. contracts.coefficient_multiplier stays the primary
-- (normal-hours) value the log shows; this table holds every published tier.
CREATE TABLE contract_coefficients (
    coefficient_id  INTEGER PRIMARY KEY,
    contract_id     INTEGER NOT NULL REFERENCES contracts(contract_id),
    label           TEXT NOT NULL,                  -- "Normal hours", "Non-normal hours", "Region 10 – normal"
    value           REAL NOT NULL,
    UNIQUE (contract_id, label)
);

-- People tied to a contract (procurement, contract admin, accounting, PM, ...).
-- Owned by a contract and/or an owner entity.
CREATE TABLE contacts (
    contact_id   INTEGER PRIMARY KEY,
    contract_id  INTEGER REFERENCES contracts(contract_id),
    owner_id     INTEGER REFERENCES owner_entities(owner_id),
    name         TEXT NOT NULL,
    title        TEXT,
    org          TEXT,
    role         TEXT,
    email        TEXT,
    phone        TEXT,                              -- E.164 when parseable
    source_url   TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX ix_contacts_contract ON contacts(contract_id);
CREATE INDEX ix_contacts_owner ON contacts(owner_id);

-- Where each contract fact came from: award letters, signed copies, emails,
-- public cooperative listings. Lets anyone re-verify a record.
CREATE TABLE contract_sources (
    source_id    INTEGER PRIMARY KEY,
    contract_id  INTEGER NOT NULL REFERENCES contracts(contract_id),
    what         TEXT NOT NULL,
    url          TEXT,
    added_at     TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (contract_id, what, url)
);
CREATE INDEX ix_sources_contract ON contract_sources(contract_id);

ALTER TABLE jobs ADD COLUMN job_number TEXT;
ALTER TABLE jobs ADD COLUMN location TEXT;
ALTER TABLE jobs ADD COLUMN paid_amount REAL;
ALTER TABLE jobs ADD COLUMN created_on TEXT;
ALTER TABLE jobs ADD COLUMN closed_on TEXT;
ALTER TABLE jobs ADD COLUMN link_confidence TEXT;   -- high|medium|low|none
ALTER TABLE jobs ADD COLUMN link_reason TEXT;
