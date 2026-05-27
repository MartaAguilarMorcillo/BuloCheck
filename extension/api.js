/**
 * api.js — All calls to the Django backend.
 * No ES module exports — all functions are global for Chrome extension compatibility.
 */

const BASE_URL = "http://127.0.0.1:8000/api";

// ── Token storage ────────────────────────────────────────────────────────────

async function getTokens() {
  return await chrome.storage.local.get(["access_token", "refresh_token"]);
}

async function saveTokens(access, refresh) {
  await chrome.storage.local.set({
    access_token: access,
    refresh_token: refresh,
  });
}

async function clearTokens() {
  await chrome.storage.local.remove(["access_token", "refresh_token"]);
}

async function getAuthHeader() {
  var tokens = await getTokens();
  if (!tokens.access_token) throw new Error("Not authenticated.");
  return { "Authorization": "Bearer " + tokens.access_token };
}

// ── Auth ─────────────────────────────────────────────────────────────────────

async function apiLogin(email, password) {
  var res = await fetch(BASE_URL + "/auth/login/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email, password: password }),
  });
  var data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Invalid email or password.");
  return data;
}

async function apiRegister(email, password) {
  var res = await fetch(BASE_URL + "/auth/register/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email, password: password }),
  });
  var data = await res.json();
  if (!res.ok) {
    var msg = (data.email && data.email[0]) ||
              (data.password && data.password[0]) ||
              "Registration failed.";
    throw new Error(msg);
  }
  return data;
}

async function apiRefresh(refreshToken) {
  var res = await fetch(BASE_URL + "/auth/refresh/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: refreshToken }),
  });
  var data = await res.json();
  if (!res.ok) throw new Error("Session expired. Please log in again.");
  return data.access;
}

// ── App endpoints ─────────────────────────────────────────────────────────────

async function apiPredict(title, text, domain) {
  var headers = await getAuthHeader();
  headers["Content-Type"] = "application/json";

  var body = { title: title, text: text };
  if (domain) body.domain = domain;

  var res = await fetch(BASE_URL + "/predict/", {
    method: "POST",
    headers: headers,
    body: JSON.stringify(body),
  });

  if (res.status === 401) {
    try {
      var tokens = await getTokens();
      var newAccess = await apiRefresh(tokens.refresh_token);
      await saveTokens(newAccess, tokens.refresh_token);
      return apiPredict(title, text, domain);
    } catch (e) {
      await clearTokens();
      showLogin();
      throw new Error("Session expired. Please log in again.");
    }
  }

  var data = await res.json();
  if (!res.ok) {
    var msg = (data.validation_errors && data.validation_errors.join(" ")) ||
              data.error ||
              ("Server error (" + res.status + ")");
    throw new Error(msg);
  }
  return data;
}

async function apiGetHistory(page, pageSize) {
  var headers = await getAuthHeader();
  var res = await fetch(
    BASE_URL + "/history/?page=" + page + "&page_size=" + pageSize,
    { headers: headers }
  );
  if (res.status === 401) { await clearTokens(); showLogin(); return null; }
  if (!res.ok) throw new Error("History error (" + res.status + ")");
  return res.json();
}

async function apiGetSimilar(title, minSim) {
  var headers = await getAuthHeader();
  var params = new URLSearchParams({ title: title, min_sim: minSim });
  var res = await fetch(BASE_URL + "/similar/?" + params.toString(),
    { headers: headers });
  if (res.status === 401) { await clearTokens(); showLogin(); return null; }
  if (!res.ok) throw new Error("Similar error (" + res.status + ")");
  return res.json();
}

async function apiGetSources() {
  var headers = await getAuthHeader();
  var res = await fetch(BASE_URL + "/sources/", { headers: headers });
  if (res.status === 401) { await clearTokens(); showLogin(); return null; }
  if (!res.ok) throw new Error("Sources error (" + res.status + ")");
  return res.json();
}

async function apiLookupSource(domain) {
  var headers = await getAuthHeader();
  var res = await fetch(
    BASE_URL + "/sources/lookup/?domain=" + encodeURIComponent(domain),
    { headers: headers }
  );
  if (res.status === 404) return null;
  if (!res.ok) return null;
  return res.json();
}