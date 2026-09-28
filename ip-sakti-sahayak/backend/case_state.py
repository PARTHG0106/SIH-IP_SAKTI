"""Conservative, verbatim case state for the local planner.

The state contains assertions, never inferred classifications. Corrections are
resolved before retrieval and rendering so old labels and cancelled destinations
cannot remain positive search signals. This is deliberately bounded parsing,
not a claim to understand every possible natural-language correction.
"""
from __future__ import annotations

from dataclasses import dataclass
import re


def segments(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])|\n+", text) if s.strip()]


def without_turn_labels(text: str) -> str:
    return re.sub(r"^(?:(?:Follow-up|Correction|Actually):\s*)+", "", text, flags=re.I)


_REQUEST = re.compile(
    r"^(?:whether|which|what|how|why|where|when|can|could|should|would|is|are|does|do|"
    r"please|give|provide|explain|identify|determine|analyse|analyze|create|use|using|cite|"
    r"compare|distinguish|discuss|include|exclude|keep|make|show|list|first list|"
    r"before (?:giving|proposing)|explicitly|tell|answer|do not|don.t|replace|discard|"
    r"ignore|treat|based on|put|turn|summari[sz]e|format|reformat)\b", re.I)


def fact_spans(text: str) -> tuple[str, ...]:
    """Retain declarative user spans, including dates, claim labels and negatives.

    An allowlist of sentence beginnings loses ordinary facts such as 'At a
    trade fair ...'. Exclude requests instead; the original span remains the
    only authority and is labelled unverified when presented.
    """
    facts = []
    for span in segments(text):
        candidate = without_turn_labels(span)
        if (_REQUEST.search(candidate) or "?" in candidate or "|" in candidate
                or re.match(r"(?:i|we)\s+(?:want|need|would like)\s+to\s+(?:know|understand|ask)\b", candidate, re.I)):
            continue
        # A reference such as 'For each ingredient, explain ...' is a request,
        # while 'For our medicine, we have two claims' is an assertion.
        if re.match(r"for\b", candidate, re.I) and re.search(
                r"\b(?:explain|analyse|analyze|identify|compare|discuss)\b", candidate, re.I):
            continue
        if len(candidate.split()) >= 3:
            facts.append(span)
    return tuple(dict.fromkeys(facts))[:40]


_REPLACEMENT = re.compile(
    r"\b(?:replace|discard|forget|ignore|withdraw)\s+(?:all\s+)?(?:the\s+)?"
    r"(?:(?:old|earlier|previous|existing|product|ownership|case|company)\s+(?:and\s+)?)"
    r"{0,6}(?:facts|case|scenario)\b"
    r"|\b(?:start (?:again|over)|reset (?:the |this |my |our )?case)\b", re.I)


def replaces_case(text: str) -> bool:
    return bool(_REPLACEMENT.search(text))


_FIELDS = {
    "sourcing": r"wild|cultivat|sourc(?:ed|ing)|collected|suppliers?|traders?|(?:own|our)\s+farm|plants?\s+(?:are\s+)?grown",
    "entity": r"foreign.{0,20}(?:control|owned)|(?:indian|german|british|foreign)[- ]owned|wholly.{0,15}owned|shareholders?|nationality|citizenship|residen(?:t|ce)|incorporat|company.{0,25}(?:control|owned|ownership)",
    "formula": r"(?:exact|complete|classical).{0,25}(?:formula|combination)|first.schedule|samhita|authoritative.{0,20}texts?|classical.{0,20}texts?",
    "ingredients": r"(?:contains?|containing|ingredients?\s+(?:are|include))",
    "disclosure": r"disclos|publish|publicly|trade fair|leaflet|demonstrat",
    "markets": r"\b(?:sell|sold|exports?|markets?)\b|\b(?:India|Germany|EU|US|United States|Europe)\s+label\b",
    "claims": r"website|(?:only|therapeutic|disease|marketing|health|treatment).{0,20}claim|cures?\s+\w+|hair conditioning",
}


def _fields(text: str) -> set[str]:
    fields = {key for key, pattern in _FIELDS.items() if re.search(pattern, text, re.I)}
    # Absence from an authoritative book is a formula-reference fact, not a
    # statement about the inventor's later public disclosure.
    if re.search(r"disclos\w*\s+in\s+(?:classical|authoritative|first.schedule)", text, re.I) and not re.search(
            r"public|publish|trade fair|leaflet|demonstrat", text, re.I):
        fields.discard("disclosure")
    return fields


def _clauses(span: str) -> list[str]:
    # Split independent subject clauses for correction purposes only. This
    # keeps, for example, supplier facts when only the shareholder changes.
    return [p.strip() for p in re.split(
        r";\s*|,\s*(?:and|while|but)\s+(?=(?:our|the|all|we|plants?|herbs?)\b)"
        r"|\s+and\s+(?=(?:our company|the company|all plants|all herbs|we sell|our suppliers)\b)"
        r"|\s+(?=containing\b)",
        span, flags=re.I) if p.strip()]


@dataclass(frozen=True)
class CaseState:
    context: str
    facts: tuple[str, ...]
    discarded_facts: tuple[str, ...]


