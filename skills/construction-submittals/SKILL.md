---
name: construction-submittals
description: Public construction submittal tracking — scan specs, generate registers, track lead times, and manage approvals by CSI division and trade
---

# Construction Submittals & Lead Time Tracking

## Overview

Skill for JOC (Job Order Contracting) and public construction management operations. Covers submittal identification from specifications, register generation, status tracking, and lead time management organized by CSI MasterFormat division and trade.

## Capabilities

1. **Spec Scanning** — Parse specification sections to extract submittal requirements by CSI division
2. **Register Generation** — Auto-generate a submittal log/register with standard fields (number, spec section, description, trade, type, status, lead time)
3. **Status Tracking** — Track submittal lifecycle: Not Started → In Preparation → Submitted → Under Review → Approved / Approved as Noted / Revise & Resubmit / Rejected
4. **Lead Time Management** — Track manufacturer lead times, review durations, and flag items on the critical path
5. **Trade-Based Organization** — Group submittals by CSI division and responsible trade/subcontractor

## Submittal Types (Common in Public Construction)

| Code | Type | Description |
|------|------|-------------|
| SD | Shop Drawings | Fabrication/installation drawings from manufacturer or sub |
| PD | Product Data | Catalog cuts, specs, performance data, MSDS/SDS |
| SS | Samples | Physical or color samples for approval |
| CP | Certificates/Permits | Manufacturer certs, test reports, permits |
| DI | Design Information | Calculations, mix designs, engineering data |
| MO | Mockups | Full-scale assemblies for quality standard |
| QC | Quality Control | Test reports, inspection reports |
| CL | Closeout | O&M manuals, warranties, as-builts, attic stock |
| WP | Work Plan | Method statements, safety plans, schedules |
| SR | Sustainable/LEED | Environmental product declarations, recycled content |

## CSI MasterFormat Divisions — Common Submittals by Trade

### Division 01 — General Requirements
- Construction schedule (WP)
- Safety plan / HASP (WP)
- Quality control plan (QC)
- Waste management plan (WP)
- Schedule of values (PD)

### Division 02 — Existing Conditions
- Hazmat survey/abatement plan (WP, CP)
- Demolition plan (WP)

### Division 03 — Concrete
**Trade: Concrete Contractor**
- Concrete mix designs (DI) — *Lead: 2-3 weeks*
- Reinforcing steel shop drawings (SD) — *Lead: 3-4 weeks*
- Formwork drawings (SD) — *Lead: 2-3 weeks*
- Concrete admixtures product data (PD)
- Curing compounds (PD)
- Concrete test reports (QC)

### Division 04 — Masonry
**Trade: Mason**
- CMU product data and samples (PD, SS) — *Lead: 2-4 weeks*
- Mortar and grout mix designs (DI)
- Stone samples (SS) — *Lead: 4-8 weeks*
- Masonry reinforcement (PD)

### Division 05 — Metals
**Trade: Structural Steel / Misc. Metals**
- Structural steel shop drawings (SD) — *Lead: 6-10 weeks*
- Steel connection details (SD)
- Metal deck product data (PD) — *Lead: 4-6 weeks*
- Miscellaneous metals shop drawings (SD) — *Lead: 4-6 weeks*
- Welding certifications (CP)
- Mill certificates (CP)
- Steel joist shop drawings (SD) — *Lead: 6-8 weeks*

### Division 06 — Wood, Plastics, Composites
**Trade: Carpentry**
- Engineered wood product data (PD) — *Lead: 2-4 weeks*
- Architectural woodwork shop drawings (SD) — *Lead: 6-10 weeks*
- Casework shop drawings (SD) — *Lead: 6-8 weeks*
- Finish samples (SS)

### Division 07 — Thermal & Moisture Protection
**Trade: Roofing / Waterproofing / Insulation**
- Roofing system product data (PD) — *Lead: 2-4 weeks*
- Roofing warranty documentation (CP)
- Waterproofing/damproofing product data (PD) — *Lead: 2-3 weeks*
- Insulation product data (PD)
- Metal wall panels shop drawings (SD) — *Lead: 8-12 weeks*
- Joint sealant product data and samples (PD, SS)
- Fireproofing product data (PD)

### Division 08 — Openings
**Trade: Door/Window/Glazing**
- Hollow metal door and frame shop drawings (SD) — *Lead: 6-10 weeks*
- Wood door product data and samples (PD, SS) — *Lead: 6-8 weeks*
- Hardware schedule and product data (PD) — *Lead: 8-14 weeks*
- Aluminum storefront/curtain wall shop drawings (SD) — *Lead: 8-12 weeks*
- Glass and glazing product data (PD) — *Lead: 6-10 weeks*
- Door hardware keying schedule (PD)

### Division 09 — Finishes
**Trade: Drywall / Painter / Flooring / Tile**
- Gypsum board assemblies (PD) — *Lead: 1-2 weeks*
- Tile product data and samples (PD, SS) — *Lead: 4-8 weeks*
- Acoustical ceiling product data (PD) — *Lead: 3-5 weeks*
- Resilient flooring product data and samples (PD, SS) — *Lead: 4-6 weeks*
- Carpet product data and samples (PD, SS) — *Lead: 4-6 weeks*
- Paint/coating product data and color samples (PD, SS) — *Lead: 1-2 weeks*
- Terrazzo samples (SS) — *Lead: 6-8 weeks*
- Epoxy flooring product data (PD) — *Lead: 2-4 weeks*

