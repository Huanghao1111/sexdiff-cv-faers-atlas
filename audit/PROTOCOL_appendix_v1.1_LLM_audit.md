# Protocol Appendix v1.1 — LLM-as-auditor module for dictionary validation

**Frozen:** 2026-10-16
**Status:** Revision and replacement of PROTOCOL_v1 §4.2 (the LLM role changed from "normalization engine" to "independent auditor"; §4.2 task B, indication standardization, remains deferred to phase II)
**Rationale:** Rule dictionary v2 is the production classifier and all atlas results were already frozen; the LLM module was repurposed to provide a quantified, external, blinded validation of dictionary accuracy, forming a three-layer architecture of "deterministic pipeline + independent AI audit + human gold standard", consistent with the target journal's digital-tools scope.

---

## 1. Objectives

- **Primary question:** classification accuracy of the frozen drug-class dictionary v2 (39 classes, including 3 matched-but-excluded classes) against a human gold standard (per-class sensitivity, specificity, positive predictive value).
- **Secondary questions:** accuracy of the LLM as an independent classifier; error-mode taxonomy of dictionary–LLM disagreements; report-weighted impact of dictionary error on CV-universe report volume.
- **Explicit non-goals:** the main analysis pipeline is not re-run; the audit quantifies dictionary precision only, and no atlas number (106 candidates, 13 validated signals, all figures and tables) is revised on the basis of audit results; handling of any substantive dictionary defect found is pre-specified in §8 (Deviations and responses).

## 2. Sampling (executed; frozen)

- Frame: `drug_name_freq` table — 152,380 unique (drugname_u × prod_ai_u) pairs (all FAERS primary-suspect drug rows, 2004Q1–2026Q2), of which 19,553 dictionary-hit and 132,827 unmatched pairs.
- Stratification (script `src/audit_sample.py`, random seed **20261016**, reproducible):
  - **Stratum A, 500 pairs:** dictionary-hit pairs drawn probability-proportional-to-report-count (PPS) — covers the exposure mass of the CV universe;
  - **Stratum B, 200 pairs:** uniform sample of the remaining hit pairs — covers the long tail, where dictionary errors often hide;
  - **Stratum C, 300 pairs:** unmatched pairs drawn PPS — false-negative screen for names currently excluded from the CV universe that may in fact be cardiovascular drugs.
- Products: `src/audit_sample_1000.csv` (blinded sample, unlabeled) and `src/audit_sample_1000_KEY.csv` (sealed key with dictionary labels). The sample covers 9,225,001 reports.

## 3. LLM classification procedure

- **Blinding statement and limitation:** at classification time the LLM sees only the name-pair strings and the class definitions (frozen prompt, §3.1) — never the per-pair dictionary labels; sample order was shuffled, and stratum information, though retained, did not enter classification. Limitation disclosed verbatim: because the LLM encountered class-definition text during development, its classifications do not constitute taxonomically independent discovery — the audit's validity is anchored in the human gold standard, and the LLM serves as an independent re-classifier and disagreement screener (analogous to AI-assisted first-pass screening in systematic reviews).
- **Execution metadata** (filled at execution and released with the supplement): model name/version, full prompt text, temperature, call dates, batch count.
- **Output format:** `src/audit_llm_labels.csv` with fields sample_id, llm_classes (multiple classes joined by |, NONE for non-cardiovascular), confidence (high/medium/low), rationale (≤30 words).
- The label file is hashed and recorded before the sealed key may be opened.

### 3.1 Frozen prompt (used verbatim during classification)

