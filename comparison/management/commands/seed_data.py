"""
Seeds the database with the three laws, the comparison categories, the
comparison content, and the compliance-summary questionnaire.

Content policy (see project README):
  - Every ComparisonEntry below was checked against a primary or
    authoritative regulatory source (planalto.gov.br, eur-lex.europa.eu,
    leginfo.legislature.ca.gov, cppa.ca.gov) as of the VERIFICATION_DATE
    below, and is seeded with `is_verified=True` plus a `source_url`
    pointing to the specific source used and a `notes` field recording
    what was checked.
  - A handful of CCPA/CPRA figures (the revenue threshold, administrative
    fine amounts, and private-right-of-action statutory damages) are
    adjusted for inflation by the CPPA every odd-numbered year. Those
    entries are marked verified as of a snapshot date and explicitly flag
    the adjustment cycle so a future reader knows to recheck cppa.ca.gov
    rather than assuming the figure is permanent.
  - If you add a new entry with a specific number (a fine, a percentage,
    a threshold, a deadline, a statutory citation) that has NOT been
    checked against a current primary source, seed it with
    `is_verified=False` and a `notes` value starting with
    "TODO: VERIFY ..." — do not mark unverified content as verified.

Safe to re-run: everything is get_or_create / update_or_create, keyed on
natural/unique fields.
"""

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from comparison.models import Category, ComparisonEntry, Law, ScenarioQuestion, ScenarioRule

# Date this seed data's legal content was last checked against primary/
# regulatory sources. Update this whenever you re-verify the content.
VERIFICATION_DATE = "2026-09-01"

PLANALTO_LGPD = (
    "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm"
)
EUR_LEX_GDPR = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32016R0679"
CA_CIV_CODE = "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=CIV&sectionNum=1798.140."
CPPA_CPI_NOTICE = "https://cppa.ca.gov/regulations/cpi_adjustment.html"
CPPA_REGULATIONS = "https://cppa.ca.gov/regulations/ccpa_updates.html"
ANPD_SMALL_BUSINESS = "https://www.gov.br/anpd/pt-br/acesso-a-informacao/institucional/atos-normativos/regulamentacoes_anpd/resolucao-cd-anpd-no-2-de-27-de-janeiro-de-2022"
ANPD_DOSIMETRY = "https://www.gov.br/anpd/pt-br/acesso-a-informacao/institucional/atos-normativos/regulamentacoes_anpd"

LAWS = [
    {
        "code": "LGPD",
        "full_name": "Lei Geral de Proteção de Dados Pessoais (Lei nº 13.709/2018)",
        "jurisdiction": "Brazil",
        "regulator": "ANPD (Autoridade Nacional de Proteção de Dados)",
        "effective_date": date(2020, 9, 18),
        "official_source_url": PLANALTO_LGPD,
        "color_hex": "#0d9488",
        "order": 1,
    },
    {
        "code": "GDPR",
        "full_name": "General Data Protection Regulation (Regulation (EU) 2016/679)",
        "jurisdiction": "European Union / European Economic Area",
        "regulator": "National Data Protection Authorities (coordinated via the EDPB)",
        "effective_date": date(2018, 5, 25),
        "official_source_url": EUR_LEX_GDPR,
        "color_hex": "#2563eb",
        "order": 2,
    },
    {
        "code": "CCPA/CPRA",
        "full_name": (
            "California Consumer Privacy Act, as amended by the "
            "California Privacy Rights Act (Cal. Civ. Code § 1798.100 et seq.)"
        ),
        "jurisdiction": "California, United States",
        "regulator": "California Privacy Protection Agency (CPPA) and California Attorney General",
        "effective_date": date(2020, 1, 1),
        "official_source_url": "https://oag.ca.gov/privacy/ccpa",
        "color_hex": "#dc2626",
        "order": 3,
    },
]

CATEGORIES = [
    {
        "name": "Scope & Extraterritoriality",
        "slug": "scope-extraterritoriality",
        "icon": "🌍",
        "order": 1,
        "description": "Who and what each law covers, including when it reaches businesses outside its home jurisdiction.",
    },
    {
        "name": "Legal Basis for Processing",
        "slug": "legal-basis-for-processing",
        "icon": "📋",
        "order": 2,
        "description": "The legal grounds a business must have to process personal data under each framework.",
    },
    {
        "name": "Data Subject Rights",
        "slug": "data-subject-rights",
        "icon": "🙋",
        "order": 3,
        "description": "Rights individuals can exercise over their own personal data.",
    },
    {
        "name": "Sensitive Data Categories",
        "slug": "sensitive-data-categories",
        "icon": "🔒",
        "order": 4,
        "description": "Special categories of personal data that receive heightened protection.",
    },
    {
        "name": "Compliance Obligations (DPO/DPIA/Records)",
        "slug": "compliance-obligations-dpo-dpia-records",
        "icon": "📑",
        "order": 5,
        "description": "Organizational accountability requirements: designated privacy roles, risk assessments, and recordkeeping.",
    },
    {
        "name": "Enforcement & Penalties",
        "slug": "enforcement-penalties",
        "icon": "⚖️",
        "order": 6,
        "description": "Who enforces each law and the range of penalties for non-compliance.",
    },
    {
        "name": "Private Right of Action",
        "slug": "private-right-of-action",
        "icon": "🧾",
        "order": 7,
        "description": "Whether individuals can sue directly, as opposed to relying solely on regulator enforcement.",
    },
]

