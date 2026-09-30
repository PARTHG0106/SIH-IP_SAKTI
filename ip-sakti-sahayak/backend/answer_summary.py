"""Short, source-bound explanations for the reviewed local answer path.

This is a second presentation of the supplied, fingerprint-checked answer cards,
not retrieval or a new legal classifier. Vocabulary is attached to source IDs,
never to an exact user question. Unknown/scoped cards keep their reviewed text.
"""
from __future__ import annotations

import re

from .answer_cards import CARDS
from .case_analysis import _text as _escape_text


# These paraphrases preserve the conditions in the corresponding reviewed card
# and corpus record. They are usable only when that standard card is supplied.
_PLAIN = {
    "patents_ownership": (
        "Inventorship and ownership are separate. Employment, payment for research "
        "or being named as inventor does not by itself establish who owns the patent. "
        "The inventor must be identified, and a company relying on an assignment "
        "needs proof of its right to apply. Check inventive contributions and the "
        "employment, research and assignment agreements before deciding ownership."),
    "patents_assignments": (
        "A transfer or licence of an existing patent must be in a written, duly "
        "executed agreement recording the parties' rights and obligations. Acquiring "
        "the specified patent interest also requires an application to register it. "
        "Check the agreement and retained rights; an NDA or payment alone does not "
        "prove an assignment. Assignment of the right to apply is a separate question."),
    "patents_3p": (
        "In India, an unchanged traditional formula generally cannot be patented: "
        "section 3(p) excludes traditional knowledge and merely repeating the "
        "known properties of traditional ingredients. Absence from classical "
        "books alone does not overcome this exclusion."),
    "patents_invention": (
        "A genuinely new formulation, improvement or manufacturing process can be "
        "assessed separately. It must be new, involve an inventive step and be "
        "industrially usable; calling it new does not establish those tests or "
        "overcome patent exclusions."),
    "patents_3e": (
        "Simply mixing ingredients whose effects only add together is also excluded, "
        "as is a process for making that mere mixture. Evidence of an effect beyond "
        "that may help, but synergy alone does not guarantee a patent."),
    "patents_3d": (
        "Section 3(d) excludes a mere new form of a known substance without "
        "enhanced known efficacy, and mere discovery of a new property or use. "
        "A known process is excluded unless it produces a new product or uses "
        "at least one new reactant. The actual substance and claims need "
        "separate evidence and assessment."),
    "patents_3i": (
        "Treatment-method claims can be excluded from patents in India. A medicine "
        "or manufacturing-process claim needs its own assessment; a dosing regimen "
        "is not automatically a patentable process."),
    "patents_3j": (
        "Section 3(j) excludes plants and animals in whole or part, including seeds, "
        "varieties and species, and essentially biological processes for their "
        "production or propagation. Micro-organisms are excepted from the "
        "plants-and-animals exclusion; that exception alone does not establish "
        "patentability of a particular invention."),
    "patents_rights": (
        "In India, a patent does not itself give permission to sell the medicine or "
        "establish freedom to use other people's patented inventions. It protects "
        "the qualifying product or process claims that are granted; regulatory "
        "clearance and other patent rights need separate checks."),
    "dc_3a": (
        "Classical Ayurvedic medicine is a regulatory category requiring the "
        "intended diagnosis, treatment, mitigation or prevention of disease or "
        "disorder in humans or animals, and manufacture exclusively according "
        "to an authoritative First-Schedule formula. Ayurvedic ingredients or "
        "reading classical texts alone do not establish that category."),
    "dc_3h": (
        "The regulatory term 'patent or proprietary medicine' is not a patent "
        "grant. This ASU category requires all ingredients to appear in "
        "First-Schedule book formulae, the formulation itself to be absent from "
        "those formulae, and a non-parenteral route. These conditions are "
        "separate from invention patentability."),
    "dc_licensing": (
        "Manufacturing an Ayurvedic medicine for sale normally requires the "
        "applicable State/UT ASU licence and compliance with its conditions. "
        "Confirm the product category, premises and evidence needed with that "
        "licensing authority. A proprietary formula does not automatically move "
        "to the CDSCO new-drug route merely because it is novel."),
    "trade_secret": (
        "Confidential process know-how may be protected through secrecy and "
        "confidentiality agreements, but publicly known or readily discoverable "
        "information needs a different assessment. Secrecy cannot replace "
        "mandatory patent or ingredient disclosures. Check what can actually "
        "remain confidential and whether the agreements are enforceable."),
    "dc_label_disclosure": (
        "A proprietary Ayurvedic medicine's mandatory label disclosures include "
        "the true ingredient list, plant names, parts, forms and quantities. The "
        "formula cannot simply remain wholly secret after compliant sale. "
        "Confidential process know-how needs a separate assessment; check the "
        "actual formulation and required label particulars."),
    "bda_s7_exemption": (
        "The cultivated-medicinal-plant exemption under section 7 needs a "
        "certificate of origin from the Biodiversity Management Committee (BMC); "
        "a supplier's cultivation claim alone is insufficient. Section 7 concerns "
        "State Board intimation for covered commercial access by persons outside "
        "section 3(2). This exemption does not waive section 6 IP duties or settle "
        "all benefit-sharing obligations."),
    "bda_origin_2025": (
        "The cited 2025 amendment sets a BMC certificate process for cultivated "
        "medicinal plants from 1 November 2025: Form 11 records, Form 11A application "
        "and Form 12 certificate. Verify the certificate against the actual plants "
        "and quantities. A supplier's statement is insufficient, and the relevant "
        "records and local implementation still need checking."),
    "tm_act": (
        "A trademark can protect a distinctive product name or logo, but not the "
        "formula or manufacturing process. Descriptive, misleading or conflicting "
        "marks can be refused, so the actual brand needs a clearance and "
        "registrability check."),
    "patents_rules_2024_rfe": (
        "The cited rule, commencing 15 March 2024, gives a 31-month "
        "examination-request window from the applicable priority/filing date. "
        "Applications filed before its commencement retain the 48-month period. "
        "The filing and priority dates are needed to select and calculate "
        "the applicable deadline."),
    "patents_rules_2024_form27": (
        "Under the cited amended Rule 131, Form 27 covers each three-financial-year "
        "period starting with the financial year after grant and is due within "
        "six months after that period ends. The grant date determines the schedule."),
    "pct": (
        "The PCT offers one international patent application route; it does not "
        "grant a worldwide patent. Individual national or regional offices decide "
        "protection, with their own national-phase requirements and deadlines."),
    "madrid": (
        "The Madrid System provides an international trademark application route "
        "through the home office. Protection still depends on the designated "
        "markets and their examination; applicant eligibility and the basic mark "
        "also need checking."),
    "eu_thmpd": (
        "The cited EU traditional-use route requires product-specific evidence of "
        "at least 30 years of medicinal use, including at least 15 in the EU. Ayurveda's long history "
        "alone does not qualify a particular product, and the other registration "
        "conditions still apply."),
    "copyright_scope": (
        "Copyright protects original expression, such as written descriptions or "
        "artwork, rather than the underlying formula, method or facts. The cited "
        "handbook describes protection as automatic; authorship and ownership of "
        "the particular work still need checking."),
    "fssai_aahar": (
        "Ayurveda Aahara is a food route based on the authoritative Schedule-A "
        "recipes, ingredients or processes. It excludes Ayurvedic drugs, "
        "proprietary Ayurvedic medicines, cosmetics, narcotics and psychotropics; "
        "advertising must avoid disease claims. The actual product needs "
        "classification before choosing this route."),
    "phytopharma_gsr918": (
        "A phytopharmaceutical requires the specified purified, standardised "
        "fraction of a medicinal-plant or plant-part extract, with at least four "
        "bio-active or phytochemical compounds assessed both qualitatively and "
        "quantitatively, for diagnosis, treatment, mitigation or prevention of "
        "disease, excluding parenteral administration. Four herbs alone do not "
        "satisfy that test. The cited CDSCO new-drug route requires identity, "
        "safety and confirmatory clinical data."),
}

