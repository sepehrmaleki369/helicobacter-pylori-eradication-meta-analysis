"""
Tier B (true Bayesian) — Hierarchical binomial logistic GLM with random intercept
by study (Ref). Uses PyMC model definition + nutpie (Rust-based) sampler to bypass
the macOS C++ compilation issue.

Model:
    successes_i ~ Binomial(N_i, p_i)
    logit(p_i) = α + α_study[ref(i)] + X_i β
    α_study[k] ~ Normal(0, σ_study)
    σ_study ~ HalfNormal(1)
    β ~ Normal(0, 2)
    α ~ Normal(0, 3)

This properly accounts for within-study correlation and gives posterior HDIs
that quantify epistemic uncertainty.

Outputs:
  - figures/bayes_forest.png
  - figures/bayes_traceplot.png
  - figures/bayes_calibration.png
  - report/bayes_results.txt
  - models/bayes_marginal_ypred.npy
"""
import os, math, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")

import pymc as pm
import nutpie
import arviz as az

IN  = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/data/processed/clean_dataset.csv"
FIG = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/figures"
MDL = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/models"
RPT = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/report"
os.makedirs(FIG, exist_ok=True); os.makedirs(RPT, exist_ok=True)

# ── Load & prepare ─────────────────────────────────────────────────────────────
df = pd.read_csv(IN)
df = df.dropna(subset=["ITT_Rate","N_ITT","Successes_ITT"]).reset_index(drop=True)
df["Successes"] = df["Successes_ITT"].astype(int)
df["N_ITT"]     = df["N_ITT"].astype(int)
df["Ref"]       = df["Ref"].astype(int)

# Clinical/inference feature set (matches 07b's curated set)
FEATURES = [
    "Is_Vonoprazan","Is_Tegoprazan","Is_Dual","Is_Quadruple","Has_Bismuth",
    "Has_Clarithromycin","Duration_Days",
    "CLR_Resistance_pct","MTZ_Resistance_pct","AMX_Resistance_pct",
    "CLR_use_x_CLR_resistance",
    "Is_East_Asia","Mean_Age_yr","Compliance_pct","Is_Susceptibility_Guided",
]
for c in FEATURES:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df[c] = df[c].fillna(df[c].median())

# Standardise continuous predictors so coefficients are interpretable
CONTINUOUS = ["Duration_Days","CLR_Resistance_pct","MTZ_Resistance_pct",
              "AMX_Resistance_pct","CLR_use_x_CLR_resistance",
              "Mean_Age_yr","Compliance_pct"]
means = {c: df[c].mean() for c in CONTINUOUS}
stds  = {c: df[c].std()  for c in CONTINUOUS}
for c in CONTINUOUS:
    df[c + "_z"] = (df[c] - means[c]) / stds[c]

MODEL_FEATURES = [
    "Is_Vonoprazan","Is_Tegoprazan","Is_Dual","Is_Quadruple","Has_Bismuth",
    "Has_Clarithromycin","Duration_Days_z",
    "CLR_Resistance_pct_z","MTZ_Resistance_pct_z","AMX_Resistance_pct_z",
    "CLR_use_x_CLR_resistance_z",
    "Is_East_Asia","Mean_Age_yr_z","Compliance_pct_z","Is_Susceptibility_Guided",
]

unique_refs = sorted(df["Ref"].unique())
ref_to_idx = {r: i for i, r in enumerate(unique_refs)}
df["study_idx"] = df["Ref"].map(ref_to_idx)

X = df[MODEL_FEATURES].astype(float).values
y_succ = df["Successes"].values.astype(int)
y_n    = df["N_ITT"].values.astype(int)
study_idx = df["study_idx"].values
n_studies = len(unique_refs)
n_arms, p = X.shape

print(f"Dataset: {n_arms} arms, {n_studies} studies, "
      f"total patients={int(y_n.sum())}, {p} fixed-effect predictors")

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  Bayesian hierarchical model (PyMC + nutpie)                               ║
# ╚════════════════════════════════════════════════════════════════════════════╝

