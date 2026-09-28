"""Protect the identity and fail-closed use of newly reviewed legal sources."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import unittest

os.environ["LLM_PROVIDER"] = "none"
os.environ["RETRIEVER"] = "bm25"

from backend.generation import _card
from backend.main import assistant
from backend.models import AskRequest
from backend.sources import validate_source


ROOT = Path(__file__).resolve().parent.parent
NEW_SOURCES = {
    "patents_ownership": ("patents-act.pdf", "2005-01-01"),
    "patents_assignments": ("patents-act.pdf", "2005-01-01"),
    "dc_cosmetic": ("dc-act-2016.pdf", "2016-12-31"),
    "dc_cosmetic_licensing": ("cosmetics-rules-2020.pdf", "2020-12-15"),
}


class SourceCoverageRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = {
            doc["id"]: validate_source(doc)
            for doc in (
                json.loads(line)
                for line in (ROOT / "corpus/corpus.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        }
        manifest = json.loads((ROOT / "corpus/primary/manifest.json").read_text(encoding="utf-8"))
        cls.archives = {entry["file"]: entry for entry in manifest["documents"]}

    def test_new_primary_sources_have_matching_reviewed_archives(self):
        for source_id, (filename, source_date) in NEW_SOURCES.items():
            with self.subTest(source_id=source_id):
                doc = self.docs[source_id]
                archive = self.archives[filename]
                data = (ROOT / "corpus/primary" / filename).read_bytes()
                self.assertTrue(data.startswith(b"%PDF-"))
                self.assertEqual(hashlib.sha256(data).hexdigest(), archive["sha256"])
                self.assertEqual(len(data), archive["bytes"])
                self.assertIn(source_id, archive["source_ids"])
                self.assertEqual(doc["source_url"], archive["source_url"])
                self.assertEqual(doc["as_of"], source_date)
                self.assertEqual(doc["review_status"], "primary_checked")
                self.assertEqual(doc["reviewed_on"], "2026-09-28")

    def test_new_legal_cards_are_available_only_for_reviewed_source_content(self):
        for source_id in NEW_SOURCES:
            with self.subTest(source_id=source_id):
                doc = self.docs[source_id]
                self.assertIsNotNone(_card(doc))
                self.assertIsNone(_card({**doc, "text": doc["text"] + " No licence is required."}))
                self.assertIsNone(_card({**doc, "source_url": "https://example.com/replacement"}))

    def test_cosmetic_authority_card_is_bound_to_the_same_reviewed_gazette(self):
        doc = self.docs["dc_cosmetic_licensing"]
        card = _card(doc, "authorities")
        self.assertIsNotNone(card)
        self.assertIn("State Licensing Authority", card.established)
        self.assertIsNone(_card({**doc, "section": "r.999"}, "authorities"))

    def test_book_formula_match_does_not_override_nonmedicinal_intended_use(self):
        result = assistant.answer(AskRequest(query=(
            "Our Ayurvedic hair oil in India exactly matches a classical formula in an "
            "authoritative book. Its only intended purpose is hair conditioning and appearance; "
            "there is no disease-treatment claim. Compare the classical, proprietary and "
            "cosmetic categories. Does the book-formula match alone establish classical medicine?"
        )), use_llm=False)
        self.assertFalse(result.abstained)
        self.assertTrue({"dc_3a", "dc_3h", "dc_cosmetic"} <= {c.id for c in result.citations})
        self.assertIn("diagnosis, treatment, mitigation or prevention", result.answer)
        self.assertIn("A formula match alone does not establish that use", result.answer)
        self.assertIn("ingredient-book match alone does not classify a nonmedicinal product", result.answer)


if __name__ == "__main__":
    unittest.main()
