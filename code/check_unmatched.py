"""check_unmatched.py — for each candidate token, how many reports are ALREADY
classified vs. still unmatched under the frozen dictionary v1.

Usage: python check_unmatched.py
"""
import os
import re
import sqlite3

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "faers.db")

TOKENS = [
    # renin inhibitor
    "ALISKIREN", "TEKTURNA", "RASILEZ", "VALTURNA", "AMTURNIDE",
    # alpha split
    "TAMSULOSIN", "FLOMAX", "ALFUZOSIN", "UROXATRAL", "SILODOSIN", "RAPAFLO",
    "DUODART", "JALYN", "DOXAZOSIN", "TERAZOSIN", "PRAZOSIN",
    # PDE5
    "SILDENAFIL", "TADALAFIL", "VARDENAFIL", "AVANAFIL", "VIAGRA", "CIALIS",
    "LEVITRA", "STAXYN", "STENDRA", "SPEDRA",
    # thiazide
    "HCTZ", "HYDROCHLOROTHIAZID", "MICROZIDE",
    # lipid combos
    "VYTORIN", "CADUET", "NEXLIZET",
    # diabetes combos
    "JANUMET", "XIGDUO", "SYNJARDY", "INVOKAMET", "GLYXAMBI", "QTERN",
    "SEGLUROMET", "STEGLUJAN", "JENTADUETO", "KOMBIGLYZE", "TRIJARDY",
    "GLUCOVANCE", "METAGLIP", "SOLIQUA", "XULTOPHY",
    # BP combos
    "EXFORGE", "TWYNSTA", "AZOR", "TRIBENZOR", "HYZAAR", "DIOVAN HCT",
    "ATACAND HCT", "MICARDIS HCT", "BENICAR HCT", "AVALIDE", "EDARBYCLOR",
    "ZESTORETIC", "PRINZIDE", "VASERETIC", "CAPOZIDE", "TEVETEN HCT",
    "TEKAMLO", "PRESTALIA",
    # ARNI
    "LCZ696", "NEPARVIS", "SACUBITRIL",
    # nitrates
    "TRINITRINE", "NITRO-DUR", "MINITRAN", "NITROL", "BIDIL",
    # antiarrhythmic
    "NEXTERONE", "SORINE", "BETAPACE AF",
    # omega-3
    "OMACOR", "VASCEPA", "LOVAZA",
]

con = sqlite3.connect(DB)
cur = con.cursor()
matched = set()
for (k,) in cur.execute("SELECT DISTINCT pair_key FROM name_class"):
    matched.add(k)
rows = cur.execute("SELECT drugname_u, prod_ai_u, n_cases "
                   "FROM drug_name_freq").fetchall()
print(f"pairs={len(rows):,}  classified pairs={len(matched):,}\n")
print(f"{'token':<22s} {'pairs':>7s} {'reports':>10s} "
      f"{'matched':>9s} {'UNMATCHED':>10s}   top unmatched name")
print("-" * 110)
for t in TOKENS:
    rx = re.compile(r"\b" + re.escape(t.upper()) + r"\b")
    n_pairs = n_rep = n_m = n_u = 0
    top = ("", 0)
    for dn, pa, n in rows:
        if rx.search(dn) or rx.search(pa or ""):
            n_pairs += 1
            n_rep += n
            key = f"{dn}|{pa}"
            if key in matched:
                n_m += n
            else:
                n_u += n
                if n > top[1]:
                    top = (dn[:40], n)
    print(f"{t:<22s} {n_pairs:>7,} {n_rep:>10,} {n_m:>9,} {n_u:>10,}   "
          f"{top[0]} ({top[1]:,})" if top[1] else
          f"{t:<22s} {n_pairs:>7,} {n_rep:>10,} {n_m:>9,} {n_u:>10,}", flush=True)
con.close()
