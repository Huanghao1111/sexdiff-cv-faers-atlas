"""drug_classes.py — frozen drug-class dictionary (v2, 2026-10-15).

One entry per pharmacological class; each holds ingredient and selected brand
name patterns. Matching is done on the UPPERCASED concatenation of
drugname + prod_ai in FAERS DRUG files (word-boundary regex, plus a
separator-normalised copy of the same string).

Scope: ATC C01 / C02-C09 / C10 / B01 / A10BJ / A10BK (protocol v1 §4.3).

v1 -> v2 changes (all verified against the 2004Q1-2026Q2 FAERS extract,
152,367 distinct drugname x prod_ai pairs), see src/verify_candidates.log and
src/check_unmatched.log:
  * NEW  RENIN_INH  — aliskiren was absent entirely (6,747 reports recovered)
  * SPLIT ALPHA -> ALPHA_HTN (doxazosin/terazosin/prazosin, ~5.4k) +
            ALPHA_BPH (tamsulosin/alfuzosin/silodosin, ~16k). The v1 ALPHA
            class was 77% urology drugs, which is not cardiovascular
            pharmacotherapy; ALPHA_BPH is matched but excluded from the CV
            universe.
  * NEW  PDE5      — generic/branded sildenafil, tadalafil, vardenafil,
            avanafil (~46k unmatched reports). See the PAH note below.
  * ADDED fixed-dose combination brands that carry no ingredient string in
            drugname/prod_ai (EXFORGE, VYTORIN, JANUMET, HYZAAR, AVALIDE, ...);
            each is assigned to every component class.
  * ADDED LCZ696 / NEPARVIS (ARNI), OMACOR (OMEGA3), SORINE (AA_III),
            HCTZ / MICROZIDE (THIAZIDE), NITRO-DUR / MINITRAN / TRINITRINE
            (VASODIL), DUODART / JALYN (ALPHA_BPH).
  * DROPPED LUCEF and ZEYNQUA from SGLT2I — zero hits in the extract.

Classes outside the cardiovascular universe (matched but excluded from the
active-comparator denominator): MINOXIDIL, ALPHA_BPH, PDE5.

This is the artefact frozen before the main analysis and shipped as
supplementary material.
"""

