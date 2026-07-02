# /browserbase:scrape-page

Extract structured data from a URL the user gives you, using the Browserbase
MCP tools. Ask for the URL first if it wasn't provided, and ask what fields
they want (or infer a sensible schema from context — e.g. "prices" implies
`{name, price, url}` per item).

## Steps

1. Call `start` to open a session (reuses an existing one if already open).
2. Call `navigate` with the target URL.
3. If the page needs interaction first (cookie banner, "load more", pagination,
   login-walled content), use `observe` to find the right element before
   acting — don't guess selectors blind. Then `act` on what `observe` returns.
4. Call `extract` with a precise natural-language instruction describing the
   exact shape you want, e.g. "extract every product as {name, price, url,
   in_stock}" rather than "extract the products" — Stagehand's extraction
   quality tracks how specific the instruction is.
5. If the data spans multiple pages, repeat navigate → extract per page and
   merge results yourself; don't ask `extract` to paginate.
6. Call `end` when done, unless the user is likely to want more calls against
   the same session (e.g. they're about to ask you to scrape a second page
   from the same site) — session reuse is faster and cheaper than restarting.
7. Present the extracted data as a table or the format the user asked for.
   Note explicitly if some fields came back empty/null rather than silently
   dropping them.

## Notes

- Prefer `extract` over trying to parse raw HTML yourself — it's schema-aware
  and handles dynamic/JS-rendered content the raw DOM wouldn't show anyway.
- If `extract` returns nothing useful, don't retry the same instruction
  blindly — `observe` the page first to confirm the content actually loaded,
  then rephrase the instruction to match what's really on the page.
- See `skills/browserbase-automation/` for the full Stagehand tool contract
  and more prompt patterns.
