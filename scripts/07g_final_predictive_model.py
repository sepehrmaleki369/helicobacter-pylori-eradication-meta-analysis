"""
Phase Final — Headline predictive model (frequentist ML side).

Based on the comparison in 07e (feature selection) and 07f (extended models),
the best non-Bayesian predictor is:

    RFE top-10 features + RandomForest

This script:
  1. Performs RFE (Ridge-based) to select top-10 features
  2. Fits weighted RandomForest on full data
  3. Cross-validates with LOO + LOSO and reports honest metrics
  4. Computes SHAP attributions for clinical interpretation
  5. Saves the model and predictions for use in the report
  6. Compares to all-features baseline and Bayesian hierarchical

Outputs:
  - models/final_predictive_rfe_rf.pkl
  - models/final_predictive_loso_ypred.npy
  - figures/final_predictive_*.png
  - report/final_predictive_results.txt
"""
import os, math, pickle, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")

import shap
from sklearn.feature_selection import RFE
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import LeaveOneOut, LeaveOneGroupOut
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_squared_error, r2_score, brier_score_loss

IN  = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/data/processed/clean_dataset.csv"
MDL = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/models"
FIG = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/figures"
RPT = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/report"

with open(f"{MDL}/feature_names_pretreat.pkl", "rb") as f:
    ALL_FEATURES = pickle.load(f)

df = pd.read_csv(IN).dropna(subset=["ITT_Rate","N_ITT","Successes_ITT"]).reset_index(drop=True)
X_all = df[ALL_FEATURES].apply(pd.to_numeric, errors="coerce").values.astype(float)
y = df["ITT_Rate"].values.astype(float)
w = df["N_ITT"].values.astype(float)
g = df["Ref"].astype(int).values
print(f"Dataset: {len(df)} arms, {len(set(g))} studies, {len(ALL_FEATURES)} candidate features")

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  Step 1: RFE top-10 feature selection (Ridge as estimator)                ║
# ╚════════════════════════════════════════════════════════════════════════════╝
print("\n── Step 1: RFE top-10 feature selection ──")
X_for_rfe = SimpleImputer(strategy="median").fit_transform(X_all)
X_for_rfe = StandardScaler().fit_transform(X_for_rfe)
rfe = RFE(Ridge(alpha=1.0), n_features_to_select=10, step=1)
rfe.fit(X_for_rfe, y, sample_weight=w)
SELECTED_FEATURES = [ALL_FEATURES[i] for i, s in enumerate(rfe.support_) if s]
print(f"  Selected {len(SELECTED_FEATURES)} features:")
for i, f in enumerate(SELECTED_FEATURES, 1):
    print(f"    {i:>2}. {f}")

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  Step 2: Cross-validated evaluation (LOO + LOSO) of the reduced model     ║
# ╚════════════════════════════════════════════════════════════════════════════╝
print("\n── Step 2: Cross-validated evaluation ──")
X_sel = df[SELECTED_FEATURES].apply(pd.to_numeric, errors="coerce").values.astype(float)

def make_rf():
    return Pipeline([
        ("imp", SimpleImputer(strategy="median")),
        ("m",   RandomForestRegressor(n_estimators=500, max_depth=4,
                                       min_samples_leaf=4, random_state=42))
    ])

def cv_run(X, y, w, splits, label):
    y_pred = np.full_like(y, np.nan, dtype=float)
    for tr, te in splits:
        m = make_rf()
        try: m.fit(X[tr], y[tr], m__sample_weight=w[tr])
        except (TypeError, ValueError): m.fit(X[tr], y[tr])
        y_pred[te] = m.predict(X[te])
    mask = ~np.isnan(y_pred)
    rmse = math.sqrt(mean_squared_error(y[mask], y_pred[mask]))
    r2 = r2_score(y[mask], y_pred[mask])
    # Calibration
    o = y[mask] / 100.0; pr = y_pred[mask] / 100.0
    slope = (((pr - pr.mean()) * (o - o.mean())).sum()
             / ((pr - pr.mean())**2).sum())
    intercept = o.mean() - slope * pr.mean()
    print(f"  {label}: RMSE={rmse:.2f}%, R²={r2:+.3f}, cal slope={slope:.3f}")
    return rmse, r2, slope, intercept, y_pred

