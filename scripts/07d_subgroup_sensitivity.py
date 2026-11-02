"""
Tier C-E — Publication-grade analyses:
  C: Subgroup analyses (interactions + stratified)
  D: Sensitivity analyses (drop quality-flagged, guided, regional-resist, small-pilot)
  E: Heterogeneity (Cochran Q, tau², I²) + publication bias (funnel + Egger) + PRISMA
"""
import os, math, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
warnings.filterwarnings("ignore")

import statsmodels.api as sm
import statsmodels.formula.api as smf

IN  = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/data/processed/clean_dataset.csv"
FIG = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/figures"
RPT = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/report"
os.makedirs(FIG, exist_ok=True); os.makedirs(RPT, exist_ok=True)

# ── Load ──────────────────────────────────────────────────────────────────────
df = pd.read_csv(IN)
df = df.dropna(subset=["ITT_Rate","N_ITT","Successes_ITT"]).copy()
df["Successes"] = df["Successes_ITT"].astype(int)
df["Failures"]  = (df["N_ITT"].astype(int) - df["Successes"]).clip(lower=0)
df["Ref"]       = df["Ref"].astype(int)

# Median-impute predictors needed by formulas
for c in ["Mean_Age_yr","Compliance_pct","CLR_Resistance_pct","MTZ_Resistance_pct",
          "AMX_Resistance_pct","LFX_Resistance_pct","Duration_Days"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df[c] = df[c].fillna(df[c].median())

print(f"Dataset: {len(df)} arms, {df['Ref'].nunique()} studies, "
      f"{int(df['N_ITT'].sum())} total patients")

BASE = ("Successes + Failures ~ Is_Vonoprazan + Is_Quadruple + Duration_Days + "
        "CLR_Resistance_pct + Mean_Age_yr")

def fit_glm(formula, data, cluster_col="Ref"):
    """Fit binomial GLM with cluster-robust SE keyed on Ref."""
    return smf.glm(formula, data=data, family=sm.families.Binomial()).fit(
        cov_type="cluster", cov_kwds={"groups": data[cluster_col]})

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  C — SUBGROUP ANALYSES                                                     ║
# ╚════════════════════════════════════════════════════════════════════════════╝

print("\n" + "═"*78)
print("TIER C — Subgroup × treatment interactions (cluster-robust SE)")
print("═"*78)

# C1. Interaction-term GLMs
INTERACTIONS = [
    ("Vonoprazan × East Asia",
     f"{BASE} + Is_East_Asia + Is_Vonoprazan:Is_East_Asia",
     "Is_Vonoprazan:Is_East_Asia"),
    ("Vonoprazan × High CLR region",
     f"{BASE} + Is_High_CLR_Region + Is_Vonoprazan:Is_High_CLR_Region",
     "Is_Vonoprazan:Is_High_CLR_Region"),
    ("Susceptibility-guided × East Asia",
     f"Successes + Failures ~ Is_Susceptibility_Guided + Is_East_Asia + "
     "Is_Susceptibility_Guided:Is_East_Asia + Is_Vonoprazan + Is_Quadruple + Duration_Days",
     "Is_Susceptibility_Guided:Is_East_Asia"),
    ("Duration × Is_Dual",
     f"Successes + Failures ~ Duration_Days + Is_Dual + Duration_Days:Is_Dual + "
     "Is_Vonoprazan + Is_Quadruple + CLR_Resistance_pct",
     "Duration_Days:Is_Dual"),
]

print(f"\n{'Interaction':<40} {'OR':>7} {'95% CI':>20} {'p-value':>8}")
print("-"*78)
interaction_results = []
for name, formula, term in INTERACTIONS:
    try:
        m = fit_glm(formula, df)
        or_pt = math.exp(m.params[term])
        ci = m.conf_int().loc[term]
        or_lo = math.exp(ci[0]); or_hi = math.exp(ci[1])
        p = m.pvalues[term]
        sig = "✓" if p < 0.05 else " "
        print(f"  {name:<38} {or_pt:>7.2f}  [{or_lo:>5.2f}, {or_hi:>5.2f}]  {p:>7.4f} {sig}")
        interaction_results.append((name, or_pt, or_lo, or_hi, p))
    except Exception as e:
        print(f"  {name:<38} FAILED: {e}")

# C2. Stratified analyses — vonoprazan OR within subgroups
print("\n── Stratified analyses (Vonoprazan OR in each subgroup) ──")
STRATA = [
    ("All arms",                  lambda d: d.copy()),
    ("East Asia only",            lambda d: d[d["Is_East_Asia"]==1].copy()),
    ("Non-East Asia",             lambda d: d[d["Is_East_Asia"]==0].copy()),
    ("High CLR region (≥30%)",    lambda d: d[d["Is_High_CLR_Region"]==1].copy()),
    ("Low CLR region (<30%)",     lambda d: d[d["Is_High_CLR_Region"]==0].copy()),
    ("Multicenter only",          lambda d: d[d["Is_Multicenter"]==1].copy()),
    ("Single center only",        lambda d: d[d["Is_Multicenter"]==0].copy()),
]

print(f"\n{'Stratum':<30} {'n_arms':>7} {'OR (Vono)':>10} {'95% CI':>20}")
print("-"*72)
strata_results = []
for name, filt in STRATA:
    sub = filt(df)
    n_v = int(sub["Is_Vonoprazan"].sum())
    if len(sub) < 10 or n_v < 3:
        print(f"  {name:<28} {len(sub):>7} (too few — skipped)")
        continue
    try:
        m = fit_glm(BASE, sub)
        if "Is_Vonoprazan" not in m.params.index:
            print(f"  {name:<28} {len(sub):>7} (no vono variance — skipped)")
            continue
        or_pt = math.exp(m.params["Is_Vonoprazan"])
        ci = m.conf_int().loc["Is_Vonoprazan"]
        or_lo = math.exp(ci[0]); or_hi = math.exp(ci[1])
        print(f"  {name:<28} {len(sub):>7} {or_pt:>10.2f}  [{or_lo:>5.2f}, {or_hi:>5.2f}]")
        strata_results.append((name, len(sub), or_pt, or_lo, or_hi))
    except Exception as e:
        print(f"  {name:<28} {len(sub):>7} FAILED: {e}")

# Subgroup forest plot
fig, ax = plt.subplots(figsize=(9, max(4, len(strata_results)*0.5 + 1.5)))
ys = range(len(strata_results))
ors = [r[2] for r in strata_results]
los = [r[3] for r in strata_results]
his = [r[4] for r in strata_results]
labels = [f"{r[0]} (n={r[1]})" for r in strata_results]
ax.errorbar(ors, ys,
            xerr=[[o-l for o,l in zip(ors,los)], [h-o for o,h in zip(ors,his)]],
            fmt="o", color="#1565C0", capsize=4, markersize=8)
ax.axvline(1.0, color="red", linestyle="--", linewidth=1.0, alpha=0.7)
ax.set_yticks(list(ys)); ax.set_yticklabels(labels, fontsize=10)
ax.set_xscale("log")
ax.set_xlabel("Vonoprazan OR (cluster-robust 95% CI)", fontsize=11)
ax.set_title("Subgroup forest — vonoprazan effect across strata", fontweight="bold")
ax.grid(axis="x", alpha=0.3)
plt.tight_layout()
plt.savefig(f"{FIG}/subgroup_forest.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"\n✓ {FIG}/subgroup_forest.png")

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  D — SENSITIVITY ANALYSES                                                  ║
# ╚════════════════════════════════════════════════════════════════════════════╝

print("\n" + "═"*78)
print("TIER D — Sensitivity analyses (drop categories, refit GLM)")
print("═"*78)

SENSITIVITY = [
    ("Main analysis (no exclusion)", lambda d: d.copy()),
    ("Drop quality-flagged",
     lambda d: d[d["Quality_Flags"].fillna("").str.strip() == ""].copy()),
    ("Drop susceptibility-guided",
     lambda d: d[d["Is_Susceptibility_Guided"] == 0].copy()),
    ("Drop regional-estimate resistance",
     lambda d: d[d["Resistance_Source_Type"] == "in-paper"].copy()),
    ("Drop small arms (N_ITT < 50)",
     lambda d: d[d["N_ITT"] >= 50].copy()),
    ("Drop dropout-heavy arms",
     lambda d: d[~d["Quality_Flags"].fillna("").str.contains("dropout-heavy", case=False)].copy()),
]

print(f"\n{'Sensitivity exclusion':<35} {'n':>5} {'studies':>8} {'OR (Vono)':>10} {'95% CI':>20}")
print("-"*82)
sensitivity_results = []
for name, filt in SENSITIVITY:
    sub = filt(df)
    if len(sub) < 15 or int(sub["Is_Vonoprazan"].sum()) < 3:
        print(f"  {name:<33} {len(sub):>5} (too few — skipped)")
        continue
    try:
        m = fit_glm(BASE, sub)
        or_pt = math.exp(m.params["Is_Vonoprazan"])
        ci = m.conf_int().loc["Is_Vonoprazan"]
        or_lo = math.exp(ci[0]); or_hi = math.exp(ci[1])
        n_studies = sub["Ref"].nunique()
        print(f"  {name:<33} {len(sub):>5} {n_studies:>8} {or_pt:>10.2f}  [{or_lo:>5.2f}, {or_hi:>5.2f}]")
        sensitivity_results.append((name, len(sub), or_pt, or_lo, or_hi))
    except Exception as e:
        print(f"  {name:<33} FAILED: {e}")

# Sensitivity forest plot
fig, ax = plt.subplots(figsize=(9, max(4, len(sensitivity_results)*0.5 + 1.5)))
ys = range(len(sensitivity_results))
ors = [r[2] for r in sensitivity_results]
los = [r[3] for r in sensitivity_results]
his = [r[4] for r in sensitivity_results]
labels = [f"{r[0]} (n={r[1]})" for r in sensitivity_results]
ax.errorbar(ors, ys,
            xerr=[[o-l for o,l in zip(ors,los)], [h-o for o,h in zip(ors,his)]],
            fmt="s", color="#388E3C", capsize=4, markersize=8)
ax.axvline(1.0, color="red", linestyle="--", linewidth=1.0, alpha=0.7)
ax.set_yticks(list(ys)); ax.set_yticklabels(labels, fontsize=10)
ax.set_xscale("log")
ax.set_xlabel("Vonoprazan OR (cluster-robust 95% CI)", fontsize=11)
ax.set_title("Sensitivity forest — vonoprazan OR drift under exclusions", fontweight="bold")
ax.grid(axis="x", alpha=0.3)
plt.tight_layout()
plt.savefig(f"{FIG}/sensitivity_forest.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"\n✓ {FIG}/sensitivity_forest.png")

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  E — HETEROGENEITY + PUBLICATION BIAS                                      ║
# ╚════════════════════════════════════════════════════════════════════════════╝

print("\n" + "═"*78)
print("TIER E — Heterogeneity statistics (Cochran Q, τ², I²)")
print("═"*78)

# Build study-level effect sizes for heterogeneity analysis.
# Use the difference in logit-eradication between vonoprazan arm and comparator arm
# within each study (where both exist). This is the standard pairwise meta-analysis input.
study_effects = []
for ref, gdf in df.groupby("Ref"):
    if len(gdf) < 2: continue
    vono_arms = gdf[gdf["Is_Vonoprazan"] == 1]
    comp_arms = gdf[gdf["Is_Vonoprazan"] == 0]
    if len(vono_arms) == 0 or len(comp_arms) == 0: continue
    v = vono_arms.iloc[0]
    c = comp_arms.iloc[0]
    # log-OR with continuity correction
    a = v["Successes"] + 0.5; b = v["Failures"] + 0.5
    cc = c["Successes"] + 0.5; d = c["Failures"] + 0.5
    log_or = math.log((a*d)/(b*cc))
    se_log_or = math.sqrt(1/a + 1/b + 1/cc + 1/d)
    study_effects.append({"Ref": ref, "log_or": log_or, "se": se_log_or})

eff_df = pd.DataFrame(study_effects)
print(f"\n  {len(eff_df)} studies with paired Vonoprazan vs Comparator arms")

# Random-effects meta-analysis (DerSimonian-Laird)
weights_fixed = 1 / eff_df["se"]**2
theta_fixed = (weights_fixed * eff_df["log_or"]).sum() / weights_fixed.sum()

# Cochran Q
Q = (weights_fixed * (eff_df["log_or"] - theta_fixed)**2).sum()
k = len(eff_df)
dof = k - 1
p_Q = 1 - sm.stats.stattools.chi2.cdf(Q, dof) if False else None  # avoid scipy fallback
# Compute manually with scipy stats
from scipy import stats as scipy_stats
p_Q = 1 - scipy_stats.chi2.cdf(Q, dof)

# DerSimonian-Laird tau²
C = weights_fixed.sum() - (weights_fixed**2).sum() / weights_fixed.sum()
tau2 = max(0, (Q - dof) / C) if C > 0 else 0

# I² = (Q - df) / Q  (clipped to [0,100])
I2 = max(0, 100 * (Q - dof) / Q) if Q > 0 else 0

# Random-effects re-weighted estimate
weights_re = 1 / (eff_df["se"]**2 + tau2)
theta_re = (weights_re * eff_df["log_or"]).sum() / weights_re.sum()
se_re = math.sqrt(1 / weights_re.sum())
or_re = math.exp(theta_re)
or_re_lo = math.exp(theta_re - 1.96*se_re)
or_re_hi = math.exp(theta_re + 1.96*se_re)

print(f"\n  Random-effects meta-analysis (DerSimonian-Laird):")
print(f"    Pooled OR (Vonoprazan vs comparator): {or_re:.2f}  [{or_re_lo:.2f}, {or_re_hi:.2f}]")
print(f"\n  Heterogeneity:")
print(f"    Cochran Q      = {Q:.2f}  (df={dof}, p={p_Q:.4f})")
print(f"    τ² (DL)         = {tau2:.4f}")
print(f"    I²              = {I2:.1f}%  ({'low' if I2<25 else 'moderate' if I2<60 else 'high'})")

# Publication bias — funnel plot + Egger regression
fig, ax = plt.subplots(figsize=(8, 7))
ax.scatter(eff_df["log_or"], 1/eff_df["se"], s=50, alpha=0.7,
           color="#1565C0", edgecolors="white", label="Studies")
ax.axvline(theta_re, color="red", linestyle="--", linewidth=1.2,
           label=f"Pooled log-OR = {theta_re:.2f}")
ax.set_xlabel("log Odds Ratio (Vonoprazan vs comparator)", fontsize=11)
ax.set_ylabel("Precision (1/SE)", fontsize=11)
ax.set_title("Funnel plot — vonoprazan vs comparator across studies",
             fontweight="bold")
ax.legend(fontsize=10); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(f"{FIG}/funnel_plot.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"\n✓ {FIG}/funnel_plot.png")

# Egger regression: standardised effect on precision
X_egger = 1 / eff_df["se"]
y_egger = eff_df["log_or"] / eff_df["se"]  # standardised
X_egger_with_const = sm.add_constant(X_egger)
egger_model = sm.OLS(y_egger, X_egger_with_const).fit()
egger_intercept = egger_model.params["const"]
egger_p = egger_model.pvalues["const"]
print(f"\n  Egger's regression intercept: {egger_intercept:.3f}  (p={egger_p:.4f})")
print(f"    Egger intercept significantly ≠ 0: "
      f"{'YES — small-study effect/bias detected' if egger_p < 0.10 else 'no — no strong asymmetry'}")

# PRISMA flow diagram
fig, ax = plt.subplots(figsize=(13, 12.5))
ax.set_xlim(0, 14); ax.set_ylim(0, 12)
ax.axis("off")
def box(x, y, w, h, text, color="#E1F5FE", fontsize=10, fontweight="normal"):
    rect = plt.Rectangle((x-w/2, y-h/2), w, h, facecolor=color,
                          edgecolor="black", linewidth=1.0)
    ax.add_patch(rect)
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
            fontweight=fontweight, wrap=True)

# Geometry: center column boxes centered at x=5.5. Pink boxes centered at x=11, width 2.4.

# Top — two-source identification
box(2.7, 11.4, 4.5, 0.8,
    "Source 1 (seed):\nTaufiqqurrachman 2026\nNetwork meta-analysis\n51 RCTs",
    "#FFF9C4", 9, "bold")
box(8.3, 11.4, 4.5, 0.8,
    "Source 2 (supplementary):\nPubMed searches (5 queries)\n2010–2025\n~45 additional records",
    "#FFF9C4", 9, "bold")
ax.annotate("", xy=(5.5, 10.4), xytext=(2.7, 11.0), arrowprops=dict(arrowstyle="->", lw=1.5))
ax.annotate("", xy=(5.5, 10.4), xytext=(8.3, 11.0), arrowprops=dict(arrowstyle="->", lw=1.5))

box(5.5, 10.0, 5, 0.7, "Combined records identified\n(~96 unique after merging sources)",
    "#FFF9C4", 10, "bold")
ax.annotate("", xy=(5.5, 9.1), xytext=(5.5, 9.65), arrowprops=dict(arrowstyle="->", lw=1.5))

box(5.5, 8.7, 5, 0.7, "Duplicates removed (n=4)\n→ 92 unique records")
ax.annotate("", xy=(5.5, 7.8), xytext=(5.5, 8.35), arrowprops=dict(arrowstyle="->", lw=1.5))

# Screening
box(5.5, 7.3, 5, 0.7, "Title/abstract screening\n92 records screened",
    "#FFF9C4", 10, "bold")
ax.annotate("", xy=(5.5, 6.4), xytext=(5.5, 6.95), arrowprops=dict(arrowstyle="->", lw=1.5))
ax.annotate("", xy=(9.8, 7.3), xytext=(8.0, 7.3), arrowprops=dict(arrowstyle="->", lw=1.5))
box(11.0, 7.3, 2.4, 0.7, "Excluded n=14\n(reviews, non-RCT)",
    "#FFCDD2", 8)

box(5.5, 6.0, 5, 0.7, "Full-text reviewed\n78 records", "#FFF9C4", 10, "bold")
ax.annotate("", xy=(5.5, 5.1), xytext=(5.5, 5.65), arrowprops=dict(arrowstyle="->", lw=1.5))
ax.annotate("", xy=(9.8, 6.0), xytext=(8.0, 6.0), arrowprops=dict(arrowstyle="->", lw=1.5))
box(11.0, 6.0, 2.4, 1.1, "Excluded n=15\n• adjunct dietary\n• pediatric\n• rescue only\n• retrospective",
    "#FFCDD2", 8)

box(5.5, 4.7, 5, 0.7, "63 studies included in synthesis\n(146 arms total)",
    "#C8E6C9", 11, "bold")
ax.annotate("", xy=(5.5, 3.8), xytext=(5.5, 4.35), arrowprops=dict(arrowstyle="->", lw=1.5))
ax.annotate("", xy=(9.8, 4.7), xytext=(8.0, 4.7), arrowprops=dict(arrowstyle="->", lw=1.5))
box(11.0, 4.7, 2.4, 1.1, "Excluded:\nRef 38 (protocol)\nRefs 40, 73, 75\n(microbiome)\n2 arms no ITT",
    "#FFCDD2", 8)

box(5.5, 3.2, 5.5, 0.8, "Final analyzed cohort:\n144 arms · 62 studies · 18,264 patients",
    "#A5D6A7", 12, "bold")
ax.annotate("", xy=(5.5, 2.3), xytext=(5.5, 2.8), arrowprops=dict(arrowstyle="->", lw=1.5))

# Analytical layers
box(3.0, 1.7, 4, 0.6, "Tier 1: Weighted ElasticNet ML", "#BBDEFB", 10)
box(8.0, 1.7, 4, 0.6, "Tier 2: Binomial GLM + cluster-robust SE", "#BBDEFB", 10)
box(3.0, 0.9, 4, 0.6, "Tier 3: Beta regression", "#BBDEFB", 10)
box(8.0, 0.9, 4, 0.6, "Tier B: Bayesian hierarchical", "#BBDEFB", 10)
box(5.5, 0.2, 6, 0.5, "Tier C-E: subgroup × sensitivity × heterogeneity", "#BBDEFB", 10)

ax.set_title("PRISMA-style flow diagram — H. pylori meta-analysis pipeline",
             fontsize=13, fontweight="bold", pad=15)
plt.tight_layout()
plt.savefig(f"{FIG}/prisma_flow.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"✓ {FIG}/prisma_flow.png")

# ── Write text report ────────────────────────────────────────────────────────
with open(f"{RPT}/sensitivity_results.txt", "w", encoding="utf-8") as f:
    f.write("Tier C-E — Publication-grade analyses\n")
    f.write("="*70 + "\n\n")

    f.write("── Subgroup × treatment interactions (cluster-robust SE) ──\n")
    for name, or_pt, or_lo, or_hi, p in interaction_results:
        sig = " *" if p < 0.05 else "  "
        f.write(f"  {name:<40} OR={or_pt:.2f}  [{or_lo:.2f}, {or_hi:.2f}]  p={p:.4f}{sig}\n")

    f.write("\n── Stratified analyses (Vonoprazan OR within subgroups) ──\n")
    for name, n, or_pt, or_lo, or_hi in strata_results:
        f.write(f"  {name:<28} n={n:>3}  OR={or_pt:.2f}  [{or_lo:.2f}, {or_hi:.2f}]\n")

    f.write("\n── Sensitivity analyses (drop categories) ──\n")
    for name, n, or_pt, or_lo, or_hi in sensitivity_results:
        f.write(f"  {name:<35} n={n:>3}  OR={or_pt:.2f}  [{or_lo:.2f}, {or_hi:.2f}]\n")

    f.write(f"\n── Heterogeneity (vonoprazan vs comparator, {len(eff_df)} paired studies) ──\n")
    f.write(f"  Pooled OR (random-effects): {or_re:.2f}  [{or_re_lo:.2f}, {or_re_hi:.2f}]\n")
    f.write(f"  Cochran Q:     {Q:.2f}  (df={dof}, p={p_Q:.4f})\n")
    f.write(f"  τ² (DL):       {tau2:.4f}\n")
    f.write(f"  I²:            {I2:.1f}%\n")
    f.write(f"\n── Publication bias (Egger regression) ──\n")
    f.write(f"  Egger intercept: {egger_intercept:.3f}  (p={egger_p:.4f})\n")

print(f"\n✓ {RPT}/sensitivity_results.txt")
print("\n✓ Tier C-E complete.")
