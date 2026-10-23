"""make_top_table.py — build the per-class top signal table (Table 2 material).

For each class: top 10 female-shifted and top 10 male-shifted signals (q<0.05).

Source-concentration QC (v2):
  share      = fraction of the signal's sex-known index cases carried by the
               dominant product name
  baseline   = that product's share of the class's sex-known reports
  enrichment = share / baseline  -> >2 means one product carries the signal far
               beyond its usual weight in the class (bulk / single-source
               reporting artefact)
  product_female_share vs class_female_share -> exposes products whose own
               report stream is sex-skewed (one brand filed mostly for women),
               which mechanically manufactures fake sex-differential signals

Writes table2_top_signals.csv.
"""
import csv
import os
import sqlite3
import sys

DB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "faers.db")
OUTDIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(OUTDIR, "table2_top_signals.csv")
TOP_N = 10

# Frozen 2026-10-15 after manual review (takeover review round):
# STATIN x EMOTIONAL DISTRESS is driven by the same LIPITOR female-skewed
# single-source reporting stream as the confirmed STATIN x T2DM artefact
# (LIPITOR product stream 61.0% female vs 53.0% class baseline; enrichment
# 2.90 — it escaped the automatic gate only because the 8pp skew is just
# under the 10pp threshold). Excluded from headline signals and documented
# in the manuscript as a borderline case study of the QC framework.
MANUAL_FLAGS = {
    ("STATIN", "EMOTIONAL DISTRESS"):
        "single-source reporting artefact (LIPITOR female-skewed stream)",
}


