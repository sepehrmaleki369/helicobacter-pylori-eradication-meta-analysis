"""
Extended EDA on the current 144-arm dataset (Round 2):
  - Missing data heatmap
  - Feature correlation matrix
  - Univariate associations (each feature vs ITT_Rate; weighted Spearman ρ + p)
  - Predictor distributions stratified by treatment type
  - Outcome distribution by each binary feature (boxplots)
  - Outlier identification (residuals from simple OLS)

Outputs to project/figures/eda_*.png
"""
import os, math, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy import stats as scipy_stats
warnings.filterwarnings("ignore")

IN  = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/data/processed/clean_dataset.csv"
FIG = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/figures"
RPT = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/report"
os.makedirs(FIG, exist_ok=True); os.makedirs(RPT, exist_ok=True)

df = pd.read_csv(IN)
df = df.dropna(subset=["ITT_Rate", "N_ITT"]).reset_index(drop=True)
print(f"EDA on {len(df)} arms")

# Features used in modeling
FEATURES_NUM = ["Duration_Days","CLR_Resistance_pct","MTZ_Resistance_pct",
                "AMX_Resistance_pct","LFX_Resistance_pct","CLR_use_x_CLR_resistance",
                "Mean_Age_yr","Compliance_pct","PPI_Daily_mg","Amox_Daily_mg",
                "Study_Era","N_ITT"]
FEATURES_BIN = ["Is_Dual","Is_Triple","Is_Quadruple","Has_Bismuth",
                "Is_Vonoprazan","Is_Tegoprazan","Is_Standard_PPI","Is_PCAB",
                "Has_Clarithromycin","Has_Metronidazole",
                "Is_Concomitant","Is_Sequential","Is_Hybrid","Is_Bismuth_Quad",
                "Is_East_Asia","Is_Western","Is_South_Asia_ME","Is_Latin_America",
                "Is_Southeast_Asia","Is_High_CLR_Region","Is_High_AMX_Region",
                "Is_Susceptibility_Guided","Is_Multicenter"]
for c in FEATURES_NUM + FEATURES_BIN:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  1. MISSING DATA HEATMAP                                                   ║
# ╚════════════════════════════════════════════════════════════════════════════╝
miss = df[FEATURES_NUM + FEATURES_BIN].isnull().astype(int)
fig, ax = plt.subplots(figsize=(12, max(6, len(df)*0.04)))
im = ax.imshow(miss.values, aspect="auto", cmap="Reds", vmin=0, vmax=1)
ax.set_xticks(range(len(miss.columns)))
ax.set_xticklabels(miss.columns, rotation=70, ha="right", fontsize=7)
ax.set_yticks([])
ax.set_ylabel("Arms (rows)", fontsize=10)

# Annotate missing % per column
miss_pct = miss.mean() * 100
for i, p in enumerate(miss_pct):
    if p > 0:
        ax.text(i, len(df)+1, f"{p:.0f}%", ha="center", fontsize=7,
                color="darkred", fontweight="bold")
ax.set_title("Missing data pattern across features\n(red = missing; % missing labeled below)",
             fontweight="bold")
plt.tight_layout()
plt.savefig(f"{FIG}/eda_missing_heatmap.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"✓ eda_missing_heatmap.png")

# Console summary
print("\n── Missing data summary ──")
for c, p in miss_pct.sort_values(ascending=False).items():
    if p > 0:
        print(f"  {c:<32} {p:>5.1f}% missing ({int(miss[c].sum())} arms)")

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  2. CORRELATION MATRIX (numeric features + ITT_Rate)                       ║
# ╚════════════════════════════════════════════════════════════════════════════╝
corr_cols = FEATURES_NUM + ["ITT_Rate", "PP_Rate"]
corr = df[corr_cols].corr(method="pearson")
fig, ax = plt.subplots(figsize=(11, 10))
im = ax.imshow(corr.values, cmap="coolwarm", vmin=-1, vmax=1)
plt.colorbar(im, ax=ax, label="Pearson r")
ax.set_xticks(range(len(corr_cols))); ax.set_xticklabels(corr_cols, rotation=70, ha="right", fontsize=9)
ax.set_yticks(range(len(corr_cols))); ax.set_yticklabels(corr_cols, fontsize=9)
for i in range(len(corr_cols)):
    for j in range(len(corr_cols)):
        v = corr.values[i, j]
        if not math.isnan(v):
            ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                    fontsize=7, color="white" if abs(v) > 0.5 else "black")
ax.set_title("Pearson correlation matrix — numeric features + outcomes",
             fontweight="bold", pad=15)
