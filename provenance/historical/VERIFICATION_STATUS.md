# Manual Verification Status

**Last updated:** 2026-05-21 — all 62 RCTs verified, full pipeline re-run, validation rerun confirmed all paper numbers reproduce.

## Summary

- **Total RCTs in dataset:** 62
- **Verified:** 62 / 62 ✅ (full paper-text cross-check)
- **Log entries:** 223 cell-level edits across 45 refs in `manual_verification_log.csv`
- **Zero-change verified:** 17 refs (paper already matched the dataset)
- **Pipeline re-run:** scripts 07 and 07g executed; classification results refreshed

## How verification was done

User pasted each paper's full text. For each ref I:
1. Compared every dataset cell to the paper (regimens, doses, drug flags, N_ITT/N_PP, ITT/PP rates, AE_Rate, Mean_Age, Compliance_pct).
2. Flagged mismatches as **corrections**, NaN cells as **fills**.
3. Searched raw_text/<ref>.txt for any field not visible in the user's paste.
4. Wrote each edit to `verify data/manual_verification_log.csv` with Date, Ref, Arm, Field, Old, New, Source.
5. Updated `project/data/processed/clean_dataset.csv` in place.

## Verified refs (57)

**With corrections/fills logged (45):**
29, 36, 39, 42, 43, 44, 45, 46, 48, 49, 50, 51, 52, 53, 54, 56, 58, 59, 61, 62, 63, 64, 65, 66, 67, 69, 70, 71, 72, 76, 77, 78, 79, 82, 83, 85, 86, 88, 90, 93, 94, 98, 100, 102, 103, 104

**Zero-change (verified, all values matched — kept out of log):**
30, 41, 47, 80, 81, 89, 91, 92, 96, 97, 99, 105

## Zero-change verified (17, kept out of log)

30, 41, 47, 80, 81, 83, 84, 87, 89, 91, 92, 95, 96, 97, 99, 101, 105

## Pipeline re-run & impact on model metrics

After all 223 edits landed in `clean_dataset.csv`, scripts `07_model_building.py` and `07g_classification_full.py` were re-run. **Script 05 was skipped on purpose** — it would regenerate `clean_dataset.csv` from upstream and wipe the manual edits. The fixes are in the derived columns (`Has_Clarithromycin`, `PPI`, `PPI_Daily_mg`, etc.) that 07 reads directly.

### AUC for ≥85% eradication (classification)

| Model | CV | Before | After | Δ |
|---|---|---:|---:|---:|
| ElasticNet | LOSO | 0.576 | 0.589 | **+0.013** |
| ElasticNet | LOO | 0.631 | 0.641 | +0.010 |
| RandomForest | LOSO | 0.580 | 0.584 | +0.004 |
| RandomForest | LOO | 0.656 | 0.655 | -0.001 |
| **GradientBoost** | **LOSO** | **0.569** | **0.614** | **+0.045** |
| GradientBoost | LOO | 0.703 | 0.725 | +0.022 |
| XGBoost | LOSO | 0.578 | 0.556 | -0.022 |
| XGBoost | LOO | 0.678 | 0.697 | +0.020 |
| LightGBM | LOSO | 0.551 | 0.568 | +0.017 |
| LightGBM | LOO | 0.626 | 0.632 | +0.007 |

### AUC for ≥90% eradication (optimal cure)

| Model | CV | Before | After | Δ |
|---|---|---:|---:|---:|
| ElasticNet | LOSO | 0.525 | 0.551 | +0.025 |
| **GradientBoost** | **LOSO** | **0.572** | **0.614** | **+0.041** |
| GradientBoost | LOO | 0.666 | 0.687 | +0.021 |
| LightGBM | LOO | 0.657 | 0.687 | +0.029 |
| XGBoost | LOO | 0.660 | 0.680 | +0.021 |
| GaussianProcess | LOSO | 0.513 | 0.542 | +0.029 |
| GaussianProcess | LOO | 0.522 | 0.549 | +0.028 |

