# Project Init Templates

IPDM and Highway files use the six standard platform keys: `google_drive`, `ebuilder`, `jobtread`, `building_connected`, `procore`, `hubspot`. No secrets in any of these files.

## `.ntxp/ipdm/project.yaml`

```yaml
project:
  id: ""                      # NTXP-{YYYY}-{SEQ}
  name: ""
  owner: ""
  contract_type: ""           # JOC | CSP | Hard Bid | CM-at-Risk | Design-Build
  cooperative: ""             # TIPS | BuyBoard | Sourcewell | Choice Partners | None
  status: "Pursuit"           # Pursuit | Pre-Con | Active | Closeout | Warranty
  platforms:
    google_drive: ""
    ebuilder: ""
    jobtread: ""
    building_connected: ""
    procore: ""
    hubspot: ""
  contacts: []
  trades: []
  documents: []               # indexed by folder number, e.g. 5.1
```

## Coda files

`.ntxp/coda/registry.yaml`, `crosswalk.yaml` and `sync-log.jsonl` are defined in `coda.md` (single source; do not copy them here).

## `.ntxp/ipdm/skill-config.yaml`

```yaml
skill_rewiring:
  search_source: ".ntxp/ipdm/"
  save_target: ".ntxp/ipdm/"
  link_registry: ".ntxp/coda/registry.yaml"
  crosswalk_registry: ".ntxp/coda/crosswalk.yaml"
  credential_source: "ntxp-secrets-vault"
  auth_provider: "ntxp-id"
  model_config: ".ntxp/ipdm/model-council.yaml"
  routing_config: ".ntxp/highway/config.yaml"
  routing_log: ".ntxp/highway/routing-log.jsonl"
  skills:
    - { name: ntxp-estimating,   reads: [project.trades, project.contract_type, project.cooperative], writes: [documents, ntxp_tools.estimating_workspace] }
    - { name: ntxp-folder-system, reads: [project.name, project.id], writes: [platforms.google_drive, documents] }
    - { name: ntxp-submittal-command, reads: [project.trades, documents], writes: [ntxp_tools.submittal_register] }
    - { name: itb-generator,     reads: [project.trades, contacts], writes: [documents] }
    - { name: ntxp-quantity-takeoff, reads: [project.trades, documents], writes: [documents] }
    - { name: dallas-isd-sov-payapp-review, reads: [project.trades, project.contract_type, documents], writes: [ntxp_tools.schedule_of_values, documents] }
    - { name: buildingconnected-mcp, reads: [platforms.building_connected], writes: [platforms.building_connected, crosswalk] }
    - { name: jobtread-data-integrator, reads: [platforms.jobtread], writes: [platforms.jobtread, crosswalk] }
    - { name: trimble-ebuilder-connector, reads: [platforms.ebuilder], writes: [platforms.ebuilder, crosswalk] }
```

## `.ntxp/highway/config.yaml` routes

| Pattern | Primary | Fallback | Tier |
|---|---|---|---|
| estimate, price, cost, budget | ntxp-estimating | rsmeans-estimate-generator | 3 |
| takeoff, quantity, measure | ntxp-quantity-takeoff | demolition-takeoff | 3 |
| bid, ITB, solicit | ntxp-project-itb-brief | itb-generator | 2 |
| folder, file, organize, drive | ntxp-folder-system | ntxp-folder-structure | 1 |
| schedule, SOV, pay app, billing | dallas-isd-sov-payapp-review | estimating | 3 |
| submittal, RFI | ntxp-submittal-command | specs-skill | 2 |
| credential, key, secret, token | ntxp-secrets-vault | none | 1 |
| markup, redline, plan | ntxp-pdf-markups-and-redlines | apply-construction-markups | 2 |
| model, council, AI, routing | ntxp-model-council | none | 2 |
| project setup, init, deploy, new project | ntxp-project-init | init | 1 |
