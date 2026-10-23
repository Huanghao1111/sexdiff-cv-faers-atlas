"""stage7_sensitivity.py — Stage 7: pre-specified sensitivity analyses (v1 §5.3).

Layers (same 2x2 ROR_ratio engine as Stage 5, restricted universes):
  S1 physician-only   : universe restricted to occp_cod='MD' reports
  S2 serious-only     : universe restricted to reports in the serious table
  S4 era              : fda year <=2014 vs >=2015 (MedDRA/reporting-structure
                        change); S3 (primary-suspect-only) is satisfied by
                        design (drug_ps is role='PS' only); S5 (indication
                        stratification) deferred pending the LLM-module call.

Within-class (§5.3.6):
  S6a statin potency  : HIGH (atorvastatin/rosuvastatin + CADUET) vs LOW
                        (simvastatin/pravastatin/lovastatin/fluvastatin/
                        pitavastatin/cerivastatin + VYTORIN) vs CV-minus-STATIN
                        comparator; pre-defined muscle/hepatic/neuro events
                        + the statin candidate signal.
  S6b DOAC head-to-head: rivaroxaban/apixaban/edoxaban vs DABIGATRAN as
                        reference comparator; pre-defined bleeding/thrombotic
                        events (mirrors Anatol J Cardiol 2026 scope).

Outputs: stage7_layers.csv, stage7_within_class.csv
"""
import csv
import math
import os
import sqlite3
import time

import numpy as np

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "faers.db")
OUTDIR = os.path.dirname(os.path.abspath(__file__))
MIN_CELL = 5

STATIN_EVENTS = [
    "MYOPATHY", "MYALGIA", "MYOSITIS", "IMMUNE-MEDIATED MYOSITIS",
    "RHABDOMYOLYSIS", "PERIPHERAL SENSORY NEUROPATHY",
    "ALANINE AMINOTRANSFERASE INCREASED", "GYNAECOMASTIA",
]
DOAC_EVENTS = [
    "GASTROINTESTINAL HAEMORRHAGE", "HAEMORRHAGE INTRACRANIAL", "MELAENA",
    "HAEMATEMESIS", "EPISTAXIS", "ANAEMIA", "HAEMORRHAGE",
    "RECTAL HAEMORRHAGE", "ISCHAEMIC STROKE", "DEEP VEIN THROMBOSIS",
]
DOAC_AGENTS = ["RIVAROXABAN", "APIXABAN", "EDOXABAN"]


def ror_ratio(af, am, nf, nm, Af, Am, Nf_univ, Nm_univ):
    """2x2s + delta-method SE, identical to Stage 5.

    Af/Am = UNIVERSE reports with the PT; Nf_univ/Nm_univ = universe totals.
    The index set must be a subset of the universe: comparator cells are
    obtained by subtraction.
    """
    cf, cm = Af - af, Am - am
    Nf, Nm = Nf_univ - nf, Nm_univ - nm
    bf, bm = nf - af, nm - am
    df, dm = Nf - cf, Nm - cm
    if min(af, am, cf, cm, bf, bm, df, dm) < MIN_CELL:
        return None
    rf = (af / bf) / (cf / df)
    rm = (am / bm) / (cm / dm)
    ratio = rf / rm
    se = math.sqrt(sum(1.0 / x for x in (af, bf, cf, df, am, bm, cm, dm)))
    z = math.log(ratio) / se
    p = math.erfc(abs(z) / math.sqrt(2.0))
    return ratio, math.exp(math.log(ratio) - 1.96 * se), \
        math.exp(math.log(ratio) + 1.96 * se), p


def ror_ratio_ext(af, am, nf, nm, cf, cm, Nf_c, Nm_c):
    """Variant with an EXTERNALLY defined comparator (within-class analyses):
    cf/cm and Nf_c/Nm_c are the comparator's own PT counts and totals,
    used as-is (the index set is disjoint from the comparator by
    construction, so NOTHING is subtracted).
    """
    bf, bm = nf - af, nm - am
    df, dm = Nf_c - cf, Nm_c - cm
    if min(af, am, cf, cm, bf, bm, df, dm) < MIN_CELL:
        return None
    rf = (af / bf) / (cf / df)
    rm = (am / bm) / (cm / dm)
    ratio = rf / rm
    se = math.sqrt(sum(1.0 / x for x in (af, bf, cf, df, am, bm, cm, dm)))
    z = math.log(ratio) / se
    p = math.erfc(abs(z) / math.sqrt(2.0))
    return ratio, math.exp(math.log(ratio) - 1.96 * se), \
        math.exp(math.log(ratio) + 1.96 * se), p


