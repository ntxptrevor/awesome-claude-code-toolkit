import { getJson } from "../http.js";
import type { Adapter, AuthKind, Opportunity, Reliability, SearchParams, SourceConfig } from "../types.js";

/**
 * Generic JSON adapter for sources that expose an API but whose exact contract
 * isn't bundled here — the caller supplies the base URL (and key) at runtime.
 *
 * Used for:
 *  - OpenGov Procurement (developer.opengov.com — per-agency API key/OAuth)
 *  - "GovCloud" (no public portal by that exact name resolved during research;
 *    point this at whatever endpoint the user actually means, or use samgov/
 *    the GovTribe MCP server for federal data).
 *
 * Set {SOURCE}_BASE_URL to a search URL that returns JSON. The literal token
 * {q} in the URL is replaced with the URL-encoded keywords; {limit} with the
 * limit. The response is searched for the first array of objects to map.
 */
function pick(obj: Record<string, unknown>, keys: string[]): string | undefined {
  for (const k of keys) {
    const v = obj[k];
    if (typeof v === "string" && v) return v;
    if (typeof v === "number") return String(v);
  }
  return undefined;
}

function firstArray(data: unknown): Record<string, unknown>[] {
  if (Array.isArray(data)) return data as Record<string, unknown>[];
  if (data && typeof data === "object") {
    for (const v of Object.values(data as Record<string, unknown>)) {
      if (Array.isArray(v) && v.length && typeof v[0] === "object") return v as Record<string, unknown>[];
    }
  }
  return [];
}

export function makeConfigurableAdapter(opts: {
  platform: string;
  configEnv: string[];
  auth?: AuthKind;
  reliability?: Reliability;
}): Adapter {
  return {
    platform: opts.platform,
    auth: opts.auth ?? "api-key",
    reliability: opts.reliability ?? "requires-config",
    configEnv: opts.configEnv,
    async search(params: SearchParams, cfg: SourceConfig): Promise<Opportunity[]> {
      if (!cfg.baseUrl) {
        throw new Error(
          `${opts.platform} needs a search endpoint. Set ${opts.configEnv[0]} to a JSON URL ` +
            `(use {q} and {limit} placeholders), and an API key if required.`
        );
      }
      const url = cfg.baseUrl
        .replace("{q}", encodeURIComponent(params.keywords ?? ""))
        .replace("{limit}", String(Math.min(params.limit ?? 25, 100)));
      const headers = cfg.apiKey ? { Authorization: `Bearer ${cfg.apiKey}` } : undefined;
      const data = await getJson(url, headers);
      return firstArray(data).map((r) => ({
        source: opts.platform,
        id: pick(r, ["id", "uuid", "number", "reference"]) ?? "",
        title: pick(r, ["title", "name", "subject", "projectName"]) ?? "(untitled)",
        agency: pick(r, ["agency", "organization", "department", "buyer", "entity"]),
        status: pick(r, ["status", "state"]),
        postedDate: pick(r, ["posted_date", "postedDate", "published", "openDate"]),
        dueDate: pick(r, ["due_date", "dueDate", "close_date", "closeDate", "deadline"]),
        url: pick(r, ["url", "link", "href", "portalUrl"]),
        description: pick(r, ["description", "summary"]),
        raw: params.verbose ? r : undefined,
      }));
    },
  };
}
