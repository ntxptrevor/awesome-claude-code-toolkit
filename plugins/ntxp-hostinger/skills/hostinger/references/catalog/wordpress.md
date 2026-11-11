# Hostinger operations: wordpress

Generated from Hostinger API spec 2.13.1. Run any row with `hostinger_call`. Get the argument schema first with `hostinger_describe`.

## WordPress: AI Content

| Operation | Class | What it does |
|---|---|---|
| `hosting_generateImagesV1` | write | Generate images |
| `hosting_getGenerationResultV1` | read | Get generation result |

## WordPress: AI Tools

| Operation | Class | What it does |
|---|---|---|
| `hosting_showAIOptionStatusV1` | read | Show AI option status |
| `hosting_setAIOptionStatusV1` | write | Set AI option status |

## WordPress: Installations

| Operation | Class | What it does |
|---|---|---|
| `hosting_checkIfWordPressInstallationsAreValidV1` | read | Check if WordPress installations are valid |
| `hosting_deleteWordPressInstallationV1` | DESTRUCTIVE | Delete WordPress installation |
| `hosting_detectWordPressInstallationsV1` | read | Detect WordPress installations |
| `hosting_importWordPressWebsiteV1` | DESTRUCTIVE | Import WordPress website |
| `hosting_installWordPressV1` | write | Install WordPress |
| `hosting_listWordPressInstallationsV1` | read | List WordPress installations |
| `hosting_listAvailableWordPressCoreUpdatesV1` | read | List available WordPress core updates |
| `hosting_getInstallationJWTTokenV1` | read | Get installation JWT token |
| `hosting_showWordPressCoreVersionV1` | read | Show WordPress core version |
| `hosting_updateWordPressCoreV1` | write | Update WordPress core |

## WordPress: LiteSpeed Cache

| Operation | Class | What it does |
|---|---|---|
| `hosting_purgeLiteSpeedCacheV1` | DESTRUCTIVE | Purge LiteSpeed Cache |
| `hosting_showLiteSpeedCacheStatusV1` | read | Show LiteSpeed Cache status |

## WordPress: Login

| Operation | Class | What it does |
|---|---|---|
| `hosting_createLoginLinksV1` | write | Create login links |

## WordPress: Maintenance

| Operation | Class | What it does |
|---|---|---|
| `hosting_showMaintenanceStatusV1` | read | Show maintenance status |
| `hosting_toggleMaintenanceModeV1` | write | Toggle maintenance mode |

## WordPress: Object Cache

| Operation | Class | What it does |
|---|---|---|
| `hosting_showMemcachedObjectCacheStatusV1` | read | Show Memcached object cache status |
| `hosting_toggleMemcachedObjectCacheV1` | write | Toggle Memcached object cache |

## WordPress: Plugins

| Operation | Class | What it does |
|---|---|---|
| `hosting_activateWordPressPluginV1` | write | Activate WordPress plugin |
| `hosting_deactivateWordPressPluginV1` | write | Deactivate WordPress plugin |
| `hosting_deployWordPressPluginV1` | DESTRUCTIVE | Deploy WordPress plugin |
| `hosting_installWordPressPluginsV1` | write | Install WordPress plugins |
| `hosting_listAvailableWordPressPluginsV1` | read | List available WordPress plugins |
| `hosting_listInstalledWordPressPluginsV1` | read | List installed WordPress plugins |
| `hosting_searchWordPressPluginsV1` | read | Search WordPress plugins |
| `hosting_listSuggestedWordPressPluginsV1` | read | List suggested WordPress plugins |
| `hosting_checkIfWooCommerceIsInstalledV1` | read | Check if WooCommerce is installed |
| `hosting_uninstallWordPressPluginsV1` | DESTRUCTIVE | Uninstall WordPress plugins |
| `hosting_updateHostingerWordPressPluginV1` | write | Update Hostinger WordPress plugin |
| `hosting_updateWordPressPluginsV1` | write | Update WordPress plugins |

## WordPress: Themes

| Operation | Class | What it does |
|---|---|---|
| `hosting_activateWordPressThemeV1` | write | Activate WordPress theme |
| `hosting_deployWordPressThemeV1` | DESTRUCTIVE | Deploy WordPress theme |
| `hosting_installWordPressThemeV1` | write | Install WordPress theme |
| `hosting_listInstalledWordPressThemesV1` | read | List installed WordPress themes |
| `hosting_listWordPressThemesV1` | read | List WordPress themes |
| `hosting_uninstallWordPressThemesV1` | DESTRUCTIVE | Uninstall WordPress themes |
| `hosting_updateWordPressThemesV1` | write | Update WordPress themes |