def main():
    rows = list(csv.DictReader(open(
        os.path.join(OUTDIR, "sexdiff_tests_filtered.csv"), encoding="utf-8")))
    sig = [r for r in rows if float(r["q"]) < 0.05]
    print(f"all tests: {len(rows):,} ; q<0.05: {len(sig):,}")

    by_class = {}
    for r in sig:
        by_class.setdefault(r["class"], []).append(r)
    # De-duplicated: a class with fewer than 2*TOP_N significant signals used
    # to contribute the same row to both the female-shifted and the
    # male-shifted list, producing duplicate rows in Table 2.
    selected, seen = [], set()
    for c, lst in sorted(by_class.items()):
        for r in (sorted(lst, key=lambda x: -float(x["ROR_ratio"]))[:TOP_N]
                  + sorted(lst, key=lambda x: float(x["ROR_ratio"]))[:TOP_N]):
            key = (r["class"], r["pt"])
            if key in seen:
                continue
            seen.add(key)
            selected.append(r)
    print(f"selected: {len(selected)} signals over {len(by_class)} classes "
          f"({len(selected)} unique class x PT)")

    con = sqlite3.connect(DB)
    cur = con.cursor()
    conc, base_share, prod_sex, class_sex = {}, {}, {}, {}

    for c in sorted(by_class):
        sel_pts = sorted({r["pt"] for r in selected if r["class"] == c})
        if not sel_pts:
            continue
        cur.execute("CREATE TEMP TABLE idx_set AS "
                    "SELECT DISTINCT primaryid FROM report_class WHERE class=?",
                    (c,))
        cur.execute("CREATE TEMP TABLE pt_set (pt TEXT)")
        cur.executemany("INSERT INTO pt_set VALUES (?)",
                        [(p,) for p in sel_pts])

        # denominators are counted in REPORTS everywhere (see main_analysis)
        cs = dict(cur.execute(
            """SELECT m.sex, COUNT(DISTINCT m.primaryid) FROM demo m
               WHERE m.sex IN ('M','F')
                 AND m.primaryid IN (SELECT primaryid FROM idx_set)
               GROUP BY m.sex"""))
        class_sex[c] = cs.get("F", 0) / max(cs.get("F", 0) + cs.get("M", 0), 1)

        # baseline: prevalence of each product name among the class's reports.
        # The denominator is the number of CLASS REPORTS (not the sum of the
        # per-name counts, which double-counts reports listing several drugs),
        # so that `share` and `baseline` are on the same report-level scale and
        # their ratio (enrichment) is interpretable.
        tot_base = cur.execute(
            """SELECT COUNT(DISTINCT m.primaryid) FROM demo m
               WHERE m.sex IN ('M','F')
                 AND m.primaryid IN (SELECT primaryid FROM idx_set)"""
        ).fetchone()[0]
        for dn, n in cur.execute(
                """SELECT UPPER(TRIM(d.drugname)), COUNT(DISTINCT d.primaryid)
                   FROM drug_ps d JOIN demo m ON m.primaryid = d.primaryid
                   WHERE m.sex IN ('M','F')
                     AND d.primaryid IN (SELECT primaryid FROM idx_set)
                   GROUP BY 1"""):
            base_share[(c, dn)] = n / max(tot_base, 1)

        for dn, f, m in cur.execute(
                """SELECT UPPER(TRIM(d.drugname)),
                          COUNT(DISTINCT CASE WHEN m.sex='F'
                                              THEN m.primaryid END),
                          COUNT(DISTINCT CASE WHEN m.sex='M'
                                              THEN m.primaryid END)
                   FROM drug_ps d JOIN demo m ON m.primaryid = d.primaryid
                   WHERE m.sex IN ('M','F')
                     AND d.primaryid IN (SELECT primaryid FROM idx_set)
                   GROUP BY 1"""):
            if f + m >= 20:
                prod_sex[(c, dn)] = f / (f + m)

        for pt, dn, n in cur.execute(
                """SELECT r.pt, UPPER(TRIM(d.drugname)),
                          COUNT(DISTINCT r.primaryid)
                   FROM reac r
                   JOIN drug_ps d ON d.primaryid = r.primaryid
                   JOIN demo m ON m.primaryid = r.primaryid
                   WHERE m.sex IN ('M','F')
                     AND r.primaryid IN (SELECT primaryid FROM idx_set)
                     AND r.pt IN (SELECT pt FROM pt_set)
                   GROUP BY r.pt, 2"""):
            if n > conc.get((c, pt), (0, ""))[0]:
                conc[(c, pt)] = (n, dn)
        cur.execute("DROP TABLE idx_set")
        cur.execute("DROP TABLE pt_set")
        print(f"  {c}: QC done", flush=True)

    cols = list(rows[0].keys()) + [
        "direction", "dominant_product", "product_share_pct",
        "product_baseline_pct", "enrichment", "product_female_share_pct",
        "class_female_share_pct", "src_concentrated", "manual_flag"]
    n_flag = 0
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in selected:
            c, pt = r["class"], r["pt"]
            tot = int(r["a_f"]) + int(r["a_m"])
            n, dn = conc.get((c, pt), (0, ""))
            share = n / tot if tot else 0.0
            bl = base_share.get((c, dn), 0.0)
            enr = share / bl if bl > 0 else float("nan")
            out = dict(r)
            out["direction"] = "female" if float(r["ROR_ratio"]) > 1 else "male"
            out["dominant_product"] = dn
            out["product_share_pct"] = f"{100*share:.1f}"
            out["product_baseline_pct"] = f"{100*bl:.1f}"
            out["enrichment"] = f"{enr:.2f}" if enr == enr else ""
            out["product_female_share_pct"] = (
                f"{100*prod_sex[(c, dn)]:.1f}" if (c, dn) in prod_sex else "")
            out["class_female_share_pct"] = f"{100*class_sex.get(c, 0):.1f}"
            # artefact only if the signal is both product-concentrated AND
            # that product is anomalous (dominates the signal, or its own
            # report stream is sex-skewed relative to the class baseline)
            skew = abs(prod_sex.get((c, dn), class_sex.get(c, 0.5))
                       - class_sex.get(c, 0.5))
            flagged = bool(share > 0.5 and enr == enr and enr > 2
                           and (share > 0.8 or skew > 0.10))
            out["src_concentrated"] = "YES" if flagged else "no"
            out["manual_flag"] = MANUAL_FLAGS.get((c, pt), "")
            n_flag += flagged
            w.writerow(out)
    print(f"written: {OUT} ; flagged source-concentrated: "
          f"{n_flag}/{len(selected)}")


if __name__ == "__main__":
    main()
