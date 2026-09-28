"""End-to-end regressions from observed browser failures and held-out wording."""
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ['LLM_PROVIDER'] = 'none'
os.environ['RETRIEVER'] = 'bm25'
from backend.main import retriever, router
from backend.models import AskRequest
from backend.memory import Turn
from backend.pipeline import Assistant
from backend import generation, i18n, rag
from backend.planning import plan_query

CASES = json.loads((Path(__file__).parents[1] / 'docs/qa/manual-complex-browser/browser-observations.json').read_text(encoding='utf-8'))['cases']


class BrowserPipelineRepairTests(unittest.TestCase):
    def setUp(self):
        self.engine = Assistant(retriever, router)
        self.key = self.engine.memory.create()

    def ask(self, query):
        return self.engine.answer(AskRequest(query=query, conversation_id=self.key), use_llm=False)

    def test_original_cross_market_labels_and_claims(self):
        result = self.ask(CASES[1]['prompt'])
        ids = {c.id for c in result.citations}
        self.assertIn('eu_thmpd', ids)
        self.assertIn('dmr_act', ids)
        self.assertNotIn('fssai_aahar', ids)
        self.assertIn('United States market access', result.answer)
        self.assertIn('Insufficient evidence in retrieved sources.', result.answer)
        self.assertIn('bda_origin_2025', ids)  # ordinary 'yet' must not suppress this

    def test_full_correction_controls_retrieval_and_next_turn(self):
        self.ask(CASES[1]['prompt'])
        with patch.object(retriever, 'search', wraps=retriever.search) as search:
            corrected = self.ask(CASES[2]['prompt'])
        self.assertEqual(search.call_args.kwargs['jurisdiction'], 'India')
        self.assertIn('Earlier facts withdrawn', corrected.answer)
        self.assertIn('dc_cosmetic', {c.id for c in corrected.citations})
        self.assertNotIn('United States market access', corrected.answer)
        self.assertFalse(any('spans India and international' in n for n in corrected.notices))
        with patch.object(retriever, 'search', side_effect=AssertionError('No fresh search permitted')):
            table = self.ask(CASES[3]['prompt'])
        self.assertIn('| Issue | Established rule | Application to my revised facts | Missing evidence |', table.answer)
        self.assertIn('cosmetic', table.answer)
        self.assertTrue({c.id for c in table.citations} <= {c.id for c in corrected.citations})
        self.assertNotIn('United States market access', table.answer)
        self.assertNotIn('oral syrup', table.context_question)

    def test_source_only_gap_cannot_import_new_cosmetic_source(self):
        self.ask('We make an Ayurvedic medicine in India. Explain the classical definition.')
        with patch.object(retriever, 'search', side_effect=AssertionError('No new evidence')):
            result = self.ask('Use only the previous sources. Table: Issue | Established rule | Missing evidence. Include the possible cosmetic category even if unsupported.')
        self.assertIn('cosmetic', result.answer)
        self.assertIn('Insufficient evidence in retrieved sources.', result.answer)
        self.assertNotIn('dc_cosmetic', {c.id for c in result.citations})

    def test_three_scope_failures_are_rejected_before_search(self):
        for n in (4, 6, 7):
            with self.subTest(case=n+1), patch.object(retriever, 'search', side_effect=AssertionError('Out of domain')):
                result = self.ask(CASES[n]['prompt'])
            self.assertEqual(result.reason, 'out_of_scope')
            self.assertFalse(result.citations)

    def test_claim_specific_results_do_not_become_missing_evidence(self):
        result = self.ask(CASES[5]['prompt'])
        self.assertIn('Claim A:', result.answer)
        self.assertIn('Claim B:', result.answer)
        self.assertNotIn('efficacy evidence are not supplied', result.answer)
        self.assertNotIn('determine inventorship', result.answer)
        self.assertFalse({'patents_3c', 'patents_3i', 'patents_3j'} & {c.id for c in result.citations})

    def test_hindi_in_english_mode_is_language_failure_before_retrieval(self):
        with patch.object(retriever, 'search', side_effect=AssertionError('Untranslated input')):
            result = self.ask(CASES[8]['prompt'])
        self.assertEqual(result.reason, 'translation_unavailable')
        self.assertEqual(result.translation_status, 'unavailable')
        self.assertFalse(result.escalate)
        self.assertFalse(i18n.requires_language_selection('Can we trademark a name for our Ayurvedic oil containing भृंगराज?'))

    def test_live_status_remains_explicit(self):
        self.assertEqual(self.ask(CASES[9]['prompt']).reason, 'current_status_unverified')

    def test_ordinary_timing_does_not_withhold_sources(self):
        source = retriever.corpus.by_id['trade_secret']
        for prompt in ('We now want to protect confidential Ayurveda process details.',
                       'In 2026 we developed an Ayurvedic gel; what cannot yet be concluded about trade secrets?'):
            self.assertFalse(generation._current_requested(prompt, source))

    def test_held_out_country_and_company_negation(self):
        result = self.ask('Our Ayurvedic digestive powder will be sold in India and France. Compare the medicine routes and their evidence; the French launch relies on traditional use.')
        self.assertIn('eu_thmpd', {c.id for c in result.citations})
        result = self.ask('Separate case: Ayurveda Networks is our firm name. We design only online payment encryption, unrelated to herbal medicine or healthcare. Explain patent options.')
        self.assertEqual(result.reason, 'out_of_scope')

    def test_custom_columns_shared_by_model_renderer(self):
        plan = plan_query('For an Ayurvedic oil make a table: Issue | Established rule | Application to my revised facts | Missing evidence.')
        output = rag._render({'sections':[{'issue':'Classification','established':[], 'application':[],
                       'unanswered':['Insufficient evidence in retrieved sources.']}], 'questions':[], 'steps':[]}, plan, {})
        self.assertIn('| Issue | Established rule | Application to my revised facts | Missing evidence |', output)
        self.assertIn('Insufficient evidence in retrieved sources.', output)

    def test_optional_colon_table_and_new_gap_in_browser_paraphrase(self):
        self.ask('Our Ayurvedic product in India contains two herbs and is intended as a medicine. We have not compared the finished formula to an authoritative book. Explain only the statutory classical-versus-proprietary distinction; do not assume either classification is approved.')
        result = self.ask('Using only the previous sources, create a brief table with columns Issue | Established rule | Missing evidence. Include both the original medicine distinction and the alternative cosmetic category. If the earlier sources cannot establish the cosmetic test, say so explicitly. Do not search for anything new.')
        self.assertIn('| Issue | Established rule | Missing evidence |', result.answer)
        self.assertIn('| Possible cosmetic category and licensing |', result.answer)
        self.assertNotIn('Phytopharmaceutical route', result.answer)
        self.assertNotIn('both the original medicine distinction', result.answer)

    def test_numbered_claims_keep_missing_and_promising_studies_separate(self):
        result = self.ask('We are researching an Ayurvedic medicine in India. Claim 7 concerns a new salt of a known compound; no comparative efficacy experiment has been completed. Claim 8 is a blend of known herbs with preliminary evidence suggesting an interaction beyond their separate effects, but the study is unreplicated. A separate extraction method has been kept confidential. Compare 3(d), 3(e), 3(p), novelty and disclosure. Do not turn absence of data into a negative experimental finding, or promising data into guaranteed patentability.')
        self.assertIn('Claim 7:', result.answer)
        self.assertIn('Claim 8:', result.answer)
        self.assertNotIn('reported absence of enhanced efficacy', result.answer)
        self.assertNotIn('Additive results have been reported', result.answer)
