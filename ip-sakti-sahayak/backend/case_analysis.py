"""Conservative local application of reviewed rules to the current question.

This module adds no evidence and makes no provider calls. Its inputs are the
reviewed (document, card) pairs that generation actually used. User statements
are unverified assertions; a word such as "new" never establishes a legal test.
"""
from __future__ import annotations

import html
import re

from .answer_cards import CARDS
from .case_state import COUNTRIES, fact_spans


_QUESTION = re.compile(
    r"^\s*(?:whether|what\b|which\b|how\b|why\b|when\b|where\b|who\b|if\b|"
    r"suppose\b|assuming\b|could\b|would\b|can\b|does\b|do\b|is\b|are\b|"
    r"please\b|explain\b|analyse\b|analyze\b|identify\b|compare\b)", re.I)


def _assertions(text: str) -> str:
    """Use the planner's fact boundary, additionally excluding hypotheses."""
    assertions = []
    normalized = "\n".join(re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line)
                           for line in (text or "").splitlines())
    for raw in fact_spans(normalized):
        span = raw.strip()
        span = re.sub(r"^(?:(?:follow-up|correction|actually)\s*:\s*)+", "", span, flags=re.I)
        if span and "?" not in span and not _QUESTION.search(span):
            assertions.append(span)
    return "\n".join(assertions)


def _asserted_word(text: str, pattern: str) -> bool:
    for match in re.finditer(pattern, text, re.I):
        prefix = text[max(0, match.start() - 45):match.start()]
        if not re.search(r"(?:\bnot|\bno|\bnone|\bnever|without|rather than)\b[^,;\n]{0,30}$", prefix, re.I):
            return True
    return False


def _quoted(value: str) -> str:
    return f'“{_text(" ".join(value.split()))}”'


def _disclosure_facts(facts: str) -> tuple[list[str], list[str]]:
    """Keep public and withheld material separate, including mixed sentences."""
    public, private = [], []
    public_pattern = (r"\b(?:publish\w*|publicly\s+(?:disclos\w*|show\w*|present\w*|"
                      r"display\w*|demonstrat\w*|exhibit\w*)|(?:show\w*|present\w*|display\w*|"
                      r"demonstrat\w*|exhibit\w*|disclos\w*).{0,35}publicly|post\w*\s+online|"
                      r"(?:made|make)\s+public)\b")
    private_pattern = re.compile(
        r"\b(?:(?:did|do|does|have|has|had|was|were|is|are)\s+not|never|haven't|hasn't|didn't)"
        r"\s+(?:been\s+)?(?:publicly\s+)?(?:disclos\w*|publish\w*|reveal\w*|shar\w*|show\w*|"
        r"display\w*|demonstrat\w*|made\s+public)|\b(?:remain\w*|kept|keep|still)\s+"
        r"(?:\w+\s+){0,3}(?:secret|confidential|undisclosed|private)\b", re.I)
    for sentence in _assertions(facts).splitlines():
        for clause in re.split(r"\s*;\s*|,?\s+\b(?:but|whereas|while)\b\s+", sentence, flags=re.I):
            public_event = bool(re.search(r"\b(?:trade fair|public exhibition|public demonstration)\b", clause, re.I)
                                and _asserted_word(clause, r"\b(?:showed|shown|demonstrat\w*|display\w*|exhibit\w*|handed\s+out|distributed)\b"))
            if _asserted_word(clause, public_pattern) or public_event:
                public.append(clause.strip())
            if private_pattern.search(clause):
                private.append(clause.strip())
    return list(dict.fromkeys(public)), list(dict.fromkeys(private))


def _entity_facts(facts: str) -> list[str]:
    return [span for span in _assertions(facts).splitlines()
            if re.search(r"compan|entit|incorporat|shareholder|applicant|citizen|residen", span, re.I)
            and re.search(r"owned|ownership|control|incorporat|shareholder|citizen|residen|nationality", span, re.I)]


def _sourcing_facts(facts: str) -> list[str]:
    return [span for span in _assertions(facts).splitlines()
            if re.search(r"\b(?:plants?|herbs?|materials?|resources?)\b", span, re.I)
            and re.search(r"cultivat|grown|sourc|collect|farm|trader|supplier", span, re.I)]


def _medicinal_claims(facts: str) -> list[str]:
    return [span for span in _assertions(facts).splitlines()
            if re.search(r"website|label|advertis|claim|say", span, re.I)
            and _asserted_word(span, r"\b(?:cures?|treats?|prevents?|treating|curing|preventing)\b")]


def _unproved_eu_history(facts: str) -> list[str]:
    return [span for span in _assertions(facts).splitlines()
            if re.search(COUNTRIES["EU"], span, re.I)
            and re.search(r"(?:not|no|lack|never).{0,90}(?:history|medicinal.use)|"
                          r"(?:history|medicinal.use).{0,50}(?:unproven|undocumented|unverified|unknown|"
                          r"not\s+(?:yet\s+)?(?:proved|established|documented|verified))", span, re.I)]


