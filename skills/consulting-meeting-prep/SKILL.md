---
name: consulting-meeting-prep
description: TIPS consulting meeting preparation - generates exhaustive entity research report and pitch deck for potential vendors or members
---

# TIPS Consulting Meeting Prep

When the user mentions an upcoming TIPS consulting meeting with a potential vendor or public entity member, run this full preparation workflow. The goal is to arm the consultant with deep intelligence on the entity and produce two polished deliverables.

## Trigger

Activate when the user mentions any of:
- A TIPS consulting meeting
- Meeting prep for a vendor or member
- `/consulting-meeting-prep <entity name>`

The `$ARGUMENTS` should contain the entity name (vendor company name or public entity / member name). If not provided, ask for it.

## Step 1 — Entity Identification & Classification

Determine whether the target is:

- **Vendor** — a company that sells products/services through TIPS or wants to
- **Member** — a public entity (school district, city, county, state agency, higher-ed institution, etc.) that purchases through TIPS or could

Gather the basics:
- Full legal name, HQ location, key contacts (if available in CRM)
- Entity type, size, sector
- TIPS membership or vendor status (active, lapsed, prospect)

Use all available data sources:
- HubSpot CRM (`search_crm_objects` for contacts, companies, deals)
- Google search / web research for public records
- Any connected databases or spreadsheets

## Step 2 — Revenue & Financial Profile

### For Vendors:
- Annual revenue (public filings, estimates)
- TIPS contract history — past and current contract values, sales volume through TIPS
- Product/service categories on TIPS
- Comparison to peer vendors in same category
- Growth trajectory (revenue trend if available)

### For Members:
- Annual operating budget and fund balances (from public budget documents, CAFRs)
- Historical purchasing volume through TIPS
- Purchasing volume through competing cooperatives (Sourcewell, OMNIA, BuyBoard, etc.)
- Bond elections, capital improvement plans, recent RFPs
- Grant funding received (ESSER, ARPA, state grants, etc.)

## Step 3 — Contracts & Purchasing Rules

### For Vendors:
- Current TIPS contract number(s), expiration dates, awarded categories
- Contract utilization rate (% of available capacity being used)
- Compliance status (insurance, reporting, fees current)
- Other cooperative contracts held (Sourcewell, OMNIA, BuyBoard, E&I, NCPA)

### For Members:
- State procurement thresholds and rules for the entity's state
- Board-approved cooperative purchasing policies
- Existing interlocal agreements or cooperative memberships
- Procurement staff and decision-makers (purchasing director, CFO, superintendent/city manager)

## Step 4 — Relationship & History

- All past interactions logged in CRM (calls, emails, meetings, notes)
- Previous deals — won, lost, in-pipeline
- Support tickets or complaints
- Key relationship owner(s) at TIPS
- NPS or satisfaction signals if available
- Conference attendance, webinar participation, event history

## Step 5 — Current Budgets & Spending Analysis

### For Members:
- Current fiscal year budget by major category (facilities, technology, transportation, food service, etc.)
- Capital project pipeline (bonds passed, projects in design/construction)
- Deferred maintenance estimates
- Technology refresh cycles
- Fleet replacement schedules

### For Vendors:
- Marketing/co-op advertising budget allocated to cooperatives
- Sales team size dedicated to cooperative channel
- Current promotional programs or rebate structures

## Step 6 — Challenges & Opportunities

Identify the top 5 challenges the entity likely faces:
- Budget constraints, enrollment/population trends, staffing shortages
- Regulatory changes, compliance requirements
- Supply chain issues, price escalation
- Technology modernization needs
- Competitive pressure (for vendors)

Identify the top 5 opportunities for TIPS:
- Unmet purchasing needs in categories TIPS covers
- Expiring competitor contracts
- New construction or renovation projects
- Grant-funded purchasing windows
- Product/service gaps TIPS vendors could fill

## Step 7 — Shared Vendor / Member Overlap

- For a **member**: list TIPS vendors already doing business with them (and through what channel — direct, other co-op, or TIPS)
- For a **vendor**: list TIPS members already purchasing from them (and through what channel)
- Identify cross-sell and introduction opportunities

## Step 8 — Competitive Intelligence

- Which competing cooperatives are active with this entity?
- Win/loss history against competitors
- Pricing or fee structure comparisons where available
- Unique TIPS advantages for this specific entity

## Deliverable 1 — Pitch Deck

