"""qc_top_signals.py — post-hoc source-concentration QC for top signals.

Reads sexdiff_top.csv, and for every (class, PT) pair computes:
  - the single drugname variant carrying the largest share of index cases
  - its share (%)  -> >50% flags a bulk/manufacturer reporting artefact
  - the single quarter carrying the largest share
Rewrites the CSV with the added columns.
"""
import csv
import os
import sqlite3
import sys

DB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "faers.db")
OUT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(OUT, "sexdiff_top.csv")

cols_extra = ["top_drugname", "top_drugname_share_pct",
              "top_quarter", "top_quarter_share_pct", "src_concentrated"]


def main():
    with open(SRC, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys())
    con = sqlite3.connect(DB)
    cur = con.cursor()

    by_class = {}
    for r in rows:
        by_class.setdefault(r["class"], []).append(r["pt"])

    conc_dn, conc_q = {}, {}
    for cname, pts in by_class.items():
        cur.execute("CREATE TEMP TABLE idx_set AS "
                    "SELECT DISTINCT primaryid FROM report_class WHERE class=?",
                    (cname,))
        cur.execute("CREATE TEMP TABLE pt_set (pt TEXT)")
        cur.executemany("INSERT INTO pt_set VALUES (?)", [(p,) for p in pts])
        for pt, dn, n in cur.execute(
                """SELECT r.pt, UPPER(TRIM(d.drugname)),
                          COUNT(DISTINCT r.primaryid)
                   FROM reac r JOIN drug_ps d ON r.primaryid = d.primaryid
                   WHERE r.primaryid IN (SELECT primaryid FROM idx_set)
                     AND r.pt IN (SELECT pt FROM pt_set)
                   GROUP BY r.pt, UPPER(TRIM(d.drugname))"""):
            if n > conc_dn.get((cname, pt), (0, ""))[0]:
                conc_dn[(cname, pt)] = (n, dn)
        for pt, q, n in cur.execute(
                """SELECT r.pt, d.quarter, COUNT(DISTINCT r.primaryid)
                   FROM reac r JOIN drug_ps d ON r.primaryid = d.primaryid
                   WHERE r.primaryid IN (SELECT primaryid FROM idx_set)
                     AND r.pt IN (SELECT pt FROM pt_set)
                   GROUP BY r.pt, d.quarter"""):
            if n > conc_q.get((cname, pt), (0, ""))[0]:
                conc_q[(cname, pt)] = (n, q)
        cur.execute("DROP TABLE idx_set")
        cur.execute("DROP TABLE pt_set")

    for r in rows:
        tot = int(r["a_f"]) + int(r["a_m"])
        n, dn = conc_dn.get((r["class"], r["pt"]), (0, ""))
        nq, q = conc_q.get((r["class"], r["pt"]), (0, ""))
        r["top_drugname"] = dn
        r["top_drugname_share_pct"] = f"{100.0*n/tot:.1f}" if tot else ""
        r["top_quarter"] = q
        r["top_quarter_share_pct"] = f"{100.0*nq/tot:.1f}" if tot else ""
        r["src_concentrated"] = "YES" if tot and n / tot > 0.5 else "no"

    fieldnames += cols_extra
    with open(SRC, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    n_flag = sum(1 for r in rows if r["src_concentrated"] == "YES")
    print(f"rows: {len(rows)} ; flagged source-concentrated: {n_flag}")
    print(f"rewritten: {SRC}")


if __name__ == "__main__":
    main()
