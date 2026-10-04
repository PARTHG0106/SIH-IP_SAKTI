"use strict";

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[c]);
const emptyAnswer = $("#answer").innerHTML;
const state = {
  jurisdiction: "India", lang: "en", category: null, categoryLabel: "",
  answers: {}, trail: [], sources: [], lastResponse: null, lastQuestion: "",
  askSequence: 0, classSequence: 0, askController: null, classController: null,
  conversationId: null, turns: [], nextTurnId: 1, memoryExpired: false
};

function safeUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password ? url.href : "";
  } catch { return ""; }
}

async function api(path, body, signal, method = body === undefined ? "GET" : "POST") {
  const response = await fetch(path, {
    method, signal, ...(body === undefined ? {} : {
      headers: {"Content-Type":"application/json"}, body: JSON.stringify(body)
    })
  });
  if (response.status === 204) return {};
  let data;
  try { data = await response.json(); }
  catch { throw new Error("The service returned an unreadable response. Please retry."); }
  if (!response.ok) {
    const message = Array.isArray(data.detail)
      ? data.detail.map(item => item.msg).join(" ")
      : data.detail?.message || data.detail;
    const error = new Error(typeof message === "string" ? message : "The request could not be completed.");
    error.status = response.status;
    error.reason = data.detail?.reason;
    throw error;
  }
  return data;
}

function toast(message) {
  $("#toast").textContent = message;
  $("#toast").hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { $("#toast").hidden = true; }, 3500);
}

function showView(view) {
  const library = view === "sources";
  $("#intro").hidden = library;
  $("#advisorView").hidden = library;
  $("#sourcesView").hidden = !library;
  $("#advisorTab").classList.toggle("active", !library);
  $("#sourcesTab").classList.toggle("active", library);
  $("#advisorTab").toggleAttribute("aria-current", !library);
  $("#sourcesTab").toggleAttribute("aria-current", library);
  (library ? $("#sourcesTab") : $("#advisorTab")).setAttribute("aria-current", "page");
}
$("#advisorTab").addEventListener("click", () => showView("advisor"));
$("#sourcesTab").addEventListener("click", () => showView("sources"));
$("#howItWorks").addEventListener("click", event => {
  event.preventDefault();
  showView("advisor");
  $("#methodGuide").focus({preventScroll: true});
  $("#methodGuide").scrollIntoView({block: "start"});
});
$("#jumpToQuestion").addEventListener("click", event => {
  event.preventDefault();
  $("#q").focus({preventScroll: true});
  $("#askTitle").scrollIntoView({block: "start"});
});

// Only display preferences are persisted; chat content stays page-scoped.
function applyDisplayPreferences(textSize, highContrast) {
  const size = ["small", "default", "large"].includes(textSize) ? textSize : "default";
  document.documentElement.dataset.textSize = size;
  document.documentElement.dataset.contrast = highContrast ? "high" : "default";
  $$("[data-text-size]").filter(button => button instanceof HTMLButtonElement).forEach(button => {
    button.setAttribute("aria-pressed", String(button.dataset.textSize === size));
  });
  $("#contrastToggle").setAttribute("aria-pressed", String(highContrast));
  $("#contrastToggle").setAttribute("aria-label", highContrast ? "Use standard contrast" : "Use high contrast");
}
function saveDisplayPreferences() {
  try {
    localStorage.setItem("ip-sakti-display", JSON.stringify({
      textSize: document.documentElement.dataset.textSize,
      highContrast: document.documentElement.dataset.contrast === "high"
    }));
  } catch { /* Display controls still work if browser storage is unavailable. */ }
}
try {
  const preferences = JSON.parse(localStorage.getItem("ip-sakti-display") || "{}");
  applyDisplayPreferences(preferences?.textSize, preferences?.highContrast === true);
} catch { applyDisplayPreferences("default", false); }
$$("button[data-text-size]").forEach(button => button.addEventListener("click", () => {
  applyDisplayPreferences(button.dataset.textSize, document.documentElement.dataset.contrast === "high");
  saveDisplayPreferences();
}));
$("#contrastToggle").addEventListener("click", () => {
  applyDisplayPreferences(document.documentElement.dataset.textSize, document.documentElement.dataset.contrast !== "high");
  saveDisplayPreferences();
});

function invalidateAnswer() {
  state.askSequence++;
  state.askController?.abort();
  state.lastResponse = null;
  $("#answer").innerHTML = emptyAnswer;
  $("#answer").setAttribute("aria-busy", "false");
  $("#askBtn").disabled = false;
  $("#askBtn").innerHTML = 'Get a sourced answer <span aria-hidden="true">↗</span>';
}

function updateMemoryNote(message = "") {
  $("#memoryNote").textContent = message || (state.memoryExpired
    ? "This chat's server memory has expired. Earlier answers remain visible; start a new chat and restate the question to continue."
    : "Temporary chat: recent turns and product context; expires after 30 minutes of inactivity. Reloading starts a new chat.");
}

