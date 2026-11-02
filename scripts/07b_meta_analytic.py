"""
Phase 5b (Tier 2 + 3) — Meta-analytic models for arm-level eradication data.

Tier 2: Weighted binomial logistic GLM with cluster-robust SE on Ref,
        + cluster-bootstrap 95% CIs on key treatment-effect odds ratios.
Tier 3: Beta regression with N_ITT-based precision parametrisation.

LOSO predictions on proportion scale → Brier score, calibration comparison
against Tier-1 ElasticNet predictions.

Outputs:
  - project/figures/meta_*.png
  - project/report/meta_results.txt
  - console summary
"""
import csv, os, math, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")

import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.othermod.betareg import BetaModel
import patsy

IN  = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/data/processed/clean_dataset.csv"
FIG = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/figures"
MDL = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/models"
RPT = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/report"
os.makedirs(FIG, exist_ok=True)
os.makedirs(RPT, exist_ok=True)

# ── Load and prepare ──────────────────────────────────────────────────────────
df = pd.read_csv(IN)
df = df.dropna(subset=["ITT_Rate", "N_ITT", "Successes_ITT"]).copy()
df["Successes"] = df["Successes_ITT"].astype(int)
df["Failures"]  = (df["N_ITT"].astype(int) - df["Successes"]).clip(lower=0)
df["Ref"]       = df["Ref"].astype(int)

# Sanity F2.5
assert (df["Successes"] + df["Failures"]).sum() == df["N_ITT"].sum(), \
    "successes + failures != N_ITT"
print(f"Dataset: {len(df)} arms, {df['Ref'].nunique()} unique studies, "
      f"total patients={int(df['N_ITT'].sum())}")

