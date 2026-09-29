"""Planner recovery preserves actual user spans without accepting paraphrases."""
import json
from pathlib import Path
import unittest

from backend.planning import _local_plan, _model_plan


class PlannerGroundingTests(unittest.TestCase):
    def refine(self, current, facts=(), context=None, question="How is the product classified?",
               search="India Ayurvedic product classification"):
        output = {
            "subquestions": [{"question": question, "search_query": search}],
            "facts": list(facts), "missing_facts": [],
            "output_format": {"table": None, "steps": False, "concise": False, "columns": []},
        }
        return _model_plan(json.dumps(output), _local_plan(current, context), current, context)

    def test_unique_capitalization_match_restores_original_fact(self):
        current = "Our Ayurvedic oil contains two plants. Explain its classification."
        plan = self.refine(current, ["our Ayurvedic oil contains two plants."])
        self.assertEqual(plan.planner, "model")
        self.assertIn("Our Ayurvedic oil contains two plants.", plan.facts)
        self.assertNotIn("our Ayurvedic oil contains two plants.", plan.facts)

    def test_unique_context_match_restores_original_fact(self):
        context = "We sell our Ayurvedic oil only in India."
        plan = self.refine("Explain the licensing route.", ["we sell our Ayurvedic oil only in India."], context)
        self.assertIn(context, plan.facts)

    def test_exact_match_remains_valid_when_repeated(self):
        fact = "Our Ayurvedic oil contains two plants."
        plan = self.refine(fact + " " + fact, [fact])
        self.assertEqual(plan.facts.count(fact), 1)

    def test_ambiguous_capitalization_match_is_rejected(self):
        current = "Our Ayurvedic oil contains two plants. OUR Ayurvedic oil contains two plants."
        with self.assertRaisesRegex(ValueError, "Ungrounded planner fact"):
            self.refine(current, ["our Ayurvedic oil contains two plants."])

    def test_altered_number_negation_or_spacing_is_rejected(self):
        current = "Our Ayurvedic oil contains 2 plants. It is not exported."
        for fact in ("our Ayurvedic oil contains 3 plants.", "it is exported.",
                     "our Ayurvedic oil contains  2 plants."):
            with self.subTest(fact=fact), self.assertRaisesRegex(ValueError, "Ungrounded planner fact"):
                self.refine(current, [fact])

    def test_identical_question_and_search_are_valid(self):
        question = "What is TKDL?"
        plan = self.refine(question, question=question, search=question)
        self.assertEqual(plan.planner, "model")
        self.assertEqual(plan.subquestions, (question,))
        self.assertIn(question, plan.search_queries)

    def test_identical_question_and_search_still_obey_length_bound(self):
        text = "x" * 801
        with self.assertRaisesRegex(ValueError, "Invalid planner string list"):
            self.refine("What is TKDL?", question=text, search=text)

    def test_recorded_planner_capitalization_failure_is_recovered(self):
        path = Path(__file__).resolve().parents[1] / "docs/qa/live-provider/corrections/results.json"
        case = next(c for c in json.loads(path.read_text(encoding="utf-8"))["cases"] if c["id"] == 4)
        output = next(e["output"] for e in case["provider_events"] if e["stage"] == "planner")
        current, context = case["prompt"], case["response"]["context_question"]
        fallback = _local_plan(current, context)
        plan = _model_plan(output, fallback, current, context)
        self.assertEqual(plan.planner, "model")
        self.assertEqual(plan.issues, fallback.issues)
        self.assertEqual(plan.facts_query, fallback.facts_query)
        self.assertTrue(all(fact in current or fact in context for fact in plan.facts))


if __name__ == "__main__":
    unittest.main()