function clearChat(message = "") {
  const oldId = state.conversationId;
  state.conversationId = null;
  state.turns = [];
  state.nextTurnId = 1;
  state.memoryExpired = false;
  state.lastQuestion = "";
  invalidateAnswer();
  $("#q").value = "";
  $("#chatHistory").innerHTML = "";
  $("#chatHistory").hidden = true;
  updateMemoryNote();
  if (message) toast(message);
  if (oldId) api("/api/chat/" + encodeURIComponent(oldId), undefined, undefined, "DELETE")
    .catch(() => toast("A new chat has started. The old server memory will expire automatically."));
}
$("#newChat").addEventListener("click", () => {
  clearChat("New chat started. Previous questions and sources are no longer used.");
  $("#q").focus();
});

function updateScope() {
  $("#scopeText").textContent = jurisdictionLabel(state.jurisdiction) + " · " +
    (state.categoryLabel || "Ayurveda IP & regulation");
  $("#lang").value = state.lang;
}

function jurisdictionLabel(jurisdiction) {
  return jurisdiction === "Both" ? "India + international" : jurisdiction;
}

function answerModeLabel(source) {
  return ({
    rag_synthesis: "AI synthesis from retrieved sources",
    reviewed_guidance: "Reviewed local guidance",
    grounded_synthesis: "Reviewed local guidance",
    llm_selected: "Reviewed guidance · AI-selected sources",
    extractive: "Source excerpts"
  })[source] || "";
}

function answerOutcomeLabel(result) {
  if (result.reason === "out_of_scope") return "Outside Ayurveda scope";
  if (result.reason === "translation_unavailable") return result.translation_status === "language_selection_required"
    ? "Choose a language" : "Translation unavailable";
  return result.abstained ? "Further verification needed" : "Sourced answer";
}

const examples = {
  India: [
    ["Classical formula & patents", "Can a classical Ayurvedic formula be patented?"],
    ["Patent examination deadline", "What is the request-for-examination deadline for an Ayurvedic formulation patent in India?"],
    ["Protect a brand", "How can I protect the brand name of an Ayurvedic product?"]
  ],
  International: [
    ["PCT filing route", "How can I use the PCT route to seek patent protection for an Ayurvedic formulation in several countries?"],
    ["EU herbal registration", "Why do Ayurvedic products struggle to register in the EU?"],
    ["GRATK & Ayurveda", "What does the WIPO GRATK treaty mean for Ayurveda patents, and can these sources confirm whether it is in force?"]
  ],
  Both: [
    ["India, US & EU", "Compare the IP and regulatory issues for launching an Ayurvedic formulation in India, the US and the EU. Identify evidence gaps for each market."],
    ["Protect overseas", "How can an Ayurveda startup protect its formulation and brand in India and overseas?"],
    ["Biodiversity & patents", "What biodiversity and traditional-knowledge issues should an Ayurvedic product developer consider for Indian patents and international patent filings?"]
  ]
};
function renderExamples() {
  $("#examples").innerHTML = '<span class="examples-label">Try a question:</span>' +
    examples[state.jurisdiction].map(([label, query]) =>
      '<button type="button" data-query="' + esc(query) + '">' + esc(label) + '</button>').join("");
}
$("#examples").addEventListener("click", event => {
  const button = event.target.closest("[data-query]");
  if (!button || $("#askBtn").disabled) return;
  $("#q").value = button.dataset.query;
  ask();
});
$("#jseg").addEventListener("click", event => {
  const button = event.target.closest("[data-j]");
  if (!button || state.jurisdiction === button.dataset.j) return;
  state.jurisdiction = button.dataset.j;
  $$("#jseg button").forEach(item => {
    item.classList.toggle("active", item === button);
    item.setAttribute("aria-pressed", String(item === button));
  });
  clearChat("Jurisdiction changed. A new chat has started.");
  updateScope();
  renderExamples();
});
$("#lang").addEventListener("change", event => {
  const question = $("#q").value;
  state.lang = event.target.value;
  clearChat("Answer language changed. A new chat has started.");
  $("#q").value = question;
  updateScope();
});

async function loadHealth() {
  try {
    const health = await api("/api/health");
    $("#navCount").textContent = health.corpus_size;
    $("#modeflag").textContent = health.llm_enabled ? "AI-assisted sourced answers" : "Local source mode";
    $("#privacyNote").textContent = health.llm_enabled
      ? "Questions and recent chat context go to the configured model provider. Chat text stays in temporary memory, not the audit log."
      : "Local mode uses reviewed guidance from the available source library and may give limited answers to novel questions. Chat text stays in temporary memory, not the audit log.";
    $("#languageNote").textContent = health.translation_available
      ? "Ask in English or the selected language. Answers are machine-translated when needed; source notes stay in English."
      : "English is available offline. Other languages need a configured translation provider.";
    $("#lang").innerHTML = health.languages.map(language =>
      '<option value="' + esc(language.code) + '"' + (language.available ? "" : " disabled") + ">" +
      esc(language.name) + (language.available ? "" : " — unavailable") + "</option>").join("");
    updateScope();
  } catch {
    $("#modeflag").textContent = "Service unavailable";
    $("#languageNote").textContent = "The service could not be reached. Retry your request when it is available.";
  }
}