def _claim_blocks(facts: str) -> list[tuple[str, str]]:
    """Associate evidence with its named claim rather than another nearby claim."""
    asserted = _assertions(facts)
    starts = list(re.finditer(r"\bClaim\s+([A-Z]|\d+)\b", asserted))
    if not starts:
        return [("The described claim", asserted)]
    blocks = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(asserted)
        block = asserted[match.start():end].strip()
        # A separately described process is not evidence about the preceding claim.
        block = re.split(r"\b(?:(?:We|I)\s+(?:also\s+)?have\s+(?:a\s+)?|(?:A|An|The)\s+)separate\b", block)[0].strip()
        blocks.append((f"Claim {match[1]}", block))
    return blocks


def _efficacy_result(text: str) -> str:
    negative = re.search(
        r"\bno\s+(?:\w+\s+){0,2}(?:enhancement|improvement|increase)\s+(?:in|of)\s+(?:\w+\s+){0,2}efficacy"
        r"|\b(?:did|does|do)\s+not\s+(?:enhance|improve|increase)\s+(?:\w+\s+){0,2}efficacy"
        r"|\befficacy\s+(?:is|was|remains?)\s+(?:unchanged|not\s+(?:enhanced|improved|increased))", text, re.I)
    if negative:
        return "negative"
    if _missing_study(text):
        return "missing"
    if _asserted_word(text, r"\b(?:tests?|results?|data|evidence|experiments?|stud(?:y|ies)).{0,55}"
                      r"(?:show\w*|suggest\w*|found|demonstrat\w*).{0,30}"
                      r"(?:enhanc\w*|improv\w*|increas\w*).{0,30}efficacy\b|"
                      r"\befficacy\s+(?:is|was|has\s+been)\s+(?:enhanced|improved|increased)\b"):
        return "positive"
    return "unknown"


def _missing_study(text: str) -> bool:
    return bool(re.search(
        r"\bno\s+(?:\w+\s+){0,4}(?:experiment|study|comparison|data|evidence|test)\b"
        r"|\b(?:experiment|study|comparison|testing|data|evidence|results?)\b.{0,45}"
        r"(?:not\s+(?:yet\s+)?(?:been\s+)?(?:completed|performed|conducted|available|collected)|pending|unavailable)"
        r"|\b(?:not|never)\s+(?:yet\s+)?(?:performed|conducted|completed)\b.{0,35}"
        r"(?:experiment|study|comparison|test)\b", text, re.I))


def _additive_result(text: str) -> bool:
    # Absence of synergy data alone does not establish a mere aggregation.
    return bool(re.search(
        r"\bonly\s+(?:(?:show\w*|produce\w*|give\w*|provide\w*|an?|the)\s+){0,3}"
        r"(?:sum|aggregation|additive|known\s+effects)\b"
        r"|\b(?:effects?|results?|activity)\s+(?:are|is|were|was)\s+(?:merely\s+|only\s+)?additive\b"
        r"|\bmerely\s+additive\b", text, re.I))


def _mixture_result(text: str) -> str:
    if _additive_result(text):
        return "additive"
    # A suggestion of interaction is a reported finding, not verified synergy.
    if _asserted_word(text, r"\binteraction\s+beyond\b.{0,45}(?:sum|separate\s+effects|individual\s+effects|"
                      r"component\s+effects)|\b(?:non[- ]additive|synergistic)\s+(?:effect|interaction|activity)|"
                      r"\b(?:evidence|results?|data).{0,35}(?:suggest\w*|show\w*|demonstrat\w*).{0,20}synergy\b"):
        return "interaction"
    if _missing_study(text):
        return "missing"
    return "unknown"


def _relevant_claims(facts: str, family: str) -> list[tuple[str, str]]:
    pattern = (r"\b(?:salt|polymorph|ester|new\s+form|known\s+(?:active|substance))\b"
               if family == "form" else r"\b(?:combin\w*|mix\w*|blend|admixture|herbs|components)\b")
    return [(name, block) for name, block in _claim_blocks(facts) if re.search(pattern, block, re.I)]


def _formula_status(facts: str) -> str:
    """A development claim or a 'proprietary' label is not a formula comparison."""
    asserted = _assertions(facts)
    absent = re.search(
        r"(?:formula(?:tion)?|combination|recipe).{0,65}(?:not\s+(?:included|found|disclosed|described|present)|absent)"
        r".{0,35}(?:book|text|schedule)|"
        r"(?:formula(?:tion)?|combination|recipe).{0,40}(?:does not|doesn't)\s+match.{0,35}(?:book|text|formula)|"
        r"(?:not|no longer)\s+(?:an?\s+)?classical\s+(?:formula|medicine)", asserted, re.I)
    exact = re.search(
        r"(?:formula(?:tion)?|recipe|medicine|product|manufactur\w*).{0,65}"
        r"(?:exactly\s+(?:matches?|follows?|as|according to)|unchanged\s+from|"
        r"exclusively\s+according to).{0,60}(?:book|text|formula|schedule|samhita)|"
        r"(?:same|identical)\s+formula.{0,35}(?:first.schedule|classical text|authoritative book)", asserted, re.I)
    if bool(absent) == bool(exact):
        return "unknown"
    return "absent" if absent else "exact"


