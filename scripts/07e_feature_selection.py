"""
Feature selection comparison — does reducing features improve generalization?

Methods compared:
  1. All features (39, baseline = current Tier 1 pretreat)
  2. SHAP top-K with K=8, 12, 18
  3. Lasso non-zero coefficients (auto feature selection)
  4. Recursive Feature Elimination (RFE) with K=10

For each feature set:
  - Refit ElasticNet, RandomForest, GradientBoost
  - Evaluate LOO + LOSO regression
  - Compare to baseline full-feature model

Outputs:
  - figures/feature_selection_comparison.png
  - report/feature_selection_results.txt
"""
import csv, math, os, pickle, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")

import shap
from sklearn.linear_model import Ridge, Lasso, ElasticNetCV
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.feature_selection import RFE
from sklearn.model_selection import LeaveOneOut, LeaveOneGroupOut
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_squared_error, r2_score

IN  = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/data/processed/clean_dataset.csv"
MDL = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/models"
FIG = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/figures"
RPT = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/report"

with open(f"{MDL}/feature_names_pretreat.pkl", "rb") as f:
    ALL_FEATURES = pickle.load(f)

df = pd.read_csv(IN).dropna(subset=["ITT_Rate","N_ITT"]).reset_index(drop=True)
print(f"Dataset: {len(df)} arms, {df['Ref'].nunique()} studies")
print(f"All features ({len(ALL_FEATURES)}): {ALL_FEATURES}\n")

def build_xy(feats):
    X = df[feats].apply(pd.to_numeric, errors="coerce").values.astype(float)
    y = df["ITT_Rate"].values.astype(float)
    w = df["N_ITT"].values.astype(float)
    g = df["Ref"].astype(int).values
    return X, y, w, g

def pipe_reg(model, scale=True):
    steps = [("imp", SimpleImputer(strategy="median"))]
    if scale: steps.append(("sc", StandardScaler()))
    steps.append(("m", model))
    return Pipeline(steps)

def cv_regression(model_factory, X, y, w, splits):
    y_pred = np.full_like(y, np.nan, dtype=float)
    for tr, te in splits:
        m = model_factory()
        try: m.fit(X[tr], y[tr], m__sample_weight=w[tr])
        except (TypeError, ValueError): m.fit(X[tr], y[tr])
        y_pred[te] = m.predict(X[te])
    mask = ~np.isnan(y_pred)
    rmse = math.sqrt(mean_squared_error(y[mask], y_pred[mask]))
    r2 = r2_score(y[mask], y_pred[mask])
    return rmse, r2

def make_models():
    return {
        "ElasticNet":    lambda: pipe_reg(ElasticNetCV(
                            l1_ratio=[0.3,0.5,0.7,0.9,1.0],
                            alphas=np.logspace(-3,1,20),
                            cv=5, max_iter=10000, random_state=42)),
        "RandomForest":  lambda: pipe_reg(RandomForestRegressor(
                            n_estimators=300, max_depth=4, min_samples_leaf=4,
                            random_state=42), scale=False),
        "GradientBoost": lambda: pipe_reg(GradientBoostingRegressor(
                            n_estimators=200, max_depth=3, learning_rate=0.05,
                            subsample=0.8, min_samples_leaf=4, random_state=42),
                            scale=False),
    }

# ── Compute SHAP ranking on the saved GBM ─────────────────────────────────────
print("── Computing SHAP rankings on saved GBM (pretreat) ──")
with open(f"{MDL}/reg_pretreat_gradientboost.pkl", "rb") as f:
    gb = pickle.load(f)
X_all = df[ALL_FEATURES].apply(pd.to_numeric, errors="coerce").values.astype(float)
X_imp = SimpleImputer(strategy="median").fit_transform(X_all)
explainer = shap.TreeExplainer(gb.named_steps["m"])
shap_vals = explainer.shap_values(X_imp)
mean_abs = np.abs(shap_vals).mean(axis=0)
shap_rank = sorted(enumerate(mean_abs), key=lambda x: -x[1])
print("Top 18 features by mean |SHAP|:")
for i, (idx, val) in enumerate(shap_rank[:18]):
    print(f"  {i+1:>2}. {ALL_FEATURES[idx]:<32} {val:.3f}")

