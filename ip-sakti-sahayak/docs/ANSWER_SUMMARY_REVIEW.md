# Short explanations before sources

The advisor previously presented detailed statutory propositions and evidence gaps before giving the user a usable answer. This was especially noticeable when model synthesis failed: a simple question such as “Can a classical Ayurvedic formula be patented?” produced several legal sections without a direct conclusion.

Supported answers now have a separate cited short explanation. The example starts by explaining that, in India, an unchanged traditional formula generally cannot be patented, then distinguishes a potentially new formulation or process and the separate regulatory term “patent or proprietary medicine.” Section 3(e)'s mere-admixture test remains conditional; classical status does not establish additive effects.

## Presentation and API

- `summary` contains the short explanation; `answer` keeps the detailed reasoning.
- The UI shows the short answer first. Detailed reasoning and sources expand independently. A citation reveals and focuses its source within the correct chat turn.
- Requested tables, steps, detailed answers and fact corrections keep their detailed response open.
- Copy and research-brief downloads include the summary, detail, English originals when applicable, and sources.
- Empty summaries and abstentions retain a visible full answer.
- Summary and detail translations succeed together or fall back together to English. Both English originals remain available after successful translation.

## Evidence and generalization

The configured model generates the summary and detail together. A structured validation step checks the summary's length, citations and exact supplied-fact spans. Summary sources must also appear in the structured detailed evidence. The existing separate evidence audit examines both parts, including conclusions, qualifications and conflicts between them. Citation objects cover both rendered parts even when requested table columns omit some supporting detail. These checks are fallible and do not certify legal accuracy.

When synthesis is unavailable or rejected, local summaries use plain-language explanations attached to eligible reviewed source cards. They are selected by the question's topics, rather than matching an exact example question. Source fingerprints, withheld records and previous-source-only restrictions still apply. Local summaries remain bounded by reviewed topics and do not independently decide complex case facts.

## Verification

The automated suite covers summary source/fact boundaries, provider fallback, atomic translation, requested formats, and citation retention. The focused browser suite covers the real offline API, summary visibility, source navigation, historical citations, copy/download, mobile scrolling and fallback rendering. Translation and hostile-Markdown browser responses are explicitly fixtures; they are not live translation quality evidence.

Artifacts are saved in [docs/qa/answer-summary](qa/answer-summary/). The general browser suite is saved separately in [full-browser](qa/answer-summary/full-browser/). The saved live check identifies its answer mode, latency and output; provider configuration alone is not evidence of a successful AI answer.

Verified on 30 September 2026:

| Check | Result |
| --- | --- |
| Full Python regression suite | 265 passed |
| Offline behavioural evaluation | 40/40 passed |
| General browser suite | 18/18 passed |
| Focused summary browser suite | 7/7 passed |

The topic tests include paraphrased ownership questions, sale permission, source-only follow-ups and certificate requirements. They also check that farm ownership and company shareholding do not automatically become IP-ownership questions.

Live checks against the configured provider on the same date exercised both paths:

- The classical-formula question returned a cited reviewed summary (`grounded_synthesis`, 64.91 seconds) after the model's evidence audit rejected its draft. This verifies the user-facing fallback, not an accepted AI answer for that question.
- A different question, “Can a trademark protect the name of my Ayurvedic brand?”, returned a direct cited AI summary (`rag_synthesis`, 39.52 seconds) that passed the implemented source audit.

An earlier live summary supplied a non-verbatim fact citation. The prompt now explicitly asks for empty fact quotations for general explanations and exact spans from the resolved case context when applying supplied facts. The validator remains unchanged. These two live cases are not a broad model-quality benchmark.

This change does not update the legal corpus or establish current law. Complex scenarios and live multilingual fidelity need broader evaluation beyond these regressions.