_FOCUS = {
    "patents_3p": r"traditional|classical|\b3\s*\(p\)",
    "patents_3e": r"admixture|mixture|synerg|\b3\s*\(e\)",
    "patents_3d": r"efficacy|polymorph|new salt|known substance|\b3\s*\(d\)",
    "patents_3i": r"treatment.method|dos(?:e|age)|regimen|\b3\s*\(i\)",
    "patents_3j": r"plant.variet|seed|\b3\s*\(j\)",
    "patents_rules_2024_rfe": r"examination|\brfe\b|24b|31.month|48.month",
    "patents_rules_2024_form27": r"form\s*27|statement of working|rule\s*131",
    "pct": r"\bpct\b|global patent|worldwide patent|international patent",
    "tm_act": r"trade.?mark|brand|logo|product name",
    "madrid": r"madrid|international.{0,20}(?:brand|trade.?mark)",
    "copyright_scope": r"copyright|artwork|expression|manual",
    "eu_thmpd": r"\beu\b|europe|traditional.use|medicinal.use history",
    "fssai_aahar": r"aahara|fssai|food",
    "phytopharma_gsr918": r"phytopharma|purified|standardis|standardiz",
}

# Practical questions often contain "patent" or "classical" only as context.
# Promote the requested decision above those broad subject cues, while keeping
# every explanation conditional on the reviewed source/card actually supplied.
_DECISIONS = {
    "patent": r"patent.{0,50}(?:allow|permit|permission|right to|sell|sale|market|launch)|freedom to operate",
    "ownership": r"\bown(?:s|er(?:ship)?|ed)?\b|inventor|employ|university|contractor|commissioned|chain of title|assignment|right to apply",
    "sourcing": r"certificate(?:s)?(?: of origin)?|\bbmc\b|form\s*(?:11a?|12)\b|sourc(?:ing|ed)|supplier|provenance|geographical origin",
    "secrecy": r"\bsecret\b|trade.?secret|confiden|\bnda\b|disclos|know.?how|before filing|grace period",
    "manufacturing": r"manufacturing licen[cs]|regulatory (?:approval|permission)|permission to (?:sell|market|manufacture)|licen[cs]e.{0,25}(?:medicine|manufactur)|(?:medicine|manufactur).{0,25}licen[cs]e|\bgmp\b|schedule\s*t\b|158b",
}