# ── Compute Lasso-selected features ───────────────────────────────────────────
print("\n── Lasso path on full feature set ──")
lasso = Pipeline([("imp", SimpleImputer(strategy="median")),
                  ("sc", StandardScaler()),
                  ("m", Lasso(alpha=0.5, max_iter=20000, random_state=42))])
lasso.fit(X_all, df["ITT_Rate"].values, m__sample_weight=df["N_ITT"].values)
lasso_coefs = lasso.named_steps["m"].coef_
lasso_nonzero = [ALL_FEATURES[i] for i, c in enumerate(lasso_coefs) if abs(c) > 1e-6]
print(f"Lasso retained {len(lasso_nonzero)}/{len(ALL_FEATURES)} features:")
for f in lasso_nonzero: print(f"  {f}")

# ── RFE with K=10 (Ridge as estimator since it handles continuous outcome) ───
print("\n── RFE (Ridge, K=10) ──")
rfe = RFE(Ridge(alpha=1.0), n_features_to_select=10, step=1)
X_for_rfe = SimpleImputer(strategy="median").fit_transform(X_all)
X_for_rfe = StandardScaler().fit_transform(X_for_rfe)
rfe.fit(X_for_rfe, df["ITT_Rate"].values, sample_weight=df["N_ITT"].values)
rfe_selected = [ALL_FEATURES[i] for i, s in enumerate(rfe.support_) if s]
print(f"RFE selected {len(rfe_selected)} features:")
for f in rfe_selected: print(f"  {f}")

# ── Define feature sets to compare ────────────────────────────────────────────
shap_top8  = [ALL_FEATURES[i] for i, _ in shap_rank[:8]]
shap_top12 = [ALL_FEATURES[i] for i, _ in shap_rank[:12]]
shap_top18 = [ALL_FEATURES[i] for i, _ in shap_rank[:18]]

FEATURE_SETS = [
    ("All-39 (baseline)", ALL_FEATURES),
    ("SHAP top-8",       shap_top8),
    ("SHAP top-12",      shap_top12),
    ("SHAP top-18",      shap_top18),
    ("Lasso-retained",   lasso_nonzero),
    ("RFE top-10",       rfe_selected),
]

# ── Evaluate each feature set × each model ───────────────────────────────────
print("\n" + "═"*78)
print("EVALUATION: feature set × model × CV scheme")
print("═"*78)
print(f"{'Feature set':<22} {'Model':<14} {'LOO-RMSE':>10} {'LOO-R²':>8} {'LOSO-RMSE':>11} {'LOSO-R²':>9}")
print("-"*78)

results = {}
for fset_name, fset in FEATURE_SETS:
    X, y, w, g = build_xy(fset)
    loo_splits = list(LeaveOneOut().split(X))
    loso_splits = list(LeaveOneGroupOut().split(X, groups=g))
    for mname, factory in make_models().items():
        rmse_loo, r2_loo = cv_regression(factory, X, y, w, loo_splits)
        rmse_loso, r2_loso = cv_regression(factory, X, y, w, loso_splits)
        results[(fset_name, mname)] = {
            "n_feat": len(fset),
            "loo_rmse": rmse_loo, "loo_r2": r2_loo,
            "loso_rmse": rmse_loso, "loso_r2": r2_loso,
        }
        print(f"  {fset_name:<20} {mname:<14} {rmse_loo:>10.2f} {r2_loo:>+8.3f}"
              f" {rmse_loso:>11.2f} {r2_loso:>+9.3f}")
    print()

# ── Figure: bar chart of LOSO R² ─────────────────────────────────────────────
fset_names = [f[0] for f in FEATURE_SETS]
models = list(make_models().keys())

fig, axes = plt.subplots(1, 2, figsize=(15, 6))
# LOO R²
ax = axes[0]
x = np.arange(len(fset_names))
width = 0.27
colors = ["#2196F3","#FF9800","#4CAF50"]
for i, m in enumerate(models):
    vals = [results[(fs, m)]["loo_r2"] for fs in fset_names]
    ax.bar(x + (i-1)*width, vals, width, label=m, color=colors[i], alpha=0.85)
