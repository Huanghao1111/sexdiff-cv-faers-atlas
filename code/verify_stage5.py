"""verify_stage5.py — post-rerun verification of the Stage 5 result set.

Checks, against benchmarks frozen in the 2026-10-15 memory notes:
  1. positive controls: ACEI cough (female-shifted), DIGOXIN toxicity (female)
  2. flagship clinical signals: SGLT2I genital fungal infection, ARNI
     angioedema, LOOP torsade de pointes, PCSK9I angioedema
  3. global counts: number of tests, q<0.05 count
  4. Table 2 candidate pool: non-artefact + non-indication-coded + n>=100
  5. known-artefact flags: STATIN x T2DM must be source-concentration flagged
Run AFTER main_analysis.py + apply_exclusions.py + make_top_table.py.
"""
import csv
import os

OUT = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with open(os.path.join(OUT, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def show(rows, cls, kw, label=""):
    hit = [r for r in rows if r["class"] == cls and kw in r["pt"].upper()]
    if not hit:
        print(f"  [MISS] {cls} x {kw} {label} — NOT FOUND")
        return
    for r in hit[:3]:
        print(f"  {r['class']:<10} {r['pt']:<42} ratio={float(r['ROR_ratio']):>7.2f} "
              f"({float(r['ratio_lo']):.2f}-{float(r['ratio_hi']):.2f}) "
              f"q={float(r['q']):.2e} a_f={r['a_f']} a_m={r['a_m']} {label}")


def main():
    allt = load("sexdiff_all_tests.csv")
    filt = load("sexdiff_tests_filtered.csv")
    tab2 = load("table2_top_signals.csv")

    n_sig = sum(1 for r in allt if float(r["q"]) < 0.05)
    print(f"[1] all tests: {len(allt):,} ; q<0.05: {n_sig:,} "
          f"(benchmark ~33.5k / ~3.4k)")
    print(f"    filtered (non-informative removed): {len(filt):,}")

    print("[2] positive controls (expect female-shifted, q<0.05):")
    show(allt, "ACEI", "COUGH", "<- positive control")
    show(allt, "DIGOXIN", "TOXICITY", "<- positive control")

    print("[3] flagship signals:")
    show(allt, "SGLT2I", "GENITAL INFECTION FUNGAL")
    show(allt, "ARNI", "ANGIOEDEMA")
    show(allt, "PCSK9I", "ANGIOEDEMA")
    show(allt, "LOOP", "TORSADE")
    show(allt, "AA_III", "THYROID")
    show(allt, "STATIN", "SENSORY NEUROPATHY")

    print("[4] Table 2 candidates (non-artefact, non-indication, n>=100):")
    cand = [r for r in tab2
            if r["src_concentrated"] != "YES"
            and r.get("indication_coded") != "YES"
            and not r.get("manual_flag")
            and int(r["a_f"]) + int(r["a_m"]) >= 100]
    print(f"    table2 rows: {len(tab2)} ; candidates: {len(cand)} "
          f"(benchmark 102)")
    flagged = sum(1 for r in tab2 if r["src_concentrated"] == "YES")
    print(f"    source-concentration flagged: {flagged}/{len(tab2)} "
          f"(benchmark 59/616)")

    print("[5] artefact flags that MUST be set:")
    t2dm = [r for r in tab2 if r["class"] == "STATIN"
            and "TYPE 2 DIABETES" in r["pt"].upper()]
    for r in t2dm:
        print(f"    STATIN x {r['pt']}: ratio={float(r['ROR_ratio']):.2f} "
              f"flag={r['src_concentrated']} enrichment={r['enrichment']} "
              f"prod_fem={r['product_female_share_pct']}% "
              f"(expect YES, enrichment ~3.7)")
    emo = [r for r in tab2 if r["class"] == "STATIN"
           and "EMOTIONAL" in r["pt"].upper()]
    for r in emo:
        print(f"    STATIN x {r['pt']}: ratio={float(r['ROR_ratio']):.2f} "
              f"flag={r['src_concentrated']} enrichment={r['enrichment']} "
              f"prod_fem={r['product_female_share_pct']}% (edge case, review)")


if __name__ == "__main__":
    main()
