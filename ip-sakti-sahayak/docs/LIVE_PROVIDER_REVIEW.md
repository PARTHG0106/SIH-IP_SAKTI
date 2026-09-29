# Live-provider test continuation — 29 September 2026

The resumed run found and repaired additional translation, planning and local
fallback defects. Live AI quality is still only partially verified: the configured
gateway currently returns HTTP 503, `all nodes exhausted; retry later`, for its
only listed model, `claude-opus-4-8`. Its model-list endpoint returned HTTP 200.
This is a gateway capacity failure; the run cannot establish successful inference
or translation while it persists. Credentials were read in process and were not
written to reports or browser configuration.

## Actual evidence

| Test group | Result |
| --- | --- |
| Existing saved live runs, 28 September | 5 scenarios: 2 AI syntheses passed the implemented checks; 2 synthesis timeouts returned local guidance; 1 Hindi query-translation output was rejected |
| Resumed live requests, 29 September | 11 scenarios exercised; 5 English synthesis scenarios returned local guidance after provider errors; Hindi translation was unavailable; 5 scope/current-status guards behaved correctly |
| Ayurveda scope with a provider configured | All 4 unrelated-technology cases rejected without a provider call |
| Source-only follow-up, resumed final API run | Previous source IDs preserved; instrumented retrieval calls = 0 |
| Unit/integration suite | 230 tests passed |
| Offline behavioural evaluation | 40/40 passed; model/translation disabled |
| API smoke suite | 14 tests passed (included in the full suite, not additional unique tests) |
| Browser form submissions | 6 scenarios: 2, 3, 4, 12, 13 and 14, using local guidance |
| Browser export | Copy with sources preserved the table, citations and explicit cosmetic evidence gap |

The six browser scenarios cover the mixed-market syrup, replacement with an
India-only hair oil, the requested four-column source-only table, positive versus
absent experimental evidence for separate patent claims, and a new cosmetic
question unsupported by the previous medicine-only sources. They do not constitute
a new live-model browser sweep. File-download delivery was not retested.

## Repairs

- **Translation:** requests now separate the translation task from quoted source
  data and require a structured response. Ordered segment IDs detect missing or
  reordered chunks. Citation sequences must match within each segment and across
  the complete answer. Predominantly non-English output cannot become an English
  retrieval query. Long answers use bounded batches with larger output budgets;
  any failed batch returns the entire English answer rather than partial output.
  A configured provider failure now has a distinct, accurate explanation.
- **Planner:** a unique capitalization-only match is restored to the user's exact
  wording. Altered numbers, negation and ambiguous matches remain rejected.
  Identical question/search strings no longer cause an unpacking failure.
- **Local fallback:** `outsourced` no longer triggers plant sourcing, `original
  formulation` no longer triggers geographical origin, and European medicinal-use
  history uses the foreign-route sources. A shared statute prefix is no longer
  sufficient to borrow an unrelated provision when relevant evidence is absent.
- **Live test reporting:** HTTP 200 and local guidance no longer count as live
  synthesis passes. Reports include provider failures, answer modes, translation
  success, citation consistency and retrieval counts for source-only requests.
  The default selection includes all 15 saved browser scenarios; failed checks
  produce a nonzero exit status. Test audit logs use a temporary directory.

## Remaining limits

The translation changes have mocked-provider regression coverage, not a successful
post-repair live Hindi round trip. Segment and citation checks do not prove semantic
fidelity. Other target-language semantics still require review; all 22 languages
have not been validated. Long translations require multiple serial provider calls.

The two saved accepted syntheses are useful evidence, but the saved audit accepted
some quotations that contained only part of the support for their claims. The full
source records contained the rules. Exact-span and model-audit checks therefore
must not be described as a legal-accuracy guarantee. See the
[saved trace review](qa/live-provider/saved-trace-review.md).

Successful saved synthesis calls took about 63 and 91 seconds. The live test runner
now allows 180 seconds per call. The application's configurable default remains
30 seconds; a slow gateway requires an explicit `LLM_TIMEOUT` appropriate to that
provider. Larger timeouts do not fix HTTP 503 capacity failures. The saved short
table was also too verbose, so live concision remains a quality issue to measure.

The app remains in local source mode. Local planning and answers still rely on
reviewed topic rules and source cards. No new international legal sources were
added, and US market-access and French procedure gaps remain explicit.

## Reproduce when the gateway is healthy

From `ip-sakti-sahayak`, with the existing ignored provider file:

```powershell
python -u scripts/live_provider_eval.py --provider-file ../provider.txt --provider anthropic --model claude-opus-4-8 --timeout 180 --output docs/qa/live-provider/healthy-rerun
```

This intentionally makes paid remote calls using synthetic test prompts. It does
not enable a persistent model configuration for the browser app. Review the saved
answers as well as the automated checks before treating generalization, legal
reasoning or multilingual quality as verified.

## Saved results

- [Resumed correction requests](qa/live-provider/resumed-corrections/results.json)
- [Provider-enabled scope guards](qa/live-provider/resumed-scope/results.json)
- [Final translation/status/source-only requests](qa/live-provider/resumed-final/results.json)
- [Browser observations](qa/live-provider/resumed-browser.json)
- [Copied sourced brief](qa/live-provider/resumed-source-only-brief.md)
- [Offline evaluation](../eval/live-repair-report.json)

![Browser source-only evidence gap](qa/live-provider/resumed-source-only.png)