def application(doc: dict, card, facts_query: str) -> str:
    """Apply only this reviewed card; otherwise retain its reviewed application."""
    source_id = doc["id"]
    facts = _assertions(facts_query)
    # Scoped authority/source-record cards must not expand to a whole statute.
    full_card = card == CARDS.get(source_id)
    if source_id == "phytopharma_gsr918":
        if not full_card:
            return ("Assess CDSCO only if the product meets the cited phytopharmaceutical definition; "
                    "the number of plants alone does not establish that category.")
        return ("A plant count or a new herbal combination does not establish the required purified, "
                "standardised fraction and compound characterisation. Confirm those features before applying this category.")
    if source_id == "bda_ipr_forms" and _sourcing_facts(facts):
        sourcing = " ".join(_quoted(span) for span in _sourcing_facts(facts))
        if not full_card:
            return (f"Your sourcing account is {sourcing} Cultivation or Indian sales alone do not "
                    "establish the foreign-source trigger for Form 10. Apply that "
                    "provision only to qualifying material actually obtained from another country; "
                    "verify the farm or supplier location and material origin.")
        return (f"You supplied a sourcing account: {sourcing} Match the actual applicant and IP activity "
                "to the cited approval, registration or commercialisation form. Do not assume that a "
                "foreign-source Form 10 applies without evidence that the covered resources or knowledge "
                "were obtained from another country; verify actual origin rather than inferring it from sales markets.")
    if not full_card:
        return card.application
    if source_id == "patents_ownership":
        contributions = [span for span in facts.splitlines()
                         if re.search(r"employee|university|laboratory|contributor|designer|contractor", span, re.I)]
        supplied = f"You report {' '.join(_quoted(span) for span in contributions)} " if contributions else ""
        return (supplied + "Identify the human contributors to the claimed invention separately from the "
                "person or entity entitled to apply. If the company relies on assignment of the right to "
                "apply, it needs the applicable proof while the inventor remains identified. Employment, "
                "payment and a university collaboration do not supply that proof in this record. The "
                "company's claimed title remains unresolved until the contributions and "
                "chain of title are checked; mention as inventor does not itself confer patent rights.")
    if source_id == "patents_assignments":
        return ("For a transaction in an existing patent, assess the written, duly executed instrument "
                "and registration of the acquired title or interest under these provisions. Keep that "
                "separate from proof of an assignment of the right to apply before grant. Inspect the "
                "actual employment, university and other agreements for invention scope, retained rights "
                "and execution; payment or a confidentiality clause does not establish the required "
                "assignment here. These patent provisions do not decide copyright ownership of artwork.")
    if source_id == "dc_cosmetic":
        uses = [span for span in facts.splitlines()
                if re.search(r"condition|beautif|appearance|cleans|cosmetic|no disease|external|topical", span, re.I)]
        if uses:
            return (f"Your stated product/use facts are {' '.join(_quoted(span) for span in uses)} "
                    "A cosmetic classification is possible if the actual intended function fits the cited "
                    "cleansing, beautifying, attractiveness or appearance purposes. An external route and "
                    "absence of a disease-treatment claim alone do not prove the classification; review "
                    "the complete formulation, presentation and all claims. Ayurvedic ingredients or the "
                    "word Ayurvedic do not by themselves require the medicine route.")
    if source_id == "dc_cosmetic_licensing":
        return ("If this product is confirmed to be a cosmetic, assess the cited State cosmetic "
                "manufacturing-licence route for the actual premises and licence or loan-licence arrangement. "
                "Confirm ingredient history against the specific new-cosmetic definition before deciding "
                "whether prior Central permission is required. An own-farm supply or an Indian owner "
                "does not establish the required premises or licence compliance.")
    if source_id == "eu_thmpd":
        history = _unproved_eu_history(facts)
        claims = _medicinal_claims(facts)
        market = "German" if re.search(r"\bgermany\b|\bgerman\b", facts, re.I) else "target EU Member State's"
        parts = []
        if history:
            parts.append(f"You report {' '.join(_quoted(span) for span in history)} The supplied evidence "
                         "therefore does not establish the cited 30-year medicinal-use history including "
                         "15 years in the EU. Unproved history is not proof that the product has no such "
                         "history, but a proposed traditional-herbal-medicine label cannot replace that evidence.")
        if claims:
            parts.append(f"Your proposed medicinal claim is {' '.join(_quoted(span) for span in claims)} "
                         "This use-history source does not establish whether that specific claim or the "
                         f"proposed dosage is admissible for the {market} route; obtain the relevant "
                         "indication, claims and registration evidence before concluding eligibility.")
        if parts:
            return " ".join(parts)
    if source_id == "dmr_act" and _medicinal_claims(facts):
        claims = " ".join(_quoted(span) for span in _medicinal_claims(facts))
        return (f"You propose this medicinal advertising wording: {claims} The wording has been "
                "supplied; assess the stated indication against the specified restrictions and assess "
                "whether the claim is misleading under the cited provisions. This reviewed summary "
                "does not establish that the particular indication is prohibited, that the claim is "
                "substantiated, or that publication is lawful. A product licence or IP right does not "
                "resolve those advertising questions; check the applicable current provisions and full advertisement.")
    if source_id == "dc_3a":
        status = _formula_status(facts_query)
        intended_use = ("The classical ASU route first requires medicinal intended use for diagnosis, "
                        "treatment, mitigation or prevention of disease or disorder. A formula match "
                        "alone does not establish that use. ")
        if re.search(r"\bno\s+(?:disease[- ]treatment|therapeutic|disease)\s+claim|"
                     r"\bonly\b.{0,45}\b(?:conditioning|beautifying|cleansing)\b", facts, re.I):
            intended_use += ("Your stated conditioning/cosmetic-purpose or no-disease-claim account does "
                             "not establish this medicinal threshold; assess the actual intended function "
                             "and presentation before choosing an ASU medicine route. ")
        if status == "exact":
            return (intended_use + "You describe an exact classical-formula match. If the medicinal-use "
                    "threshold is met and the complete formula and manufacture are verified against a "
                    "First-Schedule authoritative book, the classical route may fit; "
                    "the stated match has not been independently verified.")
        if status == "absent":
            return (intended_use + "You state that the formulation does not match a classical formula. If that comparison is "
                    "confirmed against the First-Schedule books, it would not meet this classical-formula test.")
        return (intended_use + "Classical status remains unresolved: compare the complete formula and manufacture with a "
                "First-Schedule formula. Developing a combination yourself or studying classical texts does "
                "not establish either a match or its absence.")
    if source_id == "dc_3h":
        return ("First establish that the product is an ASU medicine on its actual intended use; an "
                "ingredient-book match alone does not classify a nonmedicinal product as a medicine. "
                "The proprietary category is then conditional on every ingredient meeting the First-Schedule "
                "book test, the formulation itself being absent from those formulae, and a non-parenteral route. "
                "Calling the product new or proprietary does not verify those facts or establish patentability.")
    if source_id == "patents_invention":
        process = next((span for span in facts.splitlines()
                        if re.search(r"\bseparate\b.{0,30}\b(?:process|method)\b", span, re.I)), "")
        if process:
            return (f"You describe a separate process: {_quoted(process)}. Assess its actual claims "
                    "independently for novelty, inventive step and industrial applicability; saying the "
                    "process might be new, or reporting an incomplete prior-art search, does not establish "
                    "those tests. The conclusions on a salt or mixture do not decide this separate process.")
        return ("Assess the specific formulation or manufacturing-process claims for novelty, inventive step "
                "and industrial applicability. The stated development history or a new product label does "
                "not establish those tests.")
    if source_id == "patents_3p":
        if any(_efficacy_result(block) != "unknown" or _mixture_result(block) != "unknown"
               for _, block in _claim_blocks(facts)):
            return ("Assess each claim separately against the actual traditional-knowledge teachings and known "
                    "properties of traditionally known components. The supplied claim descriptions and study "
                    "status address different questions; they do not alone establish whether a claim merely "
                    "reproduces traditional knowledge under section 3(p).")
        if re.search(r"(?:stud(?:y|ied|ying)|read|consult|review).{0,55}(?:classical|ayurved|texts?|books?)", facts, re.I):
            return ("Studying classical texts identifies material for a traditional-knowledge comparison; "
                    "it does not by itself decide the entire invention's eligibility. Compare each claimed "
                    "feature and effect with those teachings; reproducing traditional knowledge or known "
                    "properties can engage this exclusion.")
        return ("Compare the proposed claims with traditional knowledge and the known properties of "
                "traditionally known components; a new product description does not establish that this exclusion is overcome.")
    if source_id == "patents_3d":
        claims = _relevant_claims(facts, "form")
        if claims:
            parts = []
            for name, block in claims:
                status = _efficacy_result(block)
                if status == "negative":
                    conclusion = ("If the claim is a new form of a known substance and the reported absence "
                                  "of enhanced known efficacy is confirmed, it falls within the section 3(d) "
                                  "exclusion described by this source. The reported negative result is evidence "
                                  "against that claim under this test; it does not decide a different claim "
                                  "or guarantee the outcome of examination.")
                elif status == "missing":
                    conclusion = ("A missing or incomplete comparative study is not a finding of no enhancement. "
                                  "Section 3(d) requires the new-form question and enhancement of known efficacy "
                                  "to be assessed; obtain the relevant comparative evidence before deciding "
                                  "that test. The reported study status establishes neither enhancement nor "
                                  "its absence, and does not establish patentability.")
                elif status == "positive":
                    conclusion = ("The reported efficacy improvement is relevant to the enhancement question "
                                  "under section 3(d), but its comparator, methods, endpoints and reliability "
                                  "require review. A reported or preliminary improvement does not itself "
                                  "establish that this statutory test is met or that the claim is patentable.")
                else:
                    conclusion = ("The claim description is supplied, but the enhancement-of-known-efficacy "
                                  "question under section 3(d) remains unresolved. Review the actual claimed "
                                  "new form, known comparator and comparative evidence; a new salt or form "
                                  "description alone establishes neither eligibility nor exclusion.")
                parts.append(f"{name}: you state {_quoted(block)}. {conclusion}")
            return " ".join(parts)
    if source_id == "patents_3e":
        claims = _relevant_claims(facts, "mixture")
        if claims:
            parts = []
            for name, block in claims:
                status = _mixture_result(block)
                if status == "additive":
                    conclusion = ("If the claimed substance yields only the aggregation of its components' "
                                  "properties as reported, section 3(e)'s mere-admixture exclusion applies. "
                                  "Preliminary additive results do not establish an effect beyond that aggregation.")
                elif status == "interaction":
                    conclusion = ("The reported interaction beyond the separate component effects is relevant "
                                  "to section 3(e)'s mere-aggregation question. Verify the comparison and "
                                  "reliability, including replication of any preliminary study; a suggested "
                                  "interaction is not established synergy or guaranteed patentability.")
                elif status == "missing":
                    conclusion = ("Missing or incomplete comparative evidence does not establish that the blend "
                                  "is merely additive. Under section 3(e), assess whether its actual properties "
                                  "are only an aggregation of the components' properties; obtain the comparison "
                                  "before reaching a conclusion under this exclusion.")
                else:
                    conclusion = ("The blend description alone does not answer section 3(e). Compare the "
                                  "combination's properties with its separate components to determine whether "
                                  "they are only an aggregation; neither synergy nor mere additivity is "
                                  "established by the description.")
                parts.append(f"{name}: you state {_quoted(block)}. {conclusion} "
                             "Assess a separate process under this provision if it produces a substance "
                             "covered by this exclusion; the other patent requirements remain separate.")
            return " ".join(parts)
    if source_id == "bda_s3":
        supplied = _entity_facts(facts)
        if supplied:
            return (f"You supplied these applicant/entity assertions: {' '.join(_quoted(s) for s in supplied)} "
                    "Verify the actual applicant's incorporation and control, and citizenship/residence where "
                    "applicable, against section 3(2). Stated Indian ownership or a foreign shareholder alone "
                    "does not settle that statutory category. Apply prior NBA approval only to the covered "
                    "applicant and access purpose; company share ownership does not determine ownership of IP.")
        return ("Manufacturing or being incorporated in India alone does not establish the applicant category. "
                "Confirm citizenship/residence where applicable and entity incorporation/control, then assess "
                "whether the proposed resource access requires prior NBA approval under section 3.")
    if source_id == "bda_s7_exemption":
        wild = _asserted_word(facts, r"\bwild(?:[- ]sourced)?\b")
        cultivated = _asserted_word(facts, r"\bcultivat\w*\b|\bgrown\s+on\s+(?:our|my|the)\s+(?:own\s+)?farm\b|\bfarm.grown\b")
        parts = []
        if wild:
            parts.append("For the plants you describe as wild-sourced, the cultivated-medicinal-plant exemption "
                         "has not been established; assess the section 7 trigger and any other relevant exemption for that material.")
        if cultivated:
            parts.append("For the plants you describe as cultivated, verify cultivation and the prescribed BMC "
                         "certificate of origin for each material; a supplier's description alone does not complete that condition.")
        if not parts:
            parts.append("Determine wild or cultivated status separately for each material; the cultivated-medicinal-plant "
                         "exemption requires the prescribed BMC certificate of origin.")
        parts.append("Apply section 7 only to the covered applicant/access route; this exemption does not itself settle separate IP duties.")
        return " ".join(parts)
    if source_id == "bda_s6":
        return ("If the IP is based on the covered Indian-accessed resource or associated knowledge, identify "
                "the applicant category: section 3(2) persons need NBA approval before grant; section 7 persons "
                "need NBA registration before grant and, if they obtain the IP right, prior NBA approval at "
                "commercialisation. Access compliance and these IP milestones require separate checks.")
    if source_id == "bda_sourcing":
        return ("Maintain a separate provenance record for each plant/material and supply batch, distinguishing "
                "wild collection from cultivation even when one supplier supplies both. Record the applicable "
                "Form B particulars; linking invoices and batch records is a practical way to support the claimed provenance.")
    if source_id == "patents_disclosure":
        public, private = _disclosure_facts(facts)
        if public:
            result = (f"You report a public disclosure: {' '.join(_quoted(s) for s in public)} "
                      "Assess precisely what that display, publication or handout made available, its date "
                      "and any specific statutory exception. A general grace period cannot be assumed.")
            if private:
                result += (f" You separately state {' '.join(_quoted(s) for s in private)} "
                           "Distinguish those undisclosed details from the disclosed product and ingredients; "
                           "do not assume that showing the product disclosed every process parameter or that "
                           "keeping some details private cures the earlier disclosure.")
            return result
        if private:
            return (f"You describe information as undisclosed: {' '.join(_quoted(s) for s in private)} "
                    "Confirm the scope of that assertion, access and confidentiality arrangements, and "
                    "whether other disclosures occurred. Assess filing before further disclosure; a "
                    "general grace period cannot be assumed.")
        return ("Confirm whether any relevant information has already become public. If so, its content, "
                "date and any specific statutory exception matter; if not, assess confidentiality and filing "
                "before disclosure. A general grace period cannot be assumed.")
    return card.application


