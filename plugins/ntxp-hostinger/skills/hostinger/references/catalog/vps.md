# Hostinger operations: vps

Generated from Hostinger API spec 2.13.1. Run any row with `hostinger_call`. Get the argument schema first with `hostinger_describe`.

## VPS: Actions

| Operation | Class | What it does |
|---|---|---|
| `VPS_getActionDetailsV1` | read | Get action details |
| `VPS_getActionsV1` | read | Get actions |

## VPS: Backups

| Operation | Class | What it does |
|---|---|---|
| `VPS_getBackupsV1` | read | Get backups |
| `VPS_restoreBackupV1` | DESTRUCTIVE | Restore backup |

## VPS: Data centers

| Operation | Class | What it does |
|---|---|---|
| `VPS_getDataCenterListV1` | read | Get data center list |

## VPS: Docker Manager

| Operation | Class | What it does |
|---|---|---|
| `VPS_getProjectContainersV1` | read | Get project containers |
| `VPS_getProjectContentsV1` | read | Get project contents |
| `VPS_deleteProjectV1` | DESTRUCTIVE | Delete project |
| `VPS_getProjectListV1` | read | Get project list |
| `VPS_createNewProjectV1` | write | Create new project |
| `VPS_getProjectLogsV1` | read | Get project logs |
| `VPS_restartProjectV1` | write | Restart project |
| `VPS_startProjectV1` | write | Start project |
| `VPS_stopProjectV1` | DESTRUCTIVE | Stop project |
| `VPS_updateProjectV1` | write | Update project |

## VPS: Firewall

| Operation | Class | What it does |
|---|---|---|
| `VPS_activateFirewallV1` | write | Activate firewall |
| `VPS_deactivateFirewallV1` | write | Deactivate firewall |
| `VPS_getFirewallDetailsV1` | read | Get firewall details |
| `VPS_deleteFirewallV1` | DESTRUCTIVE | Delete firewall |
| `VPS_getFirewallListV1` | read | Get firewall list |
| `VPS_createNewFirewallV1` | write | Create new firewall |
| `VPS_updateFirewallRuleV1` | write | Update firewall rule |
| `VPS_deleteFirewallRuleV1` | DESTRUCTIVE | Delete firewall rule |
| `VPS_createFirewallRuleV1` | write | Create firewall rule |
| `VPS_replaceAllFirewallRulesInGroupV1` | write | Replace all firewall rules in group |
| `VPS_syncFirewallToAllAssignedVMsV1` | write | Sync firewall to all assigned VMs |
| `VPS_syncFirewallV1` | write | Sync firewall (deprecated) |

## VPS: Malware scanner

| Operation | Class | What it does |
|---|---|---|
| `VPS_getScanMetricsV1` | read | Get scan metrics |
| `VPS_installMonarxV1` | write | Install Monarx |
| `VPS_uninstallMonarxV1` | DESTRUCTIVE | Uninstall Monarx |

## VPS: OS Templates

| Operation | Class | What it does |
|---|---|---|
| `VPS_getTemplateDetailsV1` | read | Get template details |
| `VPS_getTemplatesV1` | read | Get templates |

## VPS: PTR records

| Operation | Class | What it does |
|---|---|---|
| `VPS_createPTRRecordV1` | write | Create PTR record |
| `VPS_deletePTRRecordV1` | DESTRUCTIVE | Delete PTR record |

## VPS: Post-install scripts

| Operation | Class | What it does |
|---|---|---|
| `VPS_getPostInstallScriptV1` | read | Get post-install script |
| `VPS_updatePostInstallScriptV1` | write | Update post-install script |
| `VPS_deletePostInstallScriptV1` | DESTRUCTIVE | Delete post-install script |
| `VPS_getPostInstallScriptsV1` | read | Get post-install scripts |
| `VPS_createPostInstallScriptV1` | write | Create post-install script |

## VPS: Public Keys

| Operation | Class | What it does |
|---|---|---|
| `VPS_attachPublicKeyV1` | write | Attach public key (deprecated) |
| `VPS_deletePublicKeyV1` | DESTRUCTIVE | Delete public key (deprecated) |
| `VPS_getPublicKeysV1` | read | Get public keys (deprecated) |
| `VPS_createPublicKeyV1` | write | Create public key (deprecated) |

## VPS: Recovery

| Operation | Class | What it does |
|---|---|---|
| `VPS_startRecoveryModeV1` | write | Start recovery mode |
| `VPS_stopRecoveryModeV1` | DESTRUCTIVE | Stop recovery mode |

## VPS: SSH Keys

| Operation | Class | What it does |
|---|---|---|
| `VPS_listVirtualMachineSSHKeysV1` | read | List virtual machine SSH keys |
| `VPS_addVirtualMachineSSHKeysV1` | write | Add virtual machine SSH keys |
| `VPS_removeVirtualMachineSSHKeysV1` | DESTRUCTIVE | Remove virtual machine SSH keys |

## VPS: Snapshots

| Operation | Class | What it does |
|---|---|---|
| `VPS_getSnapshotV1` | read | Get snapshot |
| `VPS_createSnapshotV1` | write | Create snapshot |
| `VPS_deleteSnapshotV1` | DESTRUCTIVE | Delete snapshot |
| `VPS_restoreSnapshotV1` | DESTRUCTIVE | Restore snapshot |

## VPS: Virtual machine

| Operation | Class | What it does |
|---|---|---|
| `VPS_getAttachedPublicKeysV1` | read | Get attached public keys (deprecated) |
| `VPS_setHostnameV1` | write | Set hostname |
| `VPS_resetHostnameV1` | DESTRUCTIVE | Reset hostname |
| `VPS_getVirtualMachineDetailsV1` | read | Get virtual machine details |
| `VPS_getVirtualMachinesV1` | read | Get virtual machines |
| `VPS_purchaseNewVirtualMachineV1` | SPENDS MONEY | Purchase new virtual machine |
| `VPS_getMetricsV1` | read | Get metrics |
| `VPS_setNameserversV1` | write | Set nameservers |
| `VPS_setPanelPasswordV1` | write | Set panel password |
| `VPS_recreateVirtualMachineV1` | DESTRUCTIVE | Recreate virtual machine |
| `VPS_restartVirtualMachineV1` | write | Restart virtual machine |
| `VPS_setRootPasswordV1` | write | Set root password |
| `VPS_setupPurchasedVirtualMachineV1` | SPENDS MONEY | Setup purchased virtual machine |
| `VPS_startVirtualMachineV1` | write | Start virtual machine |
| `VPS_stopVirtualMachineV1` | DESTRUCTIVE | Stop virtual machine |