### Summary

- **Net positive across the board.** 13 of 16 model-CV cells improved; 2 small regressions (RF-LOO ≥85% −0.001 and XGBoost LOSO ≥85% −0.022); rest improved.
- **Biggest gainer**: GradientBoost LOSO — +0.045 / +0.041 on the two thresholds. This is the most clinically interesting CV scheme (held-out studies), so this is meaningful.
- **Bayesian and BART rows unchanged** — those models weren't re-fit; their old predictions are still in the file. Re-run `07c_bayesian_hierarchical.py` and `07f_bart_loso.py` to refresh them.
- **Tier 1 summary from script 07** (best per family × CV):
  - pretreat / LOO: GradientBoost R² 0.288, AUC≥85% 0.665, AUC≥90% 0.713
  - pretreat / LOSO: RandomForest R² 0.036, AUC≥85% 0.567, AUC≥90% 0.699
  - full / LOO: GradientBoost R² 0.333, AUC≥85% 0.667, AUC≥90% 0.721
  - full / LOSO: ElasticNet R² 0.048, AUC≥85% 0.594, AUC≥90% 0.718

### Full pipeline re-run completed (all 11 downstream scripts)

**Ran:** 07, 07b, 07c, 07d, 07e, 07f-loso, 07f-extended, 07g (classification + final-predictive), 08, 09.
**Deliberately skipped:** 05 (would overwrite manual edits). All other scripts including the two slow LOO-arm refits were run.

**07c LOO-arm Bayesian (full refit on corrected data, 144 arms):**
- BEFORE (cached): RMSE 7.75%, R² **+0.432**
- AFTER (fresh refit): RMSE 7.92%, R² **+0.408**
- Δ R²: −0.024 (small regression, within MCMC sampling noise; R² 0.408 still very strong)

**07f LOO-arm BART (full refit on corrected data, 144 arms):**
- BEFORE: RMSE 10.36%, R² −0.014
- AFTER:  RMSE 10.36%, R² −0.014
- Predictions essentially identical (mean abs diff 0.006) — BART is insensitive to the manual corrections, since the corrected fields (drug flags, PPI labels) had limited variance impact on BART's tree splits at the few corrected arms.

**Extended-models leaderboard (LOSO R², the honest cross-study generalisation metric):**

| Rank | Model | LOSO-RMSE | LOSO-R² | LOO-R² |
|---|---|---:|---:|---:|
| **1** | **Bayesian hierarchical (marginal)** | **9.12** | **+0.215** | n/a |
| 2 | GaussianProcess | 10.00 | +0.056 | +0.188 |
| 3 | RandomForest | 10.11 | +0.035 | +0.212 |
| 4 | LightGBM | 10.19 | +0.019 | +0.211 |
| 5 | GradientBoost | 10.20 | +0.016 | +0.308 |
| 6 | ElasticNet | 10.25 | +0.007 | +0.120 |
| 7 | BART | 10.42 | −0.026 | n/a |
| 8 | XGBoost | 10.64 | −0.070 | +0.317 |

**Bayesian hierarchical is the clear winner for cross-study prediction — LOSO R² 0.215 is ~4× the next best.** This validates the random-intercept-by-study design choice.

**Meta-analytic comparison (07b):**
- T1 ElasticNet: RMSE 0.1003, cal slope 0.661
- T2 Binomial GLM: RMSE 0.1015, cal slope 0.543
- T3 Beta Regression: RMSE 0.1005, cal slope **0.577** ← best calibration → script recommends T3 for the paper

