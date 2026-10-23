# Sex-differential safety signals across cardiovascular pharmacotherapy

Analysis code, frozen classification rules, and the complete dictionary-audit package for an active-comparator disproportionality atlas of sex-differential harm across 36 cardiovascular drug classes, built from 90 quarterly FAERS releases (2004Q1–2026Q2; 2,190,818 sex-known cardiovascular primary-suspect reports).

This repository accompanies the manuscript under submission to *European Heart Journal – Cardiovascular Pharmacotherapy*. It contains the analysis code, the frozen classification rules, the complete dictionary-audit package, and the machine-readable result files reported in the manuscript (`data/`). Every reported result can additionally be regenerated from the publicly available FAERS quarterly data files with the code and frozen rule sets in this repository.

## Repository layout

```
code/         analysis pipeline (flat; scripts import each other from this directory)
dictionary/   resolved drug-name → class mapping artifact (name_class.csv)
audit/        complete dictionary-validation audit package (see inventory below)
data/         machine-readable result files: full_test_grid.csv (28,949-row class × PT grid),
              fig2_domain_grid.csv (708-cell domain grid), stage6_adjusted.csv (106 candidates +
              2 positive controls), stage7_layers.csv (sensitivity layers), stage8_validation.csv
              (final adjudication), stage7_within_class.csv (within-class analyses),
              class_coverage.csv (per-class dictionary coverage)
```

The frozen classification rules live in code form: `code/drug_classes.py` (drug-class dictionary, v2, frozen) and `code/pt_exclusions.py` (Preferred Term exclusion rules). `dictionary/name_class.csv` is the resolved name-to-class mapping table produced from them.

## Pipeline overview

Run order (all scripts assume the FAERS ASCII quarterly extracts and produce a local `faers.db`):

1. `faers_reader.py` — parse 90 quarterly ASCII releases across the three historical FAERS/AERS format generations; apply FDA deletion lists at both primaryid and caseid level; collapse duplicate report versions per FDA guidance.
2. `build_demo_db.py`, `build_drug_db.py`, `build_reac_db.py`, `build_outc_db.py` — build the relational SQLite tables.
3. `drug_classes.py` + `classify_drugs.py` — assign primary-suspect drugs to the 36 frozen cardiovascular classes; `check_unmatched.py` audits unmatched names; `dictionary/name_class.csv` is the frozen resolved mapping.
4. `main_analysis.py` — sex-stratified 2×2 disproportionality (ROR) for every class × MedDRA Preferred Term pair against the active comparator of all other cardiovascular drugs; female-to-male ROR ratio with Benjamini–Hochberg FDR control.
5. `stage6_regression.py` — case-centred logistic adjustment (age, report year, reporter type, seriousness).
6. `stage7_sensitivity.py` — pre-specified layers (physician-reported, serious-only, era-stratified).
7. `verify_candidates.py`, `verify_stage5.py` — candidate curation and label verification workflow.
8. `qc_top_signals.py`, `audit_c.py` — independent recomputation of benchmark signals directly from `faers.db`.
9. `build_figure_data.py`, `make_figures.py`, `make_figure4.py`, `make_top_table.py` — figures and tables.

## Dictionary-audit package (`audit/`)

The drug-class dictionary was validated by a pre-specified, hash-locked large-language-model second reader benchmarked against a dual-blind human gold standard (n = 211 pairs; dictionary pair accuracy 95.3% [95% CI 91.5–97.4]; LLM 98.1% [95.2–99.3]; exact McNemar p = 0.180; per-class κ macro 0.991). The package contains:

- `PROTOCOL_appendix_v1.1_LLM_audit.md` — audit protocol, frozen prompt, and hash-lock record
- `ADJUDICATION_INSTRUCTIONS.md` — blinded adjudication instructions for human raters
- `audit_sample_1000.csv`, `audit_sample_1000_KEY.csv` — the audit sample and its key
- `audit_llm_labels.csv` — hash-locked LLM second-reader labels
- `audit_gold_standard.csv` — dual-blind human gold standard (n = 211)
- `audit_adjudication_package.csv`, `audit_adjudication_blind.csv` — adjudication materials
- `audit_adjudication_raterhhz.csv`, `audit_adjudication_raterCSQ.csv` — the two independent blinded rater files (canonical versions)
- `audit_arbitration_list.csv`, `ARBITRATION_REQUEST_sampleHHZ.md`, `ARBITRATION_REPLY_sampleCSQ.md` — arbitration record
- `audit_metrics.md` — computed metrics
- `audit.log` — timestamped audit log
- `SHA256SUMS.txt` — SHA-256 manifest of all deposited files
- `class_audit_report.txt`, `class_audit_topnames.csv` — class-name audit summaries
- supporting code: `code/audit_sample.py`, `code/audit_classes.py`, `code/compute_audit_metrics.py`, `code/assemble_s11.py`

## Data availability

FAERS quarterly data files are publicly available from the US FDA: <https://fis.fda.gov/extensions/FPD-QDE-FAERS/FPD-QDE-FAERS.html>. No new data were generated for this study.

## Status

Public since 23 October 2026, accompanying the manuscript submitted to *European Heart Journal – Cardiovascular Pharmacotherapy* (EHJ-CVP-S-26-00773). License to be added.
