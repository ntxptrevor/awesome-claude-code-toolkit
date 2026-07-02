# /browserbase:browse-agent

Open-ended browsing: the user describes a goal ("find the cheapest flight
from X to Y on this site", "check if this product is back in stock and tell
me", "log into my dashboard and pull this month's numbers") rather than a
fixed scrape or form. Drive the Browserbase tools yourself in a loop instead
of a fixed script.

## Loop

1. `start` a session if one isn't already open.
2. `navigate` to the best starting URL for the goal (ask the user if it's
   genuinely ambiguous which site to start from).
3. Repeat until the goal is met or you're stuck:
   - `observe` the page to see what's actually interactable right now —
     don't assume the DOM from memory or a previous run.
   - Decide the next single action toward the goal and `act` it.
   - `extract` whenever you need to read the current state (prices, results,
     confirmation text) to decide the next step or to answer the user.
4. Stop and ask the user if you hit: a login wall needing credentials you
   don't have, a CAPTCHA, a paywall, or an action with real-world
   consequences (purchase, irreversible submission, messaging a third
   party) — never guess your way through those.
5. Call `end` when the goal is reached or the task is abandoned, and give the
   user a clear summary of what you found/did, including any steps you
   skipped and why.

## Notes

- Keep each `act` call to one concrete action. Compound instructions
  ("search for X and click the first result and add it to cart") are harder
  for Stagehand to execute reliably than three separate calls.
- If the same `act`/`observe` pair will repeat often in this session (e.g.
  paginating search results), reuse the exact instruction text — Stagehand
  caches successful action plans per instruction, which is faster and
  cheaper than novel phrasing each time.
- If you're not sure a site allows automated browsing for this purpose, say
  so and let the user decide whether to proceed — this command is for
  legitimate personal/business automation, not for evading a site's terms of
  service or rate limits at scale.
- See `skills/browserbase-automation/` for deeper guidance on tool selection
  and failure recovery.