# Numerics for formula
for c in ["Mean_Age_yr","Compliance_pct","CLR_Resistance_pct","MTZ_Resistance_pct",
          "AMX_Resistance_pct","LFX_Resistance_pct","CLR_use_x_CLR_resistance",
          "Duration_Days"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Median imputation for predictors used in formulas (statsmodels drops rows with NaN)
for c in ["Mean_Age_yr","Compliance_pct","CLR_Resistance_pct","MTZ_Resistance_pct",
          "AMX_Resistance_pct","LFX_Resistance_pct","CLR_use_x_CLR_resistance"]:
    med = df[c].median()
    df[c] = df[c].fillna(med)

# ── Two formulas (matches Tier 1's two model families) ───────────────────────
FORMULA_PRETREAT = (
    "Is_Vonoprazan + Is_Tegoprazan + Is_Dual + Is_Quadruple + Has_Bismuth + "
    "Has_Clarithromycin + Has_Metronidazole + Duration_Days + "
    "CLR_Resistance_pct + MTZ_Resistance_pct + AMX_Resistance_pct + "
    "CLR_use_x_CLR_resistance + Is_East_Asia + Mean_Age_yr + "
    "Is_Susceptibility_Guided"
)
FORMULA_FULL = FORMULA_PRETREAT + " + Compliance_pct"

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  TIER 2 — Binomial logistic GLM (Wald) + cluster-robust SE                 ║
# ╚════════════════════════════════════════════════════════════════════════════╝

def fit_binomial(formula, df, cluster=None):
    """Returns fitted GLM (binomial, logit link)."""
    f = "Successes + Failures ~ " + formula
    if cluster is None:
        return smf.glm(f, data=df, family=sm.families.Binomial()).fit()
    return smf.glm(f, data=df, family=sm.families.Binomial()).fit(
        cov_type="cluster", cov_kwds={"groups": df[cluster]})

print("\n" + "═"*78)
print("TIER 2A — Weighted Binomial Logistic GLM (Wald SE)")
print("═"*78)

results_t2 = {}
for fam_name, formula in [("pretreat", FORMULA_PRETREAT), ("full", FORMULA_FULL)]:
    glm_wald = fit_binomial(formula, df, cluster=None)
    glm_cluster = fit_binomial(formula, df, cluster="Ref")
    results_t2[fam_name] = {"wald": glm_wald, "cluster": glm_cluster}
    print(f"\n── Family: {fam_name} ──")
    print(f"  AIC: {glm_wald.aic:.1f}   Deviance: {glm_wald.deviance:.1f}   "
          f"df_resid: {int(glm_wald.df_resid)}")

# Print coefficient table comparison (Wald vs cluster-robust SE)
print("\n── Coefficient table (FULL family) ── Wald SE | Cluster-robust SE ─────────")
print(f"{'Term':<32} {'OR':>7} {'Wald-95%CI':>20} {'Cluster-95%CI':>20}")
print("-"*80)
glm_w = results_t2["full"]["wald"]
glm_c = results_t2["full"]["cluster"]
for term in glm_w.params.index:
    or_pt = math.exp(glm_w.params[term])
    ci_w  = glm_w.conf_int().loc[term]
    ci_c  = glm_c.conf_int().loc[term]
    print(f"  {term:<30} {or_pt:>7.2f}  "
          f"[{math.exp(ci_w[0]):>5.2f}, {math.exp(ci_w[1]):>5.2f}]  "
          f"[{math.exp(ci_c[0]):>5.2f}, {math.exp(ci_c[1]):>5.2f}]")

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  TIER 2B — Cluster bootstrap CIs on key effect sizes                        ║
# ╚════════════════════════════════════════════════════════════════════════════╝

print("\n" + "═"*78)
print("TIER 2B — Cluster bootstrap (resample studies, 2000 iter, FULL formula)")
print("═"*78)

def cluster_bootstrap(df, formula, n_iter=2000, seed=42):
    refs = df["Ref"].unique()
    f = "Successes + Failures ~ " + formula
    rng = np.random.default_rng(seed)
    boot = {"Is_Vonoprazan": [], "Is_Tegoprazan": [], "Duration_Days": [],
            "Is_Quadruple": [], "Has_Bismuth": [], "Is_East_Asia": [],
            "Compliance_pct": [], "CLR_Resistance_pct": []}
    converged = 0
    for _ in range(n_iter):
        sampled = rng.choice(refs, size=len(refs), replace=True)
        # Build bootstrapped df by concatenating selected refs' arms
        parts = [df[df["Ref"]==r] for r in sampled]
        bdf = pd.concat(parts, ignore_index=True)
        try:
            m = smf.glm(f, data=bdf, family=sm.families.Binomial()).fit(disp=0)
            for k in boot:
                if k in m.params.index:
                    boot[k].append(m.params[k])
            converged += 1
        except Exception:
            continue
    print(f"  Converged: {converged}/{n_iter} bootstraps")
    out = {}
    for k, vals in boot.items():
        if not vals: continue
        arr = np.array(vals)
        med  = np.exp(np.median(arr))
        lo, hi = np.exp(np.percentile(arr, [2.5, 97.5]))
        out[k] = {"OR_median": med, "lo": lo, "hi": hi, "n": len(arr)}
    return out

boot_results = cluster_bootstrap(df, FORMULA_FULL, n_iter=2000, seed=42)
print(f"\n{'Term':<28} {'OR median':>10} {'95% CI':>22}  {'n_boots':>8}")
print("-"*72)
for k, v in boot_results.items():
    print(f"  {k:<26} {v['OR_median']:>10.2f}  [{v['lo']:>5.2f}, {v['hi']:>5.2f}]   {v['n']:>8}")

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  TIER 2C — Leave-One-Study-Out predictions (proportion scale)              ║
# ╚════════════════════════════════════════════════════════════════════════════╝

print("\n" + "═"*78)
print("TIER 2C — LOSO predictions on proportion scale")
print("═"*78)

def loso_predict_glm(df, formula):
    f = "Successes + Failures ~ " + formula
    refs = df["Ref"].unique()
    pred = pd.Series(index=df.index, dtype=float)
    for r in refs:
        train = df[df["Ref"] != r]
        test  = df[df["Ref"] == r]
        try:
            m = smf.glm(f, data=train, family=sm.families.Binomial()).fit(disp=0)
            pred.loc[test.index] = m.predict(test)
        except Exception:
            pred.loc[test.index] = train["Successes"].sum() / train["N_ITT"].sum()
    return pred

glm_loso = {}
for fam_name, formula in [("pretreat", FORMULA_PRETREAT), ("full", FORMULA_FULL)]:
    p = loso_predict_glm(df, formula)
    obs = df["ITT_Prop"]
    rmse = math.sqrt(((p - obs)**2).mean())
    brier = ((p - obs)**2).mean()
    print(f"  GLM-binomial  family={fam_name}:  RMSE(prop)={rmse:.4f}   Brier={brier:.4f}")
    glm_loso[fam_name] = p.values

# Compare with Tier 1 ElasticNet predictions
try:
    en_full_loso     = np.load(f"{MDL}/elasticnet_full_loso_ypred.npy") / 100.0
    en_pretreat_loso = np.load(f"{MDL}/elasticnet_pretreat_loso_ypred.npy") / 100.0
    obs_arr = df["ITT_Prop"].values
    # The Tier-1 arrays match df order if rows align (same source CSV, same dropna)
    # They were built from the same clean_dataset.csv, same filters → same order
    if len(en_full_loso) == len(obs_arr):
        r_full = np.corrcoef(glm_loso["full"], en_full_loso)[0,1]
        r_pretreat = np.corrcoef(glm_loso["pretreat"], en_pretreat_loso)[0,1]
        print(f"\n  Correlation GLM-LOSO vs ElasticNet-LOSO:")
        print(f"    full     : r = {r_full:.3f}")
        print(f"    pretreat : r = {r_pretreat:.3f}")
    else:
        print(f"  (Skipping correlation: length mismatch n_glm={len(obs_arr)} vs n_en={len(en_full_loso)})")
except FileNotFoundError:
    print("  (Tier 1 ElasticNet predictions not found — run 07_model_building.py first)")

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  TIER 3 — Beta regression with N_ITT-based precision                       ║
# ╚════════════════════════════════════════════════════════════════════════════╝

print("\n" + "═"*78)
print("TIER 3 — Beta regression (Smithson-adjusted proportion)")
print("═"*78)

# Smithson & Verkuilen (2006) adjusted proportion: maps [0,1] -> (0,1)
n_total = len(df)
df["ITT_Prop_adj"] = (df["ITT_Prop"] * (n_total - 1) + 0.5) / n_total

results_t3 = {}
for fam_name, formula_mean in [("pretreat", FORMULA_PRETREAT), ("full", FORMULA_FULL)]:
    f_mean = "ITT_Prop_adj ~ " + formula_mean
    try:
        # Precision ~ N_ITT (more patients → higher precision)
        # patsy intercept + N_ITT
        exog_prec = patsy.dmatrix("N_ITT", df, return_type="dataframe")
        br = BetaModel.from_formula(f_mean, data=df, exog_precision=exog_prec).fit(disp=0)
        results_t3[fam_name] = br
        print(f"\n── Family: {fam_name} ──")
        print(f"  Converged: {br.mle_retvals.get('converged', 'unknown')}")
        # Predictions
        p_in = br.predict()
        print(f"  In-sample fit:  min={p_in.min():.3f}  max={p_in.max():.3f}  "
              f"(all in (0,1): {(0 < p_in.min() and p_in.max() < 1)})")
    except Exception as e:
        print(f"  Beta regression failed for {fam_name}: {e}")
        results_t3[fam_name] = None

# LOSO predictions for beta regression
def loso_predict_beta(df, formula_mean):
    f_mean = "ITT_Prop_adj ~ " + formula_mean
    refs = df["Ref"].unique()
    pred = pd.Series(index=df.index, dtype=float)
    for r in refs:
        train = df[df["Ref"] != r].copy()
        test  = df[df["Ref"] == r].copy()
        try:
            exog_prec_train = patsy.dmatrix("N_ITT", train, return_type="dataframe")
            m = BetaModel.from_formula(f_mean, data=train,
                                       exog_precision=exog_prec_train).fit(disp=0)
            pred.loc[test.index] = m.predict(test)
        except Exception:
            pred.loc[test.index] = train["ITT_Prop"].mean()
    return pred

print("\n── Beta regression LOSO predictions ──")
beta_loso = {}
for fam_name, formula in [("pretreat", FORMULA_PRETREAT), ("full", FORMULA_FULL)]:
    p = loso_predict_beta(df, formula)
    obs = df["ITT_Prop"]
    rmse = math.sqrt(((p - obs)**2).mean())
    brier = ((p - obs)**2).mean()
    print(f"  BetaReg  family={fam_name}:  RMSE(prop)={rmse:.4f}   Brier={brier:.4f}")
    beta_loso[fam_name] = p.values

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  CALIBRATION COMPARISON — all three methods on FULL family                 ║
# ╚════════════════════════════════════════════════════════════════════════════╝

print("\n" + "═"*78)
print("CALIBRATION COMPARISON  (LOSO, FULL family, proportion scale)")
print("═"*78)

obs = df["ITT_Prop"].values
methods = {
    "T1 ElasticNet": None,
    "T2 Binomial GLM": glm_loso["full"],
    "T3 Beta Regression": beta_loso["full"],
}
try:
    methods["T1 ElasticNet"] = en_full_loso
except NameError:
    pass

# Compute calibration metrics
def calibration_stats(obs, pred):
    """Fit linear regression obs ~ a + b*pred. Slope target=1, intercept target=0."""
    # ignore NaNs
    mask = np.isfinite(obs) & np.isfinite(pred)
    if mask.sum() < 5: return None
    o, p = obs[mask], pred[mask]
    n = len(o)
    p_mean, o_mean = p.mean(), o.mean()
    num = ((p - p_mean) * (o - o_mean)).sum()
    den = ((p - p_mean)**2).sum()
    slope = num/den if den else float("nan")
    intercept = o_mean - slope * p_mean
    rmse  = math.sqrt(((o-p)**2).mean())
    brier = ((o-p)**2).mean()
    return {"slope": slope, "intercept": intercept, "rmse": rmse, "brier": brier, "n": n}

print(f"\n{'Method':<22} {'RMSE':>7} {'Brier':>7} {'Cal-slope':>10} {'Cal-int':>10}")
print("-"*60)
calib = {}
for name, pred in methods.items():
    if pred is None: continue
    stats = calibration_stats(obs, pred)
    if stats:
        calib[name] = stats
        print(f"  {name:<20} {stats['rmse']:>7.4f} {stats['brier']:>7.4f} "
              f"{stats['slope']:>10.3f} {stats['intercept']:>10.3f}")

# ── Calibration plot ──────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7, 7))
colors = {"T1 ElasticNet": "#2196F3", "T2 Binomial GLM": "#E91E63",
          "T3 Beta Regression": "#4CAF50"}
for name, pred in methods.items():
    if pred is None: continue
    # Decile bin
    ord_idx = np.argsort(pred)
    n_bins = 10
    bins = np.array_split(ord_idx, n_bins)
    xs, ys = [], []
    for b in bins:
        xs.append(pred[b].mean())
        ys.append(obs[b].mean())
    ax.plot(xs, ys, "o-", color=colors[name], label=name, markersize=8, linewidth=2)
ax.plot([0, 1], [0, 1], "k--", linewidth=1.0, label="Perfect calibration")
ax.set_xlim(0.5, 1.0); ax.set_ylim(0.5, 1.0)
ax.set_xlabel("Predicted proportion (binned mean)", fontsize=11)
ax.set_ylabel("Observed proportion (binned mean)", fontsize=11)
ax.set_title("Calibration Plot — LOSO, FULL family\n(decile bins of predicted probability)",
             fontweight="bold")
ax.legend(fontsize=10); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(f"{FIG}/meta_calibration.png", dpi=150, bbox_inches="tight")
plt.close()
print("\n✓ meta_calibration.png")

# ── Forest plot of odds ratios (cluster-robust, FULL family) ─────────────────
glm_c = results_t2["full"]["cluster"]
KEY_TERMS = ["Is_Vonoprazan", "Is_Tegoprazan", "Is_Dual", "Is_Quadruple",
             "Has_Bismuth", "Has_Clarithromycin", "Duration_Days", "Is_East_Asia",
             "CLR_Resistance_pct", "Compliance_pct", "Mean_Age_yr"]
forest = []
for term in KEY_TERMS:
    if term in glm_c.params.index:
        or_pt = math.exp(glm_c.params[term])
        ci    = glm_c.conf_int().loc[term]
        forest.append((term, or_pt, math.exp(ci[0]), math.exp(ci[1])))

forest.sort(key=lambda x: x[1])
fig, ax = plt.subplots(figsize=(9, max(4, len(forest)*0.45 + 1.5)))
ys = range(len(forest))
labels_f = [t[0] for t in forest]
ors      = [t[1] for t in forest]
los      = [t[2] for t in forest]
his      = [t[3] for t in forest]
ax.errorbar(ors, ys, xerr=[[o-l for o,l in zip(ors,los)],
                            [h-o for o,h in zip(ors,his)]],
            fmt="o", color="#1565C0", capsize=4, markersize=7)
ax.axvline(1.0, color="red", linestyle="--", linewidth=1.0, alpha=0.7, label="OR=1 (no effect)")
ax.set_yticks(list(ys)); ax.set_yticklabels(labels_f, fontsize=10)
ax.set_xlabel("Odds ratio (cluster-robust 95% CI)", fontsize=11)
ax.set_title("Forest plot — Tier 2 Binomial GLM (FULL family)\nCluster-robust SE on study Ref",
             fontweight="bold")
ax.set_xscale("log")
ax.legend(fontsize=9); ax.grid(axis="x", alpha=0.3)
plt.tight_layout()
plt.savefig(f"{FIG}/meta_forest.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ meta_forest.png")

# ── Bootstrap forest plot ────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, max(4, len(boot_results)*0.5 + 1.5)))
boot_sorted = sorted(boot_results.items(), key=lambda kv: kv[1]["OR_median"])
ys = range(len(boot_sorted))
labels_b = [k for k,_ in boot_sorted]
ors      = [v["OR_median"] for _,v in boot_sorted]
los      = [v["lo"]        for _,v in boot_sorted]
his      = [v["hi"]        for _,v in boot_sorted]
ax.errorbar(ors, ys, xerr=[[o-l for o,l in zip(ors,los)],
                            [h-o for o,h in zip(ors,his)]],
            fmt="s", color="#9C27B0", capsize=4, markersize=7)
ax.axvline(1.0, color="red", linestyle="--", linewidth=1.0, alpha=0.7)
ax.set_yticks(list(ys)); ax.set_yticklabels(labels_b, fontsize=10)
ax.set_xlabel("Odds ratio (cluster-bootstrap 2.5–97.5%)", fontsize=11)
ax.set_title("Forest plot — Cluster-bootstrap 95% CIs (2000 iter)\nResampling studies, not arms",
             fontweight="bold")
ax.set_xscale("log")
ax.grid(axis="x", alpha=0.3)
plt.tight_layout()
plt.savefig(f"{FIG}/meta_bootstrap_forest.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ meta_bootstrap_forest.png")

# ── Write text report ────────────────────────────────────────────────────────
with open(f"{RPT}/meta_results.txt", "w", encoding="utf-8") as f:
    f.write("H. pylori meta-analytic models — Tier 2 + Tier 3 results\n")
    f.write("="*72 + "\n\n")
    f.write(f"Dataset: {len(df)} arms, {df['Ref'].nunique()} unique studies, "
            f"{int(df['N_ITT'].sum())} total patients\n\n")
    f.write("── Tier 2 Binomial GLM (FULL) — Coefficient table ──\n")
    f.write(str(results_t2["full"]["cluster"].summary()) + "\n\n")
    f.write("── Tier 2B Cluster bootstrap (FULL formula) ──\n")
    for k, v in boot_results.items():
        f.write(f"  {k:<28} OR={v['OR_median']:.2f}  [{v['lo']:.2f}, {v['hi']:.2f}]  n_boots={v['n']}\n")
    f.write("\n── Tier 3 Beta regression LOSO ──\n")
    for name, stats in calib.items():
        f.write(f"  {name:<22} RMSE={stats['rmse']:.4f}  Brier={stats['brier']:.4f}  "
                f"slope={stats['slope']:.3f}  int={stats['intercept']:.3f}\n")
print(f"\n✓ {RPT}/meta_results.txt")

# ── Decision rule for Tier 3 ──────────────────────────────────────────────────
print("\n" + "═"*78)
print("DECISION: which method to feature in the final report")
print("═"*78)
if "T2 Binomial GLM" in calib and "T3 Beta Regression" in calib:
    slope_t2 = calib["T2 Binomial GLM"]["slope"]
    slope_t3 = calib["T3 Beta Regression"]["slope"]
    if abs(slope_t3 - 1) < abs(slope_t2 - 1):
        print(f"  → Tier 3 Beta Regression has better calibration (|slope-1|={abs(slope_t3-1):.3f}"
              f" vs T2={abs(slope_t2-1):.3f}).  RECOMMEND Tier 3.")
    else:
        print(f"  → Tier 2 Binomial GLM has better calibration (|slope-1|={abs(slope_t2-1):.3f}"
              f" vs T3={abs(slope_t3-1):.3f}).  RECOMMEND Tier 2.")

print("\n✓ Tier 2 + 3 complete.")