plt.tight_layout()
plt.savefig(f"{FIG}/eda_correlation_matrix.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"✓ eda_correlation_matrix.png")

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  3. UNIVARIATE ASSOCIATIONS (every feature vs ITT_Rate)                    ║
# ╚════════════════════════════════════════════════════════════════════════════╝
print("\n── Univariate associations with ITT_Rate ──")
print(f"{'Feature':<32} {'ρ (Spearman)':>12} {'p-value':>10} {'n':>5}")
print("-"*65)
univariate = []
for c in FEATURES_NUM + FEATURES_BIN:
    sub = df[[c, "ITT_Rate"]].dropna()
    if len(sub) < 10: continue
    if sub[c].nunique() < 2: continue
    rho, p = scipy_stats.spearmanr(sub[c], sub["ITT_Rate"])
    univariate.append({"feature": c, "rho": rho, "p": p, "n": len(sub)})

univariate.sort(key=lambda x: abs(x["rho"]), reverse=True)
for u in univariate[:25]:
    sig = " ✓" if u["p"] < 0.05 else "  "
    print(f"  {u['feature']:<32} {u['rho']:>+12.3f} {u['p']:>10.4f} {u['n']:>5} {sig}")

# Forest plot of |Spearman ρ|
fig, ax = plt.subplots(figsize=(9, max(5, len(univariate)*0.30)))
order = sorted(univariate, key=lambda x: abs(x["rho"]))
ys = range(len(order))
rhos = [u["rho"] for u in order]
labels = [u["feature"] for u in order]
colors = ["#388E3C" if u["p"] < 0.05 else "#9E9E9E" for u in order]
ax.barh(ys, rhos, color=colors, alpha=0.85, height=0.7)
ax.axvline(0, color="black", linewidth=1)
ax.set_yticks(list(ys)); ax.set_yticklabels(labels, fontsize=8)
ax.set_xlabel("Spearman ρ vs ITT_Rate", fontsize=10)
ax.set_title("Univariate associations — each feature vs ITT eradication\n"
             "(green = p<0.05; gray = non-significant)", fontweight="bold")
ax.grid(axis="x", alpha=0.3)
plt.tight_layout()
plt.savefig(f"{FIG}/eda_univariate_associations.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"\n✓ eda_univariate_associations.png")

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  4. KEY NUMERIC FEATURE DISTRIBUTIONS                                      ║
# ╚════════════════════════════════════════════════════════════════════════════╝
key_num = ["Duration_Days","CLR_Resistance_pct","MTZ_Resistance_pct",
           "AMX_Resistance_pct","LFX_Resistance_pct",
           "Mean_Age_yr","Compliance_pct","PPI_Daily_mg","Amox_Daily_mg"]
fig, axes = plt.subplots(3, 3, figsize=(13, 10))
axes = axes.flatten()
for i, c in enumerate(key_num):
    ax = axes[i]
    vals = df[c].dropna()
    ax.hist(vals, bins=20, color="#1565C0", alpha=0.75, edgecolor="white")
    ax.axvline(vals.median(), color="red", linestyle="--",
               label=f"median={vals.median():.1f}")
    ax.set_xlabel(c, fontsize=9)
    ax.set_ylabel("Count")
    ax.set_title(f"{c}  (n={len(vals)})", fontsize=9, fontweight="bold")
    ax.legend(fontsize=7); ax.grid(axis="y", alpha=0.3)
plt.suptitle("Distributions of key numeric features", fontweight="bold")
plt.tight_layout()
plt.savefig(f"{FIG}/eda_feature_distributions.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"✓ eda_feature_distributions.png")

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  5. OUTCOME BY BINARY FEATURE (boxplots)                                   ║
# ╚════════════════════════════════════════════════════════════════════════════╝
key_bin = ["Is_Vonoprazan","Is_Tegoprazan","Is_PCAB","Is_Standard_PPI",
           "Is_Dual","Is_Triple","Is_Quadruple",
           "Has_Bismuth","Has_Clarithromycin","Has_Metronidazole",
           "Is_East_Asia","Is_High_CLR_Region","Is_Multicenter",
           "Is_Susceptibility_Guided"]

n_panels = len(key_bin)
ncols = 4
nrows = (n_panels + ncols - 1) // ncols
fig, axes = plt.subplots(nrows, ncols, figsize=(14, 3*nrows))
axes = axes.flatten()
for i, c in enumerate(key_bin):
    ax = axes[i]
    yes = df.loc[df[c] == 1, "ITT_Rate"].dropna()
    no  = df.loc[df[c] == 0, "ITT_Rate"].dropna()
    parts = ax.boxplot([no, yes], labels=["No (0)", "Yes (1)"],
                       patch_artist=True, widths=0.5,
                       medianprops={"color":"red", "linewidth":2})
    for patch, col in zip(parts["boxes"], ["#90A4AE", "#388E3C"]):
        patch.set_facecolor(col); patch.set_alpha(0.7)
    # Mann-Whitney U test
    if len(yes) > 2 and len(no) > 2:
        u, p = scipy_stats.mannwhitneyu(yes, no, alternative="two-sided")
        sig = "*" if p < 0.05 else ""
        ax.set_title(f"{c}  (p={p:.3f}){sig}\nn={len(no)}/{len(yes)}",
                     fontsize=9, fontweight="bold")
    else:
        ax.set_title(f"{c}\nn={len(no)}/{len(yes)}", fontsize=9, fontweight="bold")
    ax.set_ylabel("ITT %", fontsize=8)
    ax.grid(axis="y", alpha=0.3)
# Hide unused subplots
for j in range(n_panels, len(axes)):
    axes[j].axis("off")
plt.suptitle("ITT eradication rate by binary feature (Mann-Whitney U)",
             fontweight="bold")
plt.tight_layout()
plt.savefig(f"{FIG}/eda_outcome_by_binary.png", dpi=140, bbox_inches="tight")
plt.close()
print(f"✓ eda_outcome_by_binary.png")

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  6. OUTLIER DETECTION (residuals from simple OLS on key predictors)        ║
# ╚════════════════════════════════════════════════════════════════════════════╝
import statsmodels.api as sm
# Simple OLS — vonoprazan + duration + CLR resistance
X_simple = df[["Is_Vonoprazan","Duration_Days","CLR_Resistance_pct"]].copy()
X_simple = X_simple.fillna(X_simple.median())
X_simple = sm.add_constant(X_simple)
y_simple = df["ITT_Rate"]
ols = sm.OLS(y_simple, X_simple).fit()
df["residual"] = ols.resid
df["abs_resid"] = df["residual"].abs()
print("\n── Top 10 outliers (largest absolute residuals from simple OLS) ──")
top_outliers = df.nlargest(10, "abs_resid")[["Ref","Arm_Label","ITT_Rate","N_ITT","residual"]]
print(top_outliers.to_string(index=False))

# Outlier plot
fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(ols.fittedvalues, ols.resid, c=df["N_ITT"], cmap="viridis", s=60,
           alpha=0.75, edgecolors="white")
plt.colorbar(ax.collections[0], ax=ax, label="N_ITT")
ax.axhline(0, color="black", linewidth=1)
ax.axhline(15, color="red", linestyle="--", alpha=0.5)
ax.axhline(-15, color="red", linestyle="--", alpha=0.5)
ax.set_xlabel("Predicted ITT (%, from simple 3-feature OLS)", fontsize=11)
ax.set_ylabel("Residual (Observed − Predicted)", fontsize=11)
ax.set_title("Outlier detection — residuals from baseline OLS\n"
             "(red dashed = ±15% threshold)", fontweight="bold")
# Annotate top outliers
for _, r in top_outliers.head(5).iterrows():
    idx = df[df["Arm_Label"] == r["Arm_Label"]].index[0]
    ax.annotate(f"Ref{int(r['Ref'])}", (ols.fittedvalues[idx], ols.resid[idx]),
                fontsize=8, alpha=0.8)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(f"{FIG}/eda_outliers.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"✓ eda_outliers.png")

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  WRITE TEXT REPORT                                                         ║
# ╚════════════════════════════════════════════════════════════════════════════╝
with open(f"{RPT}/eda_results.txt", "w", encoding="utf-8") as f:
    f.write("Extended EDA — Round 2 dataset (144 arms)\n")
    f.write("="*60 + "\n\n")
    f.write("── Missing data summary ──\n")
    for c, p in miss_pct.sort_values(ascending=False).items():
        if p > 0:
            f.write(f"  {c:<32} {p:>5.1f}% missing\n")
    f.write("\n── Top 15 univariate associations (Spearman ρ vs ITT_Rate) ──\n")
    f.write(f"{'Feature':<32} {'ρ':>10} {'p-value':>10}\n")
    for u in univariate[:15]:
        sig = " *" if u["p"] < 0.05 else "  "
        f.write(f"  {u['feature']:<32} {u['rho']:>+10.3f} {u['p']:>10.4f}{sig}\n")
    f.write("\n── Top 10 outliers (residuals from simple 3-feature OLS) ──\n")
    f.write(top_outliers.to_string(index=False))
    f.write("\n")

print(f"\n✓ {RPT}/eda_results.txt")
print("\n✓ Extended EDA complete — 6 new figures, 1 report.")
