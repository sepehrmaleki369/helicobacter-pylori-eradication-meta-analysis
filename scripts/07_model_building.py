"""
Phase 5+6 — Tier 1 (improved):
- Sample-size weighting (N_ITT)
- Proper NaN handling + SimpleImputer
- ElasticNet (best for n≈100 with correlated features)
- Dual CV: LOO-arm + Leave-One-Study-Out (LOSO)
- Two model families: with Compliance (prediction) vs without (treatment-effect)
- Outputs: project/models/* + project/figures/model_*.png + console summary
"""
import csv, math, os, pickle, warnings
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")

from sklearn.linear_model import Ridge, Lasso, LogisticRegression, ElasticNetCV
from sklearn.ensemble import (RandomForestRegressor, RandomForestClassifier,
                              GradientBoostingRegressor, GradientBoostingClassifier,
                              StackingRegressor, StackingClassifier)
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import (KFold, StratifiedKFold, LeaveOneOut,
                                     LeaveOneGroupOut, RepeatedStratifiedKFold,
                                     cross_val_predict, cross_val_score)
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import (mean_squared_error, mean_absolute_error, r2_score,
                             roc_auc_score, f1_score, accuracy_score, brier_score_loss)

IN      = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/data/processed/clean_dataset.csv"
FIG     = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/figures"
MDL_DIR = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/models"
os.makedirs(FIG, exist_ok=True)
os.makedirs(MDL_DIR, exist_ok=True)

