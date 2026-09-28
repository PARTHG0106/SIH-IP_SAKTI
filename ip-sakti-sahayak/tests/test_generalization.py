"""Reported questions and counterexamples: facts must change the answer."""
import copy
import json
import os
from pathlib import Path
import re
import unittest
from unittest.mock import patch

os.environ["LLM_PROVIDER"] = "none"
from backend import generation, rag
from backend.models import AskRequest
from backend.pipeline import Assistant
from backend.planning import plan_query
from backend.retrieval import Retriever
from backend.router import RegistryRouter
from tests.test_conversation import ORIGINAL

QUESTIONS = json.loads((Path(__file__).parent / "fixtures/reported_questions.json").read_text(encoding="utf-8"))


class ReportedQuestionTests(unittest.TestCase):
    def setUp(self):
        self.retriever = Retriever(mode="bm25")
        self.engine = Assistant(self.retriever, RegistryRouter())
        self.chat = self.engine.memory.create()

    def ask(self, query, **kwargs):
        return self.engine.answer(AskRequest(query=query, conversation_id=self.chat, **kwargs), use_llm=False)

    def test_technology_case_is_rejected_before_retrieval_in_existing_chat(self):
        self.ask(ORIGINAL)
        with patch.object(self.retriever, "search", side_effect=AssertionError("Unrelated case must not retrieve")):
            answer = self.ask(QUESTIONS["4"])
        self.assertEqual(answer.reason, "out_of_scope")
        self.assertFalse(answer.citations)
        self.assertNotIn("extraction", answer.answer)

    def test_five_plant_case_keeps_case_facts_and_export_gaps(self):
        self.ask(ORIGINAL)
        answer = self.ask(QUESTIONS["5"])
        self.assertFalse(answer.abstained)
        self.assertFalse(answer.memory_used)
        self.assertNotIn("Ashwagandha", answer.answer)
        self.assertNotIn("does not meet that classical-formula test on the facts stated", answer.answer)
        self.assertIn("wild", answer.answer.lower())
        self.assertIn("cultivated", answer.answer.lower())
        self.assertIn("United States", answer.answer)
        self.assertIn("Insufficient evidence in retrieved sources.", answer.answer)
        ids = {c.id for c in answer.citations}
        self.assertIn("eu_thmpd", ids)
        self.assertNotIn("gi_act", ids)
        self.assertNotIn("ppvfr_act", ids)
        self.assertIn("bda_s6", ids)
        self.assertIn("bda_s7_exemption", ids)
        self.assertIn("bda_sourcing", ids)
        self.assertTrue({"India", "International"} <= {c.jurisdiction for c in answer.citations})

    def test_original_source_only_success_is_preserved(self):
        first = self.ask(ORIGINAL)
        with patch.object(self.retriever, "search", side_effect=AssertionError("No new retrieval")):
            followup = self.ask(QUESTIONS["3"])
        self.assertFalse(followup.abstained)
        self.assertIn("| Issue |", followup.answer)
        self.assertEqual(followup.evidence_scope, "previous_turn")
        self.assertTrue({c.id for c in followup.citations} <= {c.id for c in first.citations})

    def test_mixed_scope_snapshot_keeps_foreign_evidence_without_new_retrieval(self):
        first = self.ask(QUESTIONS["5"])
        with patch.object(self.retriever, "search", side_effect=AssertionError("No new retrieval")):
            followup = self.ask("Use only the previous sources and make a table covering every issue in my original question.")
        self.assertIn("eu_thmpd", {c.id for c in followup.citations})
        self.assertTrue({c.id for c in followup.citations} <= {c.id for c in first.citations})

    def test_correction_changes_classical_application(self):
        first = self.ask("My Ayurvedic formula is not included in the classical authoritative books. Is it classical or proprietary?")
        corrected = self.ask("Correction: the complete formula and manufacture exactly match a First-Schedule formula. Is this classical or proprietary?")
        self.assertNotEqual(first.answer, corrected.answer)
        self.assertNotIn("does not meet that classical-formula test on the facts stated", corrected.answer)

    def test_us_pronoun_does_not_trigger_foreign_jurisdiction(self):
        answer = self.ask("Our Ayurvedic medicine was developed by us. Explain the patent strategy in India.")
        self.assertTrue(all(c.jurisdiction == "India" for c in answer.citations))
        self.assertNotIn("United States", answer.answer)

    def test_both_scope_retrieves_only_requested_legal_topics(self):
        answer = self.ask("Compare Indian patent protection and the PCT route for an Ayurvedic extraction process.", jurisdiction="Both")
        self.assertFalse(answer.abstained)
        self.assertIn("pct", {c.id for c in answer.citations})
        self.assertIn("patents_invention", {c.id for c in answer.citations})


