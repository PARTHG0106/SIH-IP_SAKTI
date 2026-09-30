# English questions with Hindi answers

The reported screen showed an English biodiversity question, Hindi selected under **Answer language**, and a message telling the user to rewrite the question in English. The backend supplied the selected answer language as the question's source language, and the recovery text assumed that the question itself was not English.

## Change

- Question normalization now uses automatic source-language detection when a translated answer is requested. It explicitly permits an already-English question to pass through unchanged in the validated translation response.
- The output language is determined by the requested answer language. Input normalization success includes unchanged English input; it does not mean the input text had to change.
- Native-script, romanized and mixed-language questions still require successful normalization. Latin script alone is not treated as proof of English.
- Failed input normalization offers retry or choosing English under Answer language for an already-English question. A request to select the intended language has distinct guidance.
- Changing Answer language preserves the question text while starting a fresh chat, so the suggested recovery does not erase the question.
- If either the detailed answer or summary fails output translation or citation checks, both return in English with an explicit notice and the actual response language. Partial translations are not combined.

Translation still depends on the configured provider. These changes do not guarantee provider availability or semantic fidelity for every supported language.

## Verification

The full Python suite passes 270 tests. New regressions cover the reported English question with Hindi selected, native/romanized/mixed input, failed normalization, both English originals, and atomic rollback after citation loss in either translated output field.

The focused browser suite passes 5/5 checks; the general browser suite passes 18/18. The focused suite uses clearly identified language fixtures and a real offline API request for recovery after selecting English. It does not call a model. Reports and screenshots are in [docs/qa/answer-language](qa/answer-language/).

The separate live check uses the configured provider and the exact reported question with `jurisdiction=Both` and `lang=hi`. Its saved [report](qa/answer-language/live-check.json) records actual translation status, answer mode, latency and the English originals; it must be read separately from the browser fixtures.

On 30 September 2026, this live check completed with `lang=hi`, `translation_status=translated`, `abstained=false`, a Hindi summary and full answer, and both English originals. Citation markers passed the existing translation checks. Answer generation used reviewed local guidance (`grounded_synthesis`); translation used the configured provider. The complete run took 238.33 seconds, including unsuccessful model synthesis and several translation batches. This verifies the reported language flow, not provider speed or comprehensive Hindi legal accuracy.
