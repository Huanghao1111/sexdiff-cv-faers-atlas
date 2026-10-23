"""verify_candidates.py — empirical check of dictionary-addition candidates.

For each candidate token, report how many (drugname, prod_ai) pairs and how many
reports it would capture, plus the female share (a sanity signal for whether the
token really identifies the intended indication).

Usage: python verify_candidates.py
"""
import os
import re
import sqlite3
import sys

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "faers.db")

CANDIDATES = {
    "RENIN_INH": ["ALISKIREN", "TEKTURNA", "RASILEZ", "RASIHEXAL"],
    "ALPHA_HTN": ["DOXAZOSIN", "CARDURA", "TERAZOSIN", "HYTRIN", "PRAZOSIN",
                  "MINIPRESS"],
    "ALPHA_BPH": ["TAMSULOSIN", "FLOMAX", "ALFUZOSIN", "UROXATRAL",
                  "SILODOSIN", "RAPAFLO", "DUODART", "JALYN"],
    "PDE5": ["SILDENAFIL", "TADALAFIL", "VARDENAFIL", "AVANAFIL", "VIAGRA",
             "CIALIS", "LEVITRA", "STAXYN", "STENDRA", "SPEDRA", "REVATIO",
             "ADCIRCA"],
    "THIAZIDE_ADD": ["HCTZ", "HYDROCHLOROTHIAZID", "MICROZIDE"],
    "DOAC_ADD": ["DABIGATRAN ETEXILATE", "PRADAX"],
    "SGLT2I_ADD": ["BEXAGLIFLOZIN", "BRENZAVVY", "INPEFA", "SUGLAT",
                   "IPRAGLIFLOZIN", "LUCEF", "ZEYNQUA", "SOTAGLIFLOZIN",
                   "TOFAGLIFLOZIN", "APERTO", "DEBERZA"],
    "COMBO_LIPID": ["VYTORIN", "CADUET", "ROSUVASTATIN/EZETIMIBE",
                    "ATORVASTATIN/EZETIMIBE", "EZETIMIBE/ATORVASTATIN",
                    "EZETIMIBE/ROSUVASTATIN", "NEXLIZET"],
    "COMBO_DIAB": ["JANUMET", "XIGDUO", "SYNJARDY", "INVOKAMET", "GLYXAMBI",
                   "QTERN", "SEGLUROMET", "STEGLUJAN", "JENTADUETO",
                   "KOMBIGLYZE", "TRIJARDY", "GLUCOVANCE", "METAGLIP",
                   "SOLIQUA", "XULTOPHY", "RYBELSUS"],
    "COMBO_BP": ["EXFORGE", "TWYNSTA", "AZOR", "TRIBENZOR", "TEKAMLO",
                 "VALSARTAN/HYDROCHLOROTHIAZIDE", "LOSARTAN/HYDROCHLOROTHIAZIDE",
                 "BENAZEPRIL/HYDROCHLOROTHIAZIDE", "LISINOPRIL/HYDROCHLOROTHIAZIDE",
                 "TELMISARTAN/AMLODIPINE", "AMLODIPINE/VALSARTAN",
                 "OLMESARTAN/AMLODIPINE", "PRESTALIA", "ACCUPRIL", "ZESTORETIC",
                 "PRINZIDE", "VASERETIC", "CAPOZIDE", "HYZAAR", "DIOVAN HCT",
                 "ATACAND HCT", "MICARDIS HCT", "BENICAR HCT", "AVALIDE",
                 "TEVETEN HCT", "EDARBYCLOR"],
    "ARNI_ADD": ["SACUBITRIL/VALSARTAN", "VALSARTAN/SACUBITRIL",
                 "LCZ696", "ENTRESTO", "NEPARVIS"],
    "VASODIL_ADD": ["GLYCERYL TRINITRATE", "NITROGLYCERIN", "TRINITRINE",
                    "ISOSORBIDE DINITRATE", "ISOSORBIDE MONONITRATE",
                    "NITROL", "MINITRAN", "NITRO-DUR", "NITRODUR"],
    "AA_III_ADD": ["NEXTERONE", "AMIODARONE HYDROCHLORIDE", "SOTALOL",
                   "SOTALOL HYDROCHLORIDE", "BETAPACE AF", "SORINE",
                   "MULTAQ", "TIKOSYN"],
    "OTHER_ADD": ["OMACOR", "LOVAZA", "VASCEPA", "ICOSAPENT ETHYL",
                  "NEXLETOL", "LEQVIO", "INCLISIRAN", "KERENDIA",
                  "VERQUVO", "CORLANOR", "PLETAL", "RANEXA", "ADCIRCA"],
    "NITRATE_CHECK": ["ISDN", "ISMN"],
}


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    total_pairs = cur.execute(
        "SELECT COUNT(*) FROM drug_name_freq").fetchone()[0]
    print(f"distinct pairs in drug_name_freq: {total_pairs:,}\n")

    for grp, pats in CANDIDATES.items():
        print(f"=== {grp} ===")
        for p in pats:
            rx = re.compile(r"\b" + re.escape(p.upper()) + r"\b")
            pairs = []
            for dn, pa, n in cur.execute(
                    "SELECT drugname_u, prod_ai_u, n_cases FROM drug_name_freq"):
                if rx.search(dn) or rx.search(pa or ""):
                    pairs.append((dn, pa, n))
            if not pairs:
                print(f"  {p:<40s} -> 0 pairs")
                continue
            pairs.sort(key=lambda x: -x[2])
            tot = sum(x[2] for x in pairs)
            top = ", ".join(f"{d[:34]}({n:,})" for d, _, n in pairs[:4])
            print(f"  {p:<40s} -> {len(pairs):>6,} pairs, "
                  f"{tot:>9,} reports | top: {top}")
        print(flush=True)
    con.close()


if __name__ == "__main__":
    main()
