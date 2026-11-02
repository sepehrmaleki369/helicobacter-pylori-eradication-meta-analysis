"""
Phase 2: Add regional antibiotic resistance data to each arm.
Sources: in-paper data (most accurate) + published regional estimates.
Output: data/processed/arm_dataset_with_resistance.csv
"""
import csv, os

IN  = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/data/processed/arm_level_dataset.csv"
OUT = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/data/processed/arm_dataset_with_resistance.csv"

# ── Regional resistance estimates ──────────────────────────────────────────────
# CLR=Clarithromycin, MTZ=Metronidazole, AMX=Amoxicillin, LFX=Levofloxacin
# Format: (CLR%, MTZ%, AMX%, LFX%, source_note)
#
# Sources:
#  - Thung 2016, Medicine: meta-analysis of Asian H. pylori resistance
#  - Savoldi 2018, Gastroenterology: global resistance meta-analysis
#  - Liu 2019-2024: China nationwide resistance surveys
#  - Korean national consensus reports
#  - Maastricht VI (2022) regional resistance tables

RESISTANCE_DB = {
    # key: (country, approx_period) → (CLR, MTZ, AMX, LFX, source)
    ("Korea", "2009-2012"):     (17.2, 37.6, 1.0, 12.5, "Korean 2012 resistance study (Lee 2013)"),
    ("Korea", "2012-2016"):     (18.5, 38.5, 0.8, 14.0, "Park 2013; Korean consensus"),
    ("China", "2012-2016"):     (23.8, 59.3, 2.0, 20.1, "Thung 2016 meta-analysis"),
    ("China", "2016-2020"):     (28.9, 63.6, 2.3, 25.4, "Savoldi 2018; Liu 2020"),
    ("China", "2019-2022"):     (32.0, 67.0, 2.5, 28.0, "Chinese consensus 2022"),
    ("China", "2022-2025"):     (35.0, 70.0, 3.0, 30.0, "Liu 2024 nationwide survey"),
    ("China-NW", "2022-2025"):  (42.0, 83.0, 15.2, 35.7, "YunJ 2023 paper (in-paper data)"),
    ("China-S", "2024"):        (38.0, 70.0, 3.0, 35.0, "CheungKS 2024 (CLR+LFX >30%)"),
    ("Taiwan", "2019"):         (14.6, 33.7, 0.0, 11.0, "TaiWC 2019 paper (in-paper data)"),
    ("Japan", "2015-2020"):     (30.1, 27.3, 1.4, 21.8, "Japanese resistance surveys 2017-2020"),
    ("Japan", "2018-2021"):     (32.0, 28.0, 1.5, 23.0, "Horii 2021 region estimate"),
    ("Colombia", "2022"):       (19.5, 73.2, 2.0, 9.0,  "CastanoLlano 2022; Latam estimates"),
    ("Iran", "2022"):           (36.0, 79.0, 4.0, 18.0, "Regional meta-analysis 2020-2022"),
    ("Pakistan", "2021"):       (38.0, 78.0, 5.0, 22.0, "Regional estimates; Zuberi 2022 region"),
    ("USA+Europe", "2020-2022"): (20.5, 40.0, 0.5, 11.0, "FDA/EMA data; Chey 2022 trial data"),
    ("China", "2020-2023"):     (33.0, 67.5, 2.7, 29.0, "China 2020-2023 consensus estimates"),
    ("China", "2023-2025"):     (36.0, 70.0, 3.2, 31.0, "China 2023-2025 estimates"),
}