### Division 10 — Specialties
**Trade: Specialty Contractor**
- Toilet partitions and accessories (PD, SD) — *Lead: 4-8 weeks*
- Signage shop drawings (SD) — *Lead: 4-6 weeks*
- Fire extinguisher cabinets (PD) — *Lead: 3-4 weeks*
- Lockers product data (PD) — *Lead: 6-8 weeks*
- Projection screens / markerboards (PD)

### Division 11 — Equipment
**Trade: Equipment Supplier**
- Kitchen equipment (SD, PD) — *Lead: 8-14 weeks*
- Laundry equipment (PD) — *Lead: 6-10 weeks*
- Lab equipment (SD, PD) — *Lead: 8-12 weeks*

### Division 12 — Furnishings
**Trade: Furnishings Supplier**
- Window treatments (PD, SS) — *Lead: 4-8 weeks*
- Furniture product data (PD) — *Lead: 6-12 weeks*
- Countertops (PD, SS) — *Lead: 4-6 weeks*

### Division 14 — Conveying Equipment
**Trade: Elevator Contractor**
- Elevator shop drawings (SD) — *Lead: 12-20 weeks*
- Elevator product data (PD)
- Cab finish samples (SS)

### Division 21 — Fire Suppression
**Trade: Fire Protection**
- Sprinkler system shop drawings (SD) — *Lead: 3-5 weeks*
- Fire pump product data (PD) — *Lead: 6-10 weeks*
- Sprinkler head product data (PD)

### Division 22 — Plumbing
**Trade: Plumber**
- Plumbing fixture product data (PD) — *Lead: 4-8 weeks*
- Piping shop drawings (SD) — *Lead: 3-5 weeks*
- Water heater product data (PD) — *Lead: 4-6 weeks*
- Domestic water booster pump (PD) — *Lead: 6-8 weeks*

### Division 23 — HVAC
**Trade: Mechanical / HVAC**
- HVAC equipment product data (PD) — *Lead: 8-16 weeks*
- Ductwork shop drawings (SD) — *Lead: 3-5 weeks*
- Controls/BAS submittals (SD, PD) — *Lead: 4-8 weeks*
- TAB (Testing, Adjusting, Balancing) plan (WP)
- Diffusers, grilles, registers (PD) — *Lead: 3-5 weeks*
- Variable frequency drives (PD) — *Lead: 6-10 weeks*
- Refrigerant piping (PD)

### Division 26 — Electrical
**Trade: Electrician**
- Electrical panelboard/switchgear shop drawings (SD) — *Lead: 10-20 weeks*
- Lighting fixture product data (PD) — *Lead: 4-8 weeks*
- Lighting controls (PD, SD) — *Lead: 4-6 weeks*
- Generator product data (PD) — *Lead: 12-20 weeks*
- Conduit and wire product data (PD)
- Fire alarm system shop drawings (SD) — *Lead: 4-8 weeks*

### Division 27 — Communications
**Trade: Low Voltage / Telecom**
- Structured cabling product data (PD) — *Lead: 3-5 weeks*
- AV equipment (PD) — *Lead: 6-10 weeks*
- Access control/security shop drawings (SD) — *Lead: 6-10 weeks*

### Division 28 — Electronic Safety & Security
**Trade: Security / Fire Alarm**
- Fire alarm shop drawings (SD) — *Lead: 4-8 weeks*
- CCTV/surveillance product data (PD) — *Lead: 4-8 weeks*

### Division 31 — Earthwork
**Trade: Sitework / Excavation**
- Geotechnical report (DI)
- Soil compaction test results (QC)
- Erosion control plan (WP)
- Shoring/excavation support plan (SD, WP)

### Division 32 — Exterior Improvements
**Trade: Paving / Landscape**
- Asphalt/concrete paving mix designs (DI) — *Lead: 2-3 weeks*
- Pavement marking product data (PD)
- Fencing shop drawings (SD) — *Lead: 4-6 weeks*
- Landscape/planting plan (SD)
- Irrigation system (SD)

### Division 33 — Utilities
**Trade: Utilities / Underground**
- Pipe product data (PD) — *Lead: 4-8 weeks*
- Manhole/structure shop drawings (SD) — *Lead: 4-6 weeks*
- Utility trench details (SD)

## Workflow

```
Spec Review → Identify Submittals → Generate Register → Assign to Trades
     ↓
Track Preparation → Submit to A/E → Review Period → Disposition
     ↓
Approved: Proceed to procurement/fabrication
Revise & Resubmit: Return to trade, re-track
     ↓
Lead Time Tracking → Delivery Coordination → Closeout Submittals
```

## Usage

Use the companion CLI tool at `tools/construction-submittals/` to:
- `submittal_tracker.py scan <spec_file>` — Extract submittals from a specification document
- `submittal_tracker.py init <project_name>` — Initialize a new submittal register
- `submittal_tracker.py add` — Add a submittal to the register
- `submittal_tracker.py status` — View register with status dashboard
- `submittal_tracker.py update <id>` — Update submittal status or lead time
- `submittal_tracker.py report` — Generate summary report with critical path items
- `submittal_tracker.py import-spec <file>` — Bulk-import from a spec scanning result