_DECISION_SOURCES = {
    "patents_ownership": r"\bown(?:s|er(?:ship)?|ed)?\b|inventor|employ|university|contractor|commissioned|right to apply",
    "patents_assignments": r"assign|transfer|chain of title|written agreement|licen[cs].{0,25}patent|patent.{0,25}licen[cs]",
    "patents_rights": r"freedom to operate|\b(?:sell|sale|market|launch)\b|exclusive rights|what.{0,25}patent.{0,20}protect",
    "bda_s7_exemption": r"certificate(?:s)?(?: of origin)?|cultivat|section\s*7|s\.7|exempt|intimation",
    "bda_origin_2025": r"certificate(?:s)?(?: of origin)?|\bbmc\b|form\s*(?:11a?|12)\b",
    "trade_secret": r"\bsecret\b|trade.?secret|confiden|\bnda\b|know.?how",
    "patents_disclosure": r"disclos|publish|publication|before filing|grace period",
    "dc_label_disclosure": r"label|ingredient.{0,20}(?:secret|disclos)|(?:secret|disclos).{0,20}ingredient|secret.{0,40}(?:sale|sell|market)|(?:sale|sell|market).{0,40}secret",
    "dc_licensing": _DECISIONS["manufacturing"],
    "dc_rule_158b": r"158b|safety|effectiveness|efficacy|evidence.{0,25}licen[cs]",
    "dc_schedule_t": r"\bgmp\b|schedule\s*t\b|premises|quality control",
}