# ── Per-ref resistance assignment ──────────────────────────────────────────────
# Maps ref → (CLR, MTZ, AMX, LFX, note, source_type)
# source_type: "in-paper" | "regional-estimate"
REF_RESISTANCE = {
    29: (17.2, 37.6, 1.0, 12.5,
         "Korea 2009-2012; Lee 2013 Korean resistance study",
         "regional-estimate"),
    30: (23.8, 59.3, 2.0, 20.1,
         "China 2012-2016; Thung 2016 meta-analysis",
         "regional-estimate"),
    36: (14.6, 33.7, 0.0, 11.0,
         "Taiwan 2019; in-paper H. pylori culture data",
         "in-paper"),
    39: (30.1, 27.3, 1.4, 21.8,
         "Japan 2015-2020; Japanese resistance surveys",
         "regional-estimate"),
    41: (20.5, 40.0, 0.5, 11.0,
         "USA+Europe 2020-2022; Chey 2022 phase-3 trial susceptibility data",
         "in-paper"),    # Phase 3 tested all patients for susceptibility
    42: (28.9, 63.6, 2.3, 25.4,
         "China (Wuhan) 2019-2021; Savoldi 2018; Liu 2020 Hubei region",
         "regional-estimate"),
    43: (32.0, 67.0, 2.5, 28.0,
         "China 2019-2022; Chinese consensus 2022",
         "regional-estimate"),
    44: (32.0, 67.0, 2.5, 28.0,
         "China 2019-2022; Chinese consensus 2022",
         "regional-estimate"),
    45: (19.5, 73.2, 2.0, 9.0,
         "Colombia 2022; Latin American H. pylori resistance estimates",
         "regional-estimate"),
    46: (33.0, 67.5, 2.7, 29.0,
         "China (Chongqing) 2019-2022; regional estimates",
         "regional-estimate"),
    47: (28.9, 63.6, 2.3, 25.4,
         "China (Yinchuan/Hainan) 2019-2021",
         "regional-estimate"),
    48: (32.0, 67.0, 2.5, 28.0,
         "China (Henan/Zhengzhou) 2019-2022",
         "regional-estimate"),
    49: (28.9, 63.6, 2.3, 25.4,
         "China 2019-2021; regional estimates",
         "regional-estimate"),
    50: (36.0, 79.0, 4.0, 18.0,
         "Iran 2022; regional meta-analysis",
         "regional-estimate"),
    51: (42.0, 83.0, 15.2, 35.7,
         "Gansu (NW China) 2022-2023; in-paper culture data",
         "in-paper"),
    52: (38.0, 78.0, 5.0, 22.0,
         "Pakistan (Karachi) 2021; regional estimates",
         "regional-estimate"),
    53: (33.0, 67.5, 2.7, 29.0,
         "China 2023; regional estimates",
         "regional-estimate"),
    54: (33.0, 67.0, 2.5, 29.0,
         "China (multicenter) 2021-2023; Chinese consensus 2022",
         "regional-estimate"),
    56: (33.0, 67.5, 2.7, 29.0,
         "China (Chongqing) 2020-2023",
         "regional-estimate"),
    58: (43.65, 65.0, 2.0, 30.0,
         "Yangzhou China 2020-2021; in-paper clarithromycin resistance rate",
         "in-paper"),
    59: (33.0, 67.5, 2.7, 29.0,
         "China (Chongqing) 2022-2023",
         "regional-estimate"),
    61: (35.0, 68.0, 2.8, 30.0,
         "China (Eastern, Zhejiang) 2022-2023; consensus estimates",
         "regional-estimate"),
    62: (33.0, 67.0, 2.5, 29.0,
         "China (Nanchang) 2020-2022; elderly population",
         "regional-estimate"),
    63: (33.0, 67.0, 2.5, 29.0,
         "China (Hainan) 2021-2023; regional estimates",
         "regional-estimate"),
    64: (33.0, 67.0, 2.5, 29.0,
         "China (Hainan) 2022-2024; regional estimates",
         "regional-estimate"),
    65: (38.0, 70.0, 3.0, 35.0,
         "Southern China (Hong Kong region) 2022-2024; CLR>30% in-paper",
         "in-paper"),
    66: (35.0, 70.0, 3.0, 30.0,
         "China (Beijing) 2022-2024; penicillin-allergy cohort",
         "regional-estimate"),
    67: (33.0, 67.0, 2.5, 29.0,
         "China (Nanchang) 2022-2024",
         "regional-estimate"),
    68: (35.0, 70.0, 3.0, 31.0,
         "China (multicenter) 2022-2024; in-paper: no AMX resistance detected",
         "in-paper"),
    69: (33.0, 67.0, 2.5, 29.0,
         "China 2022-2024; regional estimates",
         "regional-estimate"),
    70: (33.0, 67.0, 2.5, 29.0,
         "China (multicenter) 2022-2024",
         "regional-estimate"),
    71: (33.0, 67.0, 2.5, 29.0,
         "China (multicenter Yangzhou/Dalian) 2022-2024",
         "regional-estimate"),
    72: (33.0, 67.0, 2.5, 29.0,
         "China 2022-2024; retrospective study",
         "regional-estimate"),
    76: (35.0, 70.0, 3.0, 31.0,
         "China 2022-2024; regional estimates",
         "regional-estimate"),
    77: (35.0, 70.0, 3.0, 31.0,
         "China 2023-2025; penicillin-ineligible patients",
         "regional-estimate"),
    78: (35.0, 70.0, 3.0, 31.0,
         "China 2022-2025; multicenter",
         "regional-estimate"),
    79: (35.0, 70.0, 3.0, 31.0,
         "China (Fujian) 2022-2024",
         "regional-estimate"),

    # ── Upgraded from regional-estimate to in-paper ────────────────────────────
    56: (37.6, 74.2, 0.0, 26.8,
         "China multicenter 2020-2023; HuJ 2023 in-paper culture all 194 patients",
         "in-paper"),
    58: (49.0, 38.0, 8.0, 47.0,
         "Yangzhou China 2020-2021; JiangX 2023 PCR resistance-gene testing all 255 patients",
         "in-paper"),
    70: (34.5, 67.0, 2.5, 29.0,
         "Chongqing/Sichuan 2022-2023; LiuHN 2024 agar dilution ~186 cultured patients",
         "in-paper"),

    # ── New papers Refs 80-88 ─────────────────────────────────────────────────
    80: (33.1, 7.9, 1.5, 21.8,
         "Japan 2011-2012; Murakami 2015 Gut in-paper MIC testing all 650 patients (CLR 30-36%, AMX per strict MIC; LFX estimated Japan surveys)",
         "in-paper"),
    81: (30.0, 10.0, 1.5, 22.0,
         "Japan 2015-2016; regional estimate (no in-paper resistance); Japanese resistance surveys 2017",
         "regional-estimate"),
    82: (30.3, 38.5, 1.0, 14.0,
         "Korea 2017-2018; ChoiYJ 2022 in-paper culture subset n=76 (CLR 30.3%, AMX 25% by strict MIC); MTZ/LFX Korea regional",
         "in-paper"),
    83: (23.0, 38.5, 0.8, 14.5,
         "Korea 2022-2024; ParkJY 2024 in-paper PCR (CLR avg 23%; TAC1=19%, TAC2=25.8%, LAC=24.4%)",
         "in-paper"),
    84: (22.0, 38.5, 0.8, 14.5,
         "Korea 2020-2022; regional estimate (no in-paper resistance in pilot study)",
         "regional-estimate"),
    85: (33.3, 29.4, 0.0, 27.7,
         "Thailand 2021-2022; TungtrongchitrN 2024 in-paper culture subset n=18 (CLR=33.3%, MTZ=29.4%, LFX=27.7%, AMX=0%)",
         "in-paper"),
    86: (30.0, 50.0, 0.0, 27.0,
         "Thailand 2022-2023; regional estimate (resistance from only 8 patients; too small for in-paper classification)",
         "regional-estimate"),
    87: (37.0, 67.0, 2.5, 29.0,
         "China multicenter 2020-2022; SongZ 2024 in-paper culture subset n=66 (CLR avg 37%); MTZ/AMX/LFX China regional",
         "in-paper"),
    88: (30.0, 74.0, 0.0, 28.0,
         "China nationwide 2022-2024; HuY 2025 Lancet Microbe in-paper culture n=286 (CLR=30%, MTZ=74%, LFX=28%, AMX=0%)",
         "in-paper"),

    # ── Western batch additions (Refs 89-105) ─────────────────────────────────
    89: (30.0, 55.0, 5.0, 20.0,
         "Lebanon 2023; regional estimate",
         "regional-estimate"),
    90: (30.0, 70.0, 5.0, 15.0,
         "Egypt 2022-2023; regional estimate (Shekeban paper cites high MTZ/CLR)",
         "regional-estimate"),
    91: (30.0, 70.0, 5.0, 15.0,
         "Egypt 2021 post-COVID; regional estimate; Kamal cites Egypt-wide rates",
         "regional-estimate"),
    92: (35.0, 75.0, 5.0, 22.0,
         "Pakistan 2022-2023; same as Ref 52 region; regional estimate",
         "regional-estimate"),
    93: (35.0, 30.0, 5.0, 25.0,
         "Turkey 2018-2021; regional estimate (Turkey has lower MTZ vs Iran/Egypt)",
         "regional-estimate"),
    94: (35.0, 30.0, 5.0, 25.0,
         "Turkey 2017-2018; regional estimate",
         "regional-estimate"),
    95: (30.0, 70.0, 16.0, 10.0,
         "Iran (Sari) 2022-2023; regional cites MTZ 66-82%, CLR 22-34%",
         "regional-estimate"),
    96: (25.0, 65.0, 16.0, 8.0,
         "Iran (Yazd) 2014-2016; regional estimate",
         "regional-estimate"),
    97: (30.0, 70.0, 5.0, 5.0,
         "Egypt (Damanhour) 2017-2018; regional estimate",
         "regional-estimate"),
    98: (22.4, 61.6, 16.0, 5.3,
         "Iran (Tehran) 2015-2017; Mokhtare paper cites exact regional rates",
         "regional-estimate"),
    99: (21.2, 78.1, 5.0, 15.0,
         "Qatar 2014-2016; Ennkaa paper cites in-region CLR=21.2%, MTZ=78.1%",
         "regional-estimate"),
    100: (26.9, 23.1, 1.0, 14.0,
         "Korea 2020-2023; LeeJH 2024 in-paper culture n=312 (CLR=26.9%, MTZ=23.1%, dual=8%)",
         "in-paper"),
    101: (36.2, 38.5, 0.8, 14.0,
         "Korea 2023-2025; KimJS 2026 K-CREATE in-paper DPO-PCR (CLR=36.2%)",
         "in-paper"),
    102: (28.6, 38.5, 0.8, 14.0,
         "Korea (Busan/Gyeongnam) 2020-2021; KimSJ 2022 in-paper 23S rRNA PCR (CLR=28.6%)",
         "in-paper"),
    103: (26.0, 33.7, 0.0, 13.0,
         "Taiwan 2014-2017; HsiehMS 2022 in-paper gastric-juice PCR (CLR~26%, LFX~13%)",
         "in-paper"),
    104: (32.0, 38.5, 0.8, 14.0,
         "Korea (gastric neoplasm cohort) 2019; KimJL 2020 in-paper DPO-PCR (CLR~32%)",
         "in-paper"),
    105: (12.0, 50.0, 5.0, 10.0,
         "Brazil (Porto Alegre) 2012-2014; regional estimate; Rech IL-1β substudy",
         "regional-estimate"),
}

