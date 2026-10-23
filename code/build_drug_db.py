"""build_drug_db.py — Stage 2 of the formal pipeline.

Builds the primary-suspect (PS) drug layer from all 90 quarterly archives:
  1. housekeeping: drop stage-1 intermediate tables, index demo(primaryid)
  2. stream DRUG rows, keep role_cod == 'PS', tag by quarter
  3. final drug_ps = PS rows whose primaryid survived demo dedup + deletion
     (FDA-standard: dedup first, then use the surviving report's records)
  4. drug_name_freq: distinct (drugname, prod_ai) frequency table — the input
     for the RxNorm + LLM normalization module

Usage:  python build_drug_db.py [data_dir] [db_path]
"""
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from faers_reader import iter_drug, quarter_of  # noqa: E402

DATA_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pilot", "data")
DB = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "faers.db")

DRUG_FIELDS = ["primaryid", "caseid", "drug_seq", "role_cod", "drugname",
               "prod_ai", "route", "dechal", "rechal"]


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

    # ---- housekeeping
    print("housekeeping: dropping stage-1 intermediates, indexing demo...", flush=True)
    cur.execute("DROP TABLE IF EXISTS demo_raw")
    cur.execute("DROP TABLE IF EXISTS demo_alive")
    cur.execute("DROP TABLE IF EXISTS drug_ps_raw")
    cur.execute("DROP TABLE IF EXISTS drug_ps")
    cur.execute("DROP TABLE IF EXISTS drug_name_freq")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_demo_pid ON demo(primaryid)")
    con.commit()

    cur.execute("""
        CREATE TABLE drug_ps_raw (
            quarter TEXT, primaryid TEXT, caseid TEXT, drug_seq TEXT,
            role_cod TEXT, drugname TEXT, prod_ai TEXT, route TEXT,
            dechal TEXT, rechal TEXT
        )
    """)

    # ---- ingest PS rows from all quarters
    role_counter = {}
    for qi, fname in enumerate(quarters, 1):
        y, q = quarter_of(fname)
        qtag = f"{y}Q{q}"
        path = os.path.join(DATA_DIR, fname)
        n = 0
        batch = []
        for rec in iter_drug(path):
            role = rec.get("role_cod", "").strip().upper()
            role_counter[role] = role_counter.get(role, 0) + 1
            if role != "PS":
                continue
            batch.append(tuple([qtag] + [rec.get(f, "") for f in DRUG_FIELDS]))
            n += 1
            if len(batch) >= 20000:
                cur.executemany("INSERT INTO drug_ps_raw VALUES ("
                                + ",".join("?" * 10) + ")", batch)
                batch = []
        if batch:
            cur.executemany("INSERT INTO drug_ps_raw VALUES ("
                            + ",".join("?" * 10) + ")", batch)
        if qi % 10 == 0 or qi == len(quarters):
            print(f"  [{qi}/{len(quarters)}] {qtag}: +{n} PS rows "
                  f"({time.time()-t0:.0f}s)", flush=True)
    con.commit()
    n_raw = cur.execute("SELECT COUNT(*) FROM drug_ps_raw").fetchone()[0]
    print(f"drug_ps_raw total: {n_raw:,} | role dist: {role_counter}", flush=True)

    # ---- keep only PS rows belonging to surviving (deduped) reports
    cur.execute("""
        CREATE TABLE drug_ps AS
        SELECT d.* FROM drug_ps_raw d
        WHERE d.primaryid IN (SELECT primaryid FROM demo)
    """)
    con.commit()
    n_final = cur.execute("SELECT COUNT(*) FROM drug_ps").fetchone()[0]
    print(f"drug_ps (alive reports only): {n_final:,}", flush=True)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_drugps_pid "
                "ON drug_ps(primaryid)")
    con.commit()

    # ---- drug name frequency table (normalization module input)
    cur.execute("""
        CREATE TABLE drug_name_freq AS
        SELECT UPPER(TRIM(drugname)) AS drugname_u,
               UPPER(TRIM(prod_ai)) AS prod_ai_u,
               COUNT(*) AS n_reports,
               COUNT(DISTINCT primaryid) AS n_cases
        FROM drug_ps
        GROUP BY drugname_u, prod_ai_u
    """)
    con.commit()
    n_names = cur.execute("SELECT COUNT(*) FROM drug_name_freq").fetchone()[0]
    print(f"distinct (drugname, prod_ai) pairs: {n_names:,}", flush=True)

    # coverage stats: how much volume do top names carry
    top = cur.execute("""
        SELECT drugname_u, prod_ai_u, n_cases FROM drug_name_freq
        ORDER BY n_cases DESC LIMIT 20
    """).fetchall()
    print("\ntop 20 PS drugs by case count:")
    for r in top:
        print(f"  {r[2]:>8,}  {r[0][:40]:<40} | {r[1][:40]}")

    con.close()
    print(f"\ntotal time: {time.time()-t0:.0f}s ; db: {DB}")


if __name__ == "__main__":
    main()
