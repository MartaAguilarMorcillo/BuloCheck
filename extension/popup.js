/**
 * popup.js — BuloCheck extension main script.
 * Self-contained: no imports needed (utils and api inlined).
 */

// ── Config ─────────────────────────────────────────────────────────────────
const BASE_URL = "http://127.0.0.1:8000/api";
const PAGE_SIZE = 3;

// ── State ──────────────────────────────────────────────────────────────────
const state = {
  deviceId: null,
  domain: null,
  title: "",
  body: "",
  lastResult: null,
  isReadMode: false,
  historyPage: 1,
  historyTotalPages: 1,
};

// ── DOM refs ────────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

const tabBtns    = document.querySelectorAll(".tab-btn");
const tabPanels  = document.querySelectorAll(".tab-panel");

// Tab 1
const analyzeMode   = $("analyze-mode");
const resultMode    = $("result-mode");
const boxTitle      = $("box-title");
const boxBody       = $("box-body");
const btnSelTitle   = $("btn-select-title");
const btnRemTitle   = $("btn-remove-title");
const btnSelBody    = $("btn-select-body");
const btnRemBody    = $("btn-remove-body");
const sourceDisplay = $("source-display");
const btnAnalyze    = $("btn-analyze");
const loadingEl     = $("loading");
const errorBox      = $("error-box");
const errorMsg      = $("error-message");
const verdictEl     = $("verdict");
const donutCanvas   = $("donut-chart");
const chartPct      = $("chart-pct");
const sourceResult  = $("source-result-content");
const btnSearchWeb  = $("btn-search-web");
const btnFindSim    = $("btn-find-similar");
const btnNewAnal    = $("btn-new-analysis");

// Tab 2
const historyList  = $("history-list");
const histPrev     = $("history-prev");
const histNext     = $("history-next");
const histPageInfo = $("history-page-info");
const histPag      = $("history-pagination");
const histEmpty    = $("history-empty");

// Tab 3
const similarList  = $("similar-list");
const similarEmpty = $("similar-empty");
const similarNone  = $("similar-no-title");
const simQueryTitle = $("similar-query-title");

// Tab 4
const podiumEl     = $("podium");
const sourcesEmpty = $("sources-empty");

// ══════════════════════════════════════════════════════════════════════════════
// UTILS
// ══════════════════════════════════════════════════════════════════════════════

async function getOrCreateDeviceId() {
  const result = await chrome.storage.local.get("device_id");
  if (result.device_id) return result.device_id;
  const deviceId = crypto.randomUUID();
  await chrome.storage.local.set({ device_id: deviceId });
  return deviceId;
}

async function getActiveDomain() {
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    const tab = tabs[0];
    if (!tab || !tab.id) return null;
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => window.location.hostname.replace(/^www\./, ""),
    });
    return results[0].result || null;
  } catch (e) {
    return null;
  }
}

async function getSelection() {
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    const tab = tabs[0];
    if (!tab || !tab.id) return "";
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => window.getSelection() ? window.getSelection().toString().trim() : "",
    });
    return results[0].result || "";
  } catch (e) {
    return "";
  }
}

function googleSearchUrl(title) {
  return "https://www.google.com/search?q=" + encodeURIComponent(title);
}

function formatSource(newsSource) {
  if (!newsSource) return { displayName: "Indeterminate source", logoUrl: null };
  return {
    displayName: newsSource.name || newsSource.domain,
    logoUrl: newsSource.logo_url || null,
  };
}

