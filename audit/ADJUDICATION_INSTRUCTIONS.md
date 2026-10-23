# Drug-class adjudication — one-page operating instructions

**Study:** Sex-differential safety atlas of cardiovascular drugs in FAERS — drug-dictionary quality audit
**Task:** assign each of 211 (drugname, prod_ai) name pairs to its applicable cardiovascular drug class(es)
**File:** `audit_adjudication_blind.csv` (211 rows, existing labels hidden; opens directly in Excel)

## Independence requirements

- Both raters complete the file **independently, without discussion**, and without consulting any third-party "answers".
- The sheet contains only drug names and active ingredients; this is intentional — please rely solely on your professional judgement.

## General classification rules (applied pair by pair)

1. **Active ingredient governs:** map brand names to their generic ingredient(s) first, then classify by ingredient; indication is irrelevant.
   - Example: sildenafil is PDE5 regardless of indication; topical minoxidil is MINOXIDIL.
2. **Combinations contribute every listed ingredient class:** for a combination containing multiple listed ingredients, assign one class per ingredient, joined with `|`.
   - Example: valsartan/hydrochlorothiazide → `ARB|THIAZIDE`. Ingredients not in the table below contribute no class.
3. **No listed class applies** → enter `NONE`.
4. **Name unidentifiable / insufficient information** → enter `UNRESOLVABLE` (reported separately; counts as an error for neither side).
5. If uncertain but leaning towards an answer: enter the class and briefly note the doubt in `rater_note` (≤15 words).

## Class code table (39 + 3 excluded classes)

| Code | Meaning | Code | Meaning |
|---|---|---|---|
| AA_IC | class Ic antiarrhythmics (flecainide/propafenone) | GPIIBIIIA | GPIIb/IIIa inhibitors |
| AA_III | class III (amiodarone/sotalol/dronedarone/dofetilide) | IVABRADINE | ivabradine |
| ACEI | ACE inhibitors | LOOP | loop diuretics |
| ALPHA_HTN | alpha-1 blockers for hypertension (doxazosin/terazosin/prazosin) | METFORMIN | metformin |
| ALPHA_BPH | urological alpha-1 blockers (tamsulosin/alfuzosin/silodosin) | MRA | mineralocorticoid receptor antagonists |
| ARB | angiotensin receptor blockers | OMEGA3 | omega-3 acid ethyl esters/icosapent |
| ARNI | sacubitril/valsartan | P2Y12 | P2Y12 inhibitors (incl. cangrelor) |
| ASPIRIN | aspirin | PAH | pulmonary-arterial-hypertension agents (endothelin antagonists/prostacyclins/riociguat) |
| BEMPEDOIC | bempedoic acid | PCSK9I | PCSK9 inhibitors (incl. inclisiran) |
| BETA | beta-blockers | PDE5 | PDE5 inhibitors |
| CCB_DHP | dihydropyridine calcium-channel blockers | RANOLAZINE | ranolazine |
| CCB_NON | non-dihydropyridines (verapamil/diltiazem) | RENIN_INH | renin inhibitor (aliskiren) |
| CENTRAL | central antihypertensives (clonidine/methyldopa/moxonidine) | SGLT2I | SGLT2 inhibitors |
| CILOSTAZOL | cilostazol | STATIN | statins |
| DIGOXIN | digoxin | THIAZIDE | thiazide/thiazide-like diuretics |
| DOAC | direct oral anticoagulants (dabigatran/rivaroxaban/apixaban/edoxaban) | VASODIL | nitrates/hydralazine |
| DPP4I | DPP-4 inhibitors | VERICIGUAT | vericiguat |
| EZETIMIBE | ezetimibe | VKA | vitamin K antagonists |
| FIBRATE | fibrates | MINOXIDIL | minoxidil (excluded class) |
| GLP1RA | GLP-1 receptor agonists | | |

`NONE` = none of the classes above; `UNRESOLVABLE` = name cannot be adjudicated.

## How to fill in

- Fill in only two columns: `rater_class` (required; codes from the table above, multiple classes joined with `|`) and `rater_note` (optional).
- **Do not modify** the sample_id / drugname_u / prod_ai_u columns; do not add or delete rows; save as CSV (UTF-8).
- Expected workload ~1–1.5 hours; when done, rename the file to `..._rater1.csv` / `..._rater2.csv` and return it.

## After return (no action needed from raters)

The two independent adjudications are merged pair by pair → agreements become the gold standard directly → disagreements go to third-party arbitration (Liu team) → gold_class and error-mode codes are generated for computing dictionary sensitivity/specificity (Wilson CI), McNemar's test, and Cohen's κ.

*These instructions and the adjudication package were generated per §4 of the frozen protocol "LLM-as-auditor audit appendix v1.1".*