function trailHtml(trail) {
  if (!trail.length) return "";
  return '<details class="trail"><summary>' + trail.length + ' confirmed step' + (trail.length === 1 ? "" : "s") +
    ' · review or change</summary><ol>' + trail.map((step, index) =>
      '<li><button type="button" data-edit-step="' + index + '">' + esc(step.question) + '</button><br>' +
      esc(step.label || step.answer) + (step.inferred ? " (from your description; confirm or change)" : "") + "</li>"
    ).join("") + "</ol></details>";
}

function sourceCard(source, number, prefix = "answer") {
  const needsReview = source.review_status === "needs_review";
  const type = ({
    official_reference: "Official reference", primary_document: "Primary document", secondary: "Secondary source",
    research: "Research paper", patent_record: "Patent record"
  })[source.source_type] || "Source reference";
  const url = safeUrl(source.source_url || source.url);
  return '<article class="source-card" tabindex="-1" id="' + esc(prefix + "-" + source.id) + '">' +
    '<div class="source-card-top"><span class="source-number">' + number + '</span>' +
    '<span class="jurisdiction-badge ' + esc(source.jurisdiction) + '">' + esc(source.jurisdiction) + '</span>' +
    '<span class="status-badge' + (needsReview || source.time_sensitive ? " review" : "") + '">' +
    (needsReview ? "Needs primary review" : source.time_sensitive ? "Time-sensitive" : source.review_status === "primary_checked" ? "Primary source checked" : esc(type)) + '</span></div>' +
    '<h4 translate="no" lang="en">' + esc(source.statute) + '</h4><p class="source-section" translate="no" lang="en">' + esc(source.section) + '</p>' +
    (source.review_note ? '<p class="review-note" translate="no" lang="en">' + esc(source.review_note) + '</p>' : "") +
    (source.snippet && !needsReview
      ? '<details><summary>Read the complete research note</summary><p translate="no" lang="en">' + esc(source.snippet) + '</p></details>' : "") +
    '<div class="source-bottom">' + (url ? '<a href="' + esc(url) + '" target="_blank" rel="noopener noreferrer">Open source ↗</a>' : "") +
    '<time datetime="' + esc(source.as_of) + '">Source record: ' + esc(source.as_of) + '</time></div>' +
    (source.reviewed_on ? '<p class="field-help">Primary text checked: ' + esc(source.reviewed_on) + '</p>' : '') + '</article>';
}

function renderClassifier(result) {
  state.answers = {...result.answers};
  state.trail = result.trail;
  state.category = result.complete ? result.category : null;
  state.categoryLabel = result.complete ? result.category_detail.label : "";
  updateScope();
  let html = "";
  if (result.complete) {
    const detail = result.category_detail;
    html = '<div class="category-result"><span class="status-badge">Preliminary route</span>' +
      '<h3>' + esc(detail.label) + '</h3><p>' + esc(detail.definition) + '</p>' +
      [["IP options", detail.ip_posture], ["Biodiversity duties", detail.abs_posture], ["Regulatory route", detail.regulatory]]
        .map(([title, content]) => '<div class="posture-item"><h4>' + title + '</h4><p>' + esc(content) + '</p></div>').join("") +
      '</div><p class="field-help">This product category now scopes your research questions.</p>';
  } else if (result.next_question) {
    const next = result.next_question;
    html = '<p class="question-step">Step ' + (result.trail.length + 1) + '</p>' +
      '<h3 class="classifier-question">' + esc(next.question) + '</h3>' +
      '<p class="classifier-hint">' + esc(next.hint) + '</p>' +
      '<div class="options">' + next.options.map(option =>
        '<button class="option-button" type="button" aria-label="' + esc(next.option_labels[option] || option) + '" data-node="' + esc(next.node) + '" data-option="' + esc(option) + '">' +
        esc(next.option_labels[option] || option) + "</button>").join("") + "</div>";
  }
  if (result.needs_review) {
    html += '<div class="review-box"><h3>Confirm the route with a professional.</h3><p>' +
      esc(result.review_reason) + '</p><span class="status-badge review">Further facts needed</span></div>';
  }
  if (result.trail.length) html += '<button class="back-button" type="button" data-back>← Change the previous answer</button>';
  html += trailHtml(result.trail);
  if (result.citations.length) {
    html += '<details class="trail"><summary>Legal basis & source dates</summary>' +
      result.citations.map((source, index) => sourceCard(source, index + 1, "classify")).join("") +
      '<p class="field-help">' + esc(result.disclaimer) + '</p></details>';
  }
  $("#clsFlow").innerHTML = html;
}