print("\n── Building Bayesian hierarchical model ──")
with pm.Model() as model:
    # Fixed effects
    betas = pm.Normal("betas", mu=0, sigma=2, shape=p)
    intercept = pm.Normal("intercept", mu=0, sigma=3)

    # Random intercept by study (hierarchical)
    sigma_study = pm.HalfNormal("sigma_study", sigma=1)
    alpha_study = pm.Normal("alpha_study", mu=0, sigma=sigma_study, shape=n_studies)

    # Linear predictor + link
    logit_p = intercept + alpha_study[study_idx] + pm.math.dot(X, betas)
    p_arm = pm.Deterministic("p_arm", pm.math.invlogit(logit_p))

    # Likelihood
    obs = pm.Binomial("obs", n=y_n, p=p_arm, observed=y_succ)

print("── Compiling with nutpie (Rust sampler) ──")
compiled = nutpie.compile_pymc_model(model)

print("── Sampling: 4 chains × 1500 draws (1000 tune) ──")
idata = nutpie.sample(compiled,
                      draws=1500, tune=1000, chains=4,
                      target_accept=0.95, seed=42, progress_bar=False)

# ── Posterior summary ────────────────────────────────────────────────────────
summary = az.summary(idata, var_names=["betas","intercept","sigma_study"])
print("\n── Posterior summary ──")
print(summary)

rhat_max = float(summary["r_hat"].max())
ess_min  = float(summary["ess_bulk"].min())
print(f"\n  max r_hat = {rhat_max:.4f}  (target < 1.01)")
print(f"  min ESS    = {ess_min:.0f}  (target > 400)")

# Extract posterior draws
beta_post = idata.posterior["betas"].values.reshape(-1, p)  # (draws, p)
beta_mean = beta_post.mean(axis=0)
beta_hdi_lo = np.percentile(beta_post, 2.5, axis=0)
beta_hdi_hi = np.percentile(beta_post, 97.5, axis=0)

# Effect-size table (OR scale)
print(f"\n── Posterior effect sizes (OR scale; standardised continuous = OR per SD) ──")
print(f"{'Feature':<32} {'OR':>7} {'95% HDI':>22}  {'P(OR>1)':>8} {'sig?':>5}")
print("-"*78)
results_table = []
for i, feat in enumerate(MODEL_FEATURES):
    or_pt = math.exp(beta_mean[i])
    or_lo = math.exp(beta_hdi_lo[i])
    or_hi = math.exp(beta_hdi_hi[i])
    p_pos = float((beta_post[:, i] > 0).mean())
    sig = "✓" if (or_lo > 1 or or_hi < 1) else " "
    print(f"  {feat:<30} {or_pt:>7.2f}  [{or_lo:>5.2f}, {or_hi:>5.2f}]   {p_pos:>7.3f}  {sig:>4}")
    results_table.append((feat, or_pt, or_lo, or_hi, p_pos))

sigma_study_mean = float(idata.posterior["sigma_study"].mean())
sigma_study_hdi = np.percentile(idata.posterior["sigma_study"].values, [2.5, 97.5])
print(f"\n  σ_study (study-level SD on logit scale) = {sigma_study_mean:.3f}  "
      f"[{sigma_study_hdi[0]:.3f}, {sigma_study_hdi[1]:.3f}]")

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  Marginal predictions (study-effects integrated out) — for new studies    ║
# ╚════════════════════════════════════════════════════════════════════════════╝

beta_mu = beta_mean
intercept_mu = float(idata.posterior["intercept"].mean())
alpha_mu = idata.posterior["alpha_study"].values.mean(axis=(0,1))

# In-sample (with study random effects)
logit_in = intercept_mu + alpha_mu[study_idx] + X @ beta_mu
y_pred_in = 1 / (1 + np.exp(-logit_in))

