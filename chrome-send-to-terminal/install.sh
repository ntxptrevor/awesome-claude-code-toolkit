#!/bin/bash
# Installs the native messaging host for the "Send to Terminal" extension.
# macOS only. Runs as your user, sudo is not needed.
#
#   ./install.sh              install for Chrome, Chromium, Brave, and Edge
#   ./install.sh --uninstall  remove the host and its manifests

set -euo pipefail

HOST_NAME="com.ntxp.send_to_terminal"
# Fixed by the "key" field in extension/manifest.json.
EXTENSION_ID="bhkllnkmkbbchnbggpipembijnofhcjj"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/Library/Application Support/SendToTerminal"
SUPPORT="$HOME/Library/Application Support"
BROWSER_DIRS=(
  "$SUPPORT/Google/Chrome"
  "$SUPPORT/Google/Chrome Beta"
  "$SUPPORT/Chromium"
  "$SUPPORT/BraveSoftware/Brave-Browser"
  "$SUPPORT/Microsoft Edge"
)

if [ "$(uname -s)" != "Darwin" ]; then
  echo "This installer supports macOS only." >&2
  exit 1
fi

if [ "${1:-}" = "--uninstall" ]; then
  for dir in "${BROWSER_DIRS[@]}"; do
    rm -f "$dir/NativeMessagingHosts/$HOST_NAME.json"
  done
  rm -rf "$INSTALL_DIR"
  echo "Removed. Also remove the extension at chrome://extensions."
  exit 0
fi

PYTHON="$(command -v python3 || true)"
if [ -z "$PYTHON" ]; then
  echo "python3 not found. Install it with: xcode-select --install" >&2
  exit 1
fi

mkdir -p "$INSTALL_DIR"
chmod 700 "$INSTALL_DIR"
cp "$HERE/host/send_to_terminal_host.py" "$HERE/host/runner.sh" "$INSTALL_DIR/"

# Chrome starts the host with a minimal PATH, so the launcher names the
# Python interpreter by absolute path.
LAUNCHER="$INSTALL_DIR/host-launcher.sh"
printf '#!/bin/bash\nexec %q %q\n' "$PYTHON" "$INSTALL_DIR/send_to_terminal_host.py" > "$LAUNCHER"
chmod 700 "$LAUNCHER" "$INSTALL_DIR/runner.sh" "$INSTALL_DIR/send_to_terminal_host.py"

installed=0
for dir in "${BROWSER_DIRS[@]}"; do
  [ -d "$dir" ] || continue
  mkdir -p "$dir/NativeMessagingHosts"
  "$PYTHON" - "$dir/NativeMessagingHosts/$HOST_NAME.json" "$HOST_NAME" "$LAUNCHER" "$EXTENSION_ID" <<'PY'
import json, sys
path, name, launcher, ext_id = sys.argv[1:5]
with open(path, "w") as out:
    json.dump(
        {
            "name": name,
            "description": "Send to Terminal native host",
            "path": launcher,
            "type": "stdio",
            "allowed_origins": [f"chrome-extension://{ext_id}/"],
        },
        out,
        indent=2,
    )
PY
  echo "Registered host for: $dir"
  installed=$((installed + 1))
done

if [ "$installed" -eq 0 ]; then
  echo "No Chromium-based browser profile found. Start Chrome once, then run this again." >&2
  exit 1
fi

cat <<EOF

Native host installed in: $INSTALL_DIR

Next:
  1. Open chrome://extensions and turn on Developer mode.
  2. Click "Load unpacked" and select: $HERE/extension
  3. Confirm the extension ID is: $EXTENSION_ID
  4. Right-click a selection and choose "Send to Terminal".
     macOS asks one time to let Chrome control Terminal. Click OK.
EOF
