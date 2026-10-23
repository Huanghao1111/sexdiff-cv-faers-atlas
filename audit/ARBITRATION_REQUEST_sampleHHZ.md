# Arbitration Request (1 item) — Cardiovascular Drug Dictionary Audit

**To**: Liu Yong team (third-party arbitration)
**Date**: 2026-10-17
**Background (one sentence)**: In the dictionary quality audit of our FAERS drug sex-difference study, two independent adjudicators reached agreement on 210/211 drug-name pairs; only the following 1 pair remains for third-party arbitration.

## Item Under Adjudication

| Field | Content |
|---|---|
| Drug name (verbatim reported name) | **EXFORGE D** |
| prod_ai (ingredient field) | (empty; can only be judged from the drug name) |
| Current dictionary class | `ARB|CCB_DHP` (dual: valsartan + amlodipine) |
| LLM audit label | `ARB|CCB_DHP|THIAZIDE` (triple: + hydrochlorothiazide) |
| Rater 1 (hhz) | `ARB|CCB_DHP|THIAZIDE`, rationale: "amlodipine + valsartan + HCTZ" |
| Rater 2 (CSQ) | `ARB|CCB_DHP`, rationale: "composition of 'D' uncertain" |

## Arbitration Question (one sentence)

**Does the brand name "EXFORGE D" correspond to a dual combination (amlodipine/valsartan) or a triple combination (amlodipine/valsartan/hydrochlorothiazide)?**

Reference clue: the triple combination is marketed in the US/EU as **Exforge HCT**; the naming "Exforge D" appears in some Latin American markets — please verify whether this naming contains hydrochlorothiazide.

## Please Reply (choose one)

- **Accept dual** → gold_class = `ARB|CCB_DHP`
- **Accept triple** → gold_class = `ARB|CCB_DHP|THIAZIDE`

Reply by filling in the `arbitration` / `gold_class` columns of `audit_arbitration_list.csv`.

*Per the frozen protocol "LLM-as-auditor audit appendix v1.1" §4: a disagreement becomes gold standard after third-party arbitration.*
