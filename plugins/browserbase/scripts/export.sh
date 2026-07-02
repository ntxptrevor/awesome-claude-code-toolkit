#!/usr/bin/env bash
# Export the Browserbase connector as two prepackaged, self-contained
# artifacts (nothing to install on the target beyond Node.js):
#
#   build/browserbase.mcpb           MCP Bundle — one-click install in Claude
#                                    Desktop (or `npx @anthropic-ai/mcpb install`)
#   build/browserbase-plugin.zip     Claude Code plugin with @browserbasehq/mcp
#                                    vendored in vendor/node_modules, so
#                                    bootstrap.mjs runs with no npx/network
#                                    fetch and no repo clone required
#
# Usage: scripts/export.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
BUILD="$ROOT/build"
mkdir -p "$BUILD"
cd "$ROOT"

echo "==> Vendoring @browserbasehq/mcp"
PAYLOAD="$WORK/payload"
mkdir -p "$PAYLOAD"
cat > "$PAYLOAD/package.json" <<'EOF'
{ "name": "browserbase-vendor-payload", "private": true, "dependencies": { "@browserbasehq/mcp": "latest" } }
EOF
( cd "$PAYLOAD" && npm install --omit=dev --no-audit --no-fund --silent )

# --- 1. MCP Bundle (.mcpb) ----------------------------------------------------
echo "==> Building browserbase.mcpb"
MCPB="$WORK/mcpb"
mkdir -p "$MCPB/vendor"
cp -R "$PAYLOAD/node_modules" "$MCPB/vendor/node_modules"
cp manifest.json "$MCPB/manifest.json"
( cd "$MCPB" && zip -qr "$BUILD/browserbase.mcpb" . )

# --- 2. Self-contained Claude Code plugin -------------------------------------
echo "==> Building browserbase-plugin.zip"
PLUG="$WORK/plugin/browserbase"
mkdir -p "$PLUG"
cp -R "$ROOT/." "$PLUG/"
rm -rf "$PLUG/build" "$PLUG/scripts"
mkdir -p "$PLUG/vendor"
cp -R "$PAYLOAD/node_modules" "$PLUG/vendor/node_modules"
( cd "$WORK/plugin" && zip -qr "$BUILD/browserbase-plugin.zip" browserbase )

echo "==> Done:"
ls -lh "$BUILD"/browserbase.mcpb "$BUILD"/browserbase-plugin.zip
