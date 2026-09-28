"""Factual regressions from the browser review, including reworded countercases."""
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from backend.answer_cards import CARDS, ISSUE_CARDS
from backend.case_analysis import application, render_fact_analysis, unanswered


OBSERVATIONS = json.loads((Path(__file__).parents[1] / "docs/qa/manual-complex-browser/browser-observations.json").read_text(encoding="utf-8"))
PROMPTS = {case["id"]: case["prompt"] for case in OBSERVATIONS["cases"]}


def point(source_id, issue=None):
    return ({"id": source_id, "section": "reviewed provision"},
            ISSUE_CARDS[issue][source_id] if issue else CARDS[source_id])


def plan(**updates):
    data = dict(facts_query="", substantive_query="Give conditional outcomes", facts=(),
                missing_facts=(), conditional=True, concise=False, discarded_facts=())
    data.update(updates)
    return SimpleNamespace(**data)


class BrowserFactRepairTests(unittest.TestCase):
    def test_mixed_trade_fair_disclosure_preserves_both_material_sets(self):
        text = application(*point("patents_disclosure"), PROMPTS[1])
        self.assertIn("publicly showed the gel", text)
        self.assertIn("leaflet naming the ingredients", text)
        self.assertIn("did not disclose extraction temperatures or ratios", text)
        self.assertIn("do not assume", text)
        self.assertNotIn("Confirm whether any relevant information has already become public", text)

    def test_demonstration_inflections_and_event_prefaces(self):
        for description in ("At an exhibition we publicly demonstrated the Ayurvedic cream.",
                            "Six months ago we publicly displayed the herbal ointment.",
                            "At a trade fair we showed the Ayurvedic cream.",
                            "Our herbal process was disclosed publicly last year."):
            with self.subTest(description=description):
                text = application(*point("patents_disclosure"), description)
                self.assertIn("You report a public disclosure", text)
                self.assertIn("general grace period cannot be assumed", text)

    def test_negation_and_hypothesis_never_assert_public_disclosure(self):
        for description in ("We did not publicly demonstrate the gel.",
                            "We have not published our herbal process.",
                            "What if we publicly demonstrate the gel?",
                            "At a trade fair we did not show the cream."):
            with self.subTest(description=description):
                text = application(*point("patents_disclosure"), description)
                self.assertNotIn("You report a public disclosure", text)

    def test_claim_results_change_only_the_relevant_exclusion(self):
        salt = application(*point("patents_3d"), PROMPTS[6])
        mixture = application(*point("patents_3e"), PROMPTS[6])
        self.assertIn("Claim A:", salt)
        self.assertIn("tests show no enhancement", salt)
        self.assertIn("section 3(d) exclusion", salt)
        self.assertNotIn("Claim B", salt)
        self.assertIn("Claim B:", mixture)
        self.assertIn("sum of their known effects", mixture)
        self.assertIn("mere-admixture exclusion applies", mixture)
        self.assertNotIn("Claim A", mixture)
        self.assertNotIn("relevant efficacy evidence are not supplied", unanswered(*point("patents_3d"), PROMPTS[6]))

    def test_claim_labels_are_not_fixed_to_the_reported_example(self):
        facts = ("Claim X combines herbs; its effects are merely additive. "
                 "Claim Y is a new salt of a known active. Its efficacy remains unchanged.")
        self.assertIn("Claim X:", application(*point("patents_3e"), facts))
        self.assertNotIn("Claim Y:", application(*point("patents_3e"), facts))
        self.assertIn("Claim Y:", application(*point("patents_3d"), facts))
        self.assertNotIn("Claim X:", application(*point("patents_3d"), facts))

    def test_absence_of_data_does_not_become_negative_efficacy_or_additive_result(self):
        facts = ("Claim C is a new salt of a known active; no efficacy comparison has been performed. "
                 "Claim D mixes two herbs; there is no evidence yet of an interaction.")
        self.assertNotIn("falls within", application(*point("patents_3d"), facts))
        self.assertNotIn("exclusion applies", application(*point("patents_3e"), facts))

    def test_claim_b_results_are_not_assigned_to_claim_a(self):
        facts = ("Claim A is a new salt of a known active; studies are pending. "
                 "Claim B mixes two herbs; tests show no enhancement of known efficacy.")
        self.assertNotIn("falls within", application(*point("patents_3d"), facts))
        self.assertNotIn("exclusion applies", application(*point("patents_3e"), facts))

    def test_distinct_process_and_traditional_knowledge_questions_remain_open(self):
        process = application(*point("patents_invention"), PROMPTS[6])
        traditional = application(*point("patents_3p"), PROMPTS[6])
        self.assertIn("separate extraction process", process)
        self.assertIn("independently for novelty", process)
        self.assertIn("do not alone establish", traditional)
        self.assertIn("traditional knowledge", traditional)

    def test_company_ownership_is_supplied_but_not_equated_to_statutory_status(self):
        text = application(*point("bda_s3"), PROMPTS[3])
        unknown = unanswered(*point("bda_s3"), PROMPTS[3])
        self.assertIn("wholly Indian-owned", text)
        self.assertIn("actual applicant", text)
        self.assertIn("does not settle", text)
        self.assertIn("have been supplied", unknown)
        self.assertNotIn("are not supplied", unknown)

    def test_own_farm_assertion_does_not_establish_certificate(self):
        text = application(*point("bda_s7_exemption"), "All medicinal plants are grown on our own farm.")
        self.assertIn("plants you describe as cultivated", text)
        self.assertIn("prescribed BMC certificate", text)

    def test_contributor_question_never_uses_novelty_as_ownership_authority(self):
        answer = render_fact_analysis(plan(facts_query=PROMPTS[1], missing_facts=(
            "Who contributed each inventive or creative feature, and what employment, university, funding and assignment agreements govern those contributions?",)),
            [(None, [point("patents_invention"), point("patents_3p"), point("bda_s3")])])
        self.assertIn("Insufficient evidence", answer)
        self.assertIn("stated contributors", answer)
        self.assertNotIn("[patents_invention]", answer)
        self.assertNotIn("[bda_s3]", answer)

    def test_claim_application_requires_available_full_reviewed_source(self):
        answer = render_fact_analysis(plan(facts_query=PROMPTS[6], missing_facts=(
            "What experimental evidence supports the patent claims?",)),
            [(None, [point("patents_invention")])])
        self.assertNotIn("[patents_3d]", answer)
        self.assertNotIn("section 3(d)", answer)
        self.assertNotIn("mere-admixture exclusion", answer)

    def test_correction_lists_discarded_and_current_facts_even_when_concise(self):
        answer = render_fact_analysis(plan(substantive_query="First list discarded facts then be concise.",
            discarded_facts=("Our syrup uses tulsi.", "Our company has a German shareholder."),
            facts=("We now make an India-only hair oil.",), concise=True),
            [(None, [point("bda_s3")])])
        self.assertLess(answer.index("Earlier facts withdrawn"), answer.index("Facts supplied by you"))
        self.assertIn("German shareholder", answer)
        self.assertIn("India-only hair oil", answer)

    def test_technical_contribution_question_does_not_become_ownership(self):
        question = ("What precise formulation or process features would be claimed, and what prior-art "
                    "comparison and experimental data support the claimed technical contribution?")
        answer = render_fact_analysis(plan(facts_query=PROMPTS[6], missing_facts=(question,)),
            [(None, [point("patents_invention"), point("patents_3d"), point("patents_ownership")])])
        self.assertIn("claim-specific novelty", answer)
        self.assertIn("[patents_3d]", answer)
        self.assertNotIn("[patents_ownership]", answer)
        self.assertNotIn("assignment documents", answer)

    def test_reviewed_ownership_sources_support_only_their_distinct_questions(self):
        answer = render_fact_analysis(plan(facts_query=PROMPTS[1], missing_facts=(
            "Who contributed each inventive feature and what assignments cover it?",)),
            [(None, [point("patents_ownership"), point("patents_assignments"), point("patents_invention")])])
        self.assertIn("[patents_ownership]", answer)
        self.assertIn("[patents_assignments]", answer)
        self.assertIn("company's claimed title remains unresolved", answer)
        self.assertIn("mention as inventor does not itself confer patent rights", answer)
        self.assertIn("existing patent", answer)
        self.assertNotIn("[patents_invention]", answer)

    def test_missing_assignment_source_is_not_borrowed_from_ownership_source(self):
        answer = render_fact_analysis(plan(missing_facts=("What ownership and assignments apply?",)),
            [(None, [point("patents_ownership")])])
        self.assertIn("[patents_ownership]", answer)
        self.assertNotIn("[patents_assignments]", answer)
        self.assertNotIn("duly executed instrument", answer)

    def test_cosmetic_application_uses_revised_claim_without_certifying_category(self):
        result = application(*point("dc_cosmetic"), PROMPTS[3])
        self.assertIn("hair conditioning", result)
        self.assertIn("cosmetic classification is possible if", result)
        self.assertIn("alone do not prove", result)
        self.assertIn("review the complete formulation", result)

    def test_supplied_farm_sourcing_is_acknowledged_in_full_and_scoped_forms(self):
        for issue in (None, "sourcing"):
            with self.subTest(issue=issue):
                result = application(*point("bda_ipr_forms", issue), PROMPTS[3])
                missing = unanswered(*point("bda_ipr_forms", issue), PROMPTS[3])
                self.assertIn("grown on our own farm", result)
                self.assertNotIn("Foreign sourcing needs a separate", result)
                self.assertIn("Sourcing facts have been supplied", missing)
                self.assertNotIn("actual sourcing country, intended use", missing)
                if issue:
                    self.assertNotIn("commercialisation form", result)

    def test_eu_history_and_claim_gaps_apply_to_the_reported_evidence(self):
        result = application(*point("eu_thmpd"), PROMPTS[2])
        missing = unanswered(*point("eu_thmpd"), PROMPTS[2])
        self.assertIn("not fixed dosage, proved a history", result)
        self.assertIn("does not establish the cited 30-year", result)
        self.assertIn("cures bronchitis", result)
        self.assertIn("does not establish whether that specific claim", result)
        self.assertIn("proposed disease claim", missing)
        self.assertNotIn("FDA approval", result)

    def test_format_request_is_not_quoted_as_a_cosmetic_product_fact(self):
        facts = PROMPTS[3] + "\n" + PROMPTS[4]
        result = application(*point("dc_cosmetic"), facts)
        self.assertIn("hair conditioning", result)
        self.assertNotIn("Include the possible cosmetic category", result)
        self.assertNotIn("Make a short table", result)
        self.assertNotIn("Use ONLY the sources", result)

    def test_bulleted_requests_and_hypotheses_are_not_product_facts(self):
        for instruction in ("- Include a cosmetic category even if unsupported.",
                            "Suppose our intended use is only hair conditioning.",
                            "Assuming this is an externally applied cosmetic, explain licensing."):
            with self.subTest(instruction=instruction):
                result = application(*point("dc_cosmetic"), instruction)
                self.assertNotIn("Your stated product/use facts", result)

    def test_dmr_applies_supplied_wording_without_deciding_its_legality(self):
        result = application(*point("dmr_act"), PROMPTS[2])
        missing = unanswered(*point("dmr_act"), PROMPTS[2])
        self.assertIn("cures bronchitis", result)
        self.assertIn("wording has been supplied", result)
        self.assertIn("does not establish that the particular indication is prohibited", result)
        self.assertIn("claim wording is supplied", missing)
        self.assertIn("indication-specific", missing)
        self.assertIn("current applicable advertising", missing)

    def test_numbered_claims_preserve_absent_and_promising_studies_separately(self):
        facts = ("We are researching an Ayurvedic medicine in India. Claim 7 concerns a new salt "
                 "of a known compound; no comparative efficacy experiment has been completed. "
                 "Claim 8 is a blend of known herbs with preliminary evidence suggesting an "
                 "interaction beyond their separate effects, but the study is unreplicated. "
                 "A separate extraction method has been kept confidential.")
        salt = application(*point("patents_3d"), facts)
        blend = application(*point("patents_3e"), facts)
        self.assertIn("Claim 7:", salt)
        self.assertIn("not a finding of no enhancement", salt)
        self.assertNotIn("Claim 8", salt)
        self.assertNotIn("falls within", salt)
        self.assertIn("Claim 8:", blend)
        self.assertIn("study is unreplicated", blend)
        self.assertIn("not established synergy or guaranteed patentability", blend)
        self.assertNotIn("Claim 7", blend)
        self.assertNotIn("extraction method", blend)
        self.assertIn("study status have been supplied", unanswered(*point("patents_3d"), facts))
        self.assertIn("reported study status are supplied", unanswered(*point("patents_3e"), facts))

    def test_positive_efficacy_is_relevant_but_not_a_patent_guarantee(self):
        facts = ("Claim R is a new salt of a known substance. Our preliminary results show "
                 "enhanced known efficacy, but the study is unreplicated.")
        result = application(*point("patents_3d"), facts)
        self.assertIn("Claim R:", result)
        self.assertIn("reported efficacy improvement", result)
        self.assertIn("does not itself establish", result)
        self.assertNotIn("reported absence", result)

    def test_no_interaction_study_does_not_become_reported_interaction(self):
        facts = ("Claim 3 is a mixture of known herbs. No evidence yet shows an interaction beyond "
                 "their separate effects.")
        result = application(*point("patents_3e"), facts)
        self.assertIn("Missing or incomplete comparative evidence", result)
        self.assertNotIn("The reported interaction", result)
        self.assertNotIn("mere-admixture exclusion applies", result)

    def test_undocumented_or_unknown_member_state_history_remains_unproved(self):
        for facts in ("The French distributor calls our Ayurveda product a traditional herbal medicine, "
                      "although its medicinal-use history is undocumented and dose undecided.",
                      "Our product's medicinal-use history in France is unknown."):
            with self.subTest(facts=facts):
                result = application(*point("eu_thmpd"), facts)
                self.assertIn("does not establish the cited 30-year", result)
                self.assertIn("Unproved history is not proof", result)
                self.assertNotIn("German", result)

    def test_classical_book_match_does_not_override_nonmedicinal_use(self):
        facts = ("Our Ayurvedic hair oil formula exactly follows a First-Schedule authoritative book. "
                 "The only claim is hair conditioning; there is no disease-treatment claim.")
        classical = application(*point("dc_3a"), facts)
        proprietary = application(*point("dc_3h"), facts)
        self.assertIn("medicinal intended use", classical)
        self.assertIn("formula match alone does not establish", classical)
        self.assertIn("does not establish this medicinal threshold", classical)
        self.assertIn("If the medicinal-use threshold is met", classical)
        self.assertIn("actual intended use", proprietary)
        self.assertIn("does not classify a nonmedicinal product", proprietary)

    def test_medicinal_classical_facts_still_receive_conditional_classical_route(self):
        facts = ("Our Ayurvedic medicine is intended to treat a disorder. Its formula exactly "
                 "follows an authoritative First-Schedule book.")
        result = application(*point("dc_3a"), facts)
        self.assertIn("classical route may fit", result)
        self.assertIn("medicinal-use threshold", result)
        self.assertNotIn("conditioning/cosmetic-purpose", result)

    def test_classification_branches_keep_medicinal_threshold_and_source_boundary(self):
        case = plan(facts_query=PROMPTS[3], missing_facts=("What is the correct formula classification?",))
        only_medicine = render_fact_analysis(case, [(None, [point("dc_3a"), point("dc_3h")])])
        self.assertIn("medicinal intended use", only_medicine)
        self.assertNotIn("[dc_cosmetic]", only_medicine)
        with_cosmetic = render_fact_analysis(case, [(None, [point("dc_3a"), point("dc_3h"), point("dc_cosmetic")])])
        self.assertIn("[dc_cosmetic]", with_cosmetic)
        self.assertIn("cosmetic classification is possible if", with_cosmetic)
        self.assertIn("medicinal intended use", with_cosmetic)


if __name__ == "__main__":
    unittest.main()