ax.axhline(0, color="black", linewidth=1)
ax.set_xticks(x); ax.set_xticklabels(fset_names, rotation=25, ha="right", fontsize=9)
ax.set_ylabel("LOO R²", fontsize=11)
ax.set_title("LOO-arm R² by feature set × model", fontweight="bold")
ax.legend(fontsize=9); ax.grid(axis="y", alpha=0.3)

# LOSO R²
ax = axes[1]
for i, m in enumerate(models):
    vals = [results[(fs, m)]["loso_r2"] for fs in fset_names]
    ax.bar(x + (i-1)*width, vals, width, label=m, color=colors[i], alpha=0.85)
ax.axhline(0, color="black", linewidth=1)
ax.set_xticks(x); ax.set_xticklabels(fset_names, rotation=25, ha="right", fontsize=9)
ax.set_ylabel("LOSO-study R²", fontsize=11)
ax.set_title("LOSO R² by feature set × model (honest generalization)",
             fontweight="bold")
ax.legend(fontsize=9); ax.grid(axis="y", alpha=0.3)

plt.suptitle("Feature selection comparison — does reducing features help?",
             fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(f"{FIG}/feature_selection_comparison.png", dpi=150, bbox_inches="tight")
plt.close()
print("\n✓ feature_selection_comparison.png")

# ── Identify best combination ─────────────────────────────────────────────────
print("\n" + "═"*78)
print("BEST FEATURE SET × MODEL combinations")
print("═"*78)
# Sort by LOSO R² (the honest metric)
sorted_results = sorted(results.items(), key=lambda kv: -kv[1]["loso_r2"])
print(f"\n{'Rank':<5} {'Feature set':<22} {'Model':<14} {'LOSO-R²':>9} {'LOO-R²':>8}")
print("-"*65)
for i, ((fs, m), r) in enumerate(sorted_results[:10]):
    print(f"  {i+1:<3} {fs:<22} {m:<14} {r['loso_r2']:>+9.3f} {r['loo_r2']:>+8.3f}")

# ── Write report ──────────────────────────────────────────────────────────────
with open(f"{RPT}/feature_selection_results.txt", "w", encoding="utf-8") as f:
    f.write("Feature selection comparison — Round 2 dataset (142 arms)\n")
    f.write("="*70 + "\n\n")
    f.write("── Feature sets evaluated ──\n")
    for fs_name, fs in FEATURE_SETS:
        f.write(f"  {fs_name:<22} ({len(fs)} features)\n")
    f.write("\n── Full results: feature set × model × CV scheme ──\n")
    f.write(f"{'Feature set':<22} {'Model':<14} {'LOO-RMSE':>10} {'LOO-R²':>8} {'LOSO-RMSE':>11} {'LOSO-R²':>9}\n")
    for (fs, m), r in results.items():
        f.write(f"  {fs:<20} {m:<14} {r['loo_rmse']:>10.2f} {r['loo_r2']:>+8.3f}"
                f" {r['loso_rmse']:>11.2f} {r['loso_r2']:>+9.3f}\n")
    f.write("\n── Top 5 by LOSO R² ──\n")
    for i, ((fs, m), r) in enumerate(sorted_results[:5]):
        f.write(f"  {i+1}. {fs:<22} {m:<14} LOSO R²={r['loso_r2']:.3f}, LOO R²={r['loo_r2']:.3f}\n")
    f.write("\n── SHAP top-18 features ──\n")
    for i, (idx, val) in enumerate(shap_rank[:18]):
        f.write(f"  {i+1:>2}. {ALL_FEATURES[idx]:<32} {val:.3f}\n")
    f.write("\n── Lasso-retained features ──\n")
    for fn in lasso_nonzero: f.write(f"  {fn}\n")
    f.write("\n── RFE top-10 features ──\n")
    for fn in rfe_selected: f.write(f"  {fn}\n")

print(f"\n✓ {RPT}/feature_selection_results.txt")
print("\n✓ Feature selection comparison complete.")