class SynthesisTests(unittest.TestCase):
    def setUp(self):
        self.retriever = Retriever(mode="bm25")
        self.query = "How often must I file Form 27 for my Ayurvedic process patent?"
        self.plan = plan_query(self.query)
        self.hits, self.confidence = self.retriever.search(self.query, jurisdiction="India", plan=self.plan)
        self.doc = self.retriever.corpus.by_id["patents_rules_2024_form27"]
        self.value = {"sections": [{"issue": self.plan.issues[0].title,
            "established": [{"text": "In India, Rule 131 requires a Form 27 statement for periods of three financial years.",
                             "source_id": self.doc["id"], "quote": self.doc["text"]}],
            "application": [{"text": "Assess the three-year reporting period for the Ayurvedic process patent you describe.",
                             "source_ids": [self.doc["id"]], "fact_quotes": ["my Ayurvedic process patent"]}],
            "unanswered": ["What is the patent grant date?"]}], "questions": [], "steps": []}

    def generate(self, value=None, approved=True):
        with patch("backend.llm.available", return_value=True), patch("backend.llm.chat", side_effect=[json.dumps(value or self.value), json.dumps({"supported": approved})]):
            return generation.generate(self.query, self.hits, self.confidence, "India", plan=self.plan)

    def test_checked_rag_produces_question_specific_application(self):
        answer = self.generate()
        self.assertEqual(answer["answer_source"], "rag_synthesis")
        self.assertIn("Ayurvedic process patent you describe", answer["answer"])
        self.assertEqual([h["doc"]["id"] for h in answer["citations_used"]], [self.doc["id"]])
        self.assertIn(self.doc["section"], answer["answer"])

    def test_valid_citation_with_unsupported_claim_falls_back(self):
        value = copy.deepcopy(self.value)
        value["sections"][0]["established"][0]["text"] = "Rule 131 guarantees a patent to every Ayurveda company."
        answer = self.generate(value, approved=False)
        self.assertEqual(answer["answer_source"], "grounded_synthesis")
        self.assertNotIn("guarantees", answer["answer"])

    def test_fabricated_quote_or_fact_or_source_cannot_reach_answer(self):
        for field in ("quote", "fact", "source"):
            value = copy.deepcopy(self.value)
            if field == "quote":
                value["sections"][0]["established"][0]["quote"] = "Fabricated evidence that is not in the source."
            elif field == "source":
                value["sections"][0]["established"][0]["source_id"] = "invented"
            else:
                value["sections"][0]["application"][0]["fact_quotes"] = ["The patent was granted in 2025."]
            with self.subTest(field=field):
                self.assertEqual(self.generate(value)["answer_source"], "grounded_synthesis")

    def test_missing_requested_issue_is_rejected(self):
        value = copy.deepcopy(self.value)
        value["sections"] = []
        self.assertEqual(self.generate(value)["answer_source"], "grounded_synthesis")

    def test_superseded_fact_from_raw_history_is_not_valid_model_evidence(self):
        value = copy.deepcopy(self.value)
        obsolete = "The plants are cultivated."
        value["sections"][0]["application"][0]["fact_quotes"] = [obsolete]
        with patch("backend.llm.available", return_value=True), patch("backend.llm.chat", return_value=json.dumps(value)):
            answer = generation.generate(self.query, self.hits, self.confidence, "India",
                                         plan=self.plan, context_query=obsolete)
        self.assertEqual(answer["answer_source"], "grounded_synthesis")

    def test_malformed_numeric_audit_verdict_is_not_approval(self):
        with patch("backend.llm.available", return_value=True), patch("backend.llm.chat", side_effect=[json.dumps(self.value), '{"supported":1}']):
            answer = generation.generate(self.query, self.hits, self.confidence, "India", plan=self.plan)
        self.assertEqual(answer["answer_source"], "grounded_synthesis")

    def test_offline_path_never_calls_provider(self):
        with patch("backend.llm.chat", side_effect=AssertionError("Offline must not call model")):
            answer = generation.generate(self.query, self.hits, self.confidence, "India", use_llm=False)
        self.assertFalse(answer["abstained"])


if __name__ == "__main__":
    unittest.main()
