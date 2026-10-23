# LLM-as-auditor Audit Results (Appendix v1.1 §5, after gold-standard adjudication)

Generated: 2026-10-17T23:34:49 (v3, arbitration for sample 492 returned by the adjudication panel; all 211 gold-standard pairs locked)

## Adjudication Overview
- Adjudication package: 211 pairs (14 full-set disagreements + 197 agreement pairs sampled at 20%); raters hhz / CSQ, independent and blinded
- Inter-rater agreement: 210/211 = 99.5% (set level)
- Panel arbitration: 1 pair ['492'] (see ARBITRATION_REPLY_sampleCSQ.md)
- Still unresolved: 0 pairs — none
- UNRESOLVABLE: 0 pairs; consensus misses (both sides wrong within agreement pairs): 0 pairs

## Pair-Level Exact Match (n=211, locked pairs)
| Party | Correct | Accuracy [Wilson 95% CI] |
|---|---|---|
| Dictionary | 201/211 | 0.953 [0.915, 0.974] |
| LLM | 207/211 | 0.981 [0.952, 0.993] |

McNemar: b=4 (dictionary correct / LLM wrong), c=10 (LLM correct / dictionary wrong), exact two-sided p=0.180 — no statistically significant difference in overall accuracy; error patterns are complementary.

## Arbitration Outcome (adjudication panel HHZ/CSQ, based on the publicly verifiable manufacturer label)
**sample 492 (EXFORGE D) → accept triple `ARB|CCB_DHP|THIAZIDE`**, based on the Novartis Argentina official product label (title "EXFORGE® D AMLODIPINA / VALSARTAN / HIDROCLOROTIAZIDA"; each tablet contains Amlodipina 10 mg, Valsartan 320 mg, Hidroclorotiazida 25 mg; self-reported ATC C09DX01, the triple code), with attempted falsification: no market was found in which "Exforge D" denotes the dual combination. Arbitration details in `ARBITRATION_REPLY_sampleCSQ.md`.
Consequently, on this pair the dictionary is wrong (`combination_partial`) and the LLM is correct; the originally hypothesized LLM `false_positive` does not hold.

## Error-Pattern Distribution (frozen taxonomy, all 211 pairs)
| Error pattern | Dictionary | LLM |
|---|---|---|
| scope_dispute | 4 (PDE5 inhibitors classified into PAH when used for PAH, by indication) | 4 (tirzepatide dual agonist disputed as GLP1RA; gold standard ruled the dictionary correct) |
| combination_partial | 3 (DIOVAN TRIPLE; MACITENTAN\TADALAFIL; EXFORGE D) | 0 |
| missed_brand | 2 (AVANDAMET; COMBIGAN) | 0 |
| missed_ingredient | 1 (WINREVAIR/sotatercept, new drug of 2024) | 0 |
| false_positive | 0 | 0 |

