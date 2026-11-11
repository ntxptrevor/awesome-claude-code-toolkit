# Hostinger operations: hosting

Generated from Hostinger API spec 2.13.1. Run any row with `hostinger_call`. Get the argument schema first with `hostinger_describe`.

## Hosting: CDN

| Operation | Class | What it does |
|---|---|---|
| `hosting_disableCDNV1` | DESTRUCTIVE | Disable CDN |
| `hosting_enableCDNV1` | write | Enable CDN |
| `hosting_purgeCDNCacheV1` | DESTRUCTIVE | Purge CDN cache |
| `hosting_getCDNStatusV1` | read | Get CDN status |

## Hosting: Cache

| Operation | Class | What it does |
|---|---|---|
| `hosting_clearWebsiteCacheV1` | DESTRUCTIVE | Clear website cache |
| `hosting_getCacheStatusV1` | read | Get cache status |
| `hosting_toggleCachelessModeV1` | write | Toggle cacheless mode |
| `hosting_toggleWebsiteCacheV1` | write | Toggle website cache |

## Hosting: Cron Jobs

| Operation | Class | What it does |
|---|---|---|
| `hosting_listAccountCronJobsV1` | read | List account cron jobs |
| `hosting_createAccountCronJobV1` | write | Create account cron job |
| `hosting_deleteAccountCronJobV1` | DESTRUCTIVE | Delete account cron job |
| `hosting_getCronJobOutputV1` | read | Get cron job output |

## Hosting: Databases

| Operation | Class | What it does |
|---|---|---|
| `hosting_changeDatabasePasswordV1` | write | Change database password |
| `hosting_listAccountDatabasesV1` | read | List account databases |
| `hosting_createAccountDatabaseV1` | write | Create account database |
| `hosting_deleteAccountDatabaseV1` | DESTRUCTIVE | Delete account database |
| `hosting_createDatabaseRemoteConnectionV1` | write | Create database remote connection |
| `hosting_deleteDatabaseRemoteConnectionV1` | DESTRUCTIVE | Delete database remote connection |
| `hosting_listDatabaseRemoteConnectionsV1` | read | List database remote connections |
| `hosting_repairDatabaseV1` | write | Repair database |
| `hosting_setupWebsiteDatabaseV1` | write | Setup website database |
| `hosting_getPhpMyAdminLinkV1` | read | Get phpMyAdmin link |

## Hosting: Datacenters

| Operation | Class | What it does |
|---|---|---|
| `hosting_listAvailableDatacentersV1` | read | List available datacenters |

## Hosting: Domains

| Operation | Class | What it does |
|---|---|---|
| `hosting_generateAFreeSubdomainV1` | write | Generate a free subdomain |
| `hosting_listWebsiteParkedDomainsV1` | read | List website parked domains |
| `hosting_createWebsiteParkedDomainV1` | write | Create website parked domain |
| `hosting_deleteWebsiteParkedDomainV1` | DESTRUCTIVE | Delete website parked domain |
| `hosting_listWebsiteSubdomainsV1` | read | List website subdomains |
| `hosting_createWebsiteSubdomainV1` | write | Create website subdomain |
| `hosting_deleteWebsiteSubdomainV1` | DESTRUCTIVE | Delete website subdomain |
| `hosting_verifyDomainOwnershipV1` | read | Verify domain ownership |

## Hosting: Files

| Operation | Class | What it does |
|---|---|---|
| `hosting_generateUploadURLV1` | read | Generate upload URL |
| `hosting_listWebsiteFilesAndDirectoriesV1` | read | List website files and directories |
| `hosting_getWebsiteFileContentV1` | read | Get website file content |

## Hosting: Git

| Operation | Class | What it does |
|---|---|---|
| `hosting_getGitAutoDeploymentSettingsV1` | read | Get Git auto-deployment settings |
| `hosting_updateGitAutoDeploymentSettingsV1` | DESTRUCTIVE | Update Git auto-deployment settings |
| `hosting_deleteGitAutoDeploymentSettingsV1` | DESTRUCTIVE | Delete Git auto-deployment settings |
| `hosting_listGitInstallationsV1` | read | List Git installations |
| `hosting_listGitInstallationRepositoriesV1` | read | List Git installation repositories |
| `hosting_deployWebsiteGitRepositoryV1` | DESTRUCTIVE | Deploy website Git repository |
| `hosting_listWebsiteGitRepositoriesV1` | read | List website Git repositories |
| `hosting_getGitSSHPublicKeyV1` | read | Get Git SSH public key |
| `hosting_generateGitSSHKeyV1` | write | Generate Git SSH key |

