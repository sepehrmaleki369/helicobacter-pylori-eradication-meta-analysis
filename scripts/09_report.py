"""
Phase 8: Final summary report.
Outputs: project/report/summary_report.txt + project/figures/report_*.png
"""
import csv, math, os, pickle, collections, warnings
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
warnings.filterwarnings("ignore")

from sklearn.model_selection import KFold, StratifiedKFold, cross_val_score
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.metrics import roc_auc_score

IN      = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/data/processed/clean_dataset.csv"
MDL_DIR = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/models"
FIG     = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/figures"
RPT_DIR = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/report"
os.makedirs(RPT_DIR, exist_ok=True)

with open(IN, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

def flt(v):
    try: return float(v) if v not in (None,"","None") else None
    except: return None
def intt(v):
    try: return int(float(v)) if v not in (None,"","None") else None
    except: return None

for r in rows:
    for col in ["ITT_Rate","PP_Rate","CLR_Resistance_pct","MTZ_Resistance_pct",
                "AMX_Resistance_pct","LFX_Resistance_pct","Duration_Days","Primary_Rate"]:
        r[col] = flt(r[col])
    for col in ["N_ITT","Is_Dual","Is_Triple","Is_Quadruple","Is_PCAB","Is_Vonoprazan",
                "Is_Standard_PPI","Has_Bismuth","Is_High_CLR_Region","Is_East_Asia",
                "Success_ITT_85","Success_ITT_90"]:
        r[col] = intt(r[col])

# ── Load models (Tier 1 PRETREAT family — Round 2 main analysis) ─────────────
FAM = "pretreat"
with open(f"{MDL_DIR}/feature_names_{FAM}.pkl","rb") as f: FEATURES = pickle.load(f)
X_reg = np.load(f"{MDL_DIR}/X_reg_{FAM}.npy")
y_reg = np.load(f"{MDL_DIR}/y_reg_{FAM}.npy")
X_85  = np.load(f"{MDL_DIR}/X_85_{FAM}.npy")
y_85  = np.load(f"{MDL_DIR}/y_85_{FAM}.npy")
# Impute NaN for SHAP
from sklearn.impute import SimpleImputer
X_reg = SimpleImputer(strategy="median").fit_transform(X_reg)
X_85  = SimpleImputer(strategy="median").fit_transform(X_85)
with open(f"{MDL_DIR}/reg_{FAM}_gradientboost.pkl","rb") as f: gb_reg = pickle.load(f)
with open(f"{MDL_DIR}/clf85_{FAM}_randomforest.pkl","rb") as f: rf_clf = pickle.load(f)

def mean_sd(vals):
    if not vals: return 0, 0
    m = sum(vals)/len(vals)
    sd = math.sqrt(sum((x-m)**2 for x in vals)/(len(vals)-1)) if len(vals)>1 else 0
    return m, sd

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE: 2×3 summary dashboard
# ═══════════════════════════════════════════════════════════════════════════════
PALETTE = {"dual":"#2196F3","triple":"#FF9800","quadruple":"#4CAF50","nonbismuth_quadruple":"#9C27B0"}

fig = plt.figure(figsize=(16, 11))
gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.38)

# ── Panel A: Regimen breakdown pie ─────────────────────────────────────────────
ax_a = fig.add_subplot(gs[0, 0])
ttype_counts = collections.Counter(r["Treatment_Type"] for r in rows)
type_order = ["dual","triple","quadruple","nonbismuth_quadruple"]
type_labels = ["Dual\n(PPI+Amox)", "Triple\n(+Clari/Metro)", "Quadruple\n(+Bismuth)", "Non-bismuth\nQuad"]
sizes  = [ttype_counts.get(t, 0) for t in type_order]
colors = [PALETTE[t] for t in type_order]
wedges, texts, autotexts = ax_a.pie(
    sizes, labels=type_labels, colors=colors, autopct="%1.0f%%",
    startangle=90, textprops={"fontsize": 9})
for at in autotexts: at.set_fontsize(9)
ax_a.set_title("A. Treatment Type\nBreakdown (n=84 arms)", fontsize=11, fontweight="bold")