# Marginalised (study-agnostic — for new studies)
logit_marg = intercept_mu + X @ beta_mu
y_pred_marg = 1 / (1 + np.exp(-logit_marg))

obs_prop = y_succ / y_n
rmse_in   = math.sqrt(((obs_prop - y_pred_in)**2).mean())
brier_in  = ((obs_prop - y_pred_in)**2).mean()
rmse_marg = math.sqrt(((obs_prop - y_pred_marg)**2).mean())
brier_marg = ((obs_prop - y_pred_marg)**2).mean()

# Calibration on marginal predictions
o = obs_prop; pr = y_pred_marg
slope = (((pr - pr.mean()) * (o - o.mean())).sum()
         / ((pr - pr.mean())**2).sum())
intercept_cal = o.mean() - slope * pr.mean()

print(f"\n── Posterior predictive fit ──")
print(f"  In-sample (with study REs):  RMSE={rmse_in:.4f}  Brier={brier_in:.4f}")
print(f"  Marginal (study-agnostic):   RMSE={rmse_marg:.4f}  Brier={brier_marg:.4f}")
print(f"  Marginal calibration slope:    {slope:.3f}  (target=1.0)")
print(f"  Marginal calibration intercept:{intercept_cal:.3f}  (target=0.0)")

np.save(f"{MDL}/bayes_marginal_ypred.npy", y_pred_marg)
np.save(f"{MDL}/bayes_in_sample_ypred.npy", y_pred_in)

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  FIGURES                                                                   ║
# ╚════════════════════════════════════════════════════════════════════════════╝

# Forest plot — posterior HDIs on OR scale
fig, ax = plt.subplots(figsize=(9, max(4, p*0.40 + 1.5)))
order = np.argsort([math.exp(beta_mean[i]) for i in range(p)])
ys = range(p)
ors = [math.exp(beta_mean[i]) for i in order]
los = [math.exp(beta_hdi_lo[i]) for i in order]
his = [math.exp(beta_hdi_hi[i]) for i in order]
labels = [MODEL_FEATURES[i].replace("_z","") for i in order]
# Color significant effects darker
colors = ["#5E35B1" if (los[i] > 1 or his[i] < 1) else "#B39DDB"
          for i in range(p)]
for i, (o, l, h, c) in enumerate(zip(ors, los, his, colors)):
    ax.errorbar([o], [i], xerr=[[o-l], [h-o]],
                fmt="o", color=c, capsize=4, markersize=8,
                ecolor=c, elinewidth=2)
ax.axvline(1.0, color="red", linestyle="--", linewidth=1.0, alpha=0.7,
           label="OR=1 (no effect)")
ax.set_yticks(list(ys)); ax.set_yticklabels(labels, fontsize=10)
ax.set_xscale("log")
ax.set_xlabel("Posterior odds ratio (95% HDI)", fontsize=11)
ax.set_title(f"Bayesian hierarchical GLM — fixed effects\n"
             f"σ_study = {sigma_study_mean:.2f} [{sigma_study_hdi[0]:.2f}, {sigma_study_hdi[1]:.2f}] · "
             f"max r̂ = {rhat_max:.3f}", fontweight="bold")
