"""Explicitly opt-in live-provider evaluation using synthetic saved browser cases.

Credentials are read in process from an explicitly named file or environment.
They are never included in reports. This makes paid remote API calls.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


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
              "corpus_version": retriever.corpus.version, "credential_recorded": False,
              "method": "FastAPI TestClient requests; real remote planning/synthesis/audit/translation calls; synthetic cases",
              "cases": []}
    active = []
    original_chat, original_validate, original_plan = llm.chat, rag._validate, planning._model_plan

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

    llm.chat, rag._validate, planning._model_plan = traced_chat, traced_validate, traced_plan
    try:
        with TestClient(app) as client:
            chat = None
            previous = None
            for number in sorted(selected):
                if number not in {3, 4, 14}:
                    chat = client.post("/api/chat").json()["conversation_id"]
                    previous = None
                case = cases[number]
                active = []
                start = time.monotonic()
                print(json.dumps({"case_started": number, "title": case["title"]}), flush=True)
                response = client.post("/api/ask", json={"query": case["prompt"], "jurisdiction": "India",
                                                       "lang": "hi" if number == 9 else "en", "conversation_id": chat})
                body = response.json()
                entry = {"id": number, "title": case["title"], "prompt": case["prompt"],
                         "http_status": response.status_code, "seconds": round(time.monotonic()-start,3),
                         "response": body, "provider_events": active}
                if number in {4, 14} and previous:
                    entry["source_only_citations_within_snapshot"] = {c["id"] for c in body.get("citations", [])} <= {c["id"] for c in previous.get("citations", [])}
                    entry["source_only_scope"] = body.get("evidence_scope") == "previous_turn"
                if number in {5, 7, 8, 15}:
                    entry["rejected_without_provider_call"] = body.get("reason") == "out_of_scope" and not active
                report["cases"].append(entry)
                (output / "results.json").write_text(safe(json.dumps(report, ensure_ascii=False, indent=2)), encoding="utf-8")
                print(json.dumps({"case_finished": number, "http_status": response.status_code,
                                  "answer_source": body.get("answer_source"), "reason": body.get("reason"),
                                  "translation_status": body.get("translation_status"), "seconds": entry["seconds"]}), flush=True)
                previous = body
    finally:
        llm.chat, rag._validate, planning._model_plan = original_chat, original_validate, original_plan
    report["completed_at"] = datetime.now(timezone.utc).isoformat()
    (output / "results.json").write_text(safe(json.dumps(report, ensure_ascii=False, indent=2)), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider-file", help="Explicit JSON file with url and key, never saved to reports")
    parser.add_argument("--provider", choices=("anthropic", "openai"))
    parser.add_argument("--model")
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument("--cases", type=int, nargs="+", default=[2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14])
    parser.add_argument("--output", default=str(ROOT / "docs/qa/live-provider"))
    run(parser.parse_args())