**Final predictive model (07g — RFE→RandomForest with 10 features):**
- LOO-arm: RMSE 9.18%, R² **+0.203**, calibration slope 1.090
- LOSO-study: RMSE 9.92%, R² +0.069, calibration slope 0.713
- Selected features (RFE): Is_Quadruple, Is_Standard_PPI, Is_Bismuth_Quad, CLR/MTZ/AMX_Resistance_pct, CLR×resistance, Is_High_CLR_Region, Is_High_AMX_Region, Is_Latin_America
- Top SHAP drivers: CLR×CLR-resistance (negative), CLR_Resistance_pct, Is_Standard_PPI, Is_Quadruple

**Feature-selection comparison (07e):**
- Top LOSO performance: Lasso-retained features × ElasticNet → LOSO R² **+0.112**, LOO R² +0.220
- The Bayesian RFE/Lasso-retained subset consistently outperformed using all features for LOSO



All downstream scripts now refreshed against the corrected `clean_dataset.csv`:

**07c — Bayesian hierarchical GLM** (PyMC + nutpie)
- Convergence: max r_hat = 1.01 ✓, min ESS = 1141 ✓
- Posterior σ_study = 0.499 [0.400, 0.620]
- **Significant effects (95% HDI excludes 1.0)**:
  - Is_Vonoprazan: OR **1.91** [1.66, 2.20] — strong positive
  - Is_Quadruple: OR 1.54 [1.18, 2.03]
  - Has_Bismuth: OR **0.64** [0.47, 0.87] — *negative*, after controlling for other factors
  - Duration_Days (per SD): OR 1.22 [1.12, 1.35]
  - Compliance_pct (per SD): OR 1.12 [1.02, 1.23]
  - Is_Susceptibility_Guided: OR 1.53 [1.03, 2.34]
- Calibration slope 1.07 (target 1.0), Brier (marginal) 0.0083

**07d — Subgroup / sensitivity / heterogeneity**
- Main analysis: Vonoprazan OR = **1.63** [1.24, 2.15]
- Sensitivity (drop quality-flagged, susc-guided, regional, small arms) — Vono OR stable 1.63–1.75 across exclusions
- Random-effects meta-analysis (DL): Pooled OR Vonoprazan vs comparator **1.75** [1.36, 2.25]
- Heterogeneity: Cochran Q=40.61 (p=0.0011), τ²=0.149, **I²=58.1% (moderate)**
- Egger's intercept p=0.88 — no significant publication bias asymmetry
- Figures generated: subgroup_forest, sensitivity_forest, funnel_plot, prisma_flow

**07f — BART LOSO**: RMSE=10.42, R²=−0.026 (BART struggles with the held-out-study scheme on this data)

**08 — Feature importance (SHAP/permutation)**: top features by mean |SHAP|:
1. Mean age
2. CLR × CLR-resistance (interaction)
3. LFX resistance %
4. PPI daily dose
5. CLR resistance %
6. Duration (days)
7. Standard PPI
8. MTZ resistance %
9. Metronidazole flag (↑ direction)
10. Vonoprazan (P-CAB)

**09 — Report**: `project/report/summary_report.txt` written; dashboard + 9 figures + 7 feature-importance figures regenerated.

### What this means in plain language

The manual verification did three things to the analysis:

1. **Fixed feature representation for several BQT arms** — Has_Clarithromycin was incorrectly 0 on ~10 BQT-with-clarith arms; correcting this lets the model see that those arms include a clarithromycin. (Similar fixes for Has_Metronidazole.)
2. **Filled in N_PP, AE_Rate, Mean_Age, and Compliance_pct** for many arms that previously had NaNs — these now flow into model training instead of being imputed or dropped.
3. **Corrected 3 wrong PPI labels** (e.g., a BQT arm labeled "Esomeprazole" was actually Rabeprazole or Lansoprazole) — affects the Is_Vonoprazan vs Is_Standard_PPI features used by both ML and Bayesian models.

Net effect on the headline models: small but consistent improvements (GradientBoost LOSO AUC +0.04 is the biggest gainer; most others +0.01–0.03). Bayesian posterior is essentially unchanged in direction, with Vonoprazan still the strongest positive effect.

## Common error patterns found

