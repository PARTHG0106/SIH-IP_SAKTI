"""Answer-language browser regressions: python -m scripts.browser_answer_language.

The isolated server has model and translation providers disabled. Browser-only
health/response fixtures exercise language rendering and recovery instructions;
the final English retry uses the real offline API. No provider calls are made.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from scripts.browser_smoke import ROOT, server


QUESTION = "Can a classical Ayurvedic formula be patented?"
HINDI_QUESTION = "क्या शास्त्रीय आयुर्वेदिक सूत्र का पेटेंट कराया जा सकता है?"


def run(artifacts: Path) -> dict:
    artifacts.mkdir(parents=True, exist_ok=True)
    checks = []

    def passed(name):
        checks.append(name)
        print("PASS " + name, flush=True)

    with server() as (url, _), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        health = context.request.get(url + "/api/health").json()
        assert not health["translation_available"] and not health["llm_enabled"]
        baseline_response = context.request.post(
            url + "/api/ask", data={"query": QUESTION, "lang": "en", "jurisdiction": "India"})
        assert baseline_response.ok, baseline_response.text()
        baseline = baseline_response.json()
        assert not baseline["abstained"] and baseline["summary"]
        advertised_health = {
            **health, "translation_available": True,
            "languages": [{"code": "en", "name": "English", "available": True},
                          {"code": "hi", "name": "Hindi", "available": True}],
        }
        page = context.new_page()
        page.set_default_timeout(10000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.route("**/api/health", lambda route: route.fulfill(json=advertised_health))
        page.goto(url, wait_until="networkidle")
        expect(page.locator('[data-option="medicine"]')).to_be_visible()

        def ask(query, fixture=None):
            page.unroute("**/api/ask")
            if fixture is not None:
                page.route("**/api/ask", lambda route: route.fulfill(json=fixture))
            page.locator("#q").fill(query)
            with page.expect_request("**/api/ask") as sent:
                with page.expect_response("**/api/ask") as response:
                    page.locator("#askBtn").click()
            expect(page.locator("#answer")).to_have_attribute("aria-busy", "false")
            assert response.value.ok, response.value.text()
            return response.value.json(), sent.value.post_data_json

        def screenshot(name):
            expect(page.locator("#toast")).to_be_hidden()
            page.locator("#answer").screenshot(path=str(artifacts / name))

        summary_en = "An unchanged traditional Ayurvedic formula generally cannot be patented in India. [patents_3p]"
        answer_en = "Manufacturing-process claims require their own patentability assessment. [patents_invention]"
        summary_hi = "भारत में अपरिवर्तित पारंपरिक आयुर्वेदिक सूत्र का आम तौर पर पेटेंट नहीं कराया जा सकता। [patents_3p]"
        answer_hi = "निर्माण प्रक्रिया के दावों की पेटेंट पात्रता का अलग से आकलन आवश्यक है। [patents_invention]"
        translated = {
            **baseline, "summary": summary_hi, "answer": answer_hi,
            "lang": "hi", "requested_lang": "hi", "translation_status": "translated",
            "original_summary_en": summary_en, "original_answer_en": answer_en,
            "notices": ["Machine-translated guidance. Consult the original English source notes for legal wording."],
        }
        page.locator(".chat-information > summary").click()
        expect(page.locator("#languageNote")).to_be_visible()
        expect(page.locator("#languageNote")).to_contain_text("Ask in English or the selected language")
        page.locator("#q").fill(QUESTION)
        page.locator("#lang").select_option("hi")
        expect(page.locator("#q")).to_have_value(QUESTION)
        _, sent = ask(QUESTION, translated)
        assert sent["query"] == QUESTION and sent["lang"] == "hi"
        expect(page.locator("#answer")).to_have_attribute("lang", "hi")
        expect(page.locator("#answer .summary-text").first).to_contain_text("भारत में")
        expect(page.locator("#answer .review-box")).to_have_count(0)
        page.locator("#answer .english-original>summary").click()
        expect(page.locator("#answer .english-original .summary-text")).to_contain_text(summary_en.split(" [")[0])
        screenshot("english-question-hindi-answer-fixture.png")
        passed("An English question keeps its text and requests Hindi; the Hindi fixture and English original render correctly")

        output_failed = {
            **baseline, "summary": summary_en, "answer": answer_en,
            "lang": "en", "requested_lang": "hi", "translation_status": "output_failed",
            "notices": ["Answer translation failed or changed citation markers. The English answer is shown."],
        }
        ask(QUESTION, output_failed)
        expect(page.locator("#answer")).to_have_attribute("lang", "en")
        expect(page.locator("#answer .summary-text")).to_contain_text(summary_en.split(" [")[0])
        expect(page.locator("#answer .result-notices")).to_contain_text("The English answer is shown")
        expect(page.locator("#answer .review-box")).to_have_count(0)
        passed("An output-translation failure retains the English answer with its recovery notice")

        unavailable = {
            **baseline, "summary": "", "answer": "The translation service could not prepare this question for an answer. Retry the request.",
            "abstained": True, "lang": "en", "requested_lang": "hi",
            "reason": "translation_unavailable", "translation_status": "unavailable",
            "citations": [], "registry_links": [], "source_date_range": None, "notices": [],
        }
        ask(QUESTION, unavailable)
        expect(page.locator("#answer .review-box>h3")).to_have_text("Translation is unavailable.")
        help_text = page.locator("#answer .review-box>.field-help")
        expect(help_text).to_contain_text("Retry your question")
        expect(help_text).to_contain_text("If it is already in English, choose English under Answer language")
        expect(page.locator("#answer")).not_to_contain_text("Rewrite your question in English")
        expect(page.locator("#answer")).not_to_contain_text("Ask in English to continue")
        screenshot("english-question-hindi-unavailable-fixture.png")
        passed("An English question with Hindi selected gets retry or Answer language recovery instructions without an English rewrite demand")

        page.locator("#lang").select_option("en")
        expect(page.locator("#q")).to_have_value(QUESTION)
        recovered, sent = ask(QUESTION)
        assert sent["lang"] == "en" and sent["query"] == QUESTION
        assert not recovered["abstained"] and recovered["translation_status"] == "not_requested"
        expect(page.locator("#answer .summary-text")).to_be_visible()
        expect(page.locator("#answer .review-box")).to_have_count(0)
        passed("Choosing English preserves the question and succeeds through the real offline API")

        selection_required = {
            **unavailable, "requested_lang": "en", "translation_status": "language_selection_required",
            "answer": "This question contains substantial text in an Indic script, while English is selected. Select the intended language so it can be translated.",
        }
        ask(HINDI_QUESTION, selection_required)
        expect(page.locator("#answer .review-box>h3")).to_have_text("Choose your question's language.")
        expect(page.locator("#answer .review-box>.field-help")).to_have_text(
            "Choose the language used in your question under Answer language, then submit it again.")
        expect(page.locator("#answer .result-meta")).to_contain_text("Choose a language")
        expect(page.locator("#answer")).not_to_contain_text("Retry your question")
        screenshot("language-selection-required-fixture.png")
        page.locator("#lang").select_option("hi")
        expect(page.locator("#q")).to_have_value(HINDI_QUESTION)
        _, sent = ask(HINDI_QUESTION, translated)
        assert sent["lang"] == "hi" and sent["query"] == HINDI_QUESTION
        expect(page.locator("#answer .summary-text").first).to_contain_text("भारत में")
        passed("Language selection requests name the Answer language control and preserve the original question during recovery")

        assert not errors, errors
        browser.close()

    report = {
        "passed": len(checks), "checks": checks,
        "note": "Isolated offline server; advertised translation availability and translated/error responses are browser fixtures. English recovery uses the real offline API. No provider calls.",
    }
    (artifacts / "browser-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Browser checks: {len(checks)}/{len(checks)} passed", flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=ROOT / "docs" / "qa" / "answer-language")
    run(parser.parse_args().artifacts)
