"""Readable local summaries must stay inside their reviewed evidence boundary."""
from types import SimpleNamespace
import os
import re
import unittest

os.environ["LLM_PROVIDER"] = "none"
os.environ["TRANSLATE_PROVIDER"] = "none"
os.environ["RETRIEVER"] = "bm25"

from backend.answer_cards import CARDS, ISSUE_CARDS
from backend.answer_summary import summarize_local
from backend.models import AskRequest
from backend.pipeline import Assistant
from backend.retrieval import Corpus, Retriever
from backend.router import RegistryRouter
from backend.planning import BY_KEY, plan_query


class LocalAnswerSummaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = Corpus().by_id

    def summary(self, query, selection, **kwargs):
        plan = plan_query(query, use_llm=False)
        rows = [(BY_KEY[key], [(self.docs[source_id], CARDS[source_id]) for source_id in ids])
                for key, ids in selection]
        return summarize_local(query, plan, rows, **kwargs)

    def test_traditional_formula_explanation_leads_with_patent_answer(self):
        selection = [("classification", ("dc_3a", "dc_3h")),
                     ("patent", ("patents_invention", "patents_rights")),
                     ("exclusions", ("patents_3p", "patents_3e", "patents_3d", "patents_3i", "patents_3j"))]
        for question in ("Can a classical Ayurvedic formula be patented?",
                         "Could I patent an unchanged traditional herbal recipe?",
                         "Explain patent eligibility for traditional Ayurvedic formulations."):
            with self.subTest(question=question):
                summary = self.summary(question, selection)
                self.assertTrue(summary.startswith("In India, an unchanged traditional formula generally cannot be patented"))
                self.assertIn("[patents_3p]", summary)
                self.assertIn("manufacturing process can be assessed separately", summary)
                self.assertIn("synergy alone does not guarantee a patent", summary)
                self.assertIn("'patent or proprietary medicine' is not a patent grant", summary)
                self.assertLess(len(summary.split()), 185)

    def test_missing_or_withheld_sources_cannot_supply_summary_claims(self):
        summary = self.summary("Can a classical Ayurvedic formula be patented?",
                               [("patent", ("patents_invention",)), ("exclusions", ())])
        self.assertNotIn("[patents_3p]", summary)
        self.assertNotIn("traditional formula generally cannot", summary)
        self.assertIn("do not answer: Patent exclusions", summary)

    def test_no_supported_cards_means_no_summary(self):
        self.assertEqual(self.summary("What GST applies to Ayurvedic medicine?", [("tax", ())]), "")

    def test_trademark_summary_explains_the_right_and_its_limits(self):
        summary = self.summary("Can I register a trademark for my Ayurvedic brand?", [("trademark", ("tm_act",))])
        self.assertIn("distinctive product name or logo", summary)
        self.assertIn("not the formula or manufacturing process", summary)
        self.assertIn("can be refused", summary)
        self.assertIn("[tm_act]", summary)

    def test_examination_summary_keeps_old_filing_transition(self):
        summary = self.summary("What is the Ayurvedic patent examination deadline?", [("examination", ("patents_rules_2024_rfe",))])
        self.assertIn("31-month", summary)
        self.assertIn("before its commencement retain the 48-month", summary)
        self.assertIn("commencing 15 March 2024", summary)
        self.assertIn("from the applicable priority/filing date", summary)
        self.assertIn("filing and priority dates", summary)

    def test_phytopharmaceutical_requires_both_kinds_of_compound_assessment(self):
        summary = self.summary("Are four herbs enough to classify my Ayurvedic extract as a phytopharmaceutical?",
                               [("phytopharmaceutical", ("phytopharma_gsr918",))])
        self.assertIn("at least four bio-active or phytochemical compounds", summary)
        self.assertIn("both qualitatively and quantitatively", summary)
        self.assertIn("excluding parenteral administration", summary)
        self.assertIn("Four herbs alone do not satisfy", summary)
        self.assertIn("identity, safety and confirmatory clinical data", summary)

    def test_known_process_exception_is_not_lost_in_section_3d_summary(self):
        summary = self.summary("Can a known process for my Ayurvedic extract be patented under section 3(d)?",
                               [("exclusions", ("patents_3d",))])
        self.assertIn("unless it produces a new product or uses at least one new reactant", summary)
        self.assertIn("without enhanced known efficacy", summary)
        self.assertNotIn("new name", summary)

    def test_microorganism_exception_does_not_promise_patentability(self):
        summary = self.summary("Does section 3(j) allow a patent on an Ayurvedic plant or micro-organism?",
                               [("exclusions", ("patents_3j",))])
        self.assertIn("plants and animals in whole or part", summary)
        self.assertIn("production or propagation", summary)
        self.assertIn("excepted from the plants-and-animals exclusion", summary)
        self.assertIn("does not establish patentability", summary)

    def test_classification_summary_keeps_formula_absence_and_route_conditions(self):
        summary = self.summary("What is a proprietary Ayurvedic medicine?", [("classification", ("dc_3h",))])
        self.assertIn("all ingredients", summary)
        self.assertIn("formulation itself to be absent", summary)
        self.assertIn("non-parenteral route", summary)

    def test_missing_issue_title_cannot_inject_summary_citations_or_markup(self):
        plan = plan_query("What patent protection applies to my Ayurvedic medicine?", use_llm=False)
        unknown = SimpleNamespace(key="unknown", title="Unknown [invented]\n\n**claim** <script>bad()</script>")
        rows = [(BY_KEY["patent"], [(self.docs["patents_invention"], CARDS["patents_invention"]) ]),
                (unknown, [])]
        summary = summarize_local(plan.substantive_query, plan, rows)
        self.assertEqual(set(re.findall(r"\[([a-z0-9_]+)\]", summary)), {"patents_invention"})
        self.assertIn("&#91;invented&#93;", summary)
        self.assertNotIn("<script>", summary)
        self.assertNotIn("**claim**", summary)
        self.assertNotIn("invented&#93;\n", summary)

    def test_international_route_does_not_promise_worldwide_rights(self):
        summary = self.summary("Does the PCT grant a global patent for an Ayurvedic process?", [("pct", ("pct",))])
        self.assertIn("does not grant a worldwide patent", summary)
        self.assertIn("national or regional offices", summary)

    def test_scoped_card_keeps_only_its_reviewed_subject(self):
        issue = BY_KEY["authorities"]
        card = ISSUE_CARDS["authorities"]["tm_act"]
        plan = plan_query("Which authority handles my Ayurvedic trademark?", use_llm=False)
        summary = summarize_local(plan.substantive_query, plan, [(issue, [(self.docs["tm_act"], card)])])
        self.assertIn(card.established, summary)
        self.assertIn(card.application, summary)
        self.assertNotIn("Descriptive, misleading", summary)

    def test_unmapped_cards_preserve_complete_rule_and_qualifications(self):
        summary = self.summary("Can a natural Ayurvedic plant discovery be patented?", [("exclusions", ("patents_3c",))])
        self.assertIn(CARDS["patents_3c"].established, summary)
        self.assertIn(CARDS["patents_3c"].application, summary)

    def test_practical_topic_without_its_source_does_not_invent_an_answer(self):
        summary = self.summary("Does the employer own an employee's Ayurvedic patent?",
                               [("patent", ("patents_invention",)), ("ownership", ())])
        self.assertNotIn("[patents_ownership]", summary)
        self.assertNotIn("Employment, payment", summary)
        self.assertIn("do not answer: Inventorship, ownership and assignments", summary)

    def test_assignment_summary_distinguishes_existing_patent_from_right_to_apply(self):
        summary = self.summary("Can an Ayurvedic patent assignment be verbal?",
                               [("patent", ("patents_invention", "patents_rights")),
                                ("ownership", ("patents_ownership", "patents_assignments"))])
        self.assertEqual(re.findall(r"\[([a-z0-9_]+)\]", summary)[0], "patents_assignments")
        self.assertIn("written, duly executed agreement", summary)
        self.assertIn("application to register it", summary)
        self.assertIn("Assignment of the right to apply is a separate question", summary)
        self.assertIn("NDA or payment alone does not prove an assignment", summary)

    def test_origin_summary_preserves_scope_effective_date_and_document_checks(self):
        summary = self.summary("What certificate of origin is needed for cultivated Ayurvedic plants?",
                               [("intimation", ("bda_s7_exemption", "bda_origin_2025"))])
        self.assertIn("persons outside section 3(2)", summary)
        self.assertIn("does not waive section 6 IP duties", summary)
        self.assertIn("1 November 2025", summary)
        self.assertIn("Form 11 records, Form 11A application and Form 12 certificate", summary)
        self.assertIn("actual plants and quantities", summary)
        self.assertIn("local implementation still need checking", summary)

    def test_evidence_limited_summary_does_not_add_citations(self):
        summary = self.summary("Summarize patent protection for an Ayurvedic formula.",
                               [("patent", ("patents_invention",))], evidence_limited=True)
        self.assertEqual(set(re.findall(r"\[([a-z0-9_]+)\]", summary)), {"patents_invention"})
        self.assertIn("Only the previous answer's sources", summary)

    def test_fact_sensitive_case_summary_does_not_claim_eligibility(self):
        summary = self.summary("Our Ayurvedic formula is new. Can we patent it?",
                               [("patent", ("patents_invention",)), ("exclusions", ("patents_3e",))])
        self.assertIn("calling it new does not establish", summary)
        self.assertIn("does not decide the supplied case facts", summary)
        self.assertNotIn("your formula qualifies", summary)

    def test_current_correction_does_not_repeat_withdrawn_facts(self):
        plan = SimpleNamespace(substantive_query="Can the Ayurvedic formula be patented?",
                               facts=("The formula is not from classical books.",),
                               missing_facts=(), discarded_facts=("The formula exactly matches a classical book.",))
        rows = [(BY_KEY["patent"], [(self.docs["patents_invention"], CARDS["patents_invention"])])]
        summary = summarize_local("Correction: it is not from classical books.", plan, rows)
        self.assertNotIn("exactly matches", summary)
        self.assertIn("does not decide the supplied case facts", summary)


