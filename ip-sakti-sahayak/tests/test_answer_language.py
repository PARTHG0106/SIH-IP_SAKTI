"""Answer-language selection must not assert the language of the question."""
from copy import deepcopy
import json
import os
import unittest
from unittest.mock import patch

os.environ["LLM_PROVIDER"] = "none"
os.environ["ALLOW_PROVIDER_FILE"] = "false"

from backend.models import AskRequest
from backend.pipeline import Assistant
from backend.planning import plan_query
from backend.retrieval import Retriever
from backend.router import RegistryRouter
from tests.test_translation_repair import response_for


ENGLISH_QUESTION = (
    "What biodiversity and traditional-knowledge issues should an Ayurvedic product "
    "developer consider for Indian patents and international patent filings?"
)
NATIVE_QUESTION = (
    "आयुर्वेदिक उत्पाद बनाने वाले को भारतीय पेटेंट और अंतरराष्ट्रीय पेटेंट आवेदन के लिए "
    "जैव विविधता और पारंपरिक ज्ञान से जुड़े किन मुद्दों पर ध्यान देना चाहिए?"
)
ROMANIZED_QUESTION = (
    "Ayurvedic product developer ko Indian patents aur international patent filings ke liye "
    "biodiversity aur traditional knowledge ke kin muddon par dhyan dena chahiye?"
)
MIXED_QUESTION = (
    "For an Ayurvedic product developer, भारतीय पेटेंट और अंतरराष्ट्रीय पेटेंट आवेदन में "
    "जैव विविधता और पारंपरिक ज्ञान के क्या नियम हैं?"
)


class AnswerLanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.retriever = Retriever(mode="bm25")

    def setUp(self):
        self.engine = Assistant(self.retriever, RegistryRouter())
        # Generation is a fixture here: the real retrieval and translation
        # boundaries are exercised without re-testing legal answer synthesis.
        self.english_detail = (
            "Indian patent applications involving biological resources can raise biodiversity obligations [bda_s6].\n\n"
            "A PCT filing is an international application route, not a worldwide patent [pct]."
        )
        self.english_summary = (
            "Assess biodiversity obligations separately from patentability and international filing choices [bda_s6] [pct]."
        )
        self.hindi_detail = (
            "जैविक संसाधनों से संबंधित भारतीय पेटेंट आवेदनों पर जैव विविधता संबंधी दायित्व लागू हो सकते हैं [bda_s6]।\n\n"
            "पीसीटी एक अंतरराष्ट्रीय आवेदन का मार्ग है, विश्वव्यापी पेटेंट नहीं [pct]।"
        )
        self.hindi_summary = (
            "जैव विविधता संबंधी दायित्वों का मूल्यांकन पेटेंट पात्रता और अंतरराष्ट्रीय आवेदन के विकल्पों से अलग करें [bda_s6] [pct]।"
        )
        self.translations = dict(zip(self.english_detail.split("\n\n"), self.hindi_detail.split("\n\n")))
        self.translations[self.english_summary] = self.hindi_summary
        self.generated = {
            "answer": self.english_detail, "summary": self.english_summary,
            "abstained": False, "escalate": False, "confidence": 0.9,
            "confidence_label": "High", "answer_source": "grounded_synthesis",
            "citations_used": [{"doc": self.retriever.corpus.by_id[source_id], "score": 0.9}
                               for source_id in ("bda_s6", "pct")],
            "as_of": None, "reason": None, "notices": [],
        }

    def answer_in_hindi(self, question, *, fail_output=None):
        payloads = []

        def translate(system, user, **kwargs):
            payload = json.loads(user)
            payloads.append(payload)
            self.assertEqual(payload["task"], "translate")
            if payload["target_language"] == "English":
                self.assertEqual(payload["source_language"], "auto")
                self.assertEqual(payload["segments"], [{"id": 0, "text": question}])
                return response_for(payload, lambda _: ENGLISH_QUESTION)
            self.assertEqual((payload["source_language"], payload["target_language"]), ("English", "Hindi"))
            kind = "summary" if payload["segments"][0]["text"] == self.english_summary else "detail"
            if kind == fail_output:
                # An apparently complete response with a missing citation must
                # restore both English fields, including an already translated detail.
                return response_for(payload, lambda text: self.translations[text].replace("[bda_s6]", ""))
            return response_for(payload, lambda text: self.translations[text])

        def local_plan(query, context=None, **kwargs):
            return plan_query(query, context, use_llm=False)

        with patch("backend.i18n.available", return_value=True), \
                patch("backend.pipeline.plan_query", side_effect=local_plan), \
                patch("backend.generation.generate", return_value=deepcopy(self.generated)) as generate, \
                patch.object(self.retriever, "search", wraps=self.retriever.search) as search, \
                patch("backend.llm.chat", side_effect=translate):
            response = self.engine.answer(AskRequest(query=question, lang="hi"))
        self.assertEqual(generate.call_args.args[0], ENGLISH_QUESTION)
        self.assertEqual(search.call_args.args[0], ENGLISH_QUESTION)
        self.assertEqual(search.call_args.kwargs["jurisdiction"], "Both")
        return response, payloads

    def test_english_question_with_hindi_answer_uses_unchanged_english_for_retrieval(self):
        response, payloads = self.answer_in_hindi(ENGLISH_QUESTION)
        self.assertFalse(response.abstained)
        self.assertEqual([p["target_language"] for p in payloads], ["English", "Hindi", "Hindi"])
        self.assertEqual((response.lang, response.requested_lang, response.translation_status),
                         ("hi", "hi", "translated"))
        self.assertEqual(response.answer, self.hindi_detail)
        self.assertEqual(response.summary, self.hindi_summary)
        self.assertEqual(response.original_answer_en, self.english_detail)
        self.assertEqual(response.original_summary_en, self.english_summary)
        self.assertEqual({c.id for c in response.citations}, {"bda_s6", "pct"})

    def test_native_romanized_and_mixed_questions_are_normalized_before_retrieval(self):
        for question in (NATIVE_QUESTION, ROMANIZED_QUESTION, MIXED_QUESTION):
            with self.subTest(question=question):
                response, payloads = self.answer_in_hindi(question)
                self.assertEqual(payloads[0]["segments"][0]["text"], question)
                self.assertEqual(response.answer, self.hindi_detail)
                self.assertEqual(response.summary, self.hindi_summary)
                self.assertEqual(response.translation_status, "translated")

    def test_offline_native_and_romanized_questions_do_not_reach_retrieval(self):
        questions = (NATIVE_QUESTION, "mujhe apne brand ka naam surakshit karna hai")
        for question in questions:
            with self.subTest(question=question), \
                    patch.object(self.retriever, "search", side_effect=AssertionError("Unnormalized question")), \
                    patch("backend.llm.chat", side_effect=AssertionError("Offline provider request")):
                response = self.engine.answer(AskRequest(query=question, lang="hi"), use_llm=False)
                self.assertTrue(response.abstained)
                self.assertEqual(response.reason, "translation_unavailable")
                self.assertEqual((response.lang, response.requested_lang), ("en", "hi"))
                self.assertFalse(response.citations)

    def test_rejected_normalization_does_not_bypass_checks_for_latin_script(self):
        for question in (ENGLISH_QUESTION, ROMANIZED_QUESTION):
            with self.subTest(question=question), \
                    patch("backend.i18n.available", return_value=True), \
                    patch("backend.llm.chat", return_value='{"complete":false}') as chat, \
                    patch.object(self.retriever, "search", side_effect=AssertionError("Unnormalized question")):
                response = self.engine.answer(AskRequest(query=question, lang="hi"))
                self.assertEqual(response.reason, "translation_unavailable")
                self.assertTrue(response.abstained)
                self.assertEqual(chat.call_count, 1)

    def test_hindi_output_failure_restores_full_english_answer_and_summary(self):
        for failure in ("detail", "summary"):
            with self.subTest(failure=failure):
                response, payloads = self.answer_in_hindi(ENGLISH_QUESTION, fail_output=failure)
                self.assertFalse(response.abstained)
                self.assertEqual(response.answer, self.english_detail)
                self.assertEqual(response.summary, self.english_summary)
                self.assertEqual((response.lang, response.requested_lang, response.translation_status),
                                 ("en", "hi", "output_failed"))
                self.assertIsNone(response.original_answer_en)
                self.assertIsNone(response.original_summary_en)
                self.assertEqual(len(payloads), 2 if failure == "detail" else 3)
                self.assertTrue(any("English answer is shown" in notice for notice in response.notices))


if __name__ == "__main__":
    unittest.main()
