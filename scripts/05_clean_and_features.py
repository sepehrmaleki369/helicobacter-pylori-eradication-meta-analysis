"""
Phase 3: Data cleaning + feature engineering.
Output: data/processed/clean_dataset.csv
"""
import csv, os, math

IN  = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/data/processed/arm_dataset_with_resistance.csv"
OUT = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/data/processed/clean_dataset.csv"

def flt(v, default=None):
    try: return float(v) if v not in (None, "", "None") else default
    except: return default

def intt(v, default=None):
    try: return int(float(v)) if v not in (None, "", "None") else default
    except: return default

with open(IN, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

clean = []
excluded = []
flags = []

for r in rows:
    ref = int(r["Ref"])
    arm = r["Arm_Label"]

    # ── Exclusions ──────────────────────────────────────────────────────────────
    # 1. Protocol papers (no results)
    if ref == 38:
        excluded.append((ref, arm, "protocol paper, no results"))
        continue
    # 2. Non-eradication studies
    if ref in (40, 73, 75):
        excluded.append((ref, arm, "microbiome study, not eradication RCT"))
        continue
    # 3. Arms with incomplete outcome data
    itt = flt(r.get("ITT_Rate"))
    pp  = flt(r.get("PP_Rate"))
    if itt is None and pp is None:
        excluded.append((ref, arm, "no eradication rate data"))
        continue

    # ── Flag non-RCT ────────────────────────────────────────────────────────────
    design = r.get("Study_Design", "")
    quality_flag = []
    if design in ("Observational", "Retrospective"):
        quality_flag.append(f"non-RCT ({design})")

    # ── Primary outcome: use ITT if available, else PP ──────────────────────────
    primary_rate = itt if itt is not None else pp
    rate_type    = "ITT" if itt is not None else "PP"

    # ── Categorical flags ────────────────────────────────────────────────────────
    ppi = r.get("PPI", "")
    is_pcab    = 1 if ppi in ("Vonoprazan", "Tegoprazan") else 0
    is_vono    = 1 if ppi == "Vonoprazan" else 0
    is_teg     = 1 if ppi == "Tegoprazan" else 0
    is_ppi_std = 1 if ppi in ("Esomeprazole","Lansoprazole","Rabeprazole","Omeprazole","Pantoprazole","Ilaprazole") else 0

    ttype = r.get("Treatment_Type", "")
    is_dual      = 1 if ttype == "dual" else 0
    is_triple    = 1 if ttype == "triple" else 0
    is_quadruple = 1 if ttype in ("quadruple", "nonbismuth_quadruple", "sequential") else 0
    is_suscept_guided = 1 if str(r.get("Is_Susceptibility_Guided","")).strip() in ("1","1.0") else 0

    # Quadruple sub-types (parsed from arm label / notes)
    arm_l = arm.lower()
    notes_l = (r.get("Notes","") or "").lower()
    is_concomitant = 1 if (is_quadruple and ("concomitant" in arm_l or "conc" in arm_l
                                              or "concomitant" in notes_l)) else 0
    is_sequential  = 1 if (is_quadruple and ("sequential" in arm_l or "sequential" in notes_l
                                              or arm_l.startswith("st-"))) else 0
    is_hybrid      = 1 if (is_quadruple and ("hybrid" in arm_l or "hybrid" in notes_l)) else 0
    is_bismuth_quad = 1 if (is_quadruple and int(r.get("Bismuth_used", 0) or 0) == 1) else 0
    has_bismuth  = intt(r.get("Bismuth_used"), 0)
    has_clari    = 1 if flt(r.get("Clarithromycin_mg_per_dose")) else 0
    has_metro    = 1 if flt(r.get("Metronidazole_mg_per_dose")) else 0
    has_other_ab = 1 if r.get("Other_Antibiotic") not in (None, "", "None") else 0

    other_ab = r.get("Other_Antibiotic", "") or ""
    is_tetra_dual = 1 if "Tetracycline" in other_ab else 0
    is_mino_dual  = 1 if "Minocycline" in other_ab else 0
    is_furaz_quad = 1 if "Furazolidone" in other_ab else 0

    # ── Dose features ────────────────────────────────────────────────────────────
    amox_daily = flt(r.get("Total_Amox_Daily_mg"))
    if not amox_daily:
        amox_dose = flt(r.get("Amoxicillin_mg_per_dose"))
        amox_freq = flt(r.get("Amoxicillin_freq_per_day"))
        amox_daily = amox_dose * amox_freq if amox_dose and amox_freq else None

    ppi_daily = flt(r.get("Total_PPI_Daily_mg"))
    if not ppi_daily:
        ppi_dose = flt(r.get("PPI_Dose_mg"))
        ppi_freq = flt(r.get("PPI_Freq_per_day"))
        ppi_daily = ppi_dose * ppi_freq if ppi_dose and ppi_freq else None

    duration = flt(r.get("Duration_Days"))

    # ── Patient covariates (T1.1) ───────────────────────────────────────────────
    mean_age     = flt(r.get("Mean_Age_yr"))
    compliance   = flt(r.get("Compliance_pct"))
    age_missing  = 1 if mean_age   is None else 0
    comp_missing = 1 if compliance is None else 0

    # ── Multicenter + Study Era (Round 2 Tier A4) ──────────────────────────────
    multicenter = r.get("Multicenter", "") or ""
    is_multicenter = 1 if multicenter.lower() in ("yes", "y", "true", "1") else 0

    period_end = r.get("Study_Period_End", "") or ""
    try:
        # Take last 4 chars as year
        study_era = int(period_end.strip()[-4:])
        if not (2000 <= study_era <= 2030):
            study_era = None
    except (ValueError, AttributeError):
        study_era = None
    study_era_missing = 1 if study_era is None else 0

    # Amox daily missing indicator
    amox_daily_missing = 1 if amox_daily is None else 0

    # ── Resistance features ──────────────────────────────────────────────────────
    clr_resist  = flt(r.get("CLR_Resistance_pct"))
    mtz_resist  = flt(r.get("MTZ_Resistance_pct"))
    amx_resist  = flt(r.get("AMX_Resistance_pct"))
    lfx_resist  = flt(r.get("LFX_Resistance_pct"))

    # Interaction: clarithromycin use × clarithromycin resistance
    clr_use_x_resist = (clr_resist or 0) * has_clari

    # ── Region encoding ──────────────────────────────────────────────────────────
    region = r.get("Geographic_Region", "")
    is_east_asia    = 1 if region == "East Asia" else 0
    is_western      = 1 if region == "Western" else 0
    is_south_asia   = 1 if region in ("South Asia", "Middle East") else 0
    is_latin_am     = 1 if region == "Latin America" else 0
    is_southeast_asia = 1 if region == "Southeast Asia" else 0

    # High vs low resistance region
    is_high_clr_region = 1 if (clr_resist or 0) >= 30 else 0
    is_high_amx_region = 1 if (amx_resist or 0) >= 10 else 0

    # ── N (sample size) ──────────────────────────────────────────────────────────
    n_itt = intt(r.get("N_ITT"))

    # ── Quality flags ────────────────────────────────────────────────────────────
    if r.get("Resistance_Source_Type") == "regional-estimate":
        quality_flag.append("resistance-estimated")
    if n_itt is None:
        quality_flag.append("N-missing")
    if ref in (47, 53, 63) and "Ilaprazole" in ppi:
        quality_flag.append("ilaprazole-uncommon-PPI")
    if r.get("Study_Quality_Flag", "") == "small-pilot (n=33/arm)":
        quality_flag.append("small-pilot")

    c = {
        # Identifiers
        "Ref": ref,
        "File": r.get("File"),
        "Arm_Label": arm,
        "Country": r.get("Country"),
        "Geographic_Region": region,
        "Study_Period_Start": r.get("Study_Period_Start"),
        "Study_Period_End": r.get("Study_Period_End"),
        "Study_Design": design,
        "Multicenter": r.get("Multicenter"),
        "Treatment_Naive_vs_Rescue": r.get("Treatment_Naive_vs_Rescue"),
        "Arm_Is_Intervention": intt(r.get("Arm_Is_Intervention")),
        "Quality_Flags": "; ".join(quality_flag),

        # Treatment features
        "PPI": ppi,
        "Is_PCAB": is_pcab,
        "Is_Vonoprazan": is_vono,
        "Is_Tegoprazan": is_teg,
        "Is_Standard_PPI": is_ppi_std,
        "PPI_Dose_mg": flt(r.get("PPI_Dose_mg")),
        "PPI_Freq_per_day": flt(r.get("PPI_Freq_per_day")),
        "PPI_Daily_mg": ppi_daily,
        "Treatment_Type": ttype,
        "Is_Dual": is_dual,
        "Is_Triple": is_triple,
        "Is_Quadruple": is_quadruple,
        "Has_Bismuth": has_bismuth,
        "Has_Clarithromycin": has_clari,
        "Has_Metronidazole": has_metro,
        "Has_Other_Antibiotic": has_other_ab,
        "Is_Tetracycline_Dual": is_tetra_dual,
        "Is_Minocycline_Dual": is_mino_dual,
        "Is_Furazolidone_Quad": is_furaz_quad,
        "Amox_Dose_mg": flt(r.get("Amoxicillin_mg_per_dose")),
        "Amox_Freq_per_day": flt(r.get("Amoxicillin_freq_per_day")),
        "Amox_Daily_mg": amox_daily,
        "Clari_Dose_mg": flt(r.get("Clarithromycin_mg_per_dose")),
        "Metro_Dose_mg": flt(r.get("Metronidazole_mg_per_dose")),
        "Other_AB_Dose_mg": flt(r.get("Other_Antibiotic_mg")),
        "Duration_Days": duration,

        # Resistance
        "CLR_Resistance_pct": clr_resist,
        "MTZ_Resistance_pct": mtz_resist,
        "AMX_Resistance_pct": amx_resist,
        "LFX_Resistance_pct": lfx_resist,
        "Resistance_Source_Type": r.get("Resistance_Source_Type"),
        "CLR_use_x_CLR_resistance": clr_use_x_resist,

        # Region binary
        "Is_East_Asia": is_east_asia,
        "Is_Western": is_western,
        "Is_South_Asia_ME": is_south_asia,
        "Is_Latin_America": is_latin_am,
        "Is_Southeast_Asia": is_southeast_asia,
        "Is_High_CLR_Region": is_high_clr_region,
        "Is_High_AMX_Region": is_high_amx_region,

        # Outcomes
        "N_ITT": n_itt,
        "N_PP": intt(r.get("N_PP")),
        "ITT_Rate": itt,
        "PP_Rate": pp,
        "AE_Rate": flt(r.get("AE_Rate")),
        "Primary_Rate": primary_rate,
        "Primary_Rate_Type": rate_type,
        # Binary outcome for classification
        "Success_ITT_85": int(itt >= 85) if itt is not None else None,
        "Success_ITT_90": int(itt >= 90) if itt is not None else None,
        "Success_PP_90":  int(pp  >= 90) if pp  is not None else None,

        # Patient covariates (T1.1)
        "Mean_Age_yr": mean_age,
        "Compliance_pct": compliance,
        "Mean_Age_missing": age_missing,
        "Compliance_missing": comp_missing,
        # Susceptibility-guided flag (new with Refs 100-104)
        "Is_Susceptibility_Guided": is_suscept_guided,

        # Round 2 Tier A: quadruple sub-types + multicenter + era + dose-missing
        "Is_Concomitant": is_concomitant,
        "Is_Sequential": is_sequential,
        "Is_Hybrid": is_hybrid,
        "Is_Bismuth_Quad": is_bismuth_quad,
        "Is_Multicenter": is_multicenter,
        "Study_Era": study_era,
        "Study_Era_missing": study_era_missing,
        "Amox_Daily_missing": amox_daily_missing,

        # Proportion + success count for Tier 2/3 (F4)
        "ITT_Prop": (itt/100.0) if itt is not None else None,
        "Successes_ITT": (round(itt/100.0 * n_itt) if (itt is not None and n_itt is not None) else None),
    }
    clean.append(c)

# ── Write ──────────────────────────────────────────────────────────────────────
if clean:
    all_cols = list(clean[0].keys())
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_cols)
        writer.writeheader()
        writer.writerows(clean)