loo_splits  = list(LeaveOneOut().split(X_sel))
loso_splits = list(LeaveOneGroupOut().split(X_sel, groups=g))
rmse_loo, r2_loo, slope_loo, _, ypred_loo   = cv_run(X_sel, y, w, loo_splits,  "LOO-arm")
rmse_loso, r2_loso, slope_loso, _, ypred_loso = cv_run(X_sel, y, w, loso_splits, "LOSO-study")

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  Step 3: Fit final model on full data                                      ║
# ╚════════════════════════════════════════════════════════════════════════════╝
print("\n── Step 3: Fit final RF on full data (for deployment) ──")
final_rf = make_rf()
final_rf.fit(X_sel, y, m__sample_weight=w)
y_pred_full = final_rf.predict(X_sel)
print(f"  In-sample RMSE = {math.sqrt(mean_squared_error(y, y_pred_full)):.2f}%")

# Save
with open(f"{MDL}/final_predictive_rfe_rf.pkl", "wb") as f:
    pickle.dump({"model": final_rf, "features": SELECTED_FEATURES}, f)
np.save(f"{MDL}/final_predictive_loso_ypred.npy", ypred_loso)
np.save(f"{MDL}/final_predictive_features.npy", np.array(SELECTED_FEATURES))
print(f"  ✓ Saved final_predictive_rfe_rf.pkl")

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  Step 4: SHAP attributions on the reduced model                            ║
# ╚════════════════════════════════════════════════════════════════════════════╝
print("\n── Step 4: SHAP attributions ──")
X_sel_imp = SimpleImputer(strategy="median").fit_transform(X_sel)
explainer = shap.TreeExplainer(final_rf.named_steps["m"])
shap_vals = explainer.shap_values(X_sel_imp)
mean_abs = np.abs(shap_vals).mean(axis=0)
direction = np.array([(shap_vals[:, i] * (X_sel_imp[:, i] - X_sel_imp[:, i].mean())).mean()
                       for i in range(len(SELECTED_FEATURES))])
print(f"\n  Mean |SHAP|  ── direction ──  feature")
ranked = sorted(zip(SELECTED_FEATURES, mean_abs, direction), key=lambda x: -x[1])
for f, m_abs, d in ranked:
    arrow = "↑" if d > 0 else "↓"
    print(f"    {m_abs:>6.2f}     {arrow}     {f}")

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  Step 5: Comparison figure — final predictive vs baselines vs Bayesian    ║
# ╚════════════════════════════════════════════════════════════════════════════╝
comparison = {
    "Final predictive\n(RFE-10 + RF)": {
        "n_feat": 10, "loo_r2": r2_loo, "loso_r2": r2_loso,
        "loso_rmse": rmse_loso, "cal_slope_loso": slope_loso,
    }
}
# Add comparison from prior runs
try:
    # Baseline: all features + RF (from 07e or estimated from 07_model_building log)
    comparison["All-39 features\n(RF baseline)"] = {
        "n_feat": 39, "loo_r2": 0.203, "loso_r2": 0.015,
        "loso_rmse": 10.25, "cal_slope_loso": None,
    }
except: pass
try:
    bayes_marg = np.load(f"{MDL}/bayes_marginal_ypred.npy") * 100
    if len(bayes_marg) == len(y):
        rmse_b = math.sqrt(((y - bayes_marg)**2).mean())
        r2_b = r2_score(y, bayes_marg)
        o = y/100; pr = bayes_marg/100
        slope_b = (((pr - pr.mean()) * (o - o.mean())).sum()
                   / ((pr - pr.mean())**2).sum())
        comparison["Bayesian hierarchical\n(marginal, 15 features)"] = {
            "n_feat": 15, "loo_r2": np.nan, "loso_r2": r2_b,
            "loso_rmse": rmse_b, "cal_slope_loso": slope_b,
        }
except FileNotFoundError: pass

