/**
 * Environment-driven configuration. Everything is overridable so the server
 * stays portable: laptop, home server, Raspberry Pi, or a cloud VM.
 */

export type AuthMode = "owner" | "fleet";
export type Region = "na" | "eu" | "cn";

export interface TeslaConfig {
  /** "fleet" = official Fleet API (developer app). "owner" = legacy Owner API (app-style refresh token). */
  mode: AuthMode;
  region: Region;
  /** REST base for vehicle endpoints. */
  apiBase: string;
  /** OAuth token endpoint base. */
  authBase: string;
  clientId: string;
  clientSecret?: string;
  refreshToken?: string;
  /** Optional pre-issued access token (skips refresh until it expires). */
  accessToken?: string;
  /**
   * Optional Tesla vehicle-command HTTP proxy (github.com/teslamotors/vehicle-command).
   * 2021+ vehicles require signed commands on the Fleet API; point this at your
   * running tesla-http-proxy and commands are routed through it automatically.
   */
  commandProxyUrl?: string;
  /** Default vehicle when a tool call doesn't name one (VIN or numeric id). */
  defaultVehicle?: string;
  /** Where rotated tokens are cached between runs. */
  tokenCachePath: string;
  /** Demo mode: canned data, no network, no credentials needed. */
  mock: boolean;
}

const FLEET_BASES: Record<Region, string> = {
  na: "https://fleet-api.prd.na.vn.cloud.tesla.com",
  eu: "https://fleet-api.prd.eu.vn.cloud.tesla.com",
  cn: "https://fleet-api.prd.cn.vn.cloud.tesla.cn",
};

const OWNER_BASE = "https://owner-api.teslamotors.com";
const AUTH_BASE = "https://auth.tesla.com";
const AUTH_BASE_CN = "https://auth.tesla.cn";

export function loadConfig(env: NodeJS.ProcessEnv = process.env): TeslaConfig {
  const region = (env.TESLA_REGION || "na").toLowerCase() as Region;
  const explicitMode = env.TESLA_AUTH_MODE?.toLowerCase();
  const mode: AuthMode =
    explicitMode === "owner" || explicitMode === "fleet"
      ? explicitMode
      : env.TESLA_CLIENT_ID
        ? "fleet"
        : "owner";

  const apiBase =
    env.TESLA_API_BASE ||
    (mode === "fleet" ? FLEET_BASES[region] || FLEET_BASES.na : OWNER_BASE);

  return {
    mode,
    region,
    apiBase: apiBase.replace(/\/+$/, ""),
    authBase: (env.TESLA_AUTH_BASE || (region === "cn" ? AUTH_BASE_CN : AUTH_BASE)).replace(/\/+$/, ""),
    clientId: env.TESLA_CLIENT_ID || "ownerapi",
    clientSecret: env.TESLA_CLIENT_SECRET || undefined,
    refreshToken: env.TESLA_REFRESH_TOKEN || undefined,
    accessToken: env.TESLA_ACCESS_TOKEN || undefined,
    commandProxyUrl: env.TESLA_COMMAND_PROXY_URL?.replace(/\/+$/, "") || undefined,
    defaultVehicle: env.TESLA_VIN || env.TESLA_VEHICLE_ID || undefined,
    tokenCachePath: env.TESLA_TOKEN_CACHE || ".tesla-tokens.json",
    mock: env.TESLA_MOCK === "1" || env.TESLA_MOCK === "true",
  };
}
