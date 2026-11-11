# Hostinger operations: ecommerce

Generated from Hostinger API spec 2.13.1. Run any row with `hostinger_call`. Get the argument schema first with `hostinger_describe`.

## Ecommerce: Discounts

| Operation | Class | What it does |
|---|---|---|
| `ecommerce_listDiscountsV1` | read | List discounts |
| `ecommerce_createADiscountV1` | write | Create a discount |

## Ecommerce: Miscellaneous

| Operation | Class | What it does |
|---|---|---|
| `ecommerce_getCustomStorefrontSetupInstructionsV1` | read | Get custom storefront setup instructions |

## Ecommerce: Orders

| Operation | Class | What it does |
|---|---|---|
| `ecommerce_cancelAnOrderV1` | DESTRUCTIVE | Cancel an order |
| `ecommerce_fulfilAnOrderV1` | write | Fulfil an order |
| `ecommerce_listStoreOrdersV1` | read | List store orders |
| `ecommerce_retrieveAnOrderV1` | read | Retrieve an order |

## Ecommerce: Payments

| Operation | Class | What it does |
|---|---|---|
| `ecommerce_enableManualPaymentMethodV1` | write | Enable manual payment method |
| `ecommerce_createAPaymentProviderConnectLinkV1` | write | Create a payment provider connect link |
| `ecommerce_listStorePaymentProvidersV1` | read | List store payment providers |

## Ecommerce: Product variants

| Operation | Class | What it does |
|---|---|---|
| `ecommerce_updateProductVariantsInBatchV1` | write | Update product variants in batch |
| `ecommerce_deleteAProductVariantV1` | DESTRUCTIVE | Delete a product variant |
| `ecommerce_listProductVariantsV1` | read | List product variants |
| `ecommerce_createAProductVariantV1` | write | Create a product variant |

## Ecommerce: Products

| Operation | Class | What it does |
|---|---|---|
| `ecommerce_createAProductImageUploadURLV1` | write | Create a product image upload URL |
| `ecommerce_updateAProductV1` | write | Update a product |
| `ecommerce_deleteAProductV1` | DESTRUCTIVE | Delete a product |
| `ecommerce_createDigitalProductV1` | write | Create digital product |
| `ecommerce_listProductsV1` | read | List products |
| `ecommerce_createPhysicalProductV1` | write | Create physical product |
| `ecommerce_uploadAndAttachAProductImageV1` | write | Upload and attach a product image |

## Ecommerce: Sales channels

| Operation | Class | What it does |
|---|---|---|
| `ecommerce_listSalesChannelsV1` | read | List sales channels |
| `ecommerce_createASalesChannelV1` | write | Create a sales channel |
| `ecommerce_updateSalesChannelV1` | write | Update sales channel |

## Ecommerce: Shipping

| Operation | Class | What it does |
|---|---|---|
| `ecommerce_setStoreShippingV1` | write | Set store shipping |

## Ecommerce: Stores

| Operation | Class | What it does |
|---|---|---|
| `ecommerce_deleteStoreV1` | DESTRUCTIVE | Delete store |
| `ecommerce_getStoresV1` | read | Get stores |
| `ecommerce_createStoreV1` | write | Create store |
| `ecommerce_getStoreMetadataV1` | read | Get store metadata |