print(f"✓ Clean dataset: {len(clean)} arms → {OUT}")
print(f"  Excluded: {len(excluded)}")
for ref, arm, reason in excluded:
    print(f"    Ref {ref} {arm}: {reason}")

print(f"\n── Data completeness ──")
for col in ["ITT_Rate", "PP_Rate", "N_ITT", "Amox_Daily_mg", "PPI_Daily_mg",
            "CLR_Resistance_pct", "Duration_Days", "Mean_Age_yr", "Compliance_pct"]:
    n_missing = sum(1 for r in clean if r.get(col) in (None, ""))
    pct_missing = 100 * n_missing / len(clean)
    print(f"  {col:<25}: {n_missing:>3} missing ({pct_missing:.0f}%)")

print(f"\n── Outcome distribution ──")
itts = [r["ITT_Rate"] for r in clean if r["ITT_Rate"] is not None]
pps  = [r["PP_Rate"]  for r in clean if r["PP_Rate"]  is not None]
print(f"  ITT rates: n={len(itts)}, mean={sum(itts)/len(itts):.1f}%, "
      f"min={min(itts):.1f}%, max={max(itts):.1f}%")
if pps:
    print(f"  PP  rates: n={len(pps)},  mean={sum(pps)/len(pps):.1f}%,  "
          f"min={min(pps):.1f}%, max={max(pps):.1f}%")

successes = sum(1 for r in clean if r["Success_ITT_85"] == 1)
total_with_itt = sum(1 for r in clean if r["Success_ITT_85"] is not None)
print(f"\n  Arms with ITT ≥85%: {successes}/{total_with_itt} = {100*successes/total_with_itt:.0f}%")

dual_arms = [r for r in clean if r["Is_Dual"] == 1 and r["ITT_Rate"] is not None]
quad_arms = [r for r in clean if r["Is_Quadruple"] == 1 and r["ITT_Rate"] is not None]
if dual_arms:
    print(f"  Dual therapy mean ITT: {sum(r['ITT_Rate'] for r in dual_arms)/len(dual_arms):.1f}% (n={len(dual_arms)})")
if quad_arms:
    print(f"  Quadruple therapy mean ITT: {sum(r['ITT_Rate'] for r in quad_arms)/len(quad_arms):.1f}% (n={len(quad_arms)})")