> You are auditing drug-name classification for a cardiovascular pharmacovigilance study. For each FAERS (drugname, prod_ai) pair, assign EVERY applicable class from the fixed list below, based on the active ingredient(s); map brand names and combination products to their ingredients. If no listed class applies, output NONE. Fixed class list: AA_IC (class Ic antiarrhythmics: flecainide, propafenone); AA_III (class III antiarrhythmics: amiodarone, sotalol, dronedarone, dofetilide); ACEI; ALPHA_HTN (centrally/peripherally used alpha-1 blockers for hypertension: doxazosin, terazosin, prazosin); ALPHA_BPH (urological alpha-1 blockers: tamsulosin, alfuzosin, silodosin); ARB; ARNI (sacubitril/valsartan); ASPIRIN; BEMPEDOIC (bempedoic acid); BETA (beta-blockers); CCB_DHP (dihydropyridine calcium-channel blockers); CCB_NON (non-dihydropyridines: verapamil, diltiazem); CENTRAL (central antihypertensives: clonidine, methyldopa, moxonidine); CILOSTAZOL; DIGOXIN; DOAC (dabigatran, rivaroxaban, apixaban, edoxaban); DPP4I; EZETIMIBE; FIBRATE; GLP1RA; GPIIBIIIA (abciximab, eptifibatide, tirofiban); IVABRADINE; LOOP (loop diuretics); METFORMIN; MINOXIDIL (topical/oral minoxidil); MRA (mineralocorticoid receptor antagonists: spironolactone, eplerenone, finerenone); OMEGA3 (omega-3 acid ethyl esters/icosapent); P2Y12 (clopidogrel, prasugrel, ticagrelor, cangrelor); PAH (pulmonary-arterial-hypertension agents: endothelin antagonists, prostacyclins, riociguat); PCSK9I (alirocumab, evolocumab, inclisiran); PDE5 (sildenafil, tadalafil, vardenafil, avanafil); RANOLAZINE; RENIN_INH (aliskiren); SGLT2I; STATIN; THIAZIDE (thiazide/thiazide-like diuretics); VASODIL (nitrates, hydralazine); VERICIGUAT; VKA (warfarin, acenocoumarol, phenprocoumon). Answer with: sample_id; assigned classes; confidence (high/medium/low); one-line rationale.

## 4. Human gold-standard adjudication

- **Adjudicators:** two independent adjudicators (cardiology / clinical pharmacology background), mutually blinded; disagreements go to third-party arbitration (Liu team). Adjudication basis: active ingredient → ATC assignment; brand names and combinations mapped to ingredients.
- **Adjudication set:** (i) all LLM–dictionary disagreement pairs; (ii) a random 20% of concordant pairs per stratum (to estimate the miss rate within concordant pairs). Expected volume 300–500 pairs.
- **Adjudication template** (`src/audit_adjudication_template.csv`, auto-filled when the package is generated): sample_id, drugname_u, prod_ai_u, dict_classes, llm_classes, llm_rationale, rater1_class, rater2_class, arbitration, gold_class, error_mode (see §5).
- Adjudication rules (applied pair-by-pair by both raters): active ingredient governs; combinations are assigned to every ingredient class; unidentifiable names are marked UNRESOLVABLE and recorded as jointly undecidable for dictionary and LLM (reported separately, not counted as error).

## 5. Statistical analysis (pre-specified metrics)

- Dictionary vs gold standard: per-class sensitivity, specificity, PPV (Wilson 95% CI); report-weighted extrapolation of stratum-C hit rate → estimated number of reports currently missed by the CV universe (and the direction of potential impact on candidate-signal cell counts).
- LLM vs gold standard: same metrics; LLM vs dictionary paired comparison by McNemar's test; agreement by Cohen's κ (per-class and overall).
- Error-mode taxonomy (frozen values): `missed_ingredient`, `missed_brand`, `spelling_variant`, `combination_partial`, `false_positive`, `scope_dispute` (class-boundary disputes, e.g., the dual PAH/ED indication of PDE5 inhibitors), `unresolvable`.

## 6. Integrity sequence (order may not be changed)

1. Sampling (done; seed frozen) → 2. LLM classification → 3. `audit_llm_labels.csv` locked and hashed → 4. Sealed key opened → 5. Adjudication package generated → 6. Dual adjudication and arbitration → 7. Analysis locked. Any rework of any step must be recorded, with reasons, in the audit log (appended to `src/audit.log`).

## 7. Deliverables

- **Figure 4** (the protocol's originally planned LLM-validation figure, formally reinstated): per-class sensitivity/specificity forest or heat map for dictionary vs LLM vs gold standard, plus an error-mode composition bar.
- **Methods:** new subsection "LLM-assisted audit of the drug classifier"; **Results:** one new paragraph (dictionary accuracy + impact estimate); **Supplement:** new item S11 (now Supplementary Appendix 6) with the complete audit data (sample, LLM labels, gold standard, pair-level adjudication).

## 8. Pre-specified deviations and responses

- If dictionary sensitivity for any class is <0.95 and affects the direction of a validated signal's cell count: report a robustness note for that signal (re-estimated with gold-standard-corrected counts); the full grid is not revised.
- If stratum C indicates systematic misses (estimated missed reports >1% of the CV universe): escalate to a major deviation and discuss with the authors whether to expand the dictionary and re-run the full chain; by default, no revision — disclosed as a limitation.
- UNRESOLVABLE proportion >5%: reported and discussed as an inherent limit of name resolution.