## Per-Class Metrics (gold standard n=211; sensitivity / PPV with Wilson 95% CI)
### Dictionary
| Class | Gold-standard positives | Sensitivity | PPV |
|---|---|---|---|
| AA_III | 4 | 1.00 [0.51, 1.00] | 1.00 [0.51, 1.00] |
| ACEI | 10 | 1.00 [0.72, 1.00] | 1.00 [0.72, 1.00] |
| ALPHA_BPH | 4 | 1.00 [0.51, 1.00] | 1.00 [0.51, 1.00] |
| ALPHA_HTN | 1 | 1.00 [0.21, 1.00] | 1.00 [0.21, 1.00] |
| ARB | 23 | 1.00 [0.86, 1.00] | 1.00 [0.86, 1.00] |
| ASPIRIN | 7 | 1.00 [0.65, 1.00] | 1.00 [0.65, 1.00] |
| BETA | 12 | 0.92 [0.65, 0.99] | 1.00 [0.74, 1.00] |
| CCB_DHP | 11 | 0.91 [0.62, 0.98] | 1.00 [0.72, 1.00] |
| CENTRAL | 3 | 1.00 [0.44, 1.00] | 1.00 [0.44, 1.00] |
| DOAC | 3 | 1.00 [0.44, 1.00] | 1.00 [0.44, 1.00] |
| DPP4I | 5 | 1.00 [0.57, 1.00] | 1.00 [0.57, 1.00] |
| EZETIMIBE | 2 | 1.00 [0.34, 1.00] | 1.00 [0.34, 1.00] |
| FIBRATE | 2 | 1.00 [0.34, 1.00] | 1.00 [0.34, 1.00] |
| GLP1RA | 11 | 1.00 [0.74, 1.00] | 1.00 [0.74, 1.00] |
| GPIIBIIIA | 1 | 1.00 [0.21, 1.00] | 1.00 [0.21, 1.00] |
| LOOP | 2 | 1.00 [0.34, 1.00] | 1.00 [0.34, 1.00] |
| METFORMIN | 10 | 0.90 [0.60, 0.98] | 1.00 [0.70, 1.00] |
| MINOXIDIL | 3 | 1.00 [0.44, 1.00] | 1.00 [0.44, 1.00] |
| OMEGA3 | 1 | 1.00 [0.21, 1.00] | 1.00 [0.21, 1.00] |
| P2Y12 | 4 | 1.00 [0.51, 1.00] | 1.00 [0.51, 1.00] |
| PAH | 11 | 0.91 [0.62, 0.98] | 0.71 [0.45, 0.88] |
| PCSK9I | 2 | 1.00 [0.34, 1.00] | 1.00 [0.34, 1.00] |
| PDE5 | 7 | 0.29 [0.08, 0.64] | 1.00 [0.34, 1.00] |
| RANOLAZINE | 1 | 1.00 [0.21, 1.00] | 1.00 [0.21, 1.00] |
| RENIN_INH | 1 | 1.00 [0.21, 1.00] | 1.00 [0.21, 1.00] |
| SGLT2I | 6 | 1.00 [0.61, 1.00] | 1.00 [0.61, 1.00] |
| STATIN | 10 | 1.00 [0.72, 1.00] | 1.00 [0.72, 1.00] |
| THIAZIDE | 13 | 0.85 [0.58, 0.96] | 1.00 [0.74, 1.00] |
| VASODIL | 3 | 1.00 [0.44, 1.00] | 1.00 [0.44, 1.00] |
| VKA | 1 | 1.00 [0.21, 1.00] | 1.00 [0.21, 1.00] |

