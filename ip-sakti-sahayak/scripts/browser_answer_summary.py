"""Summary-first answer regressions: python -m scripts.browser_answer_summary.

Uses the isolated offline server from browser_smoke; no model calls or real logs.
Browser-only fixtures exercise translations and hostile Markdown independently
of provider availability. Screenshots and the report go to docs/qa/answer-summary.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from scripts.browser_smoke import ROOT, server


def run(artifacts: Path) -> dict:
    artifacts.mkdir(parents=True, exist_ok=True)
    checks = []

    def passed(name):
        checks.append(name)
        print("PASS " + name, flush=True)

    with server() as (url, _), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000}, device_scale_factor=1,
            permissions=["clipboard-read", "clipboard-write"],
        )
        page = context.new_page()
        page.set_default_timeout(10000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url, wait_until="networkidle")
        expect(page.locator('[data-option="medicine"]')).to_be_visible()

        def ask(query):
            page.locator("#q").fill(query)
            with page.expect_response("**/api/ask") as response:
                page.locator("#askBtn").click()
            expect(page.locator("#answer")).to_have_attribute("aria-busy", "false")
            assert response.value.ok, response.value.text()
            return response.value.json()

        def download_brief(name):
            with page.expect_download() as download:
                page.locator("#answer [data-download]").click()
            path = artifacts / name
            download.value.save_as(path)
            return path.read_text(encoding="utf-8")

        first = ask("Can a classical Ayurvedic formula be patented?")
        assert not first["abstained"] and first["summary"].strip()
        assert not first["details_expanded"]
        expect(page.locator("#answer .answer-summary>h3")).to_have_text("Short answer")
        expect(page.locator("#answer .summary-text")).to_be_visible()
        assert not page.locator("#answer .answer-details").evaluate("node => node.open")
        assert not page.locator("#answer .answer-sources").evaluate("node => node.open")
        expect(page.locator("#answer .answer-details .answer-text")).not_to_be_visible()
        expect(page.locator("#answer .result-meta")).to_contain_text("Reviewed local guidance")
        page.locator("#answer").screenshot(path=str(artifacts / "short-answer-desktop.png"))
        passed("Classical formula answer explains first; detail and evidence are collapsed with mode visible")

        citation = page.locator("#answer .summary-text .citation-link").first
        source_id = citation.get_attribute("href")[1:]
        citation.click()
        expect(page.locator('[id="' + source_id + '"]')).to_be_visible()
        expect(page.locator('[id="' + source_id + '"]')).to_be_focused()
        assert page.locator("#answer .answer-sources").evaluate("node => node.open")
        assert not page.locator("#answer .answer-details").evaluate("node => node.open")
        passed("Summary citation reveals and focuses its source without requiring the detailed explanation")

        brief = download_brief("classical-formula-brief.md")
        assert brief.index("## Short answer") < brief.index(first["summary"])
        assert brief.index(first["summary"]) < brief.index("## Detailed explanation")
        assert brief.index("## Detailed explanation") < brief.index(first["answer"])
        assert brief.index(first["answer"]) < brief.index("## Sources")
        page.locator("#answer [data-copy]").click()
        expect(page.locator("#toast")).to_have_text("Answer and source links copied.")
        # The Windows clipboard may use CRLF while text-file reads normalize it.
        assert page.evaluate("navigator.clipboard.readText()").replace("\r\n", "\n") == brief
        passed("Copy and download include the short answer before detail, followed by matching sources")

        table = ask(
            "Based only on the sources retrieved for my previous question, create a table with: "
            "Issue | What the retrieved sources establish | Relevant section | What I should do."
        )
        assert table["memory_used"] and table["details_expanded"]
        expect(page.locator("#answer table")).to_be_visible()
        assert page.locator("#answer .answer-details").evaluate("node => node.open")
        assert not page.locator("#answer .answer-sources").evaluate("node => node.open")
        expect(page.locator("#chatHistory .history-turn")).to_have_count(1)
        page.locator("#chatHistory .history-turn>summary").click()
        history_citation = page.locator("#chatHistory .summary-text .citation-link").first
        assert history_citation.get_attribute("href") == "#" + source_id
        history_citation.click()
        expect(page.locator('[id="' + source_id + '"]')).to_be_focused()
        assert page.locator("#chatHistory .answer-sources").evaluate("node => node.open")
        assert not page.locator("#answer .answer-sources").evaluate("node => node.open")
        assert page.locator('[id="' + source_id + '"]').count() == 1
        passed("Requested tables are immediately visible; historical citations remain isolated to their turn")

        page.set_viewport_size({"width": 390, "height": 844})
        expect(page.locator("#answer table")).to_be_visible()
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        mobile_table = page.locator("#answer .answer-table")
        headers = mobile_table.locator("thead th")
        expect(headers).to_have_count(4)
        expect(headers.last).to_contain_text("What I should do")
        assert mobile_table.evaluate("node => node.scrollWidth > node.clientWidth")
        # Scroll the real overflow region using wheel input, then confirm that
        # the requested final column is fully inside its clipping viewport.
        headers.first.hover()
        page.mouse.wheel(mobile_table.evaluate("node => node.scrollWidth"), 0)
        # Fractional CSS pixels can report 0.99975 visibility for a fully
        # scrolled table. Allow rounding, then check the actual clipping edges.
        expect(headers.last).to_be_in_viewport(ratio=0.99)
        assert mobile_table.evaluate("""node => {
            const clip = node.getBoundingClientRect();
            const cell = node.querySelector('thead th:last-child').getBoundingClientRect();
            const left = clip.left + node.clientLeft;
            return cell.left >= left - 1 && cell.right <= left + node.clientWidth + 1;
        }""")
        assert mobile_table.evaluate("node => node.scrollLeft > 0")
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        expect(page.locator("#toast")).to_be_hidden()
        page.locator("#answer").screenshot(path=str(artifacts / "requested-table-mobile.png"))
        page.locator("#newChat").click()
        ask("Can a classical Ayurvedic formula be patented?")
        expect(page.locator("#answer .summary-text")).to_be_visible()
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        expect(page.locator("#toast")).to_be_hidden()
        page.locator("#answer").screenshot(path=str(artifacts / "short-answer-mobile.png"))
        passed("Mobile tables scroll to the final column; summaries and tables have no page overflow or toast obstruction")

        source_token = "[" + first["citations"][0]["id"] + "]"
        fixture = {
            **first,
            "summary": "<img src=x onerror=alert(1)> **Safe explanation** " + source_token +
                       " [Unsafe](javascript:alert(1))",
            "answer": "Detailed translated explanation. " + source_token,
            "original_summary_en": "Original English summary. " + source_token,
            "original_answer_en": "Original English detailed explanation. " + source_token,
            "lang": "hi",
        }
        page.route("**/api/ask", lambda route: route.fulfill(json=fixture))
        ask("Browser fixture: translated summary")
        expect(page.locator("#answer .summary-text").first).to_contain_text("<img src=x")
        assert page.locator("#answer img").count() == 0
        assert page.locator('#answer a[href^="javascript:"]').count() == 0
        page.locator("#answer .english-original>summary").click()
        expect(page.locator("#answer .english-original .summary-text")).to_contain_text("Original English summary")
        expect(page.locator("#answer .english-original [lang=en]")).to_have_attribute("dir", "ltr")
        original = page.locator("#answer .english-original .citation-link").first
        original_id = original.get_attribute("href")[1:]
        original.click()
        expect(page.locator('[id="' + original_id + '"]')).to_be_focused()
        translated_brief = download_brief("translation-rendering-fixture.md")
        assert translated_brief.index(fixture["summary"]) < translated_brief.index(fixture["answer"])
        assert translated_brief.index("## Original English") < translated_brief.index(fixture["original_summary_en"])
        assert translated_brief.index(fixture["original_summary_en"]) < translated_brief.index(fixture["original_answer_en"])
        passed("Translated short and detailed answers retain English originals; summary Markdown escapes HTML and unsafe links")

        page.unroute("**/api/ask")
        fallback = {**first, "summary": "", "original_summary_en": None, "details_expanded": False}
        page.route("**/api/ask", lambda route: route.fulfill(json=fallback))
        ask("Browser fixture: legacy response without summary")
        expect(page.locator("#answer .answer-summary")).to_have_count(0)
        expect(page.locator("#answer .answer-details")).to_have_count(0)
        expect(page.locator("#answer .answer-text")).to_be_visible()
        page.unroute("**/api/ask")
        page.locator("#newChat").click()
        abstention = ask("What is the current status of Rule 170?")
        assert abstention["abstained"]
        expect(page.locator("#answer .answer-summary")).to_have_count(0)
        expect(page.locator("#answer .review-box .answer-text")).to_be_visible()
        passed("Responses without summaries and abstentions retain the full visible answer")

        assert not errors, errors
        browser.close()

    report = {
        "passed": len(checks), "checks": checks,
        "note": "Isolated offline server; temporary logs. Translation and unsafe Markdown responses are browser fixtures.",
    }
    (artifacts / "browser-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Browser checks: {len(checks)}/{len(checks)} passed", flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=ROOT / "docs" / "qa" / "answer-summary")
    run(parser.parse_args().artifacts)