async function stepClassifier(body = {answers: state.answers}, clearAnswer = true) {
  const sequence = ++state.classSequence;
  state.classController?.abort();
  state.classController = new AbortController();
  if (clearAnswer) {
    clearChat(state.turns.length ? "Product facts changed. A new chat has started." : "");
    state.category = null;
    state.categoryLabel = "";
    updateScope();
  }
  $("#clsError").hidden = true;
  $("#clsFlow").setAttribute("aria-busy", "true");
  $$("#clsFlow button, #descBtn").forEach(button => { button.disabled = true; });
  try {
    const result = await api("/api/classify", body, state.classController.signal);
    if (sequence === state.classSequence) renderClassifier(result);
  } catch (error) {
    if (sequence === state.classSequence && error.name !== "AbortError") {
      $("#clsError").textContent = error.message;
      $("#clsError").hidden = false;
    }
  } finally {
    if (sequence === state.classSequence) {
      $("#clsFlow").setAttribute("aria-busy", "false");
      $$("#clsFlow button, #descBtn").forEach(button => { button.disabled = false; });
    }
  }
}
$("#clsFlow").addEventListener("click", event => {
  const option = event.target.closest("[data-option]");
  if (option) {
    const answers = {...state.answers, [option.dataset.node]: option.dataset.option};
    stepClassifier({answers});
    return;
  }
  const edit = event.target.closest("[data-edit-step]");
  if (edit || event.target.closest("[data-back]")) {
    const index = edit ? Number(edit.dataset.editStep) : state.trail.length - 1;
    const answers = Object.fromEntries(state.trail.slice(0, index).map(step => [step.node, step.answer]));
    stepClassifier({answers});
  }
});
$("#descBtn").addEventListener("click", () => {
  const description = $("#desc").value.trim();
  if (!description) {
    $("#clsError").textContent = "Add a short product description, or answer the questions below.";
    $("#clsError").hidden = false;
    $("#desc").focus();
    return;
  }
  stepClassifier({description});
});
$("#resetCls").addEventListener("click", () => {
  $("#desc").value = "";
  state.answers = {};
  state.trail = [];
  stepClassifier({answers:{}});
});

// A deliberately small Markdown renderer: all source text is escaped and only
// generated markup is emitted. It never accepts raw HTML or arbitrary URLs.
function inlineMarkdown(text, citations, prefix) {
  const ids = new Map(citations.map((source, index) => [source.id, index + 1]));
  const pattern = /(`[^`\n]+`|\*\*[^*\n]+\*\*|\[[^\]\n]+\]\([^\s)]+\)|\[[a-z0-9_]+\])/g;
  let html = "", offset = 0;
  for (const match of String(text).matchAll(pattern)) {
    html += esc(text.slice(offset, match.index));
    const token = match[0];
    if (token.startsWith("`")) html += "<code>" + esc(token.slice(1, -1)) + "</code>";
    else if (token.startsWith("**")) html += "<strong>" + esc(token.slice(2, -2)) + "</strong>";
    else {
      const link = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      const id = token.slice(1, -1);
      if (link) {
        const url = safeUrl(link[2]);
        html += url ? '<a href="' + esc(url) + '" target="_blank" rel="noopener noreferrer">' + esc(link[1]) + "</a>" : esc(token);
      } else if (ids.has(id)) {
        html += '<a class="citation-link" href="#' + esc(prefix + "-" + id) + '" aria-label="Read source ' + ids.get(id) + '">' + ids.get(id) + "</a>";
      } else html += esc(token);
    }
    offset = match.index + token.length;
  }
  return html + esc(text.slice(offset));
}