function drawDonut(canvas, realPct, fakePct) {
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

// ══════════════════════════════════════════════════════════════════════════════
// API
// ══════════════════════════════════════════════════════════════════════════════

async function apiPredict(title, text, domain, deviceId) {
  const body = { title: title, text: text, device_id: deviceId };
  if (domain) body.domain = domain;

  const res = await fetch(BASE_URL + "/predict/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await res.json();

  if (!res.ok) {
    const msg =
      (data.validation_errors && data.validation_errors.join(" ")) ||
      data.error ||
      ("Server error (" + res.status + ")");
    throw new Error(msg);
  }

  return data;
}

async function apiGetHistory(deviceId, page, pageSize) {
  const res = await fetch(
    BASE_URL + "/history/?page=" + page + "&page_size=" + pageSize,
    { headers: { "X-Device-ID": deviceId } }
  );
  if (!res.ok) throw new Error("History error (" + res.status + ")");
  return res.json();
}

async function apiGetSimilar(title, minSim) {
  const params = new URLSearchParams({ title: title, min_sim: minSim });
  const res = await fetch(BASE_URL + "/similar/?" + params.toString());
  if (!res.ok) throw new Error("Similar error (" + res.status + ")");
  return res.json();
}

async function apiGetSources(deviceId) {
  const res = await fetch(BASE_URL + "/sources/", {
    headers: { "X-Device-ID": deviceId },
  });
  if (!res.ok) throw new Error("Sources error (" + res.status + ")");
  return res.json();
}

// ══════════════════════════════════════════════════════════════════════════════
// TAB NAVIGATION
// ══════════════════════════════════════════════════════════════════════════════

function switchTab(tabName) {
  tabBtns.forEach(function(b) {
    b.classList.toggle("tab-btn--active", b.dataset.tab === tabName);
  });
  tabPanels.forEach(function(p) {
    p.classList.toggle("tab-panel--active", p.id === "tab-" + tabName);
  });

  if (tabName === "history") loadHistory();
  if (tabName === "sources") loadSources();
}

tabBtns.forEach(function(btn) {
  btn.addEventListener("click", function() {
    switchTab(btn.dataset.tab);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// TAB 1 — ANALYZE
// ══════════════════════════════════════════════════════════════════════════════

function setBox(el, text) {
  el.textContent = text;
  el.classList.add("field-box--filled");
}

function resetBox(el, placeholder) {
  el.innerHTML = '<span class="field-box__placeholder">' + placeholder + '</span>';
  el.classList.remove("field-box--filled");
}

function updateAnalyzeBtn() {
  btnAnalyze.disabled = !(state.title && state.body);
}

function renderSourcePending() {
  sourceDisplay.textContent = state.domain
    ? "Detected: " + state.domain
    : "Pending detection\u2026";
}

async function selectText(field) {
  const text = await getSelection();
  if (!text) return;
  if (field === "title") {
    state.title = text;
    setBox(boxTitle, text);
    btnRemTitle.classList.remove("hidden");
  } else {
    state.body = text;
    setBox(boxBody, text);
    btnRemBody.classList.remove("hidden");
  }
  await saveFields();  // ← guardar tras seleccionar
  updateAnalyzeBtn();
}

function clearField(field) {
  if (field === "title") {
    state.title = "";
    resetBox(boxTitle, "No title selected yet");
    btnRemTitle.classList.add("hidden");
    chrome.storage.local.remove("saved_title");
  } else {
    state.body = "";
    resetBox(boxBody, "No body selected yet");
    btnRemBody.classList.add("hidden");
    chrome.storage.local.remove("saved_body");
  }
  updateAnalyzeBtn();
}

function setLoading(on) {
  loadingEl.classList.toggle("hidden", !on);
  btnAnalyze.disabled = on;
}

function showError(msg) {
  errorBox.classList.remove("hidden");
  errorMsg.textContent = msg;
}

function hideError() {
  errorBox.classList.add("hidden");
}

function showResult(result, title, readMode) {
  state.isReadMode = readMode || false;
  analyzeMode.classList.add("hidden");
  resultMode.classList.remove("hidden");

  // Hide donut chart in read mode when no real confidence is available
  var chartWrapper = document.querySelector(".chart-wrapper");
  if (readMode && !result.probas) {
    chartWrapper.classList.add("hidden");
  } else {
    chartWrapper.classList.remove("hidden");
  }

  var isReal = result.label === "REAL";

  // Verdict badge
  verdictEl.className = "verdict verdict--" + (isReal ? "real" : "fake");
  verdictEl.innerHTML =
    '<div class="verdict__badge">' + (isReal ? "\u2713 REAL" : "\u2717 FAKE") + "</div>";

  // Donut chart
  var realPct = (result.probas && result.probas.REAL != null)
    ? result.probas.REAL
    : (isReal ? result.confidence : 1 - result.confidence);
  var fakePct = (result.probas && result.probas.FAKE != null)
    ? result.probas.FAKE
    : (isReal ? 1 - result.confidence : result.confidence);

  drawDonut(donutCanvas, realPct, fakePct);
  chartPct.textContent = Math.round((isReal ? realPct : fakePct) * 100) + "%";

  // Source
  var src = formatSource(result.news_source);
  if (src.logoUrl) {
    sourceResult.innerHTML =
      '<img class="source-result__logo" src="' + src.logoUrl + '" alt="' + src.displayName + '" ' +
      'onerror="this.remove()">' +
      '<span class="source-result__name">' + src.displayName + "</span>";
  } else {
    sourceResult.innerHTML =
      '<span class="source-result__name">' + src.displayName + "</span>";
  }

  // Warnings
  var existingWarning = resultMode.querySelector(".warning-box");
  if (existingWarning) existingWarning.remove();
  if (result.warnings && result.warnings.length) {
    var warningEl = document.createElement("div");
    warningEl.className = "warning-box";
    warningEl.textContent = "\u26a0\ufe0f " + result.warnings[0];
    resultMode.appendChild(warningEl);
  }

  state.title = title;
  btnNewAnal.textContent = readMode ? "\u2190 Back" : "+ New analysis";
}

function resetAnalyzeTab() {
  state.isReadMode = false;
  state.title = "";
  state.body = "";
  state.lastResult = null;
  chrome.storage.local.remove(["saved_title", "saved_body"]);  // ← limpiar

  analyzeMode.classList.remove("hidden");
  resultMode.classList.add("hidden");
  resetBox(boxTitle, "No title selected yet");
  resetBox(boxBody, "No body selected yet");
  btnRemTitle.classList.add("hidden");
  btnRemBody.classList.add("hidden");
  updateAnalyzeBtn();
  hideError();
  renderSourcePending();
}

async function runAnalysis() {
  setLoading(true);
  hideError();
  try {
    var result = await apiPredict(state.title, state.body, state.domain, state.deviceId);
    state.lastResult = result;
    showResult(result, state.title, false);
  } catch (err) {
    var msg = err.message === "Failed to fetch"
      ? "Could not connect to the server. Make sure the app is running and try again."
      : err.message;
    showError(msg);
  } finally {
    setLoading(false);
  }
}

btnSelTitle.addEventListener("click", function() { selectText("title"); });
btnSelBody.addEventListener("click",  function() { selectText("body"); });
btnRemTitle.addEventListener("click", function() { clearField("title"); });
btnRemBody.addEventListener("click",  function() { clearField("body"); });
btnAnalyze.addEventListener("click",  runAnalysis);
btnNewAnal.addEventListener("click",  resetAnalyzeTab);

btnSearchWeb.addEventListener("click", function() {
  if (!state.title) return;
  chrome.tabs.create({ url: googleSearchUrl(state.title) });
});

btnFindSim.addEventListener("click", function() {
  switchTab("similar");
  loadSimilar(state.title);
});

// ══════════════════════════════════════════════════════════════════════════════
// TAB 2 — HISTORY
// ══════════════════════════════════════════════════════════════════════════════

histPrev.addEventListener("click", function() {
  if (state.historyPage > 1) {
    state.historyPage--;
    loadHistory();
  }
});

histNext.addEventListener("click", function() {
  if (state.historyPage < state.historyTotalPages) {
    state.historyPage++;
    loadHistory();
  }
});

async function loadHistory() {
  historyList.innerHTML = "";
  histEmpty.classList.add("hidden");
  histPag.classList.add("hidden");

  try {
    var data = await apiGetHistory(state.deviceId, state.historyPage, PAGE_SIZE);
    state.historyTotalPages = data.total_pages;

    if (!data.results.length) {
      histEmpty.classList.remove("hidden");
      return;
    }

    data.results.forEach(function(check) {
      historyList.appendChild(buildNewsCard(check));
    });

    if (data.total_pages > 1) {
      histPag.classList.remove("hidden");
      histPageInfo.textContent = state.historyPage + " / " + data.total_pages;
      histPrev.disabled = state.historyPage <= 1;
      histNext.disabled = state.historyPage >= data.total_pages;
    }
  } catch (err) {
    historyList.innerHTML =
      '<div class="empty-state">' +
        '<span>⚠️</span>' +
        '<p>Could not connect to the server.<br>Make sure the app is running and try again.</p>' +
      '</div>';
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// TAB 3 — SIMILAR
// ══════════════════════════════════════════════════════════════════════════════

async function loadSimilar(title) {
  similarList.innerHTML = "";
  similarEmpty.classList.add("hidden");
  similarNone.classList.add("hidden");
  simQueryTitle.textContent = "";

  if (!title) {
    similarNone.classList.remove("hidden");
    return;
  }

  simQueryTitle.textContent = '"' + title + '"';

  try {
    var items = await apiGetSimilar(title, 0.25);

    if (!items.length) {
      similarEmpty.classList.remove("hidden");
      return;
    }

    items.forEach(function(item) {
      var pseudo = {
        title: item.title,
        label: item.label,
        news_source: item.source_name
          ? { name: item.source_name, domain: null, logo_url: item.source_logo }
          : null,
      };
      similarList.appendChild(buildNewsCard(pseudo));
    });
  } catch (err) {
    similarList.innerHTML =
      '<div class="empty-state">' +
        '<span>⚠️</span>' +
        '<p>Could not connect to the server.<br>Make sure the app is running and try again.</p>' +
      '</div>';
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// TAB 4 — SOURCES
// ══════════════════════════════════════════════════════════════════════════════

async function loadSources() {
  podiumEl.innerHTML = "";
  sourcesEmpty.classList.add("hidden");

  try {
    var sources = await apiGetSources(state.deviceId);

    if (!sources.length) {
      sourcesEmpty.classList.remove("hidden");
      return;
    }

    var slots = sources.slice();
    while (slots.length < 5) slots.push(null);

    slots.forEach(function(src, i) {
      podiumEl.appendChild(buildPodiumSlot(src, i + 1));
    });
  } catch (err) {
    podiumEl.innerHTML =
      '<div class="empty-state">' +
        '<span>⚠️</span>' +
        '<p>Could not connect to the server.<br>Make sure the app is running and try again.</p>' +
      '</div>';
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// SHARED BUILDERS
// ══════════════════════════════════════════════════════════════════════════════

function buildNewsCard(check) {
  var isReal = check.label === "REAL";
  var src = formatSource(check.news_source);

  var card = document.createElement("article");
  card.className = "news-card";
  card.innerHTML =
    '<div class="news-card__newspaper">' +
      '<div class="news-card__newspaper-lines">' +
        '<div class="news-card__newspaper-line"></div>' +
        '<div class="news-card__newspaper-line"></div>' +
      "</div>" +
    "</div>" +
    '<div class="news-card__body">' +
      '<p class="news-card__title">' + check.title + "</p>" +
      '<div class="news-card__footer">' +
        '<span class="news-card__source">' + src.displayName + "</span>" +
        '<span class="news-card__badge news-card__badge--' + (isReal ? "real" : "fake") + '">' +
          (isReal ? "\u2713 REAL" : "\u2717 FAKE") +
        "</span>" +
      "</div>" +
    "</div>";

  card.addEventListener("click", function() {
    switchTab("analyze");
    showResult(check, check.title, true);
  });

  return card;
}

function buildPodiumSlot(src, position) {
  var slot = document.createElement("div");
  slot.className = "podium-slot" + (src ? "" : " podium-slot--empty");

  if (src) {
    var formatted = formatSource(src.news_source);
    var domain = (src.news_source && src.news_source.domain) ? src.news_source.domain : "";
    var displayName = formatted.displayName;
    var logoUrl = formatted.logoUrl;

    var logoContent = logoUrl
      ? '<img class="podium-slot__logo" src="' + logoUrl + '" alt="' + displayName + '">'
      : '<span class="podium-slot__domain">' + displayName + "</span>";

    slot.innerHTML =
      '<div class="podium-slot__logo-wrap">' +
        logoContent +
        '<span class="podium-slot__tooltip">' + displayName + "</span>" +
      "</div>" +
      '<div class="podium-slot__step">' + position + "</div>";

    if (domain) {
      var logoWrap = slot.querySelector(".podium-slot__logo-wrap");
      logoWrap.style.cursor = "pointer";
      logoWrap.addEventListener("click", function() {
        chrome.tabs.create({ url: "https://" + domain });
      });
    }
  } else {
    slot.innerHTML =
      '<div class="podium-slot__logo-wrap">' +
        '<span class="podium-slot__domain" style="opacity:.4">\u2014</span>' +
      "</div>" +
      '<div class="podium-slot__step">' + position + "</div>";
  }

  return slot;
}

// ══════════════════════════════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════════════════════════════

async function init() {
  state.deviceId = await getOrCreateDeviceId();
  state.domain   = await getActiveDomain();
  await loadSavedFields();  // ← restaurar título y body
  renderSourcePending();
}

init();

// ── Persistencia de título y body ───────────────────────────────────────────

async function saveFields() {
  await chrome.storage.local.set({
    saved_title: state.title,
    saved_body: state.body,
  });
}

async function loadSavedFields() {
  const result = await chrome.storage.local.get(["saved_title", "saved_body"]);
  if (result.saved_title) {
    state.title = result.saved_title;
    setBox(boxTitle, result.saved_title);
    btnRemTitle.classList.remove("hidden");
  }
  if (result.saved_body) {
    state.body = result.saved_body;
    setBox(boxBody, result.saved_body);
    btnRemBody.classList.remove("hidden");
  }
  updateAnalyzeBtn();
}