def unanswered(doc: dict, card, facts_query: str) -> str:
    """Describe outstanding verification without erasing facts already supplied."""
    facts = _assertions(facts_query)
    source_id = doc["id"]
    if source_id == "bda_s3" and _entity_facts(facts):
        return ("Ownership/control assertions have been supplied but not verified. Confirm the actual "
                "applicant and documentary incorporation/control or citizenship/residence details, the "
                "access purpose and the material, before deciding the statutory applicant category.")
    if source_id == "bda_ipr_forms" and _sourcing_facts(facts):
        return ("Sourcing facts have been supplied and remain unverified. Confirm the actual farm or "
                "supplier location, material origin and access history, applicant identity and planned IP "
                "activity. Apply provider-country or Form 10 requirements only if foreign acquisition "
                "is established; Indian sales or ownership do not establish resource origin.")
    if source_id == "eu_thmpd" and (_unproved_eu_history(facts) or _medicinal_claims(facts)):
        gaps = ("Product-specific qualifying use records, the final dosage and permissible indications "
                "remain unresolved. The cited use-history rule does not establish the complete "
                "Member-State registration procedure.")
        if _medicinal_claims(facts):
            gaps += " It does not establish legality of the proposed disease claim."
        return gaps
    if source_id == "dmr_act" and _medicinal_claims(facts):
        return ("The proposed medicinal claim wording is supplied. Evidence supporting the claimed "
                "effect, the full advertisement and intended audience, the indication-specific "
                "restrictions and current applicable advertising rules/procedure remain to be verified. "
                "The general DMR summary alone cannot decide this advertisement's legality.")
    if source_id == "patents_3d" and any(_efficacy_result(block) == "negative"
                                        for _, block in _relevant_claims(facts, "form")):
        return ("The reported absence of enhanced efficacy is supplied. The known substance's identity, "
                "precise claim wording and complete comparative test methods/results still need review; "
                "the reported result has not been independently verified.")
    if source_id == "patents_3d" and _relevant_claims(facts, "form"):
        return ("The claim description and stated study status have been supplied. Verify the known "
                "substance's identity, exact claim wording, the relevant efficacy comparison and the "
                "complete methods/results. A missing study and a reported improvement are different "
                "evidentiary positions; neither is a verified conclusion that all patent tests are met.")
    if source_id == "patents_3e" and any(_additive_result(block)
                                        for _, block in _relevant_claims(facts, "mixture")):
        return ("Additive results have been reported. The full comparative study, component baselines and "
                "actual mixture/process claim wording still need review; preliminary results do not "
                "establish a further interaction or decide all other patent tests.")
    if source_id == "patents_3e" and _relevant_claims(facts, "mixture"):
        return ("The blend description and reported study status are supplied. The full component "
                "comparison, methods/results, reliability of any claimed interaction and precise "
                "mixture/process claims need review. Suggested effects and incomplete studies do "
                "not establish synergy or guarantee a patent.")
    if source_id == "patents_disclosure":
        public, private = _disclosure_facts(facts)
        if public or private:
            return ("The supplied disclosure/secrecy account needs documentary verification: the actual "
                    "display or publication and handout, precise dates, recipients, confidentiality terms, "
                    "filing history and any applicable statutory exception. Its effect on each proposed "
                    "claim has not been established.")
    if source_id == "dc_3h" and re.search(r"\bcontain\w*\b|\b(?:oral|external|topical)\w*\b", facts, re.I):
        return ("The supplied product ingredients or route are unverified. The complete ingredient list, "
                "ingredient-by-ingredient authoritative-book references, formulation comparison and exact "
                "administration route must establish every condition of this definition.")
    return card.unanswered


