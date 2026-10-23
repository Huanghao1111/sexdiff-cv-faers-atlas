"""stage6_regression.py — Stage 6: case-centered multivariable adjustment.

Protocol v1 §5.2. For each of the 106 curated candidate signals (class x PT):

    outcome : does the report contain the PT (binary, report level)
    cohort  : the sex-known CV universe (same 2,190,818 reports as Stage 5)
    model   : logit P(PT) = sex + index(class) + sex*index
                            + age_band + report_year + reporter + serious

  exp(b_sex*index) = adjusted sex interaction (adjusted analogue of the
  Stage-5 ROR_ratio): the female-vs-male disproportionality of the event
  for the index class RELATIVE to the rest of cardiovascular pharmacotherapy,
  adjusted for age band, report year, reporter type and seriousness.

All predictors are categorical, so the MLE is computed exactly on aggregated
cell counts (grouped-data logistic regression with frequency weights) —
mathematically identical to fitting 2.19M individual rows, ~1000x faster.

Age is normalised to years (age_cod YR/DEC/MON/WK/DY/HR; implausible values
outside 0-120 set to missing). Bands: <45 / 45-64 (ref) / 65-74 / >=75 /
missing. Report year from fda_dt: <=2009 pooled, then single years
2010..2026 (ref 2015). Reporter: MD (ref) / CN / other-health(PH,HP,RN) /
OT / LW / missing. Serious: membership of the serious table.

Exploratory menopause-proxy strata (protocol): the same model refitted on
reports with known age <55 and >=55 (age-band dummies that are empty within
a stratum are dropped automatically).

Output: stage6_adjusted.csv  (one row per candidate signal)
"""
import csv
import math
import os
import sqlite3
import sys
import time

import numpy as np

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "faers.db")
OUTDIR = os.path.dirname(os.path.abspath(__file__))
CAND = os.path.join(OUTDIR, "table2_top_signals.csv")
OUT = os.path.join(OUTDIR, "stage6_adjusted.csv")

AGE_BANDS = ["<45", "45-64", "65-74", ">=75", "missing"]
YEARS = ["<=2009"] + [str(y) for y in range(2010, 2027)]   # ref = "2015"
REPORTERS = ["MD", "CN", "HP", "OT", "LW", "missing"]     # ref = "MD"
ONLY_SIGNALS = None   # e.g. [("ACEI","COUGH")] for a quick test

# Protocol v1 §5.4 positive controls: clean, mechanism-established
# sex-differential associations the pipeline MUST recover.
POS_CONTROLS = [
    ("ACEI", "COUGH"),
    ("DIGOXIN", "TOXICITY TO VARIOUS AGENTS"),
]


def norm_age(age, cod):
    try:
        a = float(age)
    except (TypeError, ValueError):
        return np.nan
    if cod == "DEC":
        a *= 10.0
    elif cod == "MON":
        a /= 12.0
    elif cod == "WK":
        a /= 52.0
    elif cod in ("DY", "HR"):
        a = 0.0
    # YR or blank: assume years
    return a if 0.0 <= a <= 120.0 else np.nan


def age_band(a):
    if a != a:                      # NaN
        return 4
    if a < 45:
        return 0
    if a < 65:
        return 1
    if a < 75:
        return 2
    return 3


def year_bin(fda_dt):
    y = int(fda_dt[:4])
    if y < 2010:
        return 0
    return min(y - 2009, 17)        # 2010->1 ... 2026->17


def reporter_cat(occp):
    if occp == "MD":
        return 0
    if occp == "CN":
        return 1
    if occp in ("PH", "HP", "RN"):
        return 2
    if occp == "OT":
        return 3
    if occp == "LW":
        return 4
    return 5


