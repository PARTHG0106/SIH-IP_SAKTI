"""Isolated browser regressions: python -m scripts.browser_smoke.

Install requirements-dev.txt and run python -m playwright install chromium.
The server uses temporary audit logs; QA images go to docs/qa.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
import httpx
from playwright.sync_api import sync_playwright, expect, Error

ROOT = Path(__file__).resolve().parent.parent


@contextmanager
def server():
    with tempfile.TemporaryDirectory(prefix="ip-sakti-browser-") as directory:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = {**os.environ, "LLM_PROVIDER":"none", "RETRIEVER":"bm25",
               "TRANSLATE_PROVIDER":"none", "IP_SAKTI_LOG_DIR":directory}
        with open(Path(directory) / "server.log", "w", encoding="utf-8") as log:
            process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(port)],
                cwd=ROOT, env=env, stdout=log, stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            url = f"http://127.0.0.1:{port}"
            try:
                with httpx.Client(timeout=0.5, trust_env=False) as client:
                    for _ in range(100):
                        if process.poll() is not None:
                            raise RuntimeError("Test server exited during startup.")
                        try:
                            if client.get(url + "/api/health").status_code == 200:
                                break
                        except httpx.HTTPError:
                            pass
                        time.sleep(0.1)
                    else:
                        raise RuntimeError("Test server did not become ready.")
                yield url, Path(directory)
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


def run(artifacts):
    artifacts.mkdir(parents=True, exist_ok=True)
    checks = []

    def passed(name):
        checks.append(name)
        print("PASS " + name, flush=True)

    with server() as (url, log_dir), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width":1440, "height":1000}, device_scale_factor=1)
        page = context.new_page()
        page.set_default_timeout(10000)
        errors = []
        submitted_questions = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def reset():
            page.goto(url, wait_until="networkidle")
            expect(page.locator('[data-option="medicine"]')).to_be_visible()

        def choose(node, option):
            page.locator(f'[data-node="{node}"][data-option="{option}"]').click()

        def ask(query):
            submitted_questions.append(query)
            page.locator("#q").fill(query)
            with page.expect_response("**/api/ask") as response:
                page.locator("#askBtn").click()
            expect(page.locator("#answer")).to_have_attribute("aria-busy", "false")
            try:
                return response.value.json()
            except ValueError as exc:
                raise AssertionError(f"/api/ask returned {response.value.status}: {response.value.text()}") from exc

        reset()
        corpus_version = page.request.get(url + "/api/health").json()["corpus_version"]
        expect(page.locator("#modeflag")).to_have_text("Local source mode")
        assert page.locator('#lang option[value="hi"]').is_disabled()
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        page.screenshot(path=str(artifacts / "advisor-desktop.png"), full_page=True)
        passed("Desktop boot, offline capabilities, layout and source loading")

        page.locator(".description-box summary").click()
        page.locator("#desc").fill("A cream to treat eczema")
        page.locator("#descBtn").click()
        expect(page.locator('[data-node="q_route"]')).to_have_count(3)
        choose("q_route", "non_parenteral")
        choose("q_classical_text", "no")
        choose("q_purified_fraction", "no")
        choose("q_schedule_ingredients", "yes")
        expect(page.locator("#scopeText")).to_contain_text("Patent or proprietary")
        page.locator("[data-back]").click()
        expect(page.locator('[data-node="q_schedule_ingredients"]')).to_have_count(3)
        expect(page.locator("#scopeText")).to_contain_text("Ayurveda IP & regulation")
        passed("Therapeutic description, continuation, proprietary route and edit-back")

        page.locator("#resetCls").click()
        choose("q_intended_use", "food")
        choose("q_food_claims", "no")
        choose("q_food_text", "no")
        expect(page.locator("#clsFlow")).to_contain_text("not automatically Ayurveda Aahara")
        expect(page.locator("#scopeText")).to_contain_text("Ayurveda IP & regulation")
        passed("Food eligibility uncertainty stays unclassified")

        reset()
        first = ask("What is the request-for-examination deadline for an Ayurvedic formulation patent in India now?")
        expect(page.locator("#answer .answer-text")).to_contain_text("31 months")
        expect(page.locator("#answer .answer-text")).to_contain_text("48-month")
        expect(page.locator('#answer [id$="-patents_rules_2024_rfe"]')).to_be_attached()
        first_citation = page.locator("#answer .citation-link").first.get_attribute("href")
        with page.expect_download() as download:
            page.locator("#answer [data-download]").click()
        file = artifacts / "research-brief.md"
        download.value.save_as(file)
        content = file.read_text(encoding="utf-8")
        assert "48-month" in content and "https://" in content and "Corpus version:" in content
        assert "Outcome: Sourced answer" in content and "Dated source excerpts" not in content
        assert "Research domain: Ayurveda intellectual property and regulation" in content
        assert "Answer mode: Reviewed local guidance" in content
        page.screenshot(path=str(artifacts / "answer-desktop.png"), full_page=True)
        passed("Full RFE exception, linked citation and downloadable research brief")

        followup = ask(
            "Based ONLY on the sources you retrieved for my previous question, answer directly. "
            "Create a table with: Issue | What the retrieved sources establish | Relevant section | "
            "How it applies to my case | What remains unanswered. Include every issue requested in "
            "my original question. Do not invent missing information.")
        assert followup["conversation_id"] == first["conversation_id"]
        assert followup["memory_used"] and followup["evidence_scope"] == "previous_turn"
        assert {source["id"] for source in followup["citations"]} <= {source["id"] for source in first["citations"]}
        expect(page.locator("#answer table")).to_be_visible()
        expect(page.locator("#chatHistory .history-turn")).to_have_count(1)
        expect(page.locator("#chatHistory .history-turn")).not_to_have_attribute("open", "")
        assert page.locator(first_citation).count() == 1
        assert page.evaluate("new Set([...document.querySelectorAll('[id]')].map(el => el.id)).size === document.querySelectorAll('[id]').length")
        with page.expect_download() as download:
            page.locator("#answer [data-download]").click()
        followup_file = artifacts / "followup-brief.md"
        download.value.save_as(followup_file)
        assert "Earlier questions used as chat context:" in followup_file.read_text(encoding="utf-8")
        assert not page.evaluate("[...Object.values(localStorage), ...Object.values(sessionStorage)].some(value => /examination|previous question|conversation_id/.test(value))")
        page.screenshot(path=str(artifacts / "followup-desktop.png"), full_page=True)
        passed("Same-chat source-only follow-up, Markdown table, stable citations and context export")

        with page.expect_response("**/api/chat/" + first["conversation_id"]) as cleared:
            page.locator("#newChat").click()
        assert cleared.value.status < 300
        expect(page.locator("#q")).to_have_value("")
        expect(page.locator("#chatHistory")).to_be_hidden()
        expect(page.locator("#answer")).to_contain_text("Evidence before answers")
        fresh = ask("How often must I file Form 27?")
        assert fresh["conversation_id"] != first["conversation_id"] and not fresh["memory_used"]
        page.reload(wait_until="networkidle")
        after_reload = ask("How often must I file Form 27?")
        assert after_reload["conversation_id"] != fresh["conversation_id"]
        assert not after_reload["memory_used"]
        passed("New chat deletes server memory and reload starts a fresh ephemeral conversation")

        page.locator('[data-j="International"]').click()
        expect(page.locator("#answer")).to_contain_text("Evidence before answers")
        page.locator('[data-query*="several countries"]').click()
        expect(page.locator("#answer")).to_have_attribute("aria-busy", "false")
        expect(page.locator("#answer .answer-text")).to_contain_text("does not grant a global patent")
        expect(page.locator("#chatHistory")).to_be_hidden()
        assert page.locator("#answer .jurisdiction-badge.India").count() == 0
        passed("Jurisdiction changes clear answers and international examples stay in scope")

        page.locator('[data-j="Both"]').click()
        expect(page.locator("#scopeText")).to_contain_text("India + international")
        mixed = ask("For an Ayurvedic formulation, compare regulatory approval in India, the US and the EU.")
        assert mixed["jurisdiction"] == "Both" and not mixed["abstained"]
        assert {source["jurisdiction"] for source in mixed["citations"]} == {"India", "International"}
        expect(page.locator("#answer .answer-text")).to_contain_text("United States")
        expect(page.locator("#answer .answer-text")).to_contain_text("Insufficient evidence in retrieved sources.")
        expect(page.locator("#answer .result-meta")).to_contain_text("Reviewed local guidance")
        rejected = ask("I invented an unrelated software algorithm and electronic device. Give me a complete IP strategy.")
        assert rejected["reason"] == "out_of_scope" and not rejected["citations"]
        expect(page.locator("#answer")).to_contain_text("Outside Ayurveda scope")
        expect(page.locator("#answer .handoff")).to_have_count(0)
        passed("India + international research retains jurisdictions and US gaps; unrelated technology stays outside Ayurveda scope")

        pending = []
        page.route("**/api/ask", lambda route: pending.append(route))
        page.locator("#q").fill("An intentionally delayed question")
        page.locator("#askBtn").click()
        expect(page.locator("#askBtn")).to_be_disabled()
        page.locator('[data-j="India"]').click()
        assert pending
        try:
            pending[0].fulfill(status=200, content_type="application/json", body=json.dumps({"answer":"OBSOLETE RESPONSE"}))
        except Error:
            pass
        page.unroute("**/api/ask")
        expect(page.locator("#answer")).to_contain_text("Evidence before answers")
        expect(page.locator("#askBtn")).to_be_enabled()
        assert "OBSOLETE RESPONSE" not in page.locator("#answer").inner_text()
        passed("Obsolete responses cannot overwrite a changed jurisdiction")

        page.route("**/api/ask", lambda route: route.fulfill(status=503, content_type="application/json",
                                                          body='{"detail":"Temporarily unavailable"}'))
        ask("What is Form 27?")
        expect(page.locator("#answer")).to_contain_text("Temporarily unavailable")
        expect(page.locator("#askBtn")).to_be_enabled()
        page.unroute("**/api/ask")
        page.route("**/api/classify", lambda route: route.fulfill(status=503, content_type="application/json",
                                                               body='{"detail":"Classification unavailable"}'))
        page.locator("#resetCls").click()
        expect(page.locator("#clsError")).to_contain_text("Classification unavailable")
        expect(page.locator("#descBtn")).to_be_enabled()
        page.unroute("**/api/classify")
        passed("HTTP failures are explained and controls recover")

        reset()
        before_expiry = ask("How often must I file Form 27?")
        attempted = []
        def expired(route):
            attempted.append(route.request.post_data_json)
            route.fulfill(status=410, content_type="application/json", body='{"detail":"Chat expired"}')
        page.route("**/api/ask", expired)
        ask("Based only on my previous sources, put that answer in a table.")
        assert len(attempted) == 1
        expect(page.locator("#answer")).to_contain_text("temporary memory is no longer available")
        expect(page.locator("#chatHistory .history-turn")).to_have_count(1)
        expect(page.locator("#memoryNote")).to_contain_text("expired")
        page.unroute("**/api/ask")
        page.locator("#newChat").click()
        missing_context = ask("Based only on my previous sources, put that answer in a table.")
        assert missing_context["abstained"] and not missing_context["memory_used"]
        passed("Expired or cleared source-only follow-ups cannot silently retrieve a new evidence set")

        reset()
        malicious = {
            **before_expiry,
            "answer": "# Safe heading\n\n| Issue | Evidence |\n| --- | --- |\n"
                      "| <img src=x onerror=window.injected=true> | **Quoted** [unsafe](javascript:alert(1)) |\n\n"
                      "1. <script>window.injected=true</script>\n2. [patents_rules_2024_form27]",
            "abstained": False, "notices": [], "memory_used": False, "details_expanded": True,
        }
        page.route("**/api/ask", lambda route: route.fulfill(status=200, content_type="application/json", body=json.dumps(malicious)))
        ask("Render the evidence safely")
        expect(page.locator("#answer table")).to_be_visible()
        expect(page.locator("#answer .answer-text h3")).to_have_text("Safe heading")
        expect(page.locator("#answer .answer-text ol li")).to_have_count(2)
        assert page.locator("#answer img, #answer script, #answer a[href^='javascript:']").count() == 0
        assert not page.evaluate("Boolean(window.injected)")
        expect(page.locator("#answer .answer-text")).to_contain_text("<img src=x")
        page.unroute("**/api/ask")
        passed("Markdown tables, headings and lists escape HTML and reject unsafe links")

        reset()
        scenario = ask(
            "I am planning to launch an Ayurvedic proprietary medicine in India containing Ashwagandha "
            "and three other medicinal plants. My company developed the combination, extraction technique, "
            "dosage and manufacturing process; these are not disclosed in classical Ayurvedic texts. "
            "Give me a step-by-step IP and regulatory strategy. Address classical versus proprietary under "
            "the Drugs and Cosmetics Act; patentable aspects and Patents Act exclusions; trade secrets and "
            "confidentiality before filing; trademarks; copyright; GI; plant-variety protection; other IP; "
            "Biological Diversity Act sections 3, 6 and 7, applicant status and material source; Access and "
            "Benefit Sharing, certificates and origin records; and IP India, CDSCO/AYUSH, NBA and their roles. "
            "Create a decision table with columns: Issue | Potential protection/approval | Applicable law | "
            "Eligibility/trigger | What I should do | Primary source. Distinguish established law, inference "
            "and professional confirmation; do not invent missing requirements.")
        assert not scenario["abstained"]
        expect(page.locator("#answer table th")).to_have_count(6)
        assert page.locator("#answer table tbody tr").count() >= 10
        with page.expect_download() as download:
            page.locator("#answer [data-download]").click()
        download.value.save_as(artifacts / "ayurvedic-strategy-brief.md")
        page.screenshot(path=str(artifacts / "ayurvedic-strategy-desktop.png"), full_page=True)
        scenario_followup = ask(
            "Based ONLY on the sources you retrieved for my previous question, create a table with: "
            "Issue | What the retrieved sources establish | Relevant section | How it applies to my case | "
            "What remains unanswered. Include every issue from my original question; write Insufficient "
            "evidence in retrieved sources. for missing evidence. Give a short step-by-step strategy. "
            "Separate Established by source, Inference/application, Not established by retrieved sources.")
        assert scenario_followup["memory_used"] and scenario_followup["evidence_scope"] == "previous_turn"
        expect(page.locator("#answer table th")).to_have_count(5)
        assert page.locator("#answer table tbody tr").count() >= 10
        assert {source["id"] for source in scenario_followup["citations"]} <= {source["id"] for source in scenario["citations"]}
        expect(page.locator("#answer .answer-text")).to_contain_text("Inference/application")
        with page.expect_download() as download:
            page.locator("#answer [data-download]").click()
        download.value.save_as(artifacts / "ayurvedic-followup-brief.md")
        page.locator("#answer .answer-table").screenshot(path=str(artifacts / "ayurvedic-followup-table.png"))
        passed("Full Ayurvedic strategy and prior-source-only follow-up preserve every requested issue and table format")

        reset()
        choose("q_intended_use", "medicine")
        choose("q_route", "non_parenteral")
        choose("q_classical_text", "yes")
        ask("Can a classical Ayurvedic formula be patented?")
        page.locator('[data-resource="tkdl_referral"]').click()
        expect(page.locator("#consentDialog")).to_be_visible()
        page.route("**/api/consent", lambda route: route.fulfill(status=503, content_type="application/json",
                                                              body='{"detail":"Consent could not be saved"}'))
        page.locator("#mYes").click()
        expect(page.locator("#consentError")).to_contain_text("No resource has been opened")
        assert page.locator("#consentLink").get_attribute("href") is None
        page.unroute("**/api/consent")
        page.locator("#mNo").click()
        expect(page.locator("#consentDialog")).not_to_be_visible()
        page.locator('[data-resource="tkdl_referral"]').click()
        page.locator("#mYes").click()
        expect(page.locator("#consentSuccess")).to_be_visible()
        assert page.locator("#consentLink").get_attribute("href").startswith("https://")
        assert len(context.pages) == 1
        records = [json.loads(line) for line in (log_dir / "consent_log.jsonl").read_text(encoding="utf-8").splitlines()]
        assert [record["consent"] for record in records] == [False, True]
        assert all(record["resource_id"] == "tkdl_referral" for record in records)
        page.locator("#closeConsent").click()
        passed("Consent failure, decline and acceptance do not open third-party pages")

        ask("What is the current status of Rule 170?")
        expect(page.locator("#answer")).to_contain_text("cannot confirm the current status")
        expect(page.locator("#answer .handoff")).to_be_visible()
        assert "stub" not in page.locator("#answer").inner_text()
        passed("Dated status abstention provides professional-review preparation")

        page.locator("#sourcesTab").click()
        page.locator("#sourceReview").select_option("needs_review")
        assert page.locator("#sourceList .source-card").count() >= 2
        page.locator("#sourceSearch").fill("neem")
        expect(page.locator("#sourceList .source-card")).to_have_count(1)
        page.locator("#sourceSearch").fill("")
        page.locator("#sourceReview").select_option("")
        page.locator("#sourceScope").select_option("India")
        page.locator("#sourceSearch").fill("biodiversity")
        expect(page.locator("#sourceList .source-card").first).to_be_visible()
        expect(page.locator("#sourceList")).to_contain_text("Primary source checked")
        page.screenshot(path=str(artifacts / "sources-desktop.png"), full_page=True)
        passed("Library filters expose quarantined notes and checked primary evidence")

        mobile = context.new_page()
        mobile.set_viewport_size({"width":390, "height":844})
        mobile.on("pageerror", lambda error: errors.append(str(error)))
        mobile.goto(url, wait_until="networkidle")
        expect(mobile.locator('[data-option="medicine"]')).to_be_visible()
        assert not mobile.evaluate("document.documentElement.scrollWidth > innerWidth")
        mobile.screenshot(path=str(artifacts / "advisor-mobile.png"), full_page=True)
        mobile.locator("#q").fill("How often must I file Form 27?")
        mobile.locator("#askBtn").click()
        expect(mobile.locator("#answer")).to_have_attribute("aria-busy", "false")
        expect(mobile.locator("#answer .answer-text")).to_contain_text("three financial years")
        mobile.locator("#q").fill("Based only on my previous sources, create a table of the issue, section and what I should do.")
        mobile.locator("#askBtn").click()
        expect(mobile.locator("#answer")).to_have_attribute("aria-busy", "false")
        expect(mobile.locator("#answer table")).to_be_visible()
        assert not mobile.evaluate("document.documentElement.scrollWidth > innerWidth")
        mobile.screenshot(path=str(artifacts / "followup-mobile.png"), full_page=True)
        passed("Mobile answers and scrollable tables do not overflow the page")

        assert not errors, errors
        audit = (log_dir / "audit_log.jsonl").read_text(encoding="utf-8")
        assert all(question not in audit for question in submitted_questions)
        passed("No uncaught browser errors or question text in test audit logs")
        browser.close()

    report = {"passed":len(checks), "checks":checks, "corpus_version":corpus_version,
              "note":"Isolated offline server; temporary logs; no third-party referral pages opened."}
    (artifacts / "browser-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Browser checks: {len(checks)}/{len(checks)} passed", flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=ROOT / "docs" / "qa")
    args = parser.parse_args()
    run(args.artifacts)
