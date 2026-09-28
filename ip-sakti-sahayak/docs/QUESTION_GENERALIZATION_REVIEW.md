# Question generalization and Ayurveda scope — 28 September 2026

The reported difference between research briefs (3), (4) and (5) exposed a real limitation. The earlier implementation did not replay a saved answer for one exact question, but it assembled many answers from fixed topic-to-source mappings and reviewed answer cards. The earlier comprehensive Ayurveda strategy matched those mappings well. Different facts or a different field could still receive familiar Ayurveda applications instead of a fresh analysis of the actual question.

The submitted briefs were treated as examples of application output, not as instructions for this repair. Brief (4) describes software, an algorithm and an electronic device without an Ayurveda connection; that case is outside this project's hackathon scope. Brief (5) is an in-scope Ayurveda case. Its statement that the manufacturer studied classical texts does not establish that the complete formula is absent from those texts. Its mixed wild/cultivated sourcing and proposed US/EU exports also need separate analysis and explicit evidence gaps.

## What changed

### Ayurveda and jurisdiction boundaries

`backend/planning.py` now provides the deterministic Ayurveda-domain check used by the pipeline. Concrete unrelated technology cases are redirected before retrieval and are not stored as a usable Ayurveda follow-up. General statutory-reference questions remain available for Ayurveda research without requiring a product classification. The boundary is a bounded heuristic, not proof that every possible wording will be classified correctly.

The API accepts `jurisdiction="Both"`; the UI labels it **India + international**. A question explicitly naming India and an international framework can also retrieve both scopes while India remains selected. Sources and next-step links retain their own jurisdiction. The response's top-level jurisdiction still records the requested setting, and notices explain mixed evidence. Single-scope questions naming only a conflicting framework still receive a scope-change prompt.

The available EU traditional-herbal-medicine record supports a limited EU discussion. There is no US market-access source in this corpus. The planner keeps a United States issue so the answer can expose that gap; nearby EU or Indian evidence does not establish a US FDA route.

### Optional question planning and RAG synthesis

With a provider explicitly configured, `backend/planning.py` asks a model to decompose the current question into requested subquestions, research phrases, verbatim facts, missing-fact questions and output preferences. The response must have the expected JSON structure and bounds. Facts must be exact spans from the supplied question/context, and requested column labels must occur there. Invalid output falls back to the local plan, preserving the raw question.

`backend/retrieval.py` consumes that plan once. Each issue receives an evidence budget, and model-generated search phrases can find relevant corpus records without requiring an existing source-ID mapping for every future question. Jurisdiction, regime and category filters remain in force. Retrieval is bounded to 48 records and cannot fetch missing law from the web.

`backend/rag.py` then synthesizes against the retrieved source set. Before rendering, the implementation checks that:

- Every planned issue is represented in the expected order.
- Source claims name supplied source IDs and include an exact supporting span from that record's text.
- Applications cite supplied records and any quoted case facts occur in the question/context.
- Issues without evidence remain explicit gaps; unknown sources, invented fact spans and malformed structures are rejected.

A separate model call checks whether claims, applications and actions are entailed by the cited evidence, whether jurisdictions and supplied facts were handled correctly, and whether an issue or conditional question was skipped. This check uses the same configured provider/model; it is not an independent legal reviewer. An exact quote proves text membership, not that the quote actually supports a conclusion. The entailment check can also be wrong. Neither check certifies legal correctness or current law.

Only output passing both structural/evidence checks and the model check is rendered as `answer_source="rag_synthesis"`. Failure returns reviewed local guidance with a visible notice. Sources marked for primary review and time-sensitive records requested as current evidence remain subject to the existing withholding rules. Answer cards whose source fingerprints no longer match the reviewed record are not silently reused.

### More careful local guidance

The default remains offline. Local planning still uses topic rules, and `backend/answer_cards.py` still supplies reviewed legal propositions. `backend/case_analysis.py` adds conditional applications and missing-fact questions using only the reviewed source/card pairs actually available to the answer. It makes no provider calls and adds no source evidence.

The local applications now distinguish:

- A claimed exact classical-formula match, a stated absence from classical formulae, and an unresolved comparison. Company development or reading books alone proves none of these.
- Wild-sourced materials and cultivated materials. A supplier's cultivation statement does not by itself establish the required BMC certificate or eliminate separate biodiversity/IP duties.
- Applicant status, resource access, patent grant and later commercialisation. An Indian manufacturing address does not establish nationality, residence or control.
- Reported disclosures and unanswered disclosure questions. A question or hypothetical condition is not automatically treated as an asserted fact.

Current corrections can replace relevant older facts, and newly described cases start their own context. Follow-ups expressly limited to previous sources continue to use the previous answer's immutable source snapshot without fresh retrieval. Missing issues in that snapshot stay missing.

The existing `grounded_synthesis` API value remains compatible and is labelled **Reviewed local guidance** in the UI and exported briefs. The interface also explains that local mode can be limited on novel questions. This is improved conditional guidance within known topics, not unrestricted semantic understanding. The optional model path is intended to handle novel wording and decomposition; it is still limited by the corpus and has not received a live-provider quality evaluation in this repair.

## Configuration, sources and verification limits

Provider-disabled defaults remain unchanged: `LLM_PROVIDER=none`, `TRANSLATE_PROVIDER=none`, and BM25 retrieval. Enabling a provider sends relevant question/context/source text to that provider and ordinarily adds planning, synthesis and entailment-check calls. Translation is a separate configured capability. No live model, translation or dense-model quality validation was performed for this repair.

This change updates how the available records are selected and applied. It does not constitute a new live primary-source review. Source dates, provenance, quarantined records and time-sensitive warnings remain visible. The earlier [source updates](SOURCE_UPDATES.md) describe the corpus work already performed; a changed software path or corpus fingerprint must not be advertised as confirmation of current law.

On 28 September 2026, the full offline browser suite passed **18/18 scenarios** against corpus `5075e2e0290a52dc`. It covers the Ayurveda labels, answer-mode export, mixed India/international selection, an explicit US evidence gap, unrelated-technology rejection, source-only follow-ups, safe Markdown rendering, temporary memory, HTTP recovery, consent controls and desktop/mobile layout. Its isolated server disables providers and writes temporary logs. Desktop and mobile captures were visually inspected, and no horizontal page overflow or uncaught browser errors were reported. See the generated [browser report](qa/browser-report.json) and [evaluation scorecard](../eval/latest_report.json) for results. These are behavioral regression checks, not an accuracy benchmark for arbitrary legal questions.

The final offline unit suite passed **129/129 tests** and the existing behavioral evaluation passed **40/40 cases**. Regression fixtures retain the questions from the three reported briefs as data. Tests cover their changed behavior, multi-turn corrections, source-only snapshots across jurisdictions, malformed or unsupported model output, exact source spans, and rejection of superseded fact quotes. Model calls in these checks are mocked; passing them does not establish live-model answer quality. A revised offline response to the fifth brief is saved in [the revised brief](qa/generalized-brief-5.md).

Remaining work includes broader adversarial and paraphrase testing, a representative live-provider legal-quality evaluation, current primary-source reviews, US regulatory evidence, and validation of multilingual legal fidelity. The project remains an Ayurveda IP/regulatory research assistant with visible evidence limits.
