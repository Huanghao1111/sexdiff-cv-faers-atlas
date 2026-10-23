"""build_figure_data.py — data layer for Figures 1-2 and Table 1.

PT -> clinical event domain (keyword rules, first match wins; MedDRA SOC
hierarchy is licensed material and was not available, so domains are custom,
disclosed in the manuscript methods), then class x domain disproportionality
with the exact engine and definitions of main_analysis.py (report-level DISTINCT
primaryid counts, comparator = CV universe minus index, MIN_CELL=5, BH q).

Outputs:
  fig2_domain_grid.csv   - class x domain counts, ROR_f/ROR_m, ratio, p, q
  fig_flow_numbers.json  - Figure 1 flowchart numbers
  table1_numbers.json    - Table 1 dataset description numbers
"""
import csv
import json
import math
import os
import re
import sqlite3
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "faers.db")
MIN_CELL = 5

# ---------------- PT -> clinical event domain ----------------
RULES = [
    ("Arrhythmia / conduction", [
        r"TORSADE", r"ARRHYTHMIA", r"ATRIAL (FIBRILLATION|FLUTTER)",
        r"BRADYCARDIA", r"TACHYCARDIA", r"VENTRICULAR (FIBRILLATION|TACHY|EXTRASYST|ARRHYTH|DYSFUNC)",
        r"ELECTROCARDIOGRAM", r"PALPITATION", r"SINUS (NODE|BRADY|TACHY|ARREST)",
        r"(AV|ATRIOVENTRICULAR|BUNDLE BRANCH) BLOCK", r"HEART RATE", r"ASYSTOLE",
        r"CARDIAC ARREST", r"EXTRASYSTOLES", r"CARDIOVERSION", r"DEFIBRILLAT",
        r"WOLFF-PARKINSON", r"QT PROLONG", r"BRUGADA", r"SHORT QT",
        r"LONG QT", r"ARRHYTHMOGENIC", r"ELECTROCARDIOGRAPHIC"]),
    ("Bleeding / haematologic", [
        r"HAEMORRHAGE", r"BLEEDING", r"HAEMATOMA", r"EPISTAXIS", r"MELAENA",
        r"HAEMATEMESIS", r"HAEMOPTYSIS", r"HAEMATOCHEZIA", r"ANAEMIA",
        r"THROMBOCYTOPENIA", r"HAEMOGLOBIN", r"HAEMATOCRIT", r"INTERNATIONAL NORMALISED",
        r"COAGUL", r"ANTICOAG", r"BLOOD LOSS", r"PETECHIAE", r"PURPURA", r"ECCHYMOSIS",
        r"CONTUSION", r"HAEMOLYSIS", r"LEUKOPENIA", r"NEUTROPENIA", r"AGRANULOCYTOSIS",
        r"PANCYTOPENIA", r"LYMPHOPENIA", r"EOSINOPHILIA", r"PLATELET",
        r"ACTIVATED PARTIAL THROMBOPLASTIN", r"BLOOD COUNT", r"FIBRIN",
        r"D-DIMER", r"PROTHROMBIN"]),
    ("Vascular / thromboembolic", [
        r"THROMBOSIS", r"EMBOLISM", r"(ISCHAEMIC )?STROKE", r"CEREBROVASCULAR",
        r"MYOCARDIAL (INFARCTION|ISCHAEMIA)", r"ANGINA", r"ACUTE CORONARY",
        r"CORONARY ARTERY", r"TRANSIENT ISCHAEMIC", r"PERIPHERAL (ARTERIAL|VASCULAR|ISCHAEMIA)",
        r"INFARCTION", r"ARTERIAL OCCLUS", r"ISCHAEMIA", r"ANEURYSM",
        r"AORTIC", r"ARTERIOSCL", r"ARTERIOSPASM", r"ARTERIAL STENOSIS",
        r"^HYPERTENSION", r"BLOOD PRESSURE.*INCREASED", r"VENOUS INSUFFICIENCY",
        r"VARICOSE", r"RAYNAUD", r"FLUSHING", r"HOT FLU(SH|H)",
        r"CEREBRAL ARTERY", r"CAROTID", r"ARTERIOVENOUS", r"VASCULAR STENOSIS",
        r"ARTERY STENOSIS", r"VASCULAR OCCLUSION", r"ARTERIOPATHY"]),
    ("Heart failure / oedema", [
        r"CARDIAC FAILURE", r"OEDEMA", r"FLUID (RETENTION|OVERLOAD)",
        r"VENTRICULAR (HYPERTROPHY|DILAT)", r"EJECTION FRACTION", r"CARDIOMEGALY",
        r"CARDIOMYOPATHY", r"NATRIURETIC", r"CARDIAC (DISORDER|DYSFUNCTION)",
        r"ATRIAL ENLARGEMENT", r"SEPTAL DEFECT", r"VALVE", r"CARDIAC MURMUR",
        r"CARDIAC HYPERTROPHY", r"PERICARDIAL (EFFUSION|TAMPONADE)",
        r"CARDIAC TAMPONADE", r"ASCITES", r"PLEURAL EFFUSION$"]),
    ("Hypotension / syncope", [
        r"HYPOTENSION", r"SYNCOPE", r"DIZZINESS", r"PRESYNCOPE", r"ORTHOSTATIC",
        r"BLOOD PRESSURE.*(DECREASED|ABNORMAL|FLUCTUATION)", r"CIRCULATORY COLLAPSE", r"SHOCK"]),
    ("Renal / electrolyte", [
        r"HYPOKAL", r"HYPERKAL", r"HYPONATR", r"HYPERNATR", r"HYPOMAGNE",
        r"HYPERMAGNE", r"HYPOCALC", r"HYPERCALC", r"RENAL", r"CREATININE",
        r"NEPHRO", r"KIDNEY", r"GLOMERULAR", r"URINA(TION|RY TRACT|RY RETENTION|RY INCONTINENCE)",
        r"OLIGURIA", r"ANURIA", r"POLYURIA", r"NOCTURIA", r"PROTEINURIA",
        r"ACUTE KIDNEY", r"BLADDER", r"DYSURIA", r"MICTURITION",
        r"BLOOD (UREA|POTASSIUM|SODIUM|CALCIUM|PHOSPHORUS|MAGNESIUM|CREATININE)",
        r"BICARBONATE", r"URINE (OUTPUT|FLOW|ABNORMALITY)"]),
    ("Endocrine / metabolic", [
        r"THYROID", r"THYROTOXIC", r"DIABET", r"GLUCOSE", r"GLYCAEMIA",
        r"HYPOGLYC", r"HYPERGLYC", r"GOUT", r"URIC ACID", r"URATE",
        r"WEIGHT (INCREASED|DECREASED|FLUCTUATION)", r"OBESITY", r"APPETITE",
        r"METABOLIC", r"LIPID", r"CHOLESTEROL", r"TRIGLYCERIDE", r"HORMONE",
        r"ACIDOSIS", r"ALKALOSIS", r"AMMONIA", r"VITAMIN", r"NUTRITION",
        r"CACHEXIA", r"DEHYDRATION$"]),
    ("GI / hepatic", [
        r"NAUSEA", r"VOMITING", r"DIARRHOEA", r"CONSTIPATION", r"ABDOMINAL",
        r"GASTR", r"DYSPEPSIA", r"HEPATIC", r"HEPATO", r"LIVER", r"PANCREAT",
        r"TRANSAMINASE", r"ALANINE AMINO", r"ASPARTATE AMINO", r"BILIRUBIN",
        r"JAUNDICE", r"CHOLEST", r"INTESTINAL", r"BOWEL", r"ILEUS", r"COLITIS",
        r"OESOPHAG", r"DYSPHAGIA", r"FLATULENCE", r"STOMATITIS", r"ULCER",
        r"ANAL INCONTINENCE", r"APPENDICITIS", r"AMYLASE", r"LIPASE", r"FECAL",
        r"FAECAL", r"HAEMORRHOID", r"RECTAL", r"ANORECTAL", r"MELAENA$",
        r"CHOLELITHIASIS", r"CHOLANGITIS", r"CHOLECYST", r"CHOLURIA",
        r"GALLBLADDER", r"BILE DUCT", r"BILIARY", r"CHROMATURIA"]),
    ("Infection", [
        r"INFECTION", r"SEPSIS", r"SEPTIC", r"CELLULITIS", r"PNEUMONIA",
        r"ABSCESS", r"GANGRENE", r"FUNGAL", r"CANDIDA", r"HERPES", r"INFLUENZA",
        r"BRONCHITIS", r"SINUSITIS", r"PHARYNGITIS", r"NASOPHARYNGITIS",
        r"CYSTITIS", r"PYELONEPHRITIS", r"ERYSIPELAS", r"ENDOCARDITIS",
        r"MYOCARDITIS", r"PERICARDITIS", r"FASCITIS", r"VULVOVAGINAL", r"BALANITIS",
        r"BACTERAEMIA", r"VIRAEMIA", r"VIRAL ", r"MALARIA", r"TUBERCULOSIS"]),
    ("Musculoskeletal", [
        r"MYALGIA", r"MYOPATHY", r"MYOSITIS", r"RHABDOMYOLYSIS", r"MUSCLE",
        r"MYASTHENIA", r"CRAMP", r"ARTHRALGIA", r"ARTHRITIS", r"BACK PAIN",
        r"TENDON", r"JOINT", r"LIMB", r"CREATINE (PHOSPHO)?KINASE", r"NECK PAIN",
        r"FIBROMYALGIA", r"GROWTH OF (THE )?LIMBS", r"ARTHROPATHY", r"BURSITIS",
        r"BONE (EROSION|LOSS|DENSITY|DISORDER|PAIN)", r"OSTEOPOROSIS",
        r"OSTEOPENIA", r"OSTEONECROSIS", r"OSTEOARTHRITIS",
        r"BLOOD CREATINE ", r"COSTOCHONDRITIS", r"POLYMYALGIA", r"FRACTURE$"]),
    ("Neurological / psychiatric", [
        r"HEADACHE", r"MIGRAINE", r"NEUROPATHY", r"PARAESTHESIA", r"SEIZURE",
        r"CONVULSION", r"DEPRESSION", r"ANXIETY", r"INSOMNIA", r"CONFUSION",
        r"MEMORY", r"AMNESIA", r"SLEEP", r"SOMNOLENCE", r"SEDATION", r"TREMOR",
        r"AGITATION", r"DELIRIUM", r"ENCEPHALOPATHY", r"COMA", r"ALTERED STATE",
        r"DEMENTIA", r"HALLUCINATION", r"MOOD", r"SUICID", r"EMOTIONAL",
        r"PSYCH", r"NERVE", r"NEUROLOG", r"BALANCE", r"GAIT", r"FALL",
        r"PARALYSIS", r"FACIAL PALSY", r"RESTLESS", r"AKATHISIA",
        r"ABNORMAL BEHAVIOUR", r"AGGRESSION", r"ANGER", r"AFFECTIVE",
        r"ADJUSTMENT DISORDER", r"APATHY", r"IRRITABIL", r"NERVOUSNESS",
        r"AGEUSIA", r"DYSGEUSIA", r"ANOSMIA", r"TASTE", r"SPEECH",
        r"APHASIA", r"DYSARTHRIA", r"CATATONIA", r"EUPHORIA", r"MANIA",
        r"FEAR", r"NERVOUS SYSTEM", r"DISTURBANCE IN ATTENTION", r"DROOLING",
        r"ATAXIA", r"AURA", r"DYSKINESIA", r"HYPOKINESIA", r"BRADYKINESIA",
        r"CHOREA", r"DYSSTASIA", r"ABASIA", r"COORDINATION ABNORMAL",
        r"BRAIN", r"CEREBRAL (MASS|OEDEMA|HAEMORRHAGE|INFARCTION)", r"COGNITIVE",
        r"NEURALGIA", r"RADICULOPATHY", r"MONOPLEGIA", r"HEMIPLEGIA",
        r"HEMIPARESIS", r"PARAPLEGIA", r"SPINAL CORD"]),
    ("Respiratory", [
        r"COUGH", r"DYSPNOEA", r"BRONCHOSPASM", r"ASTHMA", r"RESPIRATORY",
        r"PLEURAL", r"PULMONARY (FIBROSIS|HYPERTENSION|FUNCTION|OEDEMA)",
        r"HYPOXIA", r"APNOEA", r"WHEEZ", r"RHINITIS", r"DYSPHONIA", r"OROPHARYNG",
        r"ALVEOLITIS", r"LUNG (INJURY|DISORDER|INFILTRATION)", r"THROAT",
        r"NASAL CONGESTION", r"UPPER RESPIRATORY", r"CHRONIC OBSTRUCTIVE",
        r"ASPIRATION", r"ASPHYXIA", r"ATELECTASIS", r"CHOKING", r"SPUTUM",
        r"HYPERVENTILATION", r"HYPOVENTILATION", r"STRIDOR", r"BREATH SOUNDS",
        r"BRONCHIECTASIS", r"BRONCHIAL", r"HICCUPS", r"SNORING"]),
    ("Skin / hypersensitivity", [
        r"RASH", r"URTICARIA", r"ANGIOEDEMA", r"PRURITUS", r"ANAPHYLA",
        r"STEVENS-JOHNSON", r"TOXIC EPIDERMAL", r"DERMATITIS", r"PHOTOSENSITIVITY",
        r"ERYTHEMA", r"ALOPECIA", r"BLISTER", r"HYPERSENSITIVITY", r"DRUG REACTION",
        r"SWELLING (FACE|OF FACE)", r"FLUSHING", r"SKIN", r"NAIL",
        r"ACNE", r"PUSTULOSIS", r"EXANTHEM", r"HYPERPIGMENT", r"HYPOPIGMENT",
        r"SWEATING", r"HYPERHIDROSIS", r"DRY SKIN", r"ROSACEA", r"LIVEDO"]),
    ("Reproductive / breast", [
        r"GYNAECOMASTIA", r"BREAST", r"ERECTILE", r"MENSTRUAL", r"MENOPAUSE",
        r"LIBIDO", r"VAGINAL", r"PENILE", r"PRIAPISM", r"OVARI", r"UTERINE",
        r"PROSTAT", r"TESTICULAR", r"SEXUAL DYSFUNCTION", r"GENITAL",
        r"GALACTORRHOEA", r"FERTILITY"]),
    ("Immunologic / autoimmune", [
        r"VASCULITIS", r"ANTINUCLEAR", r"ANTI-NEUTROPHIL", r"ANTINEUTROPHIL",
        r"AUTOIMMUNE", r"LUPUS", r"IMMUNE[- ]MEDIATED", r"SERUM SICKNESS",
        r"SJOGREN", r"SARCOID", r"ANTIPHOSPHOLIPID", r"DRESS", r"GRANULOMATOSIS",
        r"C-REACTIVE PROTEIN", r"ERYTHROCYTE SEDIMENTATION", r"ANTIBODY",
        r"IMMUNOGLOBULIN", r"COMPLEMENT ",
        r"GOODPASTURE", r"MYELITIS", r"MULTIPLE SCLEROSIS", r"DEMYELIN"]),
    ("Neoplasm", [
        r"NEOPLASM", r"CANCER", r"CARCINOMA", r"TUMOUR", r"MALIGNAN",
        r"ADENOMA", r"LEUKAEMIA", r"LYMPHOMA", r"MELANOMA", r"MYELOMA",
        r"KERATOSIS", r"METASTAS", r"SARCOMA", r"ADENOCARCINOMA"]),
    ("Injury / procedural / dosing", [
        r"ACCIDENT", r"OVERDOSE", r"INJURY", r"POISONING", r"TOXICITY",
        r"TOXIC$", r"EXPOSURE", r"ADMINISTRATION SITE", r"APPLICATION SITE",
        r"INJECTION SITE", r"INFUSION SITE", r"IMPLANT", r"CATHETER SITE",
        r"DEVICE", r"PROCEDUR", r"SURGERY", r"SURGICAL", r"OPERATION",
        r"PUNCTURE", r"AMPUTATION", r"FRACTURE", r"WOUND", r"BURN",
        r"TRANSPLANT", r"COMPLICATION", r"UNDERDOSE", r"DOSING", r"DOSE",
        r"CATHETER", r"PACEMAKER", r"ABLATION", r"CAESAREAN", r"STENT",
        r"CARDIOVERTER", r"CANNULA", r"PROSTHESIS", r"GRAFT"]),
    ("Eye / ear", [
        r"VISION", r"VISUAL", r"EYE", r"RETIN", r"MACUL", r"CATARACT",
        r"GLAUCOMA", r"OCULAR", r"OPHTHALM", r"BLINDNESS", r"DIPLOPIA",
        r"TINNITUS", r"VERTIGO", r"HEARING", r"DEAFNESS", r"^EAR ",
        r"AUDIO", r"OTITIS", r"VESTIBULAR"]),
    ("General / constitutional", [
        r"FATIGUE", r"ASTHENIA", r"MALAISE", r"PYREXIA", r"PAIN$", r"CHEST PAIN",
        r"CHILLS", r"FEELING", r"OEDEMA PERIPHERAL", r"DEHYDRATION",
        r"PERFORMANCE STATUS", r"CONDITION AGGRAVATED", r"QUALITY OF LIFE",
        r"BEDRIDDEN", r"ACTIVITIES OF DAILY LIVING", r"BODY TEMPERATURE",
        r"BLOOD TEST", r"GENERAL PHYSICAL", r"IMPAIRED (DRIVING|WORK)",
        r"MOBILITY DECREASED", r"WALKING", r"INDEPENDENCE"]),
]
COMPILED = [(d, [re.compile(p) for p in pats]) for d, pats in RULES]