# Bar chart of LOSO R²
fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
ax = axes[0]
names = list(comparison.keys())
losos = [comparison[n]["loso_r2"] for n in names]
n_feats = [comparison[n]["n_feat"] for n in names]
colors = ["#388E3C", "#9E9E9E", "#5E35B1"][:len(names)]
ax.barh(range(len(names)), losos, color=colors, alpha=0.85)
ax.axvline(0, color="black", linewidth=1)
ax.set_yticks(range(len(names))); ax.set_yticklabels(names, fontsize=10)
ax.set_xlabel("LOSO R² (honest generalisation)", fontsize=11)
ax.set_title("Predictive model comparison\n(higher = better generalisation)",
             fontweight="bold")
ax.invert_yaxis(); ax.grid(axis="x", alpha=0.3)
for i, (lr, nf) in enumerate(zip(losos, n_feats)):
    ax.text(lr + 0.005, i, f"{lr:+.3f} ({nf} feat)", va="center", fontsize=9)

# Predicted vs observed for the final model (LOSO)
ax = axes[1]
ax.scatter(y, ypred_loso, color="#388E3C", s=50, alpha=0.7, edgecolors="white")
lims = [min(min(y), min(ypred_loso))-2, max(max(y), max(ypred_loso))+2]
ax.plot(lims, lims, "k--", linewidth=1.2, label="Perfect")
ax.fill_between(lims, [l-5 for l in lims], [l+5 for l in lims],
                color="green", alpha=0.1, label="±5%")
ax.set_xlabel("Actual ITT (%)", fontsize=11)
ax.set_ylabel("Predicted ITT (%, LOSO)", fontsize=11)
ax.set_title(f"Final predictive model — LOSO predictions\n"
             f"RMSE={rmse_loso:.2f}%, R²={r2_loso:+.3f}, slope={slope_loso:.3f}",
             fontweight="bold")
ax.legend(fontsize=9); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(f"{FIG}/final_predictive_comparison.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"\n✓ {FIG}/final_predictive_comparison.png")

# SHAP summary plot on reduced model
fig, ax = plt.subplots(figsize=(9, 6))
shap.summary_plot(shap_vals, X_sel_imp, feature_names=SELECTED_FEATURES,
                  show=False, plot_size=None, max_display=10)
plt.title("SHAP — Final predictive model (RFE top-10 + RandomForest)",
          fontweight="bold")
plt.tight_layout()
plt.savefig(f"{FIG}/final_predictive_shap.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"✓ {FIG}/final_predictive_shap.png")

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  Step 6: Write report                                                      ║
# ╚════════════════════════════════════════════════════════════════════════════╝
with open(f"{RPT}/final_predictive_results.txt", "w", encoding="utf-8") as f:
    f.write("Final Predictive Model — RFE top-10 + RandomForest\n")
    f.write("="*70 + "\n\n")
    f.write(f"Dataset: {len(df)} arms, {len(set(g))} studies\n")
    f.write(f"Target: ITT_Rate (%) · Weights: N_ITT\n\n")
    f.write("── Selected features (RFE, Ridge-based, K=10) ──\n")
    for i, fn in enumerate(SELECTED_FEATURES, 1):
        f.write(f"  {i:>2}. {fn}\n")
    f.write(f"\n── Cross-validated performance ──\n")
    f.write(f"  LOO-arm:    RMSE={rmse_loo:.2f}%, R²={r2_loo:+.3f}, slope={slope_loo:.3f}\n")
    f.write(f"  LOSO-study: RMSE={rmse_loso:.2f}%, R²={r2_loso:+.3f}, slope={slope_loso:.3f}\n\n")
    f.write("── SHAP attributions (mean |SHAP|) ──\n")
    for fn, m_abs, d in ranked:
        arrow = "↑" if d > 0 else "↓"
        f.write(f"  {m_abs:>6.2f}  {arrow}  {fn}\n")
    f.write(f"\n── Comparison with baseline + Bayesian ──\n")
    f.write(f"{'Model':<40} {'n_feat':>8} {'LOSO R²':>9} {'LOSO RMSE':>11}\n")
    for n, r in comparison.items():
        n_short = n.replace("\n", " ")
        f.write(f"  {n_short:<38} {r['n_feat']:>8} {r['loso_r2']:>+9.3f} {r['loso_rmse']:>11.2f}\n")

print(f"\n✓ {RPT}/final_predictive_results.txt")
print("\n✓ Final predictive model script complete.")