def _text(value: str) -> str:
    """Keep user/planner text visibly quoted, without injecting Markdown links."""
    return (html.escape(value, quote=False).replace("[", "&#91;").replace("]", "&#93;")
            .replace("|", "&#124;").replace("*", "&#42;").replace("`", "&#96;"))


def _evidence(rows) -> dict:
    available = {}
    for _, points in rows:
        for doc, card in points:
            old = available.get(doc["id"])
            # Prefer the full reviewed rule over the scoped authority summary.
            if old is None or card == CARDS.get(doc["id"]):
                available[doc["id"]] = (doc, card)
    return available


def _cite(available: dict, source_id: str, conclusion: str, *, full: bool = True) -> str:
    pair = available.get(source_id)
    if not pair:
        return ""
    doc, card = pair
    if full and card != CARDS.get(source_id):
        return ""
    return f"{conclusion} ({doc['section']}) [{source_id}]"


def _family(question: str) -> str:
    """Route complete concept words, not substrings inside unrelated words.

    Jurisdictions and specific legal tests precede generic formulation terms.
    This prevents a question about an original formulation or outsourced
    manufacture from becoming a biological-resource sourcing question.
    """
    patterns = (
        ("applicant", r"\b(?:citizen\w*|residen\w*|incorporat\w*|control\w*|ownership\b.*\bcompan\w*)\b"),
        ("ownership", r"\b(?:inventorship|ownership|contribut(?:ors?|ed|es|ing)|employment|university|funding|assignments?|who owns)\b"),
        ("disclosure", r"\b(?:disclos\w*|publications?|published|publicly|confidential\w*)\b"),
        ("commercialisation", r"\b(?:commerciali[sz]\w*|licensing receipts|turnover|royalt\w*|patent\w*\b.*\b(?:grant\w*|licen[cs]\w*))\b"),
        ("us", r"\bunited states\b|(?-i:\bUS\b|\bUSA\b)|\bu\.s\.(?:a\.)?|\bfda\b"),
        ("export", r"\b(?:export\w*|europe(?:an)?|eu|german(?:y)?|france|french|destinations?|market.entry)\b"),
        ("sourcing", r"\b(?:sourc(?:e[sd]?|ing)|wild|cultivat\w*|origins?|suppliers?|access dates?|geograph\w*|bmc|biological materials?)\b"),
        ("patent", r"\b(?:prior.art|technical|experimental|invent\w*|efficacy|synerg\w*|would be claimed|patent claims?)\b"),
        ("classification", r"\b(?:formula\w*|ingredients?|classical|first.schedule|authoritative|parenteral|route of administration)\b"),
        ("brand", r"\b(?:brands?|trade.?marks?|logos?|artwork|copyright\w*|packag\w*|design(?:s|ers?|ing)?)\b"),
        ("licensing", r"\b(?:licen[cs]\w*|premis\w*|manufactur\w*|facilit(?:y|ies)|safety|therapeutic|intended use|outsourc\w*)\b"),
    )
    return next((key for key, pattern in patterns if re.search(pattern, question, re.I)), "other")