def prune_context(context: str, current: str) -> tuple[str, tuple[str, ...]]:
    if replaces_case(current):
        return "", fact_spans(context)
    assertions = fact_spans(current)
    changed_text = "\n".join(assertions)
    if not assertions and re.match(r"\s*(?:what if|suppose|assuming)\b", current, re.I):
        changed_text = current
    changed = _fields(changed_text)
    if not changed:
        return context, ()
    factual = set(fact_spans(context))
    kept, discarded = [], []
    for span in segments(context):
        if span not in factual:
            kept.append(span)
            continue
        clauses = _clauses(span)
        removed = [clause for clause in clauses if _fields(clause) & changed]
        if not removed:
            kept.append(span)
        else:
            discarded.extend(removed)
            kept.extend(clause for clause in clauses if clause not in removed)
    return "\n".join(kept), tuple(discarded)


def resolve_case(context: str | None, current: str, *, independent=False) -> CaseState:
    if independent:
        return CaseState(current, fact_spans(current), ())
    turns = re.split(r"(?im)^\s*Follow-up:\s*", context or "")
    resolved, discarded = turns[0], []
    for continuation in (*turns[1:], current):
        prior, removed = prune_context(resolved, continuation)
        discarded.extend(removed)
        resolved = "\n".join(filter(None, (prior, continuation)))
    return CaseState(resolved, fact_spans(resolved), tuple(dict.fromkeys(discarded)))


COUNTRIES = {
    "India": r"\bindia[n]?\b",
    "EU": r"\beu\b|european union|\beurope\b|\bgerman(?:y)?\b|\bfrance\b|\bfrench\b|\bitaly\b|\bspain\b|\bnetherlands\b|\bbelgium\b|\baustria\b|\bportugal\b|\bpoland\b|\bsweden\b|\bdenmark\b|\bfinland\b|\bireland\b|\bczech(?:ia| republic)\b|\bgreece\b|\bhungary\b|\bromania\b|\bbulgaria\b|\bcroatia\b|\bslovenia\b|\bslovakia\b|\bestonia\b|\blatvia\b|\blithuania\b|\bluxembourg\b|\bmalta\b|\bcyprus\b",
    "US": r"united states|(?-i:\bUS\b)|\busa\b|\bu\.s\.(?:a\.)?|\bus market\b|\bfda\b",
}
_COUNTRY_RE = {country: re.compile(pattern, re.I) for country, pattern in COUNTRIES.items()}
_CANCELLED = re.compile(
    r"\b(?:no|without|not|neither|cancel(?:led|ing)?|abandon(?:ed|ing)?|stopp?ed|withdrawn)\b"
    r"[^.;!?]{0,100}\b(?:export|market|launch|sell|sale|Germany|EU|US|United States)\w*", re.I)


def positive_issue_text(text: str) -> str:
    """Remove negative instructions and retracted market clauses from searches."""
    kept = []
    for span in segments(text):
        if replaces_case(without_turn_labels(span)):
            continue
        if re.match(r"(?:do not|don.t)\s+(?:assume|guarantee|equate|present|treat|repeat|add)\b", span, re.I):
            continue
        span = re.sub(r"(?:there is\s+)?no\s+(?:disease[- ]treatment|therapeutic|disease)\s+claim\b", "", span, flags=re.I)
        # A sentence can assert India-only sales and cancel two other markets.
        span = re.sub(r",?\s*(?:with\s+)?\b(?:no|without|not|neither)\b[^.;!?]*\b(?:exports?|markets?)\b", "", span, flags=re.I)
        if _CANCELLED.search(span) and re.search(r"export|market|launch|sell|sale", span, re.I):
            # Preserve any separate positive clause before a cancellation.
            span = re.split(r"\b(?:cancel(?:led|ing)?|abandon(?:ed|ing)?|stopped|withdrawn)\b", span, flags=re.I)[0]
        kept.append(span)
    return "\n".join(kept)


def market_context(text: str) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...]]:
    markets, intents = [], []
    for span in segments(text):
        for clause in re.split(r";\s*", span):
            positive = positive_issue_text(clause)
            if not positive:
                continue
            for country, pattern in _COUNTRY_RE.items():
                if not pattern.search(positive):
                    continue
                # Nationality and plant origin are case facts, not a foreign
                # destination. The home country still establishes India scope.
                if country != "India" and re.search(r"shareholder|citizen|nationality|incorporat|owned|supplier|cultivat|sourc", positive, re.I) and not re.search(
                        r"label|export|market|sell|sold|launch|registration|route|decision path|strategy|guidance", positive, re.I):
                    continue
                if country not in markets:
                    markets.append(country)
                if (country, clause.strip()) not in intents:
                    intents.append((country, clause.strip()))
    return tuple(markets), tuple(intents)


def has_indian_food_intent(text: str) -> bool:
    """Keep a foreign supplement label attached to its named jurisdiction."""
    for span in segments(text):
        for clause in re.split(r";\s*", span):
            if not re.search(r"\baahara?\b|fssai|\bfood\b|supplement", clause, re.I):
                continue
            if re.search(r"\baahara?\b|fssai", clause, re.I):
                return True
            countries = [country for country, pattern in _COUNTRY_RE.items() if pattern.search(clause)]
            if not countries or "India" in countries:
                return True
    return False
