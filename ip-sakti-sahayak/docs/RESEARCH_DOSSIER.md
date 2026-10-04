# IP-SAKTI Sahayak — Master Research & Knowledge Dossier

**Smart India Hackathon 2026 · Problem Statement 26045 · Ministry of AYUSH / All India Institute of Ayurveda**
Theme: MedTech / BioTech / HealthTech · Category: Software · Team: Vector Bytes (ID 22345)

*Compiled: 22 September 2026. This dossier consolidates every fact used to build IP-SAKTI Sahayak — the legal substance, the corrections that survived independent verification, the competitive/reliability evidence, and the primary-source text extracted from the gazette PDFs. It is the provenance record behind the version-tracked RAG corpus.*

> **Information, not legal advice.** Every statutory statement below carries a citation and an "as-of" date. Verify against the primary source before relying on it. Laws change (e.g. Rule 170, the 2024 rules); treat dated items as of the date shown.

> **Implementation review, 23–24 September 2026:** the original biodiversity and classifier summaries were too broad. Sections 3.8 and 7 now reflect conditional routing and a primary-text check of the 2023 amendment on 23 September. The app distinguishes dated dossier records, checked primary text and notes needing review. See [the implementation review](IMPROVEMENT_REVIEW.md). The other verification claims below describe the original research process; they were not all repeated during this review.

---

## 0. How this was verified (methodology & confidence key)

The team's original research (a "playbook" PDF + the pitch PPTX) was **not trusted**. It was checked over **three independent deep-research passes** (≈300 sub-agent searches/fetches total, adversarial 3-vote verification per claim) against primary/official sources, and the load-bearing regulatory facts were then confirmed **verbatim against the gazette PDFs** the team supplied. Sources were graded primary (official gov/treaty/registry) > secondary (reputable reporting) > tertiary.

**Confidence key used throughout:**
- **[CONFIRMED]** — matches a primary source (often verbatim).
- **[PARTLY-TRUE]** — core is right but the framing/number needs correction.
- **[REFUTED]** — the claim as stated is wrong; corrected fact given.
- **[UNVERIFIED]** — could not be corroborated from an authoritative source; do not present as fact.

**Source tiers for the corpus:** India Code, IP India, CDSCO, FSSAI, NBA, WIPO, WTO, EUR-Lex/EMA, CSIR/TKDL, USPTO/Google Patents, arXiv/Stanford HAI, plus the supplied gazette PDFs.

---

## 1. The problem statement, decoded

The Ministry of AYUSH (through AIIA) wants a trustworthy first-stop advisor that removes the confusion at the intersection of **IP law + biodiversity/ABS law + drug-regulatory classification**, for both India and export markets. It is **not** a general legal chatbot and **not** a reproduction of TKDL.

The deliverables (as decomposed):
1. **Classify the formulation first** — minimum clarifying questions → one of six regulatory categories, each with a different IP and ABS posture.
2. **IP answers with jurisdictional clarity** — 7 IP regimes + ABS duties, National vs International kept strictly separate via an explicit jurisdiction switch.
3. **Mandatory source citation** — specific statute/section/treaty article with a link, never vague summaries.
4. **Access facilitation** — route to the right registry/form; free databases directly, paid subscriptions only with explicit, logged consent.
5. **Multilingual, plain-language** delivery for the AYUSH community.
6. **Guardrails** — standing "information, not legal advice" disclaimer, confidence indicator, safe abstention, escalation, DPDP-aligned privacy/audit.

## 2. Headline verification result — what the team got RIGHT and what to CORRECT

**Framework held up; a handful of time-sensitive numbers/framings needed fixing.** Put these corrections on every judge-facing slide and in the corpus:

| # | Item | Team said | Verified fact | Verdict |
|---|------|-----------|---------------|---------|
| 1 | TKDL scale | ~5.2 lakh formulations | **4.54 lakh** (official page) | REFUTED → fix |
| 2 | TKDL impact | 375+ applications set aside | **324+** (official page) | REFUTED → fix |
| 3 | TKDL access | 18 offices under NDA | **16** on the official page; 2026 IP Australia/Brazil additions **could not be corroborated** | PARTLY-TRUE |
| 4 | Turmeric | patent "revoked 1997" | all claims cancelled on re-exam; **certificate 1998** (1997 = examiner decision) | PARTLY-TRUE |
| 5 | Neem | "1995 fungicidal grant to USDA/W.R. Grace" | revocation **final 8 Mar 2005** is right; the 1995-grant framing is wrong | REFUTED (framing) |
| 6 | Basmati | RiceTec "claims 15–17 struck" | **15 of 20 claims cancelled** (1–7, 10, 14–20); cert 29 Jan 2002 | PARTLY-TRUE → strengthen |
| 7 | EU THMPD | "not appropriate for holistic systems like Ayurveda" | COM(2008)584 declines to regulate whole **traditions as such**; individual products can qualify; real barrier = **15-years-in-EU** rule | PARTLY-TRUE → reframe |
| 8 | Rule 170 | "legally unsettled/evolving" | **omission STANDS** — SC vacated its stay on **11 Aug 2025** | UPDATE |
| 9 | Lexlegis | "tax-focused", ~$5M seed | general multi-jurisdiction legal AI; **funding uncorroborated — drop** | REFUTED/DROP |
| 10 | Lucio | ~$7.7M / $5M funding | exists (founders Vasu Aggarwal & Darsan G); **funding uncorroborated — drop** | UNVERIFIED/DROP |
| 11 | Jhana.ai | ~$1.6M seed | **CONFIRMED** ($1.6M seed, Together Fund/Mathrubootham, Sep 2024) | CONFIRMED — keep |
| 12 | SIH 2026 dates | launch 21 Aug, finale Dec, 36h | **not published/retrievable** on sih.gov.in — do not cite as verified | UNVERIFIED |

**Original research verification claims, subject to the corrections below:** Patents Act s.3(e)/(i)/(j)/(p); Patents (Amendment) Rules 2024; D&C Act ASU definitions, Schedule T, Rule 158B; phytopharma GSR 918(E); FSSAI Ayurveda Aahara 2022; Stanford RegLab hallucination study; IndicTrans2 (22 languages, MIT). The biodiversity applicant/exemption wording is corrected in section 3.8. Live treaty and regulatory status require current checks.

## 3. National (India) legal layer

### 3.1 The Patents Act, 1970 — the exclusions an Ayurvedic invention must clear
Source: IP India bare Act (ipindia.gov.in). Text stable since the 2002/2005 amendments. **[CONFIRMED verbatim]**

- **s.3(p) — traditional knowledge:** "an invention which, in effect, is traditional knowledge or which is an aggregation or duplication of known properties of traditionally known component or components" is **not** an invention. *This is the principal bar a classical Ayurvedic formulation hits.*
- **s.3(e) — mere admixture:** "a substance obtained by a mere admixture resulting only in the aggregation of the properties of the components thereof, or a process for producing such substance" is not patentable. *A herb combination must show synergy beyond the sum of parts.*
- **s.3(i) — methods of treatment:** any process for the "medicinal, surgical, curative, prophylactic, diagnostic, therapeutic or other treatment of human beings" (or similar treatment of animals) is excluded. *A Panchakarma/therapeutic procedure per se is not patentable.*
- **s.3(j) — plants/animals:** "plants and animals in whole or any part thereof other than micro-organisms but including seeds, varieties and species and essentially biological processes for production or propagation of plants and animals" is excluded. *Micro-organisms are patentable; plant varieties go to PPV&FR instead.*
- **s.3(d) — new form of a known substance:** the mere discovery of a new form (salt/polymorph/derivative) of a known substance without **enhancement of known efficacy** is excluded. *Relevant to a new drug derived from a known Ayurvedic active.*

### 3.2 The Patents (Amendment) Rules, 2024 — **G.S.R. 211(E), in force 15 March 2024**
Source: gazette copy (supplied PDF). **[CONFIRMED verbatim against the notification]**

- **Request for Examination (RFE):** rule 24B(1) amended — "for the words 'forty-eight months', wherever they occur, the words 'thirty-one months' shall be substituted." **RFE window cut 48 → 31 months** from priority/filing. (Applications filed before commencement keep the old 48-month period.)
- **Form 27 (statement of working):** now "furnished once in respect of every period of **three financial years**" (from the FY after grant), within six months of each period's expiry. The revised Form 27 **no longer requires revenue/value figures** but must state **whether the patent is available for licensing**. (Previously annual.)
- **Form 3 (foreign-filing statement, s.8):** the Controller may direct a fresh Form 3 within two months; and (new) "the Controller may **condone the delay or extend the time for filing Form 3 for a period up to three months** upon a request made in Form 4." Reduces repeated Form 3 filings.
- **Divisional applications:** rule 13 gains sub-rule (2A) expressly permitting an applicant to file a divisional application (including on a provisional/complete specification), codifying post-*Boehringer* practice.
- **Also:** relaxed timelines/condonation across several forms; reduced/streamlined fees for certain filings.