def _branches(family: str, available: dict, facts_query: str) -> str:
    cite = lambda key, text, **kw: _cite(available, key, text, **kw)
    def applied(key, fallback):
        pair = available.get(key)
        return cite(key, application(*pair, facts_query) if pair else fallback)

    parts = []
    if family == "classification":
        parts = [
            applied("dc_cosmetic", ""),
            applied("dc_3a", ""),
            applied("dc_3h", ""),
        ]
    elif family == "applicant":
        parts = [
            cite("bda_s3", "If the applicant falls within section 3(2), assess prior NBA approval for covered access; an Indian manufacturing address does not settle citizenship, residence or foreign control"),
            cite("bda_s7_exemption", "For a person outside section 3(2), assess section 7 prior SBB intimation and its actual exemptions for covered commercial access"),
            cite("bda_s6", "The same applicant distinction changes the IP milestone: NBA approval before grant for section 3(2) persons, versus pre-grant registration and applicable commercialisation approval for section 7 persons"),
        ]
        if _entity_facts(facts_query):
            parts.insert(0, applied("bda_s3", ""))
    elif family == "ownership":
        supported = " ".join(filter(None, (applied("patents_ownership", ""), applied("patents_assignments", ""))))
        if supported:
            return supported
        return ("Insufficient evidence in retrieved sources to determine inventorship, initial ownership "
                "or the effect of employment, university, funding and assignment terms. Record each "
                "contributor's precise technical/creative contribution separately from the documents "
                "claiming or transferring title. The supplied employee, university or designer relationship "
                "does not establish the company's title in this answer; obtain the relevant ownership "
                "provisions and agreements before deciding. Patentability rules do not answer this question.")
    elif family == "sourcing":
        pair = available.get("bda_s7_exemption")
        if pair and pair[1] == CARDS.get("bda_s7_exemption"):
            parts.append(cite("bda_s7_exemption", application(*pair, facts_query)))
        elif pair:
            parts.append(cite("bda_s7_exemption", pair[1].application, full=False))
        parts += [
            cite("bda_sourcing", "Keep resource identity, plant part, quantity, access date, source location, cultivation/wild status and supplier/knowledge particulars distinct for each material; batch/invoice links are practical supporting evidence"),
            cite("bda_origin_2025", "If relying on cultivated medicinal plants, verify the prescribed BMC records and certificate procedure for the actual plants and quantities"),
        ]
    elif family == "patent":
        parts = [
            cite("patents_invention", "An independently developed product/process still needs a claim-specific novelty, inventive-step and industrial-applicability assessment"),
            applied("patents_3p", "If claimed features merely reproduce traditional knowledge or known properties, the traditional-knowledge exclusion matters; compare the claims against the actual text passages"),
            applied("patents_3e", "If a claimed mixture only aggregates known component properties, section 3(e) can exclude it; comparative technical evidence is relevant, but is not a patent guarantee"),
            applied("patents_3d", ""),
        ]
    elif family == "disclosure":
        parts = [
            applied("patents_disclosure", "If relevant details are already public, assess their content, dates and specific statutory exceptions; if still private, decide filing and confidentiality before publication"),
            cite("patents_specification", "A patent strategy requires sufficient disclosure and the relevant best method; secrecy cannot substitute for information needed to support the claimed invention"),
            cite("dc_label_disclosure", "For the covered proprietary medicine, mandatory ingredient-label disclosures limit what formulation information can remain secret on sale; assess undisclosed process know-how separately"),
        ]
    elif family == "commercialisation":
        parts = [
            cite("bda_s6", "If the IP uses the covered Indian-accessed resource/knowledge, section 3(2) persons require NBA approval before grant; section 7 persons require pre-grant registration and, when obtaining the IP right, prior NBA approval at commercialisation"),
            cite("bda_abs_2025", "Own commercial use and licensing have distinct IP-commercialisation benefit-sharing provisions; an access exemption or nil access rate does not itself decide the later IP liability"),
            cite("bda_abs", "Determine benefit-sharing under the applicable approval framework and actual conditions; these facts do not establish a case-specific amount"),
        ]
    elif family == "licensing":
        parts = [
            applied("dc_cosmetic_licensing", ""),
            cite("dc_licensing", "If the medicine qualifies for the ASU route, identify the State/UT licensing authority for the manufacturing premises and applicable licence conditions"),
            cite("dc_rule_158b", "The confirmed product class and use determine the applicable safety/effectiveness evidence package"),
            cite("dc_schedule_t", "Manufacturing premises and quality/documentation arrangements need the applicable Schedule T assessment"),
        ]
    elif family == "brand":
        parts = [
            cite("tm_act", "Assess the actual name/logo for distinctiveness, refusal grounds and competing marks; a trademark does not protect the underlying formulation or manufacturing method"),
            cite("copyright_scope", "Original documents/artwork can be assessed as expression; copyright does not monopolise their underlying ideas, facts or methods"),
            cite("designs_act", "For packaging appearance, eligibility depends on the actual new/original visual features and any functional or prior-publication concerns"),
        ]
    elif family == "export":
        parts = [
            applied("eu_thmpd", "For the cited EU traditional-use route, verify the product-specific medicinal-use history, including the stated 30-year and 15-year EU requirements; a longstanding tradition alone does not establish product eligibility"),
            cite("pct", "An international patent application does not grant a global patent; identify the national/regional markets and relevant filing dates"),
            cite("madrid", "An international brand strategy depends on the designated markets, applicant/basic-mark requirements and examination there"),
        ]
    # A shared statute/prefix does not make another provision evidence for this
    # question. If the relevant reviewed cards are absent, preserve the gap.
    return " ".join(part for part in parts if part)


