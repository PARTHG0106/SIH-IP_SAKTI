"""Source integrity and provenance, shared by classification and answers."""
from __future__ import annotations

import re
from datetime import date
from typing import get_args
from urllib.parse import urlsplit
from .models import Category, Jurisdiction, Regime, Citation


def validate_source(doc: dict) -> dict:
    required = ("id", "title", "statute", "section", "text", "source_url", "as_of", "jurisdiction", "regime")
    if not isinstance(doc, dict) or any(not isinstance(doc.get(k), str) or not doc[k].strip() for k in required):
        raise ValueError("Every source needs non-empty identity, text, scope, date and URL fields")
    if not re.fullmatch(r"[a-z0-9_]+", doc["id"]):
        raise ValueError("Invalid source id")
    if doc["jurisdiction"] not in get_args(Jurisdiction) or doc["regime"] not in get_args(Regime):
        raise ValueError("Invalid source jurisdiction or regime")
    url = urlsplit(doc["source_url"])
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        raise ValueError("Source URLs must be public HTTPS references")
    if date.fromisoformat(doc["as_of"]).isoformat() != doc["as_of"]:
        raise ValueError("Source dates must use YYYY-MM-DD")
    for name in ("categories", "keywords"):
        if not isinstance(doc.get(name, []), list) or any(not isinstance(x, str) for x in doc.get(name, [])):
            raise ValueError(f"{name} must be a list of strings")
    if any(c not in get_args(Category) for c in doc.get("categories", [])):
        raise ValueError("Invalid source category")
    if doc.get("review_status", "dossier_record") not in {"dossier_record", "primary_checked", "needs_review"}:
        raise ValueError("Invalid source review status")
    if not isinstance(doc.get("time_sensitive", False), bool):
        raise ValueError("time_sensitive must be a boolean")
    if doc.get("reviewed_on"):
        date.fromisoformat(doc["reviewed_on"])
    if doc.get("review_status") == "primary_checked" and not doc.get("reviewed_on"):
        raise ValueError("A primary-source check needs a review date")
    return {"source_type": "official_reference", "review_status": "dossier_record",
            "review_note": None, "reviewed_on": None, "time_sensitive": False, "text_kind": "curated_summary", **doc}


def citation(doc: dict, score: float = 0) -> Citation:
    return Citation(**{k: doc[k] for k in (
        "id", "statute", "section", "title", "source_url", "as_of", "jurisdiction", "regime",
        "source_type", "review_status", "review_note", "reviewed_on", "time_sensitive", "text_kind")},
        # Full passages preserve exceptions, dates and qualifying sentences.
        snippet=doc["text"], score=score)
