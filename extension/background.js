/**
 * background.js — Service worker (Manifest V3).
 *
 * Handles tasks that need to run outside the popup lifecycle:
 *  - Opening new tabs (Search on the web, source website)
 *  - Keeping the extension alive during long API calls if needed
 */

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {

  if (message.type === "OPEN_TAB") {
    chrome.tabs.create({ url: message.url });
    sendResponse({ ok: true });
    return true;
  }

});
