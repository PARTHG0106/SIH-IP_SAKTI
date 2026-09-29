"""Fallback decisions must answer the missing fact with relevant evidence."""
from types import SimpleNamespace
import unittest

from backend.answer_cards import CARDS
from backend.case_analysis import render_fact_analysis


def render(question, *source_ids):
    plan = SimpleNamespace(
        missing_facts=(question,), conditional=True, concise=False,
        substantive_query="Explain the conditional outcomes", facts=(),
        facts_query="The product is a herbal hair oil. All plants are cultivated.",
        discarded_facts=(),
    )
    points = [({"id": source_id, "section": "reviewed provision"}, CARDS[source_id])
              for source_id in source_ids]
    return render_fact_analysis(plan, [(None, points)])


class FallbackQuestionRoutingTests(unittest.TestCase):
    def test_outsourced_manufacture_uses_licensing_not_resource_sourcing(self):
        for question in (
            "Does the company itself manufacture the hair oil, or is manufacturing outsourced to a third party?",
            "Will production be outsourced under a licence?",
            "Which facilities manufacture the product?",
        ):
            with self.subTest(question=question):
                answer = render(question, "bda_s7_exemption", "bda_origin_2025", "dc_licensing")
                self.assertIn("[dc_licensing]", answer)
                self.assertNotIn("[bda_s7_exemption]", answer)
                self.assertNotIn("[bda_origin_2025]", answer)

    def test_original_formula_uses_classification_not_resource_origin(self):
        for question in (
            "Does the formulation follow a formula from an authoritative Ayurvedic text, or is it a proprietary/original formulation?",
            "Has the original recipe been compared with authoritative books?",
            "Is the originally developed formula classical?",
        ):
            with self.subTest(question=question):
                answer = render(question, "bda_s7_exemption", "bda_origin_2025", "dc_3a", "dc_3h")
                self.assertIn("[dc_3a]", answer)
                self.assertIn("[dc_3h]", answer)
                self.assertNotIn("[bda_s7_exemption]", answer)
                self.assertNotIn("[bda_origin_2025]", answer)

    def test_actual_material_source_inflections_still_use_sourcing(self):
        for question in (
            "Where were the plants sourced?",
            "What are the sources of each herb?",
            "What sourcing records exist?",
            "What is the geographical origin of the ingredients?",
        ):
            with self.subTest(question=question):
                answer = render(question, "bda_sourcing", "dc_3a", "dc_licensing")
                self.assertIn("[bda_sourcing]", answer)
                self.assertNotIn("[dc_3a]", answer)
                self.assertNotIn("[dc_licensing]", answer)

    def test_europe_history_does_not_use_indian_formula_definition(self):
        for destination in ("Europe", "the European Union", "the EU", "Germany", "France"):
            with self.subTest(destination=destination):
                answer = render(
                    f"Is there documented evidence of this formulation's history of medicinal use in {destination}?",
                    "dc_3a", "dc_3h", "eu_thmpd",
                )
                self.assertIn("[eu_thmpd]", answer)
                self.assertNotIn("[dc_3a]", answer)
                self.assertNotIn("[dc_3h]", answer)

    def test_unknown_question_and_missing_relevant_evidence_remain_gaps(self):
        for question, irrelevant_source in (
            ("What dose is intended?", "dc_3a"),
            ("Will manufacturing be outsourced?", "dc_3a"),
            ("What is the material's geographical origin?", "bda_s6"),
            ("What experimental data supports the proposed patent claims?", "patents_rights"),
            ("Is the original formula classical?", "bda_origin_2025"),
            ("What medicinal-use history exists for this formula in Europe?", "dc_3a"),
        ):
            with self.subTest(question=question):
                answer = render(question, irrelevant_source)
                self.assertIn("Not established by the reviewed sources", answer)
                self.assertNotIn(f"[{irrelevant_source}]", answer)


if __name__ == "__main__":
    unittest.main()
