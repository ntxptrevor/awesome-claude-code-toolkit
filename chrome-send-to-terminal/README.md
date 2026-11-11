# Send to Terminal (Chrome extension, macOS)

Adds a **Send to Terminal** item to the Chrome right-click menu. The item
sends the highlighted text, or the link, image, or page address under the
pointer, to a new macOS Terminal window. Terminal shows the text and asks
before it runs anything as root.

## How it works

| Part | File | Job |
|------|------|-----|
| Extension | `extension/` | Adds the menu item. Sends the clicked content to the native host. |
| Native host | `host/send_to_terminal_host.py` | Saves the text to a private temp file (mode 0600). Opens Terminal. |
| Runner | `host/runner.sh` | Shows the text in Terminal. Asks `r`, `s`, or `q`. Calls `sudo`. |

A Chrome extension cannot start programs. Chrome native messaging is the
supported bridge, so the installer registers a small host program.

## Install

1. Run the installer. It does not need `sudo`.

   ```bash
   ./install.sh
   ```

2. Open `chrome://extensions` and turn on **Developer mode**.
3. Click **Load unpacked** and select the `extension` folder.
4. Confirm the extension ID is `bhkllnkmkbbchnbggpipembijnofhcjj`. The `key`
   field in `manifest.json` fixes this ID.

The first use shows one macOS prompt: "Google Chrome wants to control
Terminal". Click **OK**.

## Use

1. Highlight a command on a page, or right-click a link, image, or page.
2. Choose **Send to Terminal**.
3. Read the text in the Terminal window, then type one letter:

| Key | Result |
|-----|--------|
| `r` | Runs the text as root with `sudo /bin/bash`. `sudo` asks for your password. |
| `s` | Opens a root shell. The text is in `$SENT` and on the clipboard. |
| `q` or Return | Runs nothing. |

Use `s` for a link or page address, for example `curl -O "$SENT"`.

## Safety design

Web pages are not trusted input. A page can show one command and put a
different one in the selection.

- Nothing runs without a key press in Terminal and the `sudo` password.
- The runner prints the text with `cat -v`. Hidden control characters and
  terminal escape sequences show as visible text.
- The runner prints a warning when the text contains control or non-ASCII
  characters.
- The host accepts messages from this extension ID only.
- The size limit is 64 KB.

WARNING: Do not add a `NOPASSWD` rule to `sudoers` for this tool. With that
rule, one wrong key press runs web content as root.

## Uninstall

```bash
./install.sh --uninstall
```

Then remove the extension at `chrome://extensions`.

## Limits

- macOS only. The host uses `osascript` and Terminal.app.
- Needs `python3` (`xcode-select --install`).
- Run `install.sh` again after you move this folder or change Python.
