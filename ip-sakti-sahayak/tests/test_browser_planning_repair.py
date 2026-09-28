"""Case-state regressions from browser failures, plus changed-wording checks."""
import json
from pathlib import Path
import unittest

from backend.case_state import fact_spans
from backend.memory import Turn, context_for
from backend.planning import domain_scope, plan_query


_REPORT = Path(__file__).resolve().parents[1] / "docs/qa/manual-complex-browser/browser-observations.json"
_CASES = {case["id"]: case["prompt"] for case in json.loads(_REPORT.read_text(encoding="utf-8"))["cases"]}


def keys(plan):
    return {issue.key for issue in plan.issues}


class BrowserPlanningRepairTests(unittest.TestCase):
    def test_public_demonstration_and_labeled_experiments_are_preserved(self):
        first = plan_query(_CASES[1])
        self.assertTrue(any("At a trade fair" in fact and "did not disclose" in fact for fact in first.facts))
        self.assertIn("trademark", keys(first))
        self.assertIn("ownership", keys(first))
        claims = plan_query(_CASES[6])
        self.assertTrue(any(f.startswith("Claim A") and "no enhancement" in f for f in claims.facts))
        self.assertTrue(any(f.startswith("Claim B") and "not an interaction" in f for f in claims.facts))
        self.assertEqual(keys(claims), {"patent", "exclusions"})
        exclusions = next(issue for issue in claims.issues if issue.key == "exclusions")
        self.assertEqual(set(exclusions.source_ids), {"patents_3d", "patents_3e", "patents_3p"})

    def test_date_prefaces_do_not_require_a_fact_start_whitelist(self):
        text = ("During an investor meeting in June, the inventor handed out the complete extraction ratios. "
                "After testing, the laboratory found no improvement in efficacy. "
                "Explain the Ayurvedic patent consequences.")
        self.assertEqual(fact_spans(text), (
            "During an investor meeting in June, the inventor handed out the complete extraction ratios.",
            "After testing, the laboratory found no improvement in efficacy."))

    def test_labels_stay_attached_to_their_countries(self):
        plan = plan_query(_CASES[2])
        self.assertEqual(set(plan.markets), {"India", "EU", "US"})
        self.assertTrue({"eu", "us", "advertising", "manufacturing"} <= keys(plan))
        self.assertNotIn("food", keys(plan))
        self.assertTrue(any(country == "US" and "dietary supplement" in span for country, span in plan.market_intents))
        self.assertFalse(any(country == "India" and "dietary supplement" in span for country, span in plan.market_intents))

    def test_eu_members_and_foreign_shareholders_are_distinguished(self):
        plan = plan_query("Our Ayurvedic tea is sold in France as a food supplement. Explain its classification.")
        self.assertIn("EU", plan.markets)
        self.assertIn("eu", keys(plan))
        self.assertNotIn("food", keys(plan))
        shareholder = plan_query("We sell an Ayurvedic oil in India. Our company has a Swedish shareholder. Explain biodiversity duties.")
        self.assertEqual(shareholder.markets, ("India",))
        self.assertNotIn("eu", keys(shareholder))

    def test_foreign_brand_comparison_exposes_missing_substantive_rules(self):
        prompt = ("Our Ayurvedic digestive powder is planned for sale in India and France. "
                  "We have a proposed brand but no completed trademark search. "
                  "The French distributor calls it a traditional herbal medicine, although its medicinal-use history is undocumented. "
                  "Compare the classification evidence and brand-protection questions for the two markets.")
        plan = plan_query(prompt)
        self.assertTrue({"trademark", "eu_trademark", "eu"} <= keys(plan))
        gap = next(issue for issue in plan.issues if issue.key == "eu_trademark")
        self.assertEqual(gap.source_ids, ())
        self.assertIn(gap.title, plan.subquestions)
        self.assertFalse(any("Which EU member state" in question for question in plan.missing_facts))
        self.assertTrue(any("stated EU destination France" in question for question in plan.missing_facts))
        followup = plan_query("Use only the previous sources to make a brief table covering every original issue.", prompt)
        self.assertIn("eu_trademark", keys(followup))

    def test_foreign_shareholder_or_madrid_route_does_not_add_foreign_brand_checklist(self):
        for prompt in (
            "We sell an Ayurvedic product in India. Our company has a French shareholder. Explain trademark protection.",
            "Our Ayurvedic product is sold in India and France. We have a brand. Compare only its medicinal classification for both markets.",
            "We sell an Ayurvedic product in India and France. Explain only the Madrid route for our trademark registration.",
        ):
            with self.subTest(prompt=prompt):
                self.assertFalse({"eu_trademark", "us_trademark"} & keys(plan_query(prompt)))

    def test_us_and_eu_foreign_brand_comparison_does_not_invent_sources(self):
        plan = plan_query("Our Ayurvedic oil is sold in India, Germany and the United States. Compare trademark protection for each market.")
        self.assertTrue({"eu_trademark", "us_trademark"} <= keys(plan))
        self.assertTrue(all(not issue.source_ids for issue in plan.issues if issue.key in {"eu_trademark", "us_trademark"}))

    def test_full_replacement_keeps_discard_report_and_cancels_old_markets(self):
        turn = Turn(_CASES[2], _CASES[2], [], "v", .8)
        self.assertIs(context_for([turn], _CASES[3]), turn)
        plan = plan_query(_CASES[3], _CASES[2])
        self.assertEqual(plan.markets, ("India",))
        self.assertFalse({"us", "eu", "food", "ownership", "advertising"} & keys(plan))
        self.assertTrue({"classification", "manufacturing", "cosmetic", "access"} <= keys(plan))
        self.assertNotIn("German majority shareholder", plan.facts_query)
        self.assertNotIn("cures bronchitis", plan.facts_query)
        self.assertTrue(any("German majority shareholder" in fact for fact in plan.discarded_facts))
        self.assertTrue(all(fact in _CASES[2] for fact in plan.discarded_facts))

    def test_source_only_table_preserves_revised_issues_and_exact_columns(self):
        context = _CASES[2] + "\nFollow-up: " + _CASES[3]
        plan = plan_query(_CASES[4], context)
        self.assertEqual(plan.format_columns, ("Issue", "Established rule", "Application to my revised facts", "Missing evidence"))
        self.assertTrue(plan.concise)
        self.assertTrue({"classification", "manufacturing", "cosmetic", "access"} <= keys(plan))
        self.assertFalse({"us", "eu", "food"} & keys(plan))
        self.assertNotIn("cures bronchitis", plan.facts_query)

    def test_pipe_headers_can_wrap_across_lines(self):
        prompt = ("Use the same sources. Create a table with: Issue | Established rule |\n"
                  "Application to our facts | Missing evidence.\nKeep it short.")
        plan = plan_query(prompt, "We make an Ayurvedic oil. Explain its licence and cosmetic category.")
        self.assertEqual(plan.format_columns, ("Issue", "Established rule", "Application to our facts", "Missing evidence"))

    def test_header_introducers_allow_optional_colon_and_arbitrary_labels(self):
        for intro in ("Create a table with columns", "Make a table with columns:",
                      "Make a table whose headers are", "Use a table with headers as follows:"):
            with self.subTest(intro=intro):
                plan = plan_query(intro + " Topic | Source rule | Research gap.")
                self.assertEqual(plan.format_columns, ("Topic", "Source rule", "Research gap"))

    def test_named_cosmetic_alternative_preserves_source_only_medicine_topic(self):
        original = ("Our Ayurvedic product in India contains two herbs and is intended as a medicine. "
                    "We have not compared the finished formula to an authoritative book. "
                    "Explain only the statutory classical-versus-proprietary distinction; do not assume either classification is approved.")
        prompt = ("Using only the previous sources, create a brief table with columns Issue | Established rule | Missing evidence. "
                  "Include both the original medicine distinction and the alternative cosmetic category. "
                  "If the earlier sources cannot establish the cosmetic test, say so explicitly. Do not search for anything new.")
        plan = plan_query(prompt, original)
        self.assertEqual(plan.format_columns, ("Issue", "Established rule", "Missing evidence"))
        self.assertEqual(keys(plan), {"classification", "cosmetic"})
        self.assertTrue(plan.concise)

    def test_source_only_format_retains_previous_unmapped_requested_topic(self):
        original = "We make an Ayurvedic oil. Explain patents. Include distributor exclusivity."
        plan = plan_query("Using only previous sources, make a table covering every original issue.", original)
        self.assertTrue(any(issue.title == "distributor exclusivity" for issue in plan.issues))

    def test_entity_correction_preserves_unrelated_sourcing_clause(self):
        context = ("We manufacture an Ayurvedic oil. All herbs are wild collected in India; "
                   "our company is foreign-controlled. Explain section 7.")
        plan = plan_query("Correction: the company is wholly Indian-owned. Explain biodiversity duties.", context)
        self.assertIn("All herbs are wild collected in India", plan.facts_query)
        self.assertNotIn("company is foreign-controlled", plan.facts_query)
        self.assertIn("company is wholly Indian-owned", plan.facts_query)

    def test_ingredient_correction_keeps_product_identity_and_other_facts(self):
        context = "We make an Ayurvedic hair oil containing neem. The company is wholly Indian-owned."
        plan = plan_query("Correction: the product contains only sesame oil. Explain the category.", context)
        self.assertIn("We make an Ayurvedic hair oil", plan.facts_query)
        self.assertIn("company is wholly Indian-owned", plan.facts_query)
        self.assertNotIn("containing neem", plan.facts_query)
        self.assertEqual(plan.scope, "ayurveda")

    def test_public_disclosure_correction_does_not_erase_formula_reference(self):
        context = ("We make an Ayurvedic medicine. The exact combination is not disclosed in classical Ayurvedic texts. "
                   "The process has never been publicly demonstrated.")
        plan = plan_query("Correction: we publicly demonstrated the process last week. Explain patents.", context)
        self.assertIn("not disclosed in classical Ayurvedic texts", plan.facts_query)
        self.assertNotIn("never been publicly demonstrated", plan.facts_query)

    def test_short_comparison_preserves_multiple_exclusions(self):
        plan = plan_query("Compare sections 3(d), 3(e) and 3(p) and novelty for an Ayurvedic patent.")
        self.assertEqual(keys(plan), {"patent", "exclusions"})
        exclusion = next(issue for issue in plan.issues if issue.key == "exclusions")
        self.assertEqual(set(exclusion.source_ids), {"patents_3d", "patents_3e", "patents_3p"})

    def test_unmapped_explicit_topic_is_kept_as_an_evidence_gap(self):
        plan = plan_query("For our Ayurvedic product, explain patents. Include distributor exclusivity and cybersecurity insurance.")
        missing = [issue for issue in plan.issues if issue.key.startswith("requested_")]
        self.assertEqual({issue.title for issue in missing}, {"distributor exclusivity", "cybersecurity insurance"})
        self.assertTrue(all(not issue.source_ids for issue in missing))

    def test_brand_name_and_negated_domain_do_not_bypass_scope(self):
        for prompt in (_CASES[5], _CASES[7], _CASES[8],
                       "At Ayurveda Quantum Labs, we build banking encryption algorithms. Explain patent protection.",
                       "Separate case: Ayurveda Networks is our firm name. We design only online payment encryption, unrelated to herbal medicine or healthcare. Explain patent options.",
                       "Ayurveda Networks is our firm name. We design banking encryption. Explain patents.",
                       "Our server protocol has no link to Ayurveda or traditional knowledge. Explain patents."):
            with self.subTest(prompt=prompt):
                self.assertEqual(domain_scope(prompt), "out_of_scope")
                self.assertFalse(plan_query(prompt).issues)
        self.assertEqual(domain_scope("Our software controls extraction for an Ayurvedic medicine. Explain patent protection."), "ayurveda")

    def test_cancellation_mentioned_with_new_domestic_case_has_no_foreign_issue(self):
        plan = plan_query("We sell an Ayurvedic cream only in India, with no Germany or US exports. Explain its licensing.")
        self.assertEqual(plan.markets, ("India",))
        self.assertFalse({"eu", "us"} & keys(plan))


if __name__ == "__main__":
    unittest.main()
