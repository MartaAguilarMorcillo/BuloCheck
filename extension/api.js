/**
 * api.js — All calls to the Django backend.
 *
 * BASE_URL points to the local development server.
 * Change to the production URL when deploying.
 */

const BASE_URL = "http://127.0.0.1:8000/api";

/**
 * Predict whether a news article is REAL or FAKE.
 * @param {string} title
 * @param {string} text
 * @param {string|null} domain  - e.g. "bbc.com"
 * @param {string} deviceId     - UUID from chrome.storage.local
 */
export async function predict(title, text, domain, deviceId) {
  const body = { title, text, device_id: deviceId };
  if (domain) body.domain = domain;

  const res = await fetch(`${BASE_URL}/predict/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await res.json();

  if (!res.ok) {
    const msg =
      data.validation_errors?.join(" ") ||
      data.error ||
      `Server error (${res.status})`;
    throw new Error(msg);
  }

  return data;
}

/**
 * Fetch paginated history for a user.
 * @param {string} deviceId
 * @param {number} page
 * @param {number} pageSize
 */
export async function getHistory(deviceId, page = 1, pageSize = 3) {
  const res = await fetch(
    `${BASE_URL}/history/?page=${page}&page_size=${pageSize}`,
    { headers: { "X-Device-ID": deviceId } }
  );
  if (!res.ok) throw new Error(`History error (${res.status})`);
  return res.json();
}

/**
 * Find news articles with similar titles.
 * @param {string} title
 * @param {number} minSim  - similarity threshold (default 0.25)
 */
export async function getSimilar(title, minSim = 0.25) {
  const params = new URLSearchParams({ title, min_sim: minSim });
  const res = await fetch(`${BASE_URL}/similar/?${params}`);
  if (!res.ok) throw new Error(`Similar error (${res.status})`);
  return res.json();
}

/**
 * Fetch top-5 most reliable sources for a user.
 * @param {string} deviceId
 */
export async function getSources(deviceId) {
  const res = await fetch(`${BASE_URL}/sources/`, {
    headers: { "X-Device-ID": deviceId },
  });
  if (!res.ok) throw new Error(`Sources error (${res.status})`);
  return res.json();
}

/**
 * Look up a news source by domain.
 * Returns the source object or null if not found.
 * @param {string} domain
 */
export async function lookupSource(domain) {
  const res = await fetch(
    `${BASE_URL}/sources/lookup/?domain=${encodeURIComponent(domain)}`
  );
  if (res.status === 404) return null;
  if (!res.ok) return null;
  return res.json();
}
