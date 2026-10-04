"""Page-language regressions: python -m scripts.browser_page_language.

Uses the isolated offline server from browser_smoke. Real classifier, source
filters and an English answer exercise integration; small browser fixtures expose
dictionary collisions, pending states and an independently selected answer
language. No translation/model providers or third-party pages are contacted.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from playwright.sync_api import expect, sync_playwright

from scripts.browser_smoke import ROOT, server


DEVANAGARI = re.compile(r"[\u0900-\u097f]")
PREFERENCE = "ip-sakti-page-language"
QUESTION = "Can a classical Ayurvedic formula be patented?"
PRIVATE_DESCRIPTION = "Page-language test confidential formulation: India"


def settled(page):
    """Let mutation observers and the resulting layout finish, without a sleep."""
    page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")


def question_text(locator):
    return locator.evaluate("""element => {
        const copy = element.cloneNode(true);
        copy.querySelector('strong')?.remove();
        return copy.textContent.trim();
    }""")


def evidence(page):
    """UI labels may change; actual answers, source records and links must not."""
    return page.locator("#answer").evaluate("""root => ({
        content: [...root.querySelectorAll('.summary-text, .answer-text, .source-card h4, .source-section, .review-note, .source-card details > p')].map(el => el.textContent),
        links: [...root.querySelectorAll('a[href]')].map(el => el.getAttribute('href')),
        language: root.getAttribute('lang'),
        turn: root.querySelector('[data-turn]')?.getAttribute('data-turn')
    })""")


def run(artifacts: Path) -> dict:
    artifacts.mkdir(parents=True, exist_ok=True)
    checks = []
    layout_checks = []
    errors = []

    def passed(name):
        checks.append(name)
        print("PASS " + name, flush=True)

    with server() as (url, _), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        health = context.request.get(url + "/api/health").json()
        assert not health["translation_available"] and not health["llm_enabled"]
        page = context.new_page()
        page.set_default_timeout(10000)
        page.on("pageerror", lambda error: errors.append(str(error)))
        requests = []
        page.on("request", lambda request: requests.append((request.method, request.url))
                if "/api/" in request.url else None)
        page.goto(url, wait_until="networkidle")
        expect(page.locator('[data-option="medicine"]')).to_be_visible()
        expect(page.locator("html")).to_have_attribute("lang", "en")
        expect(page.locator("#pageLanguageToggle")).to_be_visible()
        expect(page.locator("#lang")).to_have_value("en")
        english = {
            "nav": page.locator("#advisorTab").inner_text(),
            "label": page.locator('label[for="q"]').inner_text(),
            "placeholder": page.locator("#q").get_attribute("placeholder"),
            "classifier": page.locator(".classifier-question").inner_text(),
        }

        def toggle_accessibility(code):
            label = "Read page interface in English" if code == "hi" else "Translate page interface to Hindi"
            button = page.locator("#pageLanguageToggle")
            expect(button).to_have_attribute("lang", "en")
            expect(button).to_have_attribute("aria-label", label)
            expect(page.get_by_role("button", name=label, exact=True)).to_be_visible()
            expect(button.locator("span")).to_have_attribute("lang", "en" if code == "hi" else "hi")
            expect(button.locator("span")).to_have_text("English" if code == "hi" else "हिन्दी")

        toggle_accessibility("en")

        def language(code, target=page, watch_requests=True):
            before = len(requests)
            if target.locator("html").get_attribute("lang") != code:
                target.locator("#pageLanguageToggle").click()
            expect(target.locator("html")).to_have_attribute("lang", code)
            settled(target)
            if watch_requests:
                assert len(requests) == before, "Changing page language caused an API request"

        def ask(query):
            page.locator("#q").fill(query)
            with page.expect_request("**/api/ask") as sent:
                with page.expect_response("**/api/ask") as received:
                    page.locator("#askBtn").click()
            expect(page.locator("#answer")).to_have_attribute("aria-busy", "false")
            settled(page)
            assert received.value.ok, received.value.text()
            assert sent.value.post_data_json["query"] == query
            assert sent.value.post_data_json["lang"] == "en"
            return received.value.json()

        page.locator(".description-box > summary").click()
        page.locator(".chat-information > summary").click()
        page.locator("#q").fill("India")
        page.locator("#desc").fill("India")
        page.evaluate("""() => {
            window.pageLanguageTestNodes = ['#q', '#desc', '#answer', '#clsFlow', '[data-option="medicine"]']
                .map(selector => [selector, document.querySelector(selector)]);
        }""")
        language("hi")
        toggle_accessibility("hi")
        for selector in ("#advisorTab", "#sourcesTab", 'label[for="q"]', ".classifier-question", "#modeflag"):
            expect(page.locator(selector)).to_contain_text(DEVANAGARI)
        expect(page.locator("#q")).to_have_attribute("placeholder", DEVANAGARI)
        expect(page.locator("#desc")).to_have_attribute("placeholder", DEVANAGARI)
        expect(page.locator("#q")).to_have_value("India")
        expect(page.locator("#desc")).to_have_value("India")
        expect(page.locator("#lang")).to_have_value("en")
        expect(page.locator(".description-box")).to_have_attribute("open", "")
        expect(page.locator(".chat-information")).to_have_attribute("open", "")
        assert page.evaluate("window.pageLanguageTestNodes.every(([selector, node]) => document.querySelector(selector) === node)")
        assert page.evaluate("key => localStorage.getItem(key)", PREFERENCE) == "hi"
        language("en")
        toggle_accessibility("en")
        expect(page.locator("#advisorTab")).to_have_text(english["nav"])
        expect(page.locator('label[for="q"]')).to_have_text(english["label"])
        expect(page.locator("#q")).to_have_attribute("placeholder", english["placeholder"])
        expect(page.locator(".classifier-question")).to_have_text(english["classifier"])
        assert page.evaluate("key => localStorage.getItem(key)", PREFERENCE) == "en"
        expect(page.locator("#q")).to_have_value("India")
        expect(page.locator("#desc")).to_have_value("India")
        passed("Hindi/English toggle has correctly tagged accessible and visible labels; controls, placeholders and offline status preserve DOM nodes, open details, typed text and answer-language selection without API calls")

        language("hi")
        page.locator('[data-node="q_intended_use"][data-option="medicine"]').click()
        expect(page.locator('[data-node="q_route"]')).to_have_count(3)
        expect(page.locator(".classifier-question")).to_contain_text(DEVANAGARI)
        expect(page.locator('[data-node="q_route"]').first).to_have_attribute("aria-label", DEVANAGARI)
        page.locator("#desc").fill(PRIVATE_DESCRIPTION)
        page.locator("#q").fill(QUESTION)
        language("en")
        assert not DEVANAGARI.search(page.locator(".classifier-question").inner_text())
        language("hi")
        expect(page.locator('[data-node="q_route"]')).to_have_count(3)
        expect(page.locator("#q")).to_have_value(QUESTION)
        expect(page.locator("#desc")).to_have_value(PRIVATE_DESCRIPTION)
        passed("New classifier steps and accessible option labels use Hindi; toggles retain the current step and typed form content")

        page.locator("#sourcesTab").click()
        expect(page.locator("#sourcesView")).to_be_visible()
        assert page.locator("#sourceScope option").evaluate_all("options => options.map(option => option.value)") == ["", "India", "International"]
        for scope, other in (("India", "International"), ("International", "India")):
            page.locator("#sourceScope").select_option(scope)
            expect(page.locator("#sourceList .source-card").first).to_be_visible()
            assert page.locator(f"#sourceList .jurisdiction-badge.{scope}").count() == page.locator("#sourceList .source-card").count()
            expect(page.locator(f"#sourceList .jurisdiction-badge.{other}")).to_have_count(0)
        page.locator("#sourceScope").select_option("India")
        page.locator("#sourceSearch").fill("biodiversity")
        expect(page.locator("#sourceList .source-card").first).to_be_visible()
        records = page.locator("#sourceList .source-card h4, #sourceList .source-section").all_text_contents()
        language("en")
        expect(page.locator("#sourcesView")).to_be_visible()
        expect(page.locator("#sourceScope")).to_have_value("India")
        expect(page.locator("#sourceSearch")).to_have_value("biodiversity")
        assert records == page.locator("#sourceList .source-card h4, #sourceList .source-section").all_text_contents()
        language("hi")
        expect(page.locator("#sourceCount")).to_contain_text(DEVANAGARI)
        page.locator("#sourceSearch").fill("")
        page.locator("#sourceScope").select_option("")
        passed("Hindi source filters retain API values, correctly restrict jurisdictions and preserve search, selected view and original research titles")

        page.locator("#advisorTab").click()
        baseline = ask(QUESTION)
        assert not baseline["abstained"] and baseline["citations"]
        expect(page.locator("#answer .citation-link").first).to_be_attached()
        original_evidence = evidence(page)
        language("en")
        assert evidence(page) == original_evidence
        language("hi")
        assert evidence(page) == original_evidence
        assert question_text(page.locator("#answer .answered-question")) == QUESTION
        passed("A real offline answer, citations, source research notes, links, answer language and turn identity survive both toggles unchanged")

        # Deliberately match UI dictionary entries: content-based translation must
        # not mistake user questions or supplied research evidence for UI labels.
        fixture = json.loads(json.dumps(baseline))
        fixture.update(summary="India", answer="Source library\n\n[" + fixture["citations"][0]["id"] + "]")
        fixture["citations"][0].update(statute="India", section="Source library", snippet="Advisor",
                                          review_note="India", review_status="primary_checked")
        page.route("**/api/ask", lambda route: route.fulfill(json=fixture))
        ask("India")
        expect(page.locator("#answer .summary-text")).to_have_text("India")
        expect(page.locator("#answer .source-card h4").first).to_have_text("India")
        assert question_text(page.locator("#answer .answered-question")) == "India"
        ask("Source library")
        expect(page.locator("#chatHistory .history-turn")).to_have_count(2)
        assert question_text(page.locator("#chatHistory .history-turn").last.locator(".answered-question")) == "India"
        assert question_text(page.locator("#answer .answered-question")) == "Source library"
        collision_evidence = evidence(page)
        for code in ("en", "hi"):
            language(code)
            assert evidence(page) == collision_evidence
            assert question_text(page.locator("#answer .answered-question")) == "Source library"
            last_history = page.locator("#chatHistory .history-turn").last
            assert question_text(last_history.locator(".answered-question")) == "India"
            assert "India" in last_history.locator(":scope > summary").text_content()
        page.unroute("**/api/ask")
        passed("Dictionary-like questions, history entries, response text and citation records stay original even when identical to translated UI labels")

        pending = []
        page.route("**/api/ask", lambda route: pending.append(route))
        page.locator("#q").fill("Page-language pending question")
        page.locator("#askBtn").click()
        expect(page.locator("#answer .loading-note")).to_be_visible()
        expect(page.locator("#askBtn")).to_be_disabled()
        expect(page.locator("#answer .loading-note")).to_contain_text(DEVANAGARI)
        language("en")
        expect(page.locator("#askBtn")).to_contain_text("Preparing answer")
        expect(page.locator("#answer .loading-note")).to_contain_text("Preparing a sourced answer")
        language("hi")
        expect(page.locator("#askBtn")).to_contain_text(DEVANAGARI)
        expect(page.locator("#askBtn")).to_be_disabled()
        assert len(pending) == 1
        pending[0].fulfill(json=fixture)
        expect(page.locator("#answer")).to_have_attribute("aria-busy", "false")
        expect(page.locator("#askBtn")).to_be_enabled()
        page.unroute("**/api/ask")
        page.locator("#newChat").click()
        expect(page.locator("#chatHistory")).to_be_hidden()
        expect(page.locator("#answer .empty-state h3")).to_contain_text(DEVANAGARI)
        expect(page.locator("#toast")).to_contain_text(DEVANAGARI)
        # Wait for new-chat deletion before measuring the next language toggle.
        page.wait_for_load_state("networkidle")
        language("en")
        expect(page.locator("#answer .empty-state h3")).to_have_text("Your next step starts with a question")
        expect(page.locator("#askBtn")).to_contain_text("Get a sourced answer")
        passed("Pending-answer and new-chat UI follow page language while preserving busy state, request count and English reversibility")

        page.locator("#q").fill(QUESTION)
        language("hi")
        storage = page.evaluate("[...Object.values(localStorage), ...Object.values(sessionStorage)]")
        assert not any(QUESTION in value or PRIVATE_DESCRIPTION in value or "Page-language pending question" in value
                       or "conversation_id" in value or baseline.get("conversation_id", "NO_CHAT_ID") in value for value in storage)
        page.reload(wait_until="networkidle")
        expect(page.locator("html")).to_have_attribute("lang", "hi")
        expect(page.locator("#advisorTab")).to_contain_text(DEVANAGARI)
        expect(page.locator(".classifier-question")).to_contain_text(DEVANAGARI)
        expect(page.locator("#q")).to_have_value("")
        expect(page.locator("#desc")).to_have_value("")
        expect(page.locator("#chatHistory")).to_be_hidden()
        expect(page.locator("#lang")).to_have_value("en")
        passed("Reload restores only Hindi display preference; questions, product text and chat content remain ephemeral")

        for code in ("en", "hi"):
            language(code)
            for text_size in ("default", "large"):
                page.locator(f'button[data-text-size="{text_size}"]').click()
                for width in (320, 390, 768, 1440):
                    page.set_viewport_size({"width": width, "height": 900})
                    for view in ("advisor", "sources"):
                        page.locator(f"#{view}Tab").click()
                        settled(page)
                        dimensions = page.evaluate("({width: innerWidth, scroll: document.documentElement.scrollWidth})")
                        case = {"language": code, "text_size": text_size, "width": width, "view": view}
                        assert dimensions["scroll"] <= dimensions["width"] + 1, (case, dimensions)
                        for selector in ("#pageLanguageToggle", "#advisorTab", "#sourcesTab", "#q" if view == "advisor" else "#sourceScope"):
                            box = page.locator(selector).bounding_box()
                            assert box and box["x"] >= -1 and box["x"] + box["width"] <= width + 1, (case, selector, box)
                        layout_checks.append(case)
                        if code == "hi" and text_size == "default" and width in (390, 1440):
                            device = "mobile" if width == 390 else "desktop"
                            page.screenshot(path=str(artifacts / f"hindi-{view}-{device}.png"), full_page=True)
        passed(f"Both views fit 320/390/768/1440 widths with default/large text in English and Hindi ({len(layout_checks)} layouts)")

        for invalid in ("{malformed", "fr"):
            invalid_context = browser.new_context()
            invalid_context.add_init_script("localStorage.setItem(" + json.dumps(PREFERENCE) + ", " + json.dumps(invalid) + ")")
            invalid_page = invalid_context.new_page()
            invalid_page.on("pageerror", lambda error: errors.append(str(error)))
            invalid_page.goto(url, wait_until="networkidle")
            expect(invalid_page.locator('[data-option="medicine"]')).to_be_visible()
            expect(invalid_page.locator("html")).to_have_attribute("lang", "en")
            language("hi", invalid_page, False)
            expect(invalid_page.locator("#advisorTab")).to_contain_text(DEVANAGARI)
            invalid_context.close()
        blocked_context = browser.new_context()
        blocked_context.add_init_script("""for (const name of ['localStorage', 'sessionStorage']) {
            Object.defineProperty(window, name, {get() {throw new DOMException('Storage disabled by test', 'SecurityError');}});
        }""")
        blocked_page = blocked_context.new_page()
        blocked_page.on("pageerror", lambda error: errors.append(str(error)))
        blocked_page.goto(url, wait_until="networkidle")
        expect(blocked_page.locator('[data-option="medicine"]')).to_be_visible()
        language("hi", blocked_page, False)
        expect(blocked_page.locator("#advisorTab")).to_contain_text(DEVANAGARI)
        language("en", blocked_page, False)
        expect(blocked_page.locator("#advisorTab")).to_have_text(english["nav"])
        blocked_context.close()
        passed("Malformed/unsupported saved language and unavailable local/session storage safely fall back and leave the toggle usable")

        independent_context = browser.new_context()
        independent_page = independent_context.new_page()
        independent_page.on("pageerror", lambda error: errors.append(str(error)))
        advertised_health = {**health, "translation_available": True,
                             "languages": [{"code": "en", "name": "English", "available": True},
                                           {"code": "hi", "name": "Hindi", "available": True}]}
        independent_page.route("**/api/health", lambda route: route.fulfill(json=advertised_health))
        independent_page.goto(url, wait_until="networkidle")
        independent_page.locator("#lang").select_option("hi")
        independent_page.locator("#q").fill(QUESTION)
        language("hi", independent_page, False)
        language("en", independent_page, False)
        expect(independent_page.locator("#lang")).to_have_value("hi")
        expect(independent_page.locator("#q")).to_have_value(QUESTION)
        independent_context.close()
        passed("An available Hindi answer-language selection stays independent of English/Hindi page language")

        assert not errors, errors
        browser.close()

    report = {
        "passed": len(checks), "checks": checks, "layouts": layout_checks,
        "note": "Isolated offline server; real classifier/filter/English answer plus browser-only dictionary-collision, pending-answer and advertised-language fixtures. No provider calls or third-party pages.",
    }
    (artifacts / "browser-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Browser checks: {len(checks)}/{len(checks)} passed", flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=ROOT / "docs" / "qa" / "page-language")
    run(parser.parse_args().artifacts)