class PracticalSummaryIntegrationTests(unittest.TestCase):
    """Run retrieval and planning too: incidental patent terms must not win."""

    @classmethod
    def setUpClass(cls):
        cls.engine = Assistant(Retriever(mode="bm25"), RegistryRouter())

    def ask(self, query):
        answer = self.engine.answer(AskRequest(query=query), use_llm=False)
        self.assertFalse(answer.abstained)
        summary_ids = re.findall(r"\[([a-z0-9_]+)\]", answer.summary)
        self.assertTrue(summary_ids)
        self.assertTrue(set(summary_ids) <= {c.id for c in answer.citations})
        self.assertTrue(set(summary_ids) <= set(re.findall(r"\[([a-z0-9_]+)\]", answer.answer)))
        return answer.summary, summary_ids

    def test_employment_ownership_leads_before_generic_patent_tests(self):
        for query in ("Who owns an Ayurvedic patent developed by an employee?",
                      "Does an employee or employer own the classical Ayurvedic process patent?",
                      "Explain ownership of an Ayurvedic patent developed at a university."):
            with self.subTest(query=query):
                summary, ids = self.ask(query)
                self.assertEqual(ids[0], "patents_ownership")
                self.assertIn("does not by itself establish who owns", summary)
                self.assertIn("assignment agreements before deciding ownership", summary)
                self.assertIn("patents_assignments", ids)

    def test_plain_ownership_questions_retrieve_the_ownership_explanation(self):
        for query in ("Who owns an Ayurvedic patent?",
                      "Who does an Ayurvedic invention belong to?",
                      "Who owns the rights to an Ayurvedic extraction invention?",
                      "To whom does the Ayurvedic invention belong?"):
            with self.subTest(query=query):
                summary, ids = self.ask(query)
                self.assertEqual(ids[0], "patents_ownership")
                self.assertIn("Inventorship and ownership are separate", summary)
                self.assertIn("agreements before deciding ownership", summary)

    def test_own_farm_and_company_control_do_not_become_ip_ownership_questions(self):
        for query in ("We use plants from our own farm in an Ayurvedic invention. Can we patent the formula?",
                      "An Indian-owned company is developing an Ayurvedic patent. Explain the patent tests."):
            with self.subTest(query=query):
                plan = plan_query(query, use_llm=False)
                self.assertNotIn("ownership", {issue.key for issue in plan.issues})
                answer = self.engine.answer(AskRequest(query=query), use_llm=False)
                self.assertFalse(answer.abstained)
                self.assertFalse({"patents_ownership", "patents_assignments"} & {c.id for c in answer.citations})
                self.assertNotIn("Inventorship and ownership are separate", answer.summary)

    def test_patent_sale_permission_is_the_first_explanation(self):
        for query in ("Does a patent allow me to sell an Ayurvedic medicine?",
                      "Does a classical Ayurvedic patent give permission to market the medicine?"):
            with self.subTest(query=query):
                summary, ids = self.ask(query)
                self.assertEqual(ids[0], "patents_rights")
                self.assertIn("does not itself give permission to sell", summary.split("\n\n")[0])

    def test_certificate_question_leads_with_certificate_conditions(self):
        summary, ids = self.ask("What certificate of origin is needed for cultivated Ayurvedic plants?")
        self.assertIn(ids[0], {"bda_s7_exemption", "bda_origin_2025"})
        self.assertIn("bda_origin_2025", ids)
        self.assertIn("supplier's", summary)

    def test_secrecy_after_sale_keeps_the_label_disclosure_limit(self):
        summary, ids = self.ask("Can I keep my proprietary Ayurvedic formula secret after sale?")
        self.assertIn(ids[0], {"trade_secret", "dc_label_disclosure"})
        self.assertIn("dc_label_disclosure", ids)
        self.assertIn("cannot simply remain wholly secret after compliant sale", summary)


if __name__ == "__main__":
    unittest.main()