# (category_slug, law_code) -> entry content.
# Every entry here has been checked against the source in `source_url` as of
# VERIFICATION_DATE (see notes for specifics) and is seeded verified=True.
ENTRIES = {
    ("scope-extraterritoriality", "LGPD"): {
        "summary": (
            "Applies extraterritorially: covers processing carried out in Brazil, "
            "processing aimed at offering goods/services to individuals in Brazil, "
            "or processing of data collected in Brazil — regardless of where the "
            "controller/processor is headquartered."
        ),
        "details": (
            "LGPD Art. 3 applies the law to any processing operation carried out by a natural "
            "or legal person, public or private, regardless of the country where its "
            "headquarters are located or where the data is stored, provided that: (I) the "
            "processing is carried out in Brazilian territory; (II) the processing activity "
            "aims to offer or supply goods/services, or to process data of individuals located "
            "in Brazil; or (III) the personal data was collected in Brazil. Data is deemed "
            "'collected in Brazil' when the data subject was in Brazilian territory at the "
            "time of collection."
        ),
        "notes": f"VERIFIED {VERIFICATION_DATE} against planalto.gov.br (Lei 13.709/2018, Art. 3, incisos I-III and §1).",
        "source_url": PLANALTO_LGPD,
        "verified": True,
    },
    ("scope-extraterritoriality", "GDPR"): {
        "summary": (
            "Applies to processing by controllers/processors established in the EU, and "
            "extraterritorially to organizations outside the EU that offer goods/services "
            "to, or monitor the behavior of, individuals in the EU/EEA."
        ),
        "details": (
            "GDPR Art. 3(1) applies the Regulation to processing carried out in the context of "
            "an establishment of a controller or processor in the Union, regardless of whether "
            "the processing takes place in the Union. Art. 3(2) extends it extraterritorially "
            "to controllers/processors not established in the Union where the processing "
            "relates to offering goods or services to data subjects in the Union, or to "
            "monitoring their behavior as far as it takes place within the Union — the feature "
            "most often compared to LGPD Art. 3 and CCPA's threshold-based approach."
        ),
        "notes": f"VERIFIED {VERIFICATION_DATE} against eur-lex.europa.eu (Regulation (EU) 2016/679, Art. 3(1)-(2)).",
        "source_url": EUR_LEX_GDPR,
        "verified": True,
    },
    ("scope-extraterritoriality", "CCPA/CPRA"): {
        "summary": (
            "Applies to for-profit businesses doing business in California that collect "
            "California consumers' personal information and meet at least one of three "
            "thresholds: annual gross revenue above $26,625,000 (2025 figure), buying/"
            "selling/sharing personal information of 100,000+ consumers or households "
            "annually, or deriving 50%+ of annual revenue from selling/sharing personal "
            "information."
        ),
        "details": (
            "Cal. Civ. Code § 1798.140(d) defines 'business' using three independent "
            "thresholds (meeting any one is enough): (1) annual gross revenue in the "
            "preceding calendar year above a statutory figure — originally $25,000,000, "
            "CPI-adjusted by the CPPA every odd-numbered year (currently $26,625,000, "
            "effective Jan. 1, 2025); (2) alone or in combination, annually buys, sells, or "
            "shares the personal information of 100,000 or more consumers or households — "
            "CPRA raised this from CCPA's original 50,000 and removed 'devices' from the "
            "count; or (3) derives 50% or more of annual revenue from selling or sharing "
            "consumers' personal information, which California's Attorney General has "
            "clarified includes revenue from cross-context behavioral advertising, and is "
            "not limited to revenue from California residents."
        ),
        "notes": (
            f"VERIFIED {VERIFICATION_DATE} against Cal. Civ. Code § 1798.140(d) (leginfo.legislature.ca.gov) "
            "and the CPPA's Dec. 17, 2024 CPI adjustment notice (cppa.ca.gov). The revenue threshold is "
            "CPI-adjusted every odd-numbered year — the next adjustment takes effect Jan. 1, 2027, so "
            "recheck cppa.ca.gov/regulations/cpi_adjustment.html before relying on the $26,625,000 figure "
            "after that date."
        ),
        "source_url": CPPA_CPI_NOTICE,
        "verified": True,
    },
    ("legal-basis-for-processing", "LGPD"): {
        "summary": (
            "Processing must fit one of ten legal bases listed in Art. 7 (e.g. consent, "
            "legal/regulatory obligation, contract performance, exercise of rights in legal "
            "proceedings, legitimate interest, credit protection), not consent alone; a "
            "separate, narrower list in Art. 11 applies specifically to sensitive data."
        ),
        "details": (
            "LGPD Art. 7 lists ten hypotheses that independently make processing lawful: "
            "(I) consent; (II) compliance with a legal or regulatory obligation; (III) "
            "execution of public policies by public administration; (IV) research by a "
            "research body, with anonymization favored whenever possible; (V) execution of a "
            "contract, or preliminary procedures related to a contract, to which the data "
            "subject is a party; (VI) exercise of rights in judicial, administrative, or "
            "arbitral proceedings; (VII) protection of life or physical safety; (VIII) health "
            "protection, exclusively in procedures by health professionals; (IX) legitimate "
            "interests of the controller or a third party, subject to a balancing test; and "
            "(X) credit protection. Art. 11 sets a separate, narrower list of bases for "
            "processing sensitive personal data."
        ),
        "notes": f"VERIFIED {VERIFICATION_DATE} against planalto.gov.br (Art. 7, incisos I-X, and Art. 11).",
        "source_url": PLANALTO_LGPD,
        "verified": True,
    },
    ("legal-basis-for-processing", "GDPR"): {
        "summary": (
            "Processing requires one of six legal bases under Art. 6(1): consent, contract, "
            "legal obligation, vital interests, a task carried out in the public interest, "
            "or the legitimate interests of the controller/a third party."
        ),
        "details": (
            "GDPR Art. 6(1)(a)-(f) sets out an exhaustive list of six lawful bases for "
            "processing personal data: (a) consent; (b) necessity for performance of a "
            "contract; (c) necessity for compliance with a legal obligation; (d) necessity "
            "to protect vital interests; (e) necessity for a task carried out in the public "
            "interest or in the exercise of official authority; and (f) necessity for the "
            "legitimate interests of the controller or a third party, unless overridden by "
            "the data subject's interests or fundamental rights (this last basis is not "
            "available to public authorities acting in performance of their tasks)."
        ),
        "notes": f"VERIFIED {VERIFICATION_DATE} against eur-lex.europa.eu (Regulation (EU) 2016/679, Art. 6(1)(a)-(f)).",
        "source_url": EUR_LEX_GDPR,
        "verified": True,
    },
    ("legal-basis-for-processing", "CCPA/CPRA"): {
        "summary": (
            "Not built around an enumerated 'legal basis' requirement the way GDPR/LGPD are — "
            "it instead uses a notice-and-choice model, regulating specific practices "
            "(sale/sharing of data, use of sensitive data) and giving consumers rights to "
            "control them."
        ),
        "details": (
            "CCPA/CPRA (Cal. Civ. Code § 1798.100 et seq.) does not condition processing on "
            "one of a defined list of lawful grounds. Businesses may generally process "
            "personal information for disclosed business purposes, subject to notice-at-"
            "collection obligations and to consumers' rights to opt out of sale/sharing and "
            "to limit use of sensitive personal information — a materially different "
            "structure from GDPR's or LGPD's basis-by-basis approach."
        ),
        "notes": (
            f"VERIFIED {VERIFICATION_DATE} — this is a structural characterization (not a specific "
            "statutory citation) confirmed against Cal. Civ. Code § 1798.100 et seq. and current CPPA "
            "regulatory materials; no lawful-basis requirement has been introduced by subsequent "
            "rulemaking, including the ADMT/risk-assessment regulations effective Jan. 1, 2026."
        ),
        "source_url": CPPA_REGULATIONS,
        "verified": True,
    },
    ("data-subject-rights", "LGPD"): {
        "summary": (
            "Individuals (titulares) have nine rights enumerated in Art. 18 — confirmation of "
            "processing, access, correction, anonymization/blocking/deletion of unnecessary "
            "or excessive data, portability, deletion of consent-based data, information "
            "about data sharing, information about consequences of refusing consent, and "
            "consent revocation — plus a separate right (Art. 20) to request review of "
            "decisions based solely on automated processing."
        ),
        "details": (
            "LGPD Art. 18 lists nine rights the data subject may exercise against the "
            "controller: (I) confirmation of the existence of processing; (II) access to the "
            "data; (III) correction of incomplete, inaccurate, or outdated data; (IV) "
            "anonymization, blocking, or deletion of unnecessary, excessive, or unlawfully "
            "processed data; (V) data portability to another provider, as regulated by the "
            "ANPD; (VI) deletion of data processed with consent, except as provided in Art. "
            "16; (VII) information about public/private entities with which the controller "
            "has shared data; (VIII) information about the option to refuse consent and the "
            "consequences of refusal; and (IX) revocation of consent. Art. 20 separately "
            "gives data subjects the right to request review of decisions made solely on the "
            "basis of automated processing of personal data affecting their interests."
        ),
        "notes": f"VERIFIED {VERIFICATION_DATE} against planalto.gov.br (Art. 18, incisos I-IX, and Art. 20).",
        "source_url": PLANALTO_LGPD,
        "verified": True,
    },
    ("data-subject-rights", "GDPR"): {
        "summary": (
            "Individuals have the right to access (Art. 15), rectification (Art. 16), "
            "erasure/'right to be forgotten' (Art. 17), restriction of processing (Art. 18), "
            "data portability (Art. 20), objection (Art. 21), and rights related to "
            "automated decision-making and profiling (Art. 22)."
        ),
        "details": (
            "GDPR Chapter III (Articles 12-23) sets out data subject rights in detail. "
            "Controllers must generally respond to a rights request without undue delay and "
            "within one month of receipt (extendable by two further months for complex or "
            "numerous requests, with the data subject informed of the extension and reasons "
            "within the first month). Several rights are qualified rather than absolute — "
            "e.g. erasure and portability apply only in specific listed circumstances."
        ),
        "notes": f"VERIFIED {VERIFICATION_DATE} against eur-lex.europa.eu (Regulation (EU) 2016/679, Arts. 12(3), 15-22).",
        "source_url": EUR_LEX_GDPR,
        "verified": True,
    },
    ("data-subject-rights", "CCPA/CPRA"): {
        "summary": (
            "Consumers have the right to know/access, delete, correct, opt out of sale/"
            "sharing (including via the Global Privacy Control), limit use of sensitive "
            "personal information, data portability, and non-discrimination for exercising "
            "these rights. CPPA regulations effective January 1, 2026 add new disclosure "
            "obligations and consumer rights around Automated Decision-Making Technology "
            "(ADMT)."
        ),
        "details": (
            "The original CCPA (2020) gave consumers the right to know what personal "
            "information is collected/sold/disclosed and why, the right to delete it, the "
            "right to opt out of its sale, and the right to non-discrimination for exercising "
            "these rights. CPRA, operative January 1, 2023, added the right to correct "
            "inaccurate personal information and the right to limit use/disclosure of "
            "sensitive personal information, and expanded the opt-out right to cover "
            "'sharing' (e.g. for cross-context behavioral advertising), not just 'sale'. "
            "CPPA regulations approved by the Office of Administrative Law in "
            "September 2025 and effective January 1, 2026 further require businesses using "
            "Automated Decision-Making Technology for significant decisions to provide "
            "pre-use notice and, in defined circumstances, an opt-out or appeal right."
        ),
        "notes": (
            f"VERIFIED {VERIFICATION_DATE} against Cal. Civ. Code § 1798.100 et seq. and the CPPA's "
            "finalized ADMT/risk-assessment/cybersecurity-audit regulations (OAL-approved "
            "Sept. 22-23, 2025; effective Jan. 1, 2026, cppa.ca.gov)."
        ),
        "source_url": CPPA_REGULATIONS,
        "verified": True,
    },
    ("sensitive-data-categories", "LGPD"): {
        "summary": (
            "Defines 'dado pessoal sensível' (Art. 5, II) as data on racial/ethnic origin, "
            "religious conviction, political opinion, membership in a union or religious/"
            "philosophical/political organization, health or sex-life data, and genetic or "
            "biometric data linked to a natural person — subject to a narrower set of legal "
            "bases (Art. 11)."
        ),
        "details": (
            "LGPD's definition of sensitive data closely tracks GDPR's 'special categories,' "
            "with some differences in wording (e.g. it does not separately list sexual "
            "orientation, folding it into 'sex life,' and it frames biometric/genetic data "
            "without GDPR's 'for the purpose of unique identification' qualifier on "
            "biometric data). Processing sensitive data is subject only to the bases listed "
            "in Art. 11, a subset of Art. 7's general list."
        ),
        "notes": f"VERIFIED {VERIFICATION_DATE} against planalto.gov.br (Art. 5, II, and Art. 11).",
        "source_url": PLANALTO_LGPD,
        "verified": True,
    },
    ("sensitive-data-categories", "GDPR"): {
        "summary": (
            "Art. 9(1) prohibits processing data revealing racial/ethnic origin, political "
            "opinions, religious/philosophical beliefs, or trade union membership, and "
            "processing genetic data, biometric data (for unique identification), health "
            "data, or data on sex life/sexual orientation — subject to specific exceptions "
            "in Art. 9(2)."
        ),
        "details": (
            "GDPR Art. 9(1) starts from a general prohibition on processing these 'special "
            "categories' of data. Art. 9(2) lists exceptions that lift the prohibition, "
            "including: explicit consent (unless EU/member state law bars it); necessity for "
            "employment, social security, or social protection law obligations; protection "
            "of vital interests where the subject is incapable of consent; legitimate "
            "activities of a foundation/association with a political, philosophical, "
            "religious, or trade-union aim, limited to members; data manifestly made public "
            "by the data subject; establishment/exercise/defense of legal claims; "
            "substantial public interest; preventive/occupational medicine and health/social "
            "care; public health; and archiving/research/statistical purposes."
        ),
        "notes": f"VERIFIED {VERIFICATION_DATE} against eur-lex.europa.eu (Regulation (EU) 2016/679, Art. 9(1)-(2)).",
        "source_url": EUR_LEX_GDPR,
        "verified": True,
    },
    ("sensitive-data-categories", "CCPA/CPRA"): {
        "summary": (
            "CPRA defines 'sensitive personal information' (Cal. Civ. Code § 1798.140(ae)) to "
            "include government IDs (e.g. SSN), precise geolocation, race/ethnicity/religion/"
            "union membership, contents of certain private communications, genetic and "
            "biometric data, health data, and sex life/sexual orientation. As of Jan. 1, "
            "2026, CPPA regulations also treat the personal information of consumers under "
            "16 as sensitive personal information regardless of category."
        ),
        "details": (
            "'Sensitive personal information' is its own defined category under CPRA, "
            "distinct from ordinary personal information. Consumers have the right to direct "
            "a business to limit use/disclosure of sensitive personal information to what is "
            "necessary to perform the requested goods/services (Civ. Code § 1798.121). "
            "Businesses must generally provide a clear 'Limit the Use of My Sensitive "
            "Personal Information' link where this right applies."
        ),
        "notes": (
            f"VERIFIED {VERIFICATION_DATE} against Cal. Civ. Code § 1798.140(ae) and § 1798.121 "
            "(leginfo.legislature.ca.gov), and the CPPA's finalized regulations effective Jan. 1, 2026 "
            "(cppa.ca.gov) regarding minors' data."
        ),
        "source_url": CA_CIV_CODE,
        "verified": True,
    },
    ("compliance-obligations-dpo-dpia-records", "LGPD"): {
        "summary": (
            "Controllers must generally designate an 'encarregado' (Art. 41) and publicly "
            "disclose their contact information — though ANPD Resolução CD/ANPD nº 2/2022 "
            "exempts small-scale processing agents from this if they maintain a contact "
            "channel with data subjects. The ANPD may separately determine, case by case, "
            "that a controller prepare a data protection impact report ('RIPD', Art. 38) — "
            "unlike GDPR's DPIA, this is not a self-triggered, general obligation."
        ),
        "details": (
            "Art. 41 requires controllers to designate an encarregado, whose duties (§2) "
            "include receiving complaints/communications from data subjects, receiving "
            "communications from the ANPD, and guiding staff/contractors on data protection "
            "practices; §3 lets the ANPD set complementary rules, including exemption "
            "hypotheses based on the entity's size/nature or processing volume. The ANPD "
            "exercised that authority in Resolução CD/ANPD nº 2/2022, exempting small-scale "
            "agents (e.g. micro/small businesses, startups) from designating an encarregado "
            "provided a data-subject contact channel exists — though voluntarily designating "
            "one still counts as a good-governance factor under Art. 52, §1, IX when the "
            "ANPD sets sanctions. Separately, Art. 38 lets (not requires) the ANPD determine "
            "that a controller prepare a RIPD for its processing operations, including "
            "sensitive data, observing trade/industrial secrets."
        ),
        "notes": (
            f"VERIFIED {VERIFICATION_DATE} against planalto.gov.br (Art. 38, Art. 41) and ANPD Resolução "
            "CD/ANPD nº 2/2022 (gov.br/anpd)."
        ),
        "source_url": ANPD_SMALL_BUSINESS,
        "verified": True,
    },
    ("compliance-obligations-dpo-dpia-records", "GDPR"): {
        "summary": (
            "Requires a Data Protection Officer where: processing is by a public authority "
            "(Art. 37(1)(a)); core activities require large-scale, regular and systematic "
            "monitoring (Art. 37(1)(b)); or core activities involve large-scale processing "
            "of special-category/criminal-record data (Art. 37(1)(c)). Separately requires "
            "Records of Processing Activities (Art. 30) and a DPIA before processing likely "
            "to result in high risk to individuals (Art. 35)."
        ),
        "details": (
            "Art. 37(1) sets three independent triggers for mandatory DPO designation — any "
            "one is sufficient. GDPR does not define a numeric 'large scale' threshold; EDPB "
            "guidance points to factors like the number of data subjects, volume/range of "
            "data, duration, and geographic extent. Art. 30 requires controllers (and, in "
            "parallel, processors) to maintain a record of processing activities, generally "
            "available to the supervisory authority on request; a limited exemption exists "
            "for organizations with fewer than 250 employees, unless their processing is "
            "regular, risky, or involves special-category/criminal-record data. Art. 35 "
            "requires a DPIA whenever processing — particularly using new technologies — is "
            "likely to result in a high risk to individuals' rights and freedoms, carried "
            "out by the controller before processing begins."
        ),
        "notes": f"VERIFIED {VERIFICATION_DATE} against eur-lex.europa.eu (Regulation (EU) 2016/679, Arts. 30, 35, 37(1)).",
        "source_url": EUR_LEX_GDPR,
        "verified": True,
    },
    ("compliance-obligations-dpo-dpia-records", "CCPA/CPRA"): {
        "summary": (
            "Does not require a formal 'DPO' role. CPPA regulations finalized in 2025 and "
            "effective January 1, 2026 require annual cybersecurity audits (phased in "
            "through 2030) and periodic risk assessments (phased in through 2027-2028) for "
            "businesses whose processing presents significant risk to consumer privacy or "
            "security."
        ),
        "details": (
            "CPRA directed the CPPA to adopt regulations on cybersecurity audits and risk "
            "assessments for higher-risk processing. Those regulations were adopted by the "
            "CPPA Board on July 24, 2025 and approved by the California Office of "
            "Administrative Law on September 22-23, 2025, taking effect January 1, 2026. "
            "Compliance deadlines are staggered by business size/risk: cybersecurity audit "
            "obligations phase in through 2030, and risk-assessment submissions are due on a "
            "rolling schedule (e.g. by Dec. 31, 2027 for assessments of processing already "
            "underway, and by April 1 of the following year for later ones). This is a "
            "notably more prescriptive accountability regime than the original 2020 CCPA."
        ),
        "notes": (
            f"VERIFIED {VERIFICATION_DATE} against cppa.ca.gov coverage of the finalized regulations "
            "(OAL-approved Sept. 22-23, 2025; effective Jan. 1, 2026). Compliance deadlines are set by "
            "regulation and could still be adjusted — recheck cppa.ca.gov before relying on a specific date."
        ),
        "source_url": CPPA_REGULATIONS,
        "verified": True,
    },
    ("enforcement-penalties", "LGPD"): {
        "summary": (
            "Enforced by the ANPD, which can apply (Art. 52): a warning, a simple or daily "
            "fine of up to 2% of the Brazilian revenue of the private entity/group/"
            "conglomerate in its last fiscal year (excluding taxes), capped at R$50,000,000 "
            "per infraction, publicity of the violation, and blocking/deletion of the data "
            "involved. A dedicated dosimetry regulation (ANPD Resolução CD/ANPD nº 4/2023) "
            "governs how fines are calculated."
        ),
        "details": (
            "Art. 52 lists the ANPD's sanction ladder for LGPD violations: warning with a "
            "deadline to correct; simple fine up to 2% of the private legal entity's, "
            "group's, or conglomerate's Brazilian revenue in its last fiscal year (excluding "
            "taxes), limited in total to R$50,000,000.00 per infraction; daily fine, subject "
            "to the same overall cap; publicity of the confirmed infraction; blocking of the "
            "personal data at issue until regularization; and deletion of that data. ANPD "
            "Resolução CD/ANPD nº 4/2023 (in force since Feb. 27, 2023, and applicable even "
            "to proceedings already underway) sets the criteria and methodology the ANPD "
            "must follow to calculate the base value of a fine."
        ),
        "notes": (
            f"VERIFIED {VERIFICATION_DATE} against planalto.gov.br (Art. 52) and ANPD Resolução CD/ANPD "
            "nº 4/2023 (gov.br/anpd). LGPD's general provisions took effect Sept. 18, 2020; the "
            "administrative-sanction provisions (Arts. 52-54) took effect separately, on Aug. 1, 2021, "
            "per Lei nº 14.010/2020."
        ),
        "source_url": ANPD_DOSIMETRY,
        "verified": True,
    },
    ("enforcement-penalties", "GDPR"): {
        "summary": (
            "Enforced by national Data Protection Authorities under Art. 83's two-tier "
            "fining structure: a lower tier up to €10 million or 2% of global annual "
            "turnover (whichever is higher), and a higher tier up to €20 million or 4% "
            "(whichever is higher), alongside non-monetary corrective powers such as "
            "processing bans."
        ),
        "details": (
            "Art. 83(4) sets the lower fining tier (up to €10,000,000, or 2% of the "
            "undertaking's total worldwide annual turnover of the preceding financial year, "
            "whichever is higher) for infringements such as failures relating to controller/"
            "processor obligations, certification bodies, or monitoring bodies. Art. 83(5)-"
            "(6) sets the higher tier (up to €20,000,000, or 4% of worldwide annual "
            "turnover, whichever is higher) for infringements of core principles such as the "
            "conditions for consent, data subject rights, or international transfer rules. "
            "DPAs also have non-monetary corrective powers under Art. 58, including issuing "
            "warnings/reprimands and ordering a temporary or definitive limitation, including "
            "a ban, on processing."
        ),
        "notes": f"VERIFIED {VERIFICATION_DATE} against eur-lex.europa.eu (Regulation (EU) 2016/679, Art. 83(4)-(6)).",
        "source_url": EUR_LEX_GDPR,
        "verified": True,
    },
    ("enforcement-penalties", "CCPA/CPRA"): {
        "summary": (
            "Enforced primarily by the California Privacy Protection Agency, with "
            "concurrent Attorney General authority. Administrative fines (Civ. Code "
            "§ 1798.155) are up to $2,663 per violation, or $7,988 per intentional "
            "violation or violation involving a consumer under 16 (2025 CPI-adjusted "
            "figures). CPRA removed the CCPA's mandatory 30-day cure period, giving the "
            "CPPA/AG discretion instead."
        ),
        "details": (
            "CPRA created the CPPA as a dedicated enforcement agency, which took over primary "
            "enforcement from the Attorney General effective July 1, 2023 (the AG retains "
            "some concurrent authority). Civ. Code § 1798.155(a) sets administrative fines of "
            "not more than $2,500 per violation, or $7,500 per intentional violation or a "
            "violation involving a consumer under 16 — both figures are CPI-adjusted by the "
            "CPPA every odd-numbered year, and as of Jan. 1, 2025 stand at $2,663 and $7,988 "
            "respectively. Unlike the original CCPA (which gave businesses a mandatory "
            "30-day window to cure a violation before penalties applied), CPRA left curing "
            "to the CPPA's/AG's discretion — considering factors like the violator's lack of "
            "intent and any voluntary remediation — rather than guaranteeing it."
        ),
        "notes": (
            f"VERIFIED {VERIFICATION_DATE} against Cal. Civ. Code §§ 1798.155 and 1798.199.95 "
            "(leginfo.legislature.ca.gov) and the CPPA's Dec. 17, 2024 CPI adjustment notice "
            "(cppa.ca.gov). These fine amounts are CPI-adjusted every odd-numbered year — the next "
            "adjustment takes effect Jan. 1, 2027, so recheck cppa.ca.gov before relying on the "
            "$2,663/$7,988 figures after that date."
        ),
        "source_url": CPPA_CPI_NOTICE,
        "verified": True,
    },
    ("private-right-of-action", "LGPD"): {
        "summary": (
            "No dedicated LGPD private-right-of-action provision. Instead, Art. 42 imposes "
            "civil liability on controllers/processors that cause patrimonial, moral, "
            "individual, or collective damage through a violation of the law — liability "
            "that Brazilian legal doctrine generally treats as not requiring proof of fault. "
            "Claims can be brought collectively, and courts may shift the burden of proof to "
            "the defendant in the data subject's favor."
        ),
        "details": (
            "Art. 42 obliges a controller or operator whose data-processing activity causes "
            "damage, in violation of data protection legislation, to repair it. Operators "
            "are jointly liable with controllers when they fail to comply with the law's "
            "obligations or act outside the controller's lawful instructions (in which case "
            "they are treated as a controller); controllers directly involved in the same "
            "damaging processing are also jointly liable — subject to the exclusions in Art. "
            "43. A judge may reverse the burden of proof in the data subject's favor where "
            "the claim is plausible, the subject lacks the means to produce evidence, or "
            "producing it would be excessively burdensome for them. Actions seeking "
            "collective redress under this article may be brought collectively, following "
            "Brazil's general collective-litigation legislation, and whoever repairs the "
            "damage has a right of recourse against other responsible parties in proportion "
            "to their share of responsibility."
        ),
        "notes": (
            f"VERIFIED {VERIFICATION_DATE} against planalto.gov.br (Art. 42, §§1-4, and Art. 43). This "
            "area continues to develop through ANPD guidance and case law — recheck for material "
            "developments before relying on this characterization in a real legal analysis."
        ),
        "source_url": PLANALTO_LGPD,
        "verified": True,
    },
    ("private-right-of-action", "GDPR"): {
        "summary": (
            "Data subjects have the right to an effective judicial remedy against a "
            "controller/processor (Art. 79) and to compensation for material or "
            "non-material damage suffered from an infringement (Art. 82). Art. 80 also "
            "allows representative actions by qualifying not-for-profit bodies."
        ),
        "details": (
            "Art. 79 gives every data subject the right to an effective judicial remedy "
            "where they consider their rights under the Regulation have been infringed as a "
            "result of processing, without prejudice to any available administrative or "
            "non-judicial remedy (e.g. lodging a complaint with a supervisory authority). "
            "Art. 82(1) entitles anyone who has suffered material or non-material damage as "
            "a result of an infringement to compensation from the controller or processor. "
            "Art. 80 lets a data subject mandate a qualifying not-for-profit body, "
            "organization, or association to lodge a complaint or exercise these rights on "
            "their behalf, and EU member states may permit such a body to act independently "
            "of a specific mandate."
        ),
        "notes": (
            f"VERIFIED {VERIFICATION_DATE} against eur-lex.europa.eu (Regulation (EU) 2016/679, Arts. 79, "
            "80, 82). CJEU case law interpreting the threshold for 'non-material damage' under Art. 82 "
            "continues to develop — recheck before relying on this in a real legal analysis."
        ),
        "source_url": EUR_LEX_GDPR,
        "verified": True,
    },
    ("private-right-of-action", "CCPA/CPRA"): {
        "summary": (
            "Provides a narrow private right of action (Civ. Code § 1798.150) limited to "
            "certain data breaches of unencrypted/unredacted personal information caused by "
            "a business's failure to implement reasonable security, with statutory damages "
            "of $107-$799 per consumer per incident (2025 CPI-adjusted figures) or actual "
            "damages, whichever is greater."
        ),
        "details": (
            "Unlike GDPR/LGPD, CCPA includes an explicit — but narrow — private right of "
            "action: it applies only to a business's unauthorized access, theft, or "
            "disclosure of nonencrypted, nonredacted personal information (or personal "
            "information rendered unusable through breach of encryption/redaction "
            "safeguards), resulting from the business's violation of its duty to implement "
            "and maintain reasonable security procedures. It does not cover most other CCPA "
            "violations (e.g. failing to honor a right-to-know or right-to-delete request), "
            "which remain enforceable only by the CPPA/Attorney General. Civ. Code "
            "§ 1798.150(a)(1)(A) allows recovery of not less than $100 and not greater than "
            "$750 per consumer per incident, or actual damages, whichever is greater — "
            "CPI-adjusted every odd-numbered year by the CPPA, standing at $107-$799 "
            "effective Jan. 1, 2025."
        ),
        "notes": (
            f"VERIFIED {VERIFICATION_DATE} against Cal. Civ. Code § 1798.150(a)(1)(A) (leginfo.legislature."
            "ca.gov) and the CPPA's Dec. 17, 2024 CPI adjustment notice (cppa.ca.gov). This statutory "
            "damages range is CPI-adjusted every odd-numbered year — the next adjustment takes effect "
            "Jan. 1, 2027, so recheck cppa.ca.gov before relying on the $107-$799 figures after that date."
        ),
        "source_url": CPPA_CPI_NOTICE,
        "verified": True,
    },
}

