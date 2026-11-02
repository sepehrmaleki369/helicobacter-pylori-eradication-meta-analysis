"""
Extract structured data from H. pylori RCT text files.
One row per treatment ARM (not per paper).
Produces: project/data/processed/extracted_arms.csv
"""
import re
import os
import csv

TEXT_DIR = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/data/raw_text"
OUT_CSV  = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/data/processed/extracted_arms.csv"

# ── helpers ────────────────────────────────────────────────────────────────────

def read(fname):
    with open(os.path.join(TEXT_DIR, fname), encoding="utf-8") as f:
        return f.read()

def first(patterns, text, flags=re.IGNORECASE):
    for p in patterns:
        m = re.search(p, text, flags)
        if m:
            try:
                return m.group(1).strip()
            except IndexError:
                return m.group(0).strip()
    return ""

def find_country(text):
    mappings = [
        (r'\bKorea\b|\bKorean\b', "Korea"),
        (r'\bChina\b|\bChinese\b|\bBeijing\b|\bShanghai\b|\bGuangzhou\b|\bHangzhou\b|\bWuhan\b|\bChengdu\b|\bChongqing\b|\bNanjing\b|\bXi\'an\b|\bShandong\b|\bZhejiang\b|\bFujian\b|\bHunan\b|\bHubei\b|\bJiangsu\b|\bHenan\b|\bSichuan\b|\bLiaoning\b|\bHeilongjiang\b', "China"),
        (r'\bTaiwan\b|\bTaipei\b|\bKaohsiung\b', "Taiwan"),
        (r'\bJapan\b|\bJapanese\b|\bTokyo\b|\bOsaka\b|\bKyoto\b', "Japan"),
        (r'\bIran\b|\bIranian\b|\bTehran\b', "Iran"),
        (r'\bPakistan\b|\bKarachi\b|\bLahore\b', "Pakistan"),
        (r'\bColombia\b|\bBogota\b|\bMedellin\b', "Colombia"),
        (r'\bUnited States\b|\bUSA\b|\bU\.S\.\b|\bAmerica\b|\bMichigan\b|\bCalifornia\b|\bNew Haven\b', "USA"),
        (r'\bEurope\b|\bFrance\b|\bGermany\b|\bSpain\b|\bItaly\b|\bUK\b|\bUnited Kingdom\b', "Europe"),
        (r'\bHong Kong\b', "Hong Kong"),
        (r'\bSingapore\b', "Singapore"),
        (r'\bThailand\b|\bBangkok\b', "Thailand"),
        (r'\bIndia\b|\bIndian\b|\bMumbai\b|\bDelhi\b', "India"),
        (r'\bTurkey\b|\bAnkara\b|\bIstanbul\b', "Turkey"),
    ]
    for pattern, country in mappings:
        if re.search(pattern, text[:3000], re.IGNORECASE):
            return country
    return "Unknown"

def find_study_period(text):
    patterns = [
        r'[Ff]rom\s+([A-Za-z]+\s+\d{4})\s+(?:through|to|until)\s+([A-Za-z]+\s+\d{4})',
        r'[Bb]etween\s+([A-Za-z]+\s+\d{4})\s+and\s+([A-Za-z]+\s+\d{4})',
        r'([A-Za-z]+\s+\d{4})\s+to\s+([A-Za-z]+\s+\d{4})',
        r'(\w+\s+\d{4})\s*[-–]\s*(\w+\s+\d{4})',
        r'[Ff]rom\s+(\w+\s+\d{4})',
        # Year range
        r'(?:conducted|enrolled|collected|recruited).*?(\d{4})\s*[-–to]+\s*(\d{4})',
    ]
    for p in patterns:
        m = re.search(p, text[:5000], re.IGNORECASE)
        if m:
            if m.lastindex and m.lastindex >= 2:
                return m.group(1).strip(), m.group(2).strip()
            elif m.lastindex:
                return m.group(1).strip(), ""
    return "", ""

def find_sample_sizes(text):
    """Return list of (label, N) tuples from randomization/assignment sentences."""
    results = []
    # Pattern: "randomly assigned to X (n=Y)" or "X group (n=Y)"
    patterns = [
        r'(\w+[\w\s]+?)\s*(?:group\s*)?\(n\s*=\s*(\d+)\)',
        r'(\w+[\w\s]+?)\s*(?:arm\s*)?\(n\s*=\s*(\d+)\)',
    ]
    # Simpler: find all n=XX near group labels
    for m in re.finditer(r'(?:group|arm|therapy)\s*\(n\s*=\s*(\d+)\)', text, re.IGNORECASE):
        results.append(int(m.group(1)))
    return results

