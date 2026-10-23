"""main_analysis.py — Stage 5: sex-differential disproportionality engine.

For each cardiovascular drug class (index) vs the remaining cardiovascular
pharmacotherapy (active comparator), for every MedDRA PT:

    ROR_female = (a_f/b_f)/(c_f/d_f)   ROR_male = (a_m/b_m)/(c_m/d_m)
    ROR_ratio  = ROR_female / ROR_male           [interaction / sex effect]

  a = index reports with the PT (by sex);  b = index reports without the PT
  c = comparator reports with the PT;      d = comparator reports without it
Signal criteria: every cell >= 5 reports, FDR (Benjamini-Hochberg) q < 0.05.

Outputs:
  sexdiff_all_tests.csv   - every tested class x PT with counts, RORs, ratio, p, q
  sexdiff_top.csv         - top 25 female-shifted / male-shifted per class
Usage:  python main_analysis.py [db_path]
"""
import csv
import math
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drug_classes import CV_CLASSES  # noqa: E402
from pt_exclusions import is_noninformative  # noqa: E402

DB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "faers.db")
OUT = os.path.dirname(os.path.abspath(__file__))
MIN_CELL = 5


def norm_sf(z):
    """Two-sided p from z."""
    return math.erfc(abs(z) / math.sqrt(2.0))


def bh_fdr(pvals):
    """Benjamini-Hochberg q-values (same order as input)."""
    n = len(pvals)
    order = sorted(range(n), key=lambda i: pvals[i])
    q = [0.0] * n
    prev = 1.0
    for rank in range(n - 1, -1, -1):
        i = order[rank]
        val = pvals[i] * n / (rank + 1)
        prev = min(prev, val)
        q[i] = min(prev, 1.0)
    return q


