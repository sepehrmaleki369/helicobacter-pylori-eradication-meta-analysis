"""
Phase 7: Feature importance analysis.
- Permutation importance (model-agnostic)
- SHAP values for Random Forest and Gradient Boosting
- Ridge regression coefficients
- Partial dependence plots for top features
Outputs: project/figures/fi_*.png
"""
import pickle, os, math, warnings
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import shap
warnings.filterwarnings("ignore")

from sklearn.inspection import permutation_importance, PartialDependenceDisplay
from sklearn.model_selection import KFold
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

MDL_DIR = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/models"
FIG     = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/figures"

# ── Load saved artefacts (use "pretreat" family — Round 2 main analysis) ────
FAM = "pretreat"
with open(f"{MDL_DIR}/feature_names_{FAM}.pkl", "rb") as f:
    FEATURES = pickle.load(f)

X_reg = np.load(f"{MDL_DIR}/X_reg_{FAM}.npy")
y_reg = np.load(f"{MDL_DIR}/y_reg_{FAM}.npy")
w_reg = np.load(f"{MDL_DIR}/w_reg_{FAM}.npy")
X_85  = np.load(f"{MDL_DIR}/X_85_{FAM}.npy")
y_85  = np.load(f"{MDL_DIR}/y_85_{FAM}.npy")

# Impute NaN for SHAP/permutation (they need complete matrices)
from sklearn.impute import SimpleImputer
imp = SimpleImputer(strategy="median")
X_reg_imp = imp.fit_transform(X_reg)
X_85_imp  = imp.fit_transform(X_85)

with open(f"{MDL_DIR}/reg_{FAM}_randomforest.pkl",  "rb") as f: rf_reg  = pickle.load(f)
with open(f"{MDL_DIR}/reg_{FAM}_gradientboost.pkl", "rb") as f: gb_reg  = pickle.load(f)
with open(f"{MDL_DIR}/clf85_{FAM}_randomforest.pkl","rb") as f: rf_clf  = pickle.load(f)
# Use imputed matrices going forward
X_reg = X_reg_imp
X_85  = X_85_imp

# Pretty feature names for display
FEAT_LABELS = {
    "Is_Dual": "Dual therapy",
    "Is_Triple": "Triple therapy",
    "Is_Quadruple": "Quadruple therapy",
    "Has_Bismuth": "Contains bismuth",
    "Is_Vonoprazan": "Vonoprazan (P-CAB)",
    "Is_Tegoprazan": "Tegoprazan (P-CAB)",
    "Is_Standard_PPI": "Standard PPI",
    "Is_PCAB": "Any P-CAB",
    "Has_Clarithromycin": "Clarithromycin",
    "Has_Metronidazole": "Metronidazole",
    "Is_Tetracycline_Dual": "Tetracycline dual",
    "Is_Minocycline_Dual": "Minocycline dual",
    "Is_Furazolidone_Quad": "Furazolidone quad",
    "Duration_Days": "Duration (days)",
    "CLR_Resistance_pct": "CLR resistance %",
    "MTZ_Resistance_pct": "MTZ resistance %",
    "AMX_Resistance_pct": "AMX resistance %",
    "LFX_Resistance_pct": "LFX resistance %",
    "CLR_use_x_CLR_resistance": "CLR × CLR-resistance",
    "Is_High_CLR_Region": "High CLR region (≥30%)",
    "Is_High_AMX_Region": "High AMX region (≥10%)",
    "Is_East_Asia": "East Asia",
    "Is_Western": "Western",
    "Is_South_Asia_ME": "South Asia / ME",
    "Is_Latin_America": "Latin America",
    "Is_Southeast_Asia": "Southeast Asia",
    "Mean_Age_yr": "Mean age (yr)",
    "Compliance_pct": "Compliance %",
    "Mean_Age_missing": "Age missing-flag",
    "Compliance_missing": "Compliance missing-flag",
    "Is_Susceptibility_Guided": "Susceptibility-guided",
}
labels = [FEAT_LABELS.get(f, f) for f in FEATURES]


# ══════════════════════════════════════════════════════════════════════════════
# FIG 1: Permutation importance — Gradient Boosting regressor
# ══════════════════════════════════════════════════════════════════════════════
perm = permutation_importance(gb_reg, X_reg, y_reg,
                              n_repeats=100, random_state=42,
                              scoring="neg_mean_squared_error",
                              sample_weight=w_reg)
