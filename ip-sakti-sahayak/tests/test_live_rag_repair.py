"""Provider-free checks for requirements that must survive live model planning."""
from dataclasses import replace
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from backend import rag
from backend.planning import _local_plan, _model_plan


class LiveRagRepairTests(unittest.TestCase):
    def setUp(self):
        self.doc = {
            "id": "dc_3a", "jurisdiction": "India", "statute": "Test statute",
            "section": "s.3(a)", "as_of": "2026-09-28",
            "text": "A medicine matching the authoritative formula satisfies this stated formula test.",
            "source_url": "https://example.invalid/reviewed-source",
        }
        self.original = "Our Ayurvedic medicine is sold in India. Explain the classical-versus-proprietary distinction."
        self.followup = ("Use only the previous sources. Make a brief table with columns Issue | Established rule | Missing evidence. "
                         "Include the alternative cosmetic category.")

    def refined(self, query=None, context=None):
        query, context = query or self.followup, context or self.original
        fallback = _local_plan(query, context)
        output = {"subquestions": [{"question": "What is the medicine distinction?", "search_query": "classical proprietary distinction"}],
                  "facts": [], "missing_facts": [],
                  "output_format": {"table": None, "steps": False, "concise": False, "columns": []}}
        return _model_plan(json.dumps(output), fallback, query, context)

    def response(self, plan):
        sections = []
        for issue in plan.issues:
            established = ([{"text": "The stated formula test is described by the source.",
                             "source_id": self.doc["id"], "quote": self.doc["text"]}]
                           if issue.key == "classification" else [])
            sections.append({"issue": issue.title, "established": established,
                             "application": [], "unanswered": [] if established else ["Insufficient evidence in retrieved sources."]})
        return {"sections": sections, "questions": [], "steps": []}

    def synthesize(self, query, context, plan, response):
        with patch("backend.rag.llm.available", return_value=True), patch("backend.rag.llm.chat", side_effect=[json.dumps(response), '{"supported":true}']) as chat:
            result = rag.synthesize(query, context, plan, [{"doc": self.doc, "score": 1.0}])
        return result, chat

    def test_planner_cannot_remove_required_cosmetic_section(self):
        plan = self.refined()
        response = self.response(plan)
        response["sections"] = response["sections"][:1]
        result, chat = self.synthesize(self.followup, self.original, plan, response)
        self.assertIsNone(result)
        self.assertEqual(chat.call_count, 1)
        payload = json.loads(chat.call_args_list[0].args[1])
        self.assertEqual(payload["requested_issues"], [issue.title for issue in plan.issues])
        self.assertEqual(payload["request_breakdown"], ["What is the medicine distinction?"])

    def test_complete_source_only_table_preserves_gap_and_custom_headers(self):
        plan = self.refined()
        result, chat = self.synthesize(self.followup, self.original, plan, self.response(plan))
        self.assertIsNotNone(result)
        self.assertIn("| Issue | Established rule | Missing evidence |", result["answer"])
        self.assertIn("Possible cosmetic category and licensing", result["answer"])
        self.assertIn("Insufficient evidence in retrieved sources.", result["answer"])
        self.assertNotIn("[dc_cosmetic]", result["answer"])
        payload = json.loads(chat.call_args_list[0].args[1])
        self.assertEqual(payload["issue_source_coverage"]["Possible cosmetic category and licensing"], [])

    def test_missing_cosmetic_sources_cannot_borrow_a_medicine_quote(self):
        plan = self.refined()
        response = self.response(plan)
        cosmetic = next(section for section in response["sections"] if "cosmetic" in section["issue"])
        cosmetic["established"] = [{"text": "This source establishes a cosmetic classification test.",
                                    "source_id": self.doc["id"], "quote": self.doc["text"]}]
        result, chat = self.synthesize(self.followup, self.original, plan, response)
        self.assertIsNone(result)
        self.assertEqual(chat.call_count, 1)

    def test_unmapped_requested_subject_stays_in_required_coverage(self):
        original = self.original + " Include distributor exclusivity."
        prompt = "Use only the previous sources to make a table covering every original issue."
        plan = self.refined(prompt, original)
        result, _ = self.synthesize(prompt, original, plan, self.response(plan))
        self.assertIsNotNone(result)
        self.assertIn("distributor exclusivity", result["answer"])
        self.assertIn("distributor exclusivity", result["missing"])

    def test_explicit_correction_renders_verbatim_case_data_before_legal_sections(self):
        path = Path(__file__).resolve().parents[1] / "docs/qa/manual-complex-browser/browser-observations.json"
        cases = {case["id"]: case["prompt"] for case in json.loads(path.read_text(encoding="utf-8"))["cases"]}
        plan = self.refined(cases[3], cases[2])
        result, _ = self.synthesize(cases[3], cases[2], plan, self.response(plan))
        self.assertIsNotNone(result)
        self.assertTrue(result["answer"].startswith("**Earlier facts withdrawn by your correction**"))
        for fact in (*plan.discarded_facts, *plan.facts):
            self.assertIn("“" + fact + "”", result["answer"])
        self.assertIn("**Current facts supplied by you (unverified)**", result["answer"])
        self.assertNotIn("Facts still needed and conditional outcomes", result["answer"])

    def test_fact_block_escapes_user_markup_and_does_not_repeat_on_format_request(self):
        plan = replace(self.refined(), discarded_facts=("Our old label is [invented](javascript:bad) <b>text</b>.",),
                       facts=("Our new label is **bright** | plain.",))
        response = self.response(plan)
        result, _ = self.synthesize("Correction: replace all product facts.", self.original, plan, response)
        self.assertIn("&#91;invented&#93;", result["answer"])
        self.assertIn("&lt;b&gt;text&lt;/b&gt;", result["answer"])
        self.assertIn("&#42;&#42;bright&#42;&#42; &#124; plain", result["answer"])
        self.assertNotIn("[invented]", result["answer"])
        formatted, _ = self.synthesize(self.followup, self.original, plan, response)
        self.assertNotIn("Earlier facts withdrawn", formatted["answer"])


if __name__ == "__main__":
    unittest.main()