def find_eradication_rates(text):
    """Extract ITT and PP eradication rates as floats."""
    itt = []
    pp = []
    # ITT patterns
    for m in re.finditer(r'(?:ITT|intention[- ]to[- ]treat)[^\n]{0,200}?(\d{1,3}\.?\d*)\s*%', text, re.IGNORECASE):
        v = float(m.group(1))
        if 30 < v < 101:
            itt.append(v)
    # PP patterns
    for m in re.finditer(r'(?:PP|per[- ]protocol)[^\n]{0,200}?(\d{1,3}\.?\d*)\s*%', text, re.IGNORECASE):
        v = float(m.group(1))
        if 30 < v < 101:
            pp.append(v)
    return itt, pp

def find_adverse_events(text):
    aes = []
    for m in re.finditer(r'adverse[^\n]{0,100}?(\d{1,3}\.?\d*)\s*%', text, re.IGNORECASE):
        v = float(m.group(1))
        if 0 <= v <= 100:
            aes.append(v)
    return aes

def find_duration(text):
    for m in re.finditer(r'(\d+)[- ]day', text[:8000], re.IGNORECASE):
        d = int(m.group(1))
        if d in (7, 10, 14, 21):
            return d
    for m in re.finditer(r'(\d+)\s*weeks?', text[:8000], re.IGNORECASE):
        d = int(m.group(1))
        if 1 <= d <= 4:
            return d * 7
    return None

def classify_regimen(text):
    """Return list of regimen types mentioned in the paper."""
    types = []
    if re.search(r'vonoprazan', text, re.IGNORECASE):
        types.append("vonoprazan_dual" if re.search(r'vonoprazan.{0,50}dual|dual.{0,50}vonoprazan', text, re.IGNORECASE) else "vonoprazan")
    if re.search(r'tegoprazan', text, re.IGNORECASE):
        types.append("tegoprazan")
    if re.search(r'bismuth', text, re.IGNORECASE):
        types.append("quadruple")
    if re.search(r'dual\s+therap', text, re.IGNORECASE):
        types.append("dual")
    if re.search(r'triple\s+therap', text, re.IGNORECASE):
        types.append("triple")
    return list(dict.fromkeys(types))

def find_ppi(text, segment=""):
    t = segment if segment else text[:6000]
    if re.search(r'vonoprazan', t, re.IGNORECASE):
        return "Vonoprazan"
    if re.search(r'tegoprazan', t, re.IGNORECASE):
        return "Tegoprazan"
    if re.search(r'esomeprazole', t, re.IGNORECASE):
        return "Esomeprazole"
    if re.search(r'rabeprazole', t, re.IGNORECASE):
        return "Rabeprazole"
    if re.search(r'lansoprazole', t, re.IGNORECASE):
        return "Lansoprazole"
    if re.search(r'omeprazole', t, re.IGNORECASE):
        return "Omeprazole"
    if re.search(r'pantoprazole', t, re.IGNORECASE):
        return "Pantoprazole"
    return "Unknown"

def find_multicenter(text):
    if re.search(r'multicenter|multi-center|multi center|multiple\s+(?:sites|centers|hospitals|institutions)', text[:5000], re.IGNORECASE):
        return "Yes"
    return "No"

def find_naive_rescue(text):
    if re.search(r'treatment[- ]na[iï]ve|first[- ]line|initial\s+treatment', text[:5000], re.IGNORECASE):
        if re.search(r'rescue|second[- ]line|salvage|refractory|failed', text[:5000], re.IGNORECASE):
            return "Both"
        return "Naive"
    if re.search(r'rescue|second[- ]line|salvage|refractory|failed', text[:5000], re.IGNORECASE):
        return "Rescue"
    return "Naive"

def find_ppi_dose(text):
    """Find PPI doses (mg) mentioned in the paper."""
    doses = {}
    for drug in ["vonoprazan", "tegoprazan", "lansoprazole", "esomeprazole", "rabeprazole", "omeprazole", "pantoprazole"]:
        m = re.search(rf'{drug}\s+(\d+)\s*mg', text[:8000], re.IGNORECASE)
        if m:
            doses[drug] = int(m.group(1))
    return doses

def find_amox_dose(text):
    for m in re.finditer(r'amoxicillin\s+(\d+(?:\.\d+)?)\s*(?:mg|g)', text[:8000], re.IGNORECASE):
        v = float(m.group(1))
        # normalize to mg
        if "g" in text[m.start():m.end()+2].lower() and v < 10:
            v *= 1000
        if 250 <= v <= 4000:
            return int(v)
    return None

def find_clari_dose(text):
    for m in re.finditer(r'clarithromycin\s+(\d+)\s*mg', text[:8000], re.IGNORECASE):
        v = int(m.group(1))
        if 200 <= v <= 1000:
            return v
    return None

def find_total_N(text):
    for m in re.finditer(r'(\d+)\s+patients?\s+(?:were\s+)?(?:randomly\s+)?(?:assigned|randomized|enrolled|included)', text[:5000], re.IGNORECASE):
        n = int(m.group(1))
        if 20 < n < 5000:
            return n
    return None

# ── per-paper extraction definitions ───────────────────────────────────────────
# Each entry: (ref, file, manual data dict)
# manual = fields that are hard to parse automatically

