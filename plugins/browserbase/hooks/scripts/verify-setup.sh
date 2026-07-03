#!/usr/bin/env bash
# verify-setup.sh  (SessionStart hook)
# Auto-discovers BROWSERBASE_API_KEY from all known credential locations,
# registers it where missing, and emits a context hint with the result.
# Never asks permission — notifies only.

FOUND_KEY=""
FOUND_IN=""
REGISTERED=()

# ─── Search for the key across all known locations ──────────────────────────

# 1. Environment variable (already exported)
if [ -n "${BROWSERBASE_API_KEY:-}" ]; then
  FOUND_KEY="$BROWSERBASE_API_KEY"
  FOUND_IN="environment variable"
fi

# 2. .env files
if [ -z "$FOUND_KEY" ]; then
  for envfile in .env .env.local .env.development .env.production; do
    if [ -f "$envfile" ] && grep -q "^BROWSERBASE_API_KEY=" "$envfile" 2>/dev/null; then
      val=$(grep "^BROWSERBASE_API_KEY=" "$envfile" | head -1 | cut -d= -f2-)
      if [ -n "$val" ] && [[ "$val" != "<"* ]] && [[ "$val" != "\${"* ]]; then
        FOUND_KEY="$val"
        FOUND_IN="$envfile"
        break
      fi
    fi
  done
fi

# 3. MCP config files
if [ -z "$FOUND_KEY" ]; then
  for mcpfile in mcp-configs/browserbase.json .mcp.json; do
    if [ -f "$mcpfile" ]; then
      val=$(grep -oP '"BROWSERBASE_API_KEY"\s*:\s*"\K[^"]+' "$mcpfile" 2>/dev/null || true)
      if [ -n "$val" ] && [[ "$val" != "<"* ]] && [[ "$val" != "\${"* ]]; then
        FOUND_KEY="$val"
        FOUND_IN="$mcpfile"
        break
      fi
    fi
  done
fi

# 4. Claude settings
if [ -z "$FOUND_KEY" ]; then
  for settings in .claude/settings.local.json .claude/settings.json "$HOME/.claude/settings.json"; do
    if [ -f "$settings" ]; then
      val=$(grep -oP '"BROWSERBASE_API_KEY"\s*:\s*"\K[^"]+' "$settings" 2>/dev/null || true)
      if [ -n "$val" ] && [[ "$val" != "<"* ]] && [[ "$val" != "\${"* ]]; then
        FOUND_KEY="$val"
        FOUND_IN="$settings"
        break
      fi
    fi
  done
fi

# 5. Shell profiles
if [ -z "$FOUND_KEY" ]; then
  for profile in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.bash_profile" "$HOME/.profile"; do
    if [ -f "$profile" ]; then
      val=$(grep -oP 'export BROWSERBASE_API_KEY=["'"'"']?\K[^"'"'"'\s]+' "$profile" 2>/dev/null || true)
      if [ -n "$val" ] && [[ "$val" != "<"* ]]; then
        FOUND_KEY="$val"
        FOUND_IN="$profile"
        break
      fi
    fi
  done
fi

# ─── If not found anywhere, emit a hint ─────────────────────────────────────
if [ -z "$FOUND_KEY" ]; then
  msg="[browserbase] BROWSERBASE_API_KEY not found in environment, .env, MCP configs, Claude settings, or shell profiles. Run /browserbase:setup or set the key at https://browserbase.com/settings."
  echo "{\"hookSpecificOutput\":{\"hookEventName\":\"SessionStart\",\"additionalContext\":\"$msg\"}}"
  exit 0
fi

# ─── Auto-register into .env if missing ──────────────────────────────────────
if [ -f .env ]; then
  if ! grep -q "^BROWSERBASE_API_KEY=" .env 2>/dev/null; then
    echo "BROWSERBASE_API_KEY=$FOUND_KEY" >> .env
    REGISTERED+=(".env")
  fi
else
  echo "BROWSERBASE_API_KEY=$FOUND_KEY" > .env
  REGISTERED+=(".env (created)")
fi

# ─── Auto-register into mcp-configs/browserbase.json if placeholder ─────────
if [ -f mcp-configs/browserbase.json ]; then
  current=$(grep -oP '"BROWSERBASE_API_KEY"\s*:\s*"\K[^"]+' mcp-configs/browserbase.json 2>/dev/null || true)
  if [[ "$current" == "<"* ]] || [ -z "$current" ]; then
    sed -i "s|<your-browserbase-api-key>|$FOUND_KEY|" mcp-configs/browserbase.json
    REGISTERED+=("mcp-configs/browserbase.json")
  fi
fi

# ─── Emit notification ──────────────────────────────────────────────────────
if [ ${#REGISTERED[@]} -gt 0 ]; then
  locs=$(printf ", %s" "${REGISTERED[@]}")
  locs="${locs:2}"
  msg="[browserbase] Auto-registered BROWSERBASE_API_KEY (found in $FOUND_IN) into: $locs. No action needed."
  echo "{\"hookSpecificOutput\":{\"hookEventName\":\"SessionStart\",\"additionalContext\":\"$msg\"}}"
else
  # Everything already configured — check CLI
  if ! command -v browse &>/dev/null; then
    msg="[browserbase] API key is configured but the browse CLI is not installed. Run: npm install -g browse@latest"
    echo "{\"hookSpecificOutput\":{\"hookEventName\":\"SessionStart\",\"additionalContext\":\"$msg\"}}"
  fi
  # Silent if everything is set up
fi
