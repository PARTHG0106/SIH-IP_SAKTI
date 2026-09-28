"""Offline behavioural scorecard. Run: python -m backend.eval_runner.

This evaluates the shared application pipeline with translation/model calls
disabled and BM25 selected explicitly. Gold-source matches are not proof of
legal accuracy; content checks and abstention reasons are reported separately.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from .config import ROOT, settings
from .models import AskRequest
from .pipeline import Assistant
from .retrieval import Retriever
from .router import RegistryRouter

EVAL = ROOT / "eval" / "eval_set.jsonl"


def run(report_path=None):
    retriever = Retriever(mode="bm25")
    assistant = Assistant(retriever, RegistryRouter())
    items = [json.loads(line) for line in EVAL.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = []
    for item in items:
        request = AskRequest(query=item["query"], jurisdiction=item.get("jurisdiction", "India"),
                             category=item.get("expected_category"), lang=item.get("lang", "en"))
        answer = assistant.answer(request, use_llm=False)
        expect_abstain = item.get("expect_abstain", False)
        expected_ids = set(item.get("expected_citations", []))
        used_ids = {c.id for c in answer.citations}
        matches_state = answer.abstained == expect_abstain
        matches_reason = not item.get("expected_reason") or answer.reason == item["expected_reason"]
        citation_match = bool(expected_ids & used_ids) if expected_ids else True
        hits, _ = retriever.search(request.query, jurisdiction=request.jurisdiction, category=request.category)
        recall = bool(expected_ids & {h["doc"]["id"] for h in hits}) if expected_ids else True
        content = (answer.original_answer_en or answer.answer).lower()
        missing_terms = [term for term in item.get("expected_terms", []) if term.lower() not in content]
        unexpected_terms = [term for term in item.get("forbidden_terms", []) if term.lower() in content]
        # Every selected source, including context on an abstention, must match scope.
        scope_ok = all(c.jurisdiction == request.jurisdiction for c in answer.citations)
        passed = matches_state and matches_reason and citation_match and scope_ok and not missing_terms and not unexpected_terms
        rows.append({
            "id": item["id"], "passed": bool(passed), "expected_abstention": expect_abstain,
            "abstention_ok": matches_state, "reason_ok": matches_reason,
            "reason": answer.reason, "citation_match": citation_match, "retrieval_recall": recall,
            "scope_ok": scope_ok, "missing_terms": missing_terms, "unexpected_terms": unexpected_terms,
            "citations": sorted(used_ids), "confidence": answer.confidence,
        })

    answerable = [row for row in rows if not row["expected_abstention"]]
    report = {
        "mode": "offline; BM25; no audit writes", "corpus_version": retriever.corpus.version,
        "n": len(rows), "passed": sum(row["passed"] for row in rows),
        "abstain_ok": sum(row["abstention_ok"] for row in rows),
        "cite_ok": sum(row["citation_match"] for row in answerable),
        "recall_ok": sum(row["retrieval_recall"] for row in answerable),
        "n_answerable": len(answerable), "n_abstain": len(rows) - len(answerable),
        "all_scopes_correct": all(row["scope_ok"] for row in rows), "rows": rows,
        "limitation": "A small seeded behavioural regression set, not a legal-accuracy benchmark."
    }
    print("IP-SAKTI offline behavioural scorecard")
    print(f"Corpus: {report['corpus_version']} | BM25 | models/translation disabled")
    for row in rows:
        print(f"  {row['id']:<5} {'PASS' if row['passed'] else 'FAIL':<5} "
              f"{row['reason'] or 'answered':<28} sources={','.join(row['citations']) or '-'}")
        if row["missing_terms"] or row["unexpected_terms"]:
            print(f"        missing={row['missing_terms']}; forbidden={row['unexpected_terms']}")
    print(f"Behavioural cases: {report['passed']}/{report['n']}")
    print(f"Abstention decisions: {report['abstain_ok']}/{report['n']}")
    print(f"Gold-source matches: {report['cite_ok']}/{report['n_answerable']}")
    print(f"Retrieval recall@{settings.top_k}: {report['recall_ok']}/{report['n_answerable']}")
    print(report["limitation"])
    if report_path:
        path = Path(report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", help="Optional path for a JSON scorecard.")
    args = parser.parse_args()
    result = run(args.report)
    raise SystemExit(0 if result["passed"] == result["n"] else 1)