with open(IN, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

def flt(v):
    try: return float(v) if v not in (None, "", "None") else None
    except: return None

# ── Two feature sets ──────────────────────────────────────────────────────────
FEATURES_PRETREAT = [
    # Pre-randomisation only — for causal/treatment-effect inference
    "Is_Dual", "Is_Triple", "Is_Quadruple", "Has_Bismuth",
    "Is_Vonoprazan", "Is_Tegoprazan", "Is_Standard_PPI", "Is_PCAB",
    "Has_Clarithromycin", "Has_Metronidazole",
    "Is_Tetracycline_Dual", "Is_Minocycline_Dual", "Is_Furazolidone_Quad",
    # Round 2 Tier A: quadruple sub-types
    "Is_Concomitant", "Is_Sequential", "Is_Hybrid", "Is_Bismuth_Quad",
    # Dosing (Round 2 Tier A3)
    "PPI_Daily_mg", "Amox_Daily_mg", "Amox_Daily_missing",
    "Duration_Days",
    "CLR_Resistance_pct", "MTZ_Resistance_pct", "AMX_Resistance_pct", "LFX_Resistance_pct",
    "CLR_use_x_CLR_resistance",
    "Is_High_CLR_Region", "Is_High_AMX_Region",
    "Is_East_Asia", "Is_Western", "Is_South_Asia_ME", "Is_Latin_America", "Is_Southeast_Asia",
    "Mean_Age_yr", "Mean_Age_missing",
    "Is_Susceptibility_Guided",
    # Round 2 Tier A4: study-level
    "Is_Multicenter", "Study_Era", "Study_Era_missing",
]
FEATURES_FULL = FEATURES_PRETREAT + ["Compliance_pct", "Compliance_missing"]

# ── Build matrices (keep NaN; track weights and study groups) ─────────────────
def build_matrix(rows, feature_cols, target_col):
    X, y, w, groups = [], [], [], []
    for r in rows:
        t = flt(r.get(target_col)); n = flt(r.get("N_ITT"))
        if t is None or n is None: continue
        X.append([flt(r.get(c)) if flt(r.get(c)) is not None else np.nan
                  for c in feature_cols])
        y.append(t); w.append(n); groups.append(int(r["Ref"]))
    return (np.array(X, dtype=float), np.array(y, dtype=float),
            np.array(w, dtype=float), np.array(groups, dtype=int))

# ── Pipeline factory ──────────────────────────────────────────────────────────
def pipe(model, scale=True):
    steps = [("imp", SimpleImputer(strategy="median"))]
    if scale:
        steps.append(("sc", StandardScaler()))
    steps.append(("m", model))
    return Pipeline(steps)

# ── Hand-rolled weighted LOO/LOSO regression evaluator ────────────────────────
def cv_regression(model_factory, X, y, w, splitter, sample_weight=True):
    """Returns (rmse, mae, r2, y_pred). Hand-rolled to safely pass sample_weight."""
    y_pred = np.full_like(y, np.nan, dtype=float)
    for train_idx, test_idx in splitter:
        m = model_factory()
        if sample_weight:
            try:
                m.fit(X[train_idx], y[train_idx], m__sample_weight=w[train_idx])
            except (TypeError, ValueError):
                m.fit(X[train_idx], y[train_idx])
        else:
            m.fit(X[train_idx], y[train_idx])
        y_pred[test_idx] = m.predict(X[test_idx])
    mask = ~np.isnan(y_pred)
    rmse = math.sqrt(mean_squared_error(y[mask], y_pred[mask]))
    mae  = mean_absolute_error(y[mask], y_pred[mask])
    r2   = r2_score(y[mask], y_pred[mask])
    return rmse, mae, r2, y_pred

def cv_classification(model_factory, X, y, w, splitter, sample_weight=True):
    """Returns (auc, brier, y_pred_proba). Hand-rolled."""
    y_proba = np.full_like(y, np.nan, dtype=float)
    for train_idx, test_idx in splitter:
        m = model_factory()
        if sample_weight:
            try:
                m.fit(X[train_idx], y[train_idx], m__sample_weight=w[train_idx])
            except (TypeError, ValueError):
                m.fit(X[train_idx], y[train_idx])
        else:
            m.fit(X[train_idx], y[train_idx])
        y_proba[test_idx] = m.predict_proba(X[test_idx])[:, 1]
    mask = ~np.isnan(y_proba)
    auc = roc_auc_score(y[mask], y_proba[mask])
    brier = brier_score_loss(y[mask], y_proba[mask])
    return auc, brier, y_proba

# ── Splits helpers ────────────────────────────────────────────────────────────
def splits_loo(X):
    return list(LeaveOneOut().split(X))

def splits_loso(X, groups):
    return list(LeaveOneGroupOut().split(X, groups=groups))

def splits_rep_strat(X, y, n_splits=5, n_repeats=10, seed=42):
    return list(RepeatedStratifiedKFold(n_splits=n_splits, n_repeats=n_repeats,
                                         random_state=seed).split(X, y))

# ── Model factories ────────────────────────────────────────────────────────────
def make_reg_models():
    def _stacking():
        est = [
            ("en",  ElasticNetCV(l1_ratio=[0.3,0.5,0.7,1.0],
                                  alphas=np.logspace(-3,1,15),
                                  cv=5, max_iter=10000, random_state=42)),
            ("rf",  RandomForestRegressor(n_estimators=300, max_depth=4,
                                           min_samples_leaf=4, random_state=42)),
            ("gbm", GradientBoostingRegressor(n_estimators=200, max_depth=3,
                                              learning_rate=0.05, subsample=0.8,
                                              random_state=42)),
        ]
        return StackingRegressor(estimators=est,
                                 final_estimator=Ridge(alpha=1.0), cv=5,
                                 passthrough=False)
    return {
        "Ridge":         lambda: pipe(Ridge(alpha=1.0)),
        "Lasso":         lambda: pipe(Lasso(alpha=0.5, max_iter=10000)),
        "ElasticNet":    lambda: pipe(ElasticNetCV(
                                l1_ratio=[0.1, 0.3, 0.5, 0.7, 0.9, 1.0],
                                alphas=np.logspace(-3, 1, 30),
                                cv=5, max_iter=20000, random_state=42)),
        "RandomForest":  lambda: pipe(RandomForestRegressor(
                                n_estimators=500, max_depth=4, min_samples_leaf=4,
                                random_state=42), scale=False),
        "GradientBoost": lambda: pipe(GradientBoostingRegressor(
                                n_estimators=300, max_depth=3, learning_rate=0.05,
                                subsample=0.8, min_samples_leaf=4, random_state=42), scale=False),
        "Stacking":      lambda: pipe(_stacking(), scale=False),
    }

def make_clf_models():
    def _stack_clf():
        est = [
            ("lr",  LogisticRegression(C=0.5, max_iter=2000, random_state=42)),
            ("rf",  RandomForestClassifier(n_estimators=300, max_depth=4,
                                            min_samples_leaf=4,
                                            class_weight="balanced", random_state=42)),
            ("gbm", GradientBoostingClassifier(n_estimators=200, max_depth=3,
                                                learning_rate=0.05, subsample=0.8,
                                                random_state=42)),
        ]
        return StackingClassifier(estimators=est,
                                  final_estimator=LogisticRegression(C=1.0, max_iter=1000),
                                  cv=5, passthrough=False)
    def _cal_gbm():
        return CalibratedClassifierCV(
            GradientBoostingClassifier(n_estimators=200, max_depth=3,
                                        learning_rate=0.05, subsample=0.8,
                                        random_state=42),
            method="isotonic", cv=5)
    return {
        "LogReg":        lambda: pipe(LogisticRegression(
                                C=0.5, max_iter=2000, random_state=42)),
        "ElasticNet-LR": lambda: pipe(LogisticRegression(
                                penalty="elasticnet", solver="saga",
                                C=0.5, l1_ratio=0.5,
                                max_iter=5000, random_state=42)),
        "RandomForest":  lambda: pipe(RandomForestClassifier(
                                n_estimators=500, max_depth=4, min_samples_leaf=4,
                                class_weight="balanced", random_state=42), scale=False),
        "GradientBoost": lambda: pipe(GradientBoostingClassifier(
                                n_estimators=200, max_depth=3, learning_rate=0.05,
                                subsample=0.8, min_samples_leaf=4, random_state=42), scale=False),
        "Stacking":      lambda: pipe(_stack_clf(), scale=False),
        "Calibrated-GBM":lambda: pipe(_cal_gbm(), scale=False),
    }

# ╔═════════════════════════════════════════════════════════════════════════════╗
# ║  RUN: Two feature families × Regression + Classification × LOO + LOSO       ║
# ╚═════════════════════════════════════════════════════════════════════════════╝

results = {}   # results[family][task][model][cv_scheme] = {...}

for fam_name, feature_cols in [("pretreat", FEATURES_PRETREAT), ("full", FEATURES_FULL)]:
    print("\n" + "═"*78)
    print(f"FAMILY: {fam_name.upper()}  ({len(feature_cols)} features)")
    print("═"*78)

    X_reg, y_reg, w_reg, g_reg = build_matrix(rows, feature_cols, "ITT_Rate")
    X_85,  y_85,  w_85,  g_85  = build_matrix(rows, feature_cols, "Success_ITT_85")
    X_90,  y_90,  w_90,  g_90  = build_matrix(rows, feature_cols, "Success_ITT_90")
    print(f"  n_regression={len(y_reg)}, n_class85_pos={int(y_85.sum())}/{len(y_85)}, "
          f"n_class90_pos={int(y_90.sum())}/{len(y_90)}, n_unique_studies={len(set(g_reg))}")

    # ── Regression ─────────────────────────────────────────────────────────────
    print(f"\n  REGRESSION  ITT_Rate (%)   [weighted by N_ITT]")
    print(f"  {'Model':<14} {'LOO-arm':>22}   {'LOSO-study':>22}")
    print(f"  {'':14} {'RMSE   MAE    R²':>22}   {'RMSE   MAE    R²':>22}")
    print(f"  {'-'*14} {'-'*22}   {'-'*22}")
    family_reg = {}
    # Skip Stacking in CV (too slow) — fit once on full data at the end
    SLOW_MODELS = {"Stacking", "Calibrated-GBM"}
    for name, factory in make_reg_models().items():
        if name in SLOW_MODELS:
            continue
        rmse_l, mae_l, r2_l, ypred_l = cv_regression(factory, X_reg, y_reg, w_reg, splits_loo(X_reg))
        rmse_s, mae_s, r2_s, ypred_s = cv_regression(factory, X_reg, y_reg, w_reg, splits_loso(X_reg, g_reg))
        family_reg[name] = {"loo": {"rmse": rmse_l, "mae": mae_l, "r2": r2_l, "ypred": ypred_l},
                            "loso":{"rmse": rmse_s, "mae": mae_s, "r2": r2_s, "ypred": ypred_s}}
        print(f"  {name:<14} {rmse_l:5.2f} {mae_l:5.2f} {r2_l:6.3f}     {rmse_s:5.2f} {mae_s:5.2f} {r2_s:6.3f}")
    # Stacking moved to 07f (extended models comparison). Skip here for speed.
    results.setdefault(fam_name, {})["regression"] = family_reg

    # ── Classification ≥85% ────────────────────────────────────────────────────
    print(f"\n  CLASSIFICATION  ITT ≥ 85%   [weighted by N_ITT]")
    print(f"  {'Model':<14} {'LOO-arm/Rep':>22}   {'LOSO-study':>22}")
    print(f"  {'':14} {'AUC      Brier':>22}   {'AUC      Brier':>22}")
    print(f"  {'-'*14} {'-'*22}   {'-'*22}")
    family_clf85 = {}
    for name, factory in make_clf_models().items():
        if name in SLOW_MODELS:
            continue
        # Repeated stratified k-fold (LOO equivalent for classification)
        auc_l, brier_l, _ = cv_classification(factory, X_85, y_85, w_85, splits_rep_strat(X_85, y_85))
        auc_s, brier_s, _ = cv_classification(factory, X_85, y_85, w_85, splits_loso(X_85, g_85))
        family_clf85[name] = {"rep": {"auc": auc_l, "brier": brier_l},
                              "loso":{"auc": auc_s, "brier": brier_s}}
        print(f"  {name:<14} {auc_l:6.3f}  {brier_l:6.4f}        {auc_s:6.3f}  {brier_s:6.4f}")
    # Stacking/Calibrated-GBM moved to 07f. Skip here for speed.
    results[fam_name]["clf85"] = family_clf85

    # ── Classification ≥90% ────────────────────────────────────────────────────
    print(f"\n  CLASSIFICATION  ITT ≥ 90%   [weighted by N_ITT]")
    print(f"  {'Model':<14} {'LOO-arm/Rep':>22}   {'LOSO-study':>22}")
    print(f"  {'':14} {'AUC      Brier':>22}   {'AUC      Brier':>22}")
    print(f"  {'-'*14} {'-'*22}   {'-'*22}")
    family_clf90 = {}
    for name, factory in make_clf_models().items():
        if name in SLOW_MODELS:
            continue
        auc_l, brier_l, _ = cv_classification(factory, X_90, y_90, w_90, splits_rep_strat(X_90, y_90))
        auc_s, brier_s, _ = cv_classification(factory, X_90, y_90, w_90, splits_loso(X_90, g_90))
        family_clf90[name] = {"rep": {"auc": auc_l, "brier": brier_l},
                              "loso":{"auc": auc_s, "brier": brier_s}}
        print(f"  {name:<14} {auc_l:6.3f}  {brier_l:6.4f}        {auc_s:6.3f}  {brier_s:6.4f}")
    results[fam_name]["clf90"] = family_clf90

    # ── Persist fitted "full-data" models for downstream (SHAP) ────────────────
    # Skip Stacking/Calibrated here too — they're already fit in their LOSO CV folds
    for name, factory in make_reg_models().items():
        if name in SLOW_MODELS: continue
        m = factory()
        try: m.fit(X_reg, y_reg, m__sample_weight=w_reg)
        except (TypeError, ValueError): m.fit(X_reg, y_reg)
        with open(f"{MDL_DIR}/reg_{fam_name}_{name.lower()}.pkl", "wb") as f:
            pickle.dump(m, f)
    for name, factory in make_clf_models().items():
        if name in SLOW_MODELS: continue
        m = factory()
        try: m.fit(X_85, y_85, m__sample_weight=w_85)
        except (TypeError, ValueError): m.fit(X_85, y_85)
        with open(f"{MDL_DIR}/clf85_{fam_name}_{name.lower()}.pkl", "wb") as f:
            pickle.dump(m, f)

    # Save data arrays for downstream
    np.save(f"{MDL_DIR}/X_reg_{fam_name}.npy", X_reg)
    np.save(f"{MDL_DIR}/y_reg_{fam_name}.npy", y_reg)
    np.save(f"{MDL_DIR}/w_reg_{fam_name}.npy", w_reg)
    np.save(f"{MDL_DIR}/g_reg_{fam_name}.npy", g_reg)
    np.save(f"{MDL_DIR}/X_85_{fam_name}.npy",  X_85)
    np.save(f"{MDL_DIR}/y_85_{fam_name}.npy",  y_85)
    with open(f"{MDL_DIR}/feature_names_{fam_name}.pkl", "wb") as f:
        pickle.dump(feature_cols, f)

# ╔═════════════════════════════════════════════════════════════════════════════╗
# ║  FIGURES                                                                    ║
# ╚═════════════════════════════════════════════════════════════════════════════╝

# Bar chart comparing families × CV scheme on best regression and classification
fig, axes = plt.subplots(2, 2, figsize=(13, 9))

# Regression — RMSE comparison
ax = axes[0,0]
models_r = ["Ridge", "Lasso", "ElasticNet", "RandomForest", "GradientBoost"]
x = np.arange(len(models_r))
w = 0.2
for i, (fam, cv_scheme) in enumerate([("pretreat","loo"), ("pretreat","loso"),
                                       ("full","loo"), ("full","loso")]):
    vals = [results[fam]["regression"][m][cv_scheme]["rmse"] for m in models_r]
    label = f"{fam}/{cv_scheme}"
    ax.bar(x + (i-1.5)*w, vals, w, label=label, alpha=0.85)
ax.set_xticks(x); ax.set_xticklabels(models_r, rotation=20, fontsize=9)
ax.set_ylabel("RMSE (%)"); ax.set_title("Regression RMSE — lower is better", fontweight="bold")
ax.legend(fontsize=8); ax.grid(axis="y", alpha=0.3)

# Regression — R² comparison
ax = axes[0,1]
for i, (fam, cv_scheme) in enumerate([("pretreat","loo"), ("pretreat","loso"),
                                       ("full","loo"), ("full","loso")]):
    vals = [results[fam]["regression"][m][cv_scheme]["r2"] for m in models_r]
    ax.bar(x + (i-1.5)*w, vals, w, label=f"{fam}/{cv_scheme}", alpha=0.85)
ax.axhline(0, color="black", linewidth=1.0)
ax.set_xticks(x); ax.set_xticklabels(models_r, rotation=20, fontsize=9)
ax.set_ylabel("R²"); ax.set_title("Regression R² — higher is better", fontweight="bold")
ax.legend(fontsize=8); ax.grid(axis="y", alpha=0.3)

# Classification ≥85% AUC
ax = axes[1,0]
models_c = ["LogReg", "ElasticNet-LR", "RandomForest", "GradientBoost"]
x = np.arange(len(models_c))
for i, (fam, cv_scheme) in enumerate([("pretreat","rep"), ("pretreat","loso"),
                                       ("full","rep"), ("full","loso")]):
    vals = [results[fam]["clf85"][m][cv_scheme]["auc"] for m in models_c]
    ax.bar(x + (i-1.5)*w, vals, w, label=f"{fam}/{cv_scheme}", alpha=0.85)
ax.axhline(0.5, color="gray", linestyle="--", linewidth=0.8)
ax.set_xticks(x); ax.set_xticklabels(models_c, rotation=20, fontsize=9)
ax.set_ylabel("ROC-AUC"); ax.set_ylim(0.45, 1.0)
ax.set_title("Classification AUC (ITT ≥85%)", fontweight="bold")
ax.legend(fontsize=8); ax.grid(axis="y", alpha=0.3)

# Classification ≥90% AUC
ax = axes[1,1]
for i, (fam, cv_scheme) in enumerate([("pretreat","rep"), ("pretreat","loso"),
                                       ("full","rep"), ("full","loso")]):
    vals = [results[fam]["clf90"][m][cv_scheme]["auc"] for m in models_c]
    ax.bar(x + (i-1.5)*w, vals, w, label=f"{fam}/{cv_scheme}", alpha=0.85)
ax.axhline(0.5, color="gray", linestyle="--", linewidth=0.8)
ax.set_xticks(x); ax.set_xticklabels(models_c, rotation=20, fontsize=9)
ax.set_ylabel("ROC-AUC"); ax.set_ylim(0.45, 1.0)
ax.set_title("Classification AUC (ITT ≥90%)", fontweight="bold")
ax.legend(fontsize=8); ax.grid(axis="y", alpha=0.3)

plt.suptitle("Tier 1 model performance — two feature families × LOO-arm + LOSO CV",
             fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(f"{FIG}/model_cv_comparison.png", dpi=150, bbox_inches="tight")
plt.close()
print("\n✓ model_cv_comparison.png")

# Actual vs predicted (best regression model: ElasticNet on full family, LOSO)
best_pred = results["full"]["regression"]["ElasticNet"]["loso"]["ypred"]
X_reg, y_reg, w_reg, g_reg = build_matrix(rows, FEATURES_FULL, "ITT_Rate")
fig, axes = plt.subplots(1, 2, figsize=(11, 5))
ax = axes[0]
ax.scatter(y_reg, best_pred, color="#2196F3", s=50, alpha=0.7, edgecolors="white")
lims = [min(y_reg)-2, max(y_reg)+2]
ax.plot(lims, lims, "k--", linewidth=1.2)
ax.fill_between(lims, [l-5 for l in lims], [l+5 for l in lims], alpha=0.1, color="blue", label="±5%")
ax.set_xlabel("Actual ITT Rate (%)"); ax.set_ylabel("Predicted (ElasticNet, LOSO)")
rmse = results["full"]["regression"]["ElasticNet"]["loso"]["rmse"]
r2   = results["full"]["regression"]["ElasticNet"]["loso"]["r2"]
ax.text(0.05, 0.95, f"RMSE = {rmse:.2f}%\nR² = {r2:.3f}",
        transform=ax.transAxes, va="top", fontsize=10, style="italic")
ax.set_title("ElasticNet (full) — LOSO CV", fontweight="bold")
ax.legend(); ax.grid(alpha=0.2)

# Residuals
ax = axes[1]
resid = y_reg - best_pred
ax.scatter(best_pred, resid, color="#FF9800", s=50, alpha=0.7, edgecolors="white")
ax.axhline(0, color="black", linewidth=1.0)
ax.axhline(5, color="red", linestyle=":", alpha=0.5)
ax.axhline(-5, color="red", linestyle=":", alpha=0.5)
ax.set_xlabel("Predicted ITT (%)"); ax.set_ylabel("Residual")
ax.set_title("Residuals — LOSO", fontweight="bold")
ax.grid(alpha=0.2)
plt.tight_layout()
plt.savefig(f"{FIG}/model_actual_vs_predicted.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ model_actual_vs_predicted.png")

# Save cross-validated predictions for Tier 2 comparison
np.save(f"{MDL_DIR}/elasticnet_full_loso_ypred.npy", best_pred)
np.save(f"{MDL_DIR}/elasticnet_full_loo_ypred.npy",
        results["full"]["regression"]["ElasticNet"]["loo"]["ypred"])
np.save(f"{MDL_DIR}/elasticnet_pretreat_loso_ypred.npy",
        results["pretreat"]["regression"]["ElasticNet"]["loso"]["ypred"])

# ── Summary table ────────────────────────────────────────────────────────────
print("\n" + "═"*78)
print("TIER 1 SUMMARY  (best per family × CV-scheme)")
print("═"*78)
print(f"{'Family / CV':<22} {'RMSE':>7} {'MAE':>7} {'R²':>7}   {'AUC≥85':>7} {'AUC≥90':>7}")
print("-"*78)
for fam in ["pretreat", "full"]:
    for cv in ["loo", "loso"]:
        regs = results[fam]["regression"]
        best_reg = min(regs.items(), key=lambda kv: kv[1][cv]["rmse"])
        cv_clf = "rep" if cv == "loo" else "loso"
        cl85 = results[fam]["clf85"]; cl90 = results[fam]["clf90"]
        best_85 = max(cl85.items(), key=lambda kv: kv[1][cv_clf]["auc"])
        best_90 = max(cl90.items(), key=lambda kv: kv[1][cv_clf]["auc"])
        print(f"  {fam:<8} / {cv:<8}  {best_reg[1][cv]['rmse']:>5.2f}  {best_reg[1][cv]['mae']:>5.2f}"
              f"  {best_reg[1][cv]['r2']:>6.3f}    {best_85[1][cv_clf]['auc']:>5.3f}   {best_90[1][cv_clf]['auc']:>5.3f}")
        print(f"             best:  {best_reg[0]:<14}                {best_85[0]:<14} {best_90[0]:<14}")

print(f"\n✓ Phase 5+6 complete (Tier 1).")