ax.legend(fontsize=9); ax.grid(axis="x", alpha=0.3)
plt.tight_layout()
plt.savefig(f"{FIG}/bayes_forest.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"\n✓ {FIG}/bayes_forest.png")

# Traceplot — diagnostics
az.plot_trace(idata, var_names=["betas","sigma_study","intercept"], compact=True)
plt.suptitle("Bayesian hierarchical GLM — MCMC trace diagnostics",
             fontweight="bold", y=1.01)
plt.tight_layout()
plt.savefig(f"{FIG}/bayes_traceplot.png", dpi=130, bbox_inches="tight")
plt.close()
print(f"✓ {FIG}/bayes_traceplot.png")

# Calibration plot — compare in-sample, marginal, and Tier-1 ElasticNet
fig, ax = plt.subplots(figsize=(8, 7))
methods = {"Bayesian (with RE)":  y_pred_in,
           "Bayesian (marginal)": y_pred_marg}
try:
    en_loso = np.load(f"{MDL}/elasticnet_pretreat_loso_ypred.npy") / 100.0
    if len(en_loso) == len(obs_prop):
        methods["T1 ElasticNet (LOSO)"] = en_loso
except FileNotFoundError:
    pass

colors_map = {"Bayesian (with RE)":"#1B5E20",
              "Bayesian (marginal)":"#5E35B1",
              "T1 ElasticNet (LOSO)":"#2196F3"}
for name, pred in methods.items():
    ord_idx = np.argsort(pred)
    bins = np.array_split(ord_idx, 10)
    xs, ysp = [], []
    for b in bins:
        xs.append(pred[b].mean()); ysp.append(obs_prop[b].mean())
    ax.plot(xs, ysp, "o-", color=colors_map.get(name, "gray"), label=name,
            markersize=8, linewidth=2)
ax.plot([0,1],[0,1], "k--", linewidth=1.0, label="Perfect")
ax.set_xlim(0.5, 1.0); ax.set_ylim(0.5, 1.0)
ax.set_xlabel("Predicted proportion (decile bins)", fontsize=11)
ax.set_ylabel("Observed proportion", fontsize=11)
ax.set_title(f"Calibration — Bayesian hierarchical vs Tier 1\n"
             f"Bayes marginal: Brier={brier_marg:.4f}, slope={slope:.3f}",
             fontweight="bold")
ax.legend(fontsize=10); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(f"{FIG}/bayes_calibration.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"✓ {FIG}/bayes_calibration.png")

# ── Write text report ───────────────────────────────────────────────────────
with open(f"{RPT}/bayes_results.txt", "w", encoding="utf-8") as f:
    f.write("Tier B — Bayesian hierarchical binomial GLM (true Bayesian via PyMC + nutpie)\n")
    f.write("="*78 + "\n\n")
    f.write(f"Dataset: {n_arms} arms, {n_studies} studies, "
            f"total patients={int(y_n.sum())}\n")
    f.write(f"Sampler: nutpie (Rust-based; avoids macOS C++ issue)\n")
    f.write(f"MCMC: 4 chains × 1500 draws (1000 tune), target_accept=0.95\n\n")
    f.write(f"Diagnostics: max r_hat = {rhat_max:.4f}  (target<1.01)\n")
    f.write(f"             min ESS    = {ess_min:.0f}  (target>400)\n\n")
    f.write(f"σ_study posterior = {sigma_study_mean:.3f}  "
            f"[{sigma_study_hdi[0]:.3f}, {sigma_study_hdi[1]:.3f}]\n\n")
    f.write("── Posterior effect sizes (binary as OR; standardised as OR per SD) ──\n")
    f.write(f"{'Feature':<32} {'OR':>7} {'95% HDI':>22}  {'P(OR>1)':>8}\n")
    for feat, or_pt, or_lo, or_hi, p_pos in results_table:
        sig = " *" if (or_lo > 1 or or_hi < 1) else "  "
        f.write(f"  {feat:<30} {or_pt:>7.2f}  [{or_lo:>5.2f}, {or_hi:>5.2f}]   {p_pos:>7.3f}{sig}\n")
    f.write(f"\n── Posterior predictive fit ──\n")
    f.write(f"  In-sample (with study REs):  RMSE={rmse_in:.4f}  Brier={brier_in:.4f}\n")
    f.write(f"  Marginal (study-agnostic):   RMSE={rmse_marg:.4f}  Brier={brier_marg:.4f}\n")
    f.write(f"  Marginal calibration slope:    {slope:.3f}\n")
    f.write(f"  Marginal calibration intercept:{intercept_cal:.3f}\n")

print(f"\n✓ {RPT}/bayes_results.txt")
print("\n✓ Tier B (true Bayesian hierarchical via nutpie) complete.")
