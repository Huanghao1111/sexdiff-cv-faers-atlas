"""audit_classes.py — data-driven audit of the frozen drug-class dictionary.

Two checks against the real 20.7M PS drug records:
  A. coverage profile: per class, report count and the top product names it
     actually matched (so a human can spot wrong inclusions at a glance)
  B. missed-candidate scan: unclassified (drugname, prod_ai) pairs with the
     highest case counts that *loosely* contain a class keyword after
     normalisation (stripping punctuation/extra spaces) -> suspected omissions
     caused by spelling variants, combination syntax, or truncation

Outputs class_audit_report.txt + class_audit_topnames.csv
"""
import csv
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drug_classes import CLASSES  # noqa: E402

DB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "faers.db")
OUT = os.path.dirname(os.path.abspath(__file__))


def norm(s):
    """letters/digits only, single spaced — tolerant of punctuation variants."""
    return re.sub(r"[^A-Z0-9]+", " ", (s or "").upper()).strip()


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    lines = []
    topnames_rows = []

    # ---- A. per-class profile
    lines.append("=" * 100)
    lines.append("A. Per-class matched profile (sorted by report count)")
    lines.append("=" * 100)
    prof = []
    for cls in CLASSES:
        r = cur.execute(
            """SELECT COUNT(DISTINCT primaryid) FROM report_class
               WHERE class=?""", (cls,)).fetchone()
        prof.append((cls, r[0]))
    for cls, n in sorted(prof, key=lambda x: -x[1]):
        lines.append(f"\n[{cls}]  reports={n:,}")
        rows = cur.execute(
            """SELECT d.drugname_u, d.prod_ai_u, SUM(
                   CASE WHEN rc.primaryid IS NOT NULL THEN 1 END) AS hits
               FROM report_class rc
               JOIN drug_ps dp ON dp.primaryid = rc.primaryid
               JOIN drug_name_freq d
                 ON UPPER(TRIM(dp.drugname)) = d.drugname_u
                AND UPPER(TRIM(dp.prod_ai)) = d.prod_ai_u
               WHERE rc.class = ?
               GROUP BY d.drugname_u, d.prod_ai_u
               ORDER BY hits DESC LIMIT 12""", (cls,)).fetchall()
        for dn, pa, h in rows:
            lines.append(f"    {h:>8,}  {dn[:44]:<44} | {pa[:34]}")
            topnames_rows.append([cls, h, dn, pa])

    # ---- B. missed candidates
    lines.append("\n" + "=" * 100)
    lines.append("B. Suspected misses: high-frequency unclassified drug names loosely containing class keywords")
    lines.append("=" * 100)
    classified = set()
    for dn, pa in cur.execute("SELECT drugname_u, prod_ai_u FROM name_class"):
        classified.add((dn, pa))
    pairs = cur.execute(
        "SELECT drugname_u, prod_ai_u, n_cases FROM drug_name_freq "
        "ORDER BY n_cases DESC LIMIT 40000").fetchall()

    kw_norm = {cls: [norm(k) for k in pats] for cls, pats in CLASSES.items()}
    missed = {}
    for dn, pa, ncase in pairs:
        if (dn, pa) in classified:
            continue
        txt = norm(dn) + " " + norm(pa)
        if not txt.strip():
            continue
        for cls, kws in kw_norm.items():
            for k in kws:
                if not k:
                    continue
                # loose containment: keyword as token sequence inside text
                if (" " + k + " ") in (" " + txt + " "):
                    missed.setdefault(cls, []).append((ncase, dn, pa, k))
                    break
    for cls in sorted(missed, key=lambda c: -sum(x[0] for x in missed[c])):
        tot = sum(x[0] for x in missed[cls])
        lines.append(f"\n[{cls}]  suspected missed cases total={tot:,} (top 12 high-frequency combinations below)")
        for ncase, dn, pa, k in sorted(missed[cls], reverse=True)[:12]:
            lines.append(f"    {ncase:>8,}  {dn[:40]:<40} | {pa[:30]:<30} <- {k}")

    out_txt = os.path.join(OUT, "class_audit_report.txt")
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    with open(os.path.join(OUT, "class_audit_topnames.csv"), "w",
              encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["class", "reports", "drugname_u", "prod_ai_u"])
        w.writerows(topnames_rows)
    print(f"written: {out_txt}")
    print(f"written: {os.path.join(OUT, 'class_audit_topnames.csv')}")
    print(f"classes audited: {len(CLASSES)} ; "
          f"classes with suspected omissions: {len(missed)}")


if __name__ == "__main__":
    main()
