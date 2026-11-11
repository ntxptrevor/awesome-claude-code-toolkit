# Hostinger operations: dns

Generated from Hostinger API spec 2.13.1. Run any row with `hostinger_call`. Get the argument schema first with `hostinger_describe`.

## DNS: Snapshot

| Operation | Class | What it does |
|---|---|---|
| `DNS_getDNSSnapshotV1` | read | Get DNS snapshot |
| `DNS_getDNSSnapshotListV1` | read | Get DNS snapshot list |
| `DNS_restoreDNSSnapshotV1` | DESTRUCTIVE | Restore DNS snapshot |

## DNS: Zone

| Operation | Class | What it does |
|---|---|---|
| `DNS_getDNSRecordsV1` | read | Get DNS records |
| `DNS_updateDNSRecordsV1` | write | Update DNS records |
| `DNS_deleteDNSRecordsV1` | DESTRUCTIVE | Delete DNS records |
| `DNS_resetDNSRecordsV1` | DESTRUCTIVE | Reset DNS records |
| `DNS_validateDNSRecordsV1` | read | Validate DNS records |
