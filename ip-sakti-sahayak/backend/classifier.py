"""Deterministic preliminary routing, with confirmation of legal facts."""
from __future__ import annotations

import re
import yaml
from .config import settings


class Classifier:
    def __init__(self, rules_path=None):
        with open(rules_path or settings.classifier_rules_path, encoding="utf-8") as f:
            self.rules = yaml.safe_load(f)
        self.nodes = self.rules["nodes"]
        self.categories = self.rules["categories"]
        self.start = self.rules["start"]

    def _node_payload(self, node_id):
        node = self.nodes[node_id]
        return {"node": node_id, "question": node["question"], "hint": node.get("hint", ""),
                "options": list(node["options"]), "option_labels": node.get("option_labels", {}),
                "statutes": node.get("statutes", [])}

    def classify(self, answers: dict[str, str], description: str | None = None) -> dict:
        answers = dict(answers)
        for node_id, value in answers.items():
            if node_id not in self.nodes or value not in self.nodes[node_id]["options"]:
                raise ValueError("Choose a listed answer for a recognised classification question.")
        inferred = set()
        # Descriptions can suggest intended use, never establish statutory eligibility.
        if description and self.start not in answers:
            guess = heuristic_answer(self.start, description)
            if guess:
                answers[self.start] = guess
                inferred.add(self.start)
        node_id, trail, seen = self.start, [], set()
        base = {"complete": False, "category": None, "category_detail": None,
                "next_question": None, "needs_review": False, "review_reason": None,
                "rules_version": self.rules["version"]}

        def result(**values):
            return {**base, "trail": trail,
                    "answers": {step["node"]: step["answer"] for step in trail}, **values}

        while node_id in self.nodes:
            if node_id in seen:
                raise ValueError(f"Cycle detected in classifier rules at {node_id}")
            seen.add(node_id)
            node = self.nodes[node_id]
            answer = answers.get(node_id)
            if answer is None:
                return result(next_question=self._node_payload(node_id))
            trail.append({"node": node_id, "question": node["question"], "answer": answer,
                          "label": node.get("option_labels", {}).get(answer, answer),
                          "inferred": node_id in inferred})
            nxt = node["options"][answer]
            if nxt.startswith("review:"):
                return result(needs_review=True, review_reason=self.rules["reviews"][nxt.split(":", 1)[1]])
            if nxt.startswith("category:"):
                category = nxt.split(":", 1)[1]
                detail = self.categories[category]
                return result(complete=True, category=category, category_detail=detail,
                              needs_review=detail.get("needs_review", False),
                              review_reason=detail.get("review_reason"))
            node_id = nxt
        raise ValueError(f"Unknown node in classifier rules: {node_id}")

    def category_detail(self, category):
        return self.categories.get(category)


def heuristic_answer(node_id: str, text: str) -> str | None:
    """Map unambiguous intended use; never infer book, ingredient or assay tests."""
    if node_id != "q_intended_use":
        return None
    text = (text or "").lower()
    text = re.sub(r"\b(?:no|without|not making|does not make)\s+(?:any\s+)?(?:new\s+)?(?:therapeutic|medicinal|disease|treatment)\s+claims?\b", "", text)
    if re.search(r"\b(?:no|not|without|neither|isn't)\b", text):
        return None
    # Therapeutic intent takes priority even for a cream, drink or hair oil.
    if re.search(r"\b(?:medicine|drug|treat(?:s|ing|ment)?|cure(?:s)?|disease|therapeutic|churna|asava|bhasma)\b", text):
        return "medicine"
    food = bool(re.search(r"\b(?:food|drink|supplement|nutraceutical|aahara?|beverage|snack|juice)\b", text))
    cosmetic = bool(re.search(r"\b(?:cosmetic|beauty|cream|lotion|shampoo|makeup|skin care|hair oil)\b", text))
    if food != cosmetic:
        return "food" if food else "cosmetic"
    return None