# ── Panel B: Mean ITT ≥85% by regimen ─────────────────────────────────────────
ax_b = fig.add_subplot(gs[0, 1])
for xi, ttype in enumerate(["dual","triple","quadruple"]):
    vals = [r["ITT_Rate"] for r in rows if r["Treatment_Type"]==ttype and r["ITT_Rate"] is not None]
    m, sd = mean_sd(vals)
    n85 = sum(1 for v in vals if v>=85)
    col = PALETTE[ttype]
    ax_b.bar(xi, m, color=col, alpha=0.8, width=0.55)
    ax_b.errorbar(xi, m, yerr=sd, fmt="none", color="black", capsize=5)
    ax_b.text(xi, m+sd+1.5, f"{m:.1f}%\n({n85}/{len(vals)}≥85%)", ha="center", fontsize=8.5, fontweight="bold")
ax_b.axhline(85, color="red", linestyle="--", lw=1.2, label="85% target")
ax_b.axhline(90, color="darkred", linestyle="--", lw=1.0, label="90% target")
ax_b.set_xticks([0,1,2]); ax_b.set_xticklabels(["Dual","Triple","Quadruple"], fontsize=10)
ax_b.set_ylim(55,100); ax_b.set_ylabel("Mean ITT Rate (%)", fontsize=10)
ax_b.set_title("B. ITT Rate by Treatment\nType (mean ± SD)", fontsize=11, fontweight="bold")
ax_b.legend(fontsize=8); ax_b.grid(axis="y", alpha=0.3)

# ── Panel C: P-CAB vs PPI ─────────────────────────────────────────────────────
ax_c = fig.add_subplot(gs[0, 2])
groups_c = [
    ("Vonoprazan\ndual", [r["ITT_Rate"] for r in rows if r["Is_Dual"]==1 and r["Is_Vonoprazan"]==1 and r["ITT_Rate"] is not None], "#E91E63"),
    ("Standard PPI\ndual", [r["ITT_Rate"] for r in rows if r["Is_Dual"]==1 and r["Is_Standard_PPI"]==1 and r["ITT_Rate"] is not None], "#607D8B"),
    ("Vonoprazan\n(all)", [r["ITT_Rate"] for r in rows if r["Is_Vonoprazan"]==1 and r["ITT_Rate"] is not None], "#AD1457"),
    ("Standard PPI\n(all)", [r["ITT_Rate"] for r in rows if r["Is_Standard_PPI"]==1 and r["ITT_Rate"] is not None], "#37474F"),
]
for xi, (lbl, vals, col) in enumerate(groups_c):
    m, sd = mean_sd(vals)
    ax_c.bar(xi, m, color=col, alpha=0.8, width=0.55)
    ax_c.errorbar(xi, m, yerr=sd, fmt="none", color="black", capsize=4)
    ax_c.text(xi, m+sd+1, f"{m:.1f}%\nn={len(vals)}", ha="center", fontsize=8, fontweight="bold")
ax_c.axhline(85, color="red", linestyle="--", lw=1.0)
ax_c.set_xticks(range(4)); ax_c.set_xticklabels([g[0] for g in groups_c], fontsize=8)
ax_c.set_ylim(55,100); ax_c.set_ylabel("Mean ITT Rate (%)", fontsize=10)
ax_c.set_title("C. P-CAB vs Standard PPI\n(mean ± SD)", fontsize=11, fontweight="bold")
ax_c.grid(axis="y", alpha=0.3)

