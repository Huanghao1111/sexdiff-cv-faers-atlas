# Third-Party Arbitration Reply · sample 492 (EXFORGE D)

**To**: Dictionary audit working group (reply to the 2026-10-17 arbitration request)
**Executed by**: Liu Yong team
**Date**: 2026-10-17
**Basis**: Frozen protocol "LLM-as-auditor audit appendix v1.1" §4 (a disagreement becomes gold standard after third-party arbitration)

---

## Ruling

**`gold_class = ARB|CCB_DHP|THIAZIDE`** (accept triple).

I.e., this drug name should be classified under each of the three component classes; "D" should be resolved as hydrochlorothiazide. Rater 1 (hhz)'s opinion is upheld; rater 2 (CSQ)'s reservation ("composition of 'D' uncertain") is not upheld.

## Supporting Evidence (graded)

**1. Manufacturer primary document (decisive)**
Novartis Argentina official product label `ExforgeD.pdf` (https://www.novartis.com/ar-es/sites/novartis_ar/files/ExforgeD.pdf):

- Title line, verbatim: **"EXFORGE® D AMLODIPINA / VALSARTAN / HIDROCLOROTIAZIDA"**
- Content statement, verbatim: **"Cada comprimido recubierto de Exforge® D 10 mg / 320 mg / 25 mg contiene: Amlodipina (como besilato) 10 mg; Valsartan 320 mg; Hidroclorotiazida 25 mg"**
- Pharmacodynamics, verbatim: **"Exforge® D es una asociación de tres antihipertensivos ... amlodipina pertenece a la clase de los antagonistas del calcio, valsartan a la de los antagonistas de la angiotensina II e hidroclorotiazida a la de los diuréticos tiazídicos"**
- Label self-reported ATC: **C09DX01** (ARB/CCB/diuretic triple)

**2. ATC code corroboration**
The same label self-reports C09DX01, the "ARB + dihydropyridine CCB + thiazide diuretic" triple code, whereas dual Exforge (amlodipine/valsartan) is C09DB01. The label itself reports the triple code, not the dual code.

**3. Secondary drug dictionaries**
ndrugs explicitly records the `Exforge D` ingredient match as "Amlodipine/hydrochlorothiazide/valsartan (Chile)", with strengths identical to the Exforge HCT series (5/160/12.5, 5/160/25, 10/160/12.5, 10/160/25, 10/320/25); Pillintrip likewise lists it as a Triple Fixed-Dose Combination.

**4. Reverse verification**
A targeted search was conducted for any market in which `Exforge D` denotes the dual combination: no manufacturer or registration document supporting that usage was found. "D" stands for **Diurético (diuretic)**, the Latin American market naming of the same triple FDC marketed in the US/EU as `Exforge HCT`.

## Impact on Upstream/Downstream

| Party | Judgment | Explanation |
|---|---|---|
| Dictionary | ✗ wrong, error pattern `combination_partial` | The EXFORGE brand was received, but only the ARB + CCB_DHP components were assigned, missing the thiazide; same pattern as the already-listed DIOVAN TRIPLE |
| LLM | ✓ correct | Triple label consistent with the manufacturer label |

---

*The ruling has been back-filled into `audit_arbitration_list.csv` (columns `arbitration` / `gold_class`), and `compute_audit_metrics.py` was re-run to lock all 211 gold-standard pairs and the final metrics.*
