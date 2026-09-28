"""Validated API contracts. Invalid scopes must never broaden a search."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictBool

Jurisdiction = Literal["India", "International", "Both"]
Category = Literal["classical", "proprietary", "new_drug", "phytopharmaceutical", "ayurveda_aahar", "cosmetic"]
Regime = Literal["patent", "trademark", "design", "copyright", "gi", "plant_variety", "biodiversity", "drug", "food", "advertising", "treaty", "reference"]
Language = Literal["en", "as", "bn", "brx", "doi", "gu", "hi", "kn", "ks", "kok", "mai", "ml", "mni", "mr", "ne", "or", "pa", "sa", "sat", "sd", "ta", "te", "ur"]


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Citation(BaseModel):
    id: str
    statute: str
    section: str
    title: str
    source_url: str
    as_of: str
    jurisdiction: str
    regime: str
    snippet: str
    score: float = 0
    source_type: str = "official_reference"
    review_status: str = "dossier_record"
    review_note: str | None = None
    reviewed_on: str | None = None
    time_sensitive: bool = False
    text_kind: str = "curated_summary"


class ClassifyRequest(Request):
    answers: dict[str, str] = Field(default_factory=dict, max_length=20)
    description: str | None = Field(default=None, max_length=4000)


class ClassifyResponse(BaseModel):
    complete: bool
    next_question: dict | None = None
    category: Category | None = None
    category_detail: dict | None = None
    trail: list[dict] = Field(default_factory=list)
    answers: dict[str, str] = Field(default_factory=dict)
    needs_review: bool = False
    review_reason: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    disclaimer: str = ""
    rules_version: str = ""


class AskRequest(Request):
    query: str = Field(min_length=3, max_length=4000)
    jurisdiction: Jurisdiction = "India"
    lang: Language = "en"
    category: Category | None = None
    regime: Regime | None = None
    conversation_id: str | None = Field(default=None, min_length=32, max_length=80,
                                       pattern=r"^[A-Za-z0-9_-]+$")


class RegistryLink(BaseModel):
    id: str
    name: str
    url: str | None = None
    regime: str
    jurisdiction: str
    access: str
    note: str | None = None


class AskResponse(BaseModel):
    answer: str
    abstained: bool
    confidence: float = Field(ge=0, le=1)
    confidence_label: str
    jurisdiction: Jurisdiction
    lang: Language
    requested_lang: Language = "en"
    category: Category | None = None
    citations: list[Citation] = Field(default_factory=list)
    registry_links: list[RegistryLink] = Field(default_factory=list)
    escalate: bool = False
    as_of: str | None = None
    source_date_range: dict[str, str] | None = None
    disclaimer: str = ""
    answer_source: str = "extractive"
    original_answer_en: str | None = None
    translation_status: str = "not_requested"
    notices: list[str] = Field(default_factory=list)
    reason: str | None = None
    corpus_version: str = ""
    request_id: str = ""
    conversation_id: str | None = None
    memory_used: bool = False
    evidence_scope: Literal["corpus", "previous_turn"] = "corpus"
    context_question: str | None = None


class ConsentRequest(Request):
    user_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    resource_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9_]+$")
    # Compatibility field; the server always uses the registry's canonical name.
    resource_name: str | None = Field(default=None, max_length=200)
    consent: StrictBool
    purpose: Literal["registry routing"] = "registry routing"
