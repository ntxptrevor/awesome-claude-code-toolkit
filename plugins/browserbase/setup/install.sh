#!/usr/bin/env bash
# install.sh — Automated Browserbase plugin setup
# Discovers credential storage, auto-registers the API key everywhere it belongs,
# installs the browse CLI, and verifies connectivity.
# Notifies the user of every change but does not ask permission.

set -euo pipefail

REGISTERED=()
SKIPPED=()

echo "=== Browserbase Plugin Setup ==="

# ─── 1. Check Node.js ───────────────────────────────────────────────────────
if ! command -v node &>/dev/null; then
  echo "ERROR: Node.js is required but not installed."
  echo "Install it from https://nodejs.org or via your package manager."
  exit 1
fi
echo "[ok] Node.js $(node --version)"

# ─── 2. Install browse CLI if missing ────────────────────────────────────────
if command -v browse &>/dev/null; then
  echo "[ok] browse CLI already installed"
else
  echo "[..] Installing browse CLI..."
  npm install -g browse@latest 2>&1 | tail -1
  if command -v browse &>/dev/null; then
    echo "[ok] browse CLI installed"
  else
    echo "ERROR: browse CLI installation failed"
    exit 1
  fi
fi

# Remove deprecated CLIs that shadow browse
for pkg in @browserbasehq/cli @browserbasehq/browse-cli; do
  if npm list -g "$pkg" &>/dev/null 2>&1; then
    echo "[..] Removing deprecated $pkg..."
    npm uninstall -g "$pkg" 2>/dev/null || true
  fi
done

# ─── 3. Locate API key ──────────────────────────────────────────────────────
# Search order: env var → .env → .env.local → MCP configs → Claude settings
API_KEY="${BROWSERBASE_API_KEY:-}"

if [ -z "$API_KEY" ]; then
  for envfile in .env .env.local .env.development .env.production; do
    if [ -f "$envfile" ] && grep -q "^BROWSERBASE_API_KEY=" "$envfile" 2>/dev/null; then
      API_KEY=$(grep "^BROWSERBASE_API_KEY=" "$envfile" | head -1 | cut -d= -f2-)
      echo "[ok] Found BROWSERBASE_API_KEY in $envfile"
      break
    fi
  done
fi

if [ -z "$API_KEY" ]; then
  # Check MCP config files
  for mcpfile in mcp-configs/browserbase.json .mcp.json; do
    if [ -f "$mcpfile" ]; then
      found=$(grep -oP '"BROWSERBASE_API_KEY"\s*:\s*"\K[^"]+' "$mcpfile" 2>/dev/null || true)
      if [ -n "$found" ] && [[ "$found" != "<"* ]] && [[ "$found" != "\${"* ]]; then
        API_KEY="$found"
        echo "[ok] Found BROWSERBASE_API_KEY in $mcpfile"
        break
      fi
    fi
  done
fi

if [ -z "$API_KEY" ]; then
  # Check Claude settings files
  for settings in .claude/settings.json .claude/settings.local.json "$HOME/.claude/settings.json"; do
    if [ -f "$settings" ]; then
      found=$(grep -oP '"BROWSERBASE_API_KEY"\s*:\s*"\K[^"]+' "$settings" 2>/dev/null || true)
      if [ -n "$found" ] && [[ "$found" != "<"* ]] && [[ "$found" != "\${"* ]]; then
        API_KEY="$found"
        echo "[ok] Found BROWSERBASE_API_KEY in $settings"
        break
      fi
    fi
  done
fi

if [ -z "$API_KEY" ]; then
  echo ""
  echo "BROWSERBASE_API_KEY not found in any known location."
  echo "Get your key at: https://browserbase.com/settings"
  echo ""
  echo "Then either:"
  echo "  export BROWSERBASE_API_KEY=bb_live_..."
  echo "  OR add it to your .env file"
  echo "  OR re-run this setup after setting it"
  exit 1
fi

export BROWSERBASE_API_KEY="$API_KEY"

# ─── 4. Auto-register key in all credential locations ────────────────────────
# Writes the key to every relevant location, skipping if already present.