def main():
    t0 = time.time()
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("PRAGMA temp_store=MEMORY")
    import sys
    sys.path.insert(0, OUTDIR)
    from drug_classes import CV_CLASSES
    qm = ",".join("?" * len(CV_CLASSES))
    cur.execute(f"CREATE TEMP TABLE cv AS SELECT DISTINCT primaryid "
                f"FROM report_class WHERE class IN ({qm})", tuple(CV_CLASSES))
    cur.execute("CREATE INDEX tmp_cv ON cv(primaryid)")

    # ---- shared arrays over the sex-known CV universe
    print("loading universe...", flush=True)
    pid, sex, md, yr = [], [], [], []
    for p, s, oc, fd in cur.execute(
            """SELECT d.primaryid, d.sex, d.occp_cod, d.fda_dt
               FROM demo d JOIN cv ON cv.primaryid=d.primaryid
               WHERE d.sex IN ('M','F')"""):
        pid.append(p)
        sex.append(1 if s == "F" else 0)
        md.append(1 if oc == "MD" else 0)
        yr.append(int(fd[:4]))
    pid = np.array(pid, np.int64)
    sex = np.array(sex, np.uint8)
    md = np.array(md, bool)
    yr = np.array(yr, np.int32)
    ser_set = {r[0] for r in cur.execute(
        "SELECT s.primaryid FROM serious s JOIN cv ON cv.primaryid=s.primaryid")}
    serious = np.isin(pid, list(ser_set))
    fem = sex == 1
    print(f"universe: {len(pid):,} ({time.time()-t0:.0f}s)", flush=True)

    # ---- signals (108 from stage6)
    sigs = []
    with open(os.path.join(OUTDIR, "stage6_adjusted.csv"),
              encoding="utf-8") as f:
        for r in csv.DictReader(f):
            sigs.append((r["class"], r["pt"], r["role"],
                         float(r["unadj_ratio"])))
    classes = sorted({c for c, _, _, _ in sigs})
    pts = sorted({p for _, p, _, _ in sigs})
    class_mask, pt_mask = {}, {}
    for c in classes:
        pids = np.array([r[0] for r in cur.execute(
            "SELECT DISTINCT primaryid FROM report_class WHERE class=?",
            (c,))], np.int64)
        class_mask[c] = np.isin(pid, pids)
    for pt in pts:
        pids = np.array([r[0] for r in cur.execute(
            "SELECT DISTINCT primaryid FROM reac WHERE pt=?", (pt,))],
            np.int64)
        pt_mask[pt] = np.isin(pid, pids)
    print(f"masks ready ({time.time()-t0:.0f}s)", flush=True)

    # ================= Part 1: restricted-universe layers =================
    layers = {
        "physician": md,
        "serious": serious,
        "era_pre2015": yr <= 2014,
        "era_post2015": yr >= 2015,
    }
    out1 = []
    for lname, lm in layers.items():
        Nf_univ = int((fem & lm).sum())
        Nm_univ = int((~fem & lm).sum())
        n_sig_kept = 0
        for c, pt, role, main_ratio in sigs:
            idx = class_mask[c] & lm
            ptm = pt_mask[pt] & lm
            af = int((idx & ptm & fem).sum())
            am = int((idx & ptm & ~fem).sum())
            nf = int((idx & fem).sum())
            nm = int((idx & ~fem).sum())
            Af = int((ptm & fem).sum())
            Am = int((ptm & ~fem).sum())
            res = ror_ratio(af, am, nf, nm, Af, Am, Nf_univ, Nm_univ)
            if res is None:
                continue
            ratio, lo, hi, p = res
            out1.append({
                "layer": lname, "class": c, "pt": pt, "role": role,
                "n_events": af + am,
                "ratio": f"{ratio:.6g}", "lo": f"{lo:.6g}", "hi": f"{hi:.6g}",
                "p": f"{p:.6g}", "main_ratio": f"{main_ratio:.6g}",
            })
            if p < 0.05:
                n_sig_kept += 1
        print(f"  layer {lname:<14} estimable {sum(1 for r in out1 if r['layer']==lname):>3}"
              f" ; p<0.05 {n_sig_kept} ({time.time()-t0:.0f}s)", flush=True)
    with open(os.path.join(OUTDIR, "stage7_layers.csv"), "w",
              encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out1[0].keys()))
        w.writeheader()
        w.writerows(out1)

    # ---- agent-level report sets from PS drug rows (single pass, substring
    # match on UPPERCASE "drugname | prod_ai" text; drug tokens are unique
    # enough that word-boundary regexes are unnecessary)
    TOKEN_SETS = {
        "statin_high": ("ATORVASTATIN", "LIPITOR", "ROSUVASTATIN", "CRESTOR",
                        "CADUET"),
        "statin_low": ("SIMVASTATIN", "ZOCOR", "PRAVASTATIN", "PRAVACHOL",
                       "LOVASTATIN", "MEVACOR", "ALTOPREV", "FLUVASTATIN",
                       "LESCOL", "PITAVASTATIN", "LIVALO", "ZYPITAMAG",
                       "CERIVASTATIN", "BAYCOL", "VYTORIN"),
        "DABIGATRAN": ("DABIGATRAN", "PRADAXA", "PRADAX"),
        "RIVAROXABAN": ("RIVAROXABAN", "XARELTO"),
        "APIXABAN": ("APIXABAN", "ELIQUIS"),
        "EDOXABAN": ("EDOXABAN", "SAVAYSA", "LIXIANA"),
    }
    sets = {k: set() for k in TOKEN_SETS}
    for dn, pa, p in cur.execute(
            "SELECT drugname, COALESCE(prod_ai,''), primaryid FROM drug_ps"):
        txt = f"{(dn or '').upper()} | {pa.upper()}"
        for k, toks in TOKEN_SETS.items():
            for tok in toks:
                if tok in txt:
                    sets[k].add(p)
                    break
    statin_high, statin_low = sets["statin_high"], sets["statin_low"]
    dabi = sets["DABIGATRAN"]
    print(f"agent sets: statin_high={len(statin_high):,} "
          f"statin_low={len(statin_low):,} dabigatran={len(dabi):,} "
          f"({time.time()-t0:.0f}s)", flush=True)

    # comparator = CV universe minus ANY statin report
    any_statin = statin_high | statin_low
    cmp_mask = ~np.isin(pid, list(any_statin))
    Nf_c = int((fem & cmp_mask).sum())
    Nm_c = int((~fem & cmp_mask).sum())

    out2 = []
    # high/low statin overlap (reports listing agents from both potency
    # groups) is excluded from both index sets so the contrast is clean
    hl_overlap = statin_high & statin_low
    for subgroup, pset in (("statin_high", statin_high - hl_overlap),
                           ("statin_low", statin_low - hl_overlap)):
        idxm = np.isin(pid, list(pset))
        for pt in STATIN_EVENTS:
            ptm = pt_mask.get(pt)
            if ptm is None:
                pids = np.array([r[0] for r in cur.execute(
                    "SELECT DISTINCT primaryid FROM reac WHERE pt=?", (pt,))],
                    np.int64)
                ptm = np.isin(pid, pids)
                pt_mask[pt] = ptm
            ptm_c = ptm & cmp_mask
            af = int((idxm & ptm & fem).sum())
            am = int((idxm & ptm & ~fem).sum())
            nf = int((idxm & fem).sum())
            nm = int((idxm & ~fem).sum())
            Af = int((ptm_c & fem).sum())
            Am = int((ptm_c & ~fem).sum())
            res = ror_ratio_ext(af, am, nf, nm, Af, Am, Nf_c, Nm_c)
            if res is None:
                continue
            ratio, lo, hi, p = res
            out2.append({
                "analysis": "statin_potency", "group": subgroup, "pt": pt,
                "n_events": af + am, "ratio": f"{ratio:.6g}",
                "lo": f"{lo:.6g}", "hi": f"{hi:.6g}", "p": f"{p:.6g}",
            })

    # ================= Part 3: DOAC head-to-head =================
    print(f"dabigatran reference pool: {len(dabi):,} reports "
          f"({time.time()-t0:.0f}s)", flush=True)
    for agent in DOAC_AGENTS:
        # reports listing BOTH agents are excluded from both arms so the
        # head-to-head contrast is mutually exclusive
        aset = sets[agent] - dabi
        dset = dabi - sets[agent]
        idxm = np.isin(pid, list(aset))
        dabi_m = np.isin(pid, list(dset))
        Nf_d = int((fem & dabi_m).sum())
        Nm_d = int((~fem & dabi_m).sum())
        print(f"  {agent}: index={len(aset):,} vs dabigatran={len(dset):,}",
              flush=True)
        for pt in DOAC_EVENTS:
            ptm = pt_mask.get(pt)
            if ptm is None:
                pids = np.array([r[0] for r in cur.execute(
                    "SELECT DISTINCT primaryid FROM reac WHERE pt=?", (pt,))],
                    np.int64)
                ptm = np.isin(pid, pids)
                pt_mask[pt] = ptm
            ptm_d = ptm & dabi_m
            af = int((idxm & ptm & fem).sum())
            am = int((idxm & ptm & ~fem).sum())
            nf = int((idxm & fem).sum())
            nm = int((idxm & ~fem).sum())
            Af = int((ptm_d & fem).sum())
            Am = int((ptm_d & ~fem).sum())
            res = ror_ratio_ext(af, am, nf, nm, Af, Am, Nf_d, Nm_d)
            if res is None:
                continue
            ratio, lo, hi, p = res
            out2.append({
                "analysis": "doac_vs_dabigatran", "group": agent, "pt": pt,
                "n_events": af + am, "ratio": f"{ratio:.6g}",
                "lo": f"{lo:.6g}", "hi": f"{hi:.6g}", "p": f"{p:.6g}",
            })

    with open(os.path.join(OUTDIR, "stage7_within_class.csv"), "w",
              encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out2[0].keys()))
        w.writeheader()
        w.writerows(out2)
    print(f"\nwritten: stage7_layers.csv ({len(out1)} rows), "
          f"stage7_within_class.csv ({len(out2)} rows)")
    print(f"total time: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
