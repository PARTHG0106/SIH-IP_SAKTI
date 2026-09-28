"""Minimal audit metadata and explicit, append-only resource consent decisions.

Question text, product descriptions, answers and provider credentials are never
written to the audit log. This is a privacy measure, not a compliance claim.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from threading import Lock
from .config import settings

_LOCK = Lock()


def _append(path, record):
    record = {"ts": datetime.now(timezone.utc).isoformat(), **record}
    with _LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def log_consent(user_id, resource_id, resource_name, consent, purpose="registry routing"):
    return _append(settings.consent_log_path, {
        "type": "consent", "user_id": user_id, "resource_id": resource_id,
        "resource_name": resource_name, "consent": bool(consent), "purpose": purpose})


def has_consent(user_id, resource_id):
    decision = False
    try:
        with _LOCK, open(settings.consent_log_path, encoding="utf-8") as stream:
            for line in stream:
                try:
                    record = json.loads(line)
                except (ValueError, TypeError):
                    continue
                if (isinstance(record, dict) and record.get("user_id") == user_id
                        and record.get("resource_id") == resource_id):
                    decision = record.get("consent") is True
    except FileNotFoundError:
        return False
    return decision


def log_query(query, jurisdiction, lang, confidence, abstained, citation_ids,
              answer_source, *, request_id="", category=None, reason=None):
    return _append(settings.audit_log_path, {
        "type": "query", "request_id": request_id, "query_chars": len(query),
        "jurisdiction": jurisdiction, "lang": lang, "category": category,
        "confidence": confidence, "abstained": abstained, "citations": citation_ids,
        "answer_source": answer_source, "reason": reason})
