# Hostinger operations: mail

Generated from Hostinger API spec 2.13.1. Run any row with `hostinger_call`. Get the argument schema first with `hostinger_describe`.

## Mail: API Tokens

| Operation | Class | What it does |
|---|---|---|
| `mail_createAPITokenV1` | write | Create API token |
| `mail_revokeAPITokenV1` | DESTRUCTIVE | Revoke API token |
| `mail_listAPITokensV1` | read | List API tokens |

## Mail: Aliases

| Operation | Class | What it does |
|---|---|---|
| `mail_createAliasV1` | write | Create alias |
| `mail_deleteAliasV1` | DESTRUCTIVE | Delete alias |
| `mail_listAliasesV1` | read | List aliases |

## Mail: Autoreplies

| Operation | Class | What it does |
|---|---|---|
| `mail_createAutoreplyV1` | write | Create autoreply |
| `mail_updateAutoreplyV1` | write | Update autoreply |
| `mail_deleteAutoreplyV1` | DESTRUCTIVE | Delete autoreply |
| `mail_listAutorepliesV1` | read | List autoreplies |

## Mail: Catchalls

| Operation | Class | What it does |
|---|---|---|
| `mail_createCatchAllV1` | write | Create catch-all |
| `mail_deleteCatchAllV1` | DESTRUCTIVE | Delete catch-all |
| `mail_listCatchAllsV1` | read | List catch-alls |
| `mail_resendCatchAllConfirmationV1` | write | Resend catch-all confirmation |

## Mail: Forwarders

| Operation | Class | What it does |
|---|---|---|
| `mail_createForwarderV1` | write | Create forwarder |
| `mail_deleteForwarderV1` | DESTRUCTIVE | Delete forwarder |
| `mail_listForwardersV1` | read | List forwarders |
| `mail_resendForwarderConfirmationV1` | write | Resend forwarder confirmation |
| `mail_updateForwarderKeepCopySettingV1` | write | Update forwarder keep-copy setting |

## Mail: Logs

| Operation | Class | What it does |
|---|---|---|
| `mail_listAccessLogsV1` | read | List access logs |
| `mail_listActionLogsV1` | read | List action logs |
| `mail_listInboundLogsV1` | read | List inbound logs |
| `mail_listMailboxActionLogsV1` | read | List mailbox action logs |
| `mail_listOutboundLogsV1` | read | List outbound logs |

## Mail: Mailboxes

| Operation | Class | What it does |
|---|---|---|
| `mail_listMailboxesV1` | read | List mailboxes |
| `mail_createMailboxV1` | write | Create mailbox |
| `mail_deleteMailboxV1` | DESTRUCTIVE | Delete mailbox |
| `mail_changeMailboxPasswordV1` | write | Change mailbox password |

## Mail: Orders

| Operation | Class | What it does |
|---|---|---|
| `mail_listOrdersV1` | read | List orders |
| `mail_getOrderPlanV1` | read | Get order plan |

## Mail: Webhooks

| Operation | Class | What it does |
|---|---|---|
| `mail_createWebhookV1` | write | Create webhook |
| `mail_listWebhookDeliveryLogsV1` | read | List webhook delivery logs |
| `mail_getWebhookV1` | read | Get webhook |
| `mail_updateWebhookV1` | write | Update webhook |
| `mail_deleteWebhookV1` | DESTRUCTIVE | Delete webhook |
| `mail_listWebhooksV1` | read | List webhooks |
| `mail_regenerateWebhookSecretV1` | write | Regenerate webhook secret |
| `mail_testWebhookV1` | write | Test webhook |
