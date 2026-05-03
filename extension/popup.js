const titleBox = document.getElementById("titleBox");
const bodyBox = document.getElementById("bodyBox");
const status = document.getElementById("status");
const button = document.getElementById("analyze");

async function loadSelections() {
  const data = await chrome.storage.local.get([
    "selectedTitle",
    "selectedBody",
  ]);

  titleBox.textContent = data.selectedTitle || "No title selected";

  bodyBox.textContent = data.selectedBody || "No body selected";
}

button.addEventListener("click", async () => {
  // VALIDAR PÁGINA ACTUAL
  const [tab] = await chrome.tabs.query({
    active: true,
    currentWindow: true,
  });

  if (!tab.url || tab.url.startsWith("chrome://")) {
    status.textContent = "Open a valid webpage 🌐";
    return;
  }

  if (!tab.url.startsWith("http")) {
    status.textContent = "Invalid page ❌";
    return;
  }

  // CARGAR DATOS
  const data = await chrome.storage.local.get([
    "selectedTitle",
    "selectedBody",
  ]);

  const selectedTitle = data.selectedTitle || "";
  const selectedBody = data.selectedBody || "";

  // VALIDACIONES
  if (!selectedTitle.trim()) {
    status.textContent = "Select a title";
    return;
  }

  if (!selectedBody.trim()) {
    status.textContent = "Select article body";
    return;
  }

  if (selectedBody.length < 20) {
    status.textContent = "Article too short";
    return;
  }

  if (selectedBody.length > 5000) {
    status.textContent = "Article too long";
    return;
  }

  console.log("TITLE:", selectedTitle);
  console.log("BODY:", selectedBody);

  status.textContent = "Data ready for backend ✔";
});

const clearButton = document.getElementById("clear");

clearButton.addEventListener("click", async () => {
  await chrome.storage.local.remove(["selectedTitle", "selectedBody"]);

  titleBox.textContent = "No title selected";
  bodyBox.textContent = "No body selected";

  status.textContent = "Selection cleared ✔";
});

loadSelections();
