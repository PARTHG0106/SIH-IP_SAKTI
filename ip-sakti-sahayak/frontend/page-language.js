"use strict";

// Translate interface text in place so changing the page language never resets
// forms, open details, API requests, or the current conversation. Evidence and
// user content are explicitly excluded; answer translation is a separate feature.
(() => {
  const hindi = {
    ...window.IP_SAKTI_HINDI,
    ...window.IP_SAKTI_HINDI_DYNAMIC,
    "The page language button translates the interface. Use Answer language for responses; source notes stay in their original language.":
      "पृष्ठ का भाषा बटन इंटरफ़ेस का अनुवाद करता है। उत्तरों के लिए ‘उत्तर की भाषा’ चुनें; स्रोत के नोट अपनी मूल भाषा में रहते हैं।"
  };
  const originals = new WeakMap();
  const attributes = new WeakMap();
  const elementLanguages = new Map();
  const excluded = 'script,style,textarea,svg,code,[translate="no"],.answer-text,.summary-text';
  const attributeNames = ["aria-label", "title", "placeholder"];
  let language = "en";
  let observer;

  function translate(text) {
    if (Object.hasOwn(hindi, text)) return hindi[text];
    const patterns = [
      [/^Step (\d+)$/, (_, n) => `चरण ${n}`],
      [/^(\d+) confirmed steps? · review or change$/, (_, n) => `${n} पुष्ट चरण · समीक्षा करें या बदलें`],
      [/^(.*) \(from your description; confirm or change\)$/, (_, label) => `${translate(label)} (आपके विवरण से; पुष्टि करें या बदलें)`],
      [/^(India|International|India \+ international) · (.+)$/, (_, scope, category) => `${translate(scope)} · ${translate(category)}`],
      [/^(\d+) cited sources?$/, (_, n) => `${n} उद्धृत स्रोत`],
      [/^Records: (.+)$/, (_, dates) => `अभिलेख: ${dates}`],
      [/^Source record: (.+)$/, (_, date) => `स्रोत अभिलेख: ${date}`],
      [/^Primary text checked: (.+)$/, (_, date) => `मूल पाठ की जाँच: ${date}`],
      [/^Sources you can inspect · (\d+)$/, (_, n) => `जाँचने योग्य स्रोत · ${n}`],
      [/^Question (\d+)$/, (_, n) => `प्रश्न ${n}`],
      [/^Read source (\d+)$/, (_, n) => `स्रोत ${n} पढ़ें`],
      [/^Preparing a sourced answer in the (.+) scope…$/, (_, scope) => `${translate(scope)} के दायरे में स्रोत आधारित उत्तर तैयार हो रहा है…`],
      [/^Corpus (.+)$/, (_, version) => `स्रोत संग्रह ${version}`],
      [/^(\d+) of (\d+) sources · (\d+) notes withheld from answers pending primary review$/, (_, count, total, withheld) => `${total} में से ${count} स्रोत · मूल स्रोत की समीक्षा तक ${withheld} नोट उत्तरों से बाहर रखे गए हैं`],
      [/^(.+) — unavailable$/, (_, name) => `${translate(name)} — उपलब्ध नहीं`],
      [/^(.+)\. Record your consent before continuing to its official referral page\.$/, (_, name) => `${name}। इसके आधिकारिक रेफ़रल पृष्ठ पर जाने से पहले अपनी सहमति दर्ज करें।`],
      [/^(.+) Please try again\.$/, (_, error) => `${translate(error)} कृपया दोबारा प्रयास करें।`],
      [/^(.+) No resource has been opened\.$/, (_, error) => `${translate(error)} कोई संसाधन नहीं खोला गया है।`]
    ];
    for (const [pattern, replacement] of patterns) {
      if (pattern.test(text)) return text.replace(pattern, replacement);
    }
    return text;
  }

  function translatedValue(value) {
    // Keep whitespace around inline links, emphasis and icons exactly as authored.
    return value.replace(/^(\s*)([\s\S]*?)(\s*)$/, (_, before, text, after) =>
      before + (language === "hi" ? translate(text) : text) + after);
  }

  function markLanguage(element) {
    if (!elementLanguages.has(element)) elementLanguages.set(element, element.getAttribute("lang"));
    element.setAttribute("lang", "hi");
  }

  function applyTranslations() {
    observer?.disconnect();
    // Restore only language annotations owned by this controller. The original
    // answer-language annotations and user content remain intact.
    for (const [element, original] of elementLanguages) {
      if (original === null) element.removeAttribute("lang");
      else element.setAttribute("lang", original);
    }
    elementLanguages.clear();
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (node.parentElement.closest(excluded) && !node.parentElement.matches(".table-help")) continue;
      const saved = originals.get(node);
      const original = saved && node.data === saved.rendered ? saved.original : node.data;
      const rendered = translatedValue(original);
      originals.set(node, {original, rendered});
      if (node.data !== rendered) node.data = rendered;
      if (language === "hi" && rendered !== original) markLanguage(node.parentElement);
    }
    for (const element of document.querySelectorAll('[aria-label],[title],[placeholder]')) {
      // Citation/table accessibility labels are UI even inside an answer.
      if (element.closest('script,style,[translate="no"]')) continue;
      const saved = attributes.get(element) || {};
      for (const name of attributeNames) {
        const current = element.getAttribute(name);
        if (current === null) continue;
        const original = saved[name] && current === saved[name].rendered ? saved[name].original : current;
        const rendered = translatedValue(original);
        saved[name] = {original, rendered};
        if (current !== rendered) element.setAttribute(name, rendered);
      }
      attributes.set(element, saved);
    }
    const title = document.querySelector("title");
    const savedTitle = originals.get(title);
    const originalTitle = savedTitle?.original || title.textContent;
    const renderedTitle = language === "hi" ? translate(originalTitle) : originalTitle;
    originals.set(title, {original: originalTitle, rendered: renderedTitle});
    if (title.textContent !== renderedTitle) title.textContent = renderedTitle;
    document.documentElement.lang = language;
    const button = document.querySelector("#pageLanguageToggle");
    const label = language === "hi" ? "Read page interface in English" : "Translate page interface to Hindi";
    const buttonText = document.createElement("span");
    buttonText.textContent = language === "hi" ? "English" : "हिन्दी";
    buttonText.lang = language === "hi" ? "en" : "hi";
    button.replaceChildren(buttonText);
    button.setAttribute("aria-label", label);
    button.title = label;
    button.setAttribute("aria-pressed", String(language === "hi"));
    observer.observe(document.documentElement, {
      subtree: true, childList: true, characterData: true,
      attributes: true, attributeFilter: attributeNames
    });
  }

  function start() {
    try {
      language = localStorage.getItem("ip-sakti-page-language") === "hi" ? "hi" : "en";
    } catch { /* The button also works when browser storage is blocked. */ }
    observer = new MutationObserver(applyTranslations);
    document.querySelector("#pageLanguageToggle").addEventListener("click", () => {
      language = language === "hi" ? "en" : "hi";
      try { localStorage.setItem("ip-sakti-page-language", language); }
      catch { /* Persisting this preference is optional. */ }
      applyTranslations();
    });
    applyTranslations();
  }
  // app.js captures its English empty state before any persisted Hindi setting
  // is applied. API-driven DOM updates are picked up by the observer afterward.
  document.addEventListener("DOMContentLoaded", start, {once: true});
})();