# 4a. .env (project root)
if [ -f .env ]; then
  if grep -q "^BROWSERBASE_API_KEY=" .env 2>/dev/null; then
    current=$(grep "^BROWSERBASE_API_KEY=" .env | head -1 | cut -d= -f2-)
    if [ "$current" != "$API_KEY" ] && [[ "$current" == "<"* || -z "$current" ]]; then
      sed -i "s|^BROWSERBASE_API_KEY=.*|BROWSERBASE_API_KEY=$API_KEY|" .env
      REGISTERED+=(".env (updated placeholder)")
    else
      SKIPPED+=(".env (already set)")
    fi
  else
    echo "BROWSERBASE_API_KEY=$API_KEY" >> .env
    REGISTERED+=(".env (added)")
  fi
else
  echo "BROWSERBASE_API_KEY=$API_KEY" > .env
  REGISTERED+=(".env (created)")
fi

# 4b. mcp-configs/browserbase.json — update placeholder
if [ -f mcp-configs/browserbase.json ]; then
  current=$(grep -oP '"BROWSERBASE_API_KEY"\s*:\s*"\K[^"]+' mcp-configs/browserbase.json 2>/dev/null || true)
  if [[ "$current" == "<"* ]] || [ -z "$current" ]; then
    sed -i "s|<your-browserbase-api-key>|$API_KEY|" mcp-configs/browserbase.json
    REGISTERED+=("mcp-configs/browserbase.json (updated placeholder)")
  else
    SKIPPED+=("mcp-configs/browserbase.json (already set)")
  fi
fi

# 4c. Claude project settings — add env var if settings exist
for settings_dir in .claude; do
  settings_file="$settings_dir/settings.local.json"
  if [ -d "$settings_dir" ]; then
    if [ -f "$settings_file" ]; then
      if grep -q "BROWSERBASE_API_KEY" "$settings_file" 2>/dev/null; then
        SKIPPED+=("$settings_file (already referenced)")
      else
        # Add to env section if the file has one, otherwise note it
        if grep -q '"env"' "$settings_file" 2>/dev/null; then
          SKIPPED+=("$settings_file (has env block, manual add recommended)")
        else
          SKIPPED+=("$settings_file (no env block)")
        fi
      fi
    fi
  fi
done

# 4d. Shell profile — add export if not already sourced
for profile in "$HOME/.bashrc" "$HOME/.zshrc"; do
  if [ -f "$profile" ]; then
    if grep -q "BROWSERBASE_API_KEY" "$profile" 2>/dev/null; then
      SKIPPED+=("$profile (already has export)")
    else
      echo "" >> "$profile"
      echo "# Browserbase API key (added by browserbase plugin setup)" >> "$profile"
      echo "export BROWSERBASE_API_KEY=\"$API_KEY\"" >> "$profile"
      REGISTERED+=("$profile (added export)")
    fi
  fi
done

# ─── 5. Verify API access ───────────────────────────────────────────────────
echo "[..] Verifying API access..."
result=$(browse cloud projects list --json 2>&1 | grep -v "Update available" | grep -v "npm install" | grep -v "DeprecationWarning")
if echo "$result" | grep -q '"id"'; then
  echo "[ok] API key verified — connected to Browserbase"
else
  echo "ERROR: API key verification failed"
  echo "$result"
  exit 1
fi

# ─── 6. Summary ─────────────────────────────────────────────────────────────
echo ""
echo "=== Setup Complete ==="
echo ""

if [ ${#REGISTERED[@]} -gt 0 ]; then
  echo "Auto-registered BROWSERBASE_API_KEY in:"
  for loc in "${REGISTERED[@]}"; do
    echo "  + $loc"
  done
fi

if [ ${#SKIPPED[@]} -gt 0 ]; then
  echo ""
  echo "Already configured (no changes):"
  for loc in "${SKIPPED[@]}"; do
    echo "  - $loc"
  done
fi

echo ""
echo "Available commands:"
echo "  /browserbase:scrape-page   — Scrape and extract data from a web page"
echo "  /browserbase:fill-form     — Fill out and submit a web form"
echo "  /browserbase:browse-agent  — Run an open-ended browsing agent"
echo ""
echo "Dashboard: https://www.browserbase.com/sessions"
echo "Docs:      https://docs.browserbase.com"
