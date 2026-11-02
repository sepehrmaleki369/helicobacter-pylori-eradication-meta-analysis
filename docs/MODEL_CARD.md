> Later data audit: three saved success counts and one proportion are stale; see DATA_ISSUES.md. This model card does not establish fresh refitting after those corrections.

# H. pylori model card — reporting audit, 2 November 2026

This is an exploratory arm-level analysis of 60 studies, 140 arms and 17,887
patients. It is not a validated clinical decision tool. Trial data and fitting
artifacts were retained unchanged during this reporting audit.

## Inference

The primary Bayesian binomial model uses a fixed, clinically motivated set of
15 covariates and study random intercepts. Prospective specification is not
established by a dated protocol. Saved posterior estimates include vonoprazan
OR 1.92 (95% HDI 1.67–2.21), susceptibility-guided therapy 1.58 (1.04–2.42),
and quadruple regimen 1.54 (1.16–2.03). These are adjusted arm-level associations.
Diagnostics in the saved report: maximum R-hat 1.010, minimum bulk ESS 1006;
study SD 0.512 (0.406–0.644).

## Prediction

The verified comparison uses the same six cached non-Bayesian prediction pairs
for regression and threshold classification. All six use 39 predictors. The
saved scripts fit training-fold imputation/scaling and sample-size weighting
where supported; Gaussian Process fitting does not support those weights.
Evaluation metrics give equal weight to arms. Per-fold provenance logs are
unavailable; this was a reporting rebuild, not a fresh reproduction of fits.

| Model | LOO-arm R² | LOSO-study R² | LOSO RMSE (percentage points) |
| --- | --- | --- | --- |
| Gaussian Process | +0.188 | +0.046 | 10.17 |
| LightGBM | +0.213 | +0.028 | 10.27 |
| RandomForest | +0.235 | +0.012 | 10.36 |
| ElasticNet | +0.137 | -0.008 | 10.46 |
| XGBoost | +0.341 | -0.019 | 10.52 |
| GradientBoost | +0.276 | -0.083 | 10.84 |

The saved Bayesian LOO-arm R² is +0.407, but preprocessing used the full cohort
and same-study information can remain in training. Genuine Bayesian LOSO is
unavailable. Full-cohort predictions with random intercept zero yield apparent
R² +0.209, RMSE 9.26 percentage points, slope 1.072 and intercept −0.076 against
reported ITT rates. Earlier slope 1.070 used success counts/sample sizes instead;
neither is held-out-study calibration.

BART is excluded: all 140 cached LOO-arm and LOSO predictions reproduce the
training-mean failure fallback to numerical precision. Its near-zero or reversed
AUCs are properties of that fallback, not fitted BART performance.

The separate RFE-RandomForest artifact used globally selected features before
cross-validation. Its reported LOSO R² +0.054 and RMSE 10.13 percentage points
remain exploratory and require nested selection. Its ten selected features are
Is_Quadruple, Is_Standard_PPI, Is_Bismuth_Quad, CLR_Resistance_pct,
MTZ_Resistance_pct, AMX_Resistance_pct, CLR_use_x_CLR_resistance,
Is_High_CLR_Region, Is_High_AMX_Region and Is_Latin_America. Largest mean absolute
SHAP attribution: CLR-use × CLR-resistance, 2.18 percentage points.

Classification targets of 85% and 90% are exploratory operational thresholds.
Probabilities assume normal residual SD of ten percentage points and have not
been independently calibrated. They are not labelled guideline-defined categories.

## Remaining limits

- Screening-stage allocation and the nominal ≥40-per-arm eligibility rule remain
  unreconciled (13 retained arms are smaller; Ref 81 uses quasi-random allocation).
- Last search date and exact executable search queries are unconfirmed.
- Bayesian LOSO, fold-specific Bayesian preprocessing, nested RFE validation and
  external validation have not been established.
- Dataset missingness indicators do not equal current missing-value counts.
- Existing fitting scripts and reports retain historical errors. Use the audited
  reporting outputs; rerunning historical scripts can overwrite cached files.

Local evidence: project/report/prediction_reporting_2026-11-02.json;
paper/MANUSCRIPT_AUDIT_2026-11-02.json; project/scripts/13_audit_manuscript.py;
project/scripts/14_rebuild_prediction_reporting.py. The repository copy of this
card and README were corrected locally; no public push was performed.