CLASSES = {
    # ---------------- Antithrombotics ----------------
    "VKA": ["WARFARIN", "ACENOCOUMAROL", "PHENPROCOUMON", "COUMADIN", "JANTOVEN",
            "MAREVAN", "SINTROM", "DICUMAROL"],
    "DOAC": ["DABIGATRAN", "PRADAXA", "PRADAX", "RIVAROXABAN", "XARELTO",
             "APIXABAN", "ELIQUIS", "EDOXABAN", "SAVAYSA", "LIXIANA",
             "BETRIXABAN", "BEVYXXA"],
    "P2Y12": ["CLOPIDOGREL", "PLAVIX", "PRASUGREL", "EFFIENT", "TICAGRELOR",
              "BRILINTA", "BRILIQUE", "TICLOPIDINE", "TICLID", "CANGRELOR",
              "KENGREAL"],
    # NOTE: a bare "ASA" token was trialled and rejected — it adds no real
    # reports and risks matching non-English text. Word-boundary matching
    # already keeps SPRYCEL / BASAGLAR / SULFASALAZINE out (verified: 0 false
    # inclusions).
    "ASPIRIN": ["ASPIRIN", "ACETYLSALICYLIC ACID"],
    "GPIIBIIIA": ["ABCIXIMAB", "REOPRO", "EPTIFIBATIDE", "INTEGRILIN",
                  "TIROFIBAN", "AGGRASTAT"],
    # ---------------- Lipid modifying ----------------
    "STATIN": ["ATORVASTATIN", "LIPITOR", "ROSUVASTATIN", "CRESTOR",
               "SIMVASTATIN", "ZOCOR", "PRAVASTATIN", "PRAVACHOL",
               "LOVASTATIN", "MEVACOR", "ALTOPREV", "FLUVASTATIN", "LESCOL",
               "PITAVASTATIN", "LIVALO", "ZYPITAMAG", "CERIVASTATIN", "BAYCOL"],
    "EZETIMIBE": ["EZETIMIBE", "ZETIA", "EZETROL"],
    "PCSK9I": ["ALIROCUMAB", "PRALUENT", "EVOLOCUMAB", "REPATHA",
               "INCLISIRAN", "LEQVIO"],
    "FIBRATE": ["FENOFIBRATE", "FENOFIBRIC ACID", "TRICOR", "LIPOFEN",
                "TRILIPIX", "GEMFIBROZIL", "LOPID", "BEZAFIBRATE",
                "CLOFIBRATE", "ATROMID"],
    "BEMPEDOIC": ["BEMPEDOIC ACID", "NEXLETOL", "NEXLIZET"],
    "OMEGA3": ["ICOSAPENT", "VASCEPA", "OMEGA-3", "OMEGA 3", "LOVAZA",
               "OMACOR"],
    # ---------------- RAAS / antihypertensives ----------------
    "ACEI": ["CAPTOPRIL", "CAPOTEN", "ENALAPRIL", "VASOTEC", "LISINOPRIL",
             "PRINIVIL", "ZESTRIL", "RAMIPRIL", "ALTACE", "PERINDOPRIL",
             "ACEON", "BENAZEPRIL", "LOTENSIN", "FOSINOPRIL", "MONOPRIL",
             "QUINAPRIL", "ACCUPRIL", "TRANDOLAPRIL", "MAVIK",
             "MOEXIPRIL", "UNIVASC", "CILAZAPRIL", "IMIDAPRIL"],
    "ARB": ["LOSARTAN", "COZAAR", "VALSARTAN", "DIOVAN", "IRBESARTAN",
            "AVAPRO", "CANDESARTAN", "ATACAND", "TELMISARTAN", "MICARDIS",
            "OLMESARTAN", "BENICAR", "EPROSARTAN", "TEVETEN",
            "AZILSARTAN", "EDARBI"],
    "ARNI": ["SACUBITRIL", "ENTRESTO", "VALSARTAN SACUBITRIL",
             "SACUBITRIL/VALSARTAN", "LCZ696", "NEPARVIS"],
    # Direct renin inhibitor — absent from v1; 6,747 reports recovered.
    "RENIN_INH": ["ALISKIREN", "TEKTURNA", "RASILEZ", "VALTURNA", "AMTURNIDE"],
    "CCB_DHP": ["AMLODIPINE", "NORVASC", "NIFEDIPINE", "PROCARDIA", "ADALAT",
                "FELODIPINE", "PLENDIL", "NICARDIPINE", "CARDENE",
                "ISRADIPINE", "DYNACIRC", "NISOLDIPINE", "SULAR",
                "LERCANIDIPINE", "ZANIDIP", "LACIDIPINE", "CLEVIDIPINE",
                "CLEVIPREX"],
    "CCB_NON": ["VERAPAMIL", "CALAN", "ISOPTIN", "DILTIAZEM", "CARDIZEM",
                "TIAZAC"],
    "BETA": ["METOPROLOL", "LOPRESSOR", "TOPROL", "ATENOLOL", "TENORMIN",
             "BISOPROLOL", "ZEBETA", "CARVEDILOL", "COREG", "NEBIVOLOL",
             "BYSTOLIC", "PROPRANOLOL", "INDERAL", "LABETALOL", "TRANDATE",
             "NADOLOL", "CORGARD", "PINDOLOL", "ACEBUTOLOL", "BETAXOLOL",
             "CELIPROLOL"],
    "LOOP": ["FUROSEMIDE", "LASIX", "TORASEMIDE", "TORSEMIDE", "DEMADEX",
             "BUMETANIDE", "BUMEX", "ETHACRYNIC ACID"],
    "THIAZIDE": ["HYDROCHLOROTHIAZIDE", "HYDROCHLOROTHIAZID", "HCTZ",
                 "MICROZIDE", "CHLORTHALIDONE", "CHLORTALIDONE",
                 "INDAPAMIDE", "METOLAZONE", "CHLOROTHIAZIDE", "DIURIL",
                 "BENDROFLUMETHIAZIDE", "HYDROFLUMETHIAZIDE"],
    "MRA": ["SPIRONOLACTONE", "ALDACTONE", "EPLERENONE", "INSPRA",
            "FINERENONE", "KERENDIA"],
    # Alpha-1 blockers used for hypertension (ATC C02CA). Kept separate from
    # the uroselective agents because they are the cardiovascular indication.
    "ALPHA_HTN": ["DOXAZOSIN", "CARDURA", "TERAZOSIN", "HYTRIN", "PRAZOSIN",
                  "MINIPRESS"],
    "CENTRAL": ["CLONIDINE", "CATAPRES", "METHYLDOPA", "ALDOMET",
                "MOXONIDINE", "GUANFACINE", "TENEX"],
    "VASODIL": ["HYDRALAZINE", "APRESOLINE", "ISOSORBIDE", "IMDUR", "ISORDIL",
                "NITROGLYCERIN", "NITROGLYCERINE", "TRINITRIN", "TRINITRINE",
                "GLYCERYL TRINITRATE", "NITROPRUSSIDE", "NITRO-DUR",
                "MINITRAN", "NITROL", "ISDN", "ISMN"],
    # ---------------- Antiarrhythmics / rate agents ----------------
    "AA_IC": ["FLECAINIDE", "TAMBOCOR", "PROPAFENONE", "RYTHMOL"],
    "AA_III": ["AMIODARONE", "CORDARONE", "PACERONE", "NEXTERONE", "SOTALOL",
               "BETAPACE", "SORINE", "DRONEDARONE", "MULTAQ",
               "DOFETILIDE", "TIKOSYN", "IBUTILIDE", "CORVERT"],
    "DIGOXIN": ["DIGOXIN", "LANOXIN", "DIGOXINE", "DIGITOXIN"],
    "IVABRADINE": ["IVABRADINE", "CORLANOR", "PROCORALAN"],
    # ---------------- Metabolic (CV outcome-modifying) ----------------
    "GLP1RA": ["EXENATIDE", "BYETTA", "BYDUREON", "LIRAGLUTIDE", "VICTOZA",
               "SAXENDA", "DULAGLUTIDE", "TRULICITY", "SEMAGLUTIDE", "OZEMPIC",
               "WEGOVY", "RYBELSUS", "LIXISENATIDE", "ADLYXIN", "TIRZEPATIDE",
               "MOUNJARO", "ZEPBOUND", "ALBIGLUTIDE", "TANZEUM"],
    "SGLT2I": ["CANAGLIFLOZIN", "INVOKANA", "DAPAGLIFLOZIN", "FARXIGA",
               "FORXIGA", "EMPAGLIFLOZIN", "JARDIANCE", "ERTUGLIFLOZIN",
               "STEGLATRO", "SOTAGLIFLOZIN", "BEXAGLIFLOZIN", "BRENZAVVY",
               "IPRAGLIFLOZIN", "SUGLAT"],
    "DPP4I": ["SITAGLIPTIN", "JANUVIA", "SAXAGLIPTIN", "ONGLYZA",
              "LINAGLIPTIN", "TRADJENTA", "ALOGLIPTIN", "NESINA",
              "VILDAGLIPTIN", "GALVUS"],
    "METFORMIN": ["METFORMIN", "GLUCOPHAGE"],
    # ---------------- Other CV ----------------
    "RANOLAZINE": ["RANOLAZINE", "RANEXA"],
    "VERICIGUAT": ["VERICIGUAT", "VERQUVO"],
    "CILOSTAZOL": ["CILOSTAZOL", "PLETAL"],
    # ---------------- Pulmonary arterial hypertension ----------------
    # PAH-specific agents, plus the two PDE5 brands that are marketed for PAH.
    # Sildenafil and tadalafil DO have a PAH indication (REVATIO 20 mg t.i.d.,
    # ADCIRCA 40 mg o.d.), which is why those brands stay in this class;
    # they are empirically PAH-like:
    #   REVATIO  7,889 reports, 66.8% female
    #   ADCIRCA  8,341 reports, 73.5% female
    # whereas the erectile-dysfunction brands are not:
    #   VIAGRA  25,677 reports,  1.6% female
    #   CIALIS  13,730 reports,  1.1% female
    # Generic sildenafil / tadalafil (34.5% / 51.8% female) are a MIXTURE of
    # both indications that cannot be resolved from FAERS drug names; they are
    # matched into the separate PDE5 class rather than being silently dropped,
    # and their inclusion is handled as a pre-specified sensitivity analysis.
    "PAH": ["BOSENTAN", "TRACLEER", "MACITENTAN", "OPSUMIT", "AMBRISENTAN",
            "LETARIS", "REVATIO", "ADCIRCA", "RIOCIGUAT", "ADEMPAS",
            "SELEXIPAG", "UPTRAVI", "EPOPROSTENOL", "FLOLAN", "VELETRI",
            "TREPROSTINIL", "REMODULIN", "TYVASO", "ORENITRAM", "ILOPROST",
            "VENTAVIS"],
    # ---------------- Matched but outside the CV universe ----------------
    # PDE5 inhibitors as prescribed in routine care are overwhelmingly used for
    # erectile dysfunction; their report stream (and therefore any
    # disproportionality signal) reflects that indication, not cardiovascular
    # pharmacotherapy. Kept as a standalone class and analysed separately
    # (sensitivity analysis S-PDE5) instead of being discarded.
    "PDE5": ["SILDENAFIL", "TADALAFIL", "VARDENAFIL", "AVANAFIL",
             "VIAGRA", "CIALIS", "LEVITRA", "STAXYN", "STENDRA", "SPEDRA"],
    # Uroselective alpha-1 blockers: lower-urinary-tract symptoms, not a
    # cardiovascular indication. In v1 these sat inside ALPHA and made it 77%
    # urology reports.
    "ALPHA_BPH": ["TAMSULOSIN", "FLOMAX", "ALFUZOSIN", "UROXATRAL",
                  "SILODOSIN", "RAPAFLO", "DUODART", "JALYN"],
    # FAERS cannot reliably separate topical minoxidil (alopecia, heavily
    # female) from oral minoxidil (hypertension); alopecia-product reports
    # dominate and distort the vasodilator class.
    "MINOXIDIL": ["MINOXIDIL", "ROGAINE", "REGAINE", "LONITEN"],
}