QUESTIONS = [
    {
        "flag": "process_eu_data",
        "question_text": "Does your business offer goods/services to, or monitor the behavior of, individuals located in the EU/EEA?",
        "help_text": "Core trigger for GDPR's extraterritorial scope (Art. 3(2)).",
        "order": 1,
    },
    {
        "flag": "process_br_data",
        "question_text": "Does your business process personal data of individuals located in Brazil, or collect data within Brazil?",
        "help_text": "Core trigger for LGPD's extraterritorial scope (Art. 3).",
        "order": 2,
    },
    {
        "flag": "does_business_in_ca",
        "question_text": "Does your business do business in California and collect personal information of California consumers?",
        "help_text": "Baseline condition for CCPA/CPRA — required in addition to at least one threshold below.",
        "order": 3,
    },
    {
        "flag": "ca_revenue_threshold",
        "question_text": "Does your business have annual gross revenue above the CCPA/CPRA revenue threshold?",
        "help_text": (
            "As of Jan. 1, 2025 this threshold is $26,625,000 (CPI-adjusted every odd-numbered "
            "year; verify at cppa.ca.gov if assessing this after Jan. 1, 2027)."
        ),
        "order": 4,
    },
    {
        "flag": "ca_data_volume_threshold",
        "question_text": "Does your business buy, sell, or share the personal information of a large number of California consumers or households annually?",
        "help_text": "This threshold is 100,000+ consumers or households annually (Cal. Civ. Code § 1798.140(d)(1)(B)).",
        "order": 5,
    },
    {
        "flag": "ca_revenue_from_sale_threshold",
        "question_text": "Does your business derive a significant share of its annual revenue from selling or sharing California consumers' personal information?",
        "help_text": (
            "This threshold is 50% or more of annual revenue, including revenue from cross-context "
            "behavioral advertising (Cal. Civ. Code § 1798.140(d)(1)(C))."
        ),
        "order": 6,
    },
    {
        "flag": "processes_sensitive_data",
        "question_text": "Does your business process sensitive/special-category data (e.g. health, biometric, precise geolocation, or children's data)?",
        "help_text": (
            "Answering yes does not by itself trigger any framework — it flags that the "
            "Sensitive Data Categories comparison is especially relevant to your business."
        ),
        "order": 7,
    },
]

