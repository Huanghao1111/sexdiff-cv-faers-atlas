"""build_demo_db.py — Stage 1 of the formal pipeline.

Builds the case-level (DEMO) layer from all 90 quarterly archives:
  1. stream DEMO rows into SQLite (raw layer, tagged by quarter)
  2. apply FDA deleted-cases lists (primaryid level)
  3. global de-duplication: per caseid keep the row with the highest
     caseversion; ties broken by latest fda_dt, then highest primaryid
  4. descriptive statistics (Table 1 material): cases by year x sex,
     era counts, missingness

Usage:  python build_demo_db.py [data_dir] [out_db]
"""
import os
import sqlite3
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from faers_reader import iter_demo, iter_deleted, quarter_of  # noqa: E402

DATA_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pilot", "data")
OUT_DB = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "faers.db")

CANON_FIELDS = ["primaryid", "caseid", "caseversion", "sex", "age", "age_cod",
                "age_grp", "event_dt", "fda_dt", "rept_dt", "rept_cod",
                "occp_cod", "reporter_country", "init_fda_dt"]


def quarter_list(data_dir):
    zips = [f for f in os.listdir(data_dir) if f.endswith(".zip")
            and ("ascii" in f.lower())]
    return sorted(zips, key=quarter_of)


def main():
    t0 = time.time()
    quarters = quarter_list(DATA_DIR)
    print(f"quarters found: {len(quarters)} "
          f"({quarters[0]} .. {quarters[-1]})", flush=True)

    if os.path.exists(OUT_DB):
        os.remove(OUT_DB)
    con = sqlite3.connect(OUT_DB)
    cur = con.cursor()
    cur.executescript("""
    CREATE TABLE demo_raw (
        quarter TEXT, primaryid TEXT, caseid TEXT, caseversion TEXT,
        sex TEXT, age TEXT, age_cod TEXT, age_grp TEXT, event_dt TEXT,
        fda_dt TEXT, rept_dt TEXT, rept_cod TEXT, occp_cod TEXT,
        reporter_country TEXT, init_fda_dt TEXT
    );
    CREATE TABLE deleted (id TEXT);
    """)

    qc_log = []  # per-quarter QC
    for qi, fname in enumerate(quarters, 1):
        y, q = quarter_of(fname)
        qtag = f"{y}Q{q}"
        path = os.path.join(DATA_DIR, fname)
        n = 0
        batch = []
        for rec in iter_demo(path):
            batch.append(tuple([qtag] + [rec.get(f, "") for f in CANON_FIELDS]))
            n += 1
            if len(batch) >= 20000:
                cur.executemany(
                    "INSERT INTO demo_raw VALUES ("
                    + ",".join("?" * 15) + ")", batch)
                batch = []
        if batch:
            cur.executemany("INSERT INTO demo_raw VALUES ("
                            + ",".join("?" * 15) + ")", batch)
        ndel = 0
        for rec in iter_deleted(path):
            cur.execute("INSERT INTO deleted VALUES (?)", (rec["primaryid"],))
            ndel += 1
        qc_log.append((qtag, n, ndel))
        if qi % 10 == 0 or qi == len(quarters):
            print(f"  [{qi}/{len(quarters)}] {qtag}: {n} demo rows, "
                  f"{ndel} deleted-case ids  ({time.time()-t0:.0f}s)", flush=True)
    con.commit()

    # ---- QC table persisted
    cur.execute("CREATE TABLE qc_quarter (quarter TEXT, demo_rows INT, deleted_ids INT)")
    cur.executemany("INSERT INTO qc_quarter VALUES (?,?,?)", qc_log)
    con.commit()

    # ---- FDA deleted-cases removal.
    # Verified 2026-10-14: the ADR*DeletedCases / DELETE* lists store CASEIDs
    # for the FAERS era (delid == caseid; primaryids are caseid*10+version)
    # and AERS-era ISRs (= our primaryid) for older cases. Matching is therefore
    # era-specific: AERS rows are matched on primaryid, FAERS rows on caseid.
    # (Blindly matching BOTH channels — as v1 did — let 7-digit AERS deletion
    # IDs delete unrelated FAERS cases whose caseid happened to be identical.)
    cur.execute("CREATE INDEX idx_deleted_id ON deleted(id)")
    con.commit()
    cur.execute("""
        CREATE TABLE demo_alive AS
        SELECT r.* FROM demo_raw r
        WHERE NOT EXISTS (
            SELECT 1 FROM deleted d
            WHERE d.id = CASE WHEN r.quarter <= '2012Q3'
                              THEN r.primaryid ELSE r.caseid END
        )
    """)
    con.commit()
    n_raw = cur.execute("SELECT COUNT(*) FROM demo_raw").fetchone()[0]
    n_del = cur.execute("SELECT COUNT(*) FROM deleted").fetchone()[0]
    n_alive = cur.execute("SELECT COUNT(*) FROM demo_alive").fetchone()[0]

    # ---- global dedup: per caseid keep the highest caseversion, then the
    #      latest fda_dt, then the highest primaryid (protocol v1 §4.2).
    # Implemented with ROW_NUMBER so the tie-break is explicit. The previous
    # two-step MAX(bestkey) + MIN(rowid) version silently collapsed to
    # "earliest inserted row" for the AERS era, where caseversion is empty and
    # the composite key degenerated to fda_dt alone — i.e. it kept the OLDEST
    # version of a case, the opposite of what the protocol states.
    cur.execute("""
        CREATE TABLE demo_dedup_case AS
        SELECT quarter, primaryid, caseid, caseversion, sex, age, age_cod,
               age_grp, event_dt, fda_dt, rept_dt, rept_cod, occp_cod,
               reporter_country, init_fda_dt
        FROM (
            SELECT a.*,
                   ROW_NUMBER() OVER (
                       PARTITION BY a.caseid
                       ORDER BY CAST(a.caseversion AS INTEGER) DESC,
                                COALESCE(CAST(a.fda_dt AS INTEGER), 0) DESC,
                                CAST(a.primaryid AS INTEGER) DESC
                   ) AS rn
            FROM demo_alive a
        ) WHERE rn = 1
    """)
    con.commit()
    # AERS-era ISRs are occasionally shared by two different CASE numbers
    # (1,787 primaryids in this extract). Keep one row per primaryid so that
    # demo is strictly one-row-per-report and COUNT(*) == COUNT(DISTINCT
    # primaryid) everywhere downstream.
    cur.execute("""
        CREATE TABLE demo AS
        SELECT quarter, primaryid, caseid, caseversion, sex, age, age_cod,
               age_grp, event_dt, fda_dt, rept_dt, rept_cod, occp_cod,
               reporter_country, init_fda_dt
        FROM (
            SELECT a.*,
                   ROW_NUMBER() OVER (
                       PARTITION BY a.primaryid
                       ORDER BY COALESCE(CAST(a.fda_dt AS INTEGER), 0) DESC,
                                CAST(a.caseversion AS INTEGER) DESC
                   ) AS rn
            FROM demo_dedup_case a
        ) WHERE rn = 1
    """)
    con.commit()
    cur.execute("DROP TABLE demo_dedup_case")
    con.commit()
    n_final = cur.execute("SELECT COUNT(*) FROM demo").fetchone()[0]
    n_pid = cur.execute(
        "SELECT COUNT(DISTINCT primaryid) FROM demo").fetchone()[0]
    print(f"final unique cases   : {n_final:,} (distinct primaryid: {n_pid:,})",
          flush=True)

    # ---- stats: year x sex (Table 1 material)
    print("\n=== SUMMARY ===")
    print(f"demo_raw rows        : {n_raw:,}")
    print(f"deleted-case ids     : {n_del:,}")
    print(f"after delete removal : {n_alive:,}")
    print(f"final unique cases   : {n_final:,}")

    rows = cur.execute("""
        SELECT substr(fda_dt, 1, 4) AS yr, sex, COUNT(*)
        FROM demo
        GROUP BY yr, sex ORDER BY yr, sex
    """).fetchall()
    year_sex = {}
    for yr, sex, n in rows:
        year_sex.setdefault(yr, Counter())[sex] = n

    stats_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "demo_stats_year_sex.csv")
    with open(stats_path, "w", encoding="utf-8") as f:
        f.write("year,M,F,missing_or_other,total,perc_female_of_known\n")
        for yr in sorted(year_sex):
            c = year_sex[yr]
            tot = sum(c.values())
            mf = c.get("M", 0) + c.get("F", 0)
            pf = 100.0 * c.get("F", 0) / mf if mf else float("nan")
            f.write(f"{yr},{c.get('M',0)},{c.get('F',0)},"
                    f"{tot - mf},{tot},{pf:.1f}\n")
    print(f"\nyear x sex table written: {stats_path}")

    tot_c = Counter()
    for c in year_sex.values():
        tot_c.update(c)
    mf = tot_c.get("M", 0) + tot_c.get("F", 0)
    print(f"overall: M={tot_c.get('M',0):,} F={tot_c.get('F',0):,} "
          f"other/missing={n_final - mf:,} "
          f"({100.0*(n_final-mf)/n_final:.1f}%) female share of sex-known="
          f"{100.0*tot_c.get('F',0)/mf:.1f}%")

    con.close()
    print(f"\ntotal time: {time.time()-t0:.0f}s ; db: {OUT_DB}")


if __name__ == "__main__":
    main()