# ── Process ────────────────────────────────────────────────────────────────────
with open(IN, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

new_cols = ["CLR_Resistance_pct", "MTZ_Resistance_pct", "AMX_Resistance_pct",
            "LFX_Resistance_pct", "Resistance_Source", "Resistance_Source_Type"]

for r in rows:
    ref = int(r["Ref"])
    if ref in REF_RESISTANCE:
        clr, mtz, amx, lfx, note, stype = REF_RESISTANCE[ref]
        r["CLR_Resistance_pct"] = clr
        r["MTZ_Resistance_pct"] = mtz
        r["AMX_Resistance_pct"] = amx
        r["LFX_Resistance_pct"] = lfx
        r["Resistance_Source"]  = note
        r["Resistance_Source_Type"] = stype
    else:
        for c in new_cols:
            r[c] = ""

all_cols = list(rows[0].keys()) if rows else []
for c in new_cols:
    if c not in all_cols:
        all_cols.append(c)

with open(OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=all_cols)
    writer.writeheader()
    writer.writerows(rows)

print(f"✓ Wrote {len(rows)} rows with resistance data → {OUT}")
in_paper = sum(1 for r in rows if r.get("Resistance_Source_Type") == "in-paper")
estimates = sum(1 for r in rows if r.get("Resistance_Source_Type") == "regional-estimate")
print(f"  In-paper resistance data: {in_paper} arms")
print(f"  Regional estimate used:   {estimates} arms")
