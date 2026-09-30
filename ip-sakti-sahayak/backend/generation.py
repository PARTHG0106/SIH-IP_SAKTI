"""Issue-complete answers from reviewed propositions and conditional applications.

Optional models synthesize the current question against retrieved sources, with
evidence-span and entailment checks. Local mode uses reviewed propositions and
conditional case analysis. No retrieval happens here.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from . import llm
from .answer_cards import CARDS, ISSUE_CARDS
from .config import settings
from .planning import plan_query
from .case_analysis import application as _case_application, render_fact_analysis, unanswered
from . import rag, answer_format
from .answer_summary import summarize_local

_ADVICE_GUARD = re.compile(r"\b(should i (?:sue|litigate|file a case)|will i win|my chances|predict (?:my|the) (?:case|outcome)|guarantee (?:me|my)|what damages will i|how much (?:can|will) i (?:win|get|claim|recover))\b", re.I)
_MEDICAL_GUARD = re.compile(r"\b(what dose|dosage should|diagnose me|treat my|how much .{0,60}(?:should i take|give my child))\b", re.I)
_CURRENT = re.compile(
    r"\b(?:current|latest|up.to.date|live)\s+(?:legal\s+)?(?:status|law|rules?|requirements?|position|counts?|numbers?|version|amendments?)\b"
    r"|\b(?:in force|still (?:valid|applicable|effective)|as of today|as of 20\d\d|status today)\b"
    r"|\b(?:has|have|is|are|was|were)\b[^.!?\n]{0,65}\b(?:repealed|amended|suspended|revoked|ratified|omitted)\b"
    r"|\b(?:is|are|does|do)\b[^.!?\n]{0,60}\b(?:apply|effective|valid|operative|binding|enforceable)\b[^.!?\n]{0,25}\b(?:now|today|currently|yet)\b", re.I)
INSUFFICIENT = "Insufficient evidence in retrieved sources."


def _current_requested(query, doc):
    # Applicant/company status is not a request for live legal status.
    return bool(_CURRENT.search(query or "") or (
        doc["id"] in {"rule_170", "wipo_gratk", "tkdl"}
        and re.search(r"\bstatus\b|\bhow many\b.{0,100}\b(?:now|today|currently)\b", query or "", re.I)))


def _label(conf):
    return "High" if conf >= 0.6 else "Medium" if conf >= 0.35 else "Low"


def abstain(reason, message, confidence=0.0, sources=None):
    return {"answer": message, "abstained": True, "escalate": True,
            "confidence": confidence, "confidence_label": _label(confidence),
            "citations_used": sources or [], "answer_source": "abstain",
            "as_of": None, "reason": reason, "notices": []}


def _card(doc, issue_key=None):
    """Fail closed if a source changed after its answer card was reviewed."""
    scoped = issue_key in ISSUE_CARDS
    card = ISSUE_CARDS[issue_key].get(doc["id"]) if scoped else CARDS.get(doc["id"])
    if not card:
        return None
    try:
        reviewed = json.loads(Path(__file__).with_name("answer_card_sources.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    digest = source_fingerprint(doc)
    key = f"{issue_key}/{doc['id']}" if scoped else doc["id"]
    return card if digest in reviewed.get(key, []) else None


def source_fingerprint(doc):
    bound = {key: doc[key] for key in ("id", "text", "section", "statute", "source_url", "jurisdiction")}
    return hashlib.sha256(json.dumps(bound, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _cell(text):
    return text.replace("|", "\\|").replace("\n", " ")


def _cite(text, source):
    return f"{text} [{source['id']}]"


def _application(doc, card, facts):
    return _case_application(doc, card, facts)


def _points(issue, evidence):
    # Keep the reviewed issue order: the central statutory rule precedes its
    # procedural elaborations regardless of a retrieval/model ranking.
    by_id = {row["doc"]["id"]: row["doc"] for row in evidence}
    points = []
    for source_id in issue.source_ids:
        doc = by_id.get(source_id)
        card = _card(doc, issue.key) if doc else None
        if card:
            points.append((doc, card))
    return points


def _issue_row(issue, points, facts, *, decision=False):
    if not points:
        missing = f"Not established by retrieved sources: {INSUFFICIENT}"
        if decision:
            return [issue.title, missing, missing, missing,
                    "Inference/application: Obtain primary-source evidence for this issue before deciding.", missing]
        return [issue.title, INSUFFICIENT, INSUFFICIENT, missing, missing]
    established = " ".join(_cite(c.established + f" ({d['jurisdiction']}; {d['section']})", d) for d, c in points)
    applications = " ".join(_cite(_application(d, c, facts), d) for d, c in points)
    unknown = " ".join(dict.fromkeys(unanswered(d, c, facts) for d, c in points))
    sections = "; ".join(f"{d['statute']} — {d['section']} [{d['id']}]" for d, _ in points)
    if decision:
        actions = " ".join(_cite(c.action, d) for d, c in points)
        sources = "; ".join(f"[{d['id']}]({d['source_url']}) ({d['as_of']})" for d, _ in points)
        return [issue.title, "Inference/application: " + applications,
                "Established by source: " + sections,
                "Established by source: " + established,
                "Inference/application: " + actions + " Not established by retrieved sources: " + unknown,
                sources]
    return [issue.title, "Established by source: " + established, sections,
            "Inference/application: " + applications,
            "Not established by retrieved sources: " + unknown]


def _strategy(rows):
    groups = (
        ("Preserve confidentiality and decide what to disclose", ("secrecy",)),
        ("Confirm the product category and licensing path", ("classification", "cosmetic", "cosmetic_licensing", "manufacturing", "food", "phytopharmaceutical")),
        ("Resolve material sourcing and access obligations", ("access", "intimation", "sourcing")),
        ("Assess the proposed patent claims", ("patent", "exclusions", "examination")),
        ("Verify inventorship and the chain of title", ("ownership",)),
        ("Plan biodiversity IP and benefit-sharing steps", ("biodiversity_ip", "abs")),
        ("Select the applicable brand and other IP protection", ("trademark", "copyright", "gi", "plant_variety", "design", "pct", "madrid", "hague")),
        ("Complete the applicable authority and launch checks", ("authorities", "advertising", "working")),
    )
    actions, seen = [], set()
    for title, keys in groups:
        points = [(d, c) for issue, source_points in rows if issue.key in keys for d, c in source_points]
        fresh = [(d, c) for d, c in points if d["id"] not in seen][:2]
        if not fresh:
            continue
        seen.update(d["id"] for d, _ in fresh)
        actions.append(f"Inference/application — {title}: " + " ".join(_cite(c.action, d) for d, c in fresh))
    return "\n\n".join(f"{n}. {action}" for n, action in enumerate(actions, 1))


def generate(query, results, confidence, jurisdiction, category=None, *, use_llm=True,
             context_query=None, evidence_limited=False, plan=None):
    """Answer current instructions. Supplied documents are the evidence universe."""
    if _ADVICE_GUARD.search(query or ""):
        return abstain("individual_legal_advice", "I can explain sourced rules, but cannot predict your case or decide whether you should litigate. Consult a qualified IP or legal professional.", confidence)
    if _MEDICAL_GUARD.search(query or ""):
        return abstain("medical_advice", "This service covers IP and regulatory information, not individual diagnosis or dosing. Please consult a qualified healthcare professional.", confidence)
    plan = plan or plan_query(query, context_query)
    if plan.scope == "out_of_scope":
        result = abstain("out_of_scope", "This assistant covers Ayurveda intellectual property and regulatory guidance. Explain the Ayurveda connection to this question.")
        result["escalate"] = False
        return result
    candidates = [r for r in results if (jurisdiction == "Both" or r["doc"]["jurisdiction"] == jurisdiction)
                  and (evidence_limited or r.get("bm25", 1) > 0)]
    minimum = max(1, settings.min_citations)
    if candidates:
        top = candidates[0]["doc"]
        if top.get("review_status") == "needs_review" and len(plan.issues) <= 2:
            return abstain("source_review_required", "The most relevant research note needs primary-source review, so I cannot use it to give a reliable answer. " + (top.get("review_note") or ""), confidence, candidates[:1])
        if top.get("time_sensitive") and _current_requested(query, top) and len(plan.issues) <= 2:
            return abstain("current_status_unverified", f"I cannot confirm the current status from this dated corpus. The relevant record is dated {top['as_of']}. Check the linked source for later changes before relying on its status or counts.", confidence, candidates[:1])
    if (not candidates or confidence < settings.abstain_threshold) and not (evidence_limited and plan.issues):
        return abstain("insufficient_evidence", "I do not have enough relevant source material for this question in the selected scope. Try a more specific IP or regulatory question, check the jurisdiction, or consult a qualified professional.", confidence)
    eligible = [r for r in candidates if r["doc"].get("review_status") != "needs_review"
                and not (r["doc"].get("time_sensitive") and _current_requested(query, r["doc"]))]
    answer_source, notices = "grounded_synthesis", []
    withheld = [r["doc"]["id"] for r in candidates if r not in eligible]
    if withheld:
        notices.append("Records needing review or a live status check were withheld: " + ", ".join(withheld) + ". The remaining sources do not establish completeness of current law.")
    if use_llm and eligible and llm.available():
        checked = [r for r in eligible if r["doc"]["id"] not in CARDS or _card(r["doc"])]
        synthesis = rag.synthesize(query, context_query, plan, checked)
        if synthesis:
            # Custom table columns can omit a source shown in the short answer.
            # Both visible parts of the response must retain their citations.
            rendered_ids = set(re.findall(r"\[([a-z0-9_]+)\]",
                                          synthesis["answer"] + "\n" + synthesis["summary"]))
            used = [r for r in checked if r["doc"]["id"] in rendered_ids]
            if len(used) >= minimum:
                dates = [r["doc"]["as_of"] for r in used]
                model_notices = notices + ["Question-specific AI synthesis was checked against the retrieved sources. These checks do not certify legal accuracy or current law."]
                if evidence_limited:
                    model_notices.append("Only the previous answer's source snapshot was used; no new retrieval occurred.")
                if synthesis["missing"]:
                    model_notices.append("Evidence gaps remain for: " + "; ".join(synthesis["missing"]) + ".")
                return {"answer": synthesis["answer"], "summary": synthesis["summary"], "abstained": False,
                        "escalate": bool(synthesis["missing"]), "confidence": confidence,
                        "confidence_label": _label(confidence), "citations_used": used,
                        "answer_source": "rag_synthesis", "as_of": min(dates), "reason": None,
                        "notices": model_notices}
        notices.append("AI synthesis was unavailable or did not pass the source checks. Reviewed local guidance is shown.")
    else:
        notices.append("Local source mode: reviewed guidance is adapted to identified facts and topics. A configured AI provider enables question-specific synthesis; local language understanding is limited.")
    issues = list(plan.issues)
    if not issues:
        return abstain("unsupported_question", "Insufficient evidence in retrieved sources. I could not map this question to a reviewed legal proposition. Ask about a specific IP right, regulatory category or cited provision.", confidence)
    rows = [(issue, _points(issue, eligible)) for issue in issues]
    used_ids = {d["id"] for _, points in rows for d, _ in points}
    used = [r for r in eligible if r["doc"]["id"] in used_ids]
    if len(used) < minimum and not (evidence_limited and len(used) == 0 and minimum == 1):
        reason = "insufficient_citations" if eligible else "insufficient_evidence"
        return abstain(reason, "Insufficient evidence in retrieved sources. There are too few usable, reviewed sources to support the requested answer.", confidence)
    if evidence_limited:
        notices.append("This answer uses only the source snapshot from the previous answer. Missing issues have not triggered a new search.")
    missing = [issue.title for issue, points in rows if not points]
    if missing:
        notices.append("Evidence gaps remain for: " + "; ".join(missing) + ".")
    stale = [r["doc"]["id"] for r in eligible if r["doc"]["id"] in CARDS and not _card(r["doc"])]
    if stale:
        notices.append("Source text changed after answer review; synthesis is withheld for: " + ", ".join(stale) + ".")
    next_steps_only = bool(re.search(r"what should i do next", query, re.I))
    if next_steps_only:
        answer = _strategy(rows) or "Not established by retrieved sources: " + INSUFFICIENT
    elif plan.table:
        lines = answer_format.header(plan)
        for issue, points in rows:
            # A short table retains the central statutory rule and its complete
            # qualifications; procedural elaborations remain in longer answers.
            compact = points
            if plan.concise and issue.key not in {"classification", "exclusions", "cosmetic", "ownership"}:
                compact = points[:1]
            title, established, references, applied, gaps = _issue_row(issue, compact, plan.facts_query)
            actions = "Inference/application: " + " ".join(_cite(c.action, d) for d, c in compact) if compact else gaps
            if compact:
                actions += " " + gaps
            sources = "; ".join(f"[{d['id']}]({d['source_url']}) ({d['as_of']})" for d, _ in compact) or gaps
            lines.append(answer_format.row(plan, issue=title, established=established,
                references=references, application=applied, gaps=gaps, actions=actions, sources=sources))
        answer = "\n".join(lines)
    elif plan.concise:
        brief = []
        for issue, points in rows:
            if not points:
                brief.append(f"- **{issue.title}** — Not established by retrieved sources: {INSUFFICIENT}")
                continue
            doc, card = points[0]
            # Preserve all retrieved legal qualifications (for example the
            # separate s.3 exclusions), but omit repeated applications.
            brief.append((f"- **{issue.title}** — " if len(rows) > 1 else "") + "Established by source: "
                         + " ".join(_cite(c.established + f" ({d['jurisdiction']}; {d['section']})", d) for d, c in points)
                         + " Inference/application: " + " ".join(_cite(_application(d, c, plan.facts_query), d) for d, c in points)
                         + " Not established by retrieved sources: " + " ".join(dict.fromkeys(unanswered(d, c, plan.facts_query) for d, c in points)))
        answer = "\n\n".join(brief)
    else:
        paragraphs = []
        for issue, points in rows:
            if not points:
                paragraphs.append(f"**{issue.title}**\n\nNot established by retrieved sources: {INSUFFICIENT}")
                continue
            paragraphs.append((f"**{issue.title}**\n\n" if len(rows) > 1 else "")
                + "Established by source: " + " ".join(_cite(c.established + f" ({d['jurisdiction']}; {d['section']})", d) for d, c in points)
                + "\n\nInference/application: " + " ".join(_cite(_application(d, c, plan.facts_query), d) for d, c in points)
                + "\n\nNot established by retrieved sources: " + " ".join(dict.fromkeys(unanswered(d, c, plan.facts_query) for d, c in points)))
        answer = "\n\n".join(paragraphs)
    facts_block = "" if plan.table and plan.concise and not plan.discarded_facts else render_fact_analysis(plan, rows)
    if facts_block and not next_steps_only:
        answer = facts_block + "\n\n" + answer
    if plan.steps and not next_steps_only:
        answer += "\n\n**Step-by-step strategy**\n\n" + (_strategy(rows) or "Not established by retrieved sources: " + INSUFFICIENT)
    if plan.table and evidence_limited:
        answer = "Established by source: The conclusions below are limited to the previous answer's retrieved source set.\n\n" + answer
    # Citation objects describe evidence actually used in the rendered answer,
    # so a shortened follow-up does not silently retain uncited source records.
    rendered_ids = set(re.findall(r"\[([a-z0-9_]+)\]", answer))
    used = [r for r in used if r["doc"]["id"] in rendered_ids]
    if len(used) < minimum and not (evidence_limited and not used and minimum == 1):
        return abstain("insufficient_citations", "Insufficient evidence in retrieved sources. The rendered answer does not meet the configured minimum source count.", confidence)
    dates = [r["doc"]["as_of"] for r in used]
    # Only summarize sources actually present in the detailed answer, including
    # short/source-only follow-ups that intentionally narrow the evidence set.
    summary_rows = [(issue, [(d, c) for d, c in points if d["id"] in rendered_ids])
                    for issue, points in rows]
    summary = summarize_local(query, plan, summary_rows, evidence_limited=evidence_limited)
    notices += list(dict.fromkeys(r["doc"]["review_note"] for r in used if r["doc"].get("review_note")))
    return {"answer": answer, "summary": summary, "abstained": False, "escalate": bool(missing),
            "confidence": confidence, "confidence_label": _label(confidence),
            "citations_used": used, "answer_source": answer_source,
            "as_of": min(dates) if dates else None, "reason": None, "notices": notices}