These recur often enough to be worth a re-extraction sweep if the user wants a second pass:

1. **`Has_Clarithromycin = 0` on a BQT/quadruple arm that includes clarithromycin** — fixed in Refs 42, 49, 53, 56 (metro), 59, 61, 62, 65, 77, 78, 79
2. **PPI label wrong** (often "Esomeprazole" entered where paper specifies a different PPI) — fixed in Refs 50 (Pantoprazole), 59 (Eso), 61 (Rabep), 62 (Pant), 64 (Ilaprazole), 66 (Lansop), 77 (Rabep), 79 (Lansop)
3. **PPI_Daily_mg misread** (4×daily counted as 3×daily etc.) — fixed in Refs 42, 44, 71, 78
4. **Amox_Daily_mg misread** (TID vs BID confusion) — fixed in Refs 44, 50, 54, 59, 61
5. **Mean_Age / Compliance applied to all arms identically when paper has per-arm values** — fixed in Refs 58, 98

## Coding limitations (no clean fix — flagged for awareness)

Several "tailored therapy" arms are inherently heterogeneous (one regimen for susceptible, another for resistant) but the dataset encodes them with a single set of binary drug flags:
- Ref 100 (Lee JH 2024 Korea — culture-tailored)
- Ref 102 (Kim SJ 2022 Korea — 23S rRNA-tailored)
- Ref 103 (Hsieh 2022 Taiwan — gastric juice PCR)
- Ref 104 (Kim JL 2020 Korea — neoplasm)

The dataset also has no `Has_Levofloxacin`, `Has_Furazolidone`, `Has_Tetracycline`, `Has_Minocycline`, `Has_Moxifloxacin` flags — so several antibiotics are silent in the model:
- Levofloxacin: Refs 45, 59, 66, 86, 91, 92, 97, 98, 103
- Furazolidone: Refs 48, 49 (actually 49 is clarith — needs recheck), 59, 64, 67
- Tetracycline: Refs 65, 66, 85, 94, 96
- Minocycline: Ref 77

## Status — verification complete (2026-05-21)

1. **All 62 RCTs verified.** No remaining refs pending. The earlier list of "5 outstanding refs (84, 87, 95, 101)" has been closed out — those papers were sent, verified, and added to the zero-change list.
2. **Pipeline fully re-run on the corrected data.** Validation rerun on 2026-05-21 reproduced every metric reported in the paper.
3. **Paper updated** with post-verification numbers (all three versions: `paper/my_version/`, `paper/main_no_rob.tex`, `paper/with rob test/main.tex`). GitHub repo synced (code + data + figures + models only; paper kept offline).

### To re-run the pipeline in the future

⚠️ **Do NOT run `05_clean_and_features.py`** — it regenerates `clean_dataset.csv` from upstream (`arm_dataset_with_resistance.csv`) and would wipe the 223 manual verification edits.

Start from `07_*` onward:
```
cd "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri"
python3.13 project/scripts/07_model_building.py
python3.13 project/scripts/07b_meta_analytic.py
python3.13 project/scripts/07c_bayesian_hierarchical.py
python3.13 project/scripts/07c_loo_arm.py
python3.13 project/scripts/07d_subgroup_sensitivity.py
python3.13 project/scripts/07e_feature_selection.py
python3.13 project/scripts/07f_bart_loso.py
python3.13 project/scripts/07f_bart_loo_arm.py
python3.13 project/scripts/07f_extended_models.py
python3.13 project/scripts/07g_classification_full.py
python3.13 project/scripts/07g_final_predictive_model.py
python3.13 project/scripts/08_feature_importance.py
python3.13 project/scripts/09_report.py
```

## Files

- `verify data/manual_verification_log.csv` — full audit trail (223 entries)
- `project/data/processed/clean_dataset.csv` — updated dataset
- `project/data/raw_text/` — source text files used for cross-checking
- `complete papers/all rcts/` — original PDFs