function markdownHtml(text, citations = [], prefix = "answer") {
  const lines = String(text || "").replace(/\r\n?/g, "\n").split("\n");
  const inline = value => inlineMarkdown(value, citations, prefix);
  const cells = row => row.trim().replace(/^\|/, "").replace(/\|$/, "").split(/(?<!\\)\|/).map(value => value.trim().replace(/\\\|/g, "|"));
  const isTable = index => index + 1 < lines.length && lines[index].includes("|") &&
    cells(lines[index + 1]).length > 1 && cells(lines[index + 1]).every(value => /^:?-{3,}:?$/.test(value));
  let html = "";
  for (let index = 0; index < lines.length;) {
    const line = lines[index].trim();
    if (!line) { index++; continue; }
    if (isTable(index)) {
      const headers = cells(lines[index]);
      html += '<p class="table-help">Scroll sideways if needed to see every column.</p><div class="answer-table" role="region" aria-label="Scrollable answer comparison table" tabindex="0"><table><thead><tr>' +
        headers.map(value => '<th scope="col">' + inline(value) + "</th>").join("") + "</tr></thead><tbody>";
      index += 2;
      while (index < lines.length && lines[index].trim() && lines[index].includes("|")) {
        const values = cells(lines[index++]);
        if (values.length > headers.length) values[headers.length - 1] = values.slice(headers.length - 1).join(" | ");
        html += "<tr>" + headers.map((_, column) => "<td>" + inline(values[column] || "") + "</td>").join("") + "</tr>";
      }
      html += "</tbody></table></div>";
      continue;
    }
    const heading = line.match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      const level = Math.min(heading[1].length + 2, 6);
      html += "<h" + level + ">" + inline(heading[2]) + "</h" + level + ">";
      index++; continue;
    }
    const list = line.match(/^(?:([-*+])|(\d+)[.)])\s+(.+)$/);
    if (list) {
      const ordered = Boolean(list[2]);
      const tag = ordered ? "ol" : "ul";
      html += "<" + tag + (ordered ? ' start="' + Number(list[2]) + '"' : "") + ">";
      while (index < lines.length) {
        const item = lines[index].trim().match(/^(?:([-*+])|(\d+)[.)])\s+(.+)$/);
        if (!item || Boolean(item[2]) !== ordered) break;
        html += "<li>" + inline(item[3]) + "</li>";
        index++;
      }
      html += "</" + tag + ">";
      continue;
    }
    const paragraph = [line];
    index++;
    while (index < lines.length && lines[index].trim() && !isTable(index) &&
      !/^(#{1,6}\s|[-*+]\s|\d+[.)]\s)/.test(lines[index].trim())) {
      paragraph.push(lines[index++].trim());
    }
    html += "<p>" + paragraph.map(inline).join("<br>") + "</p>";
  }
  return html;
}

function handoffHtml() {
  return '<details class="handoff"><summary>Prepare for a professional review</summary>' +
    '<p>Bring this research brief to a qualified patent agent or Ayurveda regulatory professional, along with:</p>' +
    '<ul><li>The product formula, process and intended claims.</li>' +
    '<li>The relevant book references or assay data.</li>' +
    '<li>Applicant details, biological-resource origin and intended markets.</li></ul>' +
    '<p class="field-help">No referral or appointment is submitted by this app. The brief stays on your device when downloaded.</p></details>';
}

function resourcesHtml(resources = []) {
  if (!resources.length) return "";
  return '<h3 class="subheading">Official next steps</h3>' +
    resources.map(resource => {
      const gated = resource.access !== "free";
      const url = safeUrl(resource.url);
      return '<article class="resource-card' + (gated ? " gated" : "") + '"><div><h4 translate="no">' + esc(resource.name) + "</h4>" +
        (resource.note ? "<p>" + esc(resource.note) + "</p>" : "") + "</div>" +
        (gated ? '<button class="button secondary small" data-resource="' + esc(resource.id) + '">Review access →</button>'
          : url ? '<a class="button secondary small" href="' + esc(url) + '" target="_blank" rel="noopener noreferrer">Visit ↗</a>' : "") +
        "</article>";
    }).join("");
}

