"""Regression scenarios for multipart answers and ephemeral source-bound chats."""
import copy
import os
import re
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

os.environ["LLM_PROVIDER"] = "none"
os.environ["RETRIEVER"] = "bm25"

from fastapi.testclient import TestClient
from backend.main import app, assistant, retriever
from backend.config import settings
from backend.memory import ConversationStore, MemoryError, Turn, needs_history, source_only
from backend.models import AskRequest
from backend.pipeline import Assistant
from backend.router import RegistryRouter


ORIGINAL = """I am planning to launch an Ayurvedic proprietary medicine in India containing
Ashwagandha and three other medicinal plants. The exact combination, extraction technique,
dosage, and manufacturing process were developed by my company and are not disclosed in
classical Ayurvedic texts. Before commercializing it, give me a step-by-step IP and regulatory
strategy for India. Determine whether it qualifies as classical or proprietary under the Drugs
and Cosmetics Act. Which aspects could be patented and which Patents Act exclusions apply?
Should the formulation/process be a trade secret and what must remain confidential before filing?
What can and cannot trademark protection cover? Are copyright, GI, plant-variety protection or
other IP mechanisms relevant? Does the Biological Diversity Act apply to Indian medicinal plants?
Distinguish sections 3, 6 and 7, applicant status, sourcing, Access and Benefit Sharing, certificates
and origin records. Identify IP India, CDSCO/AYUSH authorities and the National Biodiversity
Authority and their roles. Create a decision table with columns:
Issue | Potential protection/approval | Applicable law | Eligibility/trigger | What I should do | Primary source.
Use authoritative primary or government sources. Distinguish established law, inference and
what requires professional confirmation. Do not invent unsupported requirements."""

FOLLOWUP = """Based ONLY on the sources you retrieved for my previous question, answer directly.
Create a table with: Issue | What the retrieved sources establish | Relevant section |
How it applies to my case | What remains unanswered.
Include every issue in my original question even when sources contain no evidence.
Write "Insufficient evidence in retrieved sources." for missing evidence.
After the table provide a short step-by-step strategy using supported conclusions only.
Separate Established by source, Inference/application, Not established by retrieved sources.
Do not merely reproduce excerpts."""


class MemoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.store = ConversationStore(ttl=10, max_sessions=2, clock=lambda: self.now)

    def test_ttl_rejects_expired_ids_instead_of_recreating_them(self):
        key = self.store.create()
        self.now = 11
        with self.assertRaises(MemoryError) as error:
            with self.store.transaction(key, ("India", None, None)):
                pass
        self.assertEqual(error.exception.reason, "chat_expired")

    def test_cap_eviction_and_scope_boundaries(self):
        first, second, third = [self.store.create() for _ in range(3)]
        with self.assertRaises(MemoryError):
            with self.store.transaction(first, ("India", None, None)):
                pass
        with self.store.transaction(second, ("India", None, None)):
            pass
        with self.assertRaises(MemoryError) as error:
            with self.store.transaction(second, ("International", None, None)):
                pass
        self.assertEqual(error.exception.reason, "chat_scope_changed")
        self.assertNotEqual(second, third)

    def test_concurrent_requests_do_not_reorder_history(self):
        key = self.store.create()
        with self.store.transaction(key, ("India", None, None)):
            with self.assertRaises(MemoryError) as error:
                with self.store.transaction(key, ("India", None, None)):
                    pass
        self.assertEqual(error.exception.reason, "chat_busy")

    def test_clear_during_request_cannot_restore_deleted_memory(self):
        key = self.store.create()
        with self.store.transaction(key, ("India", None, None)) as chat:
            self.store.delete(key)
            with self.assertRaises(MemoryError):
                self.store.append(chat, Turn("q", "q", [], "v1", 0))

    def test_turns_are_bounded_and_source_snapshots_are_copied(self):
        key = self.store.create()
        sources = [{"doc": {"text": "original"}}]
        with self.store.transaction(key, ("India", None, None)) as chat:
            for i in range(12):
                self.store.append(chat, Turn(str(i), "original question", sources, "v1", 0.9))
            sources[0]["doc"]["text"] = "changed"
            self.assertEqual(len(chat.turns), 8)
            self.assertEqual(chat.turns[0].query, "4")
            self.assertEqual(chat.turns[-1].sources[0]["doc"]["text"], "original")

    def test_references_do_not_block_standalone_product_questions(self):
        self.assertFalse(needs_history("How do I patent my product?"))
        self.assertTrue(needs_history(FOLLOWUP))
        self.assertTrue(source_only("Use only those sources; do not search again."))
        self.assertTrue(source_only("Based solely on the earlier sources, summarize."))
        self.assertTrue(source_only("Use the same sources to make a table."))
        self.assertFalse(source_only("Use the earlier sources and find additional sources."))
        self.assertFalse(source_only("Use only government sources to explain trademarks."))


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.engine = Assistant(retriever, RegistryRouter())
        self.key = self.engine.memory.create()

    def ask(self, query, **kwargs):
        return self.engine.answer(AskRequest(query=query, conversation_id=self.key, **kwargs), use_llm=False)

    def test_full_question_covers_requested_issues_with_decision_table(self):
        result = self.ask(ORIGINAL)
        self.assertFalse(result.abstained)
        self.assertIn("| Issue |", result.answer)
        self.assertIn("Potential protection/approval", result.answer)
        for word in ("classical", "proprietary", "patent", "trade secret", "trademark", "copyright", "geographical", "variet", "biodiversity", "benefit", "CDSCO"):
            with self.subTest(issue=word):
                self.assertIn(word.lower(), result.answer.lower())
        self.assertIn("Established by source", result.answer)
        self.assertIn("Inference/application", result.answer)
        self.assertIn("Not established by retrieved sources", result.answer)
        self.assertGreater(len(result.citations), 3)
        self.assertTrue({
            "dc_3a", "dc_3h", "patents_invention", "patents_3c", "patents_3p", "patents_3e",
            "trade_secret", "tm_act", "copyright_act", "gi_act", "ppvfr_act",
            "bda_s3", "bda_s6", "bda_s7_exemption", "bda_abs", "dc_licensing",
        } <= {c.id for c in result.citations}, "Each core requested issue needs its available reviewed evidence")
        self.assertNotIn("patents_rules_2024_form27", {c.id for c in result.citations})
        markers = set(re.findall(r"\[([a-z][a-z0-9_]+)\]", result.answer))
        self.assertTrue(markers <= {c.id for c in result.citations})

    def test_source_only_followup_never_searches_or_adds_sources(self):
        first = self.ask(ORIGINAL)
        with patch.object(retriever, "search", side_effect=AssertionError("Source-only followups must not retrieve")):
            second = self.ask(FOLLOWUP)
        self.assertFalse(second.abstained)
        self.assertTrue(second.memory_used)
        self.assertEqual(second.evidence_scope, "previous_turn")
        self.assertEqual(second.corpus_version, first.corpus_version)
        self.assertTrue({c.id for c in second.citations} <= {c.id for c in first.citations})
        for column in ("What the retrieved sources establish", "Relevant section", "How it applies to my case", "What remains unanswered"):
            self.assertIn(column, second.answer)
        self.assertNotIn("patents_rules_2024_form27", {c.id for c in second.citations})

    def test_legacy_three_source_followup_keeps_all_issues_and_shows_gaps(self):
        ids = ("bda_s7_exemption", "bda_s6", "ppvfr_act")
        sources = [{"doc": copy.deepcopy(retriever.corpus.by_id[key]), "score": 1, "bm25": 1} for key in ids]
        with self.engine.memory.transaction(self.key, ("India", None, None)) as chat:
            self.engine.memory.append(chat, Turn(ORIGINAL, ORIGINAL, sources, "legacy-corpus", 0.9))
        with patch.object(retriever, "search", side_effect=AssertionError("No new sources")):
            answer = self.ask(FOLLOWUP)
        self.assertEqual(answer.corpus_version, "legacy-corpus")
        self.assertGreaterEqual(answer.answer.count("Insufficient evidence in retrieved sources."), 5)
        self.assertTrue({c.id for c in answer.citations} <= set(ids))
        for issue in ("copyright", "trademark", "trade secret", "classical"):
            self.assertIn(issue, answer.answer.lower())

    def test_missing_context_is_explicit_not_a_random_source_search(self):
        with patch.object(retriever, "search", side_effect=AssertionError("No ungrounded followup search")):
            answer = self.ask(FOLLOWUP)
        self.assertTrue(answer.abstained)
        self.assertEqual(answer.reason, "missing_chat_context")
        self.assertFalse(answer.citations)

    def test_empty_prior_evidence_still_preserves_requested_gap_table(self):
        with self.engine.memory.transaction(self.key, ("India", None, None)) as chat:
            self.engine.memory.append(chat, Turn(ORIGINAL, ORIGINAL, [], "empty-snapshot", 0))
        with patch.object(retriever, "search", side_effect=AssertionError("No new search")):
            answer = self.ask(FOLLOWUP)
        self.assertIn("| Issue |", answer.answer)
        self.assertIn("What remains unanswered", answer.answer)
        self.assertGreaterEqual(answer.answer.count("Insufficient evidence in retrieved sources."), 10)
        self.assertFalse(answer.citations)
        self.assertEqual(answer.corpus_version, "empty-snapshot")

    def test_new_chat_has_no_access_to_another_chats_sources(self):
        self.ask(ORIGINAL)
        different = self.engine.memory.create()
        answer = self.engine.answer(AskRequest(query=FOLLOWUP, conversation_id=different), use_llm=False)
        self.assertEqual(answer.reason, "missing_chat_context")

    def test_focused_followup_does_not_repeat_full_strategy(self):
        self.ask(ORIGINAL)
        result = self.ask("What about trademark protection for my product name?")
        self.assertTrue(result.memory_used)
        self.assertIn("trademark", result.answer.lower())
        self.assertNotIn("patents_rules_2024_form27", {c.id for c in result.citations})
        self.assertNotIn("bda_s7_exemption", {c.id for c in result.citations})

    def test_independent_new_question_does_not_inherit_old_issues(self):
        self.ask(ORIGINAL)
        result = self.ask("How often must I file Form 27?")
        self.assertFalse(result.memory_used)
        self.assertEqual([c.id for c in result.citations], ["patents_rules_2024_form27"])

    def test_concise_followup_is_shorter_and_keeps_the_source_boundary(self):
        first = self.ask("How often must I file Form 27?")
        second = self.ask("Use the same sources. Make it shorter.")
        self.assertFalse(second.abstained)
        self.assertLess(len(second.answer), len(first.answer))
        self.assertIn("three financial years", second.answer)
        self.assertEqual([c.id for c in second.citations], ["patents_rules_2024_form27"])

    def test_mixed_question_preserves_unsupported_issue_as_a_gap(self):
        result = self.ask("Explain trademark protection and GST tax obligations for my medicine. Create a table.")
        self.assertFalse(result.abstained)
        self.assertIn("trademark", result.answer.lower())
        self.assertIn("GST", result.answer)
        self.assertIn("Insufficient evidence in retrieved sources.", result.answer)


class ChatApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.audit = patch.object(settings, "audit_log_path", Path(self.temp.name) / "audit.jsonl")
        self.audit.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.audit.stop()
        self.temp.cleanup()

    def test_create_ask_clear_expiry_and_privacy(self):
        created = self.client.post("/api/chat").json()
        key = created["conversation_id"]
        self.assertGreaterEqual(len(key), 32)
        response = self.client.post("/api/ask", json={"query": "What is Form 27?", "conversation_id": key})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["conversation_id"], key)
        self.assertEqual(self.client.delete("/api/chat/" + key).status_code, 200)
        expired = self.client.post("/api/ask", json={"query": FOLLOWUP, "conversation_id": key})
        self.assertEqual(expired.status_code, 410)
        self.assertEqual(expired.json()["detail"]["reason"], "chat_expired")
        log = (Path(self.temp.name) / "audit.jsonl").read_text()
        self.assertNotIn("What is Form 27?", log)
        self.assertNotIn(key, log)

    def test_scope_change_cannot_reuse_evidence(self):
        key = self.client.post("/api/chat").json()["conversation_id"]
        self.client.post("/api/ask", json={"query": "What is Form 27?", "conversation_id": key})
        response = self.client.post("/api/ask", json={"query": "What is PCT?", "jurisdiction": "International", "conversation_id": key})
        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()
