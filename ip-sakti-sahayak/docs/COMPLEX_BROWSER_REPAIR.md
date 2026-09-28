# Complex-question repair and browser retest

28 September 2026. Project scope remains Ayurveda intellectual property and regulatory guidance across India and international regimes.

The app was not replaying one saved answer. Its offline path relied on topic patterns, reviewed legal propositions and fixed formatting. Those mechanisms were too brittle: the earlier browser review demonstrated misplaced rules, lost facts and omitted topics. This repair changes shared planning, fact resolution and rendering rather than storing answers to the reported prompts.

## What changed

- A shared case-state parser retains verbatim assertions, resolves full and field corrections, and records withdrawn facts. Country labels remain attached to their intended market; cancelled exports no longer trigger foreign retrieval. Formatting instructions are excluded from asserted product facts.
- The Ayurveda boundary rejects unrelated technology even when a company name or a negated sentence contains Ayurveda terminology.
- Planning covers trademark paraphrases, EU member states, claims/advertising, cosmetic alternatives, multiple explicitly requested patent exclusions and unsupported topics. A US supplement label does not create an Indian food classification.
- Local applications separate contributors/ownership from patentability, public displays from undisclosed process details, and the evidence for individual claims. Missing, negative and preliminary positive experimental findings receive different conditional treatment.
- Medicine alternatives retain the statutory medicinal-purpose threshold; a classical-formula match alone does not classify a conditioning-only oil as an ASU drug. Foreign trademark comparisons explicitly identify the missing foreign-brand evidence instead of extending Indian trademark provisions abroad.
- Current-status checks respond to legal-status intent rather than isolated words such as “now,” “yet” or a year.
- Local and optional model rendering share custom table headings. A request restricted to previous sources retains an immutable source snapshot, preserves unsupported issues and performs no retrieval. Concise tables omit secondary procedural elaborations while preserving the primary rule's qualifications.
- Substantial Indic-script text entered with English selected produces an explicit language limitation. No credentials, model or translation service were enabled.
- The UI displays cited-source counts and answer mode instead of a prominent “High evidence match” badge. Language failures direct the user to ask in English.
- Four narrowly verified sources were added for patent applicant/inventor distinction, patent assignments, cosmetic definitions and cosmetic manufacturing licences. See [source-review evidence](SOURCE_COVERAGE_REPAIR.md).

## Browser verification

Final verification: **194 unit/integration tests passed**, **40/40 seeded offline evaluation cases passed**, and JavaScript syntax validation passed. **15 distinct prompts were exercised through Browser Use**, including the original ten and five further variations. These are bounded behavioral checks, not an accuracy percentage for arbitrary questions.

The ten original scenarios and five additional prompts were submitted through the running chat UI using Browser Use. Rendered answers were inspected and saved. Cases 2 → 3 → 4 and 13 → 14 use the same respective chat. The source-only restriction was also tested with retrieval replaced by a function that fails if called.

The first browser retest exposed instruction text being quoted as a fact. The additional prompts exposed an optional-colon table-header bug and incomplete interpretation of preliminary positive/missing claim evidence. Those findings were repaired and the affected cases rerun; the final saved observations contain the replacement results.

Artifact QA removed inherited `current_answer` fields from cases 1-10 because they contained earlier snapshots, including repaired scope failures, and did not describe the final rendered response. All 15 case identities, exact prompts and final `rendered_response` fields were retained; each rendered response contains its own prompt. The separate before-repair evidence was left unchanged. Use `rendered_response` as the final browser observation.

| Case | Final behavior checked | Remaining boundary |
|---|---|---|
| 1 | Employee/university facts, public leaflet versus secret parameters, trademark request and ownership provisions are retained and separated. | Actual contributions, agreements, prior art and title remain unverified. |
| 2 | India, Germany/EU and US are distinguished; cure claim and absent use-history evidence are addressed; no Indian-food inference from the US label. | No supported US regulatory route; EU and advertising procedure coverage remains narrow. |
| 3 | Lists withdrawn syrup facts; retains current oil, ownership, own-farm and conditioning facts; only India sources; cosmetic alternative is present. | Classification/licensing and applicant status remain conditional. |
| 4 | Exact four-column header, shorter table, cosmetic row and previous-source boundary. | A concise table is still substantial when preserving the statutory distinctions. |
| 5, 7, 8 | Unrelated banking cases rejected with no substantive herbal answer. | This is tested domain filtering, not proof against every possible wording. |
| 6 | Claim A's negative efficacy result and Claim B's additive result receive distinct 3(d)/3(e) applications; 3(p) and the separate process remain separate. | No patentability determination. |
| 9 | Hindi input reports translation unavailable instead of insufficient legal sources. | Hindi answer generation remains unavailable in this configuration. |
| 10 | Rule 170 current status is explicitly unverified and the dated record is identified. | No live-law verification performed. |
| 11 | France resolves to EU; proposed classification, dose and undocumented use history remain conditional; foreign trademark law has its own evidence gap. | French registration and trademark procedure are not comprehensively covered. |
| 12 | Differently numbered claims preserve missing efficacy experiments versus preliminary interaction evidence; no guarantee follows. | Data and claims have not been independently assessed. |
| 13 → 14 | Medicine-definition answer followed by a three-column source-only table; cosmetic test remains an explicit gap when absent from the snapshot. | New corpus evidence is intentionally not imported. |
| 15 | Paraphrased company-name bait remains out of Ayurveda scope. | Same bounded domain-filter limitation. |

## Limits of this result

Offline mode remains a bounded parser and reviewed-guidance engine. It can still miss unfamiliar phrasing and produce lengthy or generic explanations. Passing these checks does not establish arbitrary-question understanding or legal accuracy. The optional model planner/synthesizer retains exact source/fact checks and a separate model audit, but no live provider evaluation was performed. Configuring a provider alone is not evidence that the answer-quality problem is solved.

The corpus has 58 records. Four new passage reviews do not certify current law, complete international coverage, private ownership or product approvals. US regulatory routes, detailed member-state procedures, later amendments and live multilingual quality remain outside the verified result.

## Evidence

- [Before-repair manual review](MANUAL_COMPLEX_BROWSER_REVIEW.md)
- [Final rendered browser observations and exact prompts](qa/complex-browser-repair/browser-observations.json)
- [Browser screenshot: requested table](qa/complex-browser-repair/source-only-table.png)
- [Final browser screenshot: explicit unsupported issue](qa/complex-browser-repair/source-only-gap.png)
- [Source-only research brief captured through Copy with sources](qa/complex-browser-repair/source-only-research-brief.md)
- [Offline evaluation report](../eval/repair_report.json)
- Regression suites: `test_browser_pipeline_repair.py`, `test_browser_planning_repair.py`, `test_browser_case_repair.py`, and `test_source_coverage_repair.py`, plus the existing tests.

The copied Markdown brief was checked for exact table headings, source-only scope and the cosmetic evidence gap, without a cosmetic citation outside the snapshot. The in-app browser's download-event wait timed out and no new file appeared in Downloads, so the Download control's file delivery was not verified; Copy with sources successfully produced the shared research-brief content. No browser console error was reported for that attempt.
