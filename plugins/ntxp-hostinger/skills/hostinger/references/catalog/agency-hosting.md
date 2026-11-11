# Hostinger operations: agency-hosting

Generated from Hostinger API spec 2.13.1. Run any row with `hostinger_call`. Get the argument schema first with `hostinger_describe`.

## Agency Hosting: Cache

| Operation | Class | What it does |
|---|---|---|
| `agency-hosting_clearWebsiteCacheV1` | DESTRUCTIVE | Clear website cache |

## Agency Hosting: Cron Jobs

| Operation | Class | What it does |
|---|---|---|
| `agency-hosting_listWebsiteCronJobsV1` | read | List website cron jobs |
| `agency-hosting_createWebsiteCronJobV1` | write | Create website cron job |
| `agency-hosting_deleteWebsiteCronJobV1` | DESTRUCTIVE | Delete website cron job |

## Agency Hosting: Databases

| Operation | Class | What it does |
|---|---|---|
| `agency-hosting_listWebsiteDatabasesV1` | read | List website databases |
| `agency-hosting_createWebsiteDatabaseV1` | write | Create website database |
| `agency-hosting_deleteWebsiteDatabaseV1` | DESTRUCTIVE | Delete website database |
| `agency-hosting_createWebsiteDatabaseUserV1` | write | Create website database user |
| `agency-hosting_deleteWebsiteDatabaseUserV1` | DESTRUCTIVE | Delete website database user |

## Agency Hosting: Datacenters

| Operation | Class | What it does |
|---|---|---|
| `agency-hosting_listAvailableDatacentersV1` | read | List available datacenters |

## Agency Hosting: Domains

| Operation | Class | What it does |
|---|---|---|
| `agency-hosting_changeWebsiteDomainV1` | write | Change website domain |
| `agency-hosting_linkDomainToWebsiteV1` | write | Link domain to website |
| `agency-hosting_listDomainsV1` | read | List domains |
| `agency-hosting_unlinkDomainFromWebsiteV1` | DESTRUCTIVE | Unlink domain from website |

## Agency Hosting: Files

| Operation | Class | What it does |
|---|---|---|
| `agency-hosting_generateUploadURLV1` | read | Generate upload URL |
| `agency-hosting_importWebsiteFromArchiveV1` | DESTRUCTIVE | Import website from archive |

## Agency Hosting: Metrics

| Operation | Class | What it does |
|---|---|---|
| `agency-hosting_listAgencyPlanOrderDiskUsageMetricsV1` | read | List Agency Plan order disk usage metrics |
| `agency-hosting_listOrderResourceUsageMetricsV1` | read | List order resource usage metrics |

## Agency Hosting: Orders

| Operation | Class | What it does |
|---|---|---|
| `agency-hosting_listOrdersV1` | read | List orders |

## Agency Hosting: PHP

| Operation | Class | What it does |
|---|---|---|
| `agency-hosting_listPHPExtensionsForAWebsiteV1` | read | List PHP extensions for a website |
| `agency-hosting_replaceWebsitePHPExtensionsV1` | write | Replace website PHP extensions |
| `agency-hosting_listPHPOptionsForAWebsiteV1` | read | List PHP options for a website |
| `agency-hosting_replaceWebsitePHPOptionsV1` | write | Replace website PHP options |
| `agency-hosting_listAvailablePHPVersionsForAnOrderV1` | read | List available PHP versions for an order |
| `agency-hosting_listAvailablePHPVersionsForAWebsiteV1` | read | List available PHP versions for a website |
| `agency-hosting_updateWebsitePHPVersionV1` | write | Update website PHP version |

## Agency Hosting: SSL

| Operation | Class | What it does |
|---|---|---|
| `agency-hosting_reinstallWebsiteSSLV1` | write | Reinstall website SSL |
| `agency-hosting_installWebsiteSSLV1` | write | Install website SSL |
| `agency-hosting_getWebsiteSSLStatusV1` | read | Get website SSL status |
| `agency-hosting_uninstallWebsiteSSLV1` | DESTRUCTIVE | Uninstall website SSL |

## Agency Hosting: Website Setups

| Operation | Class | What it does |
|---|---|---|
| `agency-hosting_createANewWebsiteV1` | write | Create a new website |
| `agency-hosting_getWebsiteSetupStatusV1` | read | Get website setup status |

## Agency Hosting: Websites

| Operation | Class | What it does |
|---|---|---|
| `agency-hosting_buildWebsiteNodeJSAssetsV1` | write | Build website NodeJS assets |
| `agency-hosting_getWebsiteDetailsV1` | read | Get website details |
| `agency-hosting_deleteWebsiteV1` | DESTRUCTIVE | Delete website |
| `agency-hosting_listAgencyPlanWebsitesV1` | read | List Agency Plan websites |
| `agency-hosting_listWebsiteProcessesV1` | read | List website processes |

## Agency Hosting: WordPress

| Operation | Class | What it does |
|---|---|---|
| `agency-hosting_changeWordPressVersionV1` | write | Change WordPress version |
| `agency-hosting_getWordPressSettingsV1` | read | Get WordPress settings |
| `agency-hosting_listAvailableWordPressVersionsV1` | read | List available WordPress versions |
