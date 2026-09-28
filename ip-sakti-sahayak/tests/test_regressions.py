"""Safety and behaviour regressions for the dossier-driven implementation."""
import copy
import hashlib
import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

# Tests must not discover adjacent provider credentials or download models.
os.environ["LLM_PROVIDER"] = "none"
os.environ["RETRIEVER"] = "bm25"

from fastapi.testclient import TestClient
from backend import consent, generation, i18n, llm
from backend.classifier import Classifier, heuristic_answer
from backend.config import Settings, settings, _load_provider_file
from backend.main import app, assistant, retriever, router
from backend.models import AskRequest
from backend.retrieval import Corpus, Retriever
from backend.sources import validate_source

MEDICINE = {"q_intended_use": "medicine", "q_route": "non_parenteral"}
NONCLASSICAL = {**MEDICINE, "q_classical_text": "no"}
WHOLE = {**NONCLASSICAL, "q_purified_fraction": "no"}


class ClassificationTests(unittest.TestCase):
    def setUp(self):
        self.classifier = Classifier()

    def test_six_confirmed_routes(self):
        paths = {
            "classical": {**MEDICINE, "q_classical_text": "yes"},
            "phytopharmaceutical": {**NONCLASSICAL, "q_purified_fraction": "yes"},
            "proprietary": {**WHOLE, "q_schedule_ingredients": "yes"},
            "new_drug": {**WHOLE, "q_schedule_ingredients": "no", "q_new_drug": "yes"},
            "ayurveda_aahar": {"q_intended_use": "food", "q_food_claims": "no", "q_food_text": "yes"},
            "cosmetic": {"q_intended_use": "cosmetic", "q_cosmetic_use": "yes"},
        }
        for category, answers in paths.items():
            with self.subTest(category=category):
                result = self.classifier.classify(answers)
                self.assertTrue(result["complete"])
                self.assertEqual(result["category"], category)
                self.assertEqual(result["answers"], answers)

    def test_new_drug_is_explicitly_provisional(self):
        result = self.classifier.classify({**WHOLE, "q_schedule_ingredients": "no", "q_new_drug": "yes"})
        self.assertTrue(result["needs_review"])

    def test_therapeutic_cream_is_not_automatically_cosmetic(self):
        result = self.classifier.classify({}, "A cream to treat eczema")
        self.assertFalse(result["complete"])
        self.assertEqual(result["answers"]["q_intended_use"], "medicine")
        self.assertEqual(result["next_question"]["node"], "q_route")

    def test_negation_never_confirms_statutory_tests(self):
        for node, text in [
            ("q_classical_text", "not classical, my own recipe"),
            ("q_purified_fraction", "not purified, whole herbs"),
            ("q_purified_fraction", "standardised extract with two compounds"),
            ("q_schedule_ingredients", "not all ingredients are in the First Schedule"),
        ]:
            with self.subTest(text=text):
                self.assertIsNone(heuristic_answer(node, text))

    def test_free_text_does_not_infer_legal_eligibility(self):
        result = self.classifier.classify({}, "A classical churna made exactly as in Charaka Samhita")
        self.assertFalse(result["complete"])
        self.assertEqual(result["next_question"]["node"], "q_route")

    def test_continuation_preserves_inferred_intended_use(self):
        result = self.classifier.classify({}, "A herbal medicine")
        answers = {**result["answers"], "q_route": "non_parenteral"}
        result = self.classifier.classify(answers)
        self.assertEqual(result["next_question"]["node"], "q_classical_text")

    def test_food_requires_claim_and_schedule_checks(self):
        result = self.classifier.classify({"q_intended_use": "food"})
        self.assertFalse(result["complete"])
        self.assertEqual(result["next_question"]["node"], "q_food_claims")
        result = self.classifier.classify({"q_intended_use": "food", "q_food_claims": "no"})
        self.assertEqual(result["next_question"]["node"], "q_food_text")

    def test_food_with_disease_claim_enters_medicine_checks(self):
        result = self.classifier.classify({"q_intended_use": "food", "q_food_claims": "yes"})
        self.assertEqual(result["next_question"]["node"], "q_route")

    def test_generic_supplement_does_not_become_ayurveda_aahara(self):
        result = self.classifier.classify({"q_intended_use": "food", "q_food_claims": "no", "q_food_text": "no"})
        self.assertTrue(result["needs_review"])
        self.assertIsNone(result["category"])

    def test_parenteral_route_needs_review(self):
        result = self.classifier.classify({"q_intended_use": "medicine", "q_route": "parenteral"})
        self.assertTrue(result["needs_review"])
        self.assertIsNone(result["category"])

    def test_uncertain_facts_stop_classification(self):
        result = self.classifier.classify({**NONCLASSICAL, "q_purified_fraction": "unsure"})
        self.assertTrue(result["needs_review"])
        self.assertFalse(result["complete"])

    def test_revised_answer_discards_obsolete_branch(self):
        result = self.classifier.classify({**MEDICINE, "q_classical_text": "yes",
                                           "q_schedule_ingredients": "yes"})
        self.assertNotIn("q_schedule_ingredients", result["answers"])

    def test_all_configured_statutes_exist(self):
        for record in [*self.classifier.nodes.values(), *self.classifier.categories.values()]:
            self.assertTrue(set(record.get("statutes", [])) <= set(retriever.corpus.by_id))


