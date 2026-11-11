# Project Init Templates

IPDM files use the six standard platform keys: `google_drive`, `ebuilder`, `jobtread`, `building_connected`, `procore`, `hubspot`. No secrets in any of these files.

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

