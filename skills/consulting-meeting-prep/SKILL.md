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

## Deliverable 1 — Pitch Deck (PowerPoint .pptx)

Generate a professional PowerPoint slide deck using `python-pptx`. The deck must be team-presentable with consistent branding, clean layouts, and readable fonts.

### Slide Structure

| Slide | Title | Content |
|-------|-------|---------|
| 1 | Title Slide | "TIPS Consulting — [Entity Name]", meeting date, prepared by |
| 2 | About TIPS | Brief overview of TIPS cooperative purchasing, national reach, contract portfolio, no-cost membership |
| 3 | Why [Entity Name] + TIPS | Tailored value proposition, specific pain points TIPS solves, dollar savings estimates |
| 4 | Relevant TIPS Contracts | Top 5-10 contracts most relevant to this entity — vendor names, categories, highlights |
| 5 | Success Stories | 2-3 comparable entities that benefited from TIPS with quantified results |
| 6 | Current Relationship Summary | History with TIPS (if any), recent activity, open opportunities |
| 7 | Recommended Next Steps | Specific actionable items, timeline, follow-up plan, key introductions |
| 8 | Appendix — Entity Profile | Summary of financial, purchasing, and organizational data |

### PowerPoint Formatting Requirements

- **Slide dimensions**: Widescreen 16:9 (13.333" × 7.5")
- **Title font**: Calibri Bold, 28-32pt, dark navy (#1B2A4A)
- **Body font**: Calibri, 16-18pt, dark gray (#333333)
- **Accent color**: TIPS brand blue (#0066CC) for headers and divider lines
- **Background**: White (#FFFFFF) with subtle footer containing "CONFIDENTIAL — Prepared for [Entity Name]"
- **Bullet points**: Use shaped bullets, left-aligned, with 1.2x line spacing
- **Tables**: Use light blue header row (#0066CC with white text), alternating row shading
- **Title slide**: Larger centered text, include date and "Prepared by TIPS Consulting"

### Filename Sanitization

All output filenames use a sanitized slug derived from the entity name. This prevents invalid characters, path traversal, and filesystem issues.

```python
import re

def sanitize_entity_name(name: str) -> str:
    """Convert entity name to a filesystem-safe slug.

    Rules: lowercase, replace spaces/special chars with hyphens,
    keep only alphanumeric and hyphens, collapse consecutive hyphens,
    strip leading/trailing hyphens.
    """
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug

entity_slug = sanitize_entity_name(entity_name)
```

### Generation Code Pattern

```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# Define brand colors
NAVY = RGBColor(0x1B, 0x2A, 0x4A)
BRAND_BLUE = RGBColor(0x00, 0x66, 0xCC)
DARK_GRAY = RGBColor(0x33, 0x33, 0x33)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

# Add slides with proper layouts, content, formatting...
# Each slide: add title shape, body text boxes, tables as needed
# Add footer to each slide

prs.save(f'pitch-deck-{entity_slug}.pptx')
```

Save as `pitch-deck-[entity-slug].pptx` in the current working directory.

Also save `pitch-deck-[entity-slug].md` as a Markdown reference copy.

## Deliverable 2 — Background Intelligence Report & Score (Word .docx)

Generate a professional Word document using `python-docx`. The report must be polished enough to share with executives and team members.

### Report Content Structure

```text
COVER PAGE:
  "Background Intelligence Report"
  [Entity Name]
  Prepared: [Date] | Analyst: Claude AI
  CONFIDENTIAL

EXECUTIVE SUMMARY (1 page):
  HIGH-VALUE TARGET SCORE: [X]%
  Grade: [A+ through F]
  Scoring Breakdown Table:
  | Category                    | Score | Rationale                                          |
  | Purchasing Volume Potential | X/20  | Based on budget size, growth, capital plans         |
  | Speed to Close              | X/20  | Based on procurement rules, decision-maker access   |
  | Relationship Strength       | X/20  | Based on existing history, CRM engagement           |
  | Strategic Fit               | X/20  | Based on alignment with TIPS contract portfolio     |
  | Competitive Position        | X/20  | Based on competitor presence, switching costs        |

  Tier Classification:
  - 90-100: Tier 1 — Immediate high-priority pursuit
  - 80-89:  Tier 2 — Strong opportunity, prioritize
  - 70-79:  Tier 3 — Good opportunity, standard pursuit
  - 60-69:  Tier 4 — Moderate opportunity, nurture
  - Below 60: Tier 5 — Long-term cultivation needed

  Scoring Rubrics (use for consistent scoring):

  Purchasing Volume Potential (0-20):
    18-20: Annual budget >$50M, 5%+ YoY growth, active capital plans or large contract portfolio
    14-17: Annual budget $10-50M, stable or growing, some capital plans
    10-13: Annual budget $1-10M, flat budget, limited capital plans
    6-9:   Annual budget <$1M or budget data significantly incomplete
    0-5:   Declining budget, no capital plans, or very small entity

  Speed to Close (0-20):
    18-20: Direct procurement authority, immediate need identified, decision-maker engaged
    14-17: Standard procurement process, 30-60 day timeline, internal champion identified
    10-13: Formal RFP required, 90-180 day timeline, multiple approvers needed
    6-9:   Complex approval chain, 6-12 month timeline, no internal champion
    0-5:   No current need, multi-year timeline, or significant political/legal barriers

  Relationship Strength (0-20):
    18-20: Active TIPS user, strong CRM history, executive-level champion, recent engagement
    14-17: Some TIPS history, regular contact, mid-level champion identified
    10-13: Minimal history, sporadic contact, no clear champion yet
    6-9:   Cold prospect, no prior relationship, limited contact info
    0-5:   Negative history (complaints, lost deals) or completely unknown entity

  Strategic Fit (0-20):
    18-20: Core TIPS categories match 80%+ of entity spend, flagship/reference potential
    14-17: Good category overlap (50-80%), aligns with TIPS growth priorities
    10-13: Moderate overlap (25-50%), some relevant contracts available
    6-9:   Limited overlap (<25%), niche needs outside core TIPS portfolio
    0-5:   Poor fit, entity needs largely unserved by current TIPS contracts

  Competitive Position (0-20):
    18-20: No competing co-op presence, or competitor contract expiring within 6 months
    14-17: Light competitor presence, TIPS has clear pricing/service advantages
    10-13: Moderate competitor presence, comparable offerings, winnable with effort
    6-9:   Strong competitor entrenchment, long-term contracts in place
    0-5:   Exclusive competitor agreement, high switching costs, or entity loyalty to rival

SECTION 1: Entity Overview
  [Full profile from Steps 1-2]

SECTION 2: Financial Analysis
  [Revenue/budget details from Step 2]

SECTION 3: Contracts & Procurement
  [Details from Step 3]

SECTION 4: Relationship History
  [Details from Step 4]

SECTION 5: Budget & Spending Deep Dive
  [Details from Step 5]

SECTION 6: Challenges & Opportunities
  [Top 5 challenges and top 5 opportunities from Step 6]

SECTION 7: Shared Vendors / Members
  [Overlap analysis from Step 7]

SECTION 8: Competitive Landscape
  [Details from Step 8]

SECTION 9: Recommended Strategy
  - Primary approach angle
  - Key talking points for the meeting
  - Objection handling (anticipated pushback and responses)
  - 30/60/90 day follow-up plan

SECTION 10: Risk Factors
  - Anything that could derail the engagement
  - Political considerations
  - Budget cycle timing concerns
  - Compliance or legal considerations
```

### Word Document Formatting Requirements

- **Page size**: Letter (8.5" × 11"), 1" margins
- **Title page**: Centered, entity name in 28pt Calibri Bold navy (#1B2A4A), "CONFIDENTIAL" watermark
- **Heading 1**: Calibri Bold, 22pt, navy (#1B2A4A), with a blue (#0066CC) bottom border
- **Heading 2**: Calibri Bold, 16pt, dark gray (#333333)
- **Body text**: Calibri, 11pt, dark gray (#333333), 1.15 line spacing
- **Tables**: Professional style with navy header row, alternating light gray/white rows, 10pt font
- **Score display**: The HIGH-VALUE TARGET SCORE should be prominently displayed — large bold font with color coding (green for 80+, yellow for 60-79, red for below 60)
- **Headers/Footers**: Page numbers bottom-right, "CONFIDENTIAL" top-right, entity name top-left
- **Table of Contents**: Auto-generated from heading styles
- **Page breaks**: Before each major section

### Generation Code Pattern

```python
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT

doc = Document()

# Set default font
style = doc.styles['Normal']
font = style.font
font.name = 'Calibri'
font.size = Pt(11)
font.color.rgb = RGBColor(0x33, 0x33, 0x33)

# Configure heading styles with brand colors
for level, size in [(1, 22), (2, 16), (3, 13)]:
    heading_style = doc.styles[f'Heading {level}']
    heading_style.font.name = 'Calibri'
    heading_style.font.size = Pt(size)
    heading_style.font.bold = True
    heading_style.font.color.rgb = RGBColor(0x1B, 0x2A, 0x4A)

# Add cover page, TOC, sections, tables, score display...
# Add headers and footers
# Add page breaks between sections

doc.save(f'background-report-{entity_slug}.docx')
```

Save as `background-report-[entity-slug].docx` in the current working directory.

Also save `background-report-[entity-slug].md` as a Markdown reference copy.

## Export Dependencies

Before generating the files, ensure required Python packages are installed:

```bash
pip install python-pptx python-docx
```

If `pip install` fails (e.g., no network access), fall back to Markdown-only output and notify the user that the .pptx and .docx files require `python-pptx` and `python-docx` to be installed.

## Final Output Summary

After generation, present the user with a summary of all files created:

```text
✅ Meeting Prep Complete for [Entity Name]

Downloadable Files:
  📊 pitch-deck-[entity-slug].pptx    — PowerPoint slide deck (team-presentable)
  📄 background-report-[entity-slug].docx — Word intelligence report (executive-ready)

Reference Copies:
  📝 pitch-deck-[entity-slug].md       — Markdown slide content
  📝 background-report-[entity-slug].md — Markdown report content

High-Value Target Score: [X]% ([Grade])
```

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
- Both deliverables must be saved as downloadable Office files (.pptx and .docx) plus Markdown reference copies
- Always install `python-pptx` and `python-docx` via pip before generating files
- If Office file generation fails, save Markdown versions and clearly inform the user
- Ask the user to confirm the entity name before beginning research if there is any ambiguity
- Total preparation time target: produce both deliverables in a single workflow run