> **Corpus note:** the "second amendment" (G.S.R. 215(E), 16 Mar 2024) is a **separate** notification about the adjudicating officer / penalties (Form 31) — do **not** conflate it with the RFE/Form-27 changes above.

### 3.3 The Drugs and Cosmetics Act, 1940 — ASU definitions
Source: D&C Act bare text (supplied PDF / cdsco.gov.in). **[CONFIRMED verbatim]**

- **s.3(a) — Ayurvedic/Siddha/Unani (ASU) drug:** "'Ayurvedic, Siddha or Unani drug' includes all medicines intended for internal or external use for or in the diagnosis, treatment, mitigation or prevention of disease or disorder in human beings or animals, and **manufactured exclusively in accordance with the formulae described in the authoritative books** of Ayurvedic, Siddha and Unani Tibb system of medicine, specified in the **First Schedule**." *This "exclusively per First-Schedule formula" test defines a CLASSICAL medicine.*
- **s.3(h) — patent or proprietary medicine (ASU):** "(i) in relation to Ayurvedic, Siddha or Unani Tibb systems of medicine **all formulations containing only such ingredients mentioned in the formulae described in the authoritative books** … specified in the First Schedule, but does not include a medicine which is administered by parenteral route and also a formulation included in the authoritative books as specified in clause (a)." *PROPRIETARY = First-Schedule ingredients, but not itself a classical formula.*

### 3.4 The Drugs and Cosmetics Rules, 1945 — licensing & GMP
Source: consolidated Rules (supplied PDF, "as amended vide G.S.R. 360(E) dated 01-07-2024"). **[CONFIRMED]**

- **Rule 158B — "Guidelines for issue of license with respect to Ayurveda, Siddha or Unani drugs":** distinguishes (A) classical medicines under s.3(a) from patent/proprietary medicines under s.3(h), and prescribes the proof-of-safety/effectiveness requirements per class. Applications go through the **e-AUSHADHI** portal.
- **Schedule T — Good Manufacturing Practices (GMP)** for ASU manufacturing units (premises, hygiene, machinery, QC, documentation). A manufacturing licence requires Schedule T compliance.

### 3.5 Phytopharmaceutical drugs — **G.S.R. 918(E), 30 November 2015**
Source: gazette (supplied PDF) — Drugs and Cosmetics (Eighth Amendment) Rules, 2015. **[CONFIRMED verbatim]**

- Inserted definition (rule 2(eb)): "'Phytopharmaceutical drug' includes purified and standardised fraction with **defined minimum four bio-active or phyto-chemical compounds** (qualitatively and quantitatively assessed) of an extract of a medicinal plant or its part, for internal or external use of human beings or animals for diagnosis, treatment, mitigation or prevention of any disease or disorder but does not include administration by parenteral route."
- Regulated as a **new drug** by **CDSCO** (not the Ministry of AYUSH), via Rule 122E read with **Appendix IB of Schedule Y** — requires identity, safety and confirmatory clinical data. *This is the "bridge" category with real patent potential + an evidence burden. Corroborated by the 29-08-2025 CDSCO phytopharmaceutical guidance and the CCRAS drug-development guideline.*

### 3.6 FSSAI — Food Safety and Standards (Ayurveda Aahara) Regulations, 2022
Source: FSSAI gazette, notified 05 May 2022 (supplied PDF). **[CONFIRMED verbatim]**

- Definition: "'Ayurveda Aahara' means a food prepared in accordance with the recipes or ingredients or processes as per method described in the authoritative books of Ayurveda listed under **'Schedule A'** of these regulations … but **does not include Ayurvedic drugs or proprietary Ayurvedic medicines**, cosmetics, narcotic or psychotropic substances." Licensed as **food** by FSSAI (FoSCoS), not as a drug; advertising must avoid disease claims. (A 25-07-2025 FSSAI order operationalises the scheme further.)

