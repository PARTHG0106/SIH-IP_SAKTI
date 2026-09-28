"""Question-driven planning and case isolation, without provider access."""
import json
import os
import unittest
from unittest.mock import patch

os.environ["LLM_PROVIDER"] = "none"
os.environ["RETRIEVER"] = "bm25"

from backend.memory import Turn, context_for
from backend.planning import domain_scope, plan_query


NEW_AYURVEDA_CASE = """I am an Ayurvedic manufacturer in India planning to launch a new
proprietary Ayurvedic medicine for joint pain. The formulation contains 5 medicinal plants,
and the exact combination and manufacturing process were developed by us after studying
several classical Ayurvedic texts. Two of the ingredients are sourced from wild plants
collected in India, while the other three are cultivated by our suppliers.
The product will be manufactured in India and sold under a new brand name.
We also want to eventually export it to the United States and European Union.
Whether the product could qualify as a classical Ayurvedic medicine, a patent/proprietary
medicine, or another regulatory category.
Which parts of the formulation or manufacturing process could receive patent protection?
What IP protection could be used for the brand, packaging, manufacturing know-how,
technical documents and artwork?
For the two wild-sourced plants and three cultivated plants, explain how the Biological
Diversity Act could apply differently and what sourcing facts need to be established.
Explain the roles of the National Biodiversity Authority, State Biodiversity Board,
Biodiversity Management Committee and AYUSH/State licensing authority.
Explain source, geographical origin, quantity and supplier records.
Explain what could change if the formulation is later patented and commercialised.
Identify the major facts still needed before a definitive conclusion."""

OLD_CASE = "I am planning to launch an Ayurvedic medicine with Ashwagandha and three other plants. The exact combination is not disclosed in classical Ayurvedic texts. Explain patents, GI and plant-variety rights."


