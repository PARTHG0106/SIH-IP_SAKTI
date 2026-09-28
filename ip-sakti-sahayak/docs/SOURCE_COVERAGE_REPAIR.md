# Source coverage repair - 28 September 2026

Four narrowly reviewed records support questions previously left without relevant sources: `patents_ownership`, `patents_assignments`, `dc_cosmetic` and `dc_cosmetic_licensing`. The corpus now has 58 records: 37 `primary_checked`, 19 `dossier_record` and 2 `needs_review`. The primary archive manifest contains 17 PDFs. Existing corpus records were not rewritten or upgraded.

`primary_checked` means the identified passage was read against its primary document, including complete relevant pages and footnotes. It does not establish the complete law in force today, product approval, patentability, a private party's entitlement, or the result of a legal dispute. Curated source summaries and answer cards remain paraphrases; the quotations below document the checked foundation.

## Patent inventorship, entitlement and assignments

Source: the [Patents Act statutory text hosted by WIPO Lex](https://www.wipo.int/wipolex/en/legislation/details/22960), already archived as `corpus/primary/patents-act.pdf`.

- SHA-256: `bd585b402db59cd1d386a8db79b415d04b771dc027406e9356bb087ae09e68f7`
- Size: 678,068 bytes; 69 pages.
- Existing archive/publisher comparison: 27 September 2026. Additional passage review: 28 September 2026.
- PDF and printed pages checked: 10-11, 13, 22-23 and 37.
- `as_of: 2005-01-01` follows the existing corpus provision date. Section 68's amendment footnote expressly gives that commencement date. This is not presented as a complete consolidation date or proof that no later amendment exists.

`patents_ownership` separates the applicant's right to apply from inventor identification. Section 6(1), subject to section 134, lists the person claiming to be the true and first inventor, the assignee of that person's right to apply, and the specified deceased person's legal representative; subsection (2) permits those persons to apply alone or jointly. Section 7(2) requires proof of the assignment-based right to apply. Section 7(3) requires naming the person claiming to be the true and first inventor and the specified declaration when that person is not an applicant. Section 10(6) addresses the inventorship declaration in prescribed cases, form and period. Section 28(1) expressly separates inventor mention from rights under the patent.

Checked quotations (line breaks normalised; no substantive wording changed):

> "Where the application is made by virtue of an assignment of the right to apply for a patent for the invention, there shall be furnished with the application, or within such period as may be prescribed after the filling of the application, proof of the right to make the application." - s.7(2), p.11. The PDF prints "filling".

> "Provided that the mention of any person as inventor under this section shall not confer or derogate from any rights under the patent." - s.28(1), p.23.

`patents_assignments` covers transactions in patent rights under sections 68 and 69(1)-(3). It does not collapse these rules into proof of the right to apply under section 7, or assume that an NDA, salary, university affiliation or payment assigns an invention.

> "An assignment of a patent or of a share in a patent, a mortgage, licence or the creation of any other interest in a patent shall not be valid unless the same were in writing and the agreement between the parties concerned is reduced to the form of a document embodying all the terms and conditions governing their rights and obligations and duly executed." - s.68, p.37.

Section 69(1) requires the person acquiring the specified title or interest to apply in writing to register that title or notice of interest; section 69(2) also permits the specified other party to apply. Section 69(3) requires proof of title and permits the Controller to defer action on a disputed transaction until a competent court determines rights. No present forms, deadlines, fees, employee-invention doctrine, university policy, foreign ownership rule or case-specific contribution finding was added.

## Cosmetic classification boundary

Source: [CDSCO's official compilation amended through 31 December 2016](https://cdsco.gov.in/opencms/export/sites/CDSCO_WEB/Pdf-documents/acts_rules/2016DrugsandCosmeticsAct1940Rules1945.pdf), already archived as `corpus/primary/dc-act-2016.pdf`.

- SHA-256: `62bc0d8fd5f9d0c6be90b2fb86f67f8ed5280ac719a038fbf9f26fc8aa5036bf`
- Size: 8,643,659 bytes; 635 pages.
- Additional passage review: 28 September 2026; PDF/printed pp.6-7.
- `as_of: 2016-12-31` is the compilation's stated amendment cutoff, not a 2026 consolidation.

`dc_cosmetic` uses sections 3(aaa), 3(a) and 3(b)(i) to distinguish cosmetic purpose from the stated medicinal purposes. It allows a conditional cosmetic assessment for Ayurveda-related hair or skin products without converting an ingredient name into an automatic ASU-drug classification. The complete formula, intended function, presentation and claims remain necessary for a particular classification.

> "cosmetic" means any article intended to be rubbed, poured, sprinkled or sprayed on, or introduced into, or otherwise applied to, the human body or any part thereof for cleansing, beautifying, promoting attractiveness, or altering the appearance, and includes any article intended for use as a component of cosmetic - s.3(aaa), p.7 (amendment markers omitted).

The adjoining medicinal-use definitions were checked in full, including the classical ASU formula condition in section 3(a). No claim that absence of a disease claim automatically exempts a product from drug law, licensing, safety standards or advertising rules was adopted.

## Cosmetics manufacturing route

New primary archive: `corpus/primary/cosmetics-rules-2020.pdf`, the [15 December 2020 Gazette, G.S.R. 763(E)](https://cdsco.gov.in/opencms/resources/UploadCDSCOWeb/2022/cos_rules/CR_G.S.R.%20763(E)%20dt_15.12.2020_COSMETICS%20RULES%202020.pdf).

- Discovered through the [official CDSCO Cosmetics Rules listing](https://cdsco.gov.in/opencms/opencms/en/Acts-and-rules/Cosmetics-Rules/) on 28 September 2026. The download wrapper with `num_id=OTI2Mg==` contains an iframe; the archived file is the actual referenced PDF, not wrapper HTML.
- SHA-256: `4300f85695e9a787bc5ed008e0f6b2fb9514f408ffb3a0eac1d23bbd2f2ed476`
- Size: 2,885,750 bytes; 136 pages.
- Download and passage review: 28 September 2026; complete English PDF/printed pp.73-75 and 80-81 were read and rendered.
- `as_of: 2020-12-15` is the Gazette date. This is the base Gazette, not a claim of complete amendments as of 2026.

`dc_cosmetic_licensing` covers rules 3(p), 3(r), 3(u), 4(2), 23 and 25. It supports State manufacture/loan-licence assessment: COS-5/COS-6 applications, COS-7 GMP declaration and COS-8/COS-9 licences. It preserves the defined new-cosmetic category and prior Central permission requirement rather than treating every novel formulation as a new cosmetic. It does not quote fees or promise a grant deadline.

> "Any person who intends to manufacture cosmetics shall make an application for grant of a licence or loan licence to manufacture for sale or for distribution to the state Licensing Authority." - r.23(1), p.80.

> "In case of a new cosmetic, the applicant shall obtain prior permission in Form COS-3 as provided in Chapter V from the Central Licensing Authority and no licence to manufacture any cosmetic shall be granted by the State Licensing Authority without such permission." - r.23(3), p.80 (spacing around form number normalised).

Rule 3(r), p.74, defines the new-cosmetic trigger by a novel ingredient not used anywhere in the world or not recognised for cosmetic use in national or international literature. Rule 23(2)'s offline-until-portal-operational proviso and the rest of rule 23 were read; no assertion about today's operational portal is made. Detailed schedules, current ingredient standards, later amendments, imports/exports and State-specific practice require further review.

## Implementation boundaries and verification

The four new records and cards are bound using the existing `source_fingerprint` mechanism; no fingerprint function changed. The cosmetic authority card has a separate scoped allowlist key, `authorities/dc_cosmetic_licensing`. The archive manifest links every new record to its checked PDF and preserves the older verification metadata.

`tests/test_source_coverage_repair.py` verifies archive identity and source links, valid provenance/date metadata, reviewed-card availability, and rejection when legal text or source identity changes. Source checks do not replace end-to-end browser verification of question planning and fact application.

Still unresolved: live legal currency, individual employee/student/contractor title, third-party agreements, foreign law, cosmetic product certification, detailed safety and labelling compliance, ingredient status, current State portals and any licensing exemption. No source supplied by this repair establishes the current Rule 170 position or US market access.

The final browser review also identified an omission in the existing `dc_3a` answer card: its summary retained the book-formula condition but omitted the medicinal intended-use condition already present in its checked source. The card now states both limbs of section 3(a), and makes clear that book matching alone cannot classify a product intended only for cosmetic purposes as a classical ASU medicine. Its underlying source and fingerprint are unchanged. A regression exercises an exact book-formula match combined with conditioning-only claims and requires the answer to retain both the medicinal-use threshold and the separate cosmetic assessment.
