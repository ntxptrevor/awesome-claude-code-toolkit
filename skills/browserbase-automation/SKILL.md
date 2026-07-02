---
name: browserbase-automation
description: Cloud browser automation with Browserbase and Stagehand — MCP tool contract, prompt patterns for act/observe/extract, session reuse, and failure recovery
---

# Browserbase Automation

Browserbase runs real, isolated cloud Chrome instances; [Stagehand](https://stagehand.dev/)
is the automation layer on top that lets you drive them with natural-language
instructions instead of brittle CSS selectors. The `@browserbasehq/mcp`
server exposes six tools built on this stack. This skill applies whether
you're calling those MCP tools directly, or writing a script against the
Stagehand SDK for more control.

## The 6 MCP tools

| Tool | Input | Use for |
|------|-------|---------|
| `start` | none | Open (or reuse) a cloud browser session |
| `navigate` | `{ url }` | Load a URL in the current session |
| `act` | `{ action }` | Perform one interaction: click, type, select, scroll |
| `observe` | `{ instruction }` | List interactable elements matching a description, without acting |
| `extract` | `{ instruction? }` | Pull structured data out of the current page |
| `end` | none | Close the session |

A session persists across calls until `end` — always `navigate` before
`act`/`extract`/`observe`, and reuse the session across a multi-step flow
rather than restarting it every call (each `start` spins up a fresh cloud
browser, which costs time and Browserbase minutes).

## Prompt patterns

Stagehand's reliability tracks the specificity of your instruction more than
almost anything else.

**`act` — one concrete action per call:**
```
Good: act("click the 'Add to Cart' button")
Good: act("type 'jane@example.com' into the Email field")
Bad:  act("search for shoes and click the first result and add it to cart")
```
Compound instructions fail more often and are harder to debug when they do —
you can't tell which of the three steps broke.

**`observe` before `act` on unfamiliar pages:**
Don't guess element text or position. `observe("find the cookie consent
button")` returns what's actually on the page right now; feed that result
into your next `act` instead of assuming a label that might not exist.

**`extract` — describe the exact output shape:**
```
Good: extract("extract every product as {name, price, url, in_stock}")
Bad:  extract("get the products")
```
Name every field you want, including ones that might be absent (`in_stock`
forces Stagehand to look for and report that signal instead of omitting it
silently). If you're using the Stagehand SDK directly rather than the MCP
tool, pass a Zod schema instead of relying on the instruction alone:

```typescript
import { z } from "zod";

const products = await page.extract({
  instruction: "extract every product listing",
  schema: z.object({
    products: z.array(z.object({
      name: z.string(),
      price: z.number(),
      url: z.string(),
      in_stock: z.boolean(),
    })),
  }),
});
```

**Repeat instructions verbatim for repeated actions.** Stagehand caches
successful action plans keyed on instruction text — paginating with the same
`act("click the Next Page button")` string on every loop iteration is
faster and cheaper than rephrasing each time.

## Multi-page and pagination

`extract` reads the current page only — it does not follow links or paginate
on its own. For multi-page data:

```
loop:
  navigate(page_url)            # or act("click Next") if it's client-side pagination
  extract("extract every row as {...}")
  merge results
until no more pages
```

Merge and dedupe results yourself; don't ask a single `extract` call to
describe more than what's currently rendered.

## Failure recovery

- **Empty/wrong `extract` result**: don't retry the same instruction. First
  `observe` to confirm the content actually loaded (SPA hydration, lazy
  loading, and infinite scroll are common culprits), then rephrase to match
  what's really on the page.
- **`act` reports success but nothing changed**: the target element may be
  in an iframe or behind an overlay (cookie banner, modal). `observe` again
  after dismissing anything blocking the viewport.
- **CAPTCHA or bot-detection wall**: don't try to defeat it programmatically.
  Browserbase's `--verified` flag (Verified Identity, Scale plan) reduces
  false-positive bot flags for legitimate automation; beyond that, stop and
  tell the user rather than attempting evasion.
- **Session expired mid-flow**: sessions have a max duration; if calls start
  failing after a long-running flow, `start` a fresh session and re-navigate
  rather than assuming state carried over.

## Speed and cost

- Reuse one session across a whole task instead of `start`/`end` per step —
  each `start` provisions a new cloud browser (seconds of latency, billed
  minutes).
- Set `KEEP_ALIVE` in config only if you genuinely need the session to
  survive idle gaps between tool calls; otherwise let it close naturally.
- Prefer the smallest model that reliably follows your `act`/`extract`
  instructions — the default `google/gemini-2.5-flash-lite` is tuned for
  this and is both fast and inexpensive; only switch models
  (`MODEL_NAME`/`MODEL_API_KEY`) if you're seeing accuracy problems it can't
  solve.
- Batch related reads into one `extract` call (e.g. "title, price, and
  rating" together) rather than three separate calls against the same page.

## Security and scope

- API keys belong in `~/.config/browserbase-mcp/config.json` (chmod 600) or
  the environment — never in code, prompts, or committed config.
- Treat form fields for passwords, payment info, or SSNs as sensitive: don't
  echo captured values back in full.
- Confirm with the user before any `act` that submits payment, deletes data,
  or sends something on their behalf — Stagehand executes what you tell it
  to, including mistakes.
- This is for legitimate personal/business automation. If a site's terms of
  service or robots.txt clearly prohibit automated access for the task at
  hand, say so and let the user decide rather than proceeding silently.

## Anti-patterns

- Writing your own DOM scraping/regex over raw HTML instead of `extract` —
  you lose Stagehand's handling of JS-rendered and dynamic content for no
  benefit.
- One giant `act` instruction covering a whole multi-step flow — split it
  per interaction so failures are attributable and retryable.
- Restarting the session (`end` + `start`) between every tool call — throws
  away context and multiplies latency/cost for no reliability gain.
- Vague `extract` instructions ("get the info") — always name the fields.