function answerHtml(turn) {
  const {result, question, id} = turn;
  const prefix = "answer-turn-" + id;
  const citations = result.citations || [];
  const dates = result.source_date_range;
  const outsideScope = result.reason === "out_of_scope";
  const languageUnavailable = result.reason === "translation_unavailable";
  const languageSelectionRequired = languageUnavailable && result.translation_status === "language_selection_required";
  const summary = !result.abstained && String(result.summary || "").trim();
  let html = '<article class="chat-answer" data-turn="' + id + '"><p class="answered-question"><strong>Your question</strong> <span translate="no" dir="auto">' + esc(question) + '</span></p>' +
    '<div class="result-meta"><span class="jurisdiction-badge ' + esc(result.jurisdiction) + '">' +
    esc(jurisdictionLabel(result.jurisdiction)) + '</span>' +
    (result.abstained ? '<span class="status-badge review">' + esc(answerOutcomeLabel(result)) + '</span>' :
      '<span class="status-badge" title="Number of sources cited; coverage may be incomplete">' +
      citations.length + ' cited source' + (citations.length === 1 ? "" : "s") + '</span>') +
    (answerModeLabel(result.answer_source) ? '<span class="status-badge">' + esc(answerModeLabel(result.answer_source)) + '</span>' : "") +
    (result.memory_used ? '<span class="status-badge">Uses this chat</span>' : "") +
    (result.evidence_scope === "previous_turn" ? '<span class="status-badge">Previous sources only</span>' : "") +
    (dates ? "<span>Records: " + esc(dates.oldest) + (dates.oldest === dates.newest ? "" : " – " + esc(dates.newest)) + "</span>" : "") + "</div>";
  if (result.abstained) {
    const heading = outsideScope ? "For Ayurveda IP & regulatory questions." :
      languageSelectionRequired ? "Choose your question's language." :
      languageUnavailable ? "Translation is unavailable." : "A reliable answer needs another step.";
    const nextStep = languageUnavailable
      ? '<p class="field-help">' + (languageSelectionRequired
        ? "Choose the language used in your question under Answer language, then submit it again."
        : "Retry your question. If it is already in English, choose English under Answer language and submit it again.") + '</p>'
      : outsideScope ? "" : handoffHtml();
    html += '<div class="review-box"><h3>' + heading + '</h3><div class="answer-text">' +
      markdownHtml(result.answer, citations, prefix) + "</div>" + nextStep + "</div>";
  } else if (summary) {
    html += '<section class="answer-summary" aria-labelledby="' + prefix + '-summary-title">' +
      '<h3 id="' + prefix + '-summary-title">Short answer</h3>' +
      '<div class="summary-text">' + markdownHtml(summary, citations, prefix) + '</div></section>' +
      '<details class="answer-details"' + (result.details_expanded ? " open" : "") + '><summary>Detailed explanation</summary>' +
      '<div class="answer-text">' + markdownHtml(result.answer, citations, prefix) + '</div></details>';
  } else {
    html += '<div class="answer-text">' + markdownHtml(result.answer, citations, prefix) + "</div>";
  }
  if (result.original_answer_en || result.original_summary_en) html += '<details class="english-original"><summary>Read the original English answer</summary>' +
    '<div lang="en" dir="ltr">' +
    (result.original_summary_en ? '<h3 class="subheading">Short answer</h3><div class="summary-text">' + markdownHtml(result.original_summary_en, citations, prefix) + '</div>' : "") +
    (result.original_answer_en ? '<h3 class="subheading">Detailed explanation</h3><div class="answer-text">' + markdownHtml(result.original_answer_en, citations, prefix) + '</div>' : "") + '</div></details>';
  if (result.notices?.length) html += '<div class="result-notices">' +
    result.notices.map(note => "<p>" + esc(note) + "</p>").join("") + "</div>";
  html += '<div class="result-actions"><button class="button secondary small" data-copy>Copy with sources</button>' +
    '<button class="button secondary small" data-download>Download research brief ↓</button></div>';
  if (citations.length) html += '<details class="answer-sources"><summary>Sources you can inspect · ' + citations.length + '</summary>' +
    citations.map((source, index) => sourceCard(source, index + 1, prefix)).join("") + '</details>';
  html += resourcesHtml(result.registry_links);
  return html + '<p class="disclaimer-text">' + esc(result.disclaimer) + "</p></article>";
}

function renderHistory(includeLatest = false) {
  const previous = includeLatest ? state.turns : state.turns.slice(0, -1);
  $("#chatHistory").hidden = !previous.length;
  $("#chatHistory").innerHTML = previous.length ? '<p class="history-label">Earlier in this chat</p>' + previous.map(turn =>
    '<details class="history-turn"><summary><span>Question ' + turn.id + '</span> <span translate="no" dir="auto">' + esc(turn.question) + '</span></summary>' +
    '<div lang="' + esc(turn.result.lang) + '" dir="' + (["ur", "ks", "sd"].includes(turn.result.lang) ? "rtl" : "ltr") + '">' + answerHtml(turn) + "</div></details>"
  ).join("") : "";
}

function renderAnswer(turn) {
  renderHistory();
  $("#answer").innerHTML = answerHtml(turn);
  $("#answer").setAttribute("lang", turn.result.lang);
  $("#answer").setAttribute("dir", ["ur", "ks", "sd"].includes(turn.result.lang) ? "rtl" : "ltr");
}