_DEFAULT_QUESTIONS = (
    ("classification", ("dc_3a", "dc_3h"), "What are the exact formula, ingredient book references, manufacturing method and administration route?"),
    ("applicant", ("bda_s3", "bda_s6"), "What are the applicant's incorporation/control or citizenship/residence details?"),
    ("sourcing", ("bda_s7_exemption", "bda_sourcing"), "For each plant and batch, what proves its wild/cultivated status, source, geographical origin, quantity, supplier and any BMC certificate?"),
    ("patent", ("patents_invention", "patents_3p", "patents_3e"), "What technical subject matter would be claimed, and what prior-art comparison and experimental evidence supports it?"),
    ("disclosure", ("patents_disclosure", "patents_specification"), "What has already been disclosed publicly or confidentially, on what dates, and what remains secret?"),
    ("commercialisation", ("bda_s6", "bda_abs_2025"), "Will the IP be obtained and commercialised through own use or licensing, and what are the access and commercialisation dates?"),
    ("licensing", ("dc_licensing", "dc_rule_158b"), "Where will manufacturing occur, what is the intended medicinal use, and what licence and supporting evidence exist?"),
    ("brand", ("tm_act", "copyright_scope", "designs_act"), "What are the proposed name, logo, packaging and creative works, and who owns them?"),
    ("export", ("eu_thmpd", "pct", "madrid"), "Which export markets, intended claims, product-specific use history and filing dates are relevant?"),
)


