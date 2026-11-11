# Playbooks

Each playbook starts with a read that finds the IDs. Core tools are called by name. All other operations run through `hostinger_call` (shown as `call:`), with `confirm: true` on a write only after the user said yes.

## 1. Domain search (read only)

1. call: `domains_suggestDomainNamesFromADescriptionV1` with `description` and `limit`. The same input gives different names each time.
2. `domains_checkDomainAvailabilityV1` with `domain` (the label, no TLD) and `tlds` (no dots). Put all TLDs in one call. `with_alternatives: true` needs exactly one TLD.
3. call: `billing_getCatalogItemListV1` with `category: "DOMAIN"` for prices in integer cents.

Give a table: name, available, first-year price. Then stop. A purchase is `domains_purchaseNewDomainV1` (SPENDS MONEY).

## 2. DNS safe-write

Use every step for every DNS change.

1. `DNS_getDNSRecordsV1`: read the current zone.
2. `DNS_getDNSSnapshotListV1`: note the newest snapshot. It is the rollback point.
3. `DNS_validateDNSRecordsV1` with the new records. A 422 means the records are wrong and nothing changed.
4. Show the user the difference. Wait for a yes.
5. `DNS_updateDNSRecordsV1`.
6. `DNS_getDNSRecordsV1` again, then a DNS lookup from outside.

Body: `{"overwrite": false, "zone": [{"name": "www", "type": "A", "ttl": 3600, "records": [{"content": "1.2.3.4"}]}]}`.

- `overwrite: true` deletes the records with the same name and type, then creates the new ones. Use `false` unless a replacement is intended.
- A single CNAME: `dns_set_cname` does steps 3 and 5 in one call and replaces the old CNAME for that name. Still do steps 1, 2, 4 and 6.
- Undo: `DNS_restoreDNSSnapshotV1` with `domain` and `snapshotId`.
- call: `DNS_resetDNSRecordsV1` restores Hostinger defaults and removes custom mail records. Almost never correct.

## 3. Subdomain

1. `hosting_listWebsitesV1` with `domain`: get `username`.
2. `hosting_createWebsiteSubdomainV1` with `username`, `domain`, `subdomain`.
3. `hosting_listWebsiteSubdomainsV1`: verify.

A subdomain that points to another host (Vercel, Cloudflare Pages, a VPS) is a DNS record, not a hosting subdomain. Use `dns_set_cname` or an A record through playbook 2. call: `hosting_generateAFreeSubdomainV1` gives a temporary hostname.

## 4. New website

1. `hosting_listOrdersV1`: get `order_id`.
2. `hosting_startWebsiteSetupV1` with `order_id` and `domain`. Add `type: "wordpress"` and the `wordpress` object for a WordPress site.
3. Poll `hosting_listWebsiteSetupsV1` with `domain` each 10 to 15 seconds until `status` is `completed`. File, deploy and database calls fail before that.

## 5. Deploy from Git (no file upload)

1. call: `hosting_listGitInstallationsV1`, then `hosting_listGitInstallationRepositoriesV1` with the installation `uuid`. With no installation, the user connects GitHub or GitLab once in hPanel.
2. call: `hosting_deployWebsiteGitRepositoryV1` with `username`, `domain` and the repository fields from `hostinger_describe`.
3. Node.js app: poll call: `hosting_listNodeJSBuildsV1` until the build completes or fails. On failure read `hosting_getNodeJSBuildLogsV1` and `hosting_analyseFailedNode.jsBuildV1`.

## 6. Deploy from an archive

Every deploy in this section overwrites the website contents and cannot be undone. Name the domain and get a yes before the last step.

Upload step for all rows: get `url`, `auth_key` and `rest_auth_key` from the upload-URL operation, then call `hostinger_upload_from_url` with those three values, the HTTPS `source_url` of the file, and the destination `path`. The upload keys expire in minutes, so run the steps one after another. The file must be at a public HTTPS URL (a release asset, a storage link). The limit is 50 MB.

| Target | Find the ID | Upload-URL operation | Destination `path` | Last step |
|---|---|---|---|---|
| Static site, no build | `hosting_listWebsitesV1` → `username` | `hosting_generateUploadURLV1` (`username`, `domain`) | `site.zip` | `hosting_deployStaticSiteArchiveV1` with `archive_path: "site.zip"` |
| Node.js app, built on Hostinger | same | same | `app.zip` (source only, no `node_modules`) | `hosting_getNode.jsBuildSettingsFromArchiveV1`, then `hosting_startNode.jsBuildV1` with `source_type: "archive"` and `source_options.archive_path` |
| WordPress site import | same | same, one call for both files | `site.zip` and `dump.sql` | `hosting_importWordPressWebsiteV1` with `archive_path` and `sql_path` |
| WordPress plugin | same | same | `wp-content/plugins/{slug}-{random}/{file}` for each file | `hosting_deployWordPressPluginV1` with `slug` and `plugin_path` |
| WordPress theme | same | same | `wp-content/themes/{slug}-{random}/{file}` for each file | `hosting_deployWordPressThemeV1` with `slug`, `theme_path`, `is_activated` |
| Agency Plan, PHP as-is | `agency-hosting_listDomainsV1`, match `fqdn` → `website_uid` | `agency-hosting_generateUploadURLV1` | `.h5g/app.zip` | `agency-hosting_importWebsiteFromArchiveV1` with `archive_name: "app.zip"` (no folder) |
| Agency Plan, Node static build | same | same | `{random}/app.zip` | `agency-hosting_buildWebsiteNodeJSAssetsV1` with `archive_path` |

Verify: request the site and search the response for a string from the deployed files. A 200 status alone can be a parking page. If the old content shows, call `hosting_clearWebsiteCacheV1` and check once more. A Node.js build is queued: poll `hosting_listNodeJSBuildsV1` and do not report success on a queued build.

Database for a deployed app: the app connects to `127.0.0.1` port `3306`. Put passwords in environment variables with `hosting_replaceNode.jsEnvironmentVariablesV1`, never in source code.

## 7. VPS

1. call: `VPS_getVirtualMachinesV1`: get the VM id and state.
2. New VM: `billing_getCatalogItemListV1` (`category: "VPS"`), `VPS_getDataCenterListV1`, `VPS_getTemplatesV1`, then `VPS_purchaseNewVirtualMachineV1` (SPENDS MONEY), then `VPS_setupPurchasedVirtualMachineV1`. Prefer a public key over a password. Set `enable_backups: true`.
3. Firewall: `VPS_createNewFirewallV1`, `VPS_createFirewallRuleV1`, `VPS_activateFirewallV1`.
4. Docker Compose projects use the `VPS_*Project*V1` operations: `VPS_getProjectListV1`, `VPS_getProjectContentsV1`, `VPS_getProjectLogsV1`, `VPS_restartProjectV1`, `VPS_updateProjectV1`, `VPS_createNewProjectV1`. Restart and update keep the volumes. Try them before `VPS_deleteProjectV1`.

Before a restart or an update on a VM that runs live services, tell the user which services stop.

## 8. Health check (read only)

`domains_getDomainListV1`, `hosting_listWebsitesV1`, call: `VPS_getVirtualMachinesV1`, call: `billing_getSubscriptionListV1`. Report subscriptions that expire soon, domains due for renewal (`domains_getDomainRenewalInformationV1`), and each VM that is stopped.
