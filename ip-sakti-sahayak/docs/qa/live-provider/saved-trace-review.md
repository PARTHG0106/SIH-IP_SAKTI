# Saved live-provider trace review

This review uses the previously saved `initial/results.json` and
`corrections/results.json`; it makes no new provider calls.

- The two saved synthesis fallbacks (corrections cases 2 and 3) are read
  timeouts at about 91 seconds. Neither reached synthesis validation.
  Successful synthesis took 62.579 seconds in initial case 6 and 90.909
  seconds in corrections case 4; the configured default timeout is 30 seconds.
  These traces do not support weakening evidence checks to improve delivery.
- Corrections case 4 lost model planning because one otherwise exact fact
  began with `we` while the supplied text began with `We`. The planner now
  recovers only a unique capitalization match and retains its original source
  wording. Changed numbers, negation, spacing and ambiguous matches still fail.
  A separate valid-schema defect, identical question and search text being
  deduplicated before unpacking, is also repaired.
- Both saved successful synthesis outputs pass the current structural and
  exact-span checks when replayed against the corpus. Their applications keep
  the material distinctions: uncertain formula conformity, Indian-only hair
  oil use, separate biodiversity duties, and distinct patent exclusions.
- A successful audit is not proof of quote-level entailment. In corrections
  case 4, some claims cite exact but incomplete supporting spans: the ABS-rate
  claim quotes exemption conditions rather than the rates, and the section 6
  claim quotes the warning against a uniform filing rule rather than its
  branches. The full source records contain those rules, but the auditor still
  returned `supported: true` despite its stricter quote requirement.
- The requested short table in corrections case 4 renders about 10,000
  characters. Prompted concision is not reliably enforced by the live model.
- In initial case 9, the provider returned an unsupported Hindi legal answer
  to the query-translation call. The application rejected that output and
  displayed an abstention; the unsupported text appears only in the diagnostic
  trace. This is a translation failure, not a successful synthesis.

The saved runs cover five cases, with two successful synthesized answers.
Provider-free tests verify parser, fact, coverage and fallback behavior; their
mocked audit verdicts do not measure real model entailment accuracy or latency.
The narrow planner repair passes 44 tests across planner grounding, live RAG
repair, planning scope and generalization.
