"""build_outc_db.py — Stage 3b: patient outcome (seriousness) layer.

OUTC files carry one row per outcome code per report:
  DE death, LT life-threatening, HO hospitalisation, DS disability,
  CA congenital anomaly, RI required intervention, OT other serious.
Seriousness is required for the protocol's "serious reports only" sensitivity
analysis and for Table 1 (serious-outcome proportions).

Creates table `outc(primaryid, outc_cod)` and `serious(primaryid)` holding
reports with at least one serious outcome code.
"""
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from faers_reader import iter_records, quarter_of  # noqa: E402

DATA_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pilot", "data")
DB = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "faers.db")

SERIOUS = {"DE", "LT", "HO", "DS", "CA", "RI"}


def quarter_list(d):
    zs = [f for f in os.listdir(d) if f.endswith(".zip") and "ascii" in f.lower()]
    return sorted(zs, key=quarter_of)


def main():
    t0 = time.time()
    quarters = quarter_list(DATA_DIR)
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS outc")
    cur.execute("CREATE TABLE outc (primaryid TEXT, outc_cod TEXT)")

    for qi, fname in enumerate(quarters, 1):
        # OUTC files have no canonical aliases in faers_reader; parse manually
        import zipfile
        import io
        with zipfile.ZipFile(os.path.join(DATA_DIR, fname)) as zf:
            member = None
            for n in zf.namelist():
                b = os.path.basename(n).lower()
                if b.startswith("outc") and b.endswith(".txt"):
                    member = n
                    break
            if member is None:
                continue
            batch = []
            with zf.open(member) as f:
                text = io.TextIOWrapper(f, encoding="latin-1", errors="replace")
                header = None
                i_pid = i_cod = None
                for line in text:
                    line = line.rstrip("\r\n")
                    if not line:
                        continue
                    flds = line.split("$")
                    if header is None:
                        header = [x.strip().lower().lstrip("\ufeff")
                                  for x in flds]
                        continue
                    # header-driven: OUTC layouts vary (isr/primaryid in col 0,
                    # outc_cod last in some eras, third in others); resolve the
                    # columns by name instead of by position.
                    if i_pid is None or i_cod is None:
                        i_pid = next((k for k, h in enumerate(header)
                                      if h in ("primaryid", "isr")), None)
                        i_cod = next((k for k, h in enumerate(header)
                                      if h == "outc_cod"), None)
                    if i_pid is None or i_cod is None or len(flds) <= i_cod:
                        continue
                    pid = flds[i_pid].strip()
                    cod = flds[i_cod].strip().upper()
                    if pid and cod:
                        batch.append((pid, cod))
                    if len(batch) >= 20000:
                        cur.executemany("INSERT INTO outc VALUES (?,?)", batch)
                        batch = []
            if batch:
                cur.executemany("INSERT INTO outc VALUES (?,?)", batch)
        if qi % 15 == 0 or qi == len(quarters):
            print(f"  [{qi}/{len(quarters)}] {fname} ({time.time()-t0:.0f}s)",
                  flush=True)
    con.commit()
    cur.execute("CREATE INDEX IF NOT EXISTS idx_outc_pid ON outc(primaryid)")
    # restricted to the de-duplicated, non-deleted analysis set so that the
    # serious fraction has the right denominator
    cur.execute("DROP TABLE IF EXISTS serious")
    cur.execute("CREATE TABLE serious AS "
                "SELECT DISTINCT o.primaryid FROM outc o "
                "WHERE o.outc_cod IN ('DE','LT','HO','DS','CA','RI') "
                "  AND o.primaryid IN (SELECT primaryid FROM demo)")
    con.commit()
    n_outc = cur.execute("SELECT COUNT(*) FROM outc").fetchone()[0]
    n_ser = cur.execute("SELECT COUNT(*) FROM serious").fetchone()[0]
    n_demo = cur.execute("SELECT COUNT(*) FROM demo").fetchone()[0]
    print(f"\noutc rows: {n_outc:,} ; serious reports: {n_ser:,} "
          f"({100.0*n_ser/n_demo:.1f}% of {n_demo:,} cases)")
    print("outcome code distribution:")
    for cod, n in cur.execute("SELECT outc_cod, COUNT(*) AS n FROM outc "
                              "GROUP BY outc_cod ORDER BY n DESC LIMIT 12"):
        print(f"  {cod or '(blank)':<8} {n:>10,}")
    con.close()
    print(f"total time: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