perm_mean = perm.importances_mean
perm_std  = perm.importances_std

order = np.argsort(perm_mean)[::-1][:18]  # top 18
fig, ax = plt.subplots(figsize=(9, 6.5))
colors = ["#E53935" if perm_mean[i] > 0 else "#90A4AE" for i in order]
ax.barh(range(len(order)),
        [perm_mean[i] for i in order],
        xerr=[perm_std[i] for i in order],
        color=colors[::-1], alpha=0.85, height=0.65,
        error_kw={"elinewidth":1.2, "capsize":3})
ax.set_yticks(range(len(order)))
ax.set_yticklabels([labels[i] for i in order[::-1]], fontsize=10)
ax.axvline(0, color="black", linewidth=0.8)
ax.set_xlabel("Mean decrease in MSE (permutation importance)", fontsize=10)
ax.set_title("Feature Importance — Gradient Boosting Regressor\n(permutation, n=100 repeats)", fontsize=12, fontweight="bold")
ax.grid(axis="x", alpha=0.3)
plt.tight_layout()
plt.savefig(f"{FIG}/fi_permutation_gbr.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ fi_permutation_gbr.png")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 2: RF built-in feature importance (both reg and clf)
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
for ax, model, title, color in [
        (axes[0], rf_reg,  "Random Forest Regressor\n(impurity-based)", "#2196F3"),
        (axes[1], rf_clf,  "Random Forest Classifier (ITT≥85%)\n(impurity-based)", "#E91E63")]:
    # Models are sklearn Pipelines — drill into the final estimator
    feat_imp = model.named_steps["m"].feature_importances_
    order_fi = np.argsort(feat_imp)[::-1][:15]
    vals = [feat_imp[i] for i in order_fi]
    normalized = [v/sum(vals) for v in vals]
    ax.barh(range(len(order_fi)), normalized[::-1], color=color, alpha=0.8, height=0.65)
    ax.set_yticks(range(len(order_fi)))
    ax.set_yticklabels([labels[i] for i in order_fi[::-1]], fontsize=9.5)
    ax.set_xlabel("Normalized importance", fontsize=10)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.grid(axis="x", alpha=0.3)
