"""
Build the arm-level dataset from manually extracted paper data.
One row = one treatment arm from one RCT.
Output: project/data/processed/arm_level_dataset.csv
"""
import csv, os

OUT = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/data/processed/arm_level_dataset.csv"

# ── Column definitions ─────────────────────────────────────────────────────────
COLS = [
    # Paper identifiers
    "Ref", "File", "Country", "Geographic_Region",
    "Study_Period_Start", "Study_Period_End",
    "Multicenter", "Treatment_Naive_vs_Rescue",
    "Study_Design",          # RCT / observational / retrospective / protocol
    "Study_Quality_Flag",    # notes on study quality

    # Arm identifiers
    "Arm_Label",             # short name (e.g. "VA-dual", "BQT")
    "Treatment_Type",        # dual / triple / quadruple / nonbismuth_quadruple
    "Arm_Is_Intervention",   # 1=novel arm, 0=comparator (standard)

    # Regimen details
    "PPI",                   # drug name
    "PPI_Dose_mg",           # per dose
    "PPI_Freq_per_day",      # 1/2/3/4
    "Amoxicillin_mg_per_dose",
    "Amoxicillin_freq_per_day",
    "Clarithromycin_mg_per_dose",
    "Clarithromycin_freq_per_day",
    "Metronidazole_mg_per_dose",
    "Metronidazole_freq_per_day",
    "Bismuth_used",          # 0/1
    "Other_Antibiotic",      # furazolidone / tetracycline / minocycline / levofloxacin
    "Other_Antibiotic_mg",
    "Duration_Days",

    # Sample sizes
    "N_ITT", "N_PP",

    # Outcomes
    "ITT_Rate",              # % eradication by ITT
    "PP_Rate",               # % eradication by PP
    "AE_Rate",               # % adverse events

    # Derived
    "Total_Amox_Daily_mg",   # dose × freq
    "Total_PPI_Daily_mg",

    # Notes
    "Notes",
]

# ── Data ───────────────────────────────────────────────────────────────────────
# Each tuple: (ref, file_stem, country, region, period_start, period_end,
#              multicenter, naive_rescue, design, quality_flag,
#              arm_label, treatment_type, is_intervention,
#              ppi, ppi_dose, ppi_freq, amox_dose, amox_freq,
#              clari_dose, clari_freq, metro_dose, metro_freq,
#              bismuth, other_ab, other_ab_mg, duration,
#              N_ITT, N_PP, ITT, PP, AE, notes)

def row(ref, file, country, region, ps, pe, mc, nr, design, qflag,
        arm, ttype, isint,
        ppi, ppidose, ppifreq, amoxdose, amoxfreq,
        claridose, clarifreq, metrodose, metrofreq,
        bismuth, other, othermg, dur,
        nitt, npp, itt, pp, ae, notes=""):
    total_amox = (amoxdose or 0) * (amoxfreq or 0) if amoxdose and amoxfreq else ""
    total_ppi  = (ppidose  or 0) * (ppifreq  or 0) if ppidose  and ppifreq  else ""
    return {
        "Ref": ref, "File": file, "Country": country, "Geographic_Region": region,
        "Study_Period_Start": ps, "Study_Period_End": pe,
        "Multicenter": mc, "Treatment_Naive_vs_Rescue": nr,
        "Study_Design": design, "Study_Quality_Flag": qflag,
        "Arm_Label": arm, "Treatment_Type": ttype, "Arm_Is_Intervention": isint,
        "PPI": ppi, "PPI_Dose_mg": ppidose, "PPI_Freq_per_day": ppifreq,
        "Amoxicillin_mg_per_dose": amoxdose, "Amoxicillin_freq_per_day": amoxfreq,
        "Clarithromycin_mg_per_dose": claridose, "Clarithromycin_freq_per_day": clarifreq,
        "Metronidazole_mg_per_dose": metrodose, "Metronidazole_freq_per_day": metrofreq,
        "Bismuth_used": bismuth, "Other_Antibiotic": other, "Other_Antibiotic_mg": othermg,
        "Duration_Days": dur,
        "N_ITT": nitt, "N_PP": npp, "ITT_Rate": itt, "PP_Rate": pp, "AE_Rate": ae,
        "Total_Amox_Daily_mg": total_amox, "Total_PPI_Daily_mg": total_ppi,
        "Notes": notes,
    }

# shorthand
R = row

