/**
 * content.js — Content script injected into every page.
 *
 * Responsibilities:
 *  1. Listen for messages from the popup asking for the current text selection.
 *  2. Return the selected text and the current page domain.
 *
 * The popup sets a "selection mode" flag and then the user selects text on
 * the page. When the popup polls for the selection, this script reads
 * window.getSelection() and returns the result.
 */

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {

  if (message.type === "GET_SELECTION") {
    const selected = window.getSelection()?.toString().trim() ?? "";
    sendResponse({ text: selected });
    return true;
  }

  if (message.type === "GET_DOMAIN") {
    // Remove leading www. before returning
    const domain = window.location.hostname.replace(/^www\./, "");
    sendResponse({ domain });
    return true;
  }

});
