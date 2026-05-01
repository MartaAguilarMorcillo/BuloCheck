const button = document.getElementById("analyze");
const status = document.getElementById("status");

button.addEventListener("click", async () => {
  console.log("Button clicked");

  try {
    const [tab] = await chrome.tabs.query({
      active: true,
      currentWindow: true,
    });

    // Validaciones
    if (!tab.url || tab.url.startsWith("chrome://")) {
      status.textContent = "Open a news article 🌐";
      return;
    }

    if (!tab.url.startsWith("http")) {
      status.textContent = "Invalid page ❌";
      return;
    }

    // Si pasa validaciones, seguimos
    status.textContent = "Extracting page data...";

    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => window.BuloCheck?.getPageData?.(),
    });

    const data = results?.[0]?.result;

    console.log("Extracted data:", data);

    status.textContent = "Done ✔ (check console)";
  } catch (err) {
    console.error(err);
    status.textContent = "Error ❌";
  }
});
