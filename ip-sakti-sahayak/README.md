# IP-SAKTI Sahayak

A source-grounded research assistant for Ayurveda intellectual property and preliminary regulatory routing in India and international frameworks. The default local mode uses reviewed guidance; an explicitly configured model enables question-specific RAG synthesis.

Smart India Hackathon 2026 · PS 26045 · Team Victor Bytes

**Information, not legal advice.** Answers distinguish sourced rules, application to supplied facts, and evidence gaps. A citation match is not a guarantee of legal correctness or confirmation that a rule remains current.

## Run locally

Requires Python 3.10+; verified on Python 3.14.

~~~powershell
cd ip-sakti-sahayak
python -m pip install -r requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8077
~~~

Open [the advisor](http://127.0.0.1:8077). No model, API key, JavaScript build or network connection is required for English source-based answers. Choose a different port if 8077 is already occupied.

## What works

- **Six preliminary product routes:** classical ASU, proprietary ASU, potential new drug, phytopharmaceutical, Ayurveda Aahara and cosmetic. The questionnaire explicitly checks administration route, therapeutic claims, book eligibility and ingredient/assay conditions. Uncertain or out-of-scope products go to review. Descriptions can identify intended use; they cannot establish statutory eligibility.
- **Ayurveda scope:** the assistant handles Ayurveda IP and regulatory questions, including legal-reference questions useful to that research without completing the product questionnaire. A concrete unrelated software, electronics or other technology case is redirected to explain its Ayurveda connection. A previous Ayurveda question or a selected product category does not make an unrelated new case in scope.
- **India and international research:** choose India, International or India + international. An explicit question naming India and an international framework can retrieve both scopes even while India is selected. Source jurisdiction labels stay visible, and the product questionnaire always describes an Indian regulatory route. The corpus has an EU herbal-medicine note but no US market-access source; a US request produces an evidence gap rather than an invented FDA route.
- **Question-specific planning and answers:** the optional model decomposes the current question into subquestions and search phrases, with verbatim fact validation. Retrieved evidence supports structured RAG synthesis; source IDs, exact supporting spans and supplied-fact spans are checked, followed by a separate model entailment check. Failed checks fall back to reviewed local guidance. These checks reduce unsupported output but do not certify legal correctness.
- **Transparent local guidance:** offline planning still uses topic rules and reviewed answer cards, with fact-sensitive conditional applications and missing-fact questions. It preserves the distinction between reading classical texts and establishing formula conformity, and between wild and cultivated sourcing. Novel wording or issues outside the reviewed topics can remain unsupported. The UI and exported brief identify the answer mode.
- **Temporary chat memory:** the same chat can carry product context into follow-ups. Requests limited to previous sources reuse an immutable snapshot of the previous answer's citations and bypass retrieval. The browser retains only the current page's history; New chat, scope changes and reload start afresh. Server memory expires after 30 minutes of inactivity and retains at most eight recent turns with bounded product context. Missing or expired context is explicit.
- **Source governance:** dated records have source types, review states and a content-derived corpus version. The source library exposes the current count, provenance and records that need review. Complete summaries are distinguishable from actual statutory quotations.
- **Appropriate abstention:** unsupported questions, unavailable translation, disputed records and unverified current status produce an explicit reason and a useful next step.
- **Official next steps:** category-aware links distinguish ASU licensing from CDSCO. Restricted-resource referrals require a successful consent write before the UI receives the destination. Consent does not purchase access or submit an application.
- **Practical UI:** editable classification history, expandable chat history, safe Markdown tables, jurisdiction-specific examples, accessible controls, mobile layout, source search, copy/download of sourced answers, HTTP error recovery and protection against obsolete responses.
- **Minimal logs:** query text, product descriptions and generated answers are excluded from new audit entries. Only request metadata is logged. Consent records use a session identifier and canonical resource ID.

## Research corrections

The implementation review found problems in both the code and the dossier. See [the review](docs/IMPROVEMENT_REVIEW.md) and [updated dossier](docs/RESEARCH_DOSSIER.md).

Two biodiversity notes were corrected against pages 3–4 of the NBA-hosted Biological Diversity (Amendment) Act, 2023:

1. Section 6 distinguishes NBA approval before grant for persons under section 3(2), registration before grant for persons under section 7, and approval at commercialisation under section 6(1B). It is not a uniform approval-before-filing rule.
2. The section 7 exemption for cultivated medicinal plants requires a certificate of origin from the Biodiversity Management Committee in the prescribed manner. Section-specific exemptions should not be advertised as a blanket waiver of all ABS or IP-related duties.

The [primary PDF](corpus/primary/biological-diversity-amendment-2023.pdf) and [hash manifest](corpus/primary/manifest.json) are saved locally. This check covers the cited amendment text, not every later rule or an individual applicant's circumstances.

The September 27 answer/chat repair and additional source verification are documented in [the answer review](docs/ANSWER_CHAT_REVIEW.md) and [source updates](docs/SOURCE_UPDATES.md). These supersede the earlier design decision to return only excerpts.

The September 28 [question-generalization review](docs/QUESTION_GENERALIZATION_REVIEW.md) explains why the earlier fixed answer cards performed poorly on different questions and records the Ayurveda boundary, conditional local guidance and optional RAG pipeline. It supersedes the September 27 description of the model as a source selector only. This software repair did not perform a new live legal-source review.

**Two notes remain withheld from factual answers:** the legacy/new-drug pathway summary and the neem case's non-primary citation. Rule 170, GRATK status and TKDL counts are marked time-sensitive; the app does not claim to have checked their live status.

## Optional models and translation

Copy env.sample to .env in this project. Defaults remain offline.

~~~powershell
Copy-Item env.sample .env
~~~

For model-assisted question planning and source-grounded RAG synthesis, explicitly set LLM_PROVIDER to anthropic or openai, LLM_MODEL to a model available on your endpoint, and LLM_API_KEY. LLM_BASE_URL can point to a compatible hosted or self-hosted service. A successful answer normally involves separate planning, synthesis and entailment-check calls; this increases provider latency and usage compared with local mode. The synthesis and its model checker use the same configured provider/model. [Live-provider testing](docs/LIVE_PROVIDER_REVIEW.md) has partial evidence: two saved syntheses passed the implemented checks, while the resumed gateway is unavailable. Set LLM_TIMEOUT for your provider; saved slow-gateway synthesis exceeded 90 seconds, compared with the application's 30-second default.

Set TRANSLATE_PROVIDER=llm to enable the translation layer. The UI lists English plus all 22 scheduled Indian languages, with availability determined by configuration. This is a provider capability switch, **not a quality certification for 22 languages**. Structured translation checks ordered segments and citation sequences; long answers require multiple calls. Failed translation returns the complete English fallback or an explicit abstention. English source notes remain visible. Post-repair live Hindi quality remains unverified during the gateway outage. IndicTrans2 and Bhashini connectors are not implemented.

Adjacent provider.txt files are ignored unless ALLOW_PROVIDER_FILE=true and a provider/model have been selected. LLM_PROVIDER=none always stays offline.

RETRIEVER=hybrid optionally adds sentence-transformers embeddings to BM25 through reciprocal-rank fusion. The default and evaluation mode use BM25. Retrieval budgets expand for requested issues, up to 48 source records; model search phrases can retrieve records beyond the local source-ID mappings. RERANK_TOP_N remains a legacy configuration field; no cross-encoder reranker is implemented.

## Verify

~~~powershell
python -m unittest discover -s tests -v
python -m backend.eval_runner --report eval/latest_report.json
python -m scripts.smoke_test
~~~

The evaluation uses the same answer pipeline as the API, explicitly disables model/translation calls, uses BM25 and does not write query audit logs. It checks expected abstention, reasons, source matches, jurisdiction and important content such as the RFE transition exception. It exits nonzero when a case fails.

For browser checks:

~~~powershell
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python -m scripts.browser_smoke
~~~

The browser suite starts an isolated local server with temporary logs, tests normal/error/consent/race flows and writes desktop/mobile screenshots to docs/qa. It does not open external referral pages.

Current evidence: [behavioural scorecard](eval/latest_report.json), [browser report](docs/qa/browser-report.json), [desktop](docs/qa/advisor-desktop.png), [mobile](docs/qa/advisor-mobile.png). These seeded checks are regression evidence, not a legal-accuracy benchmark. Optional live model, dense-model and translation quality integrations have not been certified by this offline suite.

## API

Interactive schema: [Swagger UI](http://127.0.0.1:8077/docs).

| Method | Path | Contract |
|---|---|---|
| GET | /api/health | Effective retrieval mode, corpus version, model/translation availability and privacy metadata |
| POST | /api/classify | Answers and optional description → next question, continuation answers, preliminary route or review; includes citations |
| POST | /api/chat | Create an opaque temporary conversation ID |
| POST | /api/ask | Query, jurisdiction, language, optional category/regime and conversation_id → sourced answer, sources, memory metadata and registry links |
| DELETE | /api/chat/{conversation_id} | Clear the conversation, including its source snapshots |
| POST | /api/consent | Anonymous session ID, known resource ID and a strict boolean decision → logged outcome; URL only after acceptance is saved |
| GET | /api/sources | Source library with provenance, dates, review notes and corpus fingerprint |

Requests reject unknown scopes, empty/oversized input and unsupported language codes. Clients should send back the classifier's returned answers object on the next step. Do not display a previous answer under a newly selected scope.

The `jurisdiction` request field accepts `India`, `International` or `Both`. The response preserves the requested value; an explicitly mixed question can use both sets of evidence under an `India` response, with a notice and individual citation labels explaining the actual evidence scope. `answer_source=rag_synthesis` identifies validated model synthesis; the existing `grounded_synthesis` value identifies reviewed local guidance. Clients should use `reason=out_of_scope` for an Ayurveda-domain redirect, not a request for professional review.

An ask without a conversation ID starts a new chat and returns its ID. Send that ID on subsequent turns; clients must not supply their own history or fabricated citations. IDs are opaque bearer capabilities, not authenticated accounts. Expired/cleared IDs return HTTP 410; conflicting scope or concurrent same-chat requests return HTTP 409. Different chats do not share context. Memory is bounded to 128 chats, with eight recent turn records and at most 12,000 context characters per record. Original product context can remain after its turn leaves the visible history. Idle chats can be evicted under capacity pressure. Expired records are swept every minute. Process restart clears all chats; use a single worker for this local prototype (a multi-worker deployment needs a secured shared TTL store or sticky routing).

## Structure

~~~text
backend/             API, classifier, retrieval, evidence selection, translation, privacy
config/              Reviewed questionnaire and official registry routing
corpus/corpus.jsonl   Curated legal/research records with provenance
corpus/primary/      Checked primary PDF and SHA-256 manifest
frontend/            HTML, CSS and browser JavaScript; no build step
tests/               Safety, grounding, classification and API regressions
eval/                Seeded behavioural cases and JSON scorecard
scripts/             Isolated API and browser smoke checks
docs/                Research dossier, implementation review and visual QA
~~~

## Privacy and remaining work

The [complex-question repair and browser retest](docs/COMPLEX_BROWSER_REPAIR.md) documents the observed failures, fixes, actual UI prompts and remaining coverage limits. Corrected case facts and markets now drive retrieval, and source-only follow-ups preserve both their evidence boundary and requested table columns. Substantial Indic-script input with English selected reports a language limitation when it cannot be interpreted.

This prototype makes no DPDP-compliance claim. New audit entries contain metadata only; chat context and source snapshots remain in process memory, never audit files or browser storage. Existing logs from earlier versions are not migrated or deleted. IP_SAKTI_LOG_DIR selects a private log directory. Authenticated user accounts, deployment access controls and a formal data-governance policy remain deployment work. Enabling a remote model or translation provider sends relevant question/context/source text to that provider.

The highest-priority research follow-ups are a current primary-source review of the new-drug pathway and neem decision, live checks for time-sensitive records, US market-access evidence and a licensed classical-text corpus. Local planning and reviewed guidance remain bounded by topic rules and available sources. Optional model planning and synthesis also remain limited by corpus coverage and fallible model checking; live-provider quality and multilingual legal fidelity have not been validated. Missing material is identified rather than authorized from general model knowledge. Human escalation prepares a local brief; there is no connected facilitator service. Paid subscriptions and restricted TKDL access are not connected.