plt.suptitle("Random Forest Feature Importances", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(f"{FIG}/fi_rf_importance.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ fi_rf_importance.png")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 3: Ridge regression coefficients
# ══════════════════════════════════════════════════════════════════════════════
# Refit ridge with standardized features AND sample weights (matches Tier 1 weighted fit)
sc = StandardScaler()
X_sc = sc.fit_transform(X_reg)
ridge = Ridge(alpha=1.0).fit(X_sc, y_reg, sample_weight=w_reg)
coefs = ridge.coef_

order_c = np.argsort(np.abs(coefs))[::-1][:18]
fig, ax = plt.subplots(figsize=(9, 6.5))
bar_colors = ["#E53935" if coefs[i] > 0 else "#1565C0" for i in order_c]
ax.barh(range(len(order_c)),
        [coefs[i] for i in order_c[::-1]],
        color=bar_colors[::-1], alpha=0.85, height=0.65)
ax.axvline(0, color="black", linewidth=1.0)
ax.set_yticks(range(len(order_c)))
ax.set_yticklabels([labels[i] for i in order_c[::-1]], fontsize=10)
ax.set_xlabel("Standardized coefficient (impact on ITT rate %)", fontsize=10)
ax.set_title("Ridge Regression Coefficients\n(standardized features; red=positive effect on eradication)", fontsize=12, fontweight="bold")
ax.grid(axis="x", alpha=0.3)
plt.tight_layout()
plt.savefig(f"{FIG}/fi_ridge_coefficients.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ fi_ridge_coefficients.png")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 4: SHAP values — Gradient Boosting regressor
# ══════════════════════════════════════════════════════════════════════════════
# gb_reg is a Pipeline — use the underlying tree estimator for SHAP
gb_tree = gb_reg.named_steps["m"]
explainer_gb = shap.TreeExplainer(gb_tree)
shap_vals_gb = explainer_gb.shap_values(X_reg)

# Summary plot (beeswarm style)
fig, ax = plt.subplots(figsize=(9, 7))
shap.summary_plot(shap_vals_gb, X_reg,
                  feature_names=labels,
                  show=False, plot_size=None,
                  max_display=18)
plt.title("SHAP Summary — Gradient Boosting Regressor\n(predicting ITT eradication rate)", fontsize=12, fontweight="bold")
plt.tight_layout()
plt.savefig(f"{FIG}/fi_shap_gbr_summary.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ fi_shap_gbr_summary.png")

# SHAP bar (mean |SHAP|)
fig, ax = plt.subplots(figsize=(9, 6.5))
shap.summary_plot(shap_vals_gb, X_reg,
                  feature_names=labels,
                  plot_type="bar", show=False,
                  max_display=18)
plt.title("SHAP Mean |Value| — Gradient Boosting Regressor", fontsize=12, fontweight="bold")
plt.tight_layout()
plt.savefig(f"{FIG}/fi_shap_gbr_bar.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ fi_shap_gbr_bar.png")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 5: SHAP values — RF classifier (≥85%)
# ══════════════════════════════════════════════════════════════════════════════
rf_tree = rf_clf.named_steps["m"]
explainer_rf = shap.TreeExplainer(rf_tree)
shap_vals_rf = explainer_rf.shap_values(X_85)
# shap_vals_rf is (n, p) for class=1
sv_cls1 = shap_vals_rf[:, :, 1] if shap_vals_rf.ndim == 3 else shap_vals_rf

fig, ax = plt.subplots(figsize=(9, 7))
shap.summary_plot(sv_cls1, X_85,
                  feature_names=labels,
                  show=False, plot_size=None,
                  max_display=18)
plt.title("SHAP Summary — RF Classifier (ITT ≥85%)\n(positive SHAP = increases probability of ≥85% eradication)", fontsize=12, fontweight="bold")
plt.tight_layout()
plt.savefig(f"{FIG}/fi_shap_rf_clf85.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ fi_shap_rf_clf85.png")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 6: Partial dependence — CLR resistance and Duration
# ══════════════════════════════════════════════════════════════════════════════
clr_idx  = FEATURES.index("CLR_Resistance_pct")
dur_idx  = FEATURES.index("Duration_Days")
vono_idx = FEATURES.index("Is_Vonoprazan")
pcab_idx = FEATURES.index("Is_PCAB")

fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
for ax, feat_idx, feat_name in [
        (axes[0], clr_idx,  "CLR_Resistance_pct"),
        (axes[1], dur_idx,  "Duration_Days"),
        (axes[2], pcab_idx, "Is_PCAB")]:
    # PDP needs a fitted estimator; gb_reg is a Pipeline — use the inner tree on imputed X
    PartialDependenceDisplay.from_estimator(
        gb_tree, X_reg, [feat_idx],
        feature_names=FEATURES,
        ax=ax, grid_resolution=30,
        line_kw={"color": "#2196F3", "linewidth": 2}
    )
    ax.set_xlabel(FEAT_LABELS.get(feat_name, feat_name), fontsize=10)
    ax.set_ylabel("Partial effect on ITT rate (%)", fontsize=9)
    ax.set_title(f"PDP: {FEAT_LABELS.get(feat_name, feat_name)}", fontsize=11, fontweight="bold")
    ax.grid(alpha=0.3)

plt.suptitle("Partial Dependence Plots — Gradient Boosting Regressor", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(f"{FIG}/fi_partial_dependence.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ fi_partial_dependence.png")


# ══════════════════════════════════════════════════════════════════════════════
# Console: top features ranked by mean |SHAP|
# ══════════════════════════════════════════════════════════════════════════════
mean_abs_shap = np.abs(shap_vals_gb).mean(axis=0)
ranked = np.argsort(mean_abs_shap)[::-1]
print("\n" + "═"*55)
print("Top features by mean |SHAP| (GBR, ITT rate)")
print("═"*55)
for rank, idx in enumerate(ranked[:15], 1):
    direction = "↑" if shap_vals_gb[:, idx].mean() > 0 else "↓"
    print(f"  {rank:>2}. {labels[idx]:<30} {mean_abs_shap[idx]:>5.2f}  {direction}")

print("\n✓ Phase 7 (feature importance) complete.")