def fit_grouped_logit(keys, has_pt):
    """Exact MLE for the categorical model via cell aggregation.

    keys: (n,) uint32 packed [sex, index, ageb(3b), yearb(5b), rep(3b), serious(1b)]
    has_pt: (n,) bool outcome
    Model: 1 + sex + index + sex*index + C(ageb, ref 45-64) + C(yearb, ref 2015)
           + C(rep, ref MD) + serious
    Aggregating identical covariate patterns with frequency weights gives the
    same MLE as row-level fitting (sufficiency of grouped data for discrete
    predictors). Convergence is judged on the stability of the interaction
    coefficient (the estimand); separated year/reporter dummies may keep
    drifting without affecting it.
    Returns (beta_int, se_int, stable).
    """
    both = (keys.astype(np.uint64) << 1) | has_pt.astype(np.uint64)
    uniq, cnt = np.unique(both, return_counts=True)
    cell = uniq >> 1
    is1 = (uniq & 1).astype(bool)
    cells, inv = np.unique(cell, return_inverse=True)
    n1 = np.zeros(len(cells))
    y1 = np.zeros(len(cells))
    np.add.at(n1, inv, cnt)
    np.add.at(y1, inv[is1], cnt[is1])

    s = (cells & 1).astype(float)
    i = ((cells >> 1) & 1).astype(float)
    a = (cells >> 2) & 7
    yb = (cells >> 3) & 31
    r = (cells >> 8) & 7
    z = ((cells >> 11) & 1).astype(float)

    cols = [np.ones_like(s), s, i, s * i]
    names = ["const", "sexF", "index", "sexF:index"]
    for lv in (0, 2, 3, 4):                     # ageb ref=1 (45-64)
        cols.append((a == lv).astype(float))
        names.append(f"ageb{lv}")
    for lv in list(range(0, 6)) + list(range(7, 18)):   # year ref=6 (2015)
        cols.append((yb == lv).astype(float))
        names.append(f"year{lv}")
    for lv in (1, 2, 3, 4, 5):                  # reporter ref=0 (MD)
        cols.append((r == lv).astype(float))
        names.append(f"rep{lv}")
    cols.append(z)
    names.append("serious")

    X = np.column_stack(cols)
    keep = [k for k in range(X.shape[1]) if k == 0 or X[:, k].any()]
    X = X[:, keep]
    names = [names[k] for k in keep]
    j = names.index("sexF:index")

    beta = np.zeros(X.shape[1])
    stable = False
    last_int = None
    same = 0
    for _ in range(80):
        eta = np.clip(X @ beta, -30, 30)
        mu = 1.0 / (1.0 + np.exp(-eta))
        W = n1 * mu * (1.0 - mu)
        g = X.T @ (y1 - n1 * mu)
        H = (X.T * W) @ X
        try:
            step = np.linalg.solve(H + 1e-10 * np.eye(H.shape[0]), g)
        except np.linalg.LinAlgError:
            break
        # step-halving on the grouped log-likelihood
        def ll(b):
            e = np.clip(X @ b, -30, 30)
            return float(np.sum(y1 * e - n1 * np.log1p(np.exp(e))))
        ll_old = ll(beta)
        bn = beta + step
        halv = 0
        while ll(bn) < ll_old and halv < 40:
            step *= 0.5
            bn = beta + step
            halv += 1
        beta = bn
        if last_int is not None and abs(beta[j] - last_int) < 1e-9:
            same += 1
            if same >= 5:
                stable = True
                break
        else:
            same = 0
        last_int = beta[j]

    eta = np.clip(X @ beta, -30, 30)
    mu = 1.0 / (1.0 + np.exp(-eta))
    W = n1 * mu * (1.0 - mu)
    H = (X.T * W) @ X
    cov = np.linalg.pinv(H)
    se = math.sqrt(max(cov[j, j], 0.0))
    return beta[j], se, stable


