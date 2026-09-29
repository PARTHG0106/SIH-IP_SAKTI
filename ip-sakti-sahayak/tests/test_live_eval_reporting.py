"""Keep provider outages and local fallbacks out of live-quality pass counts."""
import unittest

from scripts.live_provider_eval import assess_case, summarize


class LiveEvalReportingTests(unittest.TestCase):
    def entry(self, source="rag_synthesis", number=6):
        return {"id": number, "http_status": 200,
                "response": {"answer_source": source, "abstained": False,
                             "answer": "A sourced statement [pat_3d]", "citations": [{"id": "pat_3d"}]},
                "provider_events": [{"stage": stage, "ok": True} for stage in ("synthesis", "audit")]}

    def test_http_200_local_fallback_is_not_a_live_pass(self):
        entry = self.entry("grounded_synthesis")
        entry["provider_events"] = [{"stage": "synthesis", "ok": False}]
        entry["passed"] = all(assess_case(entry).values())
        report = summarize({"cases": [entry]})
        self.assertFalse(entry["passed"])
        self.assertEqual(report["validated_live_answers"], 0)
        self.assertEqual(report["local_fallback_answers"], 1)
        self.assertEqual(report["provider_failures"], 1)

    def test_live_english_answer_does_not_pass_hindi_case(self):
        entry = self.entry(number=9)
        entry["response"].update(translation_status="output_failed", lang="en")
        self.assertFalse(assess_case(entry)["hindi_translation_completed"])

    def test_source_only_live_answer_cannot_add_a_citation(self):
        entry = self.entry(number=14)
        entry["response"]["evidence_scope"] = "previous_turn"
        checks = assess_case(entry, {"citations": [{"id": "dc_3a"}]})
        self.assertTrue(checks["validated_live_synthesis"])
        self.assertFalse(checks["source_only_citations_within_snapshot"])

    def test_scope_guard_passes_without_paying_for_a_model(self):
        entry = self.entry("abstain", number=5)
        entry["response"]["reason"] = "out_of_scope"
        entry["provider_events"] = []
        self.assertTrue(all(assess_case(entry).values()))


if __name__ == "__main__":
    unittest.main()
