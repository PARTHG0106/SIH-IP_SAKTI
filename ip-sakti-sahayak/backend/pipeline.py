"""Shared answer pipeline for HTTP requests and reproducible offline evaluations."""
from __future__ import annotations

import re
from uuid import uuid4
from . import generation, i18n
from .config import DISCLAIMER
from .models import AskRequest, AskResponse, RegistryLink
from .memory import ConversationStore, Turn, context_for, needs_history, source_only
from .sources import citation
from .planning import plan_query

_INTERNATIONAL = re.compile(r"\b(wipo|gratk|pct|trips|madrid|hague|budapest|nagoya|eu|european union|united states|(?-i:USA|US))\b", re.I)
_INDIA = re.compile(r"\b(rule 170|form 27|rule 158b|fssai|sbb|nba|first.schedule|inpass)\b", re.I)


class Assistant:
    def __init__(self, retriever, router, memory=None):
        self.retriever = retriever
        self.router = router
        self.memory = memory if memory is not None else ConversationStore()

    def answer(self, req: AskRequest, *, use_llm=True) -> AskResponse:
        if req.conversation_id:
            with self.memory.transaction(req.conversation_id, (req.jurisdiction, req.category, req.regime)) as chat:
                return self._answer(req, use_llm=use_llm, chat=chat)
        return self._answer(req, use_llm=use_llm)

    def _answer(self, req: AskRequest, *, use_llm=True, chat=None) -> AskResponse:
        query_en, input_translated = i18n.to_english(req.query, req.lang, use_llm=use_llm)
        translation_status = "not_requested" if req.lang == "en" else "unavailable"
        previous = context_for(chat.turns, query_en) if chat is not None else None
        context_query = previous.context_query if previous else None
        limited = source_only(query_en)
        version = previous.corpus_version if previous and limited else self.retriever.corpus.version
        # Keep the prior source set immutable; corpus changes cannot expand a
        # follow-up expressly limited to sources already shown to the user.
        evidence_turn = chat.turns[-1] if previous and chat.turns else None
        results = []
        language_selection = req.lang == "en" and i18n.requires_language_selection(req.query)
        language_unavailable = language_selection or (req.lang != "en" and not input_translated)
        plan = plan_query(query_en, context_query, use_llm=use_llm and not language_unavailable)
        # Explicitly requested India + foreign analysis is split by source
        # jurisdiction, even when India remains the home-market UI setting.
        foreign = bool(set(plan.markets) & {"EU", "US"}) or bool(
            {issue.key for issue in plan.issues} & {"gratk", "pct", "trips", "madrid", "hague", "budapest", "nagoya"})
        mixed = "India" in plan.markets and foreign
        research_scope = "Both" if mixed or req.jurisdiction == "Both" else req.jurisdiction
        if limited and evidence_turn and len({r["doc"]["jurisdiction"] for r in evidence_turn.sources}) > 1:
            research_scope = "Both"
        if language_unavailable:
            translation_status = "language_selection_required" if language_selection and i18n.available() else "unavailable"
            gen = generation.abstain(
                "translation_unavailable",
                ("This question contains substantial text in an Indic script, while English is selected. "
                 "Select the intended language so it can be translated." if language_selection and i18n.available() else
                 "Translation is unavailable in this local configuration, so I cannot reliably interpret this question in the "
                 "selected language. Please ask in English, or configure a translation provider."))
            gen["escalate"] = False
        elif plan.scope == "out_of_scope":
            gen = generation.abstain("out_of_scope", "IP-SAKTI Sahayak covers intellectual property and regulatory guidance for Ayurveda, in India and internationally. This question describes a different field. Explain its connection to an Ayurvedic product, research project or business so I can assess the relevant sources.")
            gen["escalate"] = False
        elif ((req.jurisdiction == "India" and foreign
               and not mixed)
              or (req.jurisdiction == "International" and _INDIA.search(plan.substantive_query) and not mixed)):
            gen = generation.abstain(
                "jurisdiction_mismatch",
                "This question names a framework outside the selected jurisdiction. Change the "
                "jurisdiction switch to see the relevant sources; the two scopes stay separate.")
        elif needs_history(query_en) and previous is None:
            gen = generation.abstain(
                "missing_chat_context",
                "I do not have the earlier question and sources in this temporary chat. "
                "Restate the original question here; I cannot reconstruct a previous source set by running a new search.")
        else:
            if limited:
                results, confidence = evidence_turn.sources, evidence_turn.confidence
                version = evidence_turn.corpus_version
            else:
                results, confidence = self.retriever.search(
                    plan.substantive_query, jurisdiction=research_scope, regime=req.regime, category=req.category, plan=plan)
            gen = generation.generate(query_en, results, confidence, research_scope,
                                      req.category, use_llm=use_llm, context_query=context_query,
                                      evidence_limited=limited, plan=plan)
            if research_scope == "Both":
                gen["notices"].append("The question spans India and international regimes; sources retain their jurisdiction labels. Foreign-market evidence does not establish Indian approval, or vice versa.")

        citations = [citation(r["doc"], r["score"]) for r in gen["citations_used"]]
        # A quarantined note is searchable for triage, but its disputed text is withheld.
        for item in citations:
            if item.review_status == "needs_review":
                item.snippet = ""
        regimes = {c.regime for c in citations}
        links = []
        for scope in dict.fromkeys(c.jurisdiction for c in citations):
            scoped_regimes = {c.regime for c in citations if c.jurisdiction == scope}
            links.extend(self.router.route(scope, scoped_regimes, req.category))
        answer_out, translated = gen["answer"], False
        notices = list(gen.get("notices", []))
        if previous and not limited:
            notices.append("Used earlier question context from this temporary chat.")
        if input_translated:
            answer_out, translated = i18n.from_english(gen["answer"], req.lang, use_llm=use_llm)
            translation_status = "translated" if translated else "output_failed"
            if not translated:
                notices.append("Answer translation failed or changed citation markers. The English answer is shown.")
        if translated:
            notices.append("Machine-translated guidance. Consult the original English source notes for legal wording.")
        if citations:
            notices.append("The answer separates sourced rules from application and evidence gaps. Source cards contain curated summaries, not statutory quotations.")
        dates = [c.as_of for c in citations]
        response = AskResponse(
            answer=answer_out, abstained=gen["abstained"], confidence=gen["confidence"],
            confidence_label=gen["confidence_label"], jurisdiction=req.jurisdiction,
            lang=req.lang if translated else "en", requested_lang=req.lang, category=req.category,
            citations=citations, registry_links=[RegistryLink(**link) for link in links],
            escalate=gen["escalate"], as_of=min(dates) if dates else None,
            source_date_range={"oldest": min(dates), "newest": max(dates)} if dates else None,
            disclaimer=DISCLAIMER, answer_source=gen["answer_source"],
            original_answer_en=gen["answer"] if translated else None,
            translation_status=translation_status, notices=list(dict.fromkeys(notices)),
            reason=gen.get("reason"), corpus_version=version,
            request_id=str(uuid4()), conversation_id=req.conversation_id,
            memory_used=previous is not None, evidence_scope="previous_turn" if limited else "corpus",
            context_question=context_query if previous else None)
        if chat is not None and gen.get("reason") not in {
            "missing_chat_context", "missing_previous_evidence", "translation_unavailable", "jurisdiction_mismatch",
            "out_of_scope",
        }:
            # At most 12k characters of context per retained turn. Preserve the
            # original question and the most recent facts, never generated prose.
            context = plan.facts_query
            if len(context) > 12000:
                context = context[:4000] + "\n[Older follow-up context omitted]\n" + context[-7900:]
            self.memory.append(chat, Turn(query=query_en, context_query=context,
                                          sources=gen["citations_used"], corpus_version=version,
                                          confidence=gen["confidence"]))
        return response
