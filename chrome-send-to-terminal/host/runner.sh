#!/bin/bash
# Runs inside the Terminal window that send_to_terminal_host.py opens.
# Shows the text sent from Chrome and asks before anything runs as root.
#
# Usage: runner.sh <payload-file> <kind> [source-url]

set -u

payload="${1:-}"
kind="${2:-selection}"
source_url="${3:-}"

if [ -z "$payload" ] || [ ! -f "$payload" ] || [ ! -O "$payload" ]; then
  echo "send-to-terminal: payload file is missing or not owned by you." >&2
  exit 1
fi
trap 'rm -f "$payload"' EXIT

echo "Send to Terminal: $kind from ${source_url:-unknown page}"
echo "------------------------------------------------------------"
# cat -v prints control characters as visible text (^[ for ESC), so a web
# page cannot hide part of a command with terminal escape sequences.
cat -v "$payload"
echo "------------------------------------------------------------"

if LC_ALL=C grep -q '[^[:print:][:space:]]' "$payload"; then
  echo "WARNING: the text contains control or non-ASCII characters."
  echo "Read every line above before you run it."
fi

echo "  r  run the text above as root (sudo asks for your password)"
echo "  s  open a root shell, text is in \$SENT and on the clipboard"
echo "  q  quit, run nothing (default)"
printf "Choice [r/s/q]: "
read -r choice

case "$choice" in
  r|R)
    sudo /bin/bash "$payload"
    echo "Exit status: $?"
    ;;
  s|S)
    sent="$(cat "$payload")"
    printf '%s' "$sent" | pbcopy
    sudo /usr/bin/env SENT="$sent" /bin/bash
    ;;
  *)
    echo "Nothing was run."
    ;;
esac