## Hosting: Headless

| Operation | Class | What it does |
|---|---|---|
| `hosting_submitHeadlessBuildReportV1` | write | Submit headless build report |

## Hosting: NodeJS

| Operation | Class | What it does |
|---|---|---|
| `hosting_listNodeJSBuildsV1` | read | List NodeJS builds |
| `hosting_startNode.jsBuildV1` | write | Start Node.js build |
| `hosting_getNode.jsBuildSettingsV1` | read | Get Node.js build settings |
| `hosting_updateNode.jsBuildSettingsV1` | write | Update Node.js build settings |
| `hosting_getNode.jsBuildSettingsFromArchiveV1` | read | Get Node.js build settings from archive |
| `hosting_getNode.jsBuildSettingsFromRepositoryV1` | read | Get Node.js build settings from repository |
| `hosting_listNode.jsEnvironmentVariablesV1` | read | List Node.js environment variables |
| `hosting_replaceNode.jsEnvironmentVariablesV1` | write | Replace Node.js environment variables |
| `hosting_analyseFailedNode.jsBuildV1` | read | Analyse failed Node.js build |
| `hosting_getNode.jsBuildDetailsV1` | read | Get Node.js build details |
| `hosting_getNodeJSBuildLogsV1` | read | Get NodeJS build logs |
| `hosting_getNode.jsRuntimeLogsV1` | read | Get Node.js runtime logs |
| `hosting_clearNode.jsRuntimeLogsV1` | DESTRUCTIVE | Clear Node.js runtime logs |
| `hosting_restartNode.jsApplicationV1` | write | Restart Node.js application |
| `hosting_listNode.jsVulnerabilitiesV1` | read | List Node.js vulnerabilities |
| `hosting_patchNode.jsVulnerabilitiesV1` | write | Patch Node.js vulnerabilities |

## Hosting: Orders

| Operation | Class | What it does |
|---|---|---|
| `hosting_listOrdersV1` | read | List orders |

## Hosting: PHP

| Operation | Class | What it does |
|---|---|---|
| `hosting_resetPHPExtensionsV1` | DESTRUCTIVE | Reset PHP extensions |
| `hosting_getPHPDetailsV1` | read | Get PHP details |
| `hosting_getPHPInfoV1` | read | Get PHP info |
| `hosting_updatePHPExtensionsV1` | write | Update PHP extensions |
| `hosting_updatePHPOptionsV1` | write | Update PHP options |
| `hosting_updatePHPVersionV1` | write | Update PHP version |

## Hosting: Redirects

| Operation | Class | What it does |
|---|---|---|
| `hosting_listWebsiteRedirectsV1` | read | List website redirects |
| `hosting_createWebsiteRedirectV1` | write | Create website redirect |
| `hosting_deleteWebsiteRedirectV1` | DESTRUCTIVE | Delete website redirect |

## Hosting: SSL

| Operation | Class | What it does |
|---|---|---|
| `hosting_installSSLV1` | write | Install SSL |
| `hosting_getSSLStatusV1` | read | Get SSL status |
| `hosting_toggleHTTPSRedirectV1` | write | Toggle HTTPS redirect |
| `hosting_uninstallSSLV1` | DESTRUCTIVE | Uninstall SSL |

## Hosting: Websites

| Operation | Class | What it does |
|---|---|---|
| `hosting_listWebsiteSetupsV1` | read | List website setups |
| `hosting_startWebsiteSetupV1` | write | Start website setup |
| `hosting_listWebsitesV1` | read | List websites |
| `hosting_createWebsiteV1` | write | Create website (deprecated) |
| `hosting_deployStaticSiteArchiveV1` | DESTRUCTIVE | Deploy static site archive |
| `hosting_deleteWebsiteV1` | DESTRUCTIVE | Delete website |