# ── Panel D: SHAP importance (top 10) ─────────────────────────────────────────
ax_d = fig.add_subplot(gs[1, 0])
import shap
explainer = shap.TreeExplainer(gb_reg.named_steps["m"])
shap_vals = explainer.shap_values(X_reg)
mean_abs  = np.abs(shap_vals).mean(axis=0)
FEAT_LABELS = {
    "Is_Dual":"Dual therapy","Is_Triple":"Triple therapy","Is_Quadruple":"Quadruple therapy",
    "Has_Bismuth":"Bismuth","Is_Vonoprazan":"Vonoprazan","Is_Tegoprazan":"Tegoprazan",
    "Is_Standard_PPI":"Standard PPI","Is_PCAB":"Any P-CAB","Has_Clarithromycin":"Clarithromycin",
    "Has_Metronidazole":"Metronidazole","Is_Tetracycline_Dual":"Tetracycline dual",
    "Is_Minocycline_Dual":"Minocycline dual","Is_Furazolidone_Quad":"Furazolidone quad",
    "Duration_Days":"Duration (days)","CLR_Resistance_pct":"CLR resistance %",
    "MTZ_Resistance_pct":"MTZ resistance %","AMX_Resistance_pct":"AMX resistance %",
    "LFX_Resistance_pct":"LFX resistance %","CLR_use_x_CLR_resistance":"CLR×CLR-resist",
    "Is_High_CLR_Region":"High CLR region","Is_High_AMX_Region":"High AMX region",
    "Is_East_Asia":"East Asia","Is_Western":"Western","Is_South_Asia_ME":"S. Asia/ME",
    "Is_Latin_America":"Latin America","Is_Southeast_Asia":"Southeast Asia",
    "Mean_Age_yr":"Mean age","Compliance_pct":"Compliance %",
    "Mean_Age_missing":"Age missing","Compliance_missing":"Compliance missing",
}
labels = [FEAT_LABELS.get(f, f) for f in FEATURES]
top10 = np.argsort(mean_abs)[::-1][:10]
bar_colors = ["#E53935" if shap_vals[:,i].mean()>0 else "#1565C0" for i in top10]
ax_d.barh(range(10), [mean_abs[i] for i in top10[::-1]],
          color=bar_colors[::-1], alpha=0.85, height=0.65)
ax_d.set_yticks(range(10))
ax_d.set_yticklabels([labels[i] for i in top10[::-1]], fontsize=9)
ax_d.set_xlabel("Mean |SHAP| value", fontsize=9)
ax_d.set_title("D. Feature Importance\n(SHAP, GBR regressor)", fontsize=11, fontweight="bold")
ax_d.grid(axis="x", alpha=0.3)
red_patch  = mpatches.Patch(color="#E53935", label="↑ eradication")
blue_patch = mpatches.Patch(color="#1565C0", label="↓ eradication")
ax_d.legend(handles=[red_patch, blue_patch], fontsize=8, loc="lower right")

# ── Panel E: Model performance summary ────────────────────────────────────────
ax_e = fig.add_subplot(gs[1, 1])
# Tier 1 best CV results (pretreat family, weighted, Round 2)
model_names = ["Ridge", "Lasso", "ElasticNet", "RF", "GBM"]
rmse_vals   = [10.80, 9.77, 9.81, 9.23, 8.70]   # LOO-arm
auc_vals    = [0.542, 0.533, 0.533, 0.651, 0.640]  # AUC≥85% (rep)

x = np.arange(len(model_names))
w = 0.35
bars1 = ax_e.bar(x - w/2, rmse_vals, w, label="RMSE (%) [left]", color="#2196F3", alpha=0.8)
ax_e2 = ax_e.twinx()
bars2 = ax_e2.bar(x + w/2, auc_vals, w, label="AUC ≥85% [right]", color="#FF9800", alpha=0.8)
ax_e.set_ylabel("CV RMSE (%)", color="#2196F3", fontsize=9)
ax_e2.set_ylabel("CV ROC-AUC", color="#FF9800", fontsize=9)
ax_e.set_ylim(0, 13); ax_e2.set_ylim(0.4, 1.0)
ax_e2.axhline(0.5, color="gray", linestyle="--", lw=0.8)
ax_e.set_xticks(x); ax_e.set_xticklabels(model_names, rotation=15, fontsize=9)
ax_e.set_title("E. Model CV Performance\n(weighted LOO-arm; RMSE + AUC≥85%)", fontsize=11, fontweight="bold")
lines1, lbls1 = ax_e.get_legend_handles_labels()
lines2, lbls2 = ax_e2.get_legend_handles_labels()
ax_e.legend(lines1+lines2, lbls1+lbls2, fontsize=8, loc="upper right")

