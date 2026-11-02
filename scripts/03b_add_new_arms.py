"""
Addendum to Phase 1 arm building:
1. Corrects existing arms (doses, N_ITT, compliance, age)
2. Adds new arms from Refs 80-88 (Japan, Korea, Thailand, China)
Reads arm_level_dataset.csv, patches it, writes back.
"""
import csv, os

IN  = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/data/processed/arm_level_dataset.csv"
OUT = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/data/processed/arm_level_dataset.csv"

with open(IN, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    COLS = reader.fieldnames
    rows = list(reader)

# Add new columns if not present
NEW_COLS = ["Mean_Age_yr", "Compliance_pct"]
for c in NEW_COLS:
    if c not in COLS:
        COLS = list(COLS) + [c]
        for r in rows:
            r[c] = ""

def patch(rows, ref, arm_label, **kwargs):
    """Update fields on a matching row."""
    ref = str(ref)
    matched = 0
    for r in rows:
        if r["Ref"] == ref and r["Arm_Label"] == arm_label:
            for k, v in kwargs.items():
                r[k] = v
            matched += 1
    if not matched:
        print(f"  WARNING: no match for Ref{ref} {arm_label}")
    return matched

def R(ref, file, country, region, start, end, multicenter, naive_rescue,
      design, quality, arm, ttype, is_interv,
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

print("── Patching existing arms ──────────────────────────────────────────────")

# ── Ref 43: Amox daily ────────────────────────────────────────────────────────
patch(rows, 43, "VA-Dual-BID", Total_Amox_Daily_mg=2000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=2, Mean_Age_yr=41.1, Compliance_pct=98.2)
patch(rows, 43, "VA-Dual-TID", Total_Amox_Daily_mg=3000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=3, Mean_Age_yr=40.1, Compliance_pct=98.2)
print("  Ref 43 ✓")

# ── Ref 47: Amox + PPI daily ──────────────────────────────────────────────────
patch(rows, 47, "IAFB-Quad-14d", Total_Amox_Daily_mg=2000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=2,
      Total_PPI_Daily_mg=10, PPI_Dose_mg=5, PPI_Freq_per_day=2, Mean_Age_yr=44.1, Compliance_pct=88.7)
patch(rows, 47, "IAFB-Quad-10d", Total_Amox_Daily_mg=2000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=2,
      Total_PPI_Daily_mg=10, PPI_Dose_mg=5, PPI_Freq_per_day=2, Mean_Age_yr=44.3, Compliance_pct=90.7)
patch(rows, 47, "IA-Dual-14d",   Total_Amox_Daily_mg=3000, Amoxicillin_mg_per_dose=750,  Amoxicillin_freq_per_day=4,
      Total_PPI_Daily_mg=10, PPI_Dose_mg=5, PPI_Freq_per_day=2, Mean_Age_yr=47.6, Compliance_pct=94.7)
print("  Ref 47 ✓")

# ── Ref 48: Amox + PPI daily + N corrections ──────────────────────────────────
patch(rows, 48, "RADT-Dual",   Total_Amox_Daily_mg=3000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=3,
      Total_PPI_Daily_mg=60, PPI_Dose_mg=20, PPI_Freq_per_day=3, N_ITT=120, Mean_Age_yr=41.9, Compliance_pct=99.2)
patch(rows, 48, "RFDT-Dual",   Total_Amox_Daily_mg="", Amoxicillin_mg_per_dose="", Amoxicillin_freq_per_day="",
      Total_PPI_Daily_mg=60, PPI_Dose_mg=20, PPI_Freq_per_day=3, N_ITT=52, Mean_Age_yr=39.9, Compliance_pct=96.2,
      Notes="Arm terminated early (n=52) — eradication <80%; no amoxicillin")
patch(rows, 48, "BQT-Quadruple", Total_Amox_Daily_mg=2000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=2,
      Total_PPI_Daily_mg=40, PPI_Dose_mg=20, PPI_Freq_per_day=2, N_ITT=120, Mean_Age_yr=43.9, Compliance_pct=98.3)
print("  Ref 48 ✓")

# ── Ref 49: N_ITT + Amox + PPI ───────────────────────────────────────────────
patch(rows, 49, "HDDT-Dual",    N_ITT=496, Total_Amox_Daily_mg=3000, Amoxicillin_mg_per_dose=750,  Amoxicillin_freq_per_day=4,
      Total_PPI_Daily_mg=80, PPI_Dose_mg=20, PPI_Freq_per_day=4, Mean_Age_yr=46.7, Compliance_pct=99.2)
patch(rows, 49, "BQT-Quadruple", N_ITT=475, Total_Amox_Daily_mg=2000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=2,
      Total_PPI_Daily_mg=40, PPI_Dose_mg=20, PPI_Freq_per_day=2, Mean_Age_yr=46.2, Compliance_pct=99.2)
print("  Ref 49 ✓")

# ── Ref 51: PPI daily for ACBQT ──────────────────────────────────────────────
patch(rows, 51, "ACBQT-Quadruple", Total_PPI_Daily_mg=40, PPI_Dose_mg=20, PPI_Freq_per_day=2,
      Mean_Age_yr=49.1, Compliance_pct=98.0)
print("  Ref 51 ✓")

# ── Ref 53: Amox + PPI + N ───────────────────────────────────────────────────
patch(rows, 53, "HT-Dual",      Total_Amox_Daily_mg=3000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=3,
      Total_PPI_Daily_mg=20, PPI_Dose_mg=10, PPI_Freq_per_day=2, N_ITT=114, Mean_Age_yr=41.0, Compliance_pct=89.5)
patch(rows, 53, "BQT-Quadruple", Total_Amox_Daily_mg=2000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=2,
      Total_PPI_Daily_mg=10, PPI_Dose_mg=5, PPI_Freq_per_day=2, N_ITT=111, Mean_Age_yr=41.7, Compliance_pct=92.8)
print("  Ref 53 ✓")

# ── Ref 56: Amox + upgrade to in-paper resistance ────────────────────────────
patch(rows, 56, "VA-Dual",     Total_Amox_Daily_mg=3000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=3,
      Mean_Age_yr="", Compliance_pct=92.8)
patch(rows, 56, "EBAM-Quadruple", Total_Amox_Daily_mg=2000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=2,
      Total_PPI_Daily_mg=40, PPI_Dose_mg=20, PPI_Freq_per_day=2, Mean_Age_yr="", Compliance_pct=94.9)
print("  Ref 56 ✓")

# ── Ref 58: Amox + PPI for HDDT ──────────────────────────────────────────────
patch(rows, 58, "HDDT-Dual", Total_Amox_Daily_mg=3000, Amoxicillin_mg_per_dose=750, Amoxicillin_freq_per_day=4,
      Total_PPI_Daily_mg=80, PPI_Dose_mg=20, PPI_Freq_per_day=4, Mean_Age_yr=53.6, Compliance_pct=91.8)
print("  Ref 58 ✓")

# ── Ref 59: N_ITT + Amox/PPI for BCQ ─────────────────────────────────────────
patch(rows, 59, "VA14-Dual",       N_ITT=75,  Mean_Age_yr=45.9, Compliance_pct=85.3)
patch(rows, 59, "JWC-Modified-Dual", N_ITT=74, Mean_Age_yr=43.9, Compliance_pct=93.2)
patch(rows, 59, "BCQ-Quadruple",   N_ITT=75,  Total_Amox_Daily_mg=2000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=2,
      Total_PPI_Daily_mg=40, PPI_Dose_mg=20, PPI_Freq_per_day=2, Mean_Age_yr=42.7, Compliance_pct=81.3)
print("  Ref 59 ✓")

# ── Ref 61: Amox + PPI for B-Quad ────────────────────────────────────────────
patch(rows, 61, "B-Quad-14d", Total_Amox_Daily_mg=2000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=2,
      Total_PPI_Daily_mg=20, PPI_Dose_mg=10, PPI_Freq_per_day=2, Mean_Age_yr=38.6, Compliance_pct=88.5)
patch(rows, 61, "VA-Dual-10d", Mean_Age_yr=38.1, Compliance_pct=90.4)
print("  Ref 61 ✓")

# ── Ref 62: Amox + PPI ───────────────────────────────────────────────────────
patch(rows, 62, "HDDT-Dual",    Total_Amox_Daily_mg=3000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=3,
      Total_PPI_Daily_mg=120, PPI_Dose_mg=40, PPI_Freq_per_day=3, Mean_Age_yr=67.1, Compliance_pct=98.7)
patch(rows, 62, "BQT-Quadruple", Total_Amox_Daily_mg=2000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=2,
      Total_PPI_Daily_mg=80, PPI_Dose_mg=40, PPI_Freq_per_day=2, Mean_Age_yr=66.7, Compliance_pct=97.3)
print("  Ref 62 ✓")

# ── Ref 63: N_ITT + Amox + PPI ───────────────────────────────────────────────
patch(rows, 63, "IA-Dual",        N_ITT=101, Total_Amox_Daily_mg=3000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=3,
      Total_PPI_Daily_mg=10, PPI_Dose_mg=5, PPI_Freq_per_day=2, Mean_Age_yr=41.1, Compliance_pct=95.1)
patch(rows, 63, "IAFB-Quadruple", N_ITT=99,  Total_Amox_Daily_mg=2000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=2,
      Total_PPI_Daily_mg=10, PPI_Dose_mg=5, PPI_Freq_per_day=2, Mean_Age_yr=44.0, Compliance_pct=87.9)
print("  Ref 63 ✓")

# ── Ref 64: Amox ─────────────────────────────────────────────────────────────
patch(rows, 64, "VPZ-Dual",        Total_Amox_Daily_mg=3000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=3, Mean_Age_yr=44.9)
patch(rows, 64, "VPZ-Bismuth-Quad", Total_Amox_Daily_mg=2000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=2, Mean_Age_yr=42.4)
patch(rows, 64, "PPI-Bismuth-Quad", Total_Amox_Daily_mg=2000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=2,
      Total_PPI_Daily_mg=10, PPI_Dose_mg=5, PPI_Freq_per_day=2, Mean_Age_yr=40.8)
print("  Ref 64 ✓")

# ── Ref 65: Amox + PPI for Bismuth-Quad ──────────────────────────────────────
patch(rows, 65, "VA-Dual",     Total_Amox_Daily_mg=3000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=3, Mean_Age_yr=35.9, Compliance_pct=95.0)
patch(rows, 65, "VAC-Triple",  Total_Amox_Daily_mg=2000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=2, Mean_Age_yr=36.3, Compliance_pct=95.9)
patch(rows, 65, "Bismuth-Quad", Total_Amox_Daily_mg="", Amoxicillin_mg_per_dose="", Amoxicillin_freq_per_day="",
      Total_PPI_Daily_mg=40, PPI_Dose_mg=20, PPI_Freq_per_day=2,
      Mean_Age_yr=35.0, Compliance_pct=88.0,
      Notes="Bismuth+ESO+Tetracycline+Metronidazole; no amoxicillin")
print("  Ref 65 ✓")

# ── Ref 66: No amox in either arm ────────────────────────────────────────────
patch(rows, 66, "VT-Dual", Total_Amox_Daily_mg="", Mean_Age_yr=46.6, Compliance_pct=94.7,
      Notes="Penicillin-allergic population; VPZ+Tetracycline 500mg TID; no amoxicillin")
patch(rows, 66, "BQT-Quadruple", Total_Amox_Daily_mg="", Total_PPI_Daily_mg=60, PPI_Dose_mg=30, PPI_Freq_per_day=2,
      Mean_Age_yr=47.4, Compliance_pct=87.3,
      Notes="Penicillin-allergic; LAN+Bismuth+Tetracycline+Metronidazole; no amoxicillin")
print("  Ref 66 ✓")

# ── Ref 67: VPZ-Quad Amox ────────────────────────────────────────────────────
patch(rows, 67, "VPZ-Quad", Total_Amox_Daily_mg=2000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=2,
      Mean_Age_yr=38.4, Compliance_pct=95.8)
patch(rows, 67, "VA-Dual-BID", Mean_Age_yr=41.9, Compliance_pct=93.7)
print("  Ref 67 ✓")

# ── Ref 69: Amox ─────────────────────────────────────────────────────────────
patch(rows, 69, "TA-Dual", Total_Amox_Daily_mg=3000, Amoxicillin_mg_per_dose=750, Amoxicillin_freq_per_day=4, Mean_Age_yr=45, Compliance_pct=98.9)
patch(rows, 69, "EA-Dual", Total_Amox_Daily_mg=3000, Amoxicillin_mg_per_dose=750, Amoxicillin_freq_per_day=4, Mean_Age_yr=42, Compliance_pct=97.2)
print("  Ref 69 ✓")

# ── Ref 70: Amox ─────────────────────────────────────────────────────────────
patch(rows, 70, "TA-Dual",      Total_Amox_Daily_mg=3000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=3, Mean_Age_yr=26.2, Compliance_pct=94.1)
patch(rows, 70, "TBAC-Quadruple", Total_Amox_Daily_mg=2000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=2, Mean_Age_yr=27.3, Compliance_pct=89.0)
print("  Ref 70 ✓")

# ── Ref 71: N_ITT ────────────────────────────────────────────────────────────
patch(rows, 71, "VA-Dual-10d", N_ITT=287, Mean_Age_yr=46.9, Compliance_pct=98.9)
patch(rows, 71, "EA-Dual-14d", N_ITT=283, Mean_Age_yr=47.7, Compliance_pct=95.1)
print("  Ref 71 ✓")

# ── Ref 77: VM-Dual no amox; B-Quad amox ─────────────────────────────────────
patch(rows, 77, "VM-Dual", Total_Amox_Daily_mg="", Amoxicillin_mg_per_dose="", Amoxicillin_freq_per_day="",
      Mean_Age_yr=43.4, Compliance_pct=94.2,
      Notes="Vonoprazan+Minocycline 100mg BID; no amoxicillin (penicillin-ineligible)")
patch(rows, 77, "B-Quad", Total_Amox_Daily_mg=2000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=2,
      Total_PPI_Daily_mg=20, PPI_Dose_mg=10, PPI_Freq_per_day=2,
      Mean_Age_yr=42.4, Compliance_pct=92.5)
print("  Ref 77 ✓")

# ── Ref 78: Amox + PPI + N corrections ───────────────────────────────────────
patch(rows, 78, "EA-Dual",    N_ITT=221, Total_Amox_Daily_mg=3000, Amoxicillin_mg_per_dose=750,  Amoxicillin_freq_per_day=4, Mean_Age_yr=41.1, Compliance_pct=98.2)
patch(rows, 78, "B-Quad",     N_ITT=218, Total_Amox_Daily_mg=2000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=2,
      Total_PPI_Daily_mg=40, PPI_Dose_mg=20, PPI_Freq_per_day=2, Mean_Age_yr=41.2, Compliance_pct=98.6)
patch(rows, 78, "VA-Dual",    N_ITT=183, Total_Amox_Daily_mg=3000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=3, Mean_Age_yr=42.4, Compliance_pct=95.6)
patch(rows, 78, "VAC-Triple", N_ITT=184, Total_Amox_Daily_mg=2000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=2,
      Total_PPI_Daily_mg=40, PPI_Dose_mg=20, PPI_Freq_per_day=2, Mean_Age_yr=43.7, Compliance_pct=96.7)
print("  Ref 78 ✓")

# ── Ref 79: Amox + PPI for BQT ───────────────────────────────────────────────
patch(rows, 79, "VA-Dual",      Total_Amox_Daily_mg=3000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=3, Mean_Age_yr=44.6, Compliance_pct=97.6)
patch(rows, 79, "BQT-Quadruple", Total_Amox_Daily_mg=2000, Amoxicillin_mg_per_dose=1000, Amoxicillin_freq_per_day=2,
      Total_PPI_Daily_mg=60, PPI_Dose_mg=30, PPI_Freq_per_day=2, Mean_Age_yr=41.5, Compliance_pct=97.6)
print("  Ref 79 ✓")

print("\n── Adding new arms ─────────────────────────────────────────────────────")

new_arms = [
    # ── Ref 80: Murakami 2015, Gut — Japan Phase III ──────────────────────────
    # First-line arms only; rescue arm excluded (second-line different question)
    R(80, "80_MurakamiK_2015", "Japan", "East Asia", "2011", "2012", "Yes", "Naive",
      "RCT", "",
      "VPZ-Triple-7d", "triple", 1,
      "Vonoprazan", 20, 2,
      750, 2,
      300, 2,   # CLR 200 or 400 mg combined; median ~300 used; note below
      "", "",
      0, "", "",
      7, 329, "",
      92.6, "", 34.0,
      1500, 40,
      "Japan Phase III; CLR dose 200mg or 400mg BID (combined analysis); in-paper CLR resistance 30.4%",
      55.2, 98.0),

    R(80, "80_MurakamiK_2015", "Japan", "East Asia", "2011", "2012", "Yes", "Naive",
      "RCT", "",
      "LAN-Triple-7d", "triple", 0,
      "Lansoprazole", 30, 2,
      750, 2,
      300, 2,
      "", "",
      0, "", "",
      7, 321, "",
      75.9, "", 41.1,
      1500, 60,
      "Japan Phase III lansoprazole comparator; in-paper CLR resistance 35.9%",
      53.9, 98.0),

    # ── Ref 81: Maruyama 2017 — Japan single-center RCT ──────────────────────
    R(81, "81_MaruyamaM_2017", "Japan", "East Asia", "2015", "2016", "No", "Naive",
      "RCT", "",
      "VPZ-Triple-7d", "triple", 1,
      "Vonoprazan", 20, 2,
      750, 2,
      300, 2,
      "", "",
      0, "", "",
      7, 72, 70,
      95.8, 95.7, 26.3,
      1500, 40,
      "Japan single-center; CLR 200mg (79%) or 400mg (21%) BID",
      58.0, 97.0),

    R(81, "81_MaruyamaM_2017", "Japan", "East Asia", "2015", "2016", "No", "Naive",
      "RCT", "",
      "PPI-Triple-7d", "triple", 0,
      "Rabeprazole", 20, 2,    # majority RPZ; some LPZ (note)
      750, 2,
      300, 2,
      "", "",
      0, "", "",
      7, 69, 63,
      69.6, 71.4, 37.7,
      1500, 40,
      "Japan comparator; mixed RPZ 20mg (n=59) + LPZ 30mg (n=10) per physician choice",
      60.0, 91.0),

    # ── Ref 82: Choi 2022, Gut and Liver — Korea Phase III tegoprazan ─────────
    R(82, "82_ChoiYJ_2022", "Korea", "East Asia", "2017", "2018", "Yes", "Naive",
      "RCT", "",
      "TPZ-Triple-7d", "triple", 1,
      "Tegoprazan", 50, 2,
      1000, 2,
      500, 2,
      "", "",
      0, "", "",
      7, 175, 150,
      62.9, 69.3, 41.9,
      2000, 100,
      "Korea Phase III; 7-day tegoprazan triple; CLR resistance 30.3% (subset n=76)",
      54.7, ""),

    R(82, "82_ChoiYJ_2022", "Korea", "East Asia", "2017", "2018", "Yes", "Naive",
      "RCT", "",
      "LPZ-Triple-7d", "triple", 0,
      "Lansoprazole", 30, 2,
      1000, 2,
      500, 2,
      "", "",
      0, "", "",
      7, 175, 150,
      60.6, 67.3, 39.3,
      2000, 60,
      "Korea Phase III lansoprazole comparator; same CLR resistance pool",
      53.2, ""),

    # ── Ref 83: Park 2024, Helicobacter — Korea Phase III tegoprazan 14-day ───
    R(83, "83_ParkJY_2024", "Korea", "East Asia", "2022", "2024", "Yes", "Naive",
      "RCT", "",
      "TPZ50-Triple-14d", "triple", 1,
      "Tegoprazan", 50, 2,
      1000, 2,
      500, 2,
      "", "",
      0, "", "",
      14, 121, 113,
      86.0, 88.5, 45.5,
      2000, 100,
      "Korea Phase III 14-day; CLR resistance 19% (in-paper PCR)",
      55.3, 98.0),

    R(83, "83_ParkJY_2024", "Korea", "East Asia", "2022", "2024", "Yes", "Naive",
      "RCT", "",
      "TPZ100-Triple-14d", "triple", 1,
      "Tegoprazan", 100, 2,
      1000, 2,
      500, 2,
      "", "",
      0, "", "",
      14, 124, 119,
      85.5, 87.4, 46.4,
      2000, 200,
      "Korea Phase III 14-day 100mg dose; CLR resistance 25.8% (in-paper PCR)",
      55.0, 98.0),

    R(83, "83_ParkJY_2024", "Korea", "East Asia", "2022", "2024", "Yes", "Naive",
      "RCT", "",
      "LAN-Triple-14d", "triple", 0,
      "Lansoprazole", 30, 2,
      1000, 2,
      500, 2,
      "", "",
      0, "", "",
      14, 127, 123,
      78.7, 81.3, 39.4,
      2000, 60,
      "Korea Phase III lansoprazole comparator 14-day; CLR resistance 24.4% (in-paper PCR)",
      54.5, 97.7),

    # ── Ref 84: Park 2025, Gut and Liver — Korea pilot tego vs vono ───────────
    R(84, "84_ParkJY_2025", "Korea", "East Asia", "2020", "2022", "Yes", "Naive",
      "RCT", "small-pilot (n=33/arm)",
      "TPZ50-Triple-10d", "triple", 1,
      "Tegoprazan", 50, 2,
      1000, 2,
      500, 2,
      "", "",
      0, "", "",
      10, 33, 30,
      60.6, 66.7, 38.2,
      2000, 100,
      "Korea pilot n=33; 10-day tegoprazan 50mg triple",
      55.7, 97.1),

    R(84, "84_ParkJY_2025", "Korea", "East Asia", "2020", "2022", "Yes", "Naive",
      "RCT", "small-pilot (n=33/arm)",
      "TPZ100-Triple-10d", "triple", 1,
      "Tegoprazan", 100, 2,
      1000, 2,
      500, 2,
      "", "",
      0, "", "",
      10, 33, 30,
      78.8, 86.7, 54.6,
      2000, 200,
      "Korea pilot n=33; 10-day tegoprazan 100mg triple",
      49.7, 97.1),

    R(84, "84_ParkJY_2025", "Korea", "East Asia", "2020", "2022", "Yes", "Naive",
      "RCT", "small-pilot (n=33/arm)",
      "VPZ-Triple-10d", "triple", 0,
      "Vonoprazan", 20, 2,
      1000, 2,
      500, 2,
      "", "",
      0, "", "",
      10, 33, 32,
      84.9, 87.5, 44.1,
      2000, 40,
      "Korea pilot n=33; 10-day vonoprazan triple (active comparator)",
      55.6, 97.1),

    # ── Ref 85: Tungtrongchitr 2024, Sci Reports — Thailand VPZ bismuth quad ──
    R(85, "85_TungtrongchitrN_2024", "Thailand", "Southeast Asia", "2021", "2022", "No", "Naive",
      "RCT", "",
      "VPZ-BQ-7d", "quadruple", 1,
      "Vonoprazan", 20, 2,
      "", "",
      "", "",
      400, 3,
      1, "Tetracycline", 500,
      7, 51, 51,
      84.4, 84.4, 29.4,
      "", 40,
      "Thailand; vonoprazan bismuth quadruple 7d; bismuth subsalicylate 1024mg BID; tetracycline 500mg QID; metro 400mg TID",
      51.5, ""),

    R(85, "85_TungtrongchitrN_2024", "Thailand", "Southeast Asia", "2021", "2022", "No", "Naive",
      "RCT", "",
      "VPZ-BQ-14d", "quadruple", 1,
      "Vonoprazan", 20, 2,
      "", "",
      "", "",
      400, 3,
      1, "Tetracycline", 500,
      14, 50, 50,
      94.0, 94.0, 28.0,
      "", 40,
      "Thailand; vonoprazan bismuth quadruple 14d; in-paper CLR=33.3% MTZ=29.4% LFX=27.7% AMX=0% (n=18 subset)",
      55.4, ""),

    # ── Ref 86: Sukkamolsantiporn 2025, Sci Reports — Thailand ONCE-VONO ──────
    R(86, "86_SukkamolsantipornS_2025", "Thailand", "Southeast Asia", "2022", "2023", "No", "Naive",
      "RCT", "",
      "VCLB-7d", "quadruple", 1,
      "Vonoprazan", 40, 1,
      "", "",
      1000, 1,    # CLR-MR once daily
      "", "",
      1, "Levofloxacin", 500,
      7, 51, 48,
      88.2, 89.6, 35.3,
      "", 40,
      "Thailand; once-daily VPZ 40mg+CLR-MR 1g+LFX 500mg+bismuth 1048mg; resistance data unreliable (n=8 only)",
      58.2, ""),

    R(86, "86_SukkamolsantipornS_2025", "Thailand", "Southeast Asia", "2022", "2023", "No", "Naive",
      "RCT", "",
      "VCLB-14d", "quadruple", 1,
      "Vonoprazan", 40, 1,
      "", "",
      1000, 1,
      "", "",
      1, "Levofloxacin", 500,
      14, 51, 48,
      88.2, 93.8, 38.8,
      "", 40,
      "Thailand; once-daily 14d; levofloxacin-based quadruple; CLR-resistant strains still eradicated",
      56.1, ""),

    # ── Ref 87: Song 2024, Chin Med J — China Phase 3 VPZ vs ESO quadruple ────
    R(87, "87_SongZ_2024", "China", "East Asia", "2020", "2022", "Yes", "Naive",
      "RCT", "",
      "VPZ-BQT", "quadruple", 1,
      "Vonoprazan", 20, 2,
      1000, 2,
      500, 2,
      "", "",
      1, "", "",
      14, 242, 231,
      86.8, 87.4, 69.1,
      2000, 40,
      "China Phase 3 multicenter 29 sites; VPZ+AMX+CLR+bismuth; in-paper CLR=42.4% (n=66 subset)",
      39.5, 99.1),

    R(87, "87_SongZ_2024", "China", "East Asia", "2020", "2022", "Yes", "Naive",
      "RCT", "",
      "ESO-BQT", "quadruple", 0,
      "Esomeprazole", 20, 2,
      1000, 2,
      500, 2,
      "", "",
      1, "", "",
      14, 240, 226,
      86.7, 86.3, 61.4,
      2000, 40,
      "China Phase 3; ESO+AMX+CLR+bismuth comparator; in-paper CLR=31.8% (n=66 subset)",
      38.3, 98.8),

    # ── Ref 88: Hu 2025, Lancet Microbe — China LVA vs HVA vonoprazan dual ────
    R(88, "88_HuY_2025_LancetMicrobe", "China", "East Asia", "2022", "2024", "Yes", "Naive",
      "RCT", "",
      "LVA-Dual", "dual", 0,
      "Vonoprazan", 20, 2,
      1000, 2,
      "", "",
      "", "",
      0, "", "",
      14, 252, 240,
      85.3, 88.8, "",
      2000, 40,
      "China multicenter 12 centers 7 provinces; low-dose amox 2g/day; in-paper CLR=30% MTZ=74% LFX=28% AMX=0% (n=286)",
      "", ""),

    R(88, "88_HuY_2025_LancetMicrobe", "China", "East Asia", "2022", "2024", "Yes", "Naive",
      "RCT", "",
      "HVA-Dual", "dual", 1,
      "Vonoprazan", 20, 2,
      1000, 3,
      "", "",
      "", "",
      0, "", "",
      14, 252, 236,
      86.5, 92.4, "",
      3000, 40,
      "China multicenter; high-dose amox 3g/day; non-inferior to 2g/day (NI p=0.0022)",
      "", ""),
]

rows.extend(new_arms)
print(f"  Added {len(new_arms)} new arms (Refs 80–88)")

# ── Write ──────────────────────────────────────────────────────────────────────
# Ensure all rows have all columns
all_cols = COLS
for r in rows:
    for c in all_cols:
        if c not in r:
            r[c] = ""

with open(OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=all_cols, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)

print(f"\n✓ arm_level_dataset.csv updated: {len(rows)} total arms")
