"""build_reac_db.py — Stage 3 of the formal pipeline.

Builds the reaction (MedDRA PT) layer from all 90 quarterly archives:
  1. stream REAC rows, tag by quarter
  2. keep only rows whose primaryid survived demo dedup + deletion
  3. pt_freq: distinct PT frequency table (signal-scan coverage stats)

Usage:  python build_reac_db.py [data_dir] [db_path]
"""
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from faers_reader import iter_reac, quarter_of  # noqa: E402

DATA_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pilot", "data")
DB = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "faers.db")


def quarter_list(data_dir):
    zips = [f for f in os.listdir(data_dir) if f.endswith(".zip")
            and ("ascii" in f.lower())]
    return sorted(zips, key=quarter_of)


def main():
    t0 = time.time()
    quarters = quarter_list(DATA_DIR)
    print(f"quarters: {len(quarters)}", flush=True)

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS reac_raw")
    cur.execute("DROP TABLE IF EXISTS reac")
    cur.execute("DROP TABLE IF EXISTS pt_freq")
    cur.execute("""
        CREATE TABLE reac_raw (
            quarter TEXT, primaryid TEXT, caseid TEXT, pt TEXT,
            drug_rec_act TEXT
        )
    """)

    for qi, fname in enumerate(quarters, 1):
        y, q = quarter_of(fname)
        qtag = f"{y}Q{q}"
        path = os.path.join(DATA_DIR, fname)
        n = 0
        batch = []
        for rec in iter_reac(path):
            batch.append((qtag, rec.get("primaryid", ""), rec.get("caseid", ""),
                          rec.get("pt", "").strip(), rec.get("drug_rec_act", "")))
            n += 1
            if len(batch) >= 20000:
                cur.executemany("INSERT INTO reac_raw VALUES (?,?,?,?,?)", batch)
                batch = []
        if batch:
            cur.executemany("INSERT INTO reac_raw VALUES (?,?,?,?,?)", batch)
        if qi % 10 == 0 or qi == len(quarters):
            print(f"  [{qi}/{len(quarters)}] {qtag}: +{n} rows "
                  f"({time.time()-t0:.0f}s)", flush=True)
    con.commit()
    n_raw = cur.execute("SELECT COUNT(*) FROM reac_raw").fetchone()[0]
    print(f"reac_raw total: {n_raw:,}", flush=True)

    # Canonical report x PT layer.
    # MedDRA PTs are stored with inconsistent casing across FAERS eras
    # ("Dizziness" vs "DIZZINESS"): 39,689 raw strings collapse to 25,092
    # canonical PTs. Leaving them split halves every event count, breaks the
    # >=5 cell rule and doubles the multiplicity of the BH-FDR pool, so PTs
    # are upper-cased here, once, at the source.
    cur.execute("""
        CREATE TABLE reac AS
        SELECT DISTINCT r.primaryid AS primaryid,
               TRIM(UPPER(r.pt)) AS pt
        FROM reac_raw r
        WHERE r.primaryid IN (SELECT primaryid FROM demo)
          AND TRIM(r.pt) <> ''
    """)
    con.commit()
    n_final = cur.execute("SELECT COUNT(*) FROM reac").fetchone()[0]
    n_cases = cur.execute(
        "SELECT COUNT(DISTINCT primaryid) FROM reac").fetchone()[0]
    print(f"reac (alive reports only): {n_final:,} rows, "
          f"{n_cases:,} reports", flush=True)

    # PT frequency + case coverage
    cur.execute("""
        CREATE TABLE pt_freq AS
        SELECT pt, COUNT(*) AS n_rows, COUNT(DISTINCT primaryid) AS n_cases
        FROM reac GROUP BY pt
    """)
    con.commit()
    cur.execute("CREATE INDEX idx_reac_pt ON reac(pt)")
    con.commit()
    cur.execute("CREATE INDEX idx_reac_pid ON reac(primaryid)")
    con.commit()
    n_pt = cur.execute("SELECT COUNT(*) FROM pt_freq").fetchone()[0]
    print(f"distinct PTs: {n_pt:,}", flush=True)

    print("\ntop 15 PTs by case count:")
    for r in cur.execute("SELECT pt, n_cases FROM pt_freq "
                         "ORDER BY n_cases DESC LIMIT 15"):
        print(f"  {r[1]:>9,}  {r[0]}")

    # positive-control spot checks (known class-level signals)
    print("\npositive-control PT spot checks (cases):")
    for pt in ["MYOPATHY", "RHABDOMYOLYSIS", "IMMUNE-MEDIATED MYOSITIS",
               "CARDIAC FAILURE", "ATRIAL FIBRILLATION",
               "TORSADE DE POINTES", "NAUSEA"]:
        r = cur.execute("SELECT n_cases FROM pt_freq WHERE pt = ?", (pt,)).fetchone()
        print(f"  {pt:<28} {r[0] if r else 0:>9,}")

    con.close()
    print(f"\ntotal time: {time.time()-t0:.0f}s ; db: {DB}")


if __name__ == "__main__":
    main()
