# Answer and conversation repair — 27 September 2026

The reported Ayurvedic product strategy and its follow-up exposed three coupled defects. The answer generator was explicitly forbidden to synthesize an answer, a global score cutoff reduced broad questions to a few excerpts, and the API had no conversation identity. The second question consequently searched the words in formatting instructions and returned an unrelated Form 27 note.

## Resulting behavior

- The question planner separates legal subjects from formatting instructions and preserves the issues requested in a broad question. Retrieval gives each issue an evidence opportunity instead of using a single top-three cutoff.
- The answer layer composes reviewed source-specific rules and conditional applications. Requested decision tables and evidence tables are rendered as actual tables. A row without support says `Insufficient evidence in retrieved sources.` It does not disappear. Exact statutory anchors and citations remain inspectable.
- `Established by source`, `Inference/application`, and `Not established by retrieved sources` distinguish the strength and type of each conclusion. Patent and regulatory outcomes are conditional on facts the app cannot determine.
- A source-only follow-up uses only an immutable copy of the previous answer's cited documents. It does not invoke retrieval, silently add a source, or use updated corpus content in place of the earlier snapshot. Its corpus version remains the snapshot's version.
- The backend retains bounded temporary context behind a cryptographically random conversation ID. Questions and source snapshots are not written to audit logs. New chat, explicit deletion, expiry and capacity eviction remove access to the previous context. Concurrent requests in one chat are rejected rather than racing history updates. A cleared chat cannot be restored by a late request.
- The UI has New chat, expandable earlier turns, distinct citation anchors per answer, safe table/list formatting, and copy/download of the actual answer plus sources. Scope changes reset chat context; expiry is explained rather than disguised as a fresh search.
- Registry routing no longer truncates a broad strategy's authority links before reaching biodiversity and drug regulators.

## Evidence boundaries

The original three-source response remains a useful regression fixture. When only its BDA sections 6/7 and PPV&FR documents are available, the follow-up must retain patent, secrecy, trademark, copyright, GI, classification and regulatory issues as gaps. New corpus coverage may improve a fresh question, but cannot retrospectively fill gaps in a source-restricted follow-up.

Reviewed local synthesis is deliberately bounded by the curated topics and records. Optional models select evidence; a valid citation token alone never authorizes arbitrary generated legal claims. Exact current procedures, applicant-specific conclusions and time-sensitive status still require adequate primary evidence. See [source updates](SOURCE_UPDATES.md) for the expanded legal coverage and remaining gaps.

## Reproduce

```powershell
python -m unittest discover -s tests -v
python -m backend.eval_runner --report eval/latest_report.json
python -m scripts.browser_smoke
```

`tests/test_conversation.py` covers the reported broad strategy, the source-only follow-up, the old three-source evidence restriction, independent and focused new questions, missing context, isolated chats, TTL/capacity, scope changes, concurrency, source snapshot immutability, clear-during-answer and metadata-only logs. Existing tests retain classification, grounding, source integrity, translation and consent checks. Browser tests cover the visible two-turn flow, table rendering, New chat, expiry and markup safety in addition to the earlier smoke scenarios.

Verification on 27 September 2026, corpus `5075e2e0290a52dc`: 80 unit/API tests and 40 offline evaluation cases pass. The browser report records 17 passing scenarios, including the reported Ayurvedic strategy and its restricted follow-up. These are behavioral regression checks, not a certification of legal correctness or unrestricted language understanding.

Review the saved [first answer](qa/ayurvedic-strategy-brief.md), [source-restricted follow-up](qa/ayurvedic-followup-brief.md), [evaluation report](../eval/latest_report.json) and [browser report](qa/browser-report.json). The first answer covers all core requested issues against the expanded corpus. Empty or partial prior evidence still yields the requested rows and explicit gaps without a new search.
