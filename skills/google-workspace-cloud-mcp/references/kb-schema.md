# Knowledge base schema and query cookbook

Read this before writing `kb_sql`. It is the difference between a query that
answers in 40ms and one that eats a fifth of the daily read budget.

**Contents**

1. [The one rule that matters](#the-one-rule-that-matters)
2. [Tables](#tables)
3. [Views](#views)
4. [Query cookbook](#query-cookbook)
5. [Detection rules](#detection-rules)
6. [Retention](#retention)

---

## The one rule that matters

D1 bills **rows scanned**, not rows returned, against 5M/day. So:

```sql
-- 300,000 rows scanned. Sixteen of these and the day is over.
SELECT * FROM comm_events WHERE subject LIKE '%pay app%';

-- ~40 rows scanned. Same answer, from the pre-aggregated table.
SELECT * FROM threads WHERE last_ts >= date('now','-30 day')
  AND subject LIKE '%pay app%';
```

Practical guidance:

- **Always bound by time.** `ts`, `ts_start`, and `day` are indexed everywhere.
- **Prefer `threads` over `comm_events`** for anything subject-shaped. Threads
  carry the same text at a few percent of the row count.
- **Prefer `rollups_daily` over raw events** for anything trend-shaped. One row
  per person per day rather than hundreds.
- **Never `LIKE` an unindexed column without a date filter.**

---

## Tables

### `people` — the roster
`email` (PK), `full_name`, `given_name`, `org_unit`, `title`, `is_admin`,
`suspended`, `last_login_ts`, `created_ts`, `first_seen`, `last_seen`

Refreshed from Admin Directory every harvest. `suspended = 0` is the definition
of "active" used throughout.

### `comm_events` — email metadata, one row per message per mailbox
`id` (PK, `{person}:{gmail_id}`), `ts`, `person`, `direction`
(`inbound`/`outbound`), `counterparty`, `cp_domain`, `is_external`, `subject`,
`thread_id`, `recipient_count`, `has_attachment`, `labels`, `project_id`,
`risk_score` (0-3), `harvested_at`

Metadata only — **no message bodies are ever stored**. Subject lines are kept
because they carry most of the routing and risk signal. To read an actual body,
call the live `gmail_get_message` tool.

`person` is whose mailbox produced the row, so an internal email between two
staff correctly appears twice: once outbound, once inbound.

### `threads` — rolled-up conversation state
`thread_id` (PK), `subject`, `project_id`, `first_ts`, `last_ts`,
`last_direction`, `last_inbound_ts`, `last_outbound_ts`, `msg_count`,
`participants` (JSON), `is_external`, `awaiting_reply`, `max_risk`

`awaiting_reply = 1` means the newest message is inbound with no outbound since.
Precomputed by the harvester because the on-demand version is a self-join across
the whole message history.

### `calendar_events` — meetings
`id` (PK, `{person}:{event_id}`), `event_id`, `person`, `ts_start`, `ts_end`,
`duration_min`, `title`, `organizer`, `is_organizer`, `location`,
`attendee_count`, `external_count`, `response_status`, `status`, `recurring_id`,
`project_id`

One row per attendee-mailbox, so a six-person meeting is six rows. Use
`COUNT(DISTINCT event_id)` when counting meetings org-wide.

### `drive_events` — file and folder activity
`id` (PK), `ts`, `person`, `actor`, `file_id`, `file_name`, `mime_type`,
`action` (`created`/`modified`/`trashed`), `parent_id`, `parent_name`,
`shared_external`, `size_bytes`, `project_id`, `risk_score`

Sourced from the Drive **Changes API**, so it is a true change feed rather than
a snapshot. `parent_id` is what ties activity to a project folder.

### `counterparties` — external contacts, derived
`address` (PK), `domain`, `display_name`, `is_internal`, `first_contact`,
`last_contact`, `msg_count`, `inbound_count`, `outbound_count`, `project_id`

### `projects` — the tagging spine
`project_id` (PK), `name`, `status`, `drive_folder_id`, `match_domains` (JSON),
`match_keywords` (JSON), `owner_email`, `contract_value`, `created_ts`

Matching precedence: Drive folder → counterparty domain → subject keyword.

### `flags` / `flag_events` — detected signals and their audit trail
`flags`: `flag_id` (PK), `created_at`, `updated_at`, `rule`, `status`,
`severity`, `person`, `project_id`, `title`, `detail`, `evidence` (JSON),
`dedupe_key` (unique), `first_seen`, `occurrences`, `resolved_at`,
`resolved_by`, `note`

`flag_events` records every status transition with actor and timestamp.
Nothing deletes from it.

### `rollups_daily` — permanent aggregates
PK (`day`, `person`). `emails_sent`, `emails_received`, `external_in`,
`external_out`, `threads_touched`, `meetings`, `meeting_minutes`,
`drive_creates`, `drive_edits`, `drive_shares`, `first_activity`,
`last_activity`, `active`

Survives pruning forever. All long-range trend questions belong here.

### `sync_state` — harvest cursors
PK (`source`, `scope`). `cursor`, `last_run`, `last_ok`, `last_error`,
`items_seen`. Query this first when data looks stale.

---

## Views

| View | Gives you |
|---|---|
| `v_awaiting_reply` | External inbound with no reply, plus `hours_waiting` |
| `v_last_activity` | Every active person with `days_quiet` |
| `v_open_flags` | Open/acknowledged flags, worst severity first |

---

## Query cookbook

**What is waiting on us right now**
```sql
SELECT subject, project_id, hours_waiting, participants
FROM v_awaiting_reply ORDER BY hours_waiting DESC LIMIT 25;
```

**Everything that touched a project this week**
```sql
SELECT 'email' src, ts, person, subject detail FROM comm_events
  WHERE project_id='mcshan' AND ts >= date('now','-7 day')
UNION ALL
SELECT 'file', ts, actor, file_name FROM drive_events
  WHERE project_id='mcshan' AND ts >= date('now','-7 day')
UNION ALL
SELECT 'meeting', ts_start, organizer, title FROM calendar_events
  WHERE project_id='mcshan' AND ts_start >= date('now','-7 day')
ORDER BY ts DESC;
```

**Whose workload is climbing**
```sql
SELECT person,
       SUM(CASE WHEN day >= date('now','-7 day')  THEN emails_sent END) this_week,
       SUM(CASE WHEN day <  date('now','-7 day')
                AND day >= date('now','-14 day')  THEN emails_sent END) last_week
FROM rollups_daily WHERE day >= date('now','-14 day')
GROUP BY person ORDER BY this_week DESC;
```

**External parties who have gone quiet**
```sql
SELECT address, domain, last_contact, msg_count
FROM counterparties
WHERE is_internal = 0 AND last_contact < date('now','-21 day') AND msg_count >= 5
ORDER BY msg_count DESC;
```

**Everything shared outside the company this month**
```sql
SELECT ts, actor, file_name, project_id FROM drive_events
WHERE shared_external = 1 AND ts >= date('now','-30 day') ORDER BY ts DESC;
```

**Meeting load per person, last 30 days**
```sql
SELECT person, COUNT(DISTINCT event_id) meetings,
       ROUND(SUM(duration_min)/60.0,1) hours
FROM calendar_events
WHERE ts_start >= date('now','-30 day') AND status != 'cancelled'
GROUP BY person ORDER BY hours DESC;
```

**Response latency to a specific owner**
```sql
SELECT t.subject, t.last_inbound_ts, t.last_outbound_ts,
       ROUND((julianday(t.last_outbound_ts)-julianday(t.last_inbound_ts))*24,1) hours_to_reply
FROM threads t
WHERE t.participants LIKE '%@dallasisd.org%'
  AND t.last_outbound_ts > t.last_inbound_ts
  AND t.last_ts >= date('now','-60 day')
ORDER BY hours_to_reply DESC;
```

**Is the harvester healthy**
```sql
SELECT source, COUNT(*) scopes, MAX(last_ok) newest_success,
       SUM(last_error IS NOT NULL) failing
FROM sync_state GROUP BY source;
```

---

## Detection rules

Each runs every harvest and deduplicates on a key, so a persistent problem is
one row with a rising `occurrences` count rather than a new row per day.

| Rule | Fires when | Default | Severity |
|---|---|---|---|
| `unanswered_inbound` | External inbound with no reply | 48h | med → high at 2× |
| `escalation_language` | Contractual/dispute wording in a live subject | risk ≥ 2 | high |
| `external_share` | File shared outside the domain | any | high |
| `mass_delete` | Files trashed by one person in 24h | 20 | high → critical at 3× |
| `activity_gap` | No email, calendar, or Drive activity | 3 days | med → high at 2× |
| `login_absence` | No Workspace sign-in | 5 days | medium |
| `stale_project` | Active project with no traffic | 14 days | medium |
| `new_external_domain` | New domain in regular contact | 3 msgs/14d | low |

Every threshold is an environment variable (`T_REPLY_HOURS`,
`T_ACTIVITY_GAP_DAYS`, …). Tune them early: a rule that fires on normal
behaviour teaches everyone to ignore the queue, which costs more than the rule
was worth.

Escalation vocabulary lives in `ESCALATION_TERMS` in `harvester.py` and is
tuned for construction — notice of, cure, default, backcharge, liquidated
damages, lien, stop work, time impact. Edit it to match how your counterparties
actually write.

---

## Retention

Raw `comm_events`, `drive_events`, and `calendar_events` are pruned after
`KB_RETAIN_DAYS` (default 400). `rollups_daily`, `flags`, `flag_events`,
`people`, `projects`, and `counterparties` are never pruned.

The effect: full detail for the last ~13 months, and permanent trend history
before that. At small-company size this keeps the database around 1-2% of the 5 GB
free tier.