### 3.7 Advertising — DMR Act 1954 + the Rule 170 saga
Sources: India Code (DMR Act); reputable court reporting (LiveLaw) of recorded SC orders. **[CONFIRMED end-to-end]**

- **Drugs and Magic Remedies (Objectionable Advertisements) Act, 1954** (ss.3, 4 + Schedule): prohibits advertisements claiming to diagnose/cure/prevent the scheduled diseases and misleading drug ads (including ASU). Principal control on disease-claim advertising; central to the Patanjali/IMA litigation.
- **Rule 170 (D&C Rules 1945)** required prior approval of ASU advertisements by the State Licensing Authority. **Timeline:**
  - **Aug 2023** — AYUSH Ministry directs licensing authorities **not to enforce** Rule 170.
  - **1 Jul 2024** — Rule 170 **omitted** by the Drugs (Fourth Amendment) Rules 2024, **G.S.R. 360(E)**.
  - **27 Aug 2024** — Supreme Court (Kohli & Mehta JJ.) **stays** the omission ("Rule 170 shall remain in the statute book").
  - **24 Feb 2025** — SC actively reviews state/UT compliance, treating Rule 170 as operative.
  - **11 Aug 2025** — SC (Nagarathna & Vishwanathan JJ.) **vacates the stay** and disposes of the IMA petition.
  - **Dated dossier position after the 11 August 2025 order:** the omission was reported to stand; ASU advertising remained subject to the DMR Act 1954. This implementation review did not check subsequent orders, so the app abstains on requests to confirm the rule's present status.

### 3.8 Biological Diversity (Amendment) Act, 2023 — corrected applicant and exemption tests

**[PRIMARY TEXT CHECKED: 23 September 2026]** Source: [NBA-hosted Biological Diversity (Amendment) Act, 2023, Act 10 of 2023](https://www.nbaindia.nic.in/sites/default/files/2026-05/BDAct_2023.pdf), Gazette dated 3 August 2023, amendment sections 8–9 on pages 3–4. The [local PDF](../corpus/primary/biological-diversity-amendment-2023.pdf) and [hash manifest](../corpus/primary/manifest.json) preserve the evidence. This check covers the cited amendment text, not every later rule or notification.

- **s.6(1):** persons or entities covered by **s.3(2)** applying for IP based on research/information on biological resources accessed from India, including those deposited in repositories outside India, or associated TK, require **NBA approval before grant**.
- **s.6(1A):** persons covered by **s.7** applying for such IP require **NBA registration before grant**.
- **s.6(1B):** such persons under s.7 who obtain the IP right require **prior NBA approval at commercialisation**.
- **s.7(1):** persons outside s.3(2) must give prior SBB intimation before access for commercial utilisation, subject to the Act. Its proviso identifies codified TK, cultivated medicinal plants/products, local people and communities including growers/cultivators, and vaids, hakims and registered AYUSH practitioners practising indigenous medicine **as a profession for sustenance and livelihood**.
- **s.7(2)–(3):** the cultivated-medicinal-plant exemption is available **only if a certificate of origin is obtained from the Biodiversity Management Committee** in the prescribed manner, based on maintained records.

**Correction to the original dossier:** do not state that every applicant needs the same NBA approval before filing, or that an AYUSH/classical/cultivated label removes all benefit-sharing and IP-related duties. Establish applicant category, activity, resource origin and evidence for any exemption. Current forms, subordinate rules and individual applicability need their own review.

### 3.9 The other IP regimes (India) — for routing across all seven
- **Geographical Indications (GI) Act, 1999** — region-linked collective right; for region-specific Ayurvedic products/medicinal-plant produce (e.g. a distinctive regional herb). **[CONFIRMED]**
- **Trade Marks Act, 1999** — brand/logo/get-up; the primary, indefinitely renewable brand IP; generic/classical names are hard to register. **[CONFIRMED]**
- **Designs Act, 2000** — shape/pattern/ornament of a product or pack (10 yrs + 5); must be new & original. **[CONFIRMED]**
- **Copyright Act, 1957** — labels, artwork, literature, manuals, compilations; automatic on creation; protects expression, not the formula. **[CONFIRMED]**
- **PPV&FR Act, 2001** — because s.3(j) excludes plant varieties from patents, a new/extant/farmers' medicinal-plant variety is protected here (sui generis + farmers' rights); this is India's TRIPS 27.3(b) sui generis system. **[CONFIRMED]**

