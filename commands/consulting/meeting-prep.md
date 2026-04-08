Prepare for a TIPS consulting meeting with a potential vendor or public entity member.

Given the entity name in `$ARGUMENTS`, run an exhaustive data gathering and analysis workflow to produce two deliverables:

1. **Pitch Deck (.pptx)** — a team-presentable PowerPoint slide deck explaining why TIPS can help this entity
2. **Background Intelligence Report (.docx)** — an executive-ready Word document grading the entity on their likelihood of being a high-value target TIPS could quickly help

## Workflow

1. **Identify** the entity: determine if vendor or member, pull CRM records (HubSpot), web research
2. **Financial profile**: revenue/budget, TIPS history, purchasing volume, growth trends
3. **Contracts & procurement**: existing contracts, state purchasing rules, compliance status
4. **Relationship history**: CRM interactions, past deals, support history, key contacts
5. **Budgets & spending**: current FY budgets by category, capital plans, grant funding
6. **Challenges & opportunities**: top 5 each, specific to this entity
7. **Shared vendors/members**: overlap analysis and cross-sell opportunities
8. **Competitive intel**: competing cooperatives, win/loss, TIPS advantages

## Data Sources (use in order)

- HubSpot CRM (contacts, companies, deals)
- Connected databases (SQL queries)
- Google Sheets (tracking data)
- Web search (public records, budgets, news)
- Gmail (recent correspondence)
- Google Calendar (meeting history)
- Google Drive (existing reports)

## Output

Install `python-pptx` and `python-docx` via pip, then generate and save these files to the current directory:

### Downloadable Files (team-presentable):
- `pitch-deck-<entity-slug>.pptx` — PowerPoint slide deck (16:9, branded, Calibri fonts, navy/blue theme)
- `background-report-<entity-slug>.docx` — Word report (cover page, TOC, branded headings, score table, 10 sections)

### Markdown Reference Copies:
- `pitch-deck-<entity-slug>.md` — slide content in Markdown
- `background-report-<entity-slug>.md` — full report in Markdown

**Note**: `<entity-slug>` is a sanitized entity name (lowercase, alphanumeric + hyphens only, spaces/special chars replaced with `-`, path separators stripped).

### Scoring Categories (each 0-20 points):

| Category | What it measures |
|----------|-----------------|
| Purchasing Volume Potential | Budget size, growth, capital plans |
| Speed to Close | Procurement rules, decision-maker access, urgency |
| Relationship Strength | CRM history, engagement, champion presence |
| Strategic Fit | Alignment with TIPS contract portfolio |
| Competitive Position | Competitor presence, switching costs, TIPS advantages |


## Rules

- Cite data sources for every claim
- Label estimates vs. confirmed data clearly
- Never fabricate financial figures — mark gaps as "Not Available"
- Flag stale data (>12 months old) with freshness warnings
- Confirm entity name with user if ambiguous before proceeding