def main():
    t0 = time.time()
    # ---- candidates (same filter as verify_stage5) + forced positive controls
    cand = []
    with open(CAND, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r["src_concentrated"] != "YES"
                    and r.get("indication_coded") != "YES"
                    and not r.get("manual_flag")
                    and int(r["a_f"]) + int(r["a_m"]) >= 100):
                r["role"] = "candidate"
                cand.append(r)
    # Positive controls are force-included even when they fall outside the
    # per-class top-10 selection (the pipeline must demonstrate it recovers
    # them after adjustment — protocol v1 §5.4).
    present = {(r["class"], r["pt"]) for r in cand}
    with open(os.path.join(OUTDIR, "sexdiff_tests_filtered.csv"),
              encoding="utf-8") as f:
        pc_lookup = {(r["class"], r["pt"]): r for r in csv.DictReader(f)}
    for key in POS_CONTROLS:
        if key not in present and key in pc_lookup:
            r = dict(pc_lookup[key])
            r["role"] = "positive_control"
            cand.append(r)
    if ONLY_SIGNALS:
        cand = [r for r in cand if (r["class"], r["pt"]) in ONLY_SIGNALS]
    print(f"signals to fit: {len(cand)} "
          f"(incl. {sum(1 for r in cand if r['role']!='candidate')} "
          f"positive controls)", flush=True)

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("PRAGMA temp_store=MEMORY")
    from drug_classes import CV_CLASSES
    qm = ",".join("?" * len(CV_CLASSES))
    cur.execute(f"CREATE TEMP TABLE cv AS SELECT DISTINCT primaryid "
                f"FROM report_class WHERE class IN ({qm})", tuple(CV_CLASSES))
    cur.execute("CREATE INDEX tmp_cv ON cv(primaryid)")

    # ---- covariate frame for the sex-known CV universe
    print("loading covariate frame...", flush=True)
    pid, sex, ageb, ybin, rep, agey = [], [], [], [], [], []
    for p, s, a, ac, fd, oc in cur.execute(
            """SELECT d.primaryid, d.sex, d.age, d.age_cod, d.fda_dt, d.occp_cod
               FROM demo d JOIN cv ON cv.primaryid = d.primaryid
               WHERE d.sex IN ('M','F')"""):
        pid.append(p)
        sex.append(1 if s == "F" else 0)
        ay = norm_age(a, ac)
        agey.append(ay)
        ageb.append(age_band(ay))
        ybin.append(year_bin(fd))
        rep.append(reporter_cat(oc))
    pid = np.array(pid, np.int64)
    sex = np.array(sex, np.uint8)
    ageb = np.array(ageb, np.uint8)
    ybin = np.array(ybin, np.uint8)
    rep = np.array(rep, np.uint8)
    agey = np.array(agey, np.float32)
    n_rep = len(pid)
    print(f"sex-known CV reports: {n_rep:,} ({time.time()-t0:.0f}s)", flush=True)

    ser_set = {r[0] for r in cur.execute(
        "SELECT s.primaryid FROM serious s JOIN cv ON cv.primaryid=s.primaryid")}
    serious = np.isin(pid, list(ser_set)).astype(np.uint8)
    print(f"serious: {serious.sum():,} ({time.time()-t0:.0f}s)", flush=True)

    pid_pos = {p: k for k, p in enumerate(pid)}

    # class membership sets (only classes that appear among candidates)
    classes_needed = sorted({r["class"] for r in cand})
    class_mask = {}
    for c in classes_needed:
        pids = np.array([r[0] for r in cur.execute(
            "SELECT DISTINCT primaryid FROM report_class WHERE class=?",
            (c,))], np.int64)
        m = np.isin(pid, pids)
        class_mask[c] = m
    print(f"class masks built for {len(classes_needed)} classes "
          f"({time.time()-t0:.0f}s)", flush=True)

    # PT membership sets (distinct PTs among candidates)
    pts_needed = sorted({r["pt"] for r in cand})
    pt_mask = {}
    for pt in pts_needed:
        pids = np.array([r[0] for r in cur.execute(
            "SELECT DISTINCT primaryid FROM reac WHERE pt=?", (pt,))],
            np.int64)
        pt_mask[pt] = np.isin(pid, pids)
    print(f"PT masks built for {len(pts_needed)} PTs ({time.time()-t0:.0f}s)",
          flush=True)

    def run_model(mask_extra=None):
        """Fit for current signal. mask_extra: optional bool array subset."""
        keys = (sex.astype(np.uint32)
                | (idx.astype(np.uint32) << 1)
                | (ageb.astype(np.uint32) << 2)
                | (ybin.astype(np.uint32) << 3)
                | (rep.astype(np.uint32) << 8)
                | (serious.astype(np.uint32) << 11))
        y = has_pt.astype(bool)
        if mask_extra is not None:
            keys, y = keys[mask_extra], y[mask_extra]
        b, s_, stable = fit_grouped_logit(keys, y)
        z = b / s_ if s_ > 0 else float("nan")
        p = math.erfc(abs(z) / math.sqrt(2.0)) if s_ > 0 else float("nan")
        return b, s_, z, p, stable

    results = []
    u55 = agey < 55                       # menopause-proxy strata (known age)
    o55 = agey >= 55
    for k, row in enumerate(cand):
        c, pt = row["class"], row["pt"]
        idx = class_mask[c]
        has_pt = pt_mask[pt]
        b, s_, z, p, conv = run_model()
        bu, _, _, pu, cu = run_model(u55)
        bo, _, _, po, co = run_model(o55)
        results.append({
            "class": c, "pt": pt, "role": row["role"],
            "unadj_ratio": row["ROR_ratio"], "unadj_q": row["q"],
            "adj_logratio": f"{b:.6g}", "adj_se": f"{s_:.6g}",
            "adj_ratio": f"{math.exp(b):.6g}",
            "adj_lo": f"{math.exp(b - 1.96 * s_):.6g}",
            "adj_hi": f"{math.exp(b + 1.96 * s_):.6g}",
            "adj_z": f"{z:.6g}", "adj_p": f"{p:.6g}",
            "ratio_u55": f"{math.exp(bu):.6g}" if cu else "",
            "p_u55": f"{pu:.6g}" if cu else "",
            "ratio_o55": f"{math.exp(bo):.6g}" if co else "",
            "p_o55": f"{po:.6g}" if co else "",
            "converged": "yes" if conv else "NO",
        })
        if (k + 1) % 10 == 0:
            print(f"  {k+1}/{len(cand)} fitted ({time.time()-t0:.0f}s)",
                  flush=True)

    # BH over adjusted p (candidate signals only; positive controls are not
    # part of the discovery pool and are reported with raw adjusted p)
    cand_idx = [i for i, r in enumerate(results) if r["role"] == "candidate"]
    ps = [float(results[i]["adj_p"]) for i in cand_idx]
    order = sorted(range(len(ps)), key=lambda k: ps[k])
    prev = 1.0
    n = len(ps)
    q = [0.0] * n
    for rank in range(n - 1, -1, -1):
        i = order[rank]
        prev = min(prev, ps[i] * n / (rank + 1))
        q[i] = min(prev, 1.0)
    for r in results:
        r["adj_q"] = ""
    for k, i in enumerate(cand_idx):
        results[i]["adj_q"] = f"{q[k]:.6g}"

    cols = ["class", "pt", "role", "unadj_ratio", "unadj_q", "adj_ratio",
            "adj_lo", "adj_hi", "adj_logratio", "adj_se", "adj_z", "adj_p",
            "adj_q", "ratio_u55", "p_u55", "ratio_o55", "p_o55", "converged"]
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(results)
    n_sig = sum(1 for r in results
                if r["role"] == "candidate" and float(r["adj_q"]) < 0.05)
    n_conv = sum(1 for r in results if r["converged"] == "yes")
    print(f"\nwritten: {OUT}")
    print(f"converged: {n_conv}/{len(results)} ; "
          f"adjusted q<0.05 (candidates): {n_sig}/{len(cand_idx)}")
    print(f"total time: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
