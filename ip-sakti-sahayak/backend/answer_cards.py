"""Reviewed, source-bound propositions and conditional practical applications.

These are the offline answer vocabulary, not free-form model claims. An entry is
usable only with its cited source in the supplied evidence. Generation labels the
legal proposition separately from the application and from unresolved facts.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Card:
    established: str
    application: str
    unanswered: str
    action: str


CARDS = {
    "patents_ownership": Card(
        "Subject to s.134, s.6 permits an application by the person claiming to be the true and first inventor, the assignee of that person's right to apply, or the specified legal representative, alone or jointly. Sections 7(2)-(3) require assignment-based proof of the right to apply and naming the inventor; s.10(6) addresses the inventorship declaration. Under s.28(1), mention as inventor does not itself confer or remove patent rights.",
        "Keep the people who contributed the claimed invention separate from the applicant or owner. A company may apply through a valid assignment of the right to apply while the inventor remains identified; payment, a job title or an organisation's name does not supply the missing proof of entitlement.",
        "The actual inventive contributions, employment or research terms, university obligations and chain of title need the relevant records and agreements. These passages do not decide the particular dispute.",
        "Map each claimed technical contribution to its contributor and inspect employment, university, contractor and assignment documents before naming inventors and applicants."),
    "patents_assignments": Card(
        "Section 68 requires an assignment of a patent or share, mortgage, licence or other patent interest to be in a written, duly executed document embodying the parties' rights and obligations. Section 69(1) requires the person acquiring the specified patent title or interest to apply to register that title or notice of interest; s.69(3) addresses proof of title and disputes.",
        "Distinguish assignment of the right to apply under ss.6-7 from a transaction in an existing patent under ss.68-69. A confidentiality agreement or payment record alone should not be treated as establishing an assignment without checking its terms and execution.",
        "Whether a signed agreement covers this invention or patent, who could assign it, any retained rights and the registration position remain unverified. Patent rules do not decide copyright ownership of artwork or manuals.",
        "Review the signed chain-of-title documents, invention and patent scope, retained rights and required registration before asserting company ownership or granting a licence."),
    "dc_cosmetic": Card(
        "Section 3(aaa) defines a cosmetic by intended application to the human body for cleansing, beautifying, promoting attractiveness or altering appearance, including cosmetic components. Sections 3(a) and 3(b)(i) address the specified medicinal uses, including diagnosis, treatment, mitigation or prevention of disease or disorder.",
        "A hair or skin product intended only for the stated cosmetic purposes may fit the cosmetic definition even when it uses Ayurvedic ingredients. Therapeutic intended use requires a drug-category assessment; the word Ayurvedic alone does not settle the category.",
        "Final classification needs the complete formulation, intended function, presentation, label and advertising claims. The cited definitions alone do not certify the product, a licensing exemption or permission to sell.",
        "Review the proposed formulation and every intended-use claim with the competent licensing authority, then use the applicable cosmetic or drug route."),
    "dc_cosmetic_licensing": Card(
        "In the 2020 Gazette, r.4(2) identifies the State Licensing Authority for cosmetics manufacture for sale or distribution; r.23 prescribes COS-5/COS-6 licence or loan-licence applications and the COS-7 GMP declaration. Rule 25 specifies COS-8/COS-9 licences. For a new cosmetic as defined in r.3(r), r.23(3) requires prior Central Licensing Authority permission in COS-3.",
        "If the Ayurveda-related product is classified as a cosmetic, assess this cosmetic manufacturing route and whether it uses the manufacturer's own premises or a loan-licence arrangement. Confirm whether any ingredient brings it within the specific new-cosmetic definition.",
        "The final category, actual premises, manufacturing arrangement, ingredient history, licence compliance and current State process remain to be checked. This base Gazette review does not certify the complete law as of 2026 or establish an exemption.",
        "Confirm the product category and production arrangement with the State Licensing Authority, obtain the applicable application checklist and check later amendments and any required new-cosmetic permission."),
    "patents_rights": Card(
        "Section 48 provides the specified exclusive rights for patented products and processes in India; ss.73–74 identify the Controller of Patents and Patent Office.",
        "A patent may protect qualifying product/process claims, but does not itself establish regulatory permission to sell or freedom to operate against other patents.",
        "The scope of proposed claims, third-party rights and regulatory clearance require separate assessments.",
        "Assess patentability and freedom to operate separately, and coordinate any patent application with the Patent Office route."),
    "copyright_scope": Card(
        "The Government Copyright Office handbook explains that copyright protects expression, rather than ideas, methods or facts, and that acquisition is automatic without registration formalities.",
        "Original written or artistic descriptions may qualify; the medicine's formula and manufacturing method are not monopolised by copyright.",
        "Eligibility and ownership of the actual creative works remain unverified; the historical handbook does not establish current procedural fees or office particulars.",
        "Identify original expression worth protecting and document its authorship and ownership separately from the formulation itself."),
    "bda_ppv_exception": Card(
        "Section 6(3) excludes applications for plant-variety rights from section 6, while s.6(4) requires the granting authority to send a copy of the grant document to NBA.",
        "This is a specific section 6 exception for plant-variety rights; it does not remove every possible obligation for access to the underlying resources.",
        "Any applicable access, sourcing or other biodiversity duties still require the actual material and applicant facts.",
        "If pursuing plant-variety registration, distinguish the s.6 exception from the separate access and sourcing analysis."),
    "bda_ipr_forms": Card(
        "Rule 16 of the 2024 Rules prescribes Form 7 for s.3(2) IP approval, Form 8 for s.7 pre-grant registration and Form 9 for s.7 commercialisation approval. Rule 18 prescribes Form 10 for the covered use in India of resources or associated knowledge obtained from a foreign country.",
        "Match the applicant and activity to the correct form. Genuine foreign sourcing needs its own analysis and does not automatically eliminate biodiversity compliance.",
        "Applicant identity, the actual sourcing country, intended use and provider-country obligations have not been established.",
        "Check the applicable NBA form and ensure the IP applicant identity and resource-origin records support the filing."),
    "dc_sourcing_records": Card(
        "Rule 157A requires the specified annual raw-material record in Schedule TA, submitted to the State Drug Licensing Authority and National Medicinal Plants Board or its nominee by 30 June of the following financial year. Rules 158 and 160 require relevant manufacturing, testing and identification records.",
        "ASU manufacturing records are separate from biodiversity certificates and agreements; one document does not automatically satisfy every record-keeping duty.",
        "The facility's licensing circumstances and completeness of the actual raw-material and testing records require review.",
        "Maintain batch-linked raw-material, manufacturing and test records and calendar the applicable annual Schedule TA submission."),
    "patents_3c": Card(
        "Section 3(c) excludes the mere discovery of a scientific principle or abstract theory, or discovery of any living thing or non-living substance occurring in nature.",
        "Merely discovering a naturally occurring plant substance does not establish an invention; a claimed technical product or process must be assessed independently.",
        "Whether the claim is only to a natural discovery or to a qualifying technical invention depends on the actual claim and supporting evidence.",
        "Distinguish any natural substance discovery from the claimed technical contribution in the patent analysis."),
    "dc_label_disclosure": Card(
        "The ASU provisions require a true ingredient list; Rule 161 requires patent/proprietary ASU labels to disclose the specified ingredient particulars, including botanical names, parts, form and quantity, with a separate enclosed list permitted in the prescribed circumstances.",
        "A proprietary formulation cannot simply be kept wholly secret after compliant sale where ingredient quantities must be disclosed. Assess confidential process know-how separately.",
        "The actual label, formulation and applicable labelling particulars need regulatory review.",
        "Prepare the mandatory ingredient disclosures and retain as confidential only information that need not be disclosed by law or the chosen patent claims."),
    "bda_sourcing": Card(
        "The 2025 ABS Regulations' Form B specifies resource and sourcing particulars, including names, plant parts, quantities, access dates, wild/cultivated/trader/repository sources, geographical location and relevant supplier or traditional-knowledge particulars.",
        "Maintain material-specific records capable of supporting the applicable biodiversity filing; the provenance of each plant needs to be documented separately.",
        "Which filings and fields apply to this activity, and whether the suppliers' records substantiate the claims, remain unverified.",
        "Record botanical/common names, parts, quantities, access dates, cultivation/wild status, source locations, supplier/repository details and any associated knowledge holder."),
    "bda_origin_2025": Card(
        "The 2025 Rules amendment replaces Rule 19 from 1 November 2025 with the prescribed BMC record/application/certificate procedure using Forms 11, 11A and 12 for cultivated medicinal plants.",
        "The certificate route concerns documented cultivated medicinal plants; a cultivation assertion alone does not complete the prescribed certificate process.",
        "Availability of the relevant BMC records, the certificate for the actual material/quantity and implementation of the procedure require confirmation.",
        "Check the applicable BMC records and complete/verify the prescribed certificate-of-origin process for the actual plants and quantities."),
    "bda_abs_2025": Card(
        "The 2025 ABS Regulations replace the 2014 regulations and prescribe different access and IP-commercialisation benefit-sharing frameworks, including distinct provisions for own commercial use and licensing.",
        "An access-related exemption or nil access rate cannot automatically be used to decide the separate IP-commercialisation liability.",
        "The applicable trigger, exemptions, calculation base, turnover, licensing receipts, traditional-knowledge factors and approval conditions are needed to determine a case-specific amount.",
        "Assess the applicable 2025 regulation with the access/IP route and actual financial/sourcing facts before calculating benefit-sharing payments."),
    "dc_3a": Card(
        "Section 3(a) covers ASU medicines intended for internal or external use in the diagnosis, treatment, mitigation or prevention of disease or disorder in humans or animals, and manufactured exclusively according to formulae in the authoritative books listed in the First Schedule.",
        "Assess the classical ASU route only if both the statutory medicinal intended use and the authoritative-formula manufacturing condition are met. A book-formula match alone does not classify a product intended only for cosmetic purposes as a classical medicine.",
        "The actual intended use, complete formula, manufacture and comparison with the relevant authoritative books require verification; formula matching alone cannot establish this category.",
        "Check the actual medicinal intended use and compare the complete formula and manufacture with the First-Schedule books before choosing a licensing category."),
    "dc_3h": Card(
        "An ASU patent or proprietary medicine must contain only ingredients mentioned in formulae in First-Schedule authoritative books; the formulation itself must not be included there, and parenteral medicines are excluded.",
        "The proprietary category is a possible fit if every ingredient passes that book-based test and the route is non-parenteral. A proprietary drug classification does not itself establish patentability.",
        "Ingredient identities, their book references and the administration route are needed to confirm eligibility; describing plants as Ayurvedic is insufficient.",
        "Prepare an ingredient-by-ingredient list of authoritative-book references and record the administration route for regulatory review."),
    "patents_invention": Card(
        "A patentable invention must be a new product or process involving an inventive step and capable of industrial application; the Act separately defines inventive step and new invention.",
        "A formulation or extraction/manufacturing process could be assessed as a product or process invention. Company development and absence from classical texts alone do not prove novelty or inventive step.",
        "No prior-art search, claim analysis or experimental evidence has established that this particular invention satisfies those tests.",
        "Document the claimed technical contribution and commission a prior-art and patentability assessment before selecting claims."),
    "patents_3p": Card(
        "Traditional knowledge, and aggregation or duplication of known properties of traditionally known components, are excluded from inventions by s.3(p).",
        "Using a new combination of familiar herbs does not by itself overcome the traditional-knowledge exclusion.",
        "Whether the proposed claims merely reproduce traditional knowledge requires a claim-specific prior-art comparison.",
        "Compare the proposed claims and each claimed effect with traditional-knowledge and other prior art."),
    "patents_3e": Card(
        "Section 3(e) excludes a mere admixture giving only an aggregation of component properties and a process for producing that substance.",
        "A mixture that only adds the known effects of its herbs may fail this exclusion; evidence of an interaction beyond that aggregation is relevant to the assessment.",
        "The sources do not establish that this formulation has such an effect or that evidence of synergy alone would guarantee a patent.",
        "Have the patent professional assess comparative evidence of the combination's effect against the individual components."),
    "patents_3d": Card(
        "Section 3(d) excludes a new form of a known substance without enhancement of known efficacy and other specified discoveries involving known substances or processes.",
        "Review this exclusion if the proposed claim concerns a new form, use or process involving a known substance; a new label or dosage is not enough to decide patentability.",
        "The identity of the known substance, the precise claims and the relevant efficacy evidence are not supplied.",
        "Identify any known-substance or known-process elements and have the applicable s.3(d) tests assessed."),
    "patents_3i": Card(
        "Section 3(i) excludes processes for specified medicinal and other treatment of humans and similar treatment of animals.",
        "A claim to a treatment or administration regimen can engage this exclusion; a product or manufacturing-process claim must be assessed on its own terms.",
        "No proposed claim wording is available to determine whether a dosage feature is claimed as a product feature or a treatment method.",
        "Separate proposed composition/manufacturing claims from treatment-method or dosing-regimen claims for patent review."),
    "patents_3j": Card(
        "Section 3(j) excludes plants and animals in whole or part, including seeds, varieties and species, and essentially biological production or propagation processes, subject to its micro-organism exception.",
        "A plant, plant part or variety is not made patentable simply by being used in a new medicine; formulation/process eligibility requires a separate assessment.",
        "The exact subject matter of any plant-related claims remains unspecified.",
        "Distinguish the medicine or technical process from claims directed to plants, seeds or varieties themselves."),
    "patents_specification": Card(
        "A complete specification must sufficiently describe the invention, its operation/use and performance method, disclose the best method known to the applicant, and define the claims. Section 10(4) also addresses source and geographical origin of biological material used in the invention.",
        "Trade secrecy cannot replace disclosures required to support the invention claimed in a patent; biological-material provenance must be considered in drafting.",
        "Which process details are necessary for sufficient disclosure, and any applicable deposit requirements, require review of the actual invention.",
        "Give the patent drafter the reproducible method, relevant best-method details, biological-material sources and geographical origins."),
    "patents_disclosure": Card(
        "Section 11A provides for publication of patent applications subject to its exceptions; the Act's anticipation provisions contain specific, limited exceptions for certain disclosures.",
        "Public disclosure can affect novelty. Relying on secrecy after publication, or assuming a broad grace period for every disclosure, would be unsafe.",
        "The effect of any past disclosure depends on its content, date, recipients and the statutory exception, if any.",
        "Record prior disclosures and keep unpublished formulation ratios, extraction parameters and process know-how confidential while the filing strategy is assessed."),
    "trade_secret": Card(
        "Confidential know-how may be protected through trade-secret/confidentiality arrangements; this is distinct from registration of a patent.",
        "A process that can remain confidential may be suitable for secrecy; readily discoverable product composition and information that a patent must disclose need a different assessment.",
        "Whether secrecy is commercially effective, whether information is actually confidential, and the enforceability of specific agreements require professional review.",
        "Limit access to non-public formulae and process parameters, use appropriate confidentiality agreements and document who receives the information."),
    "tm_act": Card(
        "Trade marks distinguish the commercial origin of goods or services. Distinctiveness and the refusal grounds in s.9 matter; a descriptive or generic product name may not qualify.",
        "A distinctive product brand, logo or qualifying get-up can be considered for protection; trademark rights do not protect the medicinal formula, extraction technique or manufacturing method.",
        "Availability of the proposed mark, competing marks and the correct goods/services specification have not been checked.",
        "Choose a distinctive brand and conduct clearance before applying for the relevant goods/services."),
    "copyright_act": Card(
        "Copyright subsists in the original works specified by s.13, including literary and artistic works; ownership and registration are separate questions under the Act.",
        "Original label artwork, written material and manuals may qualify as expression. This does not confer protection over the underlying medicinal formula or functional process.",
        "Originality, ownership, assignments and any overlap with industrial-design rules require the actual works and agreements.",
        "Keep dated artwork/text files and confirm ownership or assignments for commissioned creative material."),
    "gi_act": Card(
        "A geographical indication identifies goods whose quality, reputation or other characteristic is essentially attributable to a geographical origin; s.11 provides the registration application route for representatives of producers' interests.",
        "GI protection is relevant only if the goods have the required origin-linked characteristic; using Indian plants alone does not establish that link or give a company exclusive rights to a recipe.",
        "No qualifying region, producer group or origin-linked quality/reputation has been established for this product.",
        "Assess GI only if there is evidence of a defined geographical origin and a qualifying producer-linked characteristic."),
    "ppvfr_act": Card(
        "The PPV&FR Act provides a separate plant-variety registration system and recognises farmers' rights; registration eligibility must be assessed under the Act.",
        "This may be relevant to a qualifying cultivated medicinal-plant variety, but ordinary use of an existing plant in a formulation does not establish a plant-variety right.",
        "A distinct variety, eligible applicant and applicable registration conditions have not been established.",
        "If the company has developed or holds rights in a candidate variety, check eligibility with the PPV&FR Authority."),
    "designs_act": Card(
        "Registered designs concern eligible visual features of an article, such as shape, configuration, pattern or ornament, rather than a principle of construction; the Act requires a new or original design. Section 11 provides 10 years of protection, extendable by 5 years.",
        "A qualifying bottle or packaging appearance may be protectable separately from the medicine; functional formulation or processing know-how is not protected by that appearance right.",
        "Novelty, prior publication, functionality and the design's eligibility need review of the actual article.",
        "Assess a distinctive new packaging design before publishing it or applying for registration."),
    "bda_s3": Card(
        "Section 3 requires prior NBA approval for the specified access purposes by persons within s.3(2), which distinguishes non-citizens, the specified non-resident citizens and covered foreign/foreign-controlled entities.",
        "Determine the company's incorporation and control, and any individual's citizenship/residence, before selecting the NBA or State Board access route.",
        "The company structure/control, applicant status, access purpose and material actually accessed are not supplied.",
        "Record incorporation, ownership/control and relevant residency facts, then assess s.3 before the proposed access."),
    "bda_scope": Card(
        "The Biological Diversity Act defines biological resources and commercial utilisation and includes specific exclusions; applicability depends on the resource, associated knowledge and activity.",
        "The Indian identity or name of a plant alone does not settle the access route. The material's actual source and whether the accessed item falls within the statutory definitions matter.",
        "Actual sourcing, material type, date/purpose of access and any relevant exemption remain to be verified.",
        "Create a material-by-material sourcing record: identity, source/location, supplier, wild or cultivated status, access date and intended use."),
    "bda_s6": Card(
        "For IP based on research/information on a biological resource accessed from India (including deposits in repositories outside India), or associated traditional knowledge, s.6(1) requires s.3(2) persons to obtain NBA approval before grant. Section 6(1A) requires NBA registration by s.7 persons before grant; under s.6(1B), those s.7 persons obtaining the IP right need prior NBA approval at commercialisation.",
        "The required step is applicant-specific. These provisions do not create a uniform NBA-approval-before-filing rule for every applicant.",
        "Applicant category, the link between the IP and the Indian-accessed resource/knowledge, and current NBA procedures must be confirmed.",
        "Identify the applicant category and plan the corresponding NBA approval/registration before grant and, where s.6(1B) applies, approval at commercialisation."),
    "bda_s7_exemption": Card(
        "Section 7 requires persons outside s.3(2) to give prior intimation to the State Biodiversity Board for the covered commercial access. Its proviso includes codified traditional knowledge, cultivated medicinal plants/products and specified local/professional categories; s.7(2) makes the cultivated-medicinal-plant exemption conditional on a certificate of origin from the Biodiversity Management Committee, with s.7(3) addressing records and issue.",
        "Cultivation should not be assumed from a supplier's description. This section-specific exemption is not a blanket waiver of s.6 IP duties or every possible benefit-sharing condition.",
        "Whether a particular source qualifies, whether the required certificate exists, and the applicable procedure require confirmation.",
        "If relying on cultivated medicinal plants, obtain/verify the certificate of origin through the Biodiversity Management Committee and assess s.7 separately from s.6."),
    "bda_abs": Card(
        "The Act provides for fair and equitable benefit-sharing conditions in the relevant approval framework; s.21 addresses benefit-sharing determination and possible forms of sharing.",
        "ABS obligations can arise where the applicable access/IP approval framework is triggered; an exemption from one procedural step does not by itself decide all benefit-sharing obligations.",
        "The applicable current regulations, calculation base/rate, recipients, exemptions and approval terms for this applicant/source require confirmation; no case-specific amount is established here.",
        "Have NBA/SBB applicability and the current benefit-sharing terms assessed using the applicant, material, use and sourcing records."),
    "dc_licensing": Card(
        "The ASU provisions require the applicable manufacturing licence and compliance with its conditions; the Drugs and Cosmetics Rules establish the State Licensing Authority and the relevant licensing procedure.",
        "For an eligible ASU proprietary medicine, the State/UT ASU licensing authority is the relevant manufacturing route; final category and licence requirements must be confirmed for the actual product.",
        "The manufacturing location, facilities, product category and complete filing particulars have not been supplied.",
        "Approach the State/UT ASU licensing authority with the proposed category, ingredient references, manufacturing details and required evidence before manufacture for sale."),
    "dc_rule_158b": Card(
        "Rule 158B differentiates classical and patent/proprietary ASU medicines and prescribes the applicable evidence requirements for a manufacturing licence.",
        "Novelty of the combination does not settle the evidence package; the applicable class and use determine which Rule 158B requirements need to be met.",
        "The exact product, intended use, ingredients and applicable evidence category require regulatory review.",
        "Map the product to the applicable Rule 158B category and prepare the required safety/effectiveness evidence with the licensing authority."),
    "dc_schedule_t": Card(
        "Schedule T sets GMP requirements for ASU manufacture, including premises, hygiene, equipment, quality control and documentation.",
        "An eligible ASU manufacturing operation needs the applicable Schedule T compliance as part of its licensing preparation.",
        "Facility compliance, quality-control arrangements and product-specific documentation have not been assessed.",
        "Check the manufacturing facility and quality/documentation systems against Schedule T before licensing and launch."),
    "ip_authorities": Card(
        "The respective IP statutes allocate patent, trademark, design and other registration functions to their designated offices and authorities.",
        "Choose the office by the right sought; an IP registration is a separate matter from a medicine manufacturing licence or biodiversity approval.",
        "The correct filing details and any professional representation depend on the application being made.",
        "Coordinate the patent/trademark/design filings with the relevant IP office and keep the regulatory and biodiversity filings separately tracked."),
    "dmr_act": Card(
        "Sections 3 and 4 of the Drugs and Magic Remedies (Objectionable Advertisements) Act restrict specified drug advertisements and misleading claims.",
        "IP rights or a manufacturing licence do not themselves establish that every proposed therapeutic advertisement is permissible.",
        "The legality of particular label or advertising claims requires their exact wording and applicable current rules.",
        "Review planned medicinal claims and advertisements against the statutory restrictions before publication."),
    "rule_170": Card(
        "The dated record describes Rule 170's 2024 omission, the Supreme Court stay on 27 August 2024, and the order of 11 August 2025 that VACATED that stay. The DMR Act remained relevant to ASU advertising in that account.",
        "That timeline answers the historical question; it cannot establish the rule's status after the record's review date.",
        "Later orders and notifications, and the present status of Rule 170, require live verification.",
        "Use the cited dates to trace the history and check subsequent official orders before relying on current advertising procedure."),
    "patents_rules_2024_rfe": Card(
        "The 2024 amendment reduced the request-for-examination deadline to 31 months; applications filed before commencement retain the 48-month period under the transition rule.",
        "Select the deadline using the application's filing date and the applicable priority/filing-date rule, rather than applying 31 months to every application.",
        "The filing/priority dates and any case-specific deadline relief are not supplied.",
        "Confirm the applicable transition category and calendar the examination request deadline."),
    "patents_rules_2024_form27": Card(
        "Under amended Rule 131, Form 27 is due once for each period of three financial years starting with the financial year after grant, within six months after that period ends. The revised form asks whether the patent is available for licensing and removes the approximate revenue/value figures.",
        "This is a post-grant working statement obligation; calculate the filing period from the grant date rather than treating Form 27 as a patent-application requirement.",
        "The grant date and resulting financial-year period for a particular patent are not supplied.",
        "Use the grant date to calendar each three-financial-year period and the following six-month filing window."),
    "tkdl": Card(
        "The dated source describes TKDL as a defensive prior-art database of codified traditional knowledge, with restricted full access for patent offices under access agreements.",
        "TKDL can be relevant to traditional-knowledge prior art; IP-SAKTI's public legal corpus does not provide access to the restricted full TKDL database.",
        "Current database counts, participating offices and access conditions are not established by this dated record.",
        "Use the official TKDL referral for its access conditions and account for traditional-knowledge prior art in patent review."),
    "fssai_aahar": Card(
        "The Ayurveda Aahara Regulations define the food category by the specified authoritative-book framework and exclude Ayurvedic drugs and proprietary Ayurvedic medicines.",
        "A product intended and regulated as an Ayurvedic proprietary medicine cannot be treated as Ayurveda Aahara merely to choose the food route.",
        "Food eligibility, claims and the exact recipe/process need an independent classification assessment.",
        "Determine intended use and the applicable definition before choosing an FSSAI food route."),
    "phytopharma_gsr918": Card(
        "The cited notification defines a phytopharmaceutical by a purified, standardised medicinal-plant fraction with a minimum of four (4) bio-active or phytochemical compounds assessed qualitatively and quantitatively, for the specified medicinal uses, excluding parenteral administration; it identifies the CDSCO drug pathway.",
        "Four plants are not the same criterion as four characterised compounds in such a fraction. A novel herbal combination is not automatically a phytopharmaceutical.",
        "The fraction, compound characterisation and current applicable new-drug procedure require regulatory confirmation.",
        "If the product is such a purified fraction, assess that definition and confirm the applicable CDSCO pathway."),
    "pct": Card(
        "The PCT provides a single international application procedure; it does not grant a global patent, and national/regional offices decide grant.",
        "It can preserve options for seeking patents in multiple jurisdictions, subject to the relevant national phases and deadlines.",
        "The countries, filing/priority dates and national eligibility requirements for a particular invention are not established.",
        "Identify target countries and obtain filing-deadline advice before selecting an international route."),
    "madrid": Card(
        "The Madrid System provides an international trademark application and management route through the home office for designated members.",
        "It can support a brand's export-market filing strategy; protection depends on the designated markets and their examination.",
        "Applicant eligibility, the basic mark and target-market availability require confirmation.",
        "Identify export markets and assess the home-office and basic-mark requirements."),
    "hague": Card(
        "The Hague System provides an international application route for industrial designs across designated members.",
        "It may be relevant to an eligible applicant seeking design protection in multiple member jurisdictions.",
        "Applicant entitlement and the target jurisdictions' requirements are not established for this case.",
        "Check entitlement and designated markets before selecting the Hague route."),
    "budapest": Card(
        "The Budapest Treaty enables recognised micro-organism deposits at an International Depositary Authority to serve the relevant patent-disclosure requirement in member states.",
        "This concerns qualifying micro-organism deposits; it is not a general registration route for plants or medicinal formulations.",
        "Whether the invention needs a deposit and meets the patent office's conditions remains unestablished.",
        "Assess the need and timing of a deposit if the invention involves a qualifying micro-organism."),
    "wipo_gratk": Card(
        "The 2024 WIPO GRATK Treaty sets genetic-resource/traditional-knowledge patent-disclosure provisions and an entry-into-force threshold in Article 17.",
        "Adoption alone does not establish that the treaty is in force or directly imposes a filing duty on this applicant today.",
        "Current ratifications, entry into force and relevant domestic implementation require the official live status record.",
        "Check WIPO's official status and the applicable national rules before relying on an operative treaty obligation."),
    "cbd_nagoya": Card(
        "The CBD and Nagoya framework concerns sovereign resource access, prior informed consent, mutually agreed terms and benefit sharing.",
        "A project's obligations must be assessed through the applicable domestic access and benefit-sharing framework.",
        "These international summaries do not determine a particular country's procedure, exemption or monetary rate.",
        "Identify the source jurisdiction and the domestic access/benefit-sharing rules governing the material."),
    "trips_27_3b": Card(
        "TRIPS Article 27.3(b) permits specified plant/animal patent exclusions but requires plant-variety protection by patents, an effective sui generis system, or a combination.",
        "The treaty allows distinct national mechanisms; it does not mean every plant variety is patentable in every jurisdiction.",
        "Eligibility of a particular variety and the applicant's rights require the domestic law and facts.",
        "Check the plant-variety mechanism used by the relevant jurisdiction."),
    "eu_thmpd": Card(
        "The cited EU traditional-use route requires evidence of at least 30 years of medicinal use, including 15 years within the EU, under the specified framework.",
        "An Ayurveda-derived product is not automatically eligible merely because its medical tradition is longstanding; product-specific qualifying use matters.",
        "The actual product's use history and all registration conditions have not been established.",
        "Collect product-specific use history and assess the competent authority's requirements."),
    "case_turmeric": Card(
        "The source records the cancellation of all claims of the turmeric wound-healing patent after CSIR's prior-art challenge and the 1998 re-examination certificate.",
        "The example illustrates why previously known medicinal uses can defeat patent claims; it does not decide a different invention's validity.",
        "Any new claim needs its own prior-art and legal assessment.",
        "Use the case as a prior-art lesson rather than a substitute for examining the proposed claims."),
    "case_basmati": Card(
        "The source records cancellation of 15 of the 20 original RiceTec claims in the 2002 re-examination, with specified surviving or amended claims.",
        "The record does not support a blanket claim that every claim was cancelled or that a generic monopoly over basmati survived.",
        "The scope of any relevant surviving rights requires the actual claims and status record.",
        "Read the official re-examination record and precise claims before drawing conclusions about scope."),
}

# The same statute can support distinct questions. These scoped propositions
# avoid repeating an entire patent or access analysis in the authorities row.
ISSUE_CARDS = {
    "authorities": {
        "dc_cosmetic_licensing": Card(
            "Rule 4(2) of the 2020 Cosmetics Rules Gazette identifies the State Licensing Authority for manufacture for sale or distribution of cosmetics; r.23(3) additionally requires prior Central permission for the defined new-cosmetic category.",
            "For a product classified as a cosmetic, confirm the State drugs controller or delegated licensing office for the premises and whether the specific new-cosmetic route applies.",
            "Final classification, novel-ingredient status, the actual premises and any later procedural changes need review.",
            "Confirm the cosmetic manufacturing or loan-licence route with the relevant State Licensing Authority and any required Central permission."),
        "patents_rights": Card(
            "Sections 73–74 establish the Controller of Patents and Patent Office.",
            "Use the IP India Patent Office route for patent applications; drug licensing remains a separate decision.",
            "The appropriate filing particulars and claim strategy need professional review.",
            "Coordinate the proposed patent claims and filing with the Patent Office."),
        "tm_act": Card(
            "Sections 3–5 establish the Registrar and Trade Marks Registry; section 18 governs applications.",
            "Use the Trade Marks Registry route for a qualifying product brand.",
            "The proposed mark's availability has not been checked.",
            "Clear the proposed brand and prepare its goods/services specification."),
        "gi_act": Card(
            "The GI Registrar/Registry administers registration and authorised-user routes under the cited provisions.",
            "Contact that Registry only if there is a qualifying geographical indication and producer entitlement.",
            "No qualifying origin-linked product or producer entitlement has been established.",
            "Check geographical eligibility and the applicant's producer-representative role."),
        "ppvfr_act": Card(
            "The PPV&FR Act supplies the separate plant-variety registration route and farmers' rights.",
            "Consult the PPV&FR Authority if a candidate medicinal-plant variety and applicant entitlement exist.",
            "Variety eligibility and relevant species notifications require confirmation.",
            "Check the candidate variety and applicant entitlement with the PPV&FR Authority."),
        "dc_licensing": Card(
            "Rule 152 provides for State-appointed ASU licensing authorities; rules 153–154 govern manufacturing applications and licences.",
            "Identify the State/UT AYUSH/ASU licensing authority for the manufacturing premises. Novelty alone does not move a proprietary ASU medicine to CDSCO.",
            "The premises, applicable licence conditions and specific administrative office require confirmation.",
            "Confirm the competent State/UT licensing office and applicable manufacturing application."),
        "bda_s3": Card(
            "NBA provides the prior access approval required for covered section 3(2) persons and activities.",
            "Determine applicant control/status and access purpose before selecting the access authority.",
            "Applicant status and the actual access activity have not been established.",
            "Assess NBA access approval before any covered access."),
        "bda_s6": Card(
            "NBA handles section 6 IP approval or registration and applicable commercialisation approval according to applicant category.",
            "Coordinate the separate NBA milestones with IP grant and commercialisation.",
            "The applicable applicant category and commercialisation trigger require confirmation.",
            "Map section 6 approval/registration to the applicant and planned timeline."),
        "bda_s7_exemption": Card(
            "Section 7 identifies State Biodiversity Board intimation and the BMC certificate condition for cultivated medicinal plants.",
            "Use the concerned SBB for a triggered intimation and the BMC for the prescribed cultivation-origin certificate.",
            "The relevant Board/BMC and the exemption conditions need sourcing facts.",
            "Identify the concerned SBB and BMC from the actual resource sourcing."),
        "phytopharma_gsr918": Card(
            "The cited source identifies a defined phytopharmaceutical category and the CDSCO drug pathway.",
            "Assess CDSCO if the product meets that category; four plants alone do not meet its compound-characterisation test.",
            "The actual fraction and current applicable procedure require regulatory review.",
            "Confirm whether the defined phytopharmaceutical route is applicable before approaching CDSCO."),
    },
    "sourcing": {
        "bda_scope": Card(
            "Biological-resource access and commercial utilisation depend on the statutory definitions, resource and activity.",
            "Document actual material origin and access history; an Indian species name or processed final product alone does not decide applicability.",
            "The material, access dates, origin and activity remain unverified.",
            "Trace each botanical material and its access history through the supply chain."),
        "bda_s7_exemption": Card(
            "The cultivated medicinal-plant exemption in section 7 requires the prescribed BMC certificate of origin.",
            "Retain a certificate for the actual cultivated material rather than relying only on a supplier's assertion.",
            "The certificate and relevant cultivation records have not been supplied.",
            "Verify the BMC origin certificate against the plants and quantities sourced."),
        "patents_specification": Card(
            "Section 10(4) addresses disclosure of source and geographical origin of biological material used in the invention.",
            "Give the patent drafter substantiated biological-material provenance.",
            "The actual source/geographical origin declarations and any applicable deposit requirements need review.",
            "Preserve supplier and geographical-origin records for patent disclosure."),
        "bda_ipr_forms": Card(
            "Rule 18 prescribes Form 10 for the covered use in India of resources or knowledge obtained from a foreign country.",
            "Foreign sourcing needs a separate provider-country and Indian declaration analysis.",
            "The actual foreign source and provider-country obligations remain unverified.",
            "Document foreign resource origin and assess Form 10 where applicable."),
        "bda_sourcing": CARDS["bda_sourcing"],
        "bda_origin_2025": CARDS["bda_origin_2025"],
        "dc_sourcing_records": CARDS["dc_sourcing_records"],
    },
}

