# Hostinger operations: billing

Generated from Hostinger API spec 2.13.1. Run any row with `hostinger_call`. Get the argument schema first with `hostinger_describe`.

## Billing: Catalog

| Operation | Class | What it does |
|---|---|---|
| `billing_getCatalogItemListV1` | read | Get catalog item list |

## Billing: Orders

| Operation | Class | What it does |
|---|---|---|
| `billing_createPurchaseOrderV1` | SPENDS MONEY | Create purchase order |

## Billing: Payment methods

| Operation | Class | What it does |
|---|---|---|
| `billing_setDefaultPaymentMethodV1` | write | Set default payment method |
| `billing_deletePaymentMethodV1` | DESTRUCTIVE | Delete payment method |
| `billing_getPaymentMethodListV1` | read | Get payment method list |

## Billing: Subscriptions

| Operation | Class | What it does |
|---|---|---|
| `billing_getSubscriptionListV1` | read | Get subscription list |
| `billing_disableAutoRenewalV1` | SPENDS MONEY | Disable auto-renewal |
| `billing_enableAutoRenewalV1` | SPENDS MONEY | Enable auto-renewal |
| `billing_renewSubscriptionV1` | SPENDS MONEY | Renew subscription |