def main():
    t0 = time.time()
    con = sqlite3.connect(DB)
    cur = con.cursor()
    con.execute("PRAGMA temp_store=MEMORY")

    all_classes = [r[0] for r in cur.execute(
        "SELECT DISTINCT class FROM report_class ORDER BY class")]
    classes = [c for c in all_classes if c in CV_CLASSES]
    print(f"classes in DB: {len(all_classes)} ; "
          f"analysed (CV universe): {len(classes)}", flush=True)

    # report-level denominators per class and for the CV comparator universe
    qmarks = ",".join("?" * len(classes))
    cur.execute(f"CREATE TEMP TABLE cv_univ AS "
                f"SELECT DISTINCT primaryid FROM report_class "
                f"WHERE class IN ({qmarks})", classes)
    cur.execute("CREATE INDEX tmp_cv ON cv_univ(primaryid)")

    # ---- comparator counts for the WHOLE cardiovascular universe, once.
    # idx_set is by construction a subset of cv_univ, so
    #   comparator = cv_univ \ idx_set   =>   c = c_all - a_idx
    # exactly (both sides count distinct reports per PT per sex). This turns
    # 36 x (index + comparator) full scans into 36 index scans + 1 global scan.
    a_all = {}
    for pt, sex, n in cur.execute(
            """SELECT r.pt, m.sex, COUNT(DISTINCT r.primaryid)
               FROM cv_univ u
               JOIN reac r ON r.primaryid = u.primaryid
               JOIN demo m ON m.primaryid = u.primaryid
               WHERE m.sex IN ('M','F')
               GROUP BY r.pt, m.sex"""):
        a_all.setdefault(pt, {})[sex] = n
    N_all = dict(cur.execute(
        """SELECT m.sex, COUNT(DISTINCT m.primaryid)
           FROM cv_univ u JOIN demo m ON m.primaryid = u.primaryid
           WHERE m.sex IN ('M','F') GROUP BY m.sex"""))
    print(f"CV universe: F={N_all.get('F',0):,} M={N_all.get('M',0):,} ; "
          f"PTs observed: {len(a_all):,} ({time.time()-t0:.0f}s)", flush=True)

    tests = []
    for cname in classes:
        cur.execute("CREATE TEMP TABLE idx_set AS "
                    "SELECT DISTINCT primaryid FROM report_class WHERE class=?",
                    (cname,))
        cur.execute("CREATE INDEX tmp_idx ON idx_set(primaryid)")

        a_idx = {}
        for pt, sex, n in cur.execute(
                """SELECT r.pt, m.sex, COUNT(DISTINCT r.primaryid)
                   FROM idx_set i
                   JOIN reac r ON r.primaryid = i.primaryid
                   JOIN demo m ON m.primaryid = i.primaryid
                   WHERE m.sex IN ('M','F')
                   GROUP BY r.pt, m.sex"""):
            a_idx.setdefault(pt, {})[sex] = n
        # denominators counted in REPORTS (COUNT(DISTINCT primaryid)), exactly
        # like the numerators
        n_idx = dict(cur.execute(
            """SELECT m.sex, COUNT(DISTINCT m.primaryid)
               FROM idx_set i JOIN demo m ON m.primaryid = i.primaryid
               WHERE m.sex IN ('M','F') GROUP BY m.sex"""))
        n_cmp = {s: N_all.get(s, 0) - n_idx.get(s, 0) for s in ("F", "M")}

        f_i, m_i = n_idx.get("F", 0), n_idx.get("M", 0)
        f_c, m_c = n_cmp.get("F", 0), n_cmp.get("M", 0)
        # sorted() (not set()) so the output order is deterministic across runs
        pts = sorted(a_all)
        n_skip = 0
        for pt in pts:
            if is_noninformative(pt):
                n_skip += 1
                continue
            af = a_idx.get(pt, {}).get("F", 0)
            am = a_idx.get(pt, {}).get("M", 0)
            cf = a_all[pt].get("F", 0) - af
            cm = a_all[pt].get("M", 0) - am
            if cf < 0 or cm < 0:   # can only happen if idx_set ⊄ cv_univ
                raise RuntimeError(f"comparator underflow: {cname} / {pt}")
            bf, bm = f_i - af, m_i - am
            df, dm = f_c - cf, m_c - cm
            if min(af, am, cf, cm, bf, bm, df, dm) < MIN_CELL:
                continue
            ror_f = (af / bf) / (cf / df)
            ror_m = (am / bm) / (cm / dm)
            ratio = ror_f / ror_m
            se = math.sqrt(sum(1.0 / x for x in
                               (af, bf, cf, df, am, bm, cm, dm)))
            z = math.log(ratio) / se
            tests.append({
                "class": cname, "pt": pt, "a_f": af, "n_f": f_i,
                "a_m": am, "n_m": m_i, "c_f": cf, "N_f": f_c,
                "c_m": cm, "N_m": m_c,
                "ROR_f": ror_f, "ROR_m": ror_m, "ROR_ratio": ratio,
                "se": se, "z": z, "p": norm_sf(z),
                "ratio_lo": math.exp(math.log(ratio) - 1.96 * se),
                "ratio_hi": math.exp(math.log(ratio) + 1.96 * se),
            })
        cur.execute("DROP TABLE idx_set")
        print(f"  {cname:<12} idx F={f_i:>7,} M={m_i:>7,} | "
              f"cmp F={f_c:>7,} M={m_c:>7,} | tests {len(tests):>8,} "
              f"| non-informative PTs skipped {n_skip} "
              f"({time.time()-t0:.0f}s)", flush=True)

    q = bh_fdr([t["p"] for t in tests])
    for t, qq in zip(tests, q):
        t["q"] = qq
    print(f"\ntotal tests: {len(tests):,} ; "
          f"q<0.05: {sum(1 for t in tests if t['q'] < 0.05):,}", flush=True)

    # QC columns are part of the output: in v1 they were computed and then
    # silently dropped by extrasaction="ignore".
    cols = ["class", "pt", "a_f", "n_f", "a_m", "n_m", "c_f", "N_f", "c_m",
            "N_m", "ROR_f", "ROR_m", "ROR_ratio", "ratio_lo", "ratio_hi",
            "z", "p", "q", "top_drugname", "top_drugname_share",
            "src_concentrated"]
    all_path = os.path.join(OUT, "sexdiff_all_tests.csv")
    with open(all_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for t in sorted(tests, key=lambda x: (x["p"])):
            row = dict(t)
            for k in ("ROR_f", "ROR_m", "ROR_ratio", "ratio_lo", "ratio_hi",
                      "z", "p", "q"):
                row[k] = f"{row[k]:.6g}"
            w.writerow(row)
    print(f"written: {all_path}")

    sig = [t for t in tests if t["q"] < 0.05]
    top_up = sorted(sig, key=lambda x: -x["ROR_ratio"])[:25]
    top_dn = sorted(sig, key=lambda x: x["ROR_ratio"])[:25]

    # ---- source-concentration QC for top signals.
    # Bulk/manufacturer reporting creates artefactual sex skew (e.g. one
    # product carrying thousands of identical female-only reports). Flag any
    # signal where a single product name accounts for most index cases.
    print("source-concentration QC on top signals...", flush=True)
    top_all = top_up + top_dn
    by_class = {}
    for t in top_all:
        by_class.setdefault(t["class"], []).append(t["pt"])
    for cname, ptlist in by_class.items():
        cur.execute("CREATE TEMP TABLE idx_set AS "
                    "SELECT DISTINCT primaryid FROM report_class WHERE class=?",
                    (cname,))
        cur.execute("CREATE TEMP TABLE pt_set (pt TEXT)")
        cur.executemany("INSERT INTO pt_set VALUES (?)",
                        [(p,) for p in ptlist])
        conc = {}
        for pt, dn, n in cur.execute(
                """SELECT r.pt, UPPER(TRIM(d.drugname)), COUNT(DISTINCT r.primaryid)
                   FROM reac r JOIN drug_ps d ON r.primaryid = d.primaryid
                   WHERE r.primaryid IN (SELECT primaryid FROM idx_set)
                     AND r.pt IN (SELECT pt FROM pt_set)
                   GROUP BY r.pt, UPPER(TRIM(d.drugname))"""):
            if n > conc.get(pt, (0, ""))[0]:
                conc[pt] = (n, dn)
        for t in top_all:
            if t["class"] != cname:
                continue
            n, dn = conc.get(t["pt"], (0, ""))
            tot = t["a_f"] + t["a_m"]
            t["top_drugname"] = dn
            t["top_drugname_share"] = f"{100.0*n/tot:.1f}" if tot else ""
            t["src_concentrated"] = "YES" if tot and n / tot > 0.5 else "no"
        cur.execute("DROP TABLE idx_set")
        cur.execute("DROP TABLE pt_set")

    top_path = os.path.join(OUT, "sexdiff_top.csv")
    with open(top_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for t in top_up + top_dn:
            row = dict(t)
            for k in ("ROR_f", "ROR_m", "ROR_ratio", "ratio_lo", "ratio_hi",
                      "z", "p", "q"):
                row[k] = f"{row[k]:.6g}"
            w.writerow(row)
    print(f"written: {top_path}")
    print(f"total time: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
