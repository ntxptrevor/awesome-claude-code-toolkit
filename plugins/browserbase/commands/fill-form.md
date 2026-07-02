# /browserbase:fill-form

Fill in and submit a web form on the user's behalf using the Browserbase MCP
tools. Ask for the URL and the field values first if not already given.
**Never** submit a form containing payment details, account deletion, or any
other high-stakes action without the user explicitly confirming the exact
values right before submission.

## Steps

1. Call `start`, then `navigate` to the form's URL.
2. Call `observe` with an instruction like "find the form fields for name,
   email, and message" — this returns the actual interactive elements
   Stagehand sees, which is more reliable than guessing field order.
3. For each field, call `act` with a specific instruction, e.g. `act("type
   'Jane Doe' into the Name field")`. One `act` call per logical action reads
   more reliably than one giant compound instruction.
4. Before submitting, call `extract` to read back the filled values from the
   page and confirm they match what the user asked for. Show this
   confirmation to the user for anything irreversible (payments, deletions,
   sending on someone's behalf) and wait for their go-ahead.
5. Call `act("click the Submit button")` (or equivalent) to submit.
6. Call `extract` again to confirm the success state (confirmation message,
   redirect, order number, etc.) and report it back. If the page shows a
   validation error instead, read the error text with `extract` and retry the
   specific field rather than resubmitting blind.
7. Call `end` when the flow is complete.

## Notes

- If the form has a CAPTCHA, don't try to defeat it — tell the user and stop.
  Browserbase's Verified Identity feature (`VERIFIED` config, Scale plan) can
  help with bot-detection false positives, but that's a plan/config decision
  for the user, not something to route around silently.
- Treat any field asking for a password, SSN, card number, or similar as
  sensitive: don't echo the value back in full in your response.