class RetrievalTests(unittest.TestCase):
    def test_no_zero_score_evidence_or_stopword_matches(self):
        for query in ("the and of what", "quuxxyz zxqxyz"):
            self.assertEqual(retriever.search(query, jurisdiction="India"), ([], 0.0))

    def test_jurisdictions_are_strict_even_for_reference_sources(self):
        for jurisdiction in ("India", "International"):
            hits, _ = retriever.search("legal AI hallucination patent", jurisdiction=jurisdiction)
            self.assertTrue(all(h["doc"]["jurisdiction"] == jurisdiction for h in hits))

    def test_exact_section_queries_distinguish_exclusions(self):
        hits, _ = retriever.search("section 3(p)", jurisdiction="India")
        self.assertEqual(hits[0]["doc"]["id"], "patents_3p")

    def test_classical_category_does_not_hide_brand_protection(self):
        hits, _ = retriever.search("international trademark brand Madrid", jurisdiction="International", category="classical")
        self.assertEqual(hits[0]["doc"]["id"], "madrid")

    def test_minimum_source_metadata(self):
        for source in retriever.corpus.docs:
            self.assertEqual(validate_source(source), source)

    def test_duplicate_sources_fail_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "corpus.jsonl"
            line = json.dumps(retriever.corpus.docs[0]) + "\n"
            path.write_text(line + line, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate source"):
                Corpus(path)

    def test_invalid_url_and_scope_fail_validation(self):
        for key, value in [("source_url", "javascript:alert(1)"), ("jurisdiction", "Everywhere"), ("as_of", "yesterday")]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_source({**retriever.corpus.docs[0], key: value})

    def test_manifest_version_changes_with_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "corpus.jsonl"
            source = copy.deepcopy(retriever.corpus.docs[0])
            path.write_text(json.dumps(source) + "\n", encoding="utf-8")
            first = Corpus(path).version
            source["text"] += " Additional note."
            path.write_text(json.dumps(source) + "\n", encoding="utf-8")
            self.assertNotEqual(first, Corpus(path).version)

    def test_saved_primary_document_matches_provenance_hash(self):
        root = Path(__file__).resolve().parent.parent / "corpus" / "primary"
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        for document in manifest["documents"]:
            self.assertEqual(hashlib.sha256((root / document["file"]).read_bytes()).hexdigest(), document["sha256"])

    def test_primary_check_requires_a_date(self):
        doc = {**retriever.corpus.docs[0], "review_status": "primary_checked", "reviewed_on": None}
        with self.assertRaisesRegex(ValueError, "review date"):
            validate_source(doc)


class GroundingTests(unittest.TestCase):
    def answer(self, query, jurisdiction="India", **kwargs):
        return assistant.answer(AskRequest(query=query, jurisdiction=jurisdiction), use_llm=False, **kwargs)

    def test_rfe_answer_retains_transition_exception(self):
        answer = self.answer("What is the request-for-examination deadline for a patent in India?")
        self.assertFalse(answer.abstained)
        self.assertIn("31 months", answer.answer)
        self.assertIn("48-month", answer.answer)

    def test_form27_answer_is_not_padded_with_new_salt_law(self):
        answer = self.answer("How often must I file Form 27?")
        self.assertEqual([c.id for c in answer.citations], ["patents_rules_2024_form27"])
        self.assertIn("three financial years", answer.answer)
        self.assertIn("licensing", answer.answer)

    def test_rule170_full_history_keeps_later_court_decision(self):
        answer = self.answer("What happened to Rule 170 on 11 August 2025?")
        self.assertFalse(answer.abstained)
        self.assertIn("VACATED", answer.answer)
        self.assertIn("DMR Act", answer.answer)

    def test_live_status_is_not_invented_from_dated_record(self):
        for query, jurisdiction in [
            ("What is the current status of Rule 170?", "India"),
            ("Is WIPO GRATK in force yet?", "International"),
            ("How many patent offices can use TKDL now?", "India"),
        ]:
            with self.subTest(query=query):
                answer = self.answer(query, jurisdiction)
                self.assertTrue(answer.abstained)
                self.assertEqual(answer.reason, "current_status_unverified")
                self.assertTrue(answer.citations)

    def test_quarantined_legal_notes_are_not_presented_as_answers(self):
        answer = self.answer("What happened to the neem patent at the EPO?", "International")
        self.assertTrue(answer.abstained)
        self.assertEqual(answer.reason, "source_review_required")
        self.assertEqual(answer.citations[0].snippet, "")

    def test_biodiversity_ip_duties_distinguish_applicant_categories(self):
        answer = self.answer("Do I need NBA approval before filing a patent based on an Indian plant?")
        self.assertFalse(answer.abstained)
        self.assertIn("6(1A)", answer.answer)
        self.assertIn("registration", answer.answer)
        self.assertIn("commercialisation", answer.answer)
        self.assertEqual(answer.citations[0].review_status, "primary_checked")

    def test_cultivated_plant_exemption_retains_certificate_condition(self):
        answer = self.answer("Are cultivated medicinal plants exempt from section 7 SBB intimation?")
        self.assertFalse(answer.abstained)
        self.assertIn("certificate of origin", answer.answer)
        self.assertIn("Biodiversity Management Committee", answer.answer)

    def test_cross_jurisdiction_query_gives_actionable_switch(self):
        answer = self.answer("Is the WIPO GRATK treaty in force?")
        self.assertTrue(answer.abstained)
        self.assertEqual(answer.reason, "jurisdiction_mismatch")
        self.assertFalse(answer.citations)

    def test_insufficient_and_personal_advice_queries_abstain(self):
        for query in ["What are tomorrow's lottery numbers?", "Should I sue my business partner?", "What dose should I take?", "What is the GST rate on stainless steel this year?"]:
            self.assertTrue(self.answer(query).abstained)

    def test_legitimate_information_question_is_not_advice_blocked(self):
        answer = self.answer("Does PCT guarantee a global patent?", "International")
        self.assertFalse(answer.abstained)
        self.assertIn("does not grant a global patent", answer.answer)

    def test_invalid_model_prose_cannot_smuggle_claims_with_valid_id(self):
        hits, confidence = retriever.search("What is Form 27?", jurisdiction="India")
        with patch("backend.llm.available", return_value=True), patch("backend.llm.chat", return_value="You are guaranteed a patent. [patents_rules_2024_form27] All ads are legal. [invented]"):
            answer = generation.generate("What is Form 27?", hits, confidence, "India")
        self.assertEqual(answer["answer_source"], "grounded_synthesis")
        self.assertNotIn("guaranteed", answer["answer"])

    def test_mixed_real_and_fabricated_selection_is_rejected_entirely(self):
        hits, confidence = retriever.search("What is Form 27?", jurisdiction="India")
        with patch("backend.llm.available", return_value=True), patch("backend.llm.chat", return_value='{"source_ids":["patents_rules_2024_form27","invented"]}'):
            answer = generation.generate("What is Form 27?", hits, confidence, "India")
        self.assertEqual(answer["answer_source"], "grounded_synthesis")

    def test_legacy_source_selection_is_not_treated_as_synthesis(self):
        hits, confidence = retriever.search("What is Form 27?", jurisdiction="India")
        with patch("backend.llm.available", return_value=True), patch("backend.llm.chat", return_value='{"source_ids":["patents_rules_2024_form27"]}'):
            answer = generation.generate("What is Form 27?", hits, confidence, "India")
        self.assertEqual(answer["answer_source"], "grounded_synthesis")
        self.assertIn("three financial years", answer["answer"])
        self.assertIn("Established by source", answer["answer"])
        self.assertIn("[patents_rules_2024_form27]", answer["answer"])
        self.assertNotEqual(answer["answer"], retriever.corpus.by_id["patents_rules_2024_form27"]["text"] + " [patents_rules_2024_form27]")

    def test_modified_source_cannot_reuse_a_reviewed_claim_by_id(self):
        hits, confidence = retriever.search("What is Form 27?", jurisdiction="India")
        hits = copy.deepcopy(hits)
        for hit in hits:
            if hit["doc"]["id"] == "patents_rules_2024_form27":
                hit["doc"]["text"] = "This source no longer supports any statement about Form 27."
        answer = generation.generate("What is Form 27?", hits, confidence, "India", use_llm=False)
        self.assertTrue(answer["abstained"])
        self.assertNotIn("three financial years", answer["answer"])

    def test_invalid_model_response_falls_back_to_reviewed_evidence(self):
        hits, confidence = retriever.search("What is Form 27?", jurisdiction="India")
        with patch("backend.llm.available", return_value=True), patch("backend.llm.chat", return_value="INSUFFICIENT"):
            answer = generation.generate("What is Form 27?", hits, confidence, "India")
        self.assertFalse(answer["abstained"])
        self.assertEqual(answer["answer_source"], "grounded_synthesis")

    def test_provider_failure_falls_back_to_complete_evidence(self):
        hits, confidence = retriever.search("What is Form 27?", jurisdiction="India")
        with patch("backend.llm.available", return_value=True), patch("backend.llm.chat", side_effect=llm.LLMError("unavailable")):
            answer = generation.generate("What is Form 27?", hits, confidence, "India")
        self.assertFalse(answer["abstained"])
        self.assertIn("available for licensing", answer["answer"])

    def test_minimum_citations_is_enforced(self):
        hits, confidence = retriever.search("What is Form 27?", jurisdiction="India")
        with patch.object(settings, "min_citations", 2):
            answer = generation.generate("What is Form 27?", hits[:1], confidence, "India", use_llm=False)
        self.assertTrue(answer["abstained"])

    def test_overall_date_is_oldest_source_not_newest(self):
        docs = [copy.deepcopy(retriever.corpus.by_id[i]) for i in ("patents_3p", "patents_3e")]
        docs[0]["as_of"], docs[1]["as_of"] = "2005-01-01", "2024-03-15"
        hits = [{"doc": d, "score": 1, "bm25": 1} for d in docs]
        answer = generation.generate("patent exclusions", hits, 0.9, "India", use_llm=False)
        self.assertEqual(answer["as_of"], "2005-01-01")

    def test_generation_filters_foreign_citations_defensively(self):
        hits, _ = retriever.search("PCT", jurisdiction="International")
        self.assertTrue(generation.generate("PCT", hits, 1.0, "India", use_llm=False)["abstained"])


class TranslationAndConfigTests(unittest.TestCase):
    def test_offline_language_failure_is_explicit_and_returns_actual_language(self):
        answer = assistant.answer(AskRequest(query="mujhe apne brand ka naam surakshit karna hai", lang="hi"), use_llm=False)
        self.assertTrue(answer.abstained)
        self.assertEqual((answer.lang, answer.requested_lang), ("en", "hi"))
        self.assertEqual(answer.reason, "translation_unavailable")

    def test_translation_cannot_drop_or_invent_citation_markers(self):
        for output in ("translated without marker", "translated [made_up]"):
            with self.subTest(output=output), patch("backend.i18n.available", return_value=True), patch("backend.llm.chat", return_value=output):
                text, translated = i18n.from_english("Source [patents_3p]", "hi")
                self.assertFalse(translated)
                self.assertEqual(text, "Source [patents_3p]")

    def test_translation_preserves_all_citation_occurrences(self):
        with patch("backend.i18n.available", return_value=True), patch("backend.llm.chat", return_value="translation [patents_3p]"):
            self.assertFalse(i18n.from_english("One [patents_3p]. Two [patents_3p]", "hi")[1])

    def test_explicit_offline_setting_cannot_be_overridden_by_provider_file(self):
        config = Settings(llm_provider="none", llm_model="test")
        with patch.dict(os.environ, {"ALLOW_PROVIDER_FILE":"true"}), patch("pathlib.Path.read_text") as read:
            _load_provider_file(config)
        read.assert_not_called()
        self.assertFalse(config.llm_enabled)

    def test_provider_file_is_not_read_without_explicit_optin(self):
        config = Settings(llm_provider="anthropic", llm_model="test")
        with patch.dict(os.environ, {"ALLOW_PROVIDER_FILE":"false"}), patch("pathlib.Path.read_text") as read:
            _load_provider_file(config)
        read.assert_not_called()

    def test_compatible_base_urls_do_not_duplicate_v1(self):
        self.assertEqual(llm._endpoint("https://example.test/v1/", "/v1/chat/completions"), "https://example.test/v1/chat/completions")
        self.assertEqual(llm._endpoint("https://example.test", "/v1/messages"), "https://example.test/v1/messages")


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.audit = patch.object(settings, "audit_log_path", self.root / "audit.jsonl")
        self.consent = patch.object(settings, "consent_log_path", self.root / "consent.jsonl")
        self.audit.start()
        self.consent.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.consent.stop()
        self.audit.stop()
        self.temp.cleanup()

    def test_health_and_manifest_report_actual_capabilities(self):
        health = self.client.get("/api/health").json()
        self.assertFalse(health["llm_enabled"])
        self.assertFalse(health["translation_available"])
        self.assertEqual(len(health["languages"]), 23)
        manifest = self.client.get("/api/sources").json()
        self.assertEqual(manifest["version"], health["corpus_version"])
        self.assertEqual(manifest["needs_review"], 2)
        self.assertEqual(len(manifest["sources"]), health["corpus_size"])
        self.assertGreaterEqual(len(manifest["sources"]), 36)

    def test_request_validation_rejects_empty_unknown_and_oversized_inputs(self):
        invalid = [
            {"query":"   "}, {"query":"x" * 4001}, {"query":"patents", "jurisdiction":"US"},
            {"query":"patents", "category":"unknown"}, {"query":"patents", "regime":"any"},
            {"query":"patents", "lang":"zz"}, {"query":"patents", "unexpected": True},
        ]
        for body in invalid:
            with self.subTest(body=str(body)[:70]):
                self.assertEqual(self.client.post("/api/ask", json=body).status_code, 422)

    def test_invalid_classification_answers_are_explained(self):
        for answers in ({"q_no_such_node":"yes"}, {"q_intended_use":"garbage"}):
            self.assertEqual(self.client.post("/api/classify", json={"answers": answers}).status_code, 422)

    def test_query_text_is_not_saved_in_audit(self):
        private = "Can I patent my confidential product FormulaSecret123?"
        response = self.client.post("/api/ask", json={"query":private})
        self.assertEqual(response.status_code, 200)
        stored = (self.root / "audit.jsonl").read_text(encoding="utf-8")
        self.assertNotIn(private, stored)
        self.assertNotIn("FormulaSecret123", stored)
        record = json.loads(stored)
        self.assertNotIn("query", record)
        self.assertEqual(record["query_chars"], len(private))
        self.assertEqual(record["request_id"], response.json()["request_id"])

    def test_consent_uses_canonical_registry_identity(self):
        response = self.client.post("/api/consent", json={
            "user_id":"session-test", "resource_id":"tkdl_referral",
            "resource_name":"A forged name", "consent":True})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["url"], router.get("tkdl_referral")["url"])
        self.assertEqual(data["record"]["resource_name"], router.get("tkdl_referral")["name"])

    def test_invalid_and_free_resources_cannot_create_consent_records(self):
        for resource_id, code in (("made_up",404), ("inpass",400)):
            response = self.client.post("/api/consent", json={"user_id":"s", "resource_id":resource_id, "consent":True})
            self.assertEqual(response.status_code, code)
        self.assertFalse((self.root / "consent.jsonl").exists())

    def test_string_false_is_not_accepted_as_consent(self):
        response = self.client.post("/api/consent", json={"user_id":"s", "resource_id":"tkdl_referral", "consent":"false"})
        self.assertEqual(response.status_code, 422)

    def test_declined_consent_does_not_release_url(self):
        response = self.client.post("/api/consent", json={"user_id":"s", "resource_id":"tkdl_referral", "consent":False})
        self.assertIsNone(response.json()["url"])

    def test_consent_write_failure_never_releases_destination(self):
        with patch("backend.consent.log_consent", side_effect=OSError("disk unavailable")):
            response = self.client.post("/api/consent", json={"user_id":"s", "resource_id":"tkdl_referral", "consent":True})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("url", response.json())

    def test_audit_failure_is_visible_without_losing_answer(self):
        with patch("backend.consent.log_query", side_effect=OSError("disk unavailable")), self.assertLogs("backend.main", level="WARNING"):
            response = self.client.post("/api/ask", json={"query":"What is Form 27?"}).json()
        self.assertFalse(response["abstained"])
        self.assertIn("Audit metadata could not be saved", " ".join(response["notices"]))

    def test_resources_respect_regulator_and_consent_boundary(self):
        links = router.route("India", {"drug"}, "phytopharmaceutical")
        self.assertIn("cdsco", [r["id"] for r in links])
        self.assertNotIn("e_aushadhi", [r["id"] for r in links])
        links = router.route("India", {"drug"}, "proprietary")
        self.assertIn("e_aushadhi", [r["id"] for r in links])
        self.assertNotIn("cdsco", [r["id"] for r in links])
        gated = next(r for r in links if r["id"] == "tkdl_referral")
        self.assertIsNone(gated["url"])

    def test_consent_revocation_and_corrupt_line_handling(self):
        consent.log_consent("s","tkdl_referral","TKDL",True)
        with open(settings.consent_log_path, "a", encoding="utf-8") as stream:
            stream.write("broken json\n")
        consent.log_consent("s","tkdl_referral","TKDL",False)
        self.assertFalse(consent.has_consent("s","tkdl_referral"))

    def test_concurrent_metadata_writes_remain_parseable(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda i: consent.log_query("private", "India", "en", 0.5, False, [], "extractive", request_id=str(i)), range(20)))
        records = [json.loads(line) for line in settings.audit_log_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(records), 20)
        self.assertEqual(len({r["request_id"] for r in records}), 20)

    def test_frontend_assets_and_privacy_headers(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn('script-src \'self\'', response.headers["content-security-policy"])
        self.assertEqual(self.client.get("/assets/app.js").status_code, 200)
        self.assertEqual(self.client.get("/assets/styles.css").status_code, 200)
        self.assertEqual(self.client.get("/api/health").headers["cache-control"], "no-store")


if __name__ == "__main__":
    unittest.main()