def render_fact_analysis(plan, rows) -> str:
    """Render quoted assertions and conditional decisions for the supplied plan.

    Legal branches are emitted only when their full reviewed card is in rows.
    Unknown questions remain evidence gaps rather than being answered from memory.
    """
    questions = list(getattr(plan, "missing_facts", ()) or ())
    expanded = bool(getattr(plan, "conditional", False) or re.search(
        r"comprehensiv|missing facts?|facts?.{0,30}(?:need|confirm)|what if|what changes? if",
        getattr(plan, "substantive_query", ""), re.I))
    discarded = tuple(dict.fromkeys(getattr(plan, "discarded_facts", ()) or ()))
    discard_requested = bool(discarded and re.search(
        r"discard|withdraw|replac\w*.{0,35}facts|facts.{0,35}replac",
        getattr(plan, "substantive_query", ""), re.I))
    requested = bool(expanded or questions or discard_requested)
    if not requested:
        return ""
    available = _evidence(rows)
    if not available and not discard_requested:
        return ""
    facts_query = getattr(plan, "facts_query", "")
    if not questions:
        questions = [question for _, source_ids, question in _DEFAULT_QUESTIONS
                     if any(source_id in available for source_id in source_ids)][:8]
    lines = []
    if discard_requested:
        lines += ["**Earlier facts withdrawn by your correction**", ""]
        lines += [f"- {_quoted(fact)}" for fact in discarded]
        lines += [""]
    facts = tuple(dict.fromkeys(getattr(plan, "facts", ()) or ()))
    if facts and ((expanded and not getattr(plan, "concise", False)) or discard_requested):
        lines += ["**Facts supplied by you (unverified)**", ""]
        # Exact spans are quoted, not paraphrased into verified legal findings.
        limit = len(facts) if discard_requested else 12
        lines += [f"- “{_text(fact)}”" for fact in facts[:limit]]
        if len(facts) > limit:
            lines += ["", "Further supplied facts remain in the question; none has been independently verified."]
        lines += [""]
    if questions:
        lines += ["**Facts still needed and conditional outcomes**", ""]
        limit = 8 if expanded and not getattr(plan, "concise", False) else 2
        for question in questions[:limit]:
            family = _family(question)
            branch = _branches(family, available, facts_query)
            if not branch:
                branch = ("Not established by the reviewed sources available for this answer; "
                          "confirm the facts and obtain the relevant primary-source evidence before deciding.")
            if family == "ownership" and re.search(r"employee|university|designer|contribut", _assertions(facts_query), re.I):
                question = ("What exact features did the stated contributors create, and what do their "
                            "employment, collaboration, funding and assignment documents say?")
            if family == "applicant" and _entity_facts(facts_query):
                question = ("What evidence verifies the stated ownership/control and establishes the actual "
                            "applicant's statutory category?")
            lines.append(f"- **{_text(question)}** Inference/application: {branch}")
    return "\n".join(lines)