# law_code -> list of (question_flag, required_for_all)
SCENARIO_RULES = {
    "GDPR": [("process_eu_data", False)],
    "LGPD": [("process_br_data", False)],
    "CCPA/CPRA": [
        ("does_business_in_ca", True),
        ("ca_revenue_threshold", False),
        ("ca_data_volume_threshold", False),
        ("ca_revenue_from_sale_threshold", False),
    ],
}


class Command(BaseCommand):
    help = (
        "Seeds Laws, Categories, ComparisonEntries, and the compliance-summary questionnaire."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        laws_by_code = {}
        for data in LAWS:
            law, created = Law.objects.update_or_create(code=data["code"], defaults=data)
            laws_by_code[law.code] = law
            self._log(created, "Law", law.code)

        categories_by_slug = {}
        for data in CATEGORIES:
            slug = data["slug"]
            category, created = Category.objects.update_or_create(slug=slug, defaults=data)
            categories_by_slug[slug] = category
            self._log(created, "Category", category.name)

        for (category_slug, law_code), content in ENTRIES.items():
            _entry, created = ComparisonEntry.objects.update_or_create(
                category=categories_by_slug[category_slug],
                law=laws_by_code[law_code],
                defaults={
                    "summary": content["summary"],
                    "details": content["details"],
                    "verification_notes": content["notes"],
                    "source_url": content.get("source_url", ""),
                    "is_verified": content.get("verified", False),
                },
            )
            self._log(created, "ComparisonEntry", f"{category_slug} / {law_code}")

        questions_by_flag = {}
        for data in QUESTIONS:
            question, created = ScenarioQuestion.objects.update_or_create(
                flag=data["flag"], defaults=data
            )
            questions_by_flag[question.flag] = question
            self._log(created, "ScenarioQuestion", question.flag)

        for law_code, rules in SCENARIO_RULES.items():
            for flag, required_for_all in rules:
                _rule, created = ScenarioRule.objects.update_or_create(
                    law=laws_by_code[law_code],
                    question=questions_by_flag[flag],
                    defaults={"required_for_all": required_for_all},
                )
                self._log(created, "ScenarioRule", f"{law_code} <- {flag}")

        unverified = ComparisonEntry.objects.filter(is_verified=False).count()
        self.stdout.write(self.style.SUCCESS("Seed data loaded successfully."))
        if unverified:
            self.stdout.write(
                self.style.WARNING(
                    f"{unverified} ComparisonEntry row(s) are still is_verified=False — "
                    "check their verification_notes for what to confirm before publishing."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"All ComparisonEntry rows are marked is_verified=True as of {VERIFICATION_DATE}. "
                    "A few CCPA/CPRA figures are CPI-adjusted every odd-numbered year — see each "
                    "entry's verification_notes for the next recheck date."
                )
            )

    def _log(self, created, kind, label):
        action = "Created" if created else "Updated"
        self.stdout.write(f"  {action} {kind}: {label}")
