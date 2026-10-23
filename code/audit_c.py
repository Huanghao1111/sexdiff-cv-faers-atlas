"""audit_c.py — independent recomputation of the analysis layer.

Recomputes 2x2 tables, ROR_f / ROR_m / ROR_ratio / SE / z / p for three
benchmark signals DIRECTLY from faers.db, written from scratch (temp-table
free, EXISTS-based), then compares against sexdiff_all_tests.csv.
Also re-verifies the BH q-values with an independent implementation.
"""
import csv
import math
import sqlite3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drug_classes import CV_CLASSES

DB = "faers.db"
SIGNALS = [
    ("ACEI", "COUGH"),
    ("SGLT2I", "GENITAL INFECTION FUNGAL"),
    ("LOOP", "TORSADE DE POINTES"),
    ("AA_III", "HYPERTHYROIDISM"),
]

con = sqlite3.connect(DB)
cur = con.cursor()

# universe denominators (sex-known, distinct reports), computed independently
CV_LIST = ",".join(f"'{c}'" for c in CV_CLASSES)
N = {}
for sex in ("F", "M"):
    N[sex] = cur.execute(
        f"""SELECT COUNT(*) FROM demo
           WHERE sex = ? AND EXISTS (
               SELECT 1 FROM report_class rc WHERE rc.primaryid = demo.primaryid
                 AND rc.class IN ({CV_LIST})
           )""", (sex,)).fetchone()[0]
print(f"[C0] CV universe (distinct, sex-known): {N}")

csv_rows = {}
with open("sexdiff_all_tests.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        csv_rows[(r["class"], r["pt"])] = r

def cell_counts(cls, pt, sex):
    """a = index reports with PT; n = index reports (denominator)."""
    a = cur.execute(
        """SELECT COUNT(DISTINCT d.primaryid) FROM demo d
           WHERE d.sex = ?
             AND EXISTS (SELECT 1 FROM report_class rc
                         WHERE rc.primaryid = d.primaryid AND rc.class = ?)
             AND EXISTS (SELECT 1 FROM reac r
                         WHERE r.primaryid = d.primaryid AND r.pt = ?)""",
        (sex, cls, pt)).fetchone()[0]
    n = cur.execute(
        """SELECT COUNT(DISTINCT d.primaryid) FROM demo d
           WHERE d.sex = ?
             AND EXISTS (SELECT 1 FROM report_class rc
                         WHERE rc.primaryid = d.primaryid AND rc.class = ?)""",
        (sex, cls)).fetchone()[0]
    # comparator: in universe (any CV class) with PT, minus index-with-PT
    a_univ = cur.execute(
        f"""SELECT COUNT(DISTINCT d.primaryid) FROM demo d
           WHERE d.sex = ?
             AND EXISTS (SELECT 1 FROM report_class rc
                         WHERE rc.primaryid = d.primaryid
                           AND rc.class IN ({CV_LIST}))
             AND EXISTS (SELECT 1 FROM reac r
                         WHERE r.primaryid = d.primaryid AND r.pt = ?)""",
        (sex, pt)).fetchone()[0]
    return a, n, a_univ - a, N[sex] - n

print("\n[C1] independent 2x2 recomputation vs pipeline CSV")
ok = True
for cls, pt in SIGNALS:
    row = csv_rows.get((cls, pt))
    if row is None:
        print(f"  {cls} x {pt}: NOT IN CSV!")
        ok = False
        continue
    af, nf, cf, Nf = cell_counts(cls, pt, "F")
    am, nm, cm, Nm = cell_counts(cls, pt, "M")
    bf, bm = nf - af, nm - am
    df, dm = Nf - cf, Nm - cm
    ror_f = (af / bf) / (cf / df)
    ror_m = (am / bm) / (cm / dm)
    ratio = ror_f / ror_m
    se = math.sqrt(sum(1.0 / x for x in (af, bf, cf, df, am, bm, cm, dm)))
    z = math.log(ratio) / se
    p = math.erfc(abs(z) / math.sqrt(2.0))
    cmp_ = [
        ("a_f", af, int(row["a_f"])), ("n_f", nf, int(row["n_f"])),
        ("a_m", am, int(row["a_m"])), ("n_m", nm, int(row["n_m"])),
        ("c_f", cf, int(row["c_f"])), ("N_f", Nf, int(row["N_f"])),
        ("c_m", cm, int(row["c_m"])), ("N_m", Nm, int(row["N_m"])),
    ]
    mism = [f"{k}:mine={v} csv={w}" for k, v, w in cmp_ if v != w]
    ok_ratio = abs(ratio - float(row["ROR_ratio"])) < 1e-4 * ratio
    ok_p = (p == 0 and float(row["p"]) == 0) or abs(p - float(row["p"])) < 1e-3 * max(p, 1e-300)
    status = "OK" if (not mism and ok_ratio and ok_p) else "MISMATCH"
    if status != "OK":
        ok = False
    print(f"  {cls} x {pt}: {status}  ratio mine={ratio:.6g} csv={row['ROR_ratio']} "
          f"p mine={p:.3g} csv={row['p']}")
    for m in mism:
        print(f"      {m}")

# [C2] independent BH verification
print("\n[C2] BH-FDR independent verification")
rows = list(csv_rows.values())
pvals = [float(r["p"]) for r in rows]
n = len(pvals)
# independent BH: q_i = min over j>=rank(i) of p_(j)*n/j  (compute via numpy-free loop)
order = sorted(range(n), key=lambda i: -pvals[i])  # descending
q_mine = [0.0] * n
run_min = 1.0
for rank_from_end, i in enumerate(order):
    rank = n - rank_from_end          # rank of pvals[i] ascending, 1-based
    val = pvals[i] * n / rank
    run_min = min(run_min, val)
    q_mine[i] = min(run_min, 1.0)
bad = 0
maxdiff = 0.0
for r, qm in zip(rows, q_mine):
    qc = float(r["q"])
    d = abs(qc - qm)
    maxdiff = max(maxdiff, d)
    if d > 1e-5:   # CSV stores %.6g rounded p/q; re-derived q can drift ~1e-6
        bad += 1
print(f"  tests={n:,} ; q mismatches(>1e-5): {bad} ; max|diff|={maxdiff:.3g}")
n_sig_mine = sum(1 for q in q_mine if q < 0.05)
print(f"  q<0.05 mine={n_sig_mine:,} csv={sum(1 for r in rows if float(r['q'])<0.05):,}")

# [C3] estimand sanity: TdP / QT under active comparator
print("\n[C3] estimand check: AA_III x TdP / QT (expect ratio ~1, both RORs high)")
for cls, pt in [("AA_III", "TORSADE DE POINTES"), ("AA_III", "ELECTROCARDIOGRAM QT PROLONGED"),
                ("DIGOXIN", "TORSADE DE POINTES")]:
    row = csv_rows.get((cls, pt))
    if row:
        print(f"  {cls} x {pt}: ROR_f={float(row['ROR_f']):.2f} "
              f"ROR_m={float(row['ROR_m']):.2f} ratio={float(row['ROR_ratio']):.2f} "
              f"q={float(row['q']):.2g}")
    else:
        print(f"  {cls} x {pt}: not tested (cell<5)")

con.close()
print("\nAUDIT C:", "PASS" if ok and bad == 0 else "ISSUES FOUND")