# ---- Fixed-dose combinations -------------------------------------------------
# Brand -> component classes. These brands carry no ingredient string in
# drugname or prod_ai, so they are invisible to ingredient-level matching;
# each is appended to EVERY component class, which is the standard convention
# for class-level pharmacovigilance analyses of fixed-dose combinations.
# NOT included: SOLIQUA (insulin glargine + lixisenatide) and XULTOPHY
# (insulin degludec + liraglutide) — both are already captured through their
# GLP-1 RA ingredient string, and their event profile is basal-insulin
# dominated (hypoglycaemia), so they are deliberately not forced into GLP1RA.
COMBOS = {
    # lipid
    "VYTORIN": ["STATIN", "EZETIMIBE"],          # simvastatin + ezetimibe
    "CADUET": ["STATIN", "CCB_DHP"],             # atorvastatin + amlodipine
    # glucose lowering
    "JANUMET": ["DPP4I", "METFORMIN"],           # sitagliptin + metformin
    "JENTADUETO": ["DPP4I", "METFORMIN"],        # linagliptin + metformin
    "KOMBIGLYZE": ["DPP4I", "METFORMIN"],        # saxagliptin + metformin
    "GLUCOVANCE": ["METFORMIN"],                 # glyburide + metformin
    "METAGLIP": ["METFORMIN"],                   # glipizide + metformin
    # blood pressure
    "EXFORGE": ["CCB_DHP", "ARB"],               # amlodipine + valsartan
    "EXFORGE HCT": ["CCB_DHP", "ARB", "THIAZIDE"],
    "TWYNSTA": ["ARB", "CCB_DHP"],               # telmisartan + amlodipine
    "AZOR": ["ARB", "CCB_DHP"],                  # olmesartan + amlodipine
    "TRIBENZOR": ["ARB", "CCB_DHP", "THIAZIDE"],  # olmesartan + amlo + HCTZ
    "PRESTALIA": ["ACEI", "CCB_DHP"],            # perindopril + amlodipine
    "TEKAMLO": ["RENIN_INH", "CCB_DHP"],         # aliskiren + amlodipine
    "VALTURNA": ["RENIN_INH", "ARB"],            # aliskiren + valsartan
    "AMTURNIDE": ["RENIN_INH", "CCB_DHP", "THIAZIDE"],
    "HYZAAR": ["ARB", "THIAZIDE"],               # losartan + HCTZ
    "AVALIDE": ["ARB", "THIAZIDE"],              # irbesartan + HCTZ
    "DIOVAN HCT": ["ARB", "THIAZIDE"],
    "ATACAND HCT": ["ARB", "THIAZIDE"],
    "MICARDIS HCT": ["ARB", "THIAZIDE"],
    "BENICAR HCT": ["ARB", "THIAZIDE"],
    "TEVETEN HCT": ["ARB", "THIAZIDE"],
    "EDARBYCLOR": ["ARB", "THIAZIDE"],           # azilsartan + chlorthalidone
    "ZESTORETIC": ["ACEI", "THIAZIDE"],          # lisinopril + HCTZ
    "PRINZIDE": ["ACEI", "THIAZIDE"],
    "VASERETIC": ["ACEI", "THIAZIDE"],           # enalapril + HCTZ
    "CAPOZIDE": ["ACEI", "THIAZIDE"],            # captopril + HCTZ
    # heart failure / other
    "BIDIL": ["VASODIL"],                        # isosorbide dinitrate + hydralazine
}

for _brand, _classes in COMBOS.items():
    for _c in _classes:
        if _brand not in CLASSES[_c]:
            CLASSES[_c].append(_brand)

# classes matched but excluded from the cardiovascular comparator universe
EXCLUDE_FROM_CV = {"MINOXIDIL", "ALPHA_BPH", "PDE5"}

# classes used as the cardiovascular "universe" for the active-comparator design
CV_CLASSES = [c for c in CLASSES if c not in EXCLUDE_FROM_CV]

# precedence: when a report matches both, keep the first and drop the second.
# ARNI over ARB        — sacubitril/valsartan is not an ARB-treated patient
# PAH  over PDE5       — REVATIO/ADCIRCA are PAH use, not erectile dysfunction
MUTEX = {"ARNI": ["ARB"], "PAH": ["PDE5"]}
