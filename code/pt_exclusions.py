"""pt_exclusions.py — non-informative MedDRA PTs excluded from signal scanning.

In FAERS, a large share of "events" are administrative or product-issue
labels rather than clinical adverse reactions (e.g. "Off label use",
"Product use issue", "Wrong patient received medication"). These carry no
clinical meaning, are strongly sex/reporting-pattern dependent, and dominate
disproportionality rankings if left in. Standard practice in pharmacovigilance
signal detection is to remove them before scanning.

This module freezes the exclusion rule (regex on the UPPERCASED PT).
"""
import re

PATTERNS = [
    r"^PRODUCT ",                      # product-issue family
    r"OFF LABEL",
    r"UNAPPROVED INDICATION",
    r"^DRUG INEFFECTIVE",
    r"^MEDICATION ERROR",
    r"^DRUG ADMINISTRATION ERROR",
    r"^WRONG (PATIENT|DRUG|TECHNIQUE|DOSE|ROUTE)",
    r"^INTENTIONAL (PRODUCT|DRUG|OVERDOSE|MISUSE)",
    r"^TREATMENT NONCOMPLIANCE",
    r"^NONCOMPLIANCE",
    r"^THERAPY (INTERRUPTED|CESSATION|DISCONTINUED)",
    r"^COUNTERFEIT",
    r"^EXPIRED PRODUCT",
    r"^INCORRECT (DOSE|ROUTE|DRUG|TECHNIQUE)",
    r"^ACCIDENTAL EXPOSURE",
    r"^OCCUPATIONAL EXPOSURE",
    r"^NO ADVERSE (DRUG )?(EFFECT|EVENT)",
    r"^POOR QUALITY PRODUCT",
    r"^CONTRAINDICATED PRODUCT",
    r"^ADVERSE DRUG REACTION$",        # non-specific administrative label
    r"^DISEASE RECURRENCE",
    r"^THERAPEUTIC (RESPONSE|EFFICACY|DRUG)",
    r"^DRUG (LEVEL|CONCENTRATION) (INCREASED|DECREASED|ABNORMAL)$",
    r"^PRODUCT USED FOR",
    r"^TREATMENT FAILURE",
    r"^LACK OF (EFFICACY|DRUG EFFECT)",
    r"^DRUG ABUSE",                    # misuse, not a clinical AE
    r"^DRUG DEPENDENCE",
    r"^SUBSTANCE ABUSE",
    r"^PRESCRIBED OVERDOSE",
    r"^OVERDOSE$",
    # --- round 2: administrative / misuse labels seen dominating the ranking
    r"^SUSPECTED COUNTERFEIT",
    r"^PRESCRIPTION DRUG USED WITHOUT",
    r"^DRUG EFFECT (INCOMPLETE|DELAYED|LESS THAN)",
    r"^UNDERDOSE",
    r"^UNDERDOSE$",
    r"^MEDICATION (DOSE|SCHEDULE)",
    r"^INAPPROPRIATE SCHEDULE",
    r"^DEVICE (USE ISSUE|LEAKAGE|DELIVERY|ISSUE)",
    r"^DRUG DELIVERY SYSTEM",
    r"^PRODUCT DOSE",
    # --- round 3 (frozen 2026-10-15, takeover review): pregnancy/partner
    # exposure-circumstance labels. Not adverse events, and in a
    # sex-differential analysis they are sex-tautological noise (a "maternal
    # exposure" report can only be female). Clinical pregnancy outcomes
    # (FOETAL DEATH, FOETAL MALFORMATION, PREGNANCY etc.) are NOT excluded.
    r"EXPOSURE (DURING|BEFORE) (PREGNANCY|BREAST ?FEEDING|DELIVERY)",
    r"EXPOSURE VIA PARTNER",
    r"^FOETAL EXPOSURE",
    r"^PREGNANCY OF PARTNER$",
    r"^MISCARRIAGE OF PARTNER$",
]

# PTs that in FAERS usually code the underlying indication / co-morbidity
# rather than a drug-attributable event. They are NOT excluded (they can be
# real signals, e.g. statin-associated diabetes) but are flagged so they are
# reported separately and never presented alongside clinical adverse events.
INDICATION_CODED = {
    "TYPE 2 DIABETES MELLITUS", "TYPE 1 DIABETES MELLITUS",
    "DIABETES MELLITUS", "DIABETIC NEUROPATHY", "HYPERGLYCAEMIA",
    "HYPERGLYCEMIA", "BLOOD GLUCOSE INCREASED", "HYPERTENSION",
    "HYPERLIPIDAEMIA", "HYPERLIPIDEMIA", "DYSLIPIDAEMIA",
    "HYPERCHOLESTEROLAEMIA", "BLOOD CHOLESTEROL INCREASED",
    "ATRIAL FIBRILLATION", "CARDIAC FAILURE", "HEART FAILURE",
    "CORONARY ARTERY DISEASE", "MYOCARDIAL INFARCTION", "ANGINA PECTORIS",
    # --- round 3 (frozen 2026-10-15, takeover review): chronic-disease /
    # comorbidity / procedure coding. Verified composition artefacts:
    # SLE shows opposite sex-shift directions across PAH (4.09 F) and
    # VASODIL (0.25 M) — the signature of comparator-composition, not drug
    # effect; PAH x BREAST CANCER / melanoma documented in the Stage-5
    # notes. Procedures are not adverse events by construction.
    "SYSTEMIC LUPUS ERYTHEMATOSUS", "BREAST CANCER", "BREAST CANCER FEMALE",
    "MALIGNANT MELANOMA", "BRONCHITIS", "SLEEP APNOEA SYNDROME",
    "DYSPNOEA EXERTIONAL", "ANGINA UNSTABLE",
    "RADIOTHERAPY", "CATHETERISATION CARDIAC",
}

_RX = [re.compile(p) for p in PATTERNS]


def is_noninformative(pt):
    """True if the PT is an administrative / product-issue label."""
    s = (pt or "").strip().upper()
    return any(rx.search(s) for rx in _RX)


def is_indication_coded(pt):
    """True if the PT usually codes the underlying disease, not an AE."""
    return (pt or "").strip().upper() in INDICATION_CODED


if __name__ == "__main__":
    for t in ["Off label use", "Product use issue", "Myalgia",
              "Wrong patient received medication", "Torsade de pointes",
              "Adverse drug reaction", "Rhabdomyolysis", "Drug ineffective"]:
        print(f"{t:<40} -> {'EXCLUDE' if is_noninformative(t) else 'keep'}")
