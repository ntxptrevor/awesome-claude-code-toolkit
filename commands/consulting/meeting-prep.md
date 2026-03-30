Prepare for a TIPS consulting meeting with a potential vendor or public entity member.

Given the entity name in `$ARGUMENTS`, run an exhaustive data gathering and analysis workflow to produce two deliverables:

1. **Pitch Deck** — a slide-ready Markdown document explaining why TIPS can help this entity
2. **Background Intelligence Report** — a scored assessment grading the entity on their likelihood of being a high-value target TIPS could quickly help

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

Save two files to the current directory:
- `pitch-deck-<entity-name>.md` — structured slide deck
- `background-report-<entity-name>.md` — full intelligence report with High-Value Target Score (0-100%)

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