async function ask() {
  if ($("#askBtn").disabled) return;
  const query = $("#q").value.trim();
  if (!query) { $("#q").focus(); return; }
  state.askController?.abort();
  const sequence = ++state.askSequence;
  state.askController = new AbortController();
  const body = {query, jurisdiction: state.jurisdiction, lang: state.lang, category: state.category};
  state.lastResponse = null;
  $("#askBtn").disabled = true;
  $("#askBtn").innerHTML = '<span class="spinner" aria-hidden="true"></span> Preparing answer…';
  $("#answer").setAttribute("aria-busy", "true");
  renderHistory(true);
  $("#answer").innerHTML = '<p class="loading-note">Preparing a sourced answer in the ' + esc(jurisdictionLabel(body.jurisdiction)) + " scope…</p>";
  try {
    // The browser never persists chat IDs, questions or answers. Server memory
    // is scoped to this page and is deleted on an explicit scope reset.
    if (state.memoryExpired) throw new Error("This chat's temporary memory has expired. Start a new chat and restate the product facts and question; earlier sources are no longer available to the service.");
    const signal = state.askController.signal;
    const createChat = async () => {
      const chat = await api("/api/chat", {}, signal);
      if (sequence !== state.askSequence) {
        if (chat.conversation_id) api("/api/chat/" + encodeURIComponent(chat.conversation_id), undefined, undefined, "DELETE").catch(() => {});
        return false;
      }
      if (!chat.conversation_id) throw new Error("Temporary chat memory could not be started. Please retry.");
      state.conversationId = chat.conversation_id;
      return true;
    };
    if (!state.conversationId && !await createChat()) return;
    let result;
    try {
      result = await api("/api/ask", {...body, conversation_id: state.conversationId}, signal);
    } catch (error) {
      if (![409, 410].includes(error.status) || error.reason === "chat_busy" || sequence !== state.askSequence) throw error;
      state.conversationId = null;
      // A missing context must never become a fresh retrieval for a follow-up.
      // Conservatively require a user reset if the page has any earlier turn.
      const refersBack = /\b(previous|earlier|above|original|retrieved|follow[- ]?up|same|those|these|continue|it|that)\b/i.test(query);
      if (state.turns.length || refersBack) {
        state.memoryExpired = true;
        updateMemoryNote();
        throw new Error("This chat's temporary memory is no longer available. Earlier answers remain below. Start a new chat and restate the question and any sources it must use.");
      }
      if (!await createChat()) return;
      toast("Temporary memory restarted. Your standalone question is being retried.");
      result = await api("/api/ask", {...body, conversation_id: state.conversationId}, signal);
    }
    if (sequence !== state.askSequence) return;
    state.conversationId = result.conversation_id || state.conversationId;
    const turn = {
      id: state.nextTurnId++, question: query, result,
      contextQuestions: result.memory_used ? (result.context_question ? [result.context_question] : state.turns.map(item => item.question)) : []
    };
    state.turns.push(turn);
    state.turns = state.turns.slice(-8);
    state.lastQuestion = query;
    state.lastResponse = result;
    renderAnswer(turn);
    updateMemoryNote();
  } catch (error) {
    if (sequence === state.askSequence && error.name !== "AbortError") {
      $("#answer").innerHTML = '<div class="error-note" role="alert">' + esc(error.message) + (state.memoryExpired ? "" : " Please try again.") + "</div>";
    }
  } finally {
    if (sequence === state.askSequence) {
      $("#askBtn").disabled = false;
      $("#askBtn").innerHTML = 'Get a sourced answer <span aria-hidden="true">↗</span>';
      $("#answer").setAttribute("aria-busy", "false");
    }
  }
}
$("#askBtn").addEventListener("click", ask);
$("#q").addEventListener("keydown", event => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && !$("#askBtn").disabled) {
    event.preventDefault();
    ask();
  }
});

