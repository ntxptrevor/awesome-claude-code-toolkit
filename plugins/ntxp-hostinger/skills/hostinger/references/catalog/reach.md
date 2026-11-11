# Hostinger operations: reach

Generated from Hostinger API spec 2.13.1. Run any row with `hostinger_call`. Get the argument schema first with `hostinger_describe`.

## Reach: Automations

| Operation | Class | What it does |
|---|---|---|
| `reach_getAutomationDetailsV1` | read | Get automation details |
| `reach_listAutomationsV1` | read | List automations |
| `reach_listAutomationStepsV1` | read | List automation steps |

## Reach: Campaigns

| Operation | Class | What it does |
|---|---|---|
| `reach_getCampaignDetailsV1` | read | Get campaign details |
| `reach_listCampaignsV1` | read | List campaigns |
| `reach_createADraftCampaignV1` | write | Create a draft campaign |
| `reach_getCampaignPerformanceV1` | read | Get campaign performance |

## Reach: Contact Fields

| Operation | Class | What it does |
|---|---|---|
| `reach_updateAContactFieldV1` | write | Update a contact field |
| `reach_deleteAContactFieldV1` | DESTRUCTIVE | Delete a contact field |
| `reach_listContactFieldsV1` | read | List contact fields |
| `reach_createAContactFieldV1` | write | Create a contact field |

## Reach: Contacts

| Operation | Class | What it does |
|---|---|---|
| `reach_deleteAContactV1` | DESTRUCTIVE | Delete a contact (deprecated) |
| `reach_listContactGroupsV1` | read | List contact groups (deprecated) |
| `reach_listContactsV1` | read | List contacts (deprecated) |
| `reach_createANewContactV1` | write | Create a new contact (deprecated) |
| `reach_getContactDetailsV1` | read | Get contact details |
| `reach_updateAContactV1` | write | Update a contact |
| `reach_deleteAProfileContactV1` | DESTRUCTIVE | Delete a profile contact |
| `reach_createContactsInBulkV1` | write | Create contacts in bulk |
| `reach_listProfileContactsV1` | read | List profile contacts |
| `reach_createNewContactsV1` | write | Create new contacts |

## Reach: Forms

| Operation | Class | What it does |
|---|---|---|
| `reach_getFormDetailsV1` | read | Get form details |
| `reach_updateFormV1` | write | Update form |
| `reach_deleteFormV1` | DESTRUCTIVE | Delete form |
| `reach_duplicateFormV1` | write | Duplicate form |
| `reach_listFormsV1` | read | List forms |
| `reach_createFormV1` | write | Create form |
| `reach_addFormSubmitterTagsV1` | write | Add form submitter tags |
| `reach_removeFormSubmitterTagV1` | DESTRUCTIVE | Remove form submitter tag |
| `reach_updateFormTemplateV1` | write | Update form template |

## Reach: Integrations

| Operation | Class | What it does |
|---|---|---|
| `reach_connectEcommerceStoreV1` | write | Connect Ecommerce store |
| `reach_disconnectEcommerceStoreV1` | DESTRUCTIVE | Disconnect Ecommerce store |
| `reach_listEcommerceStoresV1` | read | List Ecommerce stores |
| `reach_listConnectedWebsitesV1` | read | List connected websites |
| `reach_connectAIWebsiteBuilderSiteV1` | write | Connect AI Website Builder site |
| `reach_disconnectAIWebsiteBuilderSiteV1` | DESTRUCTIVE | Disconnect AI Website Builder site |
| `reach_disconnectWordPressSiteV1` | DESTRUCTIVE | Disconnect WordPress site |

## Reach: Profiles

| Operation | Class | What it does |
|---|---|---|
| `reach_getConnectedSendingDomainV1` | read | Get connected sending domain |
| `reach_connectSendingDomainV1` | write | Connect sending domain |
| `reach_deleteSendingDomainV1` | DESTRUCTIVE | Delete sending domain |
| `reach_getProfileDomainDNSStatusV1` | read | Get profile domain DNS status |
| `reach_listPlanFeatureAccessV1` | read | List plan feature access |
| `reach_getRemainingPlanLimitsV1` | read | Get remaining plan limits |
| `reach_listProfilesV1` | read | List Profiles |
| `reach_getProfileSettingsV1` | read | Get profile settings |
| `reach_updateProfileSettingsV1` | write | Update profile settings |

## Reach: Segments

| Operation | Class | What it does |
|---|---|---|
| `reach_listSegmentsV1` | read | List segments (deprecated) |
| `reach_createANewContactSegmentV1` | write | Create a new contact segment (deprecated) |
| `reach_countProfileSegmentContactsV1` | read | Count profile segment contacts |
| `reach_listProfileSegmentContactsV1` | read | List profile segment contacts |
| `reach_getProfileSegmentDetailsV1` | read | Get profile segment details |
| `reach_updateAProfileSegmentV1` | write | Update a profile segment |
| `reach_deleteAProfileSegmentV1` | DESTRUCTIVE | Delete a profile segment |
| `reach_listSegmentFilterAttributesV1` | read | List segment filter attributes |
| `reach_previewContactsMatchingConditionsV1` | write | Preview contacts matching conditions |
| `reach_listProfileSegmentsV1` | read | List profile segments |
| `reach_createAProfileSegmentV1` | write | Create a profile segment |
| `reach_listSegmentContactsV1` | read | List segment contacts (deprecated) |
| `reach_getSegmentDetailsV1` | read | Get segment details (deprecated) |

## Reach: Tags

| Operation | Class | What it does |
|---|---|---|
| `reach_assignAContactToATagV1` | write | Assign a contact to a tag |
| `reach_removeAContactFromATagV1` | DESTRUCTIVE | Remove a contact from a tag |
| `reach_assignContactsToATagV1` | write | Assign contacts to a tag |
| `reach_removeContactsFromATagV1` | DESTRUCTIVE | Remove contacts from a tag |
| `reach_renameATagV1` | write | Rename a tag |
| `reach_deleteATagV1` | DESTRUCTIVE | Delete a tag |
| `reach_listProfileTagsV1` | read | List profile tags |
| `reach_createOrFindTagsV1` | write | Create or find tags |

## Reach: Templates

| Operation | Class | What it does |
|---|---|---|
| `reach_listEmailTemplatesV1` | read | List email templates |
| `reach_createAnEmailTemplateV1` | write | Create an email template |
| `reach_getEmailTemplateV1` | read | Get email template |
