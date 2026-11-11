// Adds the "Send to Terminal" context menu item and forwards the clicked
// content to the native host, which opens it in macOS Terminal.

const MENU_ID = "send-to-terminal";
const HOST_NAME = "com.ntxp.send_to_terminal";

// Must match MAX_PAYLOAD_BYTES in host/send_to_terminal_host.py.
const MAX_PAYLOAD_BYTES = 64 * 1024;
// The host shows at most this many characters of the source address. A
// longer address (a large data: page) would push the message over the
// host size limit.
const MAX_SOURCE_CHARS = 2048;

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: MENU_ID,
      title: "Send to Terminal",
      contexts: ["selection", "link", "image", "video", "audio", "page"],
    });
  });
});

// Priority: highlighted text, then the link, then the media source, then
// the page address. The first one present is what the user clicked on.
function pickPayload(info) {
  if (info.selectionText) return { kind: "selection", text: info.selectionText };
  if (info.linkUrl) return { kind: "link", text: info.linkUrl };
  if (info.srcUrl) return { kind: "media", text: info.srcUrl };
  if (info.pageUrl) return { kind: "page", text: info.pageUrl };
  return null;
}

// The address of the document the text came from. Inside an iframe that is
// the frame, which can be a different site from the tab.
function pickSource(info, tab) {
  const source = info.frameUrl || info.pageUrl || tab?.url || "";
  return source.slice(0, MAX_SOURCE_CHARS);
}

function notify(message) {
  chrome.notifications.create({
    type: "basic",
    // 1x1 transparent PNG. Chrome requires an icon for every notification.
    iconUrl:
      "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
    title: "Send to Terminal",
    message,
  });
}

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId !== MENU_ID) return;

  const payload = pickPayload(info);
  if (!payload) {
    notify("Nothing to send. Highlight text or right-click a link.");
    return;
  }
  if (new TextEncoder().encode(payload.text).length > MAX_PAYLOAD_BYTES) {
    notify("Selection is larger than 64 KB. Nothing was sent.");
    return;
  }

  chrome.runtime.sendNativeMessage(
    HOST_NAME,
    { ...payload, source: pickSource(info, tab) },
    (response) => {
      if (chrome.runtime.lastError) {
        notify(
          `Native host not reachable: ${chrome.runtime.lastError.message} ` +
            "Run install.sh, then reload the extension."
        );
        return;
      }
      if (!response?.ok) {
        notify(`Terminal did not open: ${response?.error ?? "unknown error"}`);
      }
    }
  );
});
