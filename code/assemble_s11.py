# -*- coding: utf-8 -*-
"""Assemble Supplementary Appendix S11 (LLM-as-auditor dictionary audit).

Usage: python assemble_s11.py [zh|en]   (default zh)

Embeds, verbatim: frozen protocol v1.1, adjudication instructions, arbitration
record, final metric tables, full 211-pair gold standard, timestamped audit
log; appends a SHA-256 manifest of all machine-readable artefacts and verifies
the two hash values recorded in audit.log at lock time.
zh mode: Chinese source documents as-is.
en mode: S11.1–S11.4 from the English translations in ../supplement/en/;
         S11.5–S11.7 (tables, log, manifest) are language-independent.
Output: ../supplement/S11_Dictionary_Audit_Appendix[_EN].md
"""
import csv
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(ROOT, "supplement")
os.makedirs(OUT_DIR, exist_ok=True)

LANG = sys.argv[1] if len(sys.argv) > 1 else "zh"
EN = LANG == "en"
OUT = os.path.join(OUT_DIR,
                   "S11_Dictionary_Audit_Appendix_EN.md" if EN
                   else "S11_Dictionary_Audit_Appendix.md")


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8-sig") as f:
        return f.read().strip()


def sha256(rel):
    h = hashlib.sha256()
    with open(os.path.join(ROOT, rel), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def nrows(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8-sig", newline="") as f:
        return sum(1 for _ in csv.reader(f)) - 1


def md_table(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    esc = lambda s: s.replace("|", "\\|")
    lines = ["| " + " | ".join(esc(c) for c in rows[0]) + " |",
             "|" + "---|" * len(rows[0])]
    for r in rows[1:]:
        lines.append("| " + " | ".join(esc(c) for c in r) + " |")
    return "\n".join(lines)


# ---- integrity verification against audit.log -------------------------------
LOG_LLM = "68855bcf67f2ede079c433cfe2183f25f8a6b720933d58d960752a28e1426958"
LOG_KEY = "edb1ecd394e9b1f45d5ba8f09db80045466f76635fe4da3870fbd3e559d0df0e"
llm_ok = sha256("src/audit_llm_labels.csv") == LOG_LLM
key_ok = sha256("src/audit_sample_1000_KEY.csv") == LOG_KEY

MANIFEST = [
    ("PROTOCOL_appendix_v1.1_LLM_audit.md", "Frozen audit protocol appendix v1.1 (2026-10-16)", None),
    ("src/audit_sample.py", "Stratified sampling script, seed 20261016", None),
    ("src/audit_sample_1000.csv", "Blind 1,000-pair audit sample (no labels)", "rows"),
    ("src/audit_sample_1000_KEY.csv", "Sealed key: dictionary labels for the sample", "rows"),
    ("src/audit_llm_labels.csv", "Hash-locked LLM label file (frozen 39-class prompt)", "rows"),
    ("src/ADJUDICATION_INSTRUCTIONS.md", "Adjudication instructions as issued to raters", None),
    ("src/audit_adjudication_package.csv", "211-pair adjudication package (14 disagreements + 197 concordant)", "rows"),
    ("src/audit_adjudication_blind.csv", "Blinded rater worksheet (labels concealed)", "rows"),
    ("src/audit_adjudication_raterhhz.csv", "Rater 1 (HHZ) final adjudication", "rows"),
    ("src/audit_adjudication_raterCSQ.csv", "Rater 2 (CSQ) final adjudication", "rows"),
    ("src/audit_arbitration_list.csv", "Arbitration worksheet (arbitration + gold_class columns)", "rows"),
    ("src/ARBITRATION_REQUEST_sampleHHZ.md", "Arbitration request, sample 492 (Exforge D)", None),
    ("src/ARBITRATION_REPLY_sampleCSQ.md", "Arbitration reply, sample 492 (manufacturer-label evidence)", None),
    ("src/audit_gold_standard.csv", "Gold standard, 211 pairs, locked v3 (2026-10-17)", "rows"),
    ("src/compute_audit_metrics.py", "Gold-standard build + pre-specified metrics script (v3)", None),
    ("src/audit_metrics.md", "Rendered metric tables (final)", None),
    ("src/audit.log", "Timestamped audit log", None),
]

if EN:
    header = """# Supplementary Appendix S11 — LLM-as-auditor audit of the drug-class dictionary

**Manuscript:** Sex differences in cardiovascular drug safety: a global pharmacovigilance atlas (FAERS 2004Q1–2026Q2) — EHJ-CVP submission
**Status:** final, gold standard locked v3 (2026-10-17); all 211 adjudicated pairs resolved
**Language:** English submission version. S11.1–S11.4 are translated from the Chinese working documents (the verbatim Chinese versions ship alongside in the repository); the frozen classification prompt in S11.1 §3.1 was originally English and is reproduced exactly. All tables, class codes, and file hashes are language-independent.
"""
    sec1 = read("supplement/en/S11_1_protocol.md")
    sec2 = read("supplement/en/S11_2_adjudication_instructions.md")
    sec3 = read("supplement/en/S11_3_arbitration.md")
    sec4 = read("supplement/en/S11_4_metrics.md")
else:
    header = """# Supplementary Appendix S11 — LLM-as-auditor audit of the drug-class dictionary

**Manuscript:** Sex differences in cardiovascular drug safety: a global pharmacovigilance atlas (FAERS 2004Q1–2026Q2) — EHJ-CVP submission
**Status:** final, gold standard locked v3 (2026-10-17); all 211 adjudicated pairs resolved
**Note on language:** source documents (protocol, adjudication instructions, arbitration record, metric tables) are reproduced verbatim in the team's working language (Chinese); the English submission version ships alongside (`S11_Dictionary_Audit_Appendix_EN.md`). All tables, class codes, and file hashes are language-independent.
"""
    sec1 = read("PROTOCOL_appendix_v1.1_LLM_audit.md")
    sec2 = read("src/ADJUDICATION_INSTRUCTIONS.md")
    sec3 = ("### S11.3.1 Arbitration request\n\n"
            + read("src/ARBITRATION_REQUEST_sampleHHZ.md")
            + "\n\n### S11.3.2 Arbitration reply\n\n"
            + read("src/ARBITRATION_REPLY_sampleCSQ.md"))
    sec4 = read("src/audit_metrics.md")

parts = []
parts.append(header + """
## Contents
- S11.1 Audit protocol (appendix v1.1, frozen 2026-10-16)
- S11.2 Adjudication instructions (as issued to raters)
- S11.3 Arbitration record (sample 492, Exforge D)
- S11.4 Metric tables (final)
- S11.5 Gold standard, 211 pairs (full table)
- S11.6 Timestamped audit log
- S11.7 Machine-readable file manifest (SHA-256) and integrity verification
""")

parts.append("\n---\n\n## S11.1 Audit protocol (appendix v1.1, frozen 2026-10-16)\n\n" + sec1)
parts.append("\n---\n\n## S11.2 Adjudication instructions (as issued to raters)\n\n" + sec2)
parts.append("\n---\n\n## S11.3 Arbitration record (sample 492, Exforge D)\n\n" + sec3)
parts.append("\n---\n\n## S11.4 Metric tables (final; gold standard locked v3)\n\n" + sec4)

parts.append("\n---\n\n## S11.5 Gold standard, 211 pairs (full table)\n\n"
             "Columns: sample_id; stratum (A = hit PPS, B = hit long-tail uniform, C = unmatched PPS); "
             "drugname_u / prod_ai_u (upper-cased FAERS names); dict_classes / llm_classes / gold_class "
             "(pipe-separated class codes, see S11.1 §3.1); dict_correct / llm_correct (1 = exact set match); "
             "dict_error_mode / llm_error_mode (frozen taxonomy, S11.1 §5); rater notes.\n\n"
             + md_table("src/audit_gold_standard.csv"))

parts.append("\n---\n\n## S11.6 Timestamped audit log\n\n```\n"
             + read("src/audit.log")
             + "\n```")

man_lines = ["| File | Description | Rows | SHA-256 |", "|---|---|---|---|"]
for rel, desc, kind in MANIFEST:
    rows = str(nrows(rel)) if kind == "rows" else "—"
    man_lines.append(f"| `{rel}` | {desc} | {rows} | `{sha256(rel)}` |")

parts.append("\n---\n\n## S11.7 Machine-readable file manifest (SHA-256)\n\n"
             "All files ship in the study repository. Hashes computed on the files as frozen.\n\n"
             + "\n".join(man_lines)
             + "\n\n### Integrity verification against the audit log\n\n"
             f"- `audit_llm_labels.csv` SHA-256 {'matches' if llm_ok else 'DOES NOT MATCH'} "
             f"the value recorded at `LLM_LABELS_LOCKED` (2026-10-16T20:12:10): `{LOG_LLM}`\n"
             f"- `audit_sample_1000_KEY.csv` SHA-256 {'matches' if key_ok else 'DOES NOT MATCH'} "
             f"the value recorded at `SEALED_KEY_OPENED` (2026-10-16T20:13:21): `{LOG_KEY}`\n")

out = "\n".join(parts) + "\n"
with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write(out)

print("written:", OUT)
print("bytes:", len(out.encode("utf-8")), "lines:", out.count("\n"))
print("integrity: llm_labels", "PASS" if llm_ok else "FAIL",
      "| sealed_key", "PASS" if key_ok else "FAIL")
