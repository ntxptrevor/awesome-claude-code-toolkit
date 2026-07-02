#!/usr/bin/env node
/**
 * Interactive helper to obtain a Tesla refresh token (owner/app-style auth)
 * with the standard OAuth2 PKCE flow — the same tokens the mobile app uses.
 *
 *   node scripts/get-refresh-token.mjs
 *
 * 1. Opens (prints) a tesla.com login URL — sign in with your Tesla account
 *    (MFA supported; passkeys work too).
 * 2. After login the browser lands on a "Page Not Found" at
 *    https://auth.tesla.com/void/callback?code=...  — that's expected.
 * 3. Paste that full URL back here; the script exchanges it for tokens and
 *    prints the TESLA_REFRESH_TOKEN to export.
 *
 * Nothing is sent anywhere except auth.tesla.com.
 */

import { createHash, randomBytes } from "node:crypto";
import { createInterface } from "node:readline/promises";

const AUTH_BASE = process.env.TESLA_AUTH_BASE || "https://auth.tesla.com";
const REDIRECT = `${AUTH_BASE}/void/callback`;

const b64url = (buf) => buf.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const verifier = b64url(randomBytes(64));
const challenge = b64url(createHash("sha256").update(verifier).digest());
const state = b64url(randomBytes(12));

const authUrl =
  `${AUTH_BASE}/oauth2/v3/authorize?` +
  new URLSearchParams({
    client_id: "ownerapi",
    code_challenge: challenge,
    code_challenge_method: "S256",
    redirect_uri: REDIRECT,
    response_type: "code",
    scope: "openid email offline_access",
    state,
  });

console.log("\n1) Open this URL in a browser and sign in to your Tesla account:\n");
console.log(`   ${authUrl}\n`);
console.log('2) After login you will land on a "Page Not Found" — that is normal.');
console.log("   Copy the FULL address bar URL (starts with " + REDIRECT + ").\n");

const rl = createInterface({ input: process.stdin, output: process.stdout });
const pasted = (await rl.question("3) Paste that URL here: ")).trim();
rl.close();

let code;
try {
  code = new URL(pasted).searchParams.get("code");
} catch {
  code = null;
}
if (!code) {
  console.error("\nCould not find ?code=... in what you pasted. Run the script again.");
  process.exit(1);
}

const res = await fetch(`${AUTH_BASE}/oauth2/v3/token`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    grant_type: "authorization_code",
    client_id: "ownerapi",
    code,
    code_verifier: verifier,
    redirect_uri: REDIRECT,
  }),
});
if (!res.ok) {
  console.error(`\nToken exchange failed (${res.status}):`, (await res.text()).slice(0, 400));
  process.exit(1);
}
const tokens = await res.json();

console.log("\n✅ Success. Add this to your environment (keep it secret — it IS your car key):\n");
console.log(`export TESLA_REFRESH_TOKEN="${tokens.refresh_token}"`);
console.log("\nOptional short-lived access token (expires in ~" + Math.round((tokens.expires_in ?? 3600) / 60) + " min):");
console.log(`export TESLA_ACCESS_TOKEN="${tokens.access_token}"`);
