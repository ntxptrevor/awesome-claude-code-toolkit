#!/usr/bin/env python3
"""Chrome native messaging host for the "Send to Terminal" extension.

Reads one message from Chrome, saves the text to a private temp file, and
opens a macOS Terminal window that runs runner.sh on that file. The host
never executes the text. runner.sh shows the text and asks before sudo.
"""

import json
import os
import shlex
import struct
import subprocess
import sys
import tempfile

# Must match MAX_PAYLOAD_BYTES in extension/background.js.
MAX_PAYLOAD_BYTES = 64 * 1024
KINDS = {"selection", "link", "media", "page"}
RUNNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runner.sh")

# The command reaches Terminal as an osascript argument, so no AppleScript
# string escaping is needed.
APPLESCRIPT = """
on run argv
    tell application "Terminal"
        activate
        do script (item 1 of argv)
    end tell
end run
"""


def read_message():
    header = sys.stdin.buffer.read(4)
    if len(header) != 4:
        raise ValueError("no message received")
    (length,) = struct.unpack("=I", header)
    # JSON escaping can expand each byte up to 6 times.
    if length > MAX_PAYLOAD_BYTES * 6 + 4096:
        raise ValueError("message too large")
    return json.loads(sys.stdin.buffer.read(length).decode("utf-8"))


def write_message(obj):
    data = json.dumps(obj).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("=I", len(data)))
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def handle(message):
    text = message.get("text")
    kind = message.get("kind")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("empty text")
    if kind not in KINDS:
        raise ValueError("unknown kind")
    data = text.encode("utf-8")
    if len(data) > MAX_PAYLOAD_BYTES:
        raise ValueError("text larger than 64 KB")

    # mkstemp creates the file with mode 0600, so only this user can read
    # or replace the text before runner.sh shows it.
    fd, path = tempfile.mkstemp(prefix="send-to-terminal-", suffix=".txt")
    with os.fdopen(fd, "wb") as handle_:
        handle_.write(data)
        if not data.endswith(b"\n"):
            handle_.write(b"\n")

    source = message.get("source")
    source = source if isinstance(source, str) else ""
    command = " ".join(
        shlex.quote(part) for part in ("/bin/bash", RUNNER, path, kind, source[:2048])
    )
    try:
        subprocess.run(
            ["/usr/bin/osascript", "-e", APPLESCRIPT, command],
            check=True,
            capture_output=True,
            timeout=20,
        )
    except Exception:
        os.unlink(path)
        raise


def main():
    try:
        handle(read_message())
        write_message({"ok": True})
    except subprocess.CalledProcessError as error:
        detail = error.stderr.decode("utf-8", "replace").strip()
        write_message({"ok": False, "error": detail or str(error)})
    except Exception as error:  # Chrome needs a reply for every message.
        write_message({"ok": False, "error": str(error)})


if __name__ == "__main__":
    main()
