"""audit_sample.py — draw the frozen 1,000-pair audit sample (protocol appendix v1.1).

Three strata over the 152,380 distinct (drugname_u, prod_ai_u) pairs in
drug_name_freq (built from all FAERS primary-suspect drug rows, 2004Q1-2026Q2):

  A  500 matched pairs, sampled with probability proportional to n_reports
     (covers the pairs that carry the CV universe's exposure)
  B  200 matched pairs, uniform over the matched pairs not drawn in A
     (tail coverage: rare pairs where dictionary errors hide)
  C  300 unmatched pairs, sampled with probability proportional to n_reports
     (false-negative screen: reports currently excluded from the CV universe
     whose names may in fact be cardiovascular drugs)

Seed frozen at 20261016. Outputs:
  audit_sample_1000.csv      blind sample (no dictionary labels)
  audit_sample_1000_KEY.csv  sealed key (dictionary classes) - do not open
                             until audit_llm_labels.csv is locked
"""
import csv
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 20261016
N_A, N_B, N_C = 500, 200, 300


def main():
    # ---- dictionary labels (pair -> class set)
    pair2cls = {}
    with open(os.path.join(HERE, "name_class.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (r["drugname_u"], r["prod_ai_u"])
            pair2cls.setdefault(key, set()).add(r["class"])

    # ---- universe of pairs with frequencies
    import sqlite3
    con = sqlite3.connect(os.path.join(HERE, "faers.db"))
    pairs = con.execute(
        "SELECT drugname_u, prod_ai_u, n_reports FROM drug_name_freq").fetchall()
    con.close()

    matched, unmatched = [], []
    for dn, ai, n in pairs:
        key = (dn, ai)
        (matched if key in pair2cls else unmatched).append((dn, ai, int(n)))
    print(f"distinct pairs: {len(pairs):,}  matched: {len(matched):,}  "
          f"unmatched: {len(unmatched):,}")

    rng = random.Random(SEED)

    def pps(pool, k):
        """probability-proportional-to-size without replacement (sequential)."""
        pool = pool[:]
        out = []
        for _ in range(min(k, len(pool))):
            tot = sum(p[2] for p in pool)
            x = rng.uniform(0, tot)
            acc = 0.0
            for i, p in enumerate(pool):
                acc += p[2]
                if x <= acc:
                    out.append(pool.pop(i))
                    break
        return out

    samp_a = pps(matched, N_A)
    rest = [p for p in matched if p not in set((q[0], q[1], q[2]) for q in samp_a)]
    samp_b = rng.sample(rest, min(N_B, len(rest)))
    samp_c = pps(unmatched, N_C)

    rows, key = [], []
    sid = 0
    for stratum, samp in (("A", samp_a), ("B", samp_b), ("C", samp_c)):
        for dn, ai, n in samp:
            sid += 1
            rows.append({"sample_id": sid, "stratum": stratum,
                         "drugname_u": dn, "prod_ai_u": ai, "n_reports": n})
            cls = pair2cls.get((dn, ai))
            key.append({"sample_id": sid,
                        "dict_classes": "|".join(sorted(cls)) if cls else "UNMATCHED"})

    rng.shuffle(rows)  # break stratum ordering in the blind file
    order = {r["sample_id"]: i for i, r in enumerate(rows)}
    key.sort(key=lambda r: order[r["sample_id"]])

    with open(os.path.join(HERE, "audit_sample_1000.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["sample_id", "stratum", "drugname_u",
                                          "prod_ai_u", "n_reports"])
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(HERE, "audit_sample_1000_KEY.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["sample_id", "dict_classes"])
        w.writeheader()
        w.writerows(key)

    n_um = sum(1 for k in key if k["dict_classes"] == "UNMATCHED")
    print(f"sample: {len(rows)} rows ({N_A} A / {len(samp_b)} B / {len(samp_c)} C); "
          f"key sealed, {n_um} UNMATCHED in key")
    print(f"report coverage of sample: {sum(r['n_reports'] for r in rows):,} reports")


if __name__ == "__main__":
    main()
