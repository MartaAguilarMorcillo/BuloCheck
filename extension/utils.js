/**
 * utils.js — Shared utility functions.
 */

/**
 * Get or create a persistent device UUID stored in chrome.storage.local.
 * Generated once on first use, reused forever.
 * @returns {Promise<string>} UUID v4
 */
export async function getOrCreateDeviceId() {
  const result = await chrome.storage.local.get("device_id");
  if (result.device_id) return result.device_id;

  // crypto.randomUUID() is available natively in Chrome extensions
  const deviceId = crypto.randomUUID();
  await chrome.storage.local.set({ device_id: deviceId });
  return deviceId;
}

/**
 * Get the domain of the currently active tab.
 * Strips leading www. prefix.
 * @returns {Promise<string|null>}
 */
export async function getActiveDomain() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) return null;

    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => window.location.hostname.replace(/^www\./, ""),
    });
    return result || null;
  } catch {
    return null;
  }
}

/**
 * Get the current text selection from the active tab.
 * @returns {Promise<string>}
 */
export async function getSelection() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) return "";

    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => window.getSelection()?.toString().trim() ?? "",
    });
    return result || "";
  } catch {
    return "";
  }
}

/**
 * Build a Google search URL for a given title.
 * @param {string} title
 * @returns {string}
 */
export function googleSearchUrl(title) {
  return `https://www.google.com/search?q=${encodeURIComponent(title)}`;
}

/**
 * Format a source for display.
 * Returns { displayName, logoUrl } where displayName is name or domain.
 * @param {object|null} newsSource
 * @returns {{ displayName: string, logoUrl: string|null }}
 */
export function formatSource(newsSource) {
  if (!newsSource) return { displayName: "Indeterminate source", logoUrl: null };
  return {
    displayName: newsSource.name ?? newsSource.domain,
    logoUrl: newsSource.logo_url ?? null,
  };
}

/**
 * Draw a donut chart on a canvas element.
 * @param {HTMLCanvasElement} canvas
 * @param {number} realPct   - 0 to 1
 * @param {number} fakePct   - 0 to 1
 */
export function drawDonut(canvas, realPct, fakePct) {
  const ctx = canvas.getContext("2d");
  const cx = canvas.width / 2;
  const cy = canvas.height / 2;
  const r = cx - 14;
  const lineWidth = 22;
  const start = -Math.PI / 2;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Real arc (green)
  ctx.beginPath();
  ctx.arc(cx, cy, r, start, start + Math.PI * 2 * realPct);
  ctx.strokeStyle = "#22c55e";
  ctx.lineWidth = lineWidth;
  ctx.lineCap = "butt";
  ctx.stroke();

  // Fake arc (red)
  ctx.beginPath();
  ctx.arc(cx, cy, r, start + Math.PI * 2 * realPct, start + Math.PI * 2);
  ctx.strokeStyle = "#ef4444";
  ctx.lineWidth = lineWidth;
  ctx.lineCap = "butt";
  ctx.stroke();
}
