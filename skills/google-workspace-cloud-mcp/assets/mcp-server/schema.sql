-- ===========================================================================
-- Google Workspace Cloud MCP — knowledge base schema (Cloudflare D1 / SQLite)
-- ===========================================================================
--
-- Design constraints that shaped this schema:
--
--   1. D1 bills "rows read" as rows SCANNED, not rows returned. A query that
--      filters on an unindexed column scans the whole table and burns the
--      daily quota fast. Every column that appears in a WHERE or ORDER BY of
--      a shipped query has an index below. If you add a query, add its index.
--
--   2. The MCP server is stateless — it holds no memory between requests. All
--      continuity (sync cursors, OAuth grants, flag state) lives here.
--
--   3. Storage is metadata-only by deliberate choice. No message bodies, no
--      file contents, no attachments. That keeps the whole org's history
--      inside the 5 GB free tier for years and means a KB leak exposes
--      "who talked to whom when," never the substance.
--
--   4. Raw event tables are prunable; rollups are permanent. Detail ages out,
--      trend lines never do.
--
-- Apply with:  wrangler d1 execute <DB> --remote --file=schema.sql
-- ===========================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- people — the roster, refreshed from Admin Directory each harvest
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS people (
    email           TEXT PRIMARY KEY,
    full_name       TEXT,
    given_name      TEXT,
    org_unit        TEXT,
    title           TEXT,
    is_admin        INTEGER NOT NULL DEFAULT 0,
    suspended       INTEGER NOT NULL DEFAULT 0,
    last_login_ts   TEXT,
    created_ts      TEXT,
    first_seen      TEXT NOT NULL,
    last_seen       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_people_active   ON people(suspended, email);
CREATE INDEX IF NOT EXISTS idx_people_org      ON people(org_unit);
CREATE INDEX IF NOT EXISTS idx_people_login    ON people(last_login_ts);

-- ---------------------------------------------------------------------------
-- counterparties — external people/orgs we exchange mail with
-- Derived, not harvested. Lets you ask "who at DISD have we gone quiet on"
-- without scanning comm_events.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS counterparties (
    address         TEXT PRIMARY KEY,
    domain          TEXT NOT NULL,
    display_name    TEXT,
    is_internal     INTEGER NOT NULL DEFAULT 0,
    first_contact   TEXT NOT NULL,
    last_contact    TEXT NOT NULL,
    msg_count       INTEGER NOT NULL DEFAULT 0,
    inbound_count   INTEGER NOT NULL DEFAULT 0,
    outbound_count  INTEGER NOT NULL DEFAULT 0,
    project_id      TEXT REFERENCES projects(project_id)
);
CREATE INDEX IF NOT EXISTS idx_cp_domain  ON counterparties(domain, last_contact);
CREATE INDEX IF NOT EXISTS idx_cp_last    ON counterparties(last_contact);
CREATE INDEX IF NOT EXISTS idx_cp_project ON counterparties(project_id, last_contact);

-- ---------------------------------------------------------------------------
-- projects — the tagging spine. Everything else joins back to here.
-- Matched by Drive folder id, email domain, or subject/keyword regex.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    project_id      TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active',
    drive_folder_id TEXT,
    match_domains   TEXT,          -- JSON array: ["dallasisd.org"]
    match_keywords  TEXT,          -- JSON array: ["McShan","JOC-2231"]
    owner_email     TEXT,
    contract_value  REAL,
    created_ts      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_proj_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_proj_folder ON projects(drive_folder_id);

-- ---------------------------------------------------------------------------
-- comm_events — email metadata, one row per message per mailbox
-- METADATA ONLY. subject is kept because it is the single highest-signal
-- field for project tagging and risk detection; bodies never are.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS comm_events (
    id              TEXT PRIMARY KEY,       -- {person}:{gmail_message_id}
    ts              TEXT NOT NULL,          -- ISO-8601 UTC
    person          TEXT NOT NULL,          -- whose mailbox this row came from
    direction       TEXT NOT NULL,          -- inbound | outbound
    counterparty    TEXT,                   -- primary other party
    cp_domain       TEXT,
    is_external     INTEGER NOT NULL DEFAULT 0,
    subject         TEXT,
    thread_id       TEXT,
    recipient_count INTEGER NOT NULL DEFAULT 1,
    has_attachment  INTEGER NOT NULL DEFAULT 0,
    labels          TEXT,                   -- JSON array
    project_id      TEXT,
    risk_score      INTEGER NOT NULL DEFAULT 0,
    harvested_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_comm_person_ts  ON comm_events(person, ts DESC);
CREATE INDEX IF NOT EXISTS idx_comm_ts         ON comm_events(ts DESC);
CREATE INDEX IF NOT EXISTS idx_comm_thread     ON comm_events(thread_id, ts);
CREATE INDEX IF NOT EXISTS idx_comm_cp         ON comm_events(counterparty, ts DESC);
CREATE INDEX IF NOT EXISTS idx_comm_domain     ON comm_events(cp_domain, ts DESC);
CREATE INDEX IF NOT EXISTS idx_comm_project    ON comm_events(project_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_comm_risk       ON comm_events(risk_score, ts DESC) WHERE risk_score > 0;
CREATE INDEX IF NOT EXISTS idx_comm_ext        ON comm_events(is_external, ts DESC);

-- ---------------------------------------------------------------------------
-- threads — rolled-up conversation state. This is what makes
-- "what inbound has nobody answered" a 1-index lookup instead of a scan.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS threads (
    thread_id       TEXT PRIMARY KEY,
    subject         TEXT,
    project_id      TEXT,
    first_ts        TEXT NOT NULL,
    last_ts         TEXT NOT NULL,
    last_direction  TEXT,                   -- inbound | outbound
    last_inbound_ts TEXT,
    last_outbound_ts TEXT,
    msg_count       INTEGER NOT NULL DEFAULT 0,
    participants    TEXT,                   -- JSON array
    is_external     INTEGER NOT NULL DEFAULT 0,
    awaiting_reply  INTEGER NOT NULL DEFAULT 0,  -- 1 = inbound with no reply since
    max_risk        INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_thr_await   ON threads(awaiting_reply, last_inbound_ts) WHERE awaiting_reply = 1;
CREATE INDEX IF NOT EXISTS idx_thr_project ON threads(project_id, last_ts DESC);
CREATE INDEX IF NOT EXISTS idx_thr_last    ON threads(last_ts DESC);
CREATE INDEX IF NOT EXISTS idx_thr_risk    ON threads(max_risk, last_ts DESC) WHERE max_risk > 0;

-- ---------------------------------------------------------------------------
-- calendar_events — meetings, one row per event per calendar
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS calendar_events (
    id              TEXT PRIMARY KEY,       -- {person}:{event_id}
    event_id        TEXT NOT NULL,
    person          TEXT NOT NULL,
    ts_start        TEXT NOT NULL,
    ts_end          TEXT,
    duration_min    INTEGER,
    title           TEXT,
    organizer       TEXT,
    is_organizer    INTEGER NOT NULL DEFAULT 0,
    location        TEXT,
    attendee_count  INTEGER NOT NULL DEFAULT 0,
    external_count  INTEGER NOT NULL DEFAULT 0,
    response_status TEXT,                   -- accepted|declined|tentative|needsAction
    status          TEXT,                   -- confirmed|cancelled
    recurring_id    TEXT,
    project_id      TEXT,
    harvested_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cal_person_ts ON calendar_events(person, ts_start DESC);
CREATE INDEX IF NOT EXISTS idx_cal_ts        ON calendar_events(ts_start DESC);
CREATE INDEX IF NOT EXISTS idx_cal_project   ON calendar_events(project_id, ts_start DESC);
CREATE INDEX IF NOT EXISTS idx_cal_resp      ON calendar_events(response_status, ts_start DESC);
CREATE INDEX IF NOT EXISTS idx_cal_event     ON calendar_events(event_id);

-- ---------------------------------------------------------------------------
-- drive_events — file and folder activity, sourced from the Drive Changes API
-- This is the "changes to project folders" stream, the highest-value signal
-- for catching a sub uploading a revised submittal or someone sharing a
-- bid folder outside the company.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS drive_events (
    id              TEXT PRIMARY KEY,       -- {person}:{file_id}:{change_ts}
    ts              TEXT NOT NULL,
    person          TEXT NOT NULL,          -- whose drive surfaced the change
    actor           TEXT,                   -- last modifying user
    file_id         TEXT NOT NULL,
    file_name       TEXT,
    mime_type       TEXT,
    action          TEXT NOT NULL,          -- created|modified|trashed|shared|permission_change
    parent_id       TEXT,
    parent_name     TEXT,
    path_hint       TEXT,
    shared_external INTEGER NOT NULL DEFAULT 0,
    size_bytes      INTEGER,
    project_id      TEXT,
    risk_score      INTEGER NOT NULL DEFAULT 0,
    harvested_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_drv_person_ts ON drive_events(person, ts DESC);
CREATE INDEX IF NOT EXISTS idx_drv_ts        ON drive_events(ts DESC);
CREATE INDEX IF NOT EXISTS idx_drv_parent    ON drive_events(parent_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_drv_project   ON drive_events(project_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_drv_file      ON drive_events(file_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_drv_ext       ON drive_events(shared_external, ts DESC) WHERE shared_external = 1;
CREATE INDEX IF NOT EXISTS idx_drv_risk      ON drive_events(risk_score, ts DESC) WHERE risk_score > 0;

-- ---------------------------------------------------------------------------
-- flags — detected signals and their lifecycle
-- Replaces the old Google Sheet issue store. Same idea, real queries.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS flags (
    flag_id         TEXT PRIMARY KEY,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    rule            TEXT NOT NULL,          -- which detector fired
    status          TEXT NOT NULL DEFAULT 'open',   -- open|acknowledged|resolved|dismissed
    severity        TEXT NOT NULL DEFAULT 'medium', -- low|medium|high|critical
    person          TEXT,
    project_id      TEXT,
    title           TEXT NOT NULL,
    detail          TEXT,
    evidence        TEXT,                   -- JSON: ids of the rows that triggered it
    dedupe_key      TEXT NOT NULL,          -- rule+person+window; stops re-flagging
    first_seen      TEXT NOT NULL,
    occurrences     INTEGER NOT NULL DEFAULT 1,
    resolved_at     TEXT,
    resolved_by     TEXT,
    note            TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_flag_dedupe ON flags(dedupe_key);
CREATE INDEX IF NOT EXISTS idx_flag_status  ON flags(status, severity, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_flag_person  ON flags(person, status);
CREATE INDEX IF NOT EXISTS idx_flag_project ON flags(project_id, status);
CREATE INDEX IF NOT EXISTS idx_flag_rule    ON flags(rule, created_at DESC);

-- ---------------------------------------------------------------------------
-- flag_events — append-only audit trail of every status transition
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS flag_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    flag_id         TEXT NOT NULL REFERENCES flags(flag_id) ON DELETE CASCADE,
    ts              TEXT NOT NULL,
    actor           TEXT NOT NULL,
    from_status     TEXT,
    to_status       TEXT,
    note            TEXT
);
CREATE INDEX IF NOT EXISTS idx_flagev_flag ON flag_events(flag_id, ts);

-- ---------------------------------------------------------------------------
-- rollups_daily — permanent per-person-per-day aggregates
-- Raw events get pruned; these never do. Every trend question answers from
-- here, which keeps rows-scanned tiny (one row per person per day).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rollups_daily (
    day             TEXT NOT NULL,          -- YYYY-MM-DD
    person          TEXT NOT NULL,
    emails_sent     INTEGER NOT NULL DEFAULT 0,
    emails_received INTEGER NOT NULL DEFAULT 0,
    external_in     INTEGER NOT NULL DEFAULT 0,
    external_out    INTEGER NOT NULL DEFAULT 0,
    threads_touched INTEGER NOT NULL DEFAULT 0,
    meetings        INTEGER NOT NULL DEFAULT 0,
    meeting_minutes INTEGER NOT NULL DEFAULT 0,
    drive_creates   INTEGER NOT NULL DEFAULT 0,
    drive_edits     INTEGER NOT NULL DEFAULT 0,
    drive_shares    INTEGER NOT NULL DEFAULT 0,
    first_activity  TEXT,
    last_activity   TEXT,
    active          INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (day, person)
);
CREATE INDEX IF NOT EXISTS idx_roll_person ON rollups_daily(person, day DESC);
CREATE INDEX IF NOT EXISTS idx_roll_day    ON rollups_daily(day DESC);

-- ---------------------------------------------------------------------------
-- sync_state — incremental cursors. The reason a harvest costs seconds,
-- not minutes: Gmail historyId and Drive pageToken mean we only ever ask
-- Google for what changed since last time.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sync_state (
    source          TEXT NOT NULL,          -- gmail|drive|calendar|directory
    scope           TEXT NOT NULL,          -- usually the user email
    cursor          TEXT,
    last_run        TEXT,
    last_ok         TEXT,
    last_error      TEXT,
    items_seen      INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (source, scope)
);

-- ---------------------------------------------------------------------------
-- Convenience views — keep hot questions off the raw tables
-- ---------------------------------------------------------------------------

-- Inbound external mail nobody has replied to.
CREATE VIEW IF NOT EXISTS v_awaiting_reply AS
SELECT t.thread_id, t.subject, t.project_id, t.last_inbound_ts,
       t.participants, t.max_risk,
       CAST((julianday('now') - julianday(t.last_inbound_ts)) * 24 AS INTEGER) AS hours_waiting
FROM threads t
WHERE t.awaiting_reply = 1 AND t.is_external = 1;

-- Everyone's most recent day of recorded activity.
CREATE VIEW IF NOT EXISTS v_last_activity AS
SELECT p.email, p.full_name, p.org_unit, p.suspended,
       MAX(r.day) AS last_active_day,
       CAST(julianday('now') - julianday(MAX(r.day)) AS INTEGER) AS days_quiet
FROM people p
LEFT JOIN rollups_daily r ON r.person = p.email AND r.active = 1
WHERE p.suspended = 0
GROUP BY p.email;

-- The open flag queue, worst first.
CREATE VIEW IF NOT EXISTS v_open_flags AS
SELECT flag_id, created_at, updated_at, rule, severity, person, project_id,
       title, detail, occurrences
FROM flags
WHERE status IN ('open', 'acknowledged')
ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                       WHEN 'medium' THEN 2 ELSE 3 END,
         updated_at DESC;