PAPERS = [
    # Ref, file stem, {manual overrides}
    (29, "29_KimSY_2012"),
    (30, "30_HuCT_2017"),
    (31, "31_HuJL_2017"),   # duplicate of 30
    (36, "36_TaiWC_2019"),
    (38, "38_SongZ_2023"),
    (39, "39_SuzukiS_2020"),
    (40, "40_HoriiT_2021"),
    (41, "41_CheyWD_2022"),
    (42, "42_GuanJL_2022"),
    (43, "43_HuY_2022"),
    (44, "44_LinY_2022"),
    (45, "45_CastanoLlanoR_2022"),
    (46, "46_MeiH_2022"),
    (47, "47_NiuM_2022"),
    (48, "48_ShaoQQ_2022"),
    (49, "49_ShenC_2022"),
    (50, "50_YadollahiB_2022"),
    (51, "51_YunJ_2023"),
    (52, "52_ZuberiBF_2022"),
    (53, "53_ChengJ_2023"),
    (54, "54_HanYY_2023"),
    (56, "56_HuJ_2023"),
    (57, "57_HuY_2023"),    # duplicate of 43
    (58, "58_JiangX_2023"),
    (59, "59_LiJ_2023"),
    (61, "61_WangX_2023"),
    (62, "62_YangQ_2023"),
    (63, "63_ZhangXD_2023"),
    (64, "64_ChenC_2024"),
    (65, "65_CheungKS_2024"),
    (66, "66_GaoW_2024"),
    (67, "67_HuY_2024"),
    # Ref 68 removed — duplicate of Ref 88 (Hu 2025 Lancet Microbe; same study, different PDF download)
    (69, "69_KongQ_2024"),
    (70, "70_LiuHN_2024"),
    (71, "71_LiuZ_2024"),
    (72, "72_LiuZ_2024"),
    (73, "73_PengX_2023"),
    (74, "74_YanTL_2024"),  # duplicate of 61
    (75, "75_ParkH_2020"),
    (76, "76_YangF_2023"),
    (77, "77_LiM_2025"),
    (78, "78_YangXE_2025"),
    (79, "79_ZhangJY_2025"),
]

COLUMNS = [
    "Ref", "File", "Duplicate_Of",
    "Country", "Study_Period_Start", "Study_Period_End",
    "Multicenter", "Treatment_Naive_vs_Rescue",
    "Regimen_Types_In_Paper",
    "Total_N_Randomized",
    "Duration_Days",
    "PPI_Types",
    "Amox_Dose_mg_per_dose",
    "Clari_Dose_mg_per_dose",
    "ITT_Rates_All",
    "PP_Rates_All",
    "AE_Rates_All",
    "Notes",
]

DUPLICATES = {31: 30, 57: 43, 74: 61}

rows = []

for entry in PAPERS:
    ref, stem = entry
    fname = f"{stem}.txt"
    fpath = os.path.join(TEXT_DIR, fname)
    if not os.path.exists(fpath):
        print(f"MISSING: {fname}")
        continue

    text = read(fname)
    dup_of = DUPLICATES.get(ref, "")

    country = find_country(text)
    period_start, period_end = find_study_period(text)
    multicenter = find_multicenter(text)
    naive_rescue = find_naive_rescue(text)
    regimens = classify_regimen(text)
    total_n = find_total_N(text)
    duration = find_duration(text)
    ppi_doses = find_ppi_dose(text)
    amox_dose = find_amox_dose(text)
    clari_dose = find_clari_dose(text)
    itt_rates, pp_rates = find_eradication_rates(text)
    ae_rates = find_adverse_events(text)

    row = {
        "Ref": ref,
        "File": stem,
        "Duplicate_Of": dup_of,
        "Country": country,
        "Study_Period_Start": period_start,
        "Study_Period_End": period_end,
        "Multicenter": multicenter,
        "Treatment_Naive_vs_Rescue": naive_rescue,
        "Regimen_Types_In_Paper": "|".join(regimens),
        "Total_N_Randomized": total_n or "",
        "Duration_Days": duration or "",
        "PPI_Types": "|".join(f"{k}:{v}mg" for k, v in ppi_doses.items()),
        "Amox_Dose_mg_per_dose": amox_dose or "",
        "Clari_Dose_mg_per_dose": clari_dose or "",
        "ITT_Rates_All": "|".join(str(x) for x in itt_rates[:6]),
        "PP_Rates_All": "|".join(str(x) for x in pp_rates[:6]),
        "AE_Rates_All": "|".join(str(x) for x in ae_rates[:6]),
        "Notes": "",
    }
    rows.append(row)
    dup_note = f" [DUP of {dup_of}]" if dup_of else ""
    print(f"  Ref {ref:2d} {stem:<25} | {country:<10} | N={total_n or '?':>4} | {duration or '?'}d | regimens={regimens}{dup_note}")

with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(rows)

print(f"\nSaved {len(rows)} rows → {OUT_CSV}")
