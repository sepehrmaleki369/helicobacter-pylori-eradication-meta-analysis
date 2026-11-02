"""
Compute true LOO-arm R² for the Bayesian hierarchical model.
Refits PyMC model on n-1 arms, predicts held-out arm using its study's
posterior intercept.

Reduced sampling settings (2 chains × 800 draws + 400 tune) keep total
runtime manageable: ~30s per fit × 144 arms ≈ 70 min.
"""
import os, math, time, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

import pymc as pm
import nutpie
from sklearn.metrics import mean_squared_error, r2_score

IN = "project/data/processed/clean_dataset.csv"
df = pd.read_csv(IN).dropna(subset=["ITT_Rate","N_ITT","Successes_ITT"]).reset_index(drop=True)
df["Successes"] = df["Successes_ITT"].astype(int)
df["N_ITT"]     = df["N_ITT"].astype(int)
df["Ref"]       = df["Ref"].astype(int)

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
CONT = ["Duration_Days","CLR_Resistance_pct","MTZ_Resistance_pct",
        "AMX_Resistance_pct","CLR_use_x_CLR_resistance",
        "Mean_Age_yr","Compliance_pct"]
for c in CONT:
    df[c + "_z"] = (df[c] - df[c].mean()) / df[c].std()
MODEL_FEAT = [c if c not in CONT else c + "_z" for c in FEATURES]

X     = df[MODEL_FEAT].astype(float).values
y_s   = df["Successes"].values.astype(int)
y_n   = df["N_ITT"].values.astype(int)
y_rate = df["ITT_Rate"].values
refs  = df["Ref"].values
unique_refs = sorted(set(refs))
ref_to_idx = {r:i for i,r in enumerate(unique_refs)}
study_idx = np.array([ref_to_idx[r] for r in refs])
n, p = X.shape
nS = len(unique_refs)

def fit_predict_loo_arm(hold_i):
    """Fit Bayesian model on n-1 arms; predict held-out arm using its study's RE."""
    mask = np.ones(n, bool); mask[hold_i] = False
    X_tr = X[mask]; y_s_tr = y_s[mask]; y_n_tr = y_n[mask]
    s_idx_tr = study_idx[mask]
    held_study = study_idx[hold_i]
    held_x = X[hold_i]

    with pm.Model() as m:
        betas = pm.Normal("betas", mu=0, sigma=2, shape=p)
        intercept = pm.Normal("intercept", mu=0, sigma=3)
        sigma_study = pm.HalfNormal("sigma_study", sigma=1)
        alpha_study = pm.Normal("alpha_study", mu=0, sigma=sigma_study, shape=nS)
        logit_p = intercept + alpha_study[s_idx_tr] + pm.math.dot(X_tr, betas)
        pm.Binomial("obs", n=y_n_tr, p=pm.math.sigmoid(logit_p), observed=y_s_tr)
        compiled = nutpie.compile_pymc_model(m)
    trace = nutpie.sample(compiled, draws=800, tune=400, chains=2,
                          seed=42, progress_bar=False)
    # Posterior predictive for held-out arm using its study intercept
    posterior = trace.posterior
    intc = posterior["intercept"].values.flatten()  # (S,)
    bts  = posterior["betas"].values.reshape(-1, p)  # (S, p)
    alpha = posterior["alpha_study"].values.reshape(-1, nS)[:, held_study]  # (S,)
    logit = intc + alpha + bts @ held_x  # (S,)
    p_post = 1 / (1 + np.exp(-logit))
    return float(p_post.mean() * 100)  # ITT rate as %

import sys
out_path = "project/models/bayes_loo_arm_ypred.npy"

print(f"Computing LOO-arm Bayesian predictions for {n} arms ...", flush=True)
# Resume from checkpoint if exists
if os.path.isfile(out_path):
    preds = np.load(out_path)
    done_n = int((~np.isnan(preds)).sum())
    print(f"  resumed from checkpoint: {done_n}/{n} already done", flush=True)
else:
    preds = np.full(n, np.nan)
    done_n = 0
t0 = time.time()
for i in range(n):
    if not np.isnan(preds[i]):
        continue  # skip already-computed arms
    try:
        preds[i] = fit_predict_loo_arm(i)
    except Exception as e:
        print(f"  arm {i} failed: {e}", flush=True)
    elapsed = time.time() - t0
    done_n += 1
    bar_pct = (i+1) / n
    bar = "█" * int(40 * bar_pct) + "░" * (40 - int(40 * bar_pct))
    eta = elapsed / done_n * (n - (i+1))
    print(f"  [{bar}] {i+1:3d}/{n}  ({bar_pct*100:5.1f}%)  "
          f"elapsed {elapsed/60:5.1f}m  ETA {eta/60:5.1f}m", flush=True)
    if (i+1) % 5 == 0:  # checkpoint every 5 arms
        np.save(out_path, preds)
np.save(out_path, preds)

mask = ~np.isnan(preds)
rmse = math.sqrt(mean_squared_error(y_rate[mask], preds[mask]))
r2 = r2_score(y_rate[mask], preds[mask])
print(f"\n══ Bayesian LOO-arm ══")
print(f"  arms predicted: {mask.sum()}/{n}")
print(f"  RMSE = {rmse:.2f}%")
print(f"  R²   = {r2:+.3f}")
