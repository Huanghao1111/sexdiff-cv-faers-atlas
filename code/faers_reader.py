"""faers_reader.py — era-adaptive reader for FAERS/AEMS quarterly ASCII archives.

Verified against real files from all format generations (2026-10-14 probe):
  - AERS      2004Q1-2012Q3 : headers ISR/CASE/.../GNDR_COD; drug lacks prod_ai
  - FAERS v1  2012Q4-2014Q4 : primaryid/caseid/gndr_cod; drug lacks prod_ai; BOM on drug header
  - FAERS v2  2015Q1-2026Q2 : primaryid/caseid/sex; drug has prod_ai; reac has drug_rec_act
All quarters carry a header row; $-delimited; latin-1 bytes.

Public API:
    iter_records(zip_path, kind) -> iterator of dict with canonical keys
    quarter_of(zip_path) -> (year, quarter)
Kinds: "demo", "drug", "reac", "delete".
"""
import io
import os
import re
import zipfile

# canonical-name aliases across generations (lowercased, stripped)
_ALIASES = {
    "primaryid": "primaryid",
    "isr": "primaryid",
    "caseid": "caseid",
    "case": "caseid",
    "caseversion": "caseversion",
    "foll_seq": "caseversion",
    "sex": "sex",
    "gndr_cod": "sex",
    "age": "age",
    "age_cod": "age_cod",
    "age_grp": "age_grp",
    "event_dt": "event_dt",
    "mfr_dt": "mfr_dt",
    "init_fda_dt": "init_fda_dt",
    "fda_dt": "fda_dt",
    "rept_cod": "rept_cod",
    "auth_num": "auth_num",
    "mfr_num": "mfr_num",
    "mfr_sndr": "mfr_sndr",
    "lit_ref": "lit_ref",
    "e_sub": "e_sub",
    "wt": "wt",
    "wt_cod": "wt_cod",
    "rept_dt": "rept_dt",
    "to_mfr": "to_mfr",
    "occp_cod": "occp_cod",
    "reporter_country": "reporter_country",
    "occr_country": "occr_country",
    # drug
    "drug_seq": "drug_seq",
    "role_cod": "role_cod",
    "drugname": "drugname",
    "prod_ai": "prod_ai",
    "val_vbm": "val_vbm",
    "route": "route",
    "dose_vbm": "dose_vbm",
    "dechal": "dechal",
    "rechal": "rechal",
    "nda_num": "nda_num",
    # reac
    "pt": "pt",
    "drug_rec_act": "drug_rec_act",
}

_BOM = "\ufeff"

_MEMBER_PATTERNS = {
    "demo": re.compile(r"^demo", re.IGNORECASE),
    "drug": re.compile(r"^drug", re.IGNORECASE),
    "reac": re.compile(r"^reac", re.IGNORECASE),
    "delete": re.compile(r"delete", re.IGNORECASE),
}


def _clean(s):
    return s.replace(_BOM, "").strip().lstrip("\ufeff").strip()


def quarter_of(zip_path):
    """faers_ascii_2019Q2.zip / aers_ascii_2004q1.zip -> (2019, 2) / (2004, 1)."""
    m = re.search(r"(\d{4})[qQ](\d)", os.path.basename(zip_path))
    if not m:
        raise ValueError(f"cannot parse quarter from {zip_path}")
    return int(m.group(1)), int(m.group(2))


def _find_member(zf, kind):
    pat = _MEMBER_PATTERNS[kind]
    for n in zf.namelist():
        base = os.path.basename(n).lower()
        if not base.endswith(".txt"):
            continue
        if pat.search(base):
            return n
    return None


def iter_records(zip_path, kind):
    """Yield canonical dicts from the given quarterly zip for DEMO/DRUG/REAC.

    For kind == "delete", yields {"primaryid": ...} for each deleted case.
    Deleted-cases files are HEADERLESS (verified: 2019Q2 and 2026Q1 are bare
    primaryid lists, one per line, inside a deleted/ subfolder).
    """
    with zipfile.ZipFile(zip_path) as zf:
        member = _find_member(zf, kind)
        if member is None:
            return
        with zf.open(member) as f:
            text = io.TextIOWrapper(f, encoding="latin-1", errors="replace")
            header = None
            canon_idx = {}
            for line in text:
                line = line.rstrip("\r\n")
                if not line:
                    continue
                fields = line.split("$")
                if kind == "delete":
                    pid = _clean(fields[0])
                    if pid:
                        yield {"primaryid": pid}
                    continue
                if header is None:
                    header = [_clean(x).lower() for x in fields]
                    for i, name in enumerate(header):
                        canon = _ALIASES.get(name)
                        if canon:
                            canon_idx[canon] = i
                    continue
                # data row: pad to header length if trailing empties were cut
                if len(fields) < len(header):
                    fields = fields + [""] * (len(header) - len(fields))
                rec = {}
                for canon, i in canon_idx.items():
                    rec[canon] = _clean(fields[i]) if i < len(fields) else ""
                yield rec


def iter_demo(zip_path):
    yield from iter_records(zip_path, "demo")


def iter_drug(zip_path):
    yield from iter_records(zip_path, "drug")


def iter_reac(zip_path):
    yield from iter_records(zip_path, "reac")


def iter_deleted(zip_path):
    yield from iter_records(zip_path, "delete")