### LLM
| Class | Gold-standard positives | Sensitivity | PPV |
|---|---|---|---|
| AA_III | 4 | 1.00 [0.51, 1.00] | 1.00 [0.51, 1.00] |
| ACEI | 10 | 1.00 [0.72, 1.00] | 1.00 [0.72, 1.00] |
| ALPHA_BPH | 4 | 1.00 [0.51, 1.00] | 1.00 [0.51, 1.00] |
| ALPHA_HTN | 1 | 1.00 [0.21, 1.00] | 1.00 [0.21, 1.00] |
| ARB | 23 | 1.00 [0.86, 1.00] | 1.00 [0.86, 1.00] |
| ASPIRIN | 7 | 1.00 [0.65, 1.00] | 1.00 [0.65, 1.00] |
| BETA | 12 | 1.00 [0.76, 1.00] | 1.00 [0.76, 1.00] |
| CCB_DHP | 11 | 1.00 [0.74, 1.00] | 1.00 [0.74, 1.00] |
| CENTRAL | 3 | 1.00 [0.44, 1.00] | 1.00 [0.44, 1.00] |
| DOAC | 3 | 1.00 [0.44, 1.00] | 1.00 [0.44, 1.00] |
| DPP4I | 5 | 1.00 [0.57, 1.00] | 1.00 [0.57, 1.00] |
| EZETIMIBE | 2 | 1.00 [0.34, 1.00] | 1.00 [0.34, 1.00] |
| FIBRATE | 2 | 1.00 [0.34, 1.00] | 1.00 [0.34, 1.00] |
| GLP1RA | 11 | 0.64 [0.35, 0.85] | 1.00 [0.65, 1.00] |
| GPIIBIIIA | 1 | 1.00 [0.21, 1.00] | 1.00 [0.21, 1.00] |
| LOOP | 2 | 1.00 [0.34, 1.00] | 1.00 [0.34, 1.00] |
| METFORMIN | 10 | 1.00 [0.72, 1.00] | 1.00 [0.72, 1.00] |
| MINOXIDIL | 3 | 1.00 [0.44, 1.00] | 1.00 [0.44, 1.00] |
| OMEGA3 | 1 | 1.00 [0.21, 1.00] | 1.00 [0.21, 1.00] |
| P2Y12 | 4 | 1.00 [0.51, 1.00] | 1.00 [0.51, 1.00] |
| PAH | 11 | 1.00 [0.74, 1.00] | 1.00 [0.74, 1.00] |
| PCSK9I | 2 | 1.00 [0.34, 1.00] | 1.00 [0.34, 1.00] |
| PDE5 | 7 | 1.00 [0.65, 1.00] | 1.00 [0.65, 1.00] |
| RANOLAZINE | 1 | 1.00 [0.21, 1.00] | 1.00 [0.21, 1.00] |
| RENIN_INH | 1 | 1.00 [0.21, 1.00] | 1.00 [0.21, 1.00] |
| SGLT2I | 6 | 1.00 [0.61, 1.00] | 1.00 [0.61, 1.00] |
| STATIN | 10 | 1.00 [0.72, 1.00] | 1.00 [0.72, 1.00] |
| THIAZIDE | 13 | 1.00 [0.77, 1.00] | 1.00 [0.77, 1.00] |
| VASODIL | 3 | 1.00 [0.44, 1.00] | 1.00 [0.44, 1.00] |
| VKA | 1 | 1.00 [0.21, 1.00] | 1.00 [0.21, 1.00] |

(All per-class specificities ≥0.98; omitted for brevity.)

## Agreement (dictionary vs LLM, all 1,000)
- Pair-level exact-match rate: 986/1,000 = 98.6%
- Per-class Cohen's κ macro-average: 0.991; lowest κ = 0.862 (PDE5)
- Classes with κ<0.9: ['PDE5=0.86']

## Stratum C Report-Weighted Extrapolation
- Stratum C: 300 unmatched names (PPS sample) covering 6,808,151 reports; the gold standard confirmed 3 names that should have been classified (AVANDAMET→METFORMIN, COMBIGAN→BETA, WINREVAIR→PAH), corresponding to 7,329 reports
- Report-weighted under-inclusion rate = 0.1077%
- Universe unmatched reports 18,008,855 (universe reports 20,685,703) → estimated under-inclusion ≈ 19,387 reports (0.094% of the universe)
- Direction of impact on candidate-signal a values: the under-inclusion is concentrated in 1 metformin combination brand, 1 ophthalmic timolol combination, and 1 new drug of 2024 — none is the primary drug of any candidate signal; the METFORMIN class exposure count is theoretically slightly underestimated (ROR biased toward the null, negligible magnitude); no impact on other classes

## Conclusion (final; gold standard fully locked)
Dictionary pair-level accuracy 95.3% [91.5%, 97.4%] (n=211, all 211 pairs). The dictionary deviations identified by the audit are systematic policies (indication-driven classification at the PDE5/PAH boundary ×4), partial combination assignment ×3, missed brands ×2, and post-freeze new drug ×1 — none changes the direction of any candidate signal. LLM-as-auditor achieves overall accuracy comparable to the dictionary (McNemar p=0.18) with complementary error patterns; its tirzepatide ×4 deviations were clarified by the gold standard as conservative readings on the LLM side. The dictionary + LLM dual-reading architecture meets the quality threshold pre-specified in appendix v1.1.