def _priority(query, issue, doc):
    """Put explicitly requested decisions before incidental category keywords."""
    source_id = doc["id"]
    score = 20
    if issue.key in _DECISIONS and re.search(_DECISIONS[issue.key], query, re.I):
        score += 150
    if source_id in _DECISION_SOURCES and re.search(_DECISION_SOURCES[source_id], query, re.I):
        score += 200
    if source_id in _FOCUS and re.search(_FOCUS[source_id], query, re.I):
        score += 100
    patent_question = bool(re.search(r"patent|novelty|inventive.step", query, re.I))
    classification_question = bool(re.search(
        r"classif|categor|classical\s+or\s+proprietary|what\s+(?:is|does).{0,35}"
        r"(?:classical|proprietary)|\bmeaning\b", query, re.I))
    if patent_question:
        score += {"patents_invention": 70, "patents_3e": 50,
                  "dc_3h": 40, "patents_3p": 30}.get(source_id, 0)
        if issue.key == "classification" and source_id != "dc_3h" and not classification_question:
            score -= 10
    if classification_question and issue.key == "classification":
        score += 100
    # Other topics still have a general relevance mechanism, including future
    # reviewed cards. No generated text or source outside rows enters the result.
    for word in set(re.findall(r"[a-z]{4,}", issue.title.lower())):
        if re.search(r"\b" + re.escape(word) + r"\b", query, re.I):
            score += 2
    return score


def _explanation(doc, card):
    if card == CARDS.get(doc["id"]) and doc["id"] in _PLAIN:
        return _PLAIN[doc["id"]]
    # A scoped authority/sourcing card can support less than the general card
    # for the same statute. Keep its complete reviewed qualifications intact.
    return " ".join(dict.fromkeys((card.established, card.application)))


def summarize_local(query, plan, rows, *, evidence_limited=False):
    """Return a compact cited overview, or empty when there is no usable card.

    The caller supplies only eligible, fingerprint-validated (document, card)
    pairs. The detailed answer remains the record of all rules and case facts;
    this overview never claims to decide a particular person's eligibility.
    """
    candidates = []
    missing = []
    for issue, points in rows:
        if not points:
            missing.append(" ".join(_escape_text(issue.title).split()))
        for doc, card in points:
            if doc.get("id") and card is not None:
                candidates.append((issue, doc, card))
    if not candidates:
        return ""

    # Use the substantive question on a formatting-only follow-up. Resolved
    # facts are deliberately not converted into asserted legal conclusions.
    focus = " ".join(dict.fromkeys((query or "", getattr(plan, "substantive_query", "") or "")))
    candidates.sort(key=lambda row: _priority(focus, row[0], row[1]), reverse=True)
    jurisdictions = {doc.get("jurisdiction") for _, doc, _ in candidates if doc.get("jurisdiction")}
    paragraphs, used, selected_issues = [], set(), set()
    words = 0
    for issue, doc, card in candidates:
        if doc["id"] in used:
            continue
        explanation = _explanation(doc, card)
        size = len(explanation.split())
        # Never cut a legal sentence or drop a qualifier to meet a word limit.
        # Unmapped reviewed cards can be longer; show one whole proposition.
        if paragraphs and (words + size > 160 or len(paragraphs) >= 4):
            continue
        jurisdiction = doc.get("jurisdiction", "")
        if (jurisdiction and (len(jurisdictions) > 1 or not paragraphs)
                and not re.search(r"\b" + re.escape(jurisdiction) + r"\b", explanation, re.I)):
            explanation = f"{jurisdiction}: {explanation}"
        paragraphs.append(f"{explanation} [{doc['id']}]")
        used.add(doc["id"])
        selected_issues.add(issue.key)
        words += size

    supported_issues = {issue.key for issue, points in rows if points}
    if supported_issues - selected_issues:
        paragraphs.append("Other requested topics and qualifications are covered in the detailed explanation.")
    if missing:
        paragraphs.append("The retrieved sources do not answer: " + "; ".join(dict.fromkeys(missing)) + ".")
    if getattr(plan, "facts", ()) or getattr(plan, "missing_facts", ()) or getattr(plan, "discarded_facts", ()):
        paragraphs.append("This overview does not decide the supplied case facts. The details distinguish individual claims, conditions and unresolved facts.")
    if evidence_limited:
        paragraphs.append("Only the previous answer's sources support this summary.")
    return "\n\n".join(paragraphs)
