"""classify_drugs.py — Stage 4a: map FAERS drug names to pharmacological classes.

Efficient two-step design:
  1. classify the 152k distinct (drugname, prod_ai) pairs (fast, reviewable,
     freezable as supplementary material)
  2. join back to the 20.7M PS drug rows to build report-level class assignment

Output tables: name_class (pair -> class), report_class (primaryid -> class)
Output CSVs : name_class.csv, class_coverage.csv

Usage:  python classify_drugs.py [db_path]
"""
import csv
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drug_classes import CLASSES, MUTEX  # noqa: E402

DB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "faers.db")
OUT = os.path.dirname(os.path.abspath(__file__))

COMPILED = {
    cls: re.compile(r"\b(" + "|".join(pats) + r")\b")
    for cls, pats in CLASSES.items()
}


def classify(text_upper):
    hits = []
    # some drugnames are written without separators, e.g.
    # "NEXTERONE_AMIODARONE, HYDROCHLORIDE"; match on a normalised copy too
    norm_txt = re.sub(r"[^A-Z0-9]+", " ", text_upper)
    for cls, rx in COMPILED.items():
        if rx.search(text_upper) or rx.search(norm_txt):
            hits.append(cls)
    for keep, drop in MUTEX.items():
        if keep in hits:
            for d in drop:
                if d in hits:
                    hits.remove(d)
    return hits


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    cur.execute("DROP TABLE IF EXISTS name_class")
    cur.execute("DROP TABLE IF EXISTS report_class")
    cur.execute("""
        CREATE TABLE name_class (
            pair_key TEXT, drugname_u TEXT, prod_ai_u TEXT, class TEXT
        )
    """)

    rows = cur.execute(
        "SELECT drugname_u, prod_ai_u, n_cases FROM drug_name_freq"
    ).fetchall()
    print(f"distinct pairs: {len(rows):,}")

    n_rows = n_hit = 0
    batch = []
    case_weight = {}
    for dn, pa, ncase in rows:
        n_rows += 1
        text = f"{dn} | {pa}"
        hits = classify(text)
        if hits:
            n_hit += 1
            for c in hits:
                batch.append((f"{dn}|{pa}", dn, pa, c))
                case_weight[c] = case_weight.get(c, 0) + ncase
        if len(batch) >= 20000:
            cur.executemany("INSERT INTO name_class VALUES (?,?,?,?)", batch)
            batch = []
    if batch:
        cur.executemany("INSERT INTO name_class VALUES (?,?,?,?)", batch)
    con.commit()
    cur.execute("CREATE INDEX idx_name_class_key ON name_class(pair_key)")
    con.commit()
    print(f"pairs with >=1 class: {n_hit:,} ({100.0*n_hit/n_rows:.1f}%)")

    with open(os.path.join(OUT, "name_class.csv"), "w", encoding="utf-8",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(["drugname_u", "prod_ai_u", "class"])
        for r in cur.execute("SELECT drugname_u, prod_ai_u, class "
                             "FROM name_class ORDER BY class, drugname_u"):
            w.writerow(r)

    # ---- report-level class assignment
    print("building report_class (join over 20.7M PS rows)...", flush=True)
    cur.execute("""
        CREATE TABLE report_class AS
        SELECT DISTINCT d.primaryid AS primaryid, nc.class AS class
        FROM drug_ps d
        JOIN name_class nc
          ON UPPER(TRIM(d.drugname)) || '|' || UPPER(TRIM(d.prod_ai))
             = nc.pair_key
    """)
    con.commit()

    # Report-level precedence. MUTEX is applied per drug name in classify(),
    # but a single report can list two separate drug rows (e.g. ENTRESTO plus
    # a valsartan row, or REVATIO plus a sildenafil row); the overlap has to be
    # resolved again here or the report would be double-counted in both classes.
    for keep, drops in MUTEX.items():
        for drop in drops:
            cur.execute("""
                DELETE FROM report_class
                WHERE class = ?
                  AND primaryid IN (SELECT primaryid FROM report_class
                                    WHERE class = ?)
            """, (drop, keep))
    con.commit()

    cur.execute("CREATE INDEX idx_report_class_pid ON report_class(primaryid)")
    cur.execute("CREATE INDEX idx_report_class_cls ON report_class(class)")
    con.commit()
    n_rc = cur.execute("SELECT COUNT(*) FROM report_class").fetchone()[0]
    n_rep = cur.execute("SELECT COUNT(DISTINCT primaryid) "
                        "FROM report_class").fetchone()[0]
    print(f"report_class rows: {n_rc:,} ; reports with >=1 CV class: {n_rep:,}")

    # ---- coverage + sex distribution per class (first analytic output)
    out_path = os.path.join(OUT, "class_coverage.csv")
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["class", "reports", "M", "F", "other_missing",
                    "perc_female_of_known", "median_age_yr"])
        for cls in sorted(CLASSES):
            r = cur.execute("""
                SELECT COUNT(*) AS n,
                       SUM(CASE WHEN d.sex='M' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN d.sex='F' THEN 1 ELSE 0 END)
                FROM report_class rc JOIN demo d ON rc.primaryid = d.primaryid
                WHERE rc.class = ?
            """, (cls,)).fetchone()
            n, m, fl = r
            if not n:
                w.writerow([cls, 0, 0, 0, 0, "", ""])
                continue
            med = cur.execute("""
                SELECT age FROM (
                    SELECT CAST(d.age AS REAL) AS age
                    FROM report_class rc JOIN demo d ON rc.primaryid=d.primaryid
                    WHERE rc.class = ? AND d.age_cod='YR'
                      AND CAST(d.age AS REAL) BETWEEN 0 AND 120
                    ORDER BY CAST(d.age AS REAL)
                ) LIMIT 1 OFFSET (SELECT COUNT(*)/2 FROM (
                    SELECT CAST(d.age AS REAL) AS age
                    FROM report_class rc JOIN demo d ON rc.primaryid=d.primaryid
                    WHERE rc.class = ? AND d.age_cod='YR'
                      AND CAST(d.age AS REAL) BETWEEN 0 AND 120))
            """, (cls, cls)).fetchone()
            pf = 100.0 * fl / (m + fl) if (m + fl) else ""
            w.writerow([cls, n, m, fl, n - m - fl,
                        f"{pf:.1f}" if pf != "" else "",
                        med[0] if med and med[0] is not None else ""])
        tot = cur.execute("""
            SELECT COUNT(*),
                   SUM(CASE WHEN d.sex='M' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN d.sex='F' THEN 1 ELSE 0 END)
            FROM report_class rc JOIN demo d ON rc.primaryid=d.primaryid
        """).fetchone()
        n, m, fl = tot
        pf = 100.0 * fl / (m + fl)
        w.writerow(["__ANY_CV_CLASS__", n, m, fl, n - m - fl, f"{pf:.1f}", ""])
    print(f"\nwritten: {out_path}")

    # print summary
    with open(out_path, encoding="utf-8") as f:
        for line in f:
            print("  " + line.rstrip())
    con.close()


if __name__ == "__main__":
    main()
