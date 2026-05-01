console.log("BuloCheck: content script loaded");

// Future: extract article data
function getPageData() {
  const title = document.title;

  const paragraphs = Array.from(document.querySelectorAll("p"))
    .map((p) => p.innerText)
    .join(" ")
    .trim();

  return {
    title,
    text: paragraphs,
  };
}

// expose globally (for later integration)
window.BuloCheck = {
  getPageData,
};
