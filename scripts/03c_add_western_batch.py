"""
Phase 1c — Add 17 new papers (Refs 89–105):
  - Middle East: Lebanon (89), Egypt (90, 91, 97), Iran (95, 96, 98), Qatar (99)
  - South Asia: Pakistan (92)
  - Middle East/Turkey: 93, 94
  - East Asia susceptibility-guided: 100, 101, 102, 103, 104
  - Latin America: Brazil 105

Also adds `Is_Susceptibility_Guided` column.
Reads arm_level_dataset.csv (already includes prior 80–88 batch), patches it, writes back.
"""
import csv, os

IN  = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/data/processed/arm_level_dataset.csv"
OUT = IN

with open(IN, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    COLS = list(reader.fieldnames)
    rows = list(reader)

# Add new column if not present
if "Is_Susceptibility_Guided" not in COLS:
    COLS.append("Is_Susceptibility_Guided")
    for r in rows:
        r["Is_Susceptibility_Guided"] = ""

# IDEMPOTENT: remove any prior Refs 89-105 rows so we can re-run cleanly
NEW_REFS = set(range(89, 106))
before = len(rows)
rows = [r for r in rows if int(r["Ref"]) not in NEW_REFS]
removed = before - len(rows)
print(f"Removed {removed} existing rows for Refs 89-105 (idempotent rebuild)")

def R(ref, file, country, region, start, end, multicenter, naive_rescue,
      design, quality,
      arm, ttype, is_interv, suscept_guided,
      ppi, ppi_dose, ppi_freq,
      amox_dose, amox_freq,
      clari_dose, clari_freq,
      metro_dose, metro_freq,
      bismuth, other_ab, other_ab_mg,
      duration, n_itt, n_pp,
      itt, pp, ae,
      amox_daily, ppi_daily,
      notes, age="", compliance=""):
    return {
        "Ref": ref, "File": file, "Country": country, "Geographic_Region": region,
        "Study_Period_Start": start, "Study_Period_End": end,
        "Multicenter": multicenter, "Treatment_Naive_vs_Rescue": naive_rescue,
        "Study_Design": design, "Study_Quality_Flag": quality,
        "Arm_Label": arm, "Treatment_Type": ttype, "Arm_Is_Intervention": is_interv,
        "Is_Susceptibility_Guided": suscept_guided,
        "PPI": ppi, "PPI_Dose_mg": ppi_dose, "PPI_Freq_per_day": ppi_freq,
        "Amoxicillin_mg_per_dose": amox_dose, "Amoxicillin_freq_per_day": amox_freq,
        "Clarithromycin_mg_per_dose": clari_dose, "Clarithromycin_freq_per_day": clari_freq,
        "Metronidazole_mg_per_dose": metro_dose, "Metronidazole_freq_per_day": metro_freq,
        "Bismuth_used": bismuth, "Other_Antibiotic": other_ab, "Other_Antibiotic_mg": other_ab_mg,
        "Duration_Days": duration, "N_ITT": n_itt, "N_PP": n_pp,
        "ITT_Rate": itt, "PP_Rate": pp, "AE_Rate": ae,
        "Total_Amox_Daily_mg": amox_daily, "Total_PPI_Daily_mg": ppi_daily,
        "Notes": notes, "Mean_Age_yr": age, "Compliance_pct": compliance,
    }

new_arms = [
    # ── Ref 89: Elias 2025 (Lebanon) — 3 arms, rabeprazole concomitant ────────
    R(89, "89_EliasM_2025_Lebanon", "Lebanon", "Middle East", "2023", "2023", "No", "Naive",
      "RCT", "",
      "RPZ-Conc-14d", "nonbismuth_quadruple", 0, 0,
      "Rabeprazole", 20, 2, 1000, 2, 500, 2, 500, 2,
      0, "", "", 14, 38, 38, 94.7, 94.7, "",
      2000, 40, "Lebanon pilot RCT; standard concomitant", 52.4, 99.3),
    R(89, "89_EliasM_2025_Lebanon", "Lebanon", "Middle East", "2023", "2023", "No", "Naive",
      "RCT", "",
      "RPZ-Conc-DD-10d", "nonbismuth_quadruple", 1, 0,
      "Rabeprazole", 20, 2, 1000, 2, 500, 2, 500, 2,
      0, "", "", 10, 37, 30, 67.6, 83.3, "",
      2000, 40, "Lebanon double-dose concomitant 10d", 57.2, 98.1),
    R(89, "89_EliasM_2025_Lebanon", "Lebanon", "Middle East", "2023", "2023", "No", "Naive",
      "RCT", "",
      "RPZ-Conc-HD-10d", "nonbismuth_quadruple", 1, 0,
      "Rabeprazole", 20, 3, 1000, 2, 500, 2, 500, 2,
      0, "", "", 10, 38, 33, 86.8, 100.0, "",
      2000, 60, "Lebanon high-dose PPI 60mg/d concomitant 10d", 46.8, 97.6),

    # ── Ref 90: Shekeban 2025 (Egypt) — 3 arms; use mITT (drop-outs excluded) ──
    # Per agent extraction: STT mITT=70.8%(17/24), VDT mITT=77.3%(17/22), VTT mITT=76.9%(20/26)
    # Original ITT was "worst-case" counting all 44 randomized with dropouts as failures
    R(90, "90_ShekebanYM_2025_Egypt", "Egypt", "Middle East", "2022", "2023", "No", "Naive",
      "RCT", "dropout-heavy",
      "STT-Standard-Triple", "triple", 0, 0,
      "Pantoprazole", 20, 2, 875, 2, 500, 2, "", "",
      0, "", "", 14, 24, 20, 70.8, 70.0, "",
      1750, 40, "Egypt; STT comparator; used mITT (excludes 20 dropouts from N=44)", 35.5, ""),
    R(90, "90_ShekebanYM_2025_Egypt", "Egypt", "Middle East", "2022", "2023", "No", "Naive",
      "RCT", "dropout-heavy",
      "VDT-Vonoprazan-Dual", "dual", 1, 0,
      "Vonoprazan", 20, 2, 875, 3, "", "", "", "",
      0, "", "", 14, 22, 21, 77.3, 76.2, "",
      2625, 40, "Egypt; vonoprazan dual; used mITT (excludes 22 dropouts)", 31.0, ""),
    R(90, "90_ShekebanYM_2025_Egypt", "Egypt", "Middle East", "2022", "2023", "No", "Naive",
      "RCT", "dropout-heavy",
      "VTT-Vonoprazan-Triple", "triple", 1, 0,
      "Vonoprazan", 20, 2, 875, 2, 500, 2, "", "",
      0, "", "", 14, 26, 24, 76.9, 79.2, "",
      1750, 40, "Egypt; vonoprazan triple; used mITT (excludes 18 dropouts)", 37.0, ""),

    # ── Ref 91: Kamal 2023 (Egypt) — 2 arms, CLR vs LFX ───────────────────────
    R(91, "91_KamalA_2023_Egypt", "Egypt", "Middle East", "2021", "2021", "No", "Naive",
      "RCT", "post-COVID-cohort",
      "ESO-CLR-Triple", "triple", 0, 0,
      "Esomeprazole", 40, 2, 1000, 2, 500, 2, "", "",
      0, "", "", 14, 135, 116, 55.6, 64.7, "",
      2000, 80, "Egypt post-COVID cohort; standard CLR triple", 41.3, ""),
    R(91, "91_KamalA_2023_Egypt", "Egypt", "Middle East", "2021", "2021", "No", "Naive",
      "RCT", "post-COVID-cohort",
      "ESO-LFX-Triple", "triple", 1, 0,
      "Esomeprazole", 40, 2, 1000, 2, "", "", "", "",
      0, "Levofloxacin", 500, 14, 135, 117, 64.4, 74.4, "",
      2000, 80, "Egypt post-COVID; LFX 500mg QD alternative", 42.9, ""),

    # ── Ref 92: Waqar 2024 (Pakistan) — 2 arms, EAL vs VAL ────────────────────
    R(92, "92_WaqarF_2024_Pakistan", "Pakistan", "South Asia", "2022", "2023", "No", "Naive",
      "RCT", "",
      "EAL-Esomeprazole-Triple", "triple", 0, 0,
      "Esomeprazole", 20, 2, 1000, 2, "", "", "", "",
      0, "Levofloxacin", 500, 14, 61, 61, 93.4, 93.4, "",
      2000, 40, "Pakistan single center; EAL standard 14d", 38.4, 100.0),
    R(92, "92_WaqarF_2024_Pakistan", "Pakistan", "South Asia", "2022", "2023", "No", "Naive",
      "RCT", "",
      "VAL-Vonoprazan-Triple-7d", "triple", 1, 0,
      "Vonoprazan", 20, 2, 1000, 2, "", "", "", "",
      0, "Levofloxacin", 500, 7, 61, 61, 95.0, 95.0, "",
      2000, 40, "Pakistan; vonoprazan 7d triple equivalent to 14d ESO", 41.0, 100.0),

    # ── Ref 93: Koroglu 2022 (Turkey) — 4 arms ────────────────────────────────
    R(93, "93_KorogluM_2022_Turkey", "Turkey", "Middle East", "2018", "2021", "No", "Naive",
      "RCT", "",
      "sTT-Standard-Triple", "triple", 0, 0,
      "Lansoprazole", 30, 2, 1000, 2, 500, 2, "", "",
      0, "", "", 14, 76, 70, 68.4, 74.3, "",
      2000, 60, "Turkey; standard triple", 48.5, 95.9),
    R(93, "93_KorogluM_2022_Turkey", "Turkey", "Middle East", "2018", "2021", "No", "Naive",
      "RCT", "atypical-BQT-includes-CLR",
      "BQT-with-CLR", "quadruple", 1, 0,
      "Lansoprazole", 30, 2, 1000, 2, 500, 2, "", "",
      1, "Bismuth_subsalicylate", 262, 14, 78, 70, 79.5, 88.6, "",
      2000, 60, "Turkey; atypical BQT containing clarithromycin", 49.0, 94.6),
    R(93, "93_KorogluM_2022_Turkey", "Turkey", "Middle East", "2018", "2021", "No", "Naive",
      "RCT", "",
      "Sequential-10d", "nonbismuth_quadruple", 1, 0,
      "Esomeprazole", 40, 2, 1000, 2, 500, 2, 500, 2,
      0, "", "", 10, 75, 68, 78.7, 86.8, "",
      2000, 80, "Turkey; sequential (5d AMX → 5d CLR+MTZ)", 48.5, 94.4),
    R(93, "93_KorogluM_2022_Turkey", "Turkey", "Middle East", "2018", "2021", "No", "Naive",
      "RCT", "",
      "Hybrid-14d", "nonbismuth_quadruple", 1, 0,
      "Esomeprazole", 40, 2, 1000, 2, 500, 2, 500, 2,
      0, "", "", 14, 74, 67, 83.8, 92.5, "",
      2000, 80, "Turkey; hybrid (7d AMX then 7d quad)", 47.5, 94.4),

    # ── Ref 94: Özer Etik 2019 (Turkey) — 4 arms BQT duration ─────────────────
    R(94, "94_OzerEtikD_2019_Turkey", "Turkey", "Middle East", "2017", "2018", "Yes", "Naive",
      "RCT", "",
      "BQT-14d", "quadruple", 0, 0,
      "Esomeprazole", 40, 2, "", "", "", "", 500, 3,
      1, "Tetracycline", 500, 14, 54, 49, 87.0, 96.0, 44.4,
      "", 80, "Turkey; classic BQT 14d (ESO+Bis+MTZ+TET)", 44.0, ""),
    R(94, "94_OzerEtikD_2019_Turkey", "Turkey", "Middle East", "2017", "2018", "Yes", "Naive",
      "RCT", "",
      "BQT-10d", "quadruple", 1, 0,
      "Esomeprazole", 40, 2, "", "", "", "", 500, 3,
      1, "Tetracycline", 500, 10, 54, 50, 85.0, 92.0, 33.5,
      "", 80, "Turkey; BQT 10d shorter", 40.0, ""),
    R(94, "94_OzerEtikD_2019_Turkey", "Turkey", "Middle East", "2017", "2018", "Yes", "Naive",
      "RCT", "",
      "MBCT-14d", "quadruple", 1, 0,
      "Esomeprazole", 40, 2, 1000, 2, "", "", "", "",
      1, "Moxifloxacin", 500, 14, 54, 53, 81.4, 83.0, 16.6,
      2000, 80, "Turkey; moxifloxacin-bismuth combined 14d", 43.0, ""),
    R(94, "94_OzerEtikD_2019_Turkey", "Turkey", "Middle East", "2017", "2018", "Yes", "Naive",
      "RCT", "",
      "MBCT-10d", "quadruple", 1, 0,
      "Esomeprazole", 40, 2, 1000, 2, "", "", "", "",
      1, "Moxifloxacin", 500, 10, 54, 54, 72.2, 72.2, 9.2,
      2000, 80, "Turkey; moxifloxacin-bismuth 10d (lowest performer)", 41.0, ""),

    # ── Ref 95: Valizadeh Toosi 2024 (Iran) — 2 arms ──────────────────────────
    R(95, "95_ValizadehToosi_2024_Iran", "Iran", "Middle East", "2022", "2023", "No", "Naive",
      "RCT", "",
      "Concomitant-Quad-12d", "nonbismuth_quadruple", 0, 0,
      "Pantoprazole", 40, 2, 1000, 2, 500, 2, 500, 2,
      0, "", "", 12, 109, 104, 86.2, 90.4, 35.8,
      2000, 80, "Iran (Sari); standard concomitant", 44.0, 87.2),
    R(95, "95_ValizadehToosi_2024_Iran", "Iran", "Middle East", "2022", "2023", "No", "Naive",
      "RCT", "",
      "HDDT-14d", "dual", 1, 0,
      "Esomeprazole", 40, 2, 1000, 3, "", "", "", "",
      0, "", "", 14, 114, 110, 76.3, 79.1, 12.3,
      3000, 80, "Iran; HDDT (high-dose dual); lower than concomitant", 49.0, 93.0),

    # ── Ref 96: Salmanroghani 2018 (Iran) — 2 arms, DU patients ──────────────
    R(96, "96_SalmanroghaniH_2018_Iran", "Iran", "Middle East", "2014", "2016", "No", "Naive",
      "RCT", "duodenal-ulcer-only",
      "AMX-BQT-14d", "quadruple", 1, 0,
      "Omeprazole", 20, 2, 1000, 3, "", "", 500, 3,
      1, "", "", 14, 113, 110, 92.9, 95.5, 43.4,
      3000, 40, "Iran (Yazd); amoxicillin-bismuth quadruple in DU patients", 41.8, 98.2),
    R(96, "96_SalmanroghaniH_2018_Iran", "Iran", "Middle East", "2014", "2016", "No", "Naive",
      "RCT", "duodenal-ulcer-only",
      "TET-BQT-14d", "quadruple", 0, 0,
      "Omeprazole", 20, 2, "", "", "", "", 500, 3,
      1, "Tetracycline", 500, 14, 115, 105, 76.5, 83.8, 65.2,
      "", 40, "Iran; classic tetracycline-bismuth quadruple", 39.8, 91.3),

    # ── Ref 97: Elkhodary 2020 (Egypt) — 2 arms LFX-dexlansoprazole ──────────
    R(97, "97_ElkhodaryNM_2020_Egypt", "Egypt", "Middle East", "2017", "2018", "No", "Naive",
      "RCT", "small-pilot",
      "LAD-7d", "triple", 1, 0,
      "Dexlansoprazole", 60, 1, 1000, 2, "", "", "", "",
      0, "Levofloxacin", 500, 7, 33, 33, 63.6, 63.6, 0.0,
      2000, 60, "Egypt; LAD 7d small pilot", "", 100.0),
    R(97, "97_ElkhodaryNM_2020_Egypt", "Egypt", "Middle East", "2017", "2018", "No", "Naive",
      "RCT", "small-pilot",
      "LAD-10d", "triple", 1, 0,
      "Dexlansoprazole", 60, 1, 1000, 2, "", "", "", "",
      0, "Levofloxacin", 500, 10, 33, 33, 90.9, 90.9, 3.0,
      2000, 60, "Egypt; LAD 10d significantly better than 7d", "", 100.0),

    # ── Ref 98: Mokhtare 2020 (Iran) — 2 arms LFX-seq vs CLR-seq ─────────────
    R(98, "98_MokhtareM_2020_Iran", "Iran", "Middle East", "2015", "2017", "No", "Naive",
      "RCT", "",
      "LFX-Sequential-10d", "nonbismuth_quadruple", 1, 0,
      "Esomeprazole", 40, 2, 1000, 2, "", "", 500, 2,
      0, "Levofloxacin", 500, 10, 94, 86, 85.1, 93.0, "",
      2000, 80, "Iran (Tehran); LFX-tinidazole sequential", 42.3, 97.8),
    R(98, "98_MokhtareM_2020_Iran", "Iran", "Middle East", "2015", "2017", "No", "Naive",
      "RCT", "",
      "CLR-Sequential-10d", "nonbismuth_quadruple", 0, 0,
      "Esomeprazole", 40, 2, 1000, 2, 500, 2, 500, 2,
      0, "", "", 10, 92, 86, 83.7, 90.0, "",
      2000, 80, "Iran; CLR-tinidazole sequential", 42.3, 98.9),

    # ── Ref 99: Ennkaa 2018 (Qatar) — 3 arms ──────────────────────────────────
    R(99, "99_EnnkaaA_2018", "Qatar", "Middle East", "2014", "2016", "No", "Naive",
      "RCT", "",
      "TT-10d", "triple", 0, 0,
      "Pantoprazole", 40, 2, 1000, 2, 500, 2, "", "",
      0, "", "", 10, 62, 43, 45.0, 65.1, 37.1,
      2000, 80, "Qatar (Doha); 10d standard triple", 36.4, ""),
    R(99, "99_EnnkaaA_2018", "Qatar", "Middle East", "2014", "2016", "No", "Naive",
      "RCT", "",
      "TT-14d", "triple", 1, 0,
      "Pantoprazole", 40, 2, 1000, 2, 500, 2, "", "",
      0, "", "", 14, 73, 58, 54.8, 69.0, 39.7,
      2000, 80, "Qatar; 14d triple", 39.8, ""),
    R(99, "99_EnnkaaA_2018", "Qatar", "Middle East", "2014", "2016", "No", "Naive",
      "RCT", "",
      "Sequential-10d", "nonbismuth_quadruple", 1, 0,
      "Pantoprazole", 40, 2, 1000, 2, 500, 2, 500, 2,
      0, "", "", 10, 71, 51, 50.7, 70.6, 43.7,
      2000, 80, "Qatar; 10d sequential", 40.0, ""),

    # ── Ref 100: Lee JH 2024 (Korea) — culture-tailored vs concomitant ────────
    R(100, "100_LeeJH_2024_Korea_tailored", "Korea", "East Asia", "2020", "2023", "Yes", "Naive",
      "RCT", "",
      "Culture-Tailored-10d", "triple", 1, 1,
      "Lansoprazole", 30, 2, 1000, 2, "mixed", "", "mixed", "",
      0, "", "", 10, 234, 212, 84.2, 92.9, "",
      2000, 60, "Korea; culture-based 4 sub-regimens by susceptibility (PAC/PAM/PBTM)", 60.1, ""),
    R(100, "100_LeeJH_2024_Korea_tailored", "Korea", "East Asia", "2020", "2023", "Yes", "Naive",
      "RCT", "",
      "Empirical-Concomitant-10d", "nonbismuth_quadruple", 0, 0,
      "Lansoprazole", 30, 2, 1000, 2, 500, 2, 500, 2,
      0, "", "", 10, 78, 71, 83.3, 91.5, "",
      2000, 60, "Korea; empirical concomitant", 60.5, ""),

    # ── Ref 101: Kim JS 2026 (Korea K-CREATE) ─────────────────────────────────
    R(101, "101_KimJS_2026_Korea_KCREATE", "Korea", "East Asia", "2023", "2025", "Yes", "Naive",
      "RCT", "",
      "Empirical-Triple-14d", "triple", 0, 0,
      "Pantoprazole", 40, 2, 1000, 2, 500, 2, "", "",
      0, "", "", 14, 55, 53, 65.5, 67.9, 25.5,
      2000, 80, "Korea K-CREATE; empirical 14d triple", 59.0, 100.0),
    R(101, "101_KimJS_2026_Korea_KCREATE", "Korea", "East Asia", "2023", "2025", "Yes", "Naive",
      "RCT", "",
      "PCR-Tailored-7d", "triple", 1, 1,
      "Pantoprazole", 40, 2, 1000, 2, "mixed", "", "mixed", "",
      0, "", "", 7, 47, 45, 82.9, 86.7, 31.9,
      2000, 80, "Korea K-CREATE; DPO-PCR tailored 7d (TT if wt, BQT if mut)", 58.7, 97.8),

    # ── Ref 102: Kim SJ 2022 (Korea 23S rRNA) ─────────────────────────────────
    R(102, "102_KimSJ_2022_Korea_23SrRNA", "Korea", "East Asia", "2020", "2021", "Yes", "Naive",
      "RCT", "",
      "Empirical-Concomitant-14d", "nonbismuth_quadruple", 0, 0,
      "Rabeprazole", 20, 2, 1000, 2, 500, 2, 500, 2,
      0, "", "", 14, 145, 132, 82.8, 88.6, 18.7,
      2000, 40, "Korea (Busan/Gyeongnam); empirical concomitant", 59.5, ""),
    R(102, "102_KimSJ_2022_Korea_23SrRNA", "Korea", "East Asia", "2020", "2021", "Yes", "Naive",
      "RCT", "",
      "PCR-Tailored-14d", "triple", 1, 1,
      "Rabeprazole", 20, 2, 1000, 2, "mixed", "", "mixed", "",
      0, "", "", 14, 145, 129, 85.5, 94.6, 23.3,
      2000, 40, "Korea; PCR-tailored (TT if mut-, BQT if mut+)", 57.1, ""),

    # ── Ref 103: Hsieh 2022 (Taiwan, gastric juice PCR) ───────────────────────
    R(103, "103_HsiehMS_2022_Taiwan_PCR", "Taiwan", "East Asia", "2014", "2017", "No", "Naive",
      "RCT", "",
      "SGT-Juice-PCR-Guided", "triple", 1, 1,
      "Rabeprazole", 20, 2, 1000, 2, "mixed", "", "", "",
      0, "Levofloxacin", "mixed", 7, 91, 89, 89.0, 91.0, "",
      2000, 40, "Taiwan; gastric juice PCR guided (TT/LFX/dual-R hybrid)", 55.1, ""),
    R(103, "103_HsiehMS_2022_Taiwan_PCR", "Taiwan", "East Asia", "2014", "2017", "No", "Naive",
      "RCT", "",
      "STT-Empirical-7d", "triple", 0, 0,
      "Rabeprazole", 20, 2, 1000, 2, 500, 2, "", "",
      0, "", "", 7, 91, 87, 75.8, 79.3, "",
      2000, 40, "Taiwan; empirical standard triple 7d", 54.4, ""),

    # ── Ref 104: Kim JL 2020 (Korea) — gastric neoplasm cohort (FLAGGED) ─────
    R(104, "104_KimJL_2020_Korea_neoplasm", "Korea", "East Asia", "2019", "2019", "No", "Naive",
      "RCT", "gastric-neoplasm-MALT-cohort",
      "Empirical-Triple-10d", "triple", 0, 0,
      "Esomeprazole", 40, 2, 1000, 2, 500, 2, "", "",
      0, "", "", 10, 36, 33, 75.0, 81.8, "",
      2000, 80, "Korea; gastric neoplasm/MALT cohort; empirical", "", ""),
    R(104, "104_KimJL_2020_Korea_neoplasm", "Korea", "East Asia", "2019", "2019", "No", "Naive",
      "RCT", "gastric-neoplasm-MALT-cohort",
      "PCR-Tailored-10d", "triple", 1, 1,
      "Esomeprazole", 40, 2, 1000, 2, "mixed", "", "mixed", "",
      0, "", "", 10, 36, 33, 88.9, 97.0, "",
      2000, 80, "Korea; gastric neoplasm; PCR-tailored", "", ""),

    # ── Ref 105: Rech 2018 (Brazil) — single pooled arm ──────────────────────
    R(105, "105_RechTF_2018_Brazil_polymorphism", "Brazil", "Latin America", "2012", "2014", "No", "Naive",
      "RCT", "host-genotype-substudy",
      "OAC-Triple-10d", "triple", 0, 0,
      "Omeprazole", 20, 2, 1000, 2, 500, 2, "", "",
      0, "", "", 10, 149, 148, 86.6, 87.2, "",
      2000, 40, "Brazil; HEROES sub-study; IL-1β stratified; pooled rate reported", 46.1, 94.6),
]

print(f"Adding {len(new_arms)} new arms from 17 papers (Refs 89-105)...")

# Backfill existing rows' new columns with empty strings where missing
for r in rows:
    for c in COLS:
        if c not in r:
            r[c] = ""
    # Set Is_Susceptibility_Guided=0 for all existing arms (none were guided)
    if r.get("Is_Susceptibility_Guided", "") == "":
        r["Is_Susceptibility_Guided"] = 0

rows.extend(new_arms)

# Ensure all new rows also have all columns
for r in rows:
    for c in COLS:
        if c not in r:
            r[c] = ""

with open(OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)

print(f"✓ arm_level_dataset.csv updated: {len(rows)} total arms (added 38 new)")
print(f"  Unique refs: {len(set(r['Ref'] for r in rows))}")
print(f"  Susceptibility-guided arms: {sum(1 for r in rows if str(r.get('Is_Susceptibility_Guided'))=='1')}")