DATA = [
# ─── Ref 29: KimSY 2012, Korea, 14d ──────────────────────────────────────────
R(29,"29_KimSY_2012","Korea","East Asia","May 2009","Apr 2010",
  "No","Naive","RCT","",
  "Triple-LAC","triple",0,
  "Lansoprazole",30,2, 1000,2, 500,2, None,None, 0,None,None, 14,
  104,93, 74.0,82.8,35.6),
R(29,"29_KimSY_2012","Korea","East Asia","May 2009","Apr 2010",
  "No","Naive","RCT","",
  "Dual-LA","dual",1,
  "Lansoprazole",30,3, 750,3, None,None, None,None, 0,None,None, 14,
  104,88, 67.3,78.4,18.3),

# ─── Ref 30: HuCT 2017, China, 14d (3 arms) ─────────────────────────────────
R(30,"30_HuCT_2017","China","East Asia","","",
  "No","Naive","RCT","",
  "R10A-Dual","dual",1,
  "Rabeprazole",10,4, 750,4, None,None, None,None, 0,None,None, 14,
  87,None, 78.1,79.1,None),
R(30,"30_HuCT_2017","China","East Asia","","",
  "No","Naive","RCT","",
  "R20A-Dual","dual",1,
  "Rabeprazole",20,4, 750,4, None,None, None,None, 0,None,None, 14,
  87,None, 81.6,83.5,None),
R(30,"30_HuCT_2017","China","East Asia","","",
  "No","Naive","RCT","",
  "RBAC-Quadruple","quadruple",0,
  "Rabeprazole",20,2, 1000,2, 500,2, None,None, 1,None,None, 14,
  89,None, 84.3,86.2,None, "Bismuth 220mg BID"),

# ─── Ref 36: TaiWC 2019, Taiwan, 14d vs 7d ───────────────────────────────────
R(36,"36_TaiWC_2019","Taiwan","East Asia","","",
  "No","Naive","RCT","",
  "EA-Dual","dual",1,
  "Esomeprazole",40,3, 750,4, None,None, None,None, 0,None,None, 14,
  120,None, 91.7,95.7,9.6, "Amox 750mg QID × 14d"),
R(36,"36_TaiWC_2019","Taiwan","East Asia","","",
  "No","Naive","RCT","",
  "EACM-Quadruple","nonbismuth_quadruple",0,
  "Esomeprazole",40,2, 1000,2, 500,2, 500,2, 0,None,None, 7,
  120,None, 86.7,92.0,23.0),

# ─── Ref 38: SongZ 2023 → PROTOCOL, no results ───────────────────────────────
# EXCLUDED

# ─── Ref 39: SuzukiS 2020, Japan, 7d (observational not RCT) ─────────────────
R(39,"39_SuzukiS_2020","Japan","East Asia","2018","2019",
  "No","Naive","Observational","Non-randomized; historical comparison",
  "VA-Dual-7d","dual",1,
  "Vonoprazan",20,2, 750,2, None,None, None,None, 0,None,None, 7,
  60,None, 85.0,86.4,10.0),
R(39,"39_SuzukiS_2020","Japan","East Asia","2015","2017",
  "No","Naive","Observational","Non-randomized; historical comparison",
  "VAC-Triple-7d","triple",0,
  "Vonoprazan",20,2, 750,2, 200,2, None,None, 0,None,None, 7,
  161,None, 82.0,84.1,19.8),

# ─── Ref 40: HoriiT 2021, Japan (microbiome study, limited eradication data) ─
# EXCLUDED (microbiome study, N=43, not eradication RCT)

# ─── Ref 41: CheyWD 2022, USA+Europe, 14d (Phase 3 RCT, 3 arms, N=1046) ──────
R(41,"41_CheyWD_2022","USA+Europe","Western","2020","2022",
  "Yes","Naive","RCT","Multinational Phase 3",
  "VPZ-Dual","dual",1,
  "Vonoprazan",20,2, 1000,3, None,None, None,None, 0,None,None, 14,
  349,None, 77.2,None,None, "ITT all patients; non-resistant strains ITT=78.5%"),
R(41,"41_CheyWD_2022","USA+Europe","Western","2020","2022",
  "Yes","Naive","RCT","Multinational Phase 3",
  "VPZ-Triple","triple",1,
  "Vonoprazan",20,2, 1000,2, 500,2, None,None, 0,None,None, 14,
  349,None, 80.8,None,None, "ITT all patients; non-resistant strains ITT=84.7%"),
R(41,"41_CheyWD_2022","USA+Europe","Western","2020","2022",
  "Yes","Naive","RCT","Multinational Phase 3",
  "LAN-Triple","triple",0,
  "Lansoprazole",30,2, 1000,2, 500,2, None,None, 0,None,None, 14,
  349,None, 68.5,None,None, "ITT all patients; non-resistant strains ITT=78.8%"),

# ─── Ref 42: GuanJL 2022, China, 14d (multicenter, N=700) ───────────────────
R(42,"42_GuanJL_2022","China","East Asia","","",
  "Yes","Naive","RCT","",
  "HDDT-Dual","dual",1,
  "Esomeprazole",40,3, 750,4, None,None, None,None, 0,None,None, 14,
  350,None, 89.4,90.6,12.9, "Esomeprazole 40mg TID + Amox 750mg QID (verify dose)"),
R(42,"42_GuanJL_2022","China","East Asia","","",
  "Yes","Naive","RCT","",
  "BQT-Quadruple","quadruple",0,
  "Esomeprazole",20,2, 1000,2, None,None, None,None, 1,None,None, 14,
  350,None, 84.6,88.2,28.1, "Bismuth quadruple"),

# ─── Ref 43: HuY 2022, China, 14d (VA dual, BID vs TID amox, N=110) ──────────
R(43,"43_HuY_2022","China","East Asia","","",
  "No","Naive","RCT","",
  "VA-Dual-BID","dual",1,
  "Vonoprazan",20,2, None,2, None,None, None,None, 0,None,None, 14,
  55,None, 89.1,94.1,None, "Amox dose not specified in abstract"),
R(43,"43_HuY_2022","China","East Asia","","",
  "No","Naive","RCT","",
  "VA-Dual-TID","dual",1,
  "Vonoprazan",20,2, None,3, None,None, None,None, 0,None,None, 14,
  55,None, 87.3,95.9,None, "Amox dose not specified in abstract"),

# ─── Ref 44: LinY 2022, China, 7d (3 arms, vonoprazan dose comparison) ───────
R(44,"44_LinY_2022","China","East Asia","","",
  "No","Naive","RCT","Low rates; 7-day regimen",
  "H-VA-7d","dual",1,
  "Vonoprazan",20,2, 1000,2, None,None, None,None, 0,None,None, 7,
  85,83, 63.5,65.1,16.9, "High-dose vonoprazan dual 7d"),
R(44,"44_LinY_2022","China","East Asia","","",
  "No","Naive","RCT","Low rates; 7-day regimen",
  "L-VA-7d","dual",1,
  "Vonoprazan",10,2, 1000,2, None,None, None,None, 0,None,None, 7,
  84,74, 58.3,66.2,13.2, "Low-dose vonoprazan dual 7d"),
R(44,"44_LinY_2022","China","East Asia","","",
  "No","Naive","RCT","Low rates; 7-day regimen",
  "VAC-Triple-7d","triple",0,
  "Vonoprazan",20,2, 1000,2, 500,2, None,None, 0,None,None, 7,
  61,57, 60.7,64.9,24.1),

# ─── Ref 45: CastanoLlanoR 2022, Colombia, 14d (multicenter, N=266) ──────────
R(45,"45_CastanoLlanoR_2022","Colombia","Latin America","","",
  "Yes","Naive","RCT","",
  "TDA-Dual","dual",1,
  "Esomeprazole",40,3, 750,4, None,None, None,None, 0,None,None, 14,
  133,None, 88.7,96.6,16.5, "High-dose dual 14d"),
R(45,"45_CastanoLlanoR_2022","Colombia","Latin America","","",
  "Yes","Naive","RCT","",
  "TCB-Quadruple","quadruple",0,
  "Esomeprazole",40,2, 1000,2, None,None, None,None, 1,None,None, 14,
  133,None, 84.9,90.3,36.8),

# ─── Ref 46: MeiH 2022, China, 14d (multicenter, N=340) ─────────────────────
R(46,"46_MeiH_2022","China","East Asia","","",
  "Yes","Naive","RCT","",
  "HDDT-Dual","dual",1,
  "Esomeprazole",20,4, 750,4, None,None, None,None, 0,None,None, 14,
  170,None, 86.47,91.77,16.67),
R(46,"46_MeiH_2022","China","East Asia","","",
  "Yes","Naive","RCT","",
  "BQT-Quadruple","quadruple",0,
  "Esomeprazole",20,2, 1000,2, None,None, 400,4, 1,None,None, 14,
  170,None, 87.06,93.04,47.94, "Bismuth + esomeprazole + amox + metronidazole"),

# ─── Ref 47: NiuM 2022, China (ilaprazole, 3 arms, N=450) ───────────────────
R(47,"47_NiuM_2022","China","East Asia","","",
  "No","Naive","RCT","",
  "IAFB-Quad-14d","quadruple",0,
  "Ilaprazole",None,None, None,None, None,None, None,None, 1,"Furazolidone",None, 14,
  150,None, 84.0,94.7,None),
R(47,"47_NiuM_2022","China","East Asia","","",
  "No","Naive","RCT","",
  "IAFB-Quad-10d","quadruple",0,
  "Ilaprazole",None,None, None,None, None,None, None,None, 1,"Furazolidone",None, 10,
  150,None, 79.3,87.5,None),
R(47,"47_NiuM_2022","China","East Asia","","",
  "No","Naive","RCT","",
  "IA-Dual-14d","dual",1,
  "Ilaprazole",None,None, None,None, None,None, None,None, 0,None,None, 14,
  150,None, 88.0,93.0,None),

# ─── Ref 48: ShaoQQ 2022, China (3 arms, N=292) ──────────────────────────────
R(48,"48_ShaoQQ_2022","China","East Asia","","",
  "No","Naive","RCT","",
  "RADT-Dual","dual",1,
  "Rabeprazole",None,3, None,3, None,None, None,None, 0,None,None, 14,
  97,None, 85.8,89.6,None, "Rabeprazole + amox TID dual"),
R(48,"48_ShaoQQ_2022","China","East Asia","","",
  "No","Naive","RCT","",
  "RFDT-Dual","dual",1,
  "Rabeprazole",None,3, None,3, None,None, None,None, 0,"Furazolidone",None, 14,
  97,None, 48.1,51.0,None, "Rabeprazole + furazolidone; poor efficacy"),
R(48,"48_ShaoQQ_2022","China","East Asia","","",
  "No","Naive","RCT","",
  "BQT-Quadruple","quadruple",0,
  "Rabeprazole",None,2, None,None, None,None, None,None, 1,None,None, 14,
  98,None, 86.7,91.2,None),

# ─── Ref 49: ShenC 2022, China, 14d (esomeprazole QID dual) ─────────────────
R(49,"49_ShenC_2022","China","East Asia","","",
  "No","Naive","RCT","",
  "HDDT-Dual","dual",1,
  "Esomeprazole",20,4, 750,4, None,None, None,None, 0,None,None, 14,
  None,None, 88.31,91.63,13.3, "Esomeprazole 20mg QID + Amox 750mg QID; N not confirmed"),
R(49,"49_ShenC_2022","China","East Asia","","",
  "No","Naive","RCT","",
  "BQT-Quadruple","quadruple",0,
  "Esomeprazole",None,2, None,None, None,None, None,None, 1,None,None, 14,
  None,None, 85.26,90.60,28.2, "Bismuth quadruple; N not confirmed"),

# ─── Ref 50: YadollahiB 2022, Iran, 14d (N=217) ──────────────────────────────
R(50,"50_YadollahiB_2022","Iran","Middle East","","",
  "No","Naive","RCT","High resistance region",
  "HDDT-Dual","dual",1,
  "Esomeprazole",40,2, 1000,2, None,None, None,None, 0,None,None, 14,
  109,None, 80.6,82.2,20.8),
R(50,"50_YadollahiB_2022","Iran","Middle East","","",
  "No","Naive","RCT","High resistance region",
  "Concomitant-Quad","nonbismuth_quadruple",0,
  "Esomeprazole",40,2, 1000,2, 500,2, 500,2, 0,None,None, 14,
  108,None, 81.6,88.6,49.6),

# ─── Ref 51: YunJ 2023, China (NW China high resistance, N=216) ──────────────
R(51,"51_YunJ_2023","China","East Asia","","",
  "No","Naive","RCT","High clarithromycin resistance area (42%)",
  "HDDT-Dual","dual",1,
  "Esomeprazole",40,3, 750,4, None,None, None,None, 0,None,None, 14,
  108,None, 65.7,71.0,2.0, "Gansu NW China; very low eradication rates"),
R(51,"51_YunJ_2023","China","East Asia","","",
  "No","Naive","RCT","High clarithromycin resistance area (42%)",
  "ACBQT-Quadruple","quadruple",0,
  "Esomeprazole",None,2, 1000,2, 500,2, None,None, 1,None,None, 14,
  108,None, 68.5,74.7,43.4),

# ─── Ref 52: ZuberiBF 2022, Pakistan, 14d (N=179) ────────────────────────────
R(52,"52_ZuberiBF_2022","Pakistan","South Asia","Jun 2021","Sep 2021",
  "No","Naive","RCT","",
  "VA-Dual","dual",1,
  "Vonoprazan",20,2, 1000,2, None,None, None,None, 0,None,None, 14,
  92,None, 93.5,None,None),
R(52,"52_ZuberiBF_2022","Pakistan","South Asia","Jun 2021","Sep 2021",
  "No","Naive","RCT","",
  "OAC-Triple","triple",0,
  "Omeprazole",20,2, 1000,2, 500,2, None,None, 0,None,None, 14,
  87,None, 83.9,None,None),

# ─── Ref 53: ChengJ 2023, China (ilaprazole dual, N=225) ─────────────────────
R(53,"53_ChengJ_2023","China","East Asia","Feb 2023","Mar 2023",
  "No","Naive","RCT","",
  "HT-Dual","dual",1,
  "Ilaprazole",None,None, None,None, None,None, None,None, 0,None,None, 14,
  113,None, 76.3,76.3,27.2, "High-dose ilaprazole-amoxicillin dual"),
R(53,"53_ChengJ_2023","China","East Asia","Feb 2023","Mar 2023",
  "No","Naive","RCT","",
  "BQT-Quadruple","quadruple",0,
  "Ilaprazole",None,None, None,None, None,None, None,None, 1,None,None, 14,
  112,None, 61.3,61.3,81.8, "Bismuth quadruple; very high AE rate"),

# ─── Ref 54: HanYY 2023, China (VA 10d vs RA 14d dual, N=690) ───────────────
R(54,"54_HanYY_2023","China","East Asia","","",
  "Yes","Naive","RCT","Multicenter",
  "VA-Dual-10d","dual",1,
  "Vonoprazan",20,2, 1000,3, None,None, None,None, 0,None,None, 10,
  345,None, 89.3,91.4,None),
R(54,"54_HanYY_2023","China","East Asia","","",
  "Yes","Naive","RCT","Multicenter",
  "RA-Dual-14d","dual",0,
  "Rabeprazole",10,2, 1000,4, None,None, None,None, 0,None,None, 14,
  345,None, 84.9,86.6,None, "Rabeprazole 10mg BID + Amox 1g QID × 14d"),

# ─── Ref 56: HuJ 2023, China (VA dual vs EBAM quadruple, N=194) ──────────────
R(56,"56_HuJ_2023","China","East Asia","","",
  "No","Naive","RCT","",
  "VA-Dual","dual",1,
  "Vonoprazan",20,2, None,None, None,None, None,None, 0,None,None, 14,
  97,None, 88.7,95.6,None),
R(56,"56_HuJ_2023","China","East Asia","","",
  "No","Naive","RCT","",
  "EBAM-Quadruple","quadruple",0,
  "Esomeprazole",None,2, 1000,2, None,None, None,None, 1,None,None, 14,
  97,None, 91.8,96.7,None, "Esomeprazole + bismuth + amox + metronidazole"),

# ─── Ref 58: JiangX 2023, China (3 arms, N=255) ─────────────────────────────
R(58,"58_JiangX_2023","China","East Asia","Dec 2020","Oct 2021",
  "No","Naive","RCT","",
  "HDDT-Dual","dual",1,
  "Esomeprazole",None,None, None,None, None,None, None,None, 0,None,None, 14,
  85,78, None,91.0,11.5, "PP rate from 71/78"),
R(58,"58_JiangX_2023","China","East Asia","Dec 2020","Oct 2021",
  "No","Naive","RCT","",
  "BQT-Quadruple","quadruple",0,
  "Esomeprazole",None,None, None,None, None,None, None,None, 1,None,None, 14,
  85,None, None,None,None, "Clarithromycin resistance 43.65% in area"),
R(58,"58_JiangX_2023","China","East Asia","Dec 2020","Oct 2021",
  "No","Naive","RCT","",
  "RGBTT-Triple","triple",0,
  "Esomeprazole",None,None, None,None, None,None, None,None, 0,None,None, 14,
  85,None, None,None,None, "Resistance gene-based triple therapy"),

# ─── Ref 59: LiJ 2023, China (3 arms, VA14 vs BCQ vs JWC modified) ──────────
R(59,"59_LiJ_2023","China","East Asia","","",
  "No","Naive","RCT","",
  "VA14-Dual","dual",1,
  "Vonoprazan",20,2, 1000,2, None,None, None,None, 0,None,None, 14,
  None,None, 77.33,90.63,None, "Modified-ITT 90.63%"),
R(59,"59_LiJ_2023","China","East Asia","","",
  "No","Naive","RCT","",
  "BCQ-Quadruple","quadruple",0,
  "Vonoprazan",None,None, None,None, None,None, None,None, 1,None,None, 14,
  None,None, 78.67,96.72,None, "Bismuth + clarithromycin + amox quadruple"),
R(59,"59_LiJ_2023","China","East Asia","","",
  "No","Naive","RCT","",
  "JWC-Modified-Dual","dual",1,
  "Vonoprazan",20,2, 1000,2, None,None, None,None, 0,None,None, 14,
  None,None, 86.49,92.75,None, "Modified VA with JWC (Chinese herbal)"),

# ─── Ref 61: WangX 2023, China (VA 10d vs BQT 14d, N=314, multicenter) ───────
R(61,"61_WangX_2023","China","East Asia","","",
  "Yes","Naive","RCT","",
  "VA-Dual-10d","dual",1,
  "Vonoprazan",20,2, 500,2, None,None, None,None, 0,None,None, 10,
  157,None, 86.0,90.8,None, "VA 10-day dual"),
R(61,"61_WangX_2023","China","East Asia","","",
  "Yes","Naive","RCT","",
  "B-Quad-14d","quadruple",0,
  "Esomeprazole",None,2, None,None, None,None, None,None, 1,None,None, 14,
  157,None, 89.2,91.3,None),

# ─── Ref 62: YangQ 2023, China (elderly, N=150) ──────────────────────────────
R(62,"62_YangQ_2023","China","East Asia","Feb 2020","Feb 2022",
  "No","Naive","RCT","Elderly patients",
  "HDDT-Dual","dual",1,
  "Esomeprazole",None,None, None,None, None,None, None,None, 0,None,None, 14,
  75,None, 89.3,93.0,10.6),
R(62,"62_YangQ_2023","China","East Asia","Feb 2020","Feb 2022",
  "No","Naive","RCT","Elderly patients",
  "BQT-Quadruple","quadruple",0,
  "Esomeprazole",None,None, None,None, None,None, None,None, 1,None,None, 14,
  75,None, 86.6,90.3,26.6),

# ─── Ref 63: ZhangXD 2023, China/Hainan (ilaprazole, N=~260) ────────────────
R(63,"63_ZhangXD_2023","China","East Asia","","",
  "No","Naive","RCT","",
  "IA-Dual","dual",1,
  "Ilaprazole",None,None, None,None, None,None, None,None, 0,None,None, 14,
  None,None, 92.1,94.9,None),
R(63,"63_ZhangXD_2023","China","East Asia","","",
  "No","Naive","RCT","",
  "IAFB-Quadruple","quadruple",0,
  "Ilaprazole",None,None, None,None, None,None, None,None, 1,"Furazolidone",None, 14,
  None,None, 91.9,93.6,None),

# ─── Ref 64: ChenC 2024, China/Hainan (3 arms, N=135) ───────────────────────
R(64,"64_ChenC_2024","China","East Asia","","",
  "No","Naive","RCT","",
  "VPZ-Dual","dual",1,
  "Vonoprazan",20,2, None,None, None,None, None,None, 0,None,None, 14,
  45,None, 84.4,88.4,None),
R(64,"64_ChenC_2024","China","East Asia","","",
  "No","Naive","RCT","",
  "VPZ-Bismuth-Quad","quadruple",0,
  "Vonoprazan",20,2, None,None, None,None, None,None, 1,None,None, 14,
  45,41, None,92.7,None, "VPZ-based bismuth quadruple"),
R(64,"64_ChenC_2024","China","East Asia","","",
  "No","Naive","RCT","",
  "PPI-Bismuth-Quad","quadruple",0,
  "Esomeprazole",None,2, None,None, None,None, None,None, 1,None,None, 14,
  45,43, 84.4,88.4,None, "Standard PPI-based bismuth quadruple"),

# ─── Ref 65: CheungKS 2024, Southern China (3 arms, N=298, high CLR resist) ──
R(65,"65_CheungKS_2024","China","East Asia","","",
  "No","Naive","RCT","High CLR resistance >30%",
  "VA-Dual","dual",1,
  "Vonoprazan",20,2, None,None, None,None, None,None, 0,None,None, 14,
  100,None, 96.0,96.7,39.0),
R(65,"65_CheungKS_2024","China","East Asia","","",
  "No","Naive","RCT","High CLR resistance >30%",
  "VAC-Triple","triple",1,
  "Vonoprazan",20,2, None,None, None,None, None,None, 0,None,None, 14,
  98,None, 95.9,96.7,56.1),
R(65,"65_CheungKS_2024","China","East Asia","","",
  "No","Naive","RCT","High CLR resistance >30%",
  "Bismuth-Quad","quadruple",0,
  "Esomeprazole",None,2, None,None, None,None, None,None, 1,None,None, 14,
  100,None, 92.0,97.4,71.0),

# ─── Ref 66: GaoW 2024, China/Beijing (penicillin allergy, VT dual, N=300) ───
R(66,"66_GaoW_2024","China","East Asia","","",
  "Yes","Naive","RCT","Penicillin-allergic patients",
  "VT-Dual","dual",1,
  "Vonoprazan",20,2, None,None, None,None, None,None, 0,"Tetracycline",None, 14,
  150,142, 92.0,95.1,14.0, "Vonoprazan + tetracycline (penicillin-allergy alternative)"),
R(66,"66_GaoW_2024","China","East Asia","","",
  "Yes","Naive","RCT","Penicillin-allergic patients",
  "BQT-Quadruple","quadruple",0,
  "Esomeprazole",None,2, None,None, None,None, None,None, 1,None,None, 14,
  150,131, 89.3,97.7,48.0),

# ─── Ref 67: HuY 2024, China (VA dual BID vs VPZ quadruple, N=190) ──────────
R(67,"67_HuY_2024","China","East Asia","","",
  "No","Naive","RCT","",
  "VA-Dual-BID","dual",1,
  "Vonoprazan",20,2, 1000,2, None,None, None,None, 0,None,None, 14,
  95,None, 87.4,96.5,None, "Amox 1000mg BID (2g/day)"),
R(67,"67_HuY_2024","China","East Asia","","",
  "No","Naive","RCT","",
  "VPZ-Quad","quadruple",0,
  "Vonoprazan",20,2, None,None, None,None, None,None, 1,None,None, 14,
  95,None, 92.6,97.7,None, "Vonoprazan-based bismuth quadruple"),

# ─── Ref 68: REMOVED — duplicate of Ref 88 (Hu et al. 2025, Lancet Microbe).
#     The PDF 68_HuY_2025.pdf and 88_HuY_2025_LancetMicrobe.pdf are the same paper.
#     Removed on 2026-05-11 after PDF text comparison confirmed identity. ──────

# ─── Ref 69: KongQ 2024, China (EA vs TA dual, N=368) ────────────────────────
R(69,"69_KongQ_2024","China","East Asia","","",
  "No","Naive","RCT","",
  "TA-Dual","dual",1,
  "Tegoprazan",50,2, None,None, None,None, None,None, 0,None,None, 14,
  184,None, 85.8,88.2,None, "Tegoprazan (P-CAB) + amox dual"),
R(69,"69_KongQ_2024","China","East Asia","","",
  "No","Naive","RCT","",
  "EA-Dual","dual",0,
  "Esomeprazole",40,2, None,None, None,None, None,None, 0,None,None, 14,
  184,None, 84.2,88.5,None),

# ─── Ref 70: LiuHN 2024, China (TA dual vs TBAC quad, N=236, multicenter) ────
R(70,"70_LiuHN_2024","China","East Asia","","",
  "Yes","Naive","RCT","Multicenter",
  "TA-Dual","dual",1,
  "Tegoprazan",50,2, None,None, None,None, None,None, 0,None,None, 14,
  118,None, 83.9,88.3,4.2),
R(70,"70_LiuHN_2024","China","East Asia","","",
  "Yes","Naive","RCT","Multicenter",
  "TBAC-Quadruple","quadruple",0,
  "Tegoprazan",50,2, None,None, 500,2, None,None, 1,None,None, 14,
  118,None, 81.4,84.8,15.3, "Tegoprazan + bismuth + amox + clari"),

# ─── Ref 71: LiuZ 2024, China (VA 10d vs EA 14d, multicenter) ───────────────
R(71,"71_LiuZ_2024","China","East Asia","","",
  "Yes","Naive","RCT","Multicenter",
  "VA-Dual-10d","dual",1,
  "Vonoprazan",20,2, 1000,3, None,None, None,None, 0,None,None, 10,
  None,None, 85.4,91.1,9.1),
R(71,"71_LiuZ_2024","China","East Asia","","",
  "Yes","Naive","RCT","Multicenter",
  "EA-Dual-14d","dual",0,
  "Esomeprazole",20,2, 1000,3, None,None, None,None, 0,None,None, 14,
  None,None, 76.7,85.5,11.7),

# ─── Ref 72: LiuZ 2024, China (VA vs VBQT, retrospective, N=156 after PSM) ──
R(72,"72_LiuZ_2024","China","East Asia","","",
  "No","Naive","Retrospective","Propensity-score matched; not RCT",
  "VA-Dual","dual",1,
  "Vonoprazan",20,2, 1000,3, None,None, None,None, 0,None,None, 14,
  78,None, 87.2,94.4,10.3),
R(72,"72_LiuZ_2024","China","East Asia","","",
  "No","Naive","Retrospective","Propensity-score matched; not RCT",
  "VBQT-Quadruple","quadruple",0,
  "Vonoprazan",20,2, 1000,2, 500,2, None,None, 1,None,None, 14,
  78,None, 79.5,96.8,17.9),

# ─── Ref 73: PengX 2023 → EXCLUDED (oral microbiome study) ──────────────────

# ─── Ref 75: ParkH 2020 → EXCLUDED (gastric microbiome study) ───────────────

# ─── Ref 76: YangF 2023, China (VA 14d vs VA 10d vs Quadruple, N=600) ────────
R(76,"76_YangF_2023","China","East Asia","","",
  "No","Naive","RCT","",
  "VA-Dual-14d","dual",1,
  "Vonoprazan",20,2, 1000,3, None,None, None,None, 0,None,None, 14,
  200,None, 92.5,None,9.5),
R(76,"76_YangF_2023","China","East Asia","","",
  "No","Naive","RCT","",
  "VA-Dual-10d","dual",1,
  "Vonoprazan",20,2, 1000,3, None,None, None,None, 0,None,None, 10,
  200,None, 91.6,None,8.5),
R(76,"76_YangF_2023","China","East Asia","","",
  "No","Naive","RCT","",
  "Quad-14d","quadruple",0,
  "Rabeprazole",20,2, None,None, None,None, None,None, 1,None,None, 14,
  200,None, 80.1,None,17.0, "Rabeprazole + bismuth + amox + clari quadruple"),

# ─── Ref 77: LiM 2025, China (VM dual vs B-quad, N=240) ─────────────────────
R(77,"77_LiM_2025","China","East Asia","","",
  "No","Naive","RCT","For penicillin-ineligible patients",
  "VM-Dual","dual",1,
  "Vonoprazan",20,2, None,None, None,None, None,None, 0,"Minocycline",100, 14,
  120,None, 87.5,92.0,16.7, "Vonoprazan + minocycline (penicillin alternative)"),
R(77,"77_LiM_2025","China","East Asia","","",
  "No","Naive","RCT","",
  "B-Quad","quadruple",0,
  "Vonoprazan",None,None, None,None, None,None, None,None, 1,None,None, 14,
  120,None, 88.3,95.5,28.3),

# ─── Ref 78: YangXE 2025, China (4 arms: EA-dual, BQ, VA-dual, VAC-triple) ──
R(78,"78_YangXE_2025","China","East Asia","","",
  "Yes","Naive","RCT","4-arm multicenter",
  "EA-Dual","dual",1,
  "Esomeprazole",40,3, 750,4, None,None, None,None, 0,None,None, 14,
  92,None, 70.59,93.94,None),
R(78,"78_YangXE_2025","China","East Asia","","",
  "Yes","Naive","RCT","4-arm multicenter",
  "B-Quad","quadruple",0,
  "Esomeprazole",None,2, None,None, None,None, None,None, 1,None,None, 14,
  92,None, 83.49,98.38,None),
R(78,"78_YangXE_2025","China","East Asia","","",
  "Yes","Naive","RCT","4-arm multicenter",
  "VA-Dual","dual",1,
  "Vonoprazan",20,2, None,None, None,None, None,None, 0,None,None, 14,
  92,None, 84.15,96.75,None),
R(78,"78_YangXE_2025","China","East Asia","","",
  "Yes","Naive","RCT","4-arm multicenter",
  "VAC-Triple","triple",0,
  "Vonoprazan",20,2, None,None, 500,2, None,None, 0,None,None, 14,
  91,None, 83.15,93.75,None),

# ─── Ref 79: ZhangJY 2025, China/Fujian (VA dual vs BQT, N=250) ─────────────
R(79,"79_ZhangJY_2025","China","East Asia","Nov 2022","Apr 2024",
  "No","Naive","RCT","",
  "VA-Dual","dual",1,
  "Vonoprazan",20,2, None,None, None,None, None,None, 0,None,None, 14,
  125,None, 92.0,95.8,11.2),
R(79,"79_ZhangJY_2025","China","East Asia","Nov 2022","Apr 2024",
  "No","Naive","RCT","",
  "BQT-Quadruple","quadruple",0,
  "Esomeprazole",None,2, None,None, None,None, None,None, 1,None,None, 14,
  125,None, 88.0,91.7,20.8),
]

# Write CSV
with open(OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=COLS)
    writer.writeheader()
    writer.writerows(DATA)

print(f"✓ Wrote {len(DATA)} arms to {OUT}")

# Summary stats
from collections import Counter
countries = Counter(d["Country"] for d in DATA)
types = Counter(d["Treatment_Type"] for d in DATA)
ppis = Counter(d["PPI"] for d in DATA)
designs = Counter(d["Study_Design"] for d in DATA)

print(f"\nArms by country: {dict(countries.most_common(8))}")
print(f"Treatment types: {dict(types)}")
print(f"PPIs: {dict(ppis)}")
print(f"Study designs: {dict(designs)}")

refs_unique = sorted(set(d["Ref"] for d in DATA))
print(f"\nUnique refs covered: {len(refs_unique)}")
print(f"Refs: {refs_unique}")
