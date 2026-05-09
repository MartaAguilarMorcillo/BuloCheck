chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "setTitle",
    title: "Set as BuloCheck title",
    contexts: ["selection"],
  });

  chrome.contextMenus.create({
    id: "setBody",
    title: "Set as BuloCheck article body",
    contexts: ["selection"],
  });
});

chrome.contextMenus.onClicked.addListener((info) => {
  if (!info.selectionText) return;

  if (info.menuItemId === "setTitle") {
    chrome.storage.local.set({
      selectedTitle: info.selectionText,
    });

    console.log("Title saved:", info.selectionText);
  }

  if (info.menuItemId === "setBody") {
    chrome.storage.local.set({
      selectedBody: info.selectionText,
    });

    console.log("Body saved:", info.selectionText);
  }
});
