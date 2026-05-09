const titleBox = document.getElementById("titleBox");
const bodyBox = document.getElementById("bodyBox");
const status = document.getElementById("status");
const button = document.getElementById("analyze");
const resultBox = document.getElementById("resultBox");
const clearButton = document.getElementById("clear");
const confidenceBar = document.getElementById("confidenceBar");
const confWrapper = document.getElementById("confWrapper");

async function loadSelections() {
  const data = await chrome.storage.local.get([
    "selectedTitle",
    "selectedBody",
  ]);

  titleBox.textContent = data.selectedTitle || "No title selected";

  bodyBox.textContent = data.selectedBody || "No body selected";

  confWrapper.style.display = "none";

  confidenceBar.style.width = "0%";

  resultBox.classList.remove("is-fake", "is-real");
}

button.addEventListener("click", async () => {

  // VALIDAR PÁGINA
  const [tab] = await chrome.tabs.query({
    active: true,
    currentWindow: true
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
    "selectedBody"
  ]);

  const selectedTitle = data.selectedTitle || "";
  const selectedBody = data.selectedBody || "";

  // VALIDACIONES
  if (!selectedTitle.trim()) {
    status.textContent = "Select a title";
    return;
  }

  if (selectedTitle.length < 3) {
    status.textContent = "Title too short";
    return;
  }

  if (selectedTitle.length > 300) {
    status.textContent = "Title too long";
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

  // ENVIAR A FASTAPI
  try {

    status.textContent = "Analyzing article...";
    resultBox.textContent = "Analyzing...";
    confWrapper.style.display = "none";

    const response = await fetch(
      "http://127.0.0.1:8000/predict",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          title: selectedTitle,
          text: selectedBody
        })
      }
    );

    const result = await response.json();

    console.log(result);

    // MANEJO DE ERRORES BACKEND
    if (!response.ok) {

      status.textContent =
        typeof result.detail === "string"
          ? result.detail
          : result.detail?.[0]?.msg || "Backend error ❌";

      resultBox.textContent =
        "No prediction available";
      
      confWrapper.style.display = "none";
      confidenceBar.style.width = "0%";
      resultBox.classList.remove("is-fake", "is-real");

      return;
    }

    // MOSTRAR RESULTADO
    const confidence = result.confidence * 100;
    const confidenceFixed = confidence.toFixed(2);

    resultBox.textContent =
      `${result.label} (${confidenceFixed}%)`;

    confWrapper.style.display = "block";

    confidenceBar.style.width = `${confidence}%`;

    resultBox.classList.remove(
      "is-fake",
      "is-real"
    );

    if (result.label === "FAKE") {

      resultBox.classList.add("is-fake");

      confidenceBar.style.background =
        "#ef4444";

    } else {

      resultBox.classList.add("is-real");

      confidenceBar.style.background =
        "#22c55e";
    }

    status.textContent =
      "Analysis completed ✔";

  } catch (error) {

    console.error(error);

    status.textContent =
      "Backend connection failed ❌";
  }
});

clearButton.addEventListener("click", async () => {

  await chrome.storage.local.remove([
    "selectedTitle",
    "selectedBody"
  ]);

  titleBox.textContent = "No title selected";
  bodyBox.textContent = "No body selected";
  resultBox.textContent = "No prediction yet";

  resultBox.classList.remove(
    "is-fake",
    "is-real"
  );

  confWrapper.style.display = "none";

  confidenceBar.style.width = "0%";

  status.textContent = "Selection cleared ✔";
});

loadSelections();