def to_domain(pt):
    for d, pats in COMPILED:
        for p in pats:
            if p.search(pt):
                return d
    return "Other / unmapped"


def norm_sf(z):
    return math.erfc(abs(z) / math.sqrt(2.0))


def bh_fdr(pvals):
    n = len(pvals)
    order = sorted(range(n), key=lambda i: pvals[i])
    q = [0.0] * n
    prev = 1.0
    for rank in range(n - 1, -1, -1):
        i = order[rank]
        prev = min(prev, pvals[i] * n / (rank + 1))
        q[i] = min(prev, 1.0)
    return q


def main():
    t0 = time.time()
    con = sqlite3.connect(DB)
    cur = con.cursor()
    con.execute("PRAGMA temp_store=MEMORY")

    from drug_classes import CV_CLASSES
    classes = [c for c in
               [r[0] for r in cur.execute(
                   "SELECT DISTINCT class FROM report_class ORDER BY class")]
               if c in CV_CLASSES]

    # ---- PT universe + domain mapping ----
    cur.execute("CREATE TEMP TABLE pt_dom (pt TEXT PRIMARY KEY, dom TEXT)")
    all_pts = sorted(r[0] for r in cur.execute("SELECT DISTINCT pt FROM reac"))
    dom_of = {p: to_domain(p) for p in all_pts}
    cur.executemany("INSERT INTO pt_dom VALUES (?,?)",
                    [(p, d) for p, d in dom_of.items()])

    # coverage report on significant PTs
    sig_pts = set()
    with open(os.path.join(HERE, "sexdiff_tests_filtered.csv"),
              encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if float(r["q"]) < 0.05:
                sig_pts.add(r["pt"])
    unm = sorted(p for p in sig_pts if dom_of.get(p) == "Other / unmapped")
    print(f"significant PTs: {len(sig_pts)} ; unmapped: {len(unm)}")
    print("sample unmapped:", unm[:40])

    # ---- CV universe ----
    qmarks = ",".join("?" * len(classes))
    cur.execute(f"CREATE TEMP TABLE cv_univ AS SELECT DISTINCT primaryid "
                f"FROM report_class WHERE class IN ({qmarks})", classes)
    cur.execute("CREATE INDEX tmp_cv ON cv_univ(primaryid)")

    A = {}   # domain -> sex -> reports (universe level)
    for dom, sex, n in cur.execute(
            """SELECT d.dom, m.sex, COUNT(DISTINCT r.primaryid)
               FROM cv_univ u
               JOIN reac r ON r.primaryid = u.primaryid
               JOIN pt_dom d ON d.pt = r.pt
               JOIN demo m ON m.primaryid = u.primaryid
               WHERE m.sex IN ('M','F')
               GROUP BY d.dom, m.sex"""):
        A.setdefault(dom, {})[sex] = n
    N_all = dict(cur.execute(
        """SELECT m.sex, COUNT(DISTINCT m.primaryid)
           FROM cv_univ u JOIN demo m ON m.primaryid = u.primaryid
           WHERE m.sex IN ('M','F') GROUP BY m.sex"""))
    print(f"CV universe F={N_all.get('F',0):,} M={N_all.get('M',0):,} "
          f"({time.time()-t0:.0f}s)", flush=True)

    cells = []
    for cname in classes:
        cur.execute("CREATE TEMP TABLE idx_set AS SELECT DISTINCT primaryid "
                    "FROM report_class WHERE class=?", (cname,))
        cur.execute("CREATE INDEX tmp_idx ON idx_set(primaryid)")
        a = {}
        for dom, sex, n in cur.execute(
                """SELECT d.dom, m.sex, COUNT(DISTINCT r.primaryid)
                   FROM idx_set i
                   JOIN reac r ON r.primaryid = i.primaryid
                   JOIN pt_dom d ON d.pt = r.pt
                   JOIN demo m ON m.primaryid = i.primaryid
                   WHERE m.sex IN ('M','F')
                   GROUP BY d.dom, m.sex"""):
            a.setdefault(dom, {})[sex] = n
        n_idx = dict(cur.execute(
            """SELECT m.sex, COUNT(DISTINCT m.primaryid)
               FROM idx_set i JOIN demo m ON m.primaryid = i.primaryid
               WHERE m.sex IN ('M','F') GROUP BY m.sex"""))
        f_i, m_i = n_idx.get("F", 0), n_idx.get("M", 0)
        f_c, m_c = N_all.get("F", 0) - f_i, N_all.get("M", 0) - m_i
        for dom in sorted(A):
            af, am = a.get(dom, {}).get("F", 0), a.get(dom, {}).get("M", 0)
            cf, cm = A[dom].get("F", 0) - af, A[dom].get("M", 0) - am
            bf, bm = f_i - af, m_i - am
            df, dm = f_c - cf, m_c - cm
            if min(af, am, cf, cm, bf, bm, df, dm) < MIN_CELL:
                continue
            ror_f = (af / bf) / (cf / df)
            ror_m = (am / bm) / (cm / dm)
            ratio = ror_f / ror_m
            se = math.sqrt(sum(1.0 / x for x in (af, bf, cf, df, am, bm, cm, dm)))
            z = math.log(ratio) / se
            cells.append({"class": cname, "domain": dom, "a_f": af, "a_m": am,
                          "ROR_f": ror_f, "ROR_m": ror_m, "ROR_ratio": ratio,
                          "z": z, "p": norm_sf(z)})
        cur.execute("DROP TABLE idx_set")
        print(f"  {cname:<12} cells so far {len(cells)} ({time.time()-t0:.0f}s)",
              flush=True)

    q = bh_fdr([c["p"] for c in cells])
    for c, qq in zip(cells, q):
        c["q"] = qq
    out = os.path.join(HERE, "fig2_domain_grid.csv")
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["class", "domain", "a_f", "a_m",
                                          "ROR_f", "ROR_m", "ROR_ratio",
                                          "z", "p", "q"])
        w.writeheader()
        for c in cells:
            w.writerow(c)
    print(f"written: {out} ({len(cells)} cells; "
          f"q<0.05: {sum(1 for c in cells if c['q'] < 0.05)})")

    # ---- Figure 1 / Table 1 numbers ----
    raw = cur.execute("SELECT COUNT(*) FROM demo").fetchone()[0]
    sex = dict(cur.execute("SELECT sex, COUNT(DISTINCT primaryid) FROM demo "
                           "GROUP BY sex"))
    era = dict(cur.execute(
        """SELECT CASE WHEN CAST(SUBSTR(fda_dt,1,4) AS INT) < 2015
                      THEN 'pre2015' ELSE 'post2015' END y,
                  COUNT(DISTINCT primaryid)
           FROM demo WHERE LENGTH(fda_dt)>=4 GROUP BY y"""))
    n_serious = cur.execute("SELECT COUNT(DISTINCT s.primaryid) FROM serious s "
                            "JOIN cv_univ u ON u.primaryid=s.primaryid").fetchone()[0]
    nums = {
        "demo_reports": raw,
        "sex_counts": sex,
        "era": era,
        "cv_universe": {"F": N_all.get("F", 0), "M": N_all.get("M", 0)},
        "cv_serious": n_serious,
        "n_classes": len(classes),
        "n_tests": 28949, "n_sig": 2784,
        "n_candidates": 106,
    }
    # dedup numbers from qc_quarter
    try:
        dr, dl = cur.execute("SELECT SUM(demo_rows), COUNT(*) FROM qc_quarter").fetchone()
        nums["qc_quarter"] = {"demo_rows_sum": dr, "quarters": dl}
    except Exception:
        pass
    with open(os.path.join(HERE, "table1_numbers.json"), "w") as f:
        json.dump(nums, f, indent=2)
    print(json.dumps(nums, indent=2)[:1200])
    print(f"total time: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
