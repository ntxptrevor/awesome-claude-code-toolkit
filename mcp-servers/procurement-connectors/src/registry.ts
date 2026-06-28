import type { Adapter, SourceConfig } from "./types.js";
import { bonfireAdapter } from "./adapters/bonfire.js";
import { esbdAdapter } from "./adapters/esbd.js";
import { samgovAdapter } from "./adapters/samgov.js";
import { highergovAdapter } from "./adapters/highergov.js";
import { bidbananaAdapter } from "./adapters/bidbanana.js";
import { ionwaveAdapter } from "./adapters/ionwave.js";
import { jaggaerAdapter } from "./adapters/jaggaer.js";
import { makeConfigurableAdapter } from "./adapters/configurable.js";
import { demandstarAdapter, planetbidsAdapter } from "./adapters/browser-portal.js";

const opengovAdapter = makeConfigurableAdapter({
  platform: "opengov",
  configEnv: ["OPENGOV_BASE_URL", "OPENGOV_API_KEY"],
  reliability: "requires-config",
});

const govcloudAdapter = makeConfigurableAdapter({
  platform: "govcloud",
  configEnv: ["GOVCLOUD_BASE_URL", "GOVCLOUD_API_KEY"],
  reliability: "requires-config",
});

export interface SourceDef {
  name: string;
  displayName: string;
  adapter: Adapter;
  /** Static config baked into the named source (e.g. a Bonfire org). */
  fixed?: Partial<SourceConfig>;
  /** Env vars supplying apiKey / baseUrl for this source. */
  env?: { apiKey?: string; baseUrl?: string };
  notes?: string;
}

export const SOURCES: SourceDef[] = [
  // ---- Federal / national ----
  {
    name: "samgov",
    displayName: "SAM.gov (US federal opportunities)",
    adapter: samgovAdapter,
    env: { apiKey: "SAM_GOV_API_KEY" },
    notes: "Free api.data.gov key. Daily call caps apply.",
  },
  {
    name: "highergov",
    displayName: "HigherGov (gov contracting intelligence)",
    adapter: highergovAdapter,
    env: { apiKey: "HIGHERGOV_API_KEY", baseUrl: "HIGHERGOV_BASE_URL" },
    notes: "Requires a paid HigherGov subscription + API key.",
  },
  {
    name: "bidbanana",
    displayName: "BidBanana by The Bid Lab",
    adapter: bidbananaAdapter,
    env: { apiKey: "BIDBANANA_API_KEY" },
    notes: "Paid SaaS; API key provisioned by The Bid Lab.",
  },
  {
    name: "govcloud",
    displayName: "GovCloud (configurable — unresolved public portal)",
    adapter: govcloudAdapter,
    env: { apiKey: "GOVCLOUD_API_KEY", baseUrl: "GOVCLOUD_BASE_URL" },
    notes:
      "No public bid portal named 'GovCloud' was found. Point GOVCLOUD_BASE_URL at your intended source, or use samgov / the GovTribe MCP server for federal data.",
  },

  // ---- Texas state ----
  {
    name: "esbd",
    displayName: "Texas Electronic State Business Daily / TxSmartBuy",
    adapter: esbdAdapter,
    notes: "Public NetSuite search index; no auth. Covers UTD/UNT/A&M formal solicitations too.",
  },
  { name: "txsmartbuy", displayName: "TxSmartBuy (alias of ESBD)", adapter: esbdAdapter },

  // ---- Texas universities ----
  {
    name: "utd",
    displayName: "UT Dallas (Bonfire)",
    adapter: bonfireAdapter,
    fixed: { org: "utdallas" },
  },
  {
    name: "unt",
    displayName: "University of North Texas System (Jaggaer)",
    adapter: jaggaerAdapter,
    fixed: { org: "UNTS" },
    notes: "Jaggaer is browser-rendered; use 'esbd' for a machine-readable feed.",
  },
  {
    name: "texas-am",
    displayName: "Texas A&M University System (Jaggaer)",
    adapter: jaggaerAdapter,
    fixed: { org: "TAMU" },
    notes: "Jaggaer is browser-rendered; use 'esbd' for a machine-readable feed.",
  },

  // ---- Texas cities ----
  {
    name: "denton-tx",
    displayName: "City of Denton, TX (Ionwave)",
    adapter: ionwaveAdapter,
    fixed: { org: "dentontx" },
  },
  {
    name: "lewisville-tx",
    displayName: "City of Lewisville, TX (Bonfire)",
    adapter: bonfireAdapter,
    fixed: { org: "cityoflewisville" },
  },

  // ---- Top platforms (generic; supply an org/endpoint) ----
  {
    name: "bonfire",
    displayName: "Bonfire (any agency — supply 'org')",
    adapter: bonfireAdapter,
    notes: "Generic Bonfire RSS; pass org=<subdomain>.",
  },
  {
    name: "ionwave",
    displayName: "Ionwave (any agency — supply 'org')",
    adapter: ionwaveAdapter,
    notes: "Generic Ionwave scrape; pass org=<subdomain>.",
  },
  {
    name: "opengov",
    displayName: "OpenGov Procurement (configurable API)",
    adapter: opengovAdapter,
    env: { apiKey: "OPENGOV_API_KEY", baseUrl: "OPENGOV_BASE_URL" },
    notes: "Per-agency API; set OPENGOV_BASE_URL (JSON search URL with {q}/{limit}).",
  },
  { name: "demandstar", displayName: "DemandStar (browse portal)", adapter: demandstarAdapter },
  {
    name: "planetbids",
    displayName: "PlanetBids (browse portal)",
    adapter: planetbidsAdapter,
    env: { baseUrl: "PLANETBIDS_BASE_URL" },
  },
];

export function getSource(name: string): SourceDef | undefined {
  return SOURCES.find((s) => s.name === name.toLowerCase());
}

/** Resolve the runtime config for a source from its fixed values + environment. */
export function resolveConfig(def: SourceDef): SourceConfig {
  return {
    apiKey: def.env?.apiKey ? process.env[def.env.apiKey] : undefined,
    baseUrl: def.env?.baseUrl ? process.env[def.env.baseUrl] : undefined,
    org: def.fixed?.org,
  };
}

/** True when a source can run now (no missing credentials). */
export function isConfigured(def: SourceDef): boolean {
  const cfg = resolveConfig(def);
  if (def.adapter.auth === "api-key" && !cfg.apiKey) return false;
  if (def.adapter.reliability === "requires-config" && !cfg.baseUrl) return false;
  return true;
}
