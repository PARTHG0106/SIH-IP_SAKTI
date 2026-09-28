# Dossier-driven implementation review

Reviewed 23 September 2026. Scope: the supplied research dossier, the existing application and reproducible behaviour. The dossier's prior research claims were treated as provenance to inspect, not proof that the implementation was correct.

## What the dossier gets right

The strongest product idea is the combination of formulation classification, IP research, biodiversity duties and regulatory routing. Keeping jurisdictions explicit, exposing legal sources and abstaining when evidence is missing are useful foundations. A small, offline-capable rules and retrieval system fits this stage better than adding more infrastructure without improving evidence quality.

## Reproduced problems and fixes

| Finding | Concrete impact | Change |
|---|---|---|
| Keyword classification ignored negation | “not purified” became a purified fraction; a cream to treat eczema became a cosmetic | Only unambiguous intended use may be inferred. Users confirm the statutory facts. |
| Missing classification conditions | Any food became Ayurveda Aahara; proprietary ingredients and parenteral exclusions were not checked | Added claims, Schedule A, administration-route and First-Schedule ingredient checks, with review exits. |
| New claims treated as automatic new drugs | A novel ASU claim could be routed to CDSCO without establishing the governing definition | Proprietary eligibility uses ingredients; the new-drug outcome is an explicit preliminary review route. |
| First-sentence extraction | Rule 170 answers lost the later court order; “G.S.R.” was reduced to a fragment | Display complete source notes with dates and preserved qualifications. |
| One real citation legitimised fabricated prose | Mixed real/fake citations were accepted; fake tokens were simply removed | The model may select only supplied source IDs. All factual English passages are copied from corpus records. Invalid selections fall back. |
| Numeric confidence overstated certainty | Overlap with one generic word could answer unrelated queries | Stopword filtering, positive-score candidates, minimum lexical support and “evidence match” wording. |
| Date aggregation used the newest source | Old evidence looked as fresh as the newest citation | Show the date range and use its oldest date for the aggregate field. |
| Overbroad biodiversity summaries | All applicants appeared to need the same NBA approval; exemptions looked unconditional | Corrected s.6 and s.7 against the official amendment, including registration and the certificate condition. |
| Unreviewed source quality | The neem source was Wikipedia; new-drug terminology mixed legal frameworks | Mark these two records as needing review; withhold disputed passage text from answers. |
| “Current” status inferred from snapshots | Dated Rule 170, GRATK and TKDL notes were presented as live facts | Mark time sensitivity; abstain on current-status requests and show the dated reference. |
| Silent translation fallback | A Hindi question could be answered from the incidental English word “brand” | Explicit capability reporting, input-translation abstention, actual output-language metadata and citation-preservation checks. |
| Raw question logging | Formula details or personal information could be retained in audit files | Log metadata only; never store raw questions or descriptions in new audit entries. |
| Hidden credential discovery | A parent provider.txt could activate a model even with offline intent | Require explicit provider/model selection and separate credential-file opt-in. |
| Consent UI was the only boundary | Arbitrary resource names were logged; failed writes could still be treated as success | Resolve stable IDs on the server, canonicalise names and release the URL only after a successful consent write. |
| Stale UI state and missing continuation | Description-based classification lost answers; old answers remained after scope changes | Return/retain continuation state, add back/edit/reset, abort obsolete requests and clear dependent results. |
| Placeholder escalation | The button only displayed a stub alert | Offer a downloadable brief and a concrete list of material to bring to a professional. No referral is falsely claimed. |
| Optimistic evaluation claims | Citation presence passed while a material legal qualification was absent; the runner could use a model and failed on Windows console symbols | Evaluate the shared offline pipeline, include content/reason assertions and use portable console output and a failure exit code. |

## Primary-source correction

Source: [NBA-hosted Biological Diversity (Amendment) Act, 2023, Act 10 of 2023](https://www.nbaindia.nic.in/sites/default/files/2026-05/BDAct_2023.pdf). The Gazette is dated 3 August 2023. Pages 3–4 were read and visually checked on 23 September 2026. A [local copy](../corpus/primary/biological-diversity-amendment-2023.pdf) and [SHA-256 manifest](../corpus/primary/manifest.json) preserve the evidence.

- Amendment section 8 substitutes s.6(1), (1A) and (1B): persons under s.3(2) need approval before IP grant; persons under s.7 need registration before grant; s.7 IP holders need approval at commercialisation.
- Amendment section 9 substitutes s.7: its proviso is conditional, including the practitioner livelihood wording. Under s.7(2), cultivated medicinal plants require a certificate of origin from the Biodiversity Management Committee in the prescribed manner.
- These provisions support conditional guidance, not a uniform approval-before-filing rule or an exemption from every ABS/IP duty.

This review did not establish every subsequent notification, current application fee, regulator procedure or a specific applicant's eligibility.

## What the source labels mean

- **Dossier record:** carried from the research compilation; not newly verified in this implementation review.
- **Primary source checked:** the specified source text was inspected, with a separate review date. Currently the two biodiversity records.
- **Needs review:** the note is not suitable to support a factual answer until its authority or wording is corrected. Currently the neem decision and new-drug pathway.
- **Time-sensitive:** a dated record cannot establish current status. Currently Rule 170, GRATK and TKDL.

The text in the corpus is a curated summary even where the underlying source is a primary document. The interface says so. A corpus hash identifies the content loaded by a response; it is not a legal validation seal.

## Verification

Final check on 24 September 2026: **61 unit/API tests, 40/40 behavioural cases and 12/12 browser checks passed**, along with JavaScript syntax validation. Both saved reports identify corpus version **81fd537a6733a2da**. The API documentation/schema endpoints and local documentation links were also checked.

The committed scripts exercise all six routes, ambiguous/negated descriptions, safe abstention, source integrity, cross-jurisdiction restrictions, malformed model selections, failed translation, privacy and consent.

- Unit/API regressions: python -m unittest discover -s tests -v
- Shared-pipeline behavioural evaluation: python -m backend.eval_runner --report eval/latest_report.json
- Isolated API smoke checks: python -m scripts.smoke_test
- Isolated browser flows: python -m scripts.browser_smoke

See the [evaluation report](../eval/latest_report.json) and [browser report](qa/browser-report.json) for exact results. The browser script also produces [desktop](qa/advisor-desktop.png), [answer](qa/answer-desktop.png), [source-library](qa/sources-desktop.png) and [mobile](qa/advisor-mobile.png) captures.

The seeded evaluation now distinguishes dated evidence from live-status questions and explicitly expects unavailable offline translation to abstain. Its source-match metrics are not advertised as legal accuracy. Live model/dense integrations and the quality of translation into every language need their own evaluation.

## Remaining product work

1. Replace the two quarantined notes with current primary authority and review other general landing-page citations.
2. Define a governed legal-update process for time-sensitive records.
3. Integrate and evaluate an actual IndicTrans2/Bhashini deployment, with legal terminology and citation checks.
4. Expand source coverage, including trade secrets and the claimed seven-regime scope, and curate classical texts with edition-level licensing checks.
5. Implement real facilitator workflow and deployment-specific privacy, authentication, retention and access controls.

These are explicit gaps, not capabilities inferred from the dossier or from a green test score.