Generate a structured pitch deck (Markdown format suitable for conversion to PDF/slides) with:

```
# TIPS Consulting — [Entity Name]
## Meeting Date: [Date]

---

### Slide 1: About TIPS
- Brief overview of TIPS cooperative purchasing
- National reach, contract portfolio, no-cost membership

### Slide 2: Why [Entity Name] + TIPS
- Tailored value proposition based on research
- Specific pain points TIPS solves for them
- Dollar savings estimates where possible

### Slide 3: Relevant TIPS Contracts
- Top 5-10 contracts most relevant to this entity
- Vendor names, categories, contract highlights

### Slide 4: Success Stories
- 2-3 comparable entities that benefited from TIPS
- Quantified results (time saved, money saved, compliance achieved)

### Slide 5: Current Relationship Summary
- History with TIPS (if any)
- Recent activity and engagement
- Open opportunities

### Slide 6: Recommended Next Steps
- Specific actionable items for the meeting
- Timeline and follow-up plan
- Key contacts and introductions to make

### Slide 7: Appendix — Entity Profile
- Summary of financial, purchasing, and organizational data
```

Save this as `pitch-deck-[entity-name].md` in the current working directory.

## Deliverable 2 — Background Intelligence Report & Score

Generate a comprehensive report with a **High-Value Target Score** (0-100%):

```
# Background Intelligence Report
## [Entity Name]
## Prepared: [Date] | Analyst: Claude AI

---

## HIGH-VALUE TARGET SCORE: [X]%

### Scoring Breakdown (each category 0-20 points):

| Category | Score | Rationale |
|----------|-------|-----------|
| Purchasing Volume Potential | X/20 | Based on budget size, growth, capital plans |
| Speed to Close | X/20 | Based on procurement rules, decision-maker access, urgency |
| Relationship Strength | X/20 | Based on existing history, CRM engagement, champion presence |
| Strategic Fit | X/20 | Based on alignment with TIPS contract portfolio and growth goals |
| Competitive Position | X/20 | Based on competitor presence, switching costs, TIPS advantages |

### Grade: [A+ / A / B+ / B / C+ / C / D / F]
- 90-100: Tier 1 — Immediate high-priority pursuit
- 80-89: Tier 2 — Strong opportunity, prioritize
- 70-79: Tier 3 — Good opportunity, standard pursuit
- 60-69: Tier 4 — Moderate opportunity, nurture
- Below 60: Tier 5 — Long-term cultivation needed

---

## 1. Entity Overview
[Full profile from Steps 1-2]

## 2. Financial Analysis
[Revenue/budget details from Step 2]

## 3. Contracts & Procurement
[Details from Step 3]

## 4. Relationship History
[Details from Step 4]

## 5. Budget & Spending Deep Dive
[Details from Step 5]

## 6. Challenges & Opportunities
[Details from Step 6]

## 7. Shared Vendors / Members
[Details from Step 7]

## 8. Competitive Landscape
[Details from Step 8]

## 9. Recommended Strategy
- Primary approach angle
- Key talking points for the meeting
- Objection handling (anticipated pushback and responses)
- 30/60/90 day follow-up plan

## 10. Risk Factors
- Anything that could derail the engagement
- Political considerations
- Budget cycle timing concerns
- Compliance or legal considerations
```

Save this as `background-report-[entity-name].md` in the current working directory.

## Data Sources Priority

Use these tools in order of reliability:

1. **HubSpot CRM** — `search_crm_objects`, `get_crm_objects` for contacts, companies, deals, notes
2. **Connected Databases** — `queryData` for any SQL-accessible data stores
3. **Google Sheets** — check for tracking spreadsheets with vendor/member data
4. **Web Search** — for public financial records, budget documents, news
5. **Gmail** — `gmail_search_messages` for recent correspondence context
6. **Google Calendar** — `gcal_list_events` for meeting history
7. **Google Drive** — for any existing reports or documents about the entity

## Rules

- Always cite your data sources for each claim
- Clearly label estimates vs. confirmed data
- If a data source is unavailable or returns no results, note the gap and proceed with what is available
- Do NOT fabricate financial figures — use "Not Available" and explain where to find the data
- Flag any data that appears stale (older than 12 months) with a freshness warning
- Both deliverables must be saved as downloadable Markdown files
- Ask the user to confirm the entity name before beginning research if there is any ambiguity
- Total preparation time target: produce both deliverables in a single workflow run