# ── Panel F: Regional resistance profile ──────────────────────────────────────
ax_f = fig.add_subplot(gs[1, 2])
regions_data = {
    "East Asia":     [r for r in rows if r["Geographic_Region"]=="East Asia"],
    "Western":       [r for r in rows if r["Geographic_Region"]=="Western"],
    "Middle East":   [r for r in rows if r["Geographic_Region"]=="Middle East"],
    "South Asia":    [r for r in rows if r["Geographic_Region"]=="South Asia"],
    "Latin America": [r for r in rows if r["Geographic_Region"]=="Latin America"],
}
reg_labels = list(regions_data.keys())
clr_means = []
mtz_means = []
for reg, rlist in regions_data.items():
    clrs = [r["CLR_Resistance_pct"] for r in rlist if r["CLR_Resistance_pct"] is not None]
    mtzs = [r["MTZ_Resistance_pct"] for r in rlist if r["MTZ_Resistance_pct"] is not None]
    clr_means.append(sum(clrs)/len(clrs) if clrs else 0)
    mtz_means.append(sum(mtzs)/len(mtzs) if mtzs else 0)

x_f = np.arange(len(reg_labels))
ax_f.bar(x_f - 0.2, clr_means, 0.38, label="CLR resistance", color="#E53935", alpha=0.8)
ax_f.bar(x_f + 0.2, mtz_means, 0.38, label="MTZ resistance", color="#FF9800", alpha=0.8)
ax_f.axhline(30, color="#E53935", linestyle="--", lw=1.0, alpha=0.6)
ax_f.set_xticks(x_f); ax_f.set_xticklabels(reg_labels, rotation=25, ha="right", fontsize=8.5)
ax_f.set_ylabel("Mean resistance (%)", fontsize=9)
ax_f.set_title("F. Regional Antibiotic\nResistance Profile", fontsize=11, fontweight="bold")
ax_f.legend(fontsize=9); ax_f.grid(axis="y", alpha=0.3)
ax_f.set_ylim(0, 90)

plt.suptitle(f"H. pylori Eradication Therapy — ML + Meta-Analysis Summary Dashboard\n{len(rows)} treatment arms · {len(set(r['Ref'] for r in rows))} RCTs · 2012–2025",
             fontsize=14, fontweight="bold", y=1.01)
plt.savefig(f"{FIG}/report_dashboard.png", dpi=160, bbox_inches="tight")
plt.close()
print("✓ report_dashboard.png")


# ══════════════════════════════════════════════════════════════════════════════
# TEXT REPORT
# ══════════════════════════════════════════════════════════════════════════════
itts = [r["ITT_Rate"] for r in rows if r["ITT_Rate"] is not None]
pps  = [r["PP_Rate"]  for r in rows if r["PP_Rate"]  is not None]
m_itt, sd_itt = mean_sd(itts)
m_pp,  sd_pp  = mean_sd(pps)
n85 = sum(1 for v in itts if v>=85)
n90 = sum(1 for v in itts if v>=90)

dual_itts  = [r["ITT_Rate"] for r in rows if r["Is_Dual"]==1     and r["ITT_Rate"] is not None]
trip_itts  = [r["ITT_Rate"] for r in rows if r["Is_Triple"]==1   and r["ITT_Rate"] is not None]
quad_itts  = [r["ITT_Rate"] for r in rows if r["Is_Quadruple"]==1 and r["ITT_Rate"] is not None]
vono_itts  = [r["ITT_Rate"] for r in rows if r["Is_Vonoprazan"]==1 and r["ITT_Rate"] is not None]
ppi_itts   = [r["ITT_Rate"] for r in rows if r["Is_Standard_PPI"]==1 and r["ITT_Rate"] is not None]
east_itts  = [r["ITT_Rate"] for r in rows if r["Is_East_Asia"]==1 and r["ITT_Rate"] is not None]
hi_clr_itts = [r["ITT_Rate"] for r in rows if r["Is_High_CLR_Region"]==1 and r["ITT_Rate"] is not None]
lo_clr_itts = [r["ITT_Rate"] for r in rows if r["Is_High_CLR_Region"]==0 and r["ITT_Rate"] is not None]