### 3.10 TKDL — the crucial, honesty-defining finding
Source: official TKDL "About"/"Home" pages (tkdl.res.in). **[CONFIRMED verbatim; time-sensitive]**

- **What it is:** a defensive database documenting codified Indian TK (Ayurveda, Unani, Siddha, Sowa-Rigpa, Yoga) as searchable prior art to pre-empt wrongful patents abroad.
- **Verified official numbers:** "more than **4.54 lakh** formulations/practices have been transcribed"; access "available to **sixteen** Patent Offices"; "more than **324** patent applications … set aside/withdrawn/amended" on TKDL prior-art. *(Not the team's 5.2 lakh / 18 / 375.)*
- **Access:** "**Access to the full database is available to Patent Offices only under TKDL Access Agreement**" — a Non-Disclosure Agreement, for search/examination only. **No public sign-up, no fee schedule, no public/developer API.**
- **The 2026 additions (IP Australia ~9 Jul, Brazil INPI) claimed by the team → [UNVERIFIED]** (no authoritative corroboration found). Say "16 on the official page, with reported 2026 additions."
- **Design implication:** this app does not ingest restricted TKDL content. It references the public TKDL site and offers a consent-logged referral action, which does not submit an access request or grant database access. A separate classical-text corpus remains future work; edition and translation licensing must be checked before ingestion.

---

## 4. International legal layer (kept strictly separate from the India layer)

### 4.1 TRIPS Article 27.3(b)
WTO members may exclude plants/animals (other than micro-organisms) and essentially biological processes from patentability, **but must protect plant varieties** by patents or an effective **sui generis** system (or both). India implements this via Patents Act s.3(j) + the PPV&FR Act. Source: wto.org. **[CONFIRMED]**

### 4.2 CBD + Nagoya Protocol (ABS)
The Convention on Biological Diversity affirms states' sovereignty over biological resources (access on mutually agreed terms with prior informed consent); the **Nagoya Protocol** (2010, in force 2014) operationalises access-and-benefit-sharing for genetic resources and associated TK. India implements these via the Biological Diversity Act and the NBA/SBB structure. Source: cbd.int. **[CONFIRMED]**

### 4.3 WIPO GRATK Treaty, 2024 — adoption and live-status verification
Source: wipo.int (treaty page, press release PR/2024/920). **[CONFIRMED]**
- **Adopted by consensus in Geneva on 24 May 2024** (diplomatic conference 13–24 May 2024). First WIPO treaty addressing genetic resources & associated TK.
- Establishes a **mandatory patent DISCLOSURE requirement**: where an invention is based on genetic resources, disclose the country of origin/source; where based on associated TK, disclose the indigenous people/local community that provided it.
- **Article 17: enters into force 3 months after 15 eligible parties ratify/accede.** The original dossier recorded the treaty as not in force with about four parties. That live status/count was not reverified during implementation and is not asserted by the app. Check WIPO's current treaty-status record before stating that the treaty is operative.

### 4.4 PCT · Madrid · Hague · Budapest (WIPO-administered routes)
- **PCT** — one international application → patent options in many countries; national-phase decisions deferred (~30/31 months). No global patent. **[CONFIRMED]**
- **Madrid Protocol** — international trade-mark registration for a brand across members. **[CONFIRMED]**
- **Hague Agreement** — international registration of industrial designs. **[CONFIRMED]**
- **Budapest Treaty** — a single micro-organism deposit at an International Depositary Authority satisfies patent disclosure across members (micro-organisms are patentable, unlike plants). **[CONFIRMED]**

### 4.5 EU THMPD — Directive 2004/24/EC + COM(2008)584 (reframed)
Sources: EMA herbal-products page; EUR-Lex COM(2008)584. **[CONFIRMED with corrected framing]**
- Directive 2004/24/EC created a **simplified traditional-use registration** for herbal medicinal products (amending Dir 2001/83/EC): evidence of **≥30 years medicinal use, including ≥15 years within the EU**, with **no new safety/efficacy clinical trials**.
- **The correct framing:** COM(2008)584 declined to extend the scheme to regulate whole traditional-medicine **systems as such** (Ayurveda/TCM), calling that "not appropriate for a global regulation of such medical practices" — but noted **individual products can still qualify**. The real product-level barrier for Ayurvedic products is the **15-years-in-EU** use requirement, which the report acknowledges "can prevent access to the European market for … third countries." *Do not say "THMPD is unsuitable for Ayurveda" flatly.*

## 5. Landmark biopiracy cases (the narrative that justified TKDL)
Sources: USPTO/Google Patents; EPO register; reputable reporting. **[CONFIRMED, with precise dates]**

- **Turmeric — US Patent 5,401,504** ("Use of turmeric in wound healing", Univ. of Mississippi Medical Center, granted 1995). CSIR challenged it as long-known Indian TK; **all claims cancelled on re-examination, certificate issued 1998** (the oft-cited "1997" is the examiner's substantive decision). The case that motivated TKDL.
- **Neem — EPO patent** (USDA / W. R. Grace, neem-derived product). Opposed on TK grounds; Opposition Division revoked it (2000) and the **revocation became final on 8 March 2005** when the appeal was dismissed. *(Drop the team's "1995 fungicidal grant" phrasing — it was refuted.)*
- **Basmati — US Patent 5,663,484** ("Basmati rice lines and grains", RiceTec Inc., granted **2 Sep 1997**). After India (APEDA/CSIR) challenged it, the re-examination certificate (**29 Jan 2002**) **cancelled claims 1–7, 10 and 14–20 — 15 of the 20 claims** (confirming only 8, 9, 11; amending 12, 13). RiceTec could not keep a generic monopoly on "basmati". *(Stronger than the team's "claims 15–17".)*

## 6. Competitive landscape, reliability evidence & government AI stack

### 6.1 Indian legal-AI — real, but none is Ayurveda-specific (your moat)
Sources: vendor sites; Entrackr/Tracxn. **[CONFIRMED existence/positioning; funding as noted]**
- **Jhana.ai** — "India's first AI paralegal", 16M+ Indian judgments/statutes. **Seed $1.6M CONFIRMED** (Entrackr, 24 Sep 2024; led by Girish Mathrubootham/Freshworks & Manav Garg via Together Fund; Kunal Shah, Razorpay founders, OpenAI's Shyamal Anadkat participating). *Safe to cite.*
- **Lucio** — Bengaluru legaltech; **founders Vasu Aggarwal & Darsan G**; Trilegal collaboration confirmed. **Funding (~$7.7M/$5M) UNVERIFIED → drop.**
- **Lexlegis.AI** — **general, multi-jurisdiction** legal AI ("MIRA", 215 skills, 17 countries), **not tax-focused**. **Funding (~$5M) UNVERIFIED → drop.**
- **CaseMine (Gauge Data Solutions)** + **AMICUS** (2023) — RAG over Indian judgments; "India's first legal AI assistant" is **self-marketing** (present as a quote, not fact).
- **None offers Ayurveda-specific IP + regulatory classification** → that gap is IP-SAKTI's differentiation.

### 6.2 Reliability evidence — why not a general LLM / ChatGPT
Source: Magesh, Surani, Dahl, Suzgun, Manning & Ho, *"Hallucination-Free? Assessing the Reliability of Leading AI Legal Research Tools"* (Stanford RegLab/HAI; **arXiv:2405.20362**; Journal of Empirical Legal Studies, 2025). **[CONFIRMED]**
- Abstract: the leading proprietary tools "each hallucinate between **17% and 33%** of the time."
- Stanford HAI write-up (corrected figures): **Lexis+ AI / Ask Practical Law AI >17%**, **Westlaw AI-Assisted Research >34%**. *Use ">34%" for Westlaw, not "33%".*
- **Design consequence:** citation verification + safe abstention are not optional — even RAG legal tools hallucinate materially.

### 6.3 Government / open AI stack (near-zero-cost multilingual)
- **AI4Bharat IndicTrans2** — supports **all 22 scheduled Indian languages**; model checkpoints under **MIT** (GitHub + HuggingFace). **[CONFIRMED]**
- **Bhashini / ULCA** — Government of India language APIs. *(Confirmed as the national language infrastructure; wire into the i18n layer for a sovereign deployment.)*
- **Open-weight LLMs + open vector DBs** (Qwen/Llama-class; Chroma/pgvector/Qdrant; BGE-M3/multilingual-e5; BGE-reranker) — the sustainable, hostable stack behind the "Ministry can run it" story.

## 7. Six-category classifier — preliminary routing with confirmed facts

The six categories structure research; the original four-step tree was not an exhaustive legal classifier. A book name, a new claim, or the word “standardised” cannot establish eligibility. The implemented flow:

1. Establishes intended use, considering therapeutic claims even for creams, foods and supplements.
2. Asks the administration route for medicine. Parenteral products require specialist review instead of being assigned to proprietary ASU or phytopharmaceutical routes.
3. Confirms the **complete formula and manufacturing method** against a First-Schedule text for the classical route.
4. Otherwise confirms the full phytopharmaceutical test: purified/standardised fraction, at least four defined compounds, qualitative and quantitative assessment.
5. Otherwise checks that **all ingredients** meet the s.3(h)(i) First-Schedule condition for proprietary ASU medicine. A new indication alone is not treated as automatic CDSCO classification.
6. Refers products outside these definitions for regulatory assessment; a potential new-drug outcome is explicitly provisional.
7. Requires food to meet both the claim restrictions and **Schedule A Ayurveda Aahara definition**. Ordinary nutraceuticals are not automatically Ayurveda Aahara.
8. Requires external cleansing/beautifying use without therapeutic claims for preliminary cosmetic routing. Detailed licensing requirements still need competent-authority review.

Every question offers an uncertainty/review path. Descriptions can identify intended use; the model does not supply legal eligibility facts. Users can inspect and edit the answer trail.

| Route | Basis to confirm | IP guidance | Biodiversity guidance | Regulatory direction |
|---|---|---|---|---|
| **Classical ASU** | Complete First-Schedule formula/method; s.3(a) | Traditional formula faces s.3(p); brand and other IP are separate | Test s.7 exemptions and their conditions | ASU licensing, Rule 158B and Schedule T; evidence depends on product/claims |
| **Proprietary ASU** | Only listed ingredients, not itself a classical formula; non-parenteral | The category name does not mean a patent exists | Apply the relevant s.6 applicant pathway; assess s.7 separately | ASU authority; applicable safety/effectiveness requirements |
| **Potential new drug** | Outside preceding routes; current definition needs review | Novelty, inventiveness and exclusions remain separate tests | Confirm approval/registration and commercialisation duties | CDSCO/professional assessment; not a final classification |
| **Phytopharmaceutical** | Full G.S.R. 918(E) definition and non-parenteral use | Characterisation alone does not prove patentability | Applicant and sourcing facts matter | CDSCO; confirm current development/approval evidence |
| **Ayurveda Aahara** | Schedule A definition and exclusions; no disease claim | Food classification alone neither grants nor excludes a patent | Check applicable duties and exemption evidence | FSSAI/FoSCoS |
| **Cosmetic** | External cosmetic purpose; therapeutic claims need reassessment | Brand, design, copyright and confidential know-how may matter | Assess resource-related duties on their facts | Competent cosmetic licensing authority |

These are **preliminary India regulatory routes**. The International switch filters legal research, not the jurisdiction of the classifier.

## 8. SIH 2026 facts — verifiable vs not
Source: sih.gov.in (checked Sep 2026). **[Mixed]**
- **Verifiable now:** the SIH 2026 problem-statements page is live and lists **240 problem statements (58 hardware + 182 software)** with an **idea-submission deadline of 30 September 2026**. *(That deadline is the one citable SIH date.)*
- **NOT verifiable / [UNVERIFIED]:** the launch date (team: ~21 Aug 2026), the Grand Finale timing (team: ~Dec 2026) and the "36-hour software edition" detail are **not published/readable** on the site; the PS list truncates at ~26025, so **PS 26045 "IP-SAKTI Sahayak" could not be located online** (the team holds the official PS text — legitimate, just not web-citable). **Do not present these dates as verified on judge-facing slides.**

## 9. Source register (datasets — access, licensing, effort)

| # | Dataset | Source | Access | Licensing | Effort |
|---|---------|--------|--------|-----------|--------|
| 1 | India Code (central statutes) | indiacode.nic.in | download/scrape; no API | Govt public domain | Low–Med |
| 2 | Patents Act 1970 + Rules (incl. 2024) | ipindia.gov.in | download PDFs | Govt open | Low |
| 3 | IP India InPASS (patents) | iprsearch.ipindia.gov.in | web UI, CAPTCHA, no API | public, ToS limits | Med (route, don't bulk-scrape) |
| 4 | GI Registry | ipindia.gov.in/gi | journal PDFs + register | public | Low–Med |
| 5 | Trade Marks / Designs registers | ipindia.gov.in | web UI | public, ToS | Med |
| 6 | Biological Diversity Act 2023 + Rules 2024 | nbaindia.org / egazette | download | Govt open | Low |
| 7 | D&C Act 1940 & Rules 1945 (First Sch, Sch T, 158B, 122E) | cdsco.gov.in / indiacode | download | Govt open | Low |
| 8 | Phytopharmaceutical — GSR 918(E) 2015 | cdsco / egazette | download | Govt open | Low |
| 9 | DMR Act 1954 + Rule 170 notifications | indiacode.nic.in / egazette | download | Govt open | Low |
| 10 | FSSAI Ayurveda Aahara Regulations 2022 | fssai.gov.in | download | Govt open | Low |
| 11 | WIPO Lex (TRIPS, CBD, Nagoya, PCT, Madrid, Hague, Budapest, GRATK) | wipo.int/wipolex | browse/download; some APIs | free, no registration | Low |
| 12 | EU THMPD 2004/24/EC + EMA HMPC | eur-lex.europa.eu / ema.europa.eu | download | EU open | Low |
| 13 | AI4Bharat IndicTrans2 + Bhashini/ULCA | github.com/AI4Bharat / bhashini.gov.in | API + open weights | MIT / open | Med |
| 14 | Open-domain classical-text references | AMAR (ccras.res.in/amar), public texts | manual curation | open domain | Med–High |
| 15 | **TKDL** | tkdl.res.in | **GATED — patent offices only, NDA, no public API** | proprietary govt DB | N/A (route/refer only) |

> **Note:** government portals (ipindia, indiacode, cdsco, fssai, egazette, EUR-Lex) frequently **block automated fetches** (403/Cloudflare) — the corpus was built from the downloaded PDFs, which is more authoritative than scraping anyway.

### Primary-source PDFs used (supplied, text-verified)
- `1_83_1_Patent_Amendment_Rule_2024_Gazette_Copy.pdf` — **G.S.R. 211(E), 15 Mar 2024** (RFE 48→31, Form 27, Form 3, divisional).
- `Patent_second_amendment_rules_2024.pdf` — G.S.R. 215(E), 16 Mar 2024 (adjudicating officer/penalties — separate).
- `bf44d1acbe4866716a5d8abde49086e2.pdf` — D&C Act 1940 (s.3(a), s.3(h) verbatim).
- `Drugs Rules 1945_2024 09.pdf` — consolidated D&C Rules (Rule 158B, Schedule T; as amended to G.S.R. 360(E), 01-07-2024).
- `GSR_918-E-dated-30-11-2015.pdf` — phytopharmaceutical definition (≥4 bio-actives).
- `29.08.2025_Phytopharmaceutical-Drugs-General-Guidance-for-Development.pdf` + `CCRAS_Guideline-of-Drug-Development.pdf` — phytopharma / drug-development guidance.
- `62789a20b54bdGazette_Notification_Ayurveda_Aahara_09_05_2022.pdf` + `Order dated 25-07-2025 …Ayurveda Aahara.pdf` — FSSAI Ayurveda Aahara.
- `2016DrugsandCosmeticsAct1940Rules1945.pdf` — consolidated D&C Act+Rules (reference).

## 10. Caveats & open items
- **Time-sensitive:** Rule 170 status, TKDL office count, GRATK ratification count and SIH 2026 dates can change — re-verify and re-stamp "as-of" before submission.
- **[UNVERIFIED] items to keep off judge-facing slides as fact:** TKDL 2026 IP Australia/Brazil additions; Lucio & Lexlegis funding; SIH launch/finale dates & "36-hour"; CaseMine "India's first" superlative.
- **Drop/relabel:** neem "1995 fungicidal grant" framing; "Lexlegis = tax-focused".
- The **basmati** and **turmeric** dates are stable historical facts; the rest of the statutory text is stable barring amendment.
- This dossier is **strategic/technical guidance, not legal advice**; the app itself carries a standing disclaimer, cites primary sources, and abstains when uncertain.

---

*The application uses 36 selected research records; it does not cover every claim in the dossier. The sources API exposes the loaded corpus fingerprint, source types, dates and review states. Two biodiversity records carry a primary-text check date; the new-drug pathway and neem citation remain withheld pending review. Other records retain the original dossier provenance.*
