# Hostinger operations: domains

Generated from Hostinger API spec 2.13.1. Run any row with `hostinger_call`. Get the argument schema first with `hostinger_describe`.

## Domains: Availability

| Operation | Class | What it does |
|---|---|---|
| `domains_suggestDomainNamesFromADescriptionV1` | read | Suggest domain names from a description |
| `domains_suggestDomainNamesFromADomainV1` | read | Suggest domain names from a domain |
| `domains_checkDomainAvailabilityV1` | read | Check domain availability |

## Domains: Forwarding

| Operation | Class | What it does |
|---|---|---|
| `domains_getDomainForwardingV1` | read | Get domain forwarding |
| `domains_updateDomainForwardingV1` | write | Update domain forwarding |
| `domains_deleteDomainForwardingV1` | DESTRUCTIVE | Delete domain forwarding |
| `domains_createDomainForwardingV1` | write | Create domain forwarding |

## Domains: Move

| Operation | Class | What it does |
|---|---|---|
| `domains_getIncomingDomainMoveV1` | read | Get incoming domain move |
| `domains_acceptIncomingDomainMoveV1` | write | Accept incoming domain move |
| `domains_rejectIncomingDomainMoveV1` | DESTRUCTIVE | Reject incoming domain move |
| `domains_getIncomingDomainMoveListV1` | read | Get incoming domain move list |
| `domains_getOutgoingDomainMoveV1` | read | Get outgoing domain move |
| `domains_startOutgoingDomainMoveV1` | write | Start outgoing domain move |
| `domains_cancelOutgoingDomainMoveV1` | DESTRUCTIVE | Cancel outgoing domain move |
| `domains_getOutgoingDomainMoveListV1` | read | Get outgoing domain move list |

## Domains: Portfolio

| Operation | Class | What it does |
|---|---|---|
| `domains_getDomainAuthorizationCodeV1` | read | Get domain authorization code |
| `domains_claimFreeDomainV1` | SPENDS MONEY | Claim free domain |
| `domains_enableDomainLockV1` | write | Enable domain lock |
| `domains_disableDomainLockV1` | DESTRUCTIVE | Disable domain lock |
| `domains_getDomainDetailsV1` | read | Get domain details |
| `domains_getDomainListV1` | read | Get domain list |
| `domains_purchaseNewDomainV1` | SPENDS MONEY | Purchase new domain |
| `domains_enablePrivacyProtectionV1` | write | Enable privacy protection |
| `domains_disablePrivacyProtectionV1` | DESTRUCTIVE | Disable privacy protection |
| `domains_getDomainRenewalInformationV1` | read | Get domain renewal information |
| `domains_completeDomainSetupV1` | write | Complete domain setup |
| `domains_updateDomainNameserversV1` | write | Update domain nameservers |

## Domains: Transfer

| Operation | Class | What it does |
|---|---|---|
| `domains_claimFreeDomainTransferV1` | SPENDS MONEY | Claim free domain transfer |
| `domains_getTransferV1` | read | Get transfer |
| `domains_getTransferListV1` | read | Get transfer list |
| `domains_startDomainTransferV1` | SPENDS MONEY | Start domain transfer |

## Domains: WHOIS

| Operation | Class | What it does |
|---|---|---|
| `domains_getPendingIRTPVerificationV1` | read | Get pending IRTP verification |
| `domains_cancelPendingIRTPVerificationV1` | DESTRUCTIVE | Cancel pending IRTP verification |
| `domains_changeWHOISProfileForDomainV1` | write | Change WHOIS profile for domain |
| `domains_setWHOISProfileAsDefaultV1` | write | Set WHOIS profile as default |
| `domains_unsetDefaultWHOISProfileV1` | DESTRUCTIVE | Unset default WHOIS profile |
| `domains_getWHOISProfileV1` | read | Get WHOIS profile |
| `domains_deleteWHOISProfileV1` | DESTRUCTIVE | Delete WHOIS profile |
| `domains_getWHOISProfileListV1` | read | Get WHOIS profile list |
| `domains_createWHOISProfileV1` | write | Create WHOIS profile |
| `domains_getWHOISProfileUsageV1` | read | Get WHOIS profile usage |
