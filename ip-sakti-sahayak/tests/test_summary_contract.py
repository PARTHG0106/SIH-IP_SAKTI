"""Summary, evidence and translation contracts across the answer pipeline."""
from copy import deepcopy
from dataclasses import replace
import json
import os
import re
import unittest
from unittest.mock import patch

os.environ["LLM_PROVIDER"] = "none"
os.environ["ALLOW_PROVIDER_FILE"] = "false"

from backend import generation
from backend.models import AskRequest
from backend.pipeline import Assistant
from backend.planning import plan_query
from backend.retrieval import Retriever
from backend.router import RegistryRouter


class SummaryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.retriever = Retriever(mode="bm25")

    def setUp(self):
        self.engine = Assistant(self.retriever, RegistryRouter())
        self.query = "How often must I file Form 27 for my Ayurvedic process patent?"
        self.plan = plan_query(self.query, use_llm=False)
        self.hits, self.confidence = self.retriever.search(
            self.query, jurisdiction="India", plan=self.plan)
        self.doc = self.retriever.corpus.by_id["patents_rules_2024_form27"]
        self.summary_text = ("In India, Form 27 is filed for periods of three financial years; "
                             "the grant date determines the reporting period.")
        self.value = {
            "summary": [{"text": self.summary_text,
                         "source_ids": [self.doc["id"]], "fact_quotes": []}],
            "sections": [{
                "issue": self.plan.issues[0].title,
                "established": [{
                    "text": "In India, Rule 131 requires a Form 27 statement for periods of three financial years.",
                    "source_id": self.doc["id"], "quote": self.doc["text"]}],
                "application": [{
                    "text": "Assess the three-year reporting period for the Ayurvedic process patent you describe.",
                    "source_ids": [self.doc["id"]],
                    "fact_quotes": ["my Ayurvedic process patent"]}],
                "unanswered": ["What is the patent grant date?"],
            }],
            "questions": [], "steps": [],
        }

    def ask_model(self, value=None, *, audit=True, plan=None):
        output = self.value if value is None else value
        with patch("backend.pipeline.plan_query", return_value=plan or self.plan), \
                patch("backend.llm.available", return_value=True), \
                patch("backend.llm.chat", side_effect=[
                    json.dumps(output), json.dumps({"supported": audit})]) as chat:
            response = self.engine.answer(AskRequest(query=self.query))
        return response, chat

    def assert_grounded_fallback(self, response, rejected_text):
        self.assertFalse(response.abstained)
        self.assertEqual(response.answer_source, "grounded_synthesis")
        self.assertTrue(response.summary)
        self.assertNotIn(rejected_text, response.summary)
        self.assertNotIn(rejected_text, response.answer)
        markers = set(re.findall(r"\[([a-z0-9_]+)\]", response.summary))
        self.assertTrue(markers <= {c.id for c in response.citations})

    def test_accepted_model_summary_reaches_response_with_source_and_detail(self):
        response, chat = self.ask_model()
        self.assertEqual(response.answer_source, "rag_synthesis")
        self.assertEqual(response.summary, self.summary_text + " [" + self.doc["id"] + "]")
        self.assertIn("Ayurvedic process patent you describe", response.answer)
        self.assertIn("What is the patent grant date?", response.answer)
        self.assertEqual({c.id for c in response.citations}, {self.doc["id"]})
        self.assertFalse(response.details_expanded)
        self.assertIsNone(response.original_summary_en)
        audit = json.loads(chat.call_args_list[1].args[1])
        self.assertEqual(audit["proposed_answer"]["summary"], self.value["summary"])
        # These fields must survive the same serialization used by the API.
        serialized = response.model_dump()
        self.assertEqual(serialized["summary"], response.summary)
        self.assertFalse(serialized["details_expanded"])

    def test_invalid_summary_structure_or_evidence_falls_back_before_audit(self):
        variants = {}
        empty = deepcopy(self.value)
        empty["summary"] = []
        variants["empty"] = empty
        oversized = deepcopy(self.value)
        oversized["summary"][0]["text"] = "Unchecked summary. " * 91
        variants["over_word_budget"] = oversized
        unknown = deepcopy(self.value)
        unknown["summary"][0].update(text="Unchecked summary.", source_ids=["invented_source"])
        variants["unknown_source"] = unknown
        invented_fact = deepcopy(self.value)
        invented_fact["summary"][0].update(
            text="Unchecked summary.", fact_quotes=["The patent was granted in 2025."])
        variants["invented_fact"] = invented_fact
        for label, value in variants.items():
            with self.subTest(label=label):
                response, chat = self.ask_model(value)
                self.assert_grounded_fallback(response, "Unchecked summary")
                self.assertEqual(chat.call_count, 1)

    def test_summary_cannot_borrow_retrieved_evidence_unused_by_detail(self):
        extra_query = "What is the examination deadline for an Ayurvedic patent?"
        extra_plan = plan_query(extra_query, use_llm=False)
        extra_hits, _ = self.retriever.search(extra_query, jurisdiction="India", plan=extra_plan)
        extra = next(hit for hit in extra_hits if hit["doc"]["id"] == "patents_rules_2024_rfe")
        value = deepcopy(self.value)
        value["summary"][0].update(
            text="Unchecked examination summary.", source_ids=[extra["doc"]["id"]])
        with patch.object(self.retriever, "search", return_value=(self.hits + [extra], self.confidence)):
            response, chat = self.ask_model(value)
        self.assert_grounded_fallback(response, "Unchecked examination summary")
        self.assertNotIn(extra["doc"]["id"], {c.id for c in response.citations})
        self.assertEqual(chat.call_count, 1)

    def test_withdrawn_fact_in_old_context_cannot_support_summary(self):
        old_fact = "Our Ayurvedic process patent was granted in 2020."
        plan = replace(self.plan, discarded_facts=(old_fact,))
        value = deepcopy(self.value)
        value["summary"][0].update(text="Unchecked earlier grant date.", fact_quotes=[old_fact])
        with patch("backend.llm.available", return_value=True), \
                patch("backend.llm.chat", return_value=json.dumps(value)) as chat:
            response = generation.generate(
                self.query, self.hits, self.confidence, "India", plan=plan, context_query=old_fact)
        self.assertEqual(response["answer_source"], "grounded_synthesis")
        self.assertNotIn("Unchecked earlier grant date", response["summary"])
        self.assertNotIn("Unchecked earlier grant date", response["answer"])
        self.assertEqual(chat.call_count, 1)

    def test_audit_rejecting_only_summary_restores_reviewed_answer(self):
        value = deepcopy(self.value)
        unsupported = "Form 27 guarantees automatic renewal of every Ayurvedic patent."
        value["summary"][0]["text"] = unsupported
        response, chat = self.ask_model(value, audit=False)
        self.assertEqual(chat.call_count, 2)
        proposed = json.loads(chat.call_args_list[1].args[1])["proposed_answer"]
        self.assertEqual(proposed["sections"], self.value["sections"])
        self.assertEqual(proposed["summary"][0]["text"], unsupported)
        self.assert_grounded_fallback(response, unsupported)

    def test_custom_table_keeps_citation_visible_only_in_summary(self):
        query = "Can my Ayurvedic formula be patented? Make a table with columns Issue | Established rule."
        plan = plan_query(query, use_llm=False)
        # A structured application may cite traditional-knowledge evidence that
        # the user's chosen table columns omit from the detailed rendering.
        rendered = {
            "answer": "| Issue | Established rule |\n| --- | --- |\n"
                      "| Patent | Novelty and inventive step are required [patents_invention]. |",
            "summary": "Traditional knowledge is excluded from patentability [patents_3p].",
            "missing": [],
        }
        with patch("backend.pipeline.plan_query", return_value=plan), \
                patch("backend.llm.available", return_value=True), \
                patch("backend.rag.synthesize", return_value=rendered), \
                patch("backend.llm.chat", side_effect=AssertionError("No provider request expected")):
            response = self.engine.answer(AskRequest(query=query))
        self.assertEqual(response.answer_source, "rag_synthesis")
        self.assertNotIn("[patents_3p]", response.answer)
        self.assertIn("[patents_3p]", response.summary)
        self.assertEqual({c.id for c in response.citations}, {"patents_3p", "patents_invention"})
        self.assertTrue(response.details_expanded)

    def test_requested_tables_and_steps_open_details_and_retain_summary(self):
        requests = (
            (self.query + " Make a table.", "| Issue |"),
            (self.query + " Explain step by step.", "**Step-by-step strategy**"),
        )
        for query, detail_marker in requests:
            with self.subTest(query=query):
                response = self.engine.answer(AskRequest(query=query), use_llm=False)
                self.assertFalse(response.abstained)
                self.assertTrue(response.summary)
                self.assertTrue(response.details_expanded)
                self.assertIn(detail_marker, response.answer)

    def test_abstentions_never_present_an_explanatory_summary(self):
        requests = (
            AskRequest(query="Can I patent my computer software algorithm?"),
            AskRequest(query="What dose of Ayurvedic medicine should I take?"),
            AskRequest(query="Can an Ayurvedic process get a PCT patent?", jurisdiction="India"),
            AskRequest(query="क्या आयुर्वेदिक दवा का पेटेंट मिल सकता है?", lang="hi"),
        )
        for request in requests:
            with self.subTest(query=request.query):
                response = self.engine.answer(request, use_llm=False)
                self.assertTrue(response.abstained)
                self.assertEqual(response.summary, "")
                self.assertIsNone(response.original_summary_en)

    def translated_response(self, failure=None):
        hindi_query = "मेरे आयुर्वेदिक प्रक्रिया पेटेंट के लिए फॉर्म 27 कितनी बार दाखिल करना होगा?"
        marker = "[" + self.doc["id"] + "]"
        translated_blocks = {
            "**Patent statement of working**": "**पेटेंट के उपयोग का विवरण**",
            "Established by source:": "स्रोत के अनुसार: भारत में नियम 131 के तहत फॉर्म 27 का विवरण तीन वित्तीय वर्षों की अवधि के लिए दिया जाता है। " + marker,
            "Inference/application:": "अनुप्रयोग: आपके बताए आयुर्वेदिक प्रक्रिया पेटेंट के लिए तीन वर्ष की रिपोर्टिंग अवधि की जाँच करें। " + marker,
            "Not established by retrieved sources:": "साक्ष्य की कमी: पेटेंट किस तारीख को प्रदान किया गया था?",
            self.summary_text: "भारत में, फॉर्म 27 तीन वित्तीय वर्षों की अवधि के लिए दिया जाता है; पेटेंट प्रदान किए जाने की तारीख से रिपोर्टिंग अवधि निर्धारित होती है। " + marker,
        }
        output_translation_calls = []

        def provider(system, user, **kwargs):
            payload = json.loads(user)
            if payload.get("task") == "translate":
                if payload["target_language"] == "English":
                    outputs = [self.query]
                else:
                    kind = "summary" if payload["segments"][0]["text"].startswith(self.summary_text) else "detail"
                    output_translation_calls.append(kind)
                    if kind == failure:
                        return json.dumps({"target_language": "Hindi", "complete": False, "segments": []})
                    outputs = []
                    for segment in payload["segments"]:
                        options = [out for prefix, out in translated_blocks.items() if segment["text"].startswith(prefix)]
                        self.assertEqual(len(options), 1, "Unexpected source translation segment")
                        outputs.append(options[0])
                return json.dumps({"target_language": payload["target_language"], "complete": True,
                                   "segments": [{"id": segment["id"], "translation": out}
                                                for segment, out in zip(payload["segments"], outputs)]}, ensure_ascii=False)
            if "proposed_answer" in payload:
                return '{"supported":true}'
            self.assertIn("requested_issues", payload)
            return json.dumps(self.value)

        with patch("backend.pipeline.plan_query", return_value=self.plan), \
                patch("backend.i18n.available", return_value=True), \
                patch("backend.llm.available", return_value=True), \
                patch("backend.llm.chat", side_effect=provider):
            response = self.engine.answer(AskRequest(query=hindi_query, lang="hi"))
        return response, output_translation_calls, translated_blocks[self.summary_text]

    def test_summary_and_detail_translate_together_and_preserve_english_originals(self):
        english, _ = self.ask_model()
        response, calls, translated_summary = self.translated_response()
        self.assertEqual(calls, ["detail", "summary"])
        self.assertEqual((response.lang, response.requested_lang, response.translation_status),
                         ("hi", "hi", "translated"))
        self.assertEqual(response.summary, translated_summary)
        self.assertIn("**पेटेंट के उपयोग का विवरण**", response.answer)
        self.assertNotIn("Established by source:", response.answer)
        self.assertEqual(response.original_answer_en, english.answer)
        self.assertEqual(response.original_summary_en, english.summary)
        self.assertEqual(response.citations, english.citations)

    def test_failure_of_either_translation_restores_both_english_fields(self):
        english, _ = self.ask_model()
        for failure, expected_calls in (("detail", ["detail"]), ("summary", ["detail", "summary"])):
            with self.subTest(failure=failure):
                response, calls, _ = self.translated_response(failure)
                self.assertEqual(calls, expected_calls)
                self.assertEqual((response.lang, response.requested_lang, response.translation_status),
                                 ("en", "hi", "output_failed"))
                self.assertEqual(response.answer, english.answer)
                self.assertEqual(response.summary, english.summary)
                self.assertIsNone(response.original_answer_en)
                self.assertIsNone(response.original_summary_en)
                self.assertTrue(any("English answer is shown" in notice for notice in response.notices))


if __name__ == "__main__":
    unittest.main()
