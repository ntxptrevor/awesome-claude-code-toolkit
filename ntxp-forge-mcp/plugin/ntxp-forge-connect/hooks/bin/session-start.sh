#!/usr/bin/env bash
# Adds one instruction to every new session: start from live NTXP Forge.
# Fails open. A missing file or any error exits 0 with no output, because a
# non-zero exit would block the session.
context="$(dirname "$0")/session-context.txt"
[ -f "$context" ] && cat "$context"
exit 0