class PlanningScopeTests(unittest.TestCase):
    def test_new_scenario_keeps_destinations_and_actual_requested_issues(self):
        plan = plan_query(NEW_AYURVEDA_CASE, OLD_CASE)
        keys = {i.key for i in plan.issues}
        self.assertTrue({"classification", "patent", "secrecy", "copyright", "sourcing", "us", "eu"} <= keys)
        self.assertFalse(keys & {"gi", "plant_variety"})
        self.assertNotIn("Ashwagandha", plan.facts_query)
        self.assertNotIn("ppvfr_act", {s for i in plan.issues for s in i.source_ids})
        self.assertNotIn("gi_act", {s for i in plan.issues for s in i.source_ids})
        self.assertTrue(plan.conditional)
        self.assertTrue(any("United States" in q for q in plan.missing_facts))
        self.assertTrue(any("EU member state" in q for q in plan.missing_facts))
        self.assertTrue(any("commercialisation dates" in q for q in plan.missing_facts))
        self.assertTrue(all(fact in NEW_AYURVEDA_CASE for fact in plan.facts))

    def test_no_us_destination_is_inferred_from_the_pronoun(self):
        plan = plan_query("Our Ayurvedic formulation was developed by us. Explain Indian patent protection.")
        self.assertNotIn("us", {i.key for i in plan.issues})

    def test_origin_records_do_not_imply_geographical_indication(self):
        plan = plan_query("What source and geographical origin records are required for Ayurvedic medicinal plants?")
        self.assertIn("sourcing", {i.key for i in plan.issues})
        self.assertNotIn("gi", {i.key for i in plan.issues})
        geographic_product = plan_query("How do I protect a region-specific Ayurvedic product tied to its place of origin?")
        self.assertEqual([i.key for i in geographic_product.issues], ["gi"])

    def test_botanical_ingredient_does_not_become_a_historical_dispute(self):
        plan = plan_query("Can I patent an Ayurvedic formulation containing turmeric and neem?")
        self.assertEqual({i.key for i in plan.issues}, {"patent", "exclusions"})
        history = plan_query("Is turmeric's use in wound healing patentable given the old US patent?")
        self.assertEqual([i.key for i in history.issues], ["turmeric"])

    def test_current_non_ayurveda_cases_cannot_borrow_old_domain(self):
        for query in (
            "Now I have invented an algorithm and physical software device. Give me a complete IP strategy.",
            "I invented a new car tyre. How can I patent it?",
            "I own a restaurant and need trademark protection.",
            "Can I copyright my novel?",
            "What about this product which is unrelated to Ayurveda?",
        ):
            with self.subTest(query=query):
                self.assertEqual(domain_scope(query, OLD_CASE), "out_of_scope")
                self.assertFalse(plan_query(query, OLD_CASE).issues)

    def test_explicit_component_followup_can_keep_ayurveda_context(self):
        self.assertEqual(domain_scope("What about copyright for the software in my product?", OLD_CASE), "ayurveda")
        self.assertEqual(domain_scope("What makes an invention novel?"), "unclear")
        self.assertEqual(domain_scope("What is Form 27?"), "reference")

    def test_self_contained_case_starts_new_memory_chain(self):
        turn = Turn(OLD_CASE, OLD_CASE, [], "v1", .9)
        self.assertIsNone(context_for([turn], "Now " + NEW_AYURVEDA_CASE))
        self.assertIs(context_for([turn], "What about trademark protection for my product?"), turn)

    def test_correction_removes_obsolete_classical_formula_fact(self):
        query = "Correction: the complete formula and manufacture exactly match a First-Schedule formula. Is this classical or proprietary?"
        turn = Turn(OLD_CASE, OLD_CASE, [], "v1", .9)
        self.assertIs(context_for([turn], query), turn)
        plan = plan_query(query, OLD_CASE)
        self.assertIn("First-Schedule formula", plan.facts_query)
        self.assertNotIn("not disclosed in classical Ayurvedic texts", plan.facts_query)

    def test_multiple_source_corrections_keep_only_latest_material_facts(self):
        context = ("I manufacture an Ayurvedic medicine. The plants are wild collected in India.\n"
                   "Follow-up: Correction: all plants are cultivated by our suppliers.")
        current = "Correction: all plants are wild collected, not cultivated. Explain section 7."
        plan = plan_query(current, context)
        self.assertNotIn("The plants are wild collected in India", plan.facts_query)
        self.assertNotIn("all plants are cultivated by our suppliers", plan.facts_query)
        self.assertIn("all plants are wild collected, not cultivated", plan.facts_query)
        self.assertIn("I manufacture an Ayurvedic medicine", plan.facts_query)
        self.assertTrue(all(fact in context + "\n" + current for fact in plan.facts))

    def test_format_followup_does_not_restore_superseded_source_facts(self):
        context = ("I manufacture an Ayurvedic medicine. The plants are wild collected in India.\n"
                   "Follow-up: Correction: all plants are cultivated by our suppliers.\n"
                   "Follow-up: Correction: all plants are wild collected, not cultivated. Explain section 7.")
        plan = plan_query("Make it a table using the same sources.", context)
        self.assertNotIn("all plants are cultivated by our suppliers", plan.facts_query)
        self.assertNotIn("The plants are wild collected in India", plan.facts_query)
        self.assertIn("all plants are wild collected, not cultivated", plan.facts_query)

    def test_two_material_groups_in_one_scenario_are_both_preserved(self):
        context = "I manufacture an Ayurvedic medicine. The plants from one supplier are wild collected. The materials from another supplier are cultivated."
        plan = plan_query("Explain section 7 for my product.", context)
        self.assertIn("one supplier are wild collected", plan.facts_query)
        self.assertIn("another supplier are cultivated", plan.facts_query)

    def test_sourcing_question_with_unrelated_new_fact_preserves_sources(self):
        context = "I manufacture an Ayurvedic medicine. The plants are wild collected in India."
        plan = plan_query("Our company is foreign-controlled. Explain how the rules for cultivated plants differ.", context)
        self.assertIn("The plants are wild collected in India", plan.facts_query)
        self.assertIn("Our company is foreign-controlled", plan.facts_query)

    def test_source_bound_format_followup_preserves_original_issues(self):
        plan = plan_query("Based ONLY on the sources for my previous question, create a table covering every original issue.", OLD_CASE)
        self.assertEqual(plan.substantive_query, OLD_CASE)
        self.assertTrue({"patent", "gi", "plant_variety"} <= {i.key for i in plan.issues})

    def test_comparison_keeps_domestic_patent_and_pct(self):
        plan = plan_query("Compare Indian patent protection and the PCT route for an Ayurvedic extraction process.")
        self.assertEqual({i.key for i in plan.issues}, {"patent", "pct"})

    def test_model_refinement_preserves_reviewed_local_fallback(self):
        query = "What is the patent statement of working in Form 27?"
        output = json.dumps({
            "subquestions": [{"question": "What does Form 27 require?", "search_query": "statement of working patent Rule 131"}],
            "facts": [], "missing_facts": [],
            "output_format": {"table": None, "steps": False, "concise": False, "columns": []},
        })
        with patch("backend.planning.llm.available", return_value=True), patch("backend.planning.llm.chat", return_value=output):
            plan = plan_query(query, use_llm=True)
        self.assertEqual(plan.planner, "model")
        self.assertEqual([i.key for i in plan.issues], ["working"])
        self.assertEqual(plan.issues[0].source_ids, ("patents_rules_2024_form27",))
        self.assertEqual(plan.subquestions, ("What does Form 27 require?",))

    def test_model_cannot_restore_facts_from_an_independent_old_case(self):
        output = json.dumps({
            "subquestions": [{"question": "Which regulatory category applies?", "search_query": "Ayurvedic proprietary medicine"}],
            "facts": ["The exact combination is not disclosed in classical Ayurvedic texts."],
            "missing_facts": [],
            "output_format": {"table": None, "steps": False, "concise": False, "columns": []},
        })
        with patch("backend.planning.llm.available", return_value=True), patch("backend.planning.llm.chat", return_value=output):
            plan = plan_query(NEW_AYURVEDA_CASE, OLD_CASE, use_llm=True)
        self.assertEqual(plan.planner, "local")
        self.assertNotIn("not disclosed in classical Ayurvedic texts", plan.facts_query)


if __name__ == "__main__":
    unittest.main()
