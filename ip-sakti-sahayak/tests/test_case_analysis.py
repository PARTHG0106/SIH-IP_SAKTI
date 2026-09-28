"""Facts must change local reasoning without changing its evidence universe."""
import os
from types import SimpleNamespace
import unittest

os.environ["LLM_PROVIDER"] = "none"
os.environ["RETRIEVER"] = "bm25"

from backend.answer_cards import CARDS, ISSUE_CARDS
from backend.case_analysis import application, render_fact_analysis


def point(source_id, issue=None):
    return ({"id": source_id, "section": "reviewed section"},
            ISSUE_CARDS[issue][source_id] if issue else CARDS[source_id])


def plan(**overrides):
    data = dict(facts_query="", substantive_query="Analyse comprehensively", facts=(),
                missing_facts=(), conditional=True, concise=False)
    data.update(overrides)
    return SimpleNamespace(**data)


class FactApplicationTests(unittest.TestCase):
    def apply(self, source, text, issue=None):
        return application(*point(source, issue), text)

    def test_company_development_is_not_evidence_of_absence_from_books(self):
        answer = self.apply("dc_3a", "The formulation was developed by us after studying several classical Ayurvedic texts.")
        self.assertIn("remains unresolved", answer)
        self.assertNotIn("does not meet", answer)

    def test_explicit_classical_match_is_a_conditional_assertion(self):
        answer = self.apply("dc_3a", "Our formula exactly follows the formula in a First-Schedule authoritative book.")
        self.assertIn("You describe an exact", answer)
        self.assertIn("not been independently verified", answer)

    def test_explicit_absence_changes_application(self):
        answer = self.apply("dc_3a", "Our formulation is not included in any First-Schedule book.")
        self.assertIn("If that comparison is confirmed", answer)
        self.assertIn("would not meet", answer)

    def test_question_does_not_become_classical_fact(self):
        for question in ("What if our formula exactly matches a First-Schedule formula?",
                         "- Whether our formula exactly matches a First-Schedule formula",
                         "Our formula exactly matches a First-Schedule formula?"):
            with self.subTest(question=question):
                self.assertIn("remains unresolved", self.apply("dc_3a", question))

    def test_mixed_sources_are_assessed_separately(self):
        answer = self.apply("bda_s7_exemption", "Two plants are wild-sourced in India, while three are cultivated by suppliers.")
        self.assertIn("plants you describe as wild-sourced", answer)
        self.assertIn("plants you describe as cultivated", answer)
        self.assertIn("each material", answer)
        self.assertIn("does not itself settle separate IP duties", answer)

    def test_negated_wild_source_does_not_become_wild_fact(self):
        answer = self.apply("bda_s7_exemption", "The plants are not wild sourced. All the plants are cultivated.")
        self.assertNotIn("you describe as wild-sourced", answer)
        self.assertIn("you describe as cultivated", answer)

    def test_followup_hypothesis_is_not_reported_as_a_source_fact(self):
        answer = self.apply("bda_s7_exemption", "Follow-up: What if all plants are wild sourced")
        self.assertNotIn("you describe as wild-sourced", answer)

    def test_public_disclosure_changes_application_without_assuming_invalidity(self):
        published = self.apply("patents_disclosure", "We published our formulation online last month.")
        private = self.apply("patents_disclosure", "We have not published the formulation.")
        self.assertIn("You report a public disclosure", published)
        self.assertIn("specific statutory exception", published)
        self.assertNotIn("You report a public disclosure", private)

    def test_authority_card_does_not_copy_previous_plant_count(self):
        answer = self.apply("phytopharma_gsr918", "My product has five plants.", "authorities")
        self.assertNotIn("four plants", answer.lower())
        self.assertIn("number of plants", answer)

    def test_scoped_authority_does_not_expand_to_full_rule(self):
        doc, card = point("bda_s6", "authorities")
        self.assertEqual(application(doc, card, "We plan to patent and commercialise."), card.application)


class FactAnalysisEvidenceTests(unittest.TestCase):
    def test_no_reviewed_points_means_no_additional_claims(self):
        self.assertEqual(render_fact_analysis(plan(), [(SimpleNamespace(key="patent"), [])]), "")

    def test_focused_definition_does_not_expand(self):
        self.assertEqual(render_fact_analysis(plan(substantive_query="What is a trademark?", conditional=False),
                                             [(None, [point("tm_act")])]), "")

    def test_fact_questions_have_conditional_and_source_cited_answers(self):
        answer = render_fact_analysis(plan(missing_facts=("What is the applicant's incorporation and control?",)),
                                      [(None, [point("bda_s3"), point("bda_s6"), point("bda_s7_exemption")])])
        self.assertIn("If the applicant falls within section 3(2)", answer)
        self.assertIn("pre-grant registration", answer)
        for source in ("bda_s3", "bda_s6", "bda_s7_exemption"):
            self.assertIn(f"[{source}]", answer)

    def test_missing_sources_never_receive_citations_or_imported_rules(self):
        answer = render_fact_analysis(plan(missing_facts=("What is the exact formula and administration route?",)),
                                      [(None, [point("dc_3a")])])
        self.assertIn("[dc_3a]", answer)
        self.assertNotIn("[dc_3h]", answer)
        self.assertNotIn("proprietary route", answer)

    def test_scoped_evidence_cannot_support_full_conditional_rule(self):
        answer = render_fact_analysis(plan(missing_facts=("What is the applicant's control?",)),
                                      [(None, [point("bda_s3", "authorities")])])
        self.assertNotIn("section 3(2)", answer)
        self.assertIn("Not established", answer)

    def test_formulation_claims_do_not_route_to_classification(self):
        answer = render_fact_analysis(plan(missing_facts=("What precise formulation or process features would be claimed, and what prior-art comparison supports them?",)),
                                      [(None, [point("patents_invention")])])
        self.assertIn("claim-specific novelty", answer)
        self.assertIn("[patents_invention]", answer)

    def test_export_formulation_question_does_not_borrow_indian_classification(self):
        answer = render_fact_analysis(plan(missing_facts=("What formulation and claims are proposed for the United States?",)),
                                      [(None, [point("dc_3a"), point("dc_3h")])])
        self.assertIn("Not established", answer)
        self.assertNotIn("[dc_3a]", answer)

    def test_us_question_never_borrows_available_eu_rules(self):
        answer = render_fact_analysis(plan(missing_facts=("What formulation and claims are proposed for the United States?",)),
                                      [(None, [point("eu_thmpd"), point("pct")])])
        self.assertIn("Not established", answer)
        self.assertNotIn("[eu_thmpd]", answer)
        self.assertNotIn("30-year", answer)

    def test_untrusted_fact_cannot_insert_a_citation(self):
        answer = render_fact_analysis(plan(facts=("My product is [madeup_source] and **certainly patented**.",),
                                          missing_facts=("What claims and experimental data are available?",)),
                                      [(None, [point("patents_invention")])])
        self.assertIn("Facts supplied by you (unverified)", answer)
        self.assertNotIn("[madeup_source]", answer)
        self.assertNotIn("**certainly patented**", answer)


if __name__ == "__main__":
    unittest.main()