function researchBrief(turn) {
  if (!turn) return "";
  const {result, question, contextQuestions} = turn;
  return "# IP-SAKTI Sahayak — research brief\n\n" +
    "Question: " + question + "\n\nJurisdiction: " + jurisdictionLabel(result.jurisdiction) +
    "\nResearch domain: Ayurveda intellectual property and regulation" +
    "\nProduct category: " + (result.category || "Not classified") +
    "\nCorpus version: " + result.corpus_version +
    (answerModeLabel(result.answer_source) ? "\nAnswer mode: " + answerModeLabel(result.answer_source) : "") +
    "\nOutcome: " + answerOutcomeLabel(result) +
    "\nEvidence scope: " + (result.evidence_scope === "previous_turn" ? "Only sources retrieved for the previous answer" : "Curated source corpus") +
    (contextQuestions?.length ? "\n\nEarlier questions used as chat context:\n" + contextQuestions.map((text, index) => (index + 1) + ". " + text).join("\n") : "") + "\n\n" +
    (result.summary && !result.abstained ? "## Short answer\n\n" + result.summary + "\n\n## Detailed explanation\n\n" : "") + result.answer +
    (result.original_summary_en || result.original_answer_en ? "\n\n## Original English\n\n" +
      (result.original_summary_en ? "### Short answer\n\n" + result.original_summary_en + "\n\n" : "") +
      (result.original_answer_en ? "### Detailed explanation\n\n" + result.original_answer_en : "") : "") +
    "\n\n## Sources\n\n" + result.citations.map(source =>
      "[" + source.id + "] " + source.statute + " — " + source.section +
      "\nSource date: " + source.as_of + "; review status: " + source.review_status +
      "\n" + source.source_url + (source.review_note ? "\nReview note: " + source.review_note : "")).join("\n\n") +
    "\n\n" + (result.notices || []).join("\n") + "\n\n" + result.disclaimer + "\n";
}
$("#advisorView").addEventListener("click", async event => {
  const answer = event.target.closest("[data-turn]");
  const turn = answer && state.turns.find(item => item.id === Number(answer.dataset.turn));
  if (!turn) return;
  const citation = event.target.closest(".citation-link");
  if (citation) {
    const target = document.getElementById(citation.getAttribute("href").slice(1));
    if (!target || !answer.contains(target)) return;
    event.preventDefault();
    for (let parent = target?.parentElement; parent; parent = parent.parentElement) {
      if (parent instanceof HTMLDetailsElement) parent.open = true;
    }
    target.focus({preventScroll:true});
    target.scrollIntoView({block:"center"});
  }
  if (event.target.closest("[data-copy]")) {
    try { await navigator.clipboard.writeText(researchBrief(turn)); toast("Answer and source links copied."); }
    catch { toast("Copy is unavailable. Use Download research brief instead."); }
  }
  if (event.target.closest("[data-download]")) {
    const blob = new Blob([researchBrief(turn)], {type:"text/markdown;charset=utf-8"});
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "ip-sakti-research-brief.md";
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const button = event.target.closest("[data-resource]");
  if (button) openConsent(turn.result.registry_links.find(resource => resource.id === button.dataset.resource));
});

let pendingResource = null;
let sessionId;
try {
  sessionId = sessionStorage.getItem("ip-sakti-session") || crypto.randomUUID();
  sessionStorage.setItem("ip-sakti-session", sessionId);
} catch { sessionId = "session-" + Date.now() + "-" + Math.random().toString(36).slice(2); }

function openConsent(resource) {
  if (!resource) return;
  pendingResource = resource;
  $("#consentTitle").textContent = resource.access === "paid" ? "Review paid-resource access" : "Open a restricted-resource referral";
  $("#consentText").textContent = resource.name + ". Record your consent before continuing to its official referral page.";
  $("#consentError").hidden = true;
  $("#consentActions").hidden = false;
  $("#consentSuccess").hidden = true;
  $("#mYes").disabled = $("#mNo").disabled = false;
  $("#consentLink").removeAttribute("href");
  $("#consentDialog").showModal();
}
$("#closeConsent").addEventListener("click", () => $("#consentDialog").close());
async function recordConsent(decision) {
  if (!pendingResource) return;
  const resource = pendingResource;
  $("#mYes").disabled = $("#mNo").disabled = true;
  $("#consentError").hidden = true;
  try {
    const response = await api("/api/consent", {
      user_id: sessionId, resource_id: resource.id, consent: decision, purpose: "registry routing"
    });
    if (!response.logged) throw new Error("Consent was not recorded.");
    if (!$("#consentDialog").open || pendingResource !== resource) return;
    if (!decision) {
      $("#consentDialog").close();
      toast("Your decline was recorded. No resource was opened.");
    } else {
      const url = safeUrl(response.url);
      if (!url) throw new Error("The service did not provide a valid destination.");
      $("#consentLink").href = url;
      $("#consentActions").hidden = true;
      $("#consentSuccess").hidden = false;
      $("#consentLink").focus();
    }
  } catch (error) {
    $("#consentError").textContent = error.message + " No resource has been opened.";
    $("#consentError").hidden = false;
  } finally {
    if (pendingResource === resource) $("#mYes").disabled = $("#mNo").disabled = false;
  }
}
$("#mYes").addEventListener("click", () => recordConsent(true));
$("#mNo").addEventListener("click", () => recordConsent(false));

async function loadSources() {
  try {
    const data = await api("/api/sources");
    state.sources = data.sources;
    $("#corpusVersion").textContent = "Corpus " + data.version;
    renderSourceLibrary();
  } catch (error) {
    $("#sourceCount").textContent = "Source library could not be loaded.";
    $("#sourceList").innerHTML = '<div class="error-note">' + esc(error.message) + "</div>";
  }
}
function renderSourceLibrary() {
  const search = $("#sourceSearch").value.trim().toLowerCase();
  const scope = $("#sourceScope").value;
  const review = $("#sourceReview").value;
  const selected = state.sources.filter(source =>
    (!scope || source.jurisdiction === scope) &&
    (!review || (review === "needs_review" ? source.review_status === "needs_review" : source.time_sensitive)) &&
    (!search || [source.statute, source.section, source.title, source.regime, source.snippet].join(" ").toLowerCase().includes(search)));
  const needsReview = state.sources.filter(source => source.review_status === "needs_review").length;
  $("#sourceCount").textContent = selected.length + " of " + state.sources.length + " sources · " +
    needsReview + " notes withheld from answers pending primary review";
  $("#sourceList").innerHTML = selected.length
    ? selected.map((source, index) => sourceCard(source, index + 1, "library")).join("")
    : '<p class="empty-note">No sources match these filters.</p>';
}
$("#sourceSearch").addEventListener("input", renderSourceLibrary);
$("#sourceScope").addEventListener("change", renderSourceLibrary);
$("#sourceReview").addEventListener("change", renderSourceLibrary);

renderExamples();
Promise.allSettled([loadHealth(), stepClassifier({answers:{}}, false), loadSources()]);
