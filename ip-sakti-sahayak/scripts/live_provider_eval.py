"""Explicitly opt-in live-provider evaluation using synthetic saved browser cases.

Credentials are read in process from an explicitly named file or environment.
They are never included in reports. This makes paid remote API calls.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def assess_case(entry, previous=None):
    """A successful HTTP request or local fallback is not a live-model pass."""
    body = entry["response"]
    number = entry["id"]
    events = entry["provider_events"]
    checks = {"http_ok": entry["http_status"] == 200}
    if number in {5, 7, 8, 15}:
        checks["ayurveda_scope_guard"] = body.get("reason") == "out_of_scope"
        checks["no_provider_call"] = not events
    elif number == 10:
        checks["dated_status_guard"] = body.get("reason") == "current_status_unverified"
    else:
        checks["validated_live_synthesis"] = body.get("answer_source") == "rag_synthesis"
        checks["synthesis_and_audit_completed"] = all(
            any(e["stage"] == stage and e.get("ok") for e in events)
            for stage in ("synthesis", "audit"))
        checks["not_abstained"] = body.get("abstained") is False
        citation_ids = {c["id"] for c in body.get("citations", [])}
        markers = set(re.findall(r"\[([a-z0-9_]+)\]", body.get("answer", "")))
        checks["rendered_citations_match"] = bool(markers) and markers == citation_ids
    if number == 9:
        checks["hindi_translation_completed"] = (
            body.get("translation_status") == "translated" and body.get("lang") == "hi")
    if number in {4, 14}:
        checks["source_only_scope"] = body.get("evidence_scope") == "previous_turn"
        checks["source_only_no_retrieval"] = entry.get("retrieval_calls") == 0
        checks["source_only_citations_within_snapshot"] = previous is not None and (
            {c["id"] for c in body.get("citations", [])}
            <= {c["id"] for c in previous.get("citations", [])})
    return checks


def summarize(report):
    cases = report["cases"]
    return {
        "cases_completed": len(cases),
        "checks_passed_cases": sum(c["passed"] for c in cases),
        "checks_failed_cases": sum(not c["passed"] for c in cases),
        "validated_live_answers": sum(c["response"].get("answer_source") == "rag_synthesis" for c in cases),
        "local_fallback_answers": sum(c["response"].get("answer_source") == "grounded_synthesis" for c in cases),
        "provider_failures": sum(not e.get("ok", False) for c in cases for e in c["provider_events"]
                                 if e["stage"] in {"planner", "synthesis", "audit", "translation"}),
    }


def run(args):
    from backend.config import settings
    if args.provider_file:
        cfg = json.loads(Path(args.provider_file).read_text(encoding="utf-8"))
        settings.llm_base_url = cfg["url"].strip()
        settings.llm_api_key = cfg["key"].strip()
    if args.provider:
        settings.llm_provider = args.provider
    if args.model:
        settings.llm_model = args.model
    settings.llm_timeout = args.timeout
    settings.translate_provider = "llm"
    if not settings.llm_enabled:
        raise SystemExit("Choose provider/model and supply configured credentials before live evaluation.")

    from fastapi.testclient import TestClient
    from backend import llm, planning, rag
    from backend.main import app, retriever
    cases = json.loads((ROOT / "docs/qa/complex-browser-repair/browser-observations.json").read_text(encoding="utf-8"))["cases"]
    cases = {case["id"]: case for case in cases}
    selected = set(args.cases)
    if not selected <= cases.keys():
        raise SystemExit("Unknown case ID; choose from 1 through 15.")
    if selected & {3, 4}:
        selected.add(2)
    if 4 in selected:
        selected.add(3)
    if 14 in selected:
        selected.add(13)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    report = {"started_at": datetime.now(timezone.utc).isoformat(),
              "provider_protocol": settings.llm_provider, "model": settings.llm_model,
              "timeout_seconds": settings.llm_timeout,
              "corpus_version": retriever.corpus.version, "credential_recorded": False,
              "method": "FastAPI TestClient requests; real remote planning/synthesis/audit/translation calls; synthetic cases",
              "cases": []}
    active = []
    retrieval_calls = 0
    original_chat, original_validate, original_plan = llm.chat, rag._validate, planning._model_plan
    original_search = retriever.search

    def safe(value):
        return str(value).replace(settings.llm_api_key, "[redacted]")

    def traced_chat(system, user, **kwargs):
        stage = ("planner" if system == planning._PLAN_SYSTEM else
                 "synthesis" if system == rag._SYSTEM else "audit" if system == rag._VERIFY
                 else "translation")
        event = {"stage": stage, "max_tokens": kwargs.get("max_tokens")}
        start = time.monotonic()
        try:
            answer = original_chat(system, user, **kwargs)
            event.update(output=safe(answer), output_characters=len(answer), ok=True)
            return answer
        except Exception as error:
            event.update(ok=False, error_type=type(error).__name__, error=safe(error))
            raise
        finally:
            event["seconds"] = round(time.monotonic() - start, 3)
            active.append(event)
            print(json.dumps({"event": stage, "ok": event["ok"], "seconds": event["seconds"]}), flush=True)

    def traced_validate(*values, **kwargs):
        try:
            return original_validate(*values, **kwargs)
        except Exception as error:
            active.append({"stage": "synthesis_validation", "ok": False, "error": safe(error)})
            raise

    def traced_plan(*values, **kwargs):
        try:
            result = original_plan(*values, **kwargs)
            active.append({"stage": "planner_validation", "ok": True,
                           "required_issues": [i.title for i in result.issues]})
            return result
        except Exception as error:
            active.append({"stage": "planner_validation", "ok": False, "error": safe(error)})
            raise

    def traced_search(*values, **kwargs):
        nonlocal retrieval_calls
        retrieval_calls += 1
        return original_search(*values, **kwargs)

    llm.chat, rag._validate, planning._model_plan = traced_chat, traced_validate, traced_plan
    retriever.search = traced_search
    original_audit_path = settings.audit_log_path
    try:
        with TemporaryDirectory(prefix="ip-sakti-live-eval-") as temporary, TestClient(app) as client:
            settings.audit_log_path = Path(temporary) / "audit.jsonl"
            chat = None
            previous = None
            for number in sorted(selected):
                if number not in {3, 4, 14}:
                    chat = client.post("/api/chat").json()["conversation_id"]
                    previous = None
                case = cases[number]
                active = []
                retrieval_calls = 0
                start = time.monotonic()
                print(json.dumps({"case_started": number, "title": case["title"]}), flush=True)
                response = client.post("/api/ask", json={"query": case["prompt"], "jurisdiction": "India",
                                                       "lang": "hi" if number == 9 else "en", "conversation_id": chat})
                body = response.json()
                entry = {"id": number, "title": case["title"], "prompt": case["prompt"],
                         "http_status": response.status_code, "seconds": round(time.monotonic()-start,3),
                         "response": body, "provider_events": active, "retrieval_calls": retrieval_calls}
                if number in {4, 14} and previous:
                    entry["source_only_citations_within_snapshot"] = {c["id"] for c in body.get("citations", [])} <= {c["id"] for c in previous.get("citations", [])}
                    entry["source_only_scope"] = body.get("evidence_scope") == "previous_turn"
                if number in {5, 7, 8, 15}:
                    entry["rejected_without_provider_call"] = body.get("reason") == "out_of_scope" and not active
                entry["checks"] = assess_case(entry, previous)
                entry["passed"] = all(entry["checks"].values())
                report["cases"].append(entry)
                report["summary"] = summarize(report)
                (output / "results.json").write_text(safe(json.dumps(report, ensure_ascii=False, indent=2)), encoding="utf-8")
                print(json.dumps({"case_finished": number, "http_status": response.status_code,
                                  "answer_source": body.get("answer_source"), "reason": body.get("reason"),
                                  "translation_status": body.get("translation_status"), "seconds": entry["seconds"],
                                  "checks_passed": entry["passed"]}), flush=True)
                previous = body
    finally:
        llm.chat, rag._validate, planning._model_plan = original_chat, original_validate, original_plan
        retriever.search = original_search
        settings.audit_log_path = original_audit_path
    report["completed_at"] = datetime.now(timezone.utc).isoformat()
    (output / "results.json").write_text(safe(json.dumps(report, ensure_ascii=False, indent=2)), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider-file", help="Explicit JSON file with url and key, never saved to reports")
    parser.add_argument("--provider", choices=("anthropic", "openai"))
    parser.add_argument("--model")
    parser.add_argument("--timeout", type=float, default=180,
                        help="Per-call timeout; saved successful synthesis exceeded 90 seconds")
    parser.add_argument("--cases", type=int, nargs="+", default=list(range(1, 16)))
    parser.add_argument("--output", default=str(ROOT / "docs/qa/live-provider"))
    result = run(parser.parse_args())
    print(json.dumps(result["summary"]), flush=True)
    raise SystemExit(1 if result["summary"]["checks_failed_cases"] else 0)