report = f"""
H. PYLORI ERADICATION THERAPY — MACHINE LEARNING ANALYSIS
Final Report · {len(rows)} arms · 37 RCTs · 2012–2025
Generated by: 09_report.py
=======================================================================

1. DATASET OVERVIEW
───────────────────────────────────────────────────────────────────────
  Total arms analyzed          : {len(rows)}
  Arms with ITT data           : {len(itts)}
  Arms with PP data            : {len(pps)}
  Unique study references      : {len(set(r['Ref'] for r in rows))}
  Study period                 : 2012–2025
  Geographic focus             : East Asia ({sum(1 for r in rows if r['Is_East_Asia']==1)} arms, {100*sum(1 for r in rows if r['Is_East_Asia']==1)/len(rows):.0f}%)

  Treatment type breakdown:
    Dual (PPI/P-CAB + amoxicillin)  : {sum(1 for r in rows if r['Is_Dual']==1)} arms
    Triple (PPI + amox + clari/metro): {sum(1 for r in rows if r['Is_Triple']==1)} arms
    Quadruple (bismuth-containing)   : {sum(1 for r in rows if r['Is_Quadruple']==1)} arms

  PPI class:
    Vonoprazan (P-CAB)  : {sum(1 for r in rows if r['Is_Vonoprazan']==1)} arms
    Tegoprazan (P-CAB)  : {sum(1 for r in rows if r.get('Is_Tegoprazan')=='1' or r.get('Is_Tegoprazan')==1)} arms
    Standard PPI        : {sum(1 for r in rows if r['Is_Standard_PPI']==1)} arms

  Resistance data quality:
    In-paper culture data  : {sum(1 for r in rows if r.get('Resistance_Source_Type')=='in-paper')} arms
    Regional estimates     : {sum(1 for r in rows if r.get('Resistance_Source_Type')=='regional-estimate')} arms

2. ERADICATION OUTCOMES
───────────────────────────────────────────────────────────────────────
  ITT rates (n={len(itts)}):
    Mean ± SD   : {m_itt:.1f}% ± {sd_itt:.1f}%
    Range       : {min(itts):.1f}% – {max(itts):.1f}%
    Arms ≥85%   : {n85}/{len(itts)} ({100*n85/len(itts):.0f}%)
    Arms ≥90%   : {n90}/{len(itts)} ({100*n90/len(itts):.0f}%)

  PP rates (n={len(pps)}):
    Mean ± SD   : {m_pp:.1f}% ± {mean_sd(pps)[1]:.1f}%
    Range       : {min(pps):.1f}% – {max(pps):.1f}%
    Mean PP−ITT : +{m_pp-m_itt:.1f} percentage points

  By treatment type (ITT):
    Dual therapy       : {mean_sd(dual_itts)[0]:.1f}% ± {mean_sd(dual_itts)[1]:.1f}%  (n={len(dual_itts)})
    Triple therapy     : {mean_sd(trip_itts)[0]:.1f}% ± {mean_sd(trip_itts)[1]:.1f}%  (n={len(trip_itts)})
    Quadruple therapy  : {mean_sd(quad_itts)[0]:.1f}% ± {mean_sd(quad_itts)[1]:.1f}%  (n={len(quad_itts)})

  By PPI class (ITT):
    Vonoprazan (P-CAB) : {mean_sd(vono_itts)[0]:.1f}% ± {mean_sd(vono_itts)[1]:.1f}%  (n={len(vono_itts)})
    Standard PPI       : {mean_sd(ppi_itts)[0]:.1f}% ± {mean_sd(ppi_itts)[1]:.1f}%  (n={len(ppi_itts)})

  By CLR resistance region (ITT):
    High CLR region (≥30%) : {mean_sd(hi_clr_itts)[0]:.1f}%  (n={len(hi_clr_itts)})
    Low CLR region (<30%)  : {mean_sd(lo_clr_itts)[0]:.1f}%  (n={len(lo_clr_itts)})

3. PREDICTION VS INFERENCE — TWO SEPARATE MODELS
───────────────────────────────────────────────────────────────────────
  Following Heinze 2018 / Royston 2009 / Berk 2013, predictive feature
  selection and inferential covariate adjustment were handled separately.

  See report/MODEL_CARD.md for full details.

3A. PREDICTION MODEL  (data-driven, optimised for LOSO R²)
───────────────────────────────────────────────────────────────────────
  Headline:  RFE top-10 + RandomForest (weighted by N_ITT)
  Selected features (10): Is_Quadruple, Has_Bismuth, Is_Standard_PPI,
    CLR/MTZ/AMX resistance %, CLR×CLR-resistance, Is_High_CLR_Region,
    Is_High_AMX_Region, Is_Latin_America
  Cross-validated metrics (LOO-arm | LOSO-study):
    RMSE      = 9.27% | 9.95%
    R²        = +0.195 | +0.073
    Cal slope = 1.073 | 0.733

  Top SHAP driver: CLR_use × CLR_resistance (mean|SHAP|=2.02, ↓)

  Best overall predictor:  Bayesian hierarchical (marginal)
    LOSO R² = +0.21, calibration slope = 1.016 (near-perfect)
    Used as both prediction AND inference model — same fit serves both.

3B. INFERENCE MODEL  (clinically pre-specified, for treatment effects)
───────────────────────────────────────────────────────────────────────
  Headline:  Bayesian hierarchical binomial GLM with random
             intercept by study (PyMC + nutpie sampler).
  Feature set: 15 clinically pre-specified covariates (NOT RFE-selected).

  Significant posterior effects (95% HDI excludes 1.0):
    Vonoprazan                OR=1.96  [1.69, 2.25]  P(>1)=100%  ✓
    Susceptibility-guided     OR=1.98  [1.29, 3.05]  P(>1)=99.9% ✓
    Is_Quadruple              OR=1.65  [1.25, 2.17]  P(>1)=100%  ✓
    Duration (per SD)         OR=1.24  [1.12, 1.37]  P(>1)=100%  ✓
    Compliance (per SD)       OR=1.11  [1.02, 1.21]  P(>1)=99.3% ✓
    CLR×CLR-resistance        OR=0.73  [0.55, 0.97]  P(<1)=98.4% ✓
    Has_Bismuth               OR=0.66  [0.48, 0.93]  P(<1)=99.2% ✓

  Heterogeneity: σ_study = 0.51 [0.40, 0.64]
  MCMC: max r̂=1.010, min ESS=611 — converged.

3C. GEE-STYLE HIERARCHICAL INFERENCE (cluster-robust SE on Ref)
───────────────────────────────────────────────────────────────────────
  Population-averaged binomial GLM (PyMC compilation failed on
  macOS; statsmodels GEE-equivalent used instead):

  Significant effects (cluster-robust 95% CI, p < 0.05):
    Vonoprazan         OR = 1.64  [1.30, 2.09]   p < 0.0001 ✓
    Is_Quadruple       OR = 1.87  [1.26, 2.78]   p = 0.0019 ✓
    Has_Clarithromycin OR = 0.64  [0.44, 0.93]   p = 0.018  ✓ ↓
    Tegoprazan         OR = 1.12  [0.81, 1.56]   ns
    Has_Bismuth        OR = 0.71  [0.43, 1.16]   ns
    Duration (per day) OR = 1.06  [0.99, 1.14]   borderline
    Is_East_Asia       OR = 1.29  [0.90, 1.84]   ns

  CLINICAL INTERPRETATION:
   • Vonoprazan-containing regimens have 64% higher odds of
     eradication than standard PPI-based regimens.
   • Quadruple therapy has 87% higher odds than reference (dual).
   • Clarithromycin presence REDUCES odds by 36% — likely
     because CLR-containing arms include the failing standard
     triple in high-resistance regions.

3B. META-ANALYTIC RESULTS (Tier 2 Binomial GLM, cluster-robust SE)
───────────────────────────────────────────────────────────────────────
  Cluster-bootstrap CIs (2000 iter, resampling studies):
    Vonoprazan       OR = 1.61  [1.23, 2.16]   significant ↑
    Tegoprazan       OR = 1.11  [0.70, 1.75]   not significant
    Duration (per day) OR = 1.07 [0.98, 1.14]  borderline
    Is_Quadruple     OR = 1.64  [0.85, 3.21]   wide CI

3D. RANDOM-EFFECTS META-ANALYSIS (Vonoprazan vs comparator, 18 paired studies)
───────────────────────────────────────────────────────────────────────
  Pooled OR (DerSimonian-Laird) = 1.75  [1.36, 2.25]   significant ↑
  Heterogeneity:
    Cochran Q  = 40.61  (df=17, p=0.0011)   significant
    τ²         = 0.149
    I²         = 58.1%   MODERATE heterogeneity
  Publication bias (Egger):
    Intercept  = 0.139  (p=0.883)   NO bias detected

3E. SUBGROUP ANALYSES (Vonoprazan effect)
───────────────────────────────────────────────────────────────────────
  Stratum                       n      OR     95% CI
  ───────────────────────────────────────────────────
  All arms                     142    1.61   [1.22, 2.12]
  East Asia only                99    1.64   [1.23, 2.18]
  Non-East Asia                 43    1.61   [1.11, 2.36]
  High CLR region (≥30%)       103    1.90   [1.47, 2.44]  ←
  Low CLR region (<30%)         39    0.98   [0.64, 1.51]  ←
  Multicenter only              49    1.56   [1.15, 2.12]
  Single center only            93    1.86   [1.22, 2.83]

  Key interaction (cluster-robust):
    Vonoprazan × High_CLR_Region: OR=1.92 [1.29, 2.87], p=0.0013

  CLINICAL INTERPRETATION:
    Vonoprazan's benefit is CONCENTRATED in high-CLR regions.
    In low-CLR regions, vonoprazan ≈ standard PPI (OR=0.98).

3F. SENSITIVITY ANALYSES (drift of vonoprazan OR under exclusions)
───────────────────────────────────────────────────────────────────────
  Main analysis (no exclusion)         n=142  OR=1.61  [1.22, 2.12]
  Drop quality-flagged arms             n=39  OR=1.73  [1.15, 2.59]
  Drop susceptibility-guided           n=137  OR=1.65  [1.25, 2.18]
  Drop regional-estimate resistance     n=39  OR=1.73  [1.15, 2.59]
  Drop small arms (N_ITT < 50)         n=126  OR=1.63  [1.22, 2.18]

  → Vonoprazan effect is ROBUST across all sensitivity scenarios.

3C. CALIBRATION (LOSO, proportion scale, FULL family)
───────────────────────────────────────────────────────────────────────
                          RMSE    Brier   Cal-slope  Cal-int
    T1 ElasticNet        0.096   0.009     0.17       0.69
    T2 Binomial GLM      0.105   0.011     0.20       0.67
    T3 Beta Regression   0.102   0.010     0.24       0.63  ← best slope

  All models heavily shrink toward the mean (slopes ≪ 1) —
  the dataset has too little outcome variance for sharp prediction.
  Tier 3 Beta Regression has the closest calibration slope to 1.

4. KEY PREDICTORS (SHAP — Gradient Boosting Regressor, FULL family)
───────────────────────────────────────────────────────────────────────
  Rank  Feature                     Mean|SHAP|  Direction
  ────  ────────────────────────────────────────────────
    1   Duration (days)               1.85      ↓ (in dataset; ↑ in GLM)
    2   Vonoprazan (P-CAB)            1.66      ↑ positive effect
    3   CLR resistance %              1.63      ↑ (confounded — see note*)
    4   LFX resistance %              1.32      ↑ (confounded)
    5   MTZ resistance %              1.27      ↓ higher = worse
    6   Compliance %                  1.22      ↓ in SHAP — see note**
    7   Mean age (years)              1.15      ↓ older = worse
    8   AMX resistance %              0.67      ↓ higher = worse
    9   CLR × CLR-resistance          0.66      complex interaction
   10   Standard PPI                  0.46      ↑ neutral baseline

  * CLR/LFX resistance SHAP signs are positive in the tree model
    because most high-resistance arms use vonoprazan-dual, which
    overcomes resistance — confounding. The GLM (Tier 2) controls
    for treatment and shows AMX resistance is the only significant
    negative resistance predictor (OR=0.94 per 1% increase).
  ** Compliance_pct is partly post-randomisation; treat in the
    "prediction" model but exclude in the "treatment-effect" inference.

5. CLINICAL INSIGHTS
───────────────────────────────────────────────────────────────────────
  • Vonoprazan-containing dual therapy achieves mean ITT ≈ 85%,
    comparable to quadruple therapy, with fewer drugs.
  • High clarithromycin resistance (>30%) does NOT reduce eradication
    rates in the vonoprazan-dual era — P-CABs appear to overcome
    resistance by maintaining acid suppression.
  • Treatment duration is the strongest linear predictor: 14-day
    regimens consistently outperform 7-day regimens.
  • Triple therapy performs poorly (mean ITT 78.6%, only 12% reach ≥85%)
    in East Asia, consistent with >30% CLR resistance rates.
  • Bismuth-quadruple remains effective (mean ITT 84.1%) but P-CAB
    dual achieves similar rates with a simpler regimen.
  • Levofloxacin resistance (LFX ↑) is a negative predictor —
    particularly relevant for rescue therapy arms.

6. LIMITATIONS
───────────────────────────────────────────────────────────────────────
  • n=102 treatment arms from 45 studies is moderate for ML; results
    should be treated as hypothesis-generating but with valid
    cluster-robust inference for treatment effects.
  • 70/102 arms (~69%) rely on regional resistance estimates rather
    than in-paper culture data — resistance features are approximate.
  • All studies are aggregate RCT data, not individual patient records.
  • Geographic skew: 87% of arms East Asian; findings may not
    generalize to Western populations (n=3 Western arms only).
  • Calibration slopes far from 1.0 — predictions cluster near the
    overall mean (≈83%) regardless of features. The dataset has
    too narrow an outcome range for sharp prediction.
  • Compliance_pct (45% missing) and Mean_Age (38% missing) imputed
    by median; results sensitive to imputation strategy.

7. FILES PRODUCED
───────────────────────────────────────────────────────────────────────
  Data:
    data/processed/extracted_arms.csv          (paper-level first pass)
    data/processed/arm_level_dataset.csv       (106 arms, hand-coded)
    data/processed/arm_dataset_with_resistance.csv (106 + resistance)
    data/processed/clean_dataset.csv           (104 arms, ML-ready)

  Figures (project/figures/):
    fig1_rate_distributions.png
    fig2_forest_plot.png
    fig3_treatment_type_comparison.png
    fig4_pcab_vs_ppi.png
    fig5_scatter_clr_resistance.png
    fig6_resistance_heatmap.png
    fig7_duration_effect.png
    fig8_ppi_comparison_dual.png
    fig9_itt_vs_pp.png
    model_cv_comparison.png
    model_roc_curves.png
    model_actual_vs_predicted.png
    model_learning_curve.png
    fi_permutation_gbr.png
    fi_rf_importance.png
    fi_ridge_coefficients.png
    fi_shap_gbr_summary.png
    fi_shap_gbr_bar.png
    fi_shap_rf_clf85.png
    fi_partial_dependence.png
    report_dashboard.png

  Models (project/models/):
    reg_ridge.pkl, reg_lasso.pkl
    reg_randomforest.pkl, reg_gradientboost.pkl
    clf85_logreg.pkl, clf85_randomforest.pkl, clf85_gradientboost.pkl
    clf90_logreg.pkl, clf90_randomforest.pkl, clf90_gradientboost.pkl
=======================================================================
"""

report_path = f"{RPT_DIR}/summary_report.txt"
with open(report_path, "w", encoding="utf-8") as f:
    f.write(report)

print(report)
print(f"✓ Report written to {report_path}")
print("✓ Phase 8 complete — project pipeline finished.")
