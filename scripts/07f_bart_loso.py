"""Compute BART LOSO continuous predictions (one fit per held-out study)."""
import os, time, warnings, pickle
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
import pymc as pm, pymc_bart as pmb
from sklearn.impute import SimpleImputer

IN = "project/data/processed/clean_dataset.csv"
MDL = "project/models"
with open(f"{MDL}/feature_names_pretreat.pkl", "rb") as f:
    FEATURES = pickle.load(f)
df = pd.read_csv(IN).dropna(subset=["ITT_Rate","N_ITT","Successes_ITT"]).reset_index(drop=True)
X = SimpleImputer(strategy="median").fit_transform(df[FEATURES].apply(pd.to_numeric, errors="coerce").values.astype(float))
y = df["ITT_Rate"].values.astype(float)
g = df["Ref"].astype(int).values
n = len(y)
studies = sorted(set(g))

out = f"{MDL}/bart_loso_ypred.npy"
preds = np.full(n, np.nan)
if os.path.isfile(out):
    preds = np.load(out)
    print(f"  resumed: {(~np.isnan(preds)).sum()}/{n} done", flush=True)

t0 = time.time()
for i, held in enumerate(studies):
    test_mask = (g == held)
    if not np.isnan(preds[test_mask]).any():
        continue
    tr = ~test_mask
    X_tr = X[tr]; y_tr = y[tr]; X_te = X[test_mask]
    try:
        with pm.Model():
            mu_t = pmb.BART("mu", X_tr, y_tr, m=20, shape=len(y_tr))
            sigma_t = pm.HalfNormal("sigma", sigma=10)
            pm.Normal("obs", mu=mu_t, sigma=sigma_t, observed=y_tr)
            id_t = pm.sample(draws=200, tune=200, chains=1, cores=1,
                              random_seed=42, progressbar=False,
                              compute_convergence_checks=False)
        mu_post = id_t.posterior["mu"].values.mean(axis=(0,1))
        for j, x_te in enumerate(X_te):
            dists = np.linalg.norm(X_tr - x_te, axis=1)
            preds[np.where(test_mask)[0][j]] = mu_post[np.argmin(dists)]
    except Exception as e:
        preds[test_mask] = np.mean(y_tr)
    pct = (i+1)/len(studies)
    bar = "█"*int(40*pct) + "░"*(40-int(40*pct))
    elapsed = time.time()-t0
    eta = elapsed/(i+1) * (len(studies)-i-1)
    print(f"  [{bar}] {i+1:2d}/{len(studies)} ({pct*100:5.1f}%)  elapsed {elapsed/60:.1f}m  ETA {eta/60:.1f}m", flush=True)
    if (i+1) % 5 == 0:
        np.save(out, preds)
np.save(out, preds)

# Metrics
from sklearn.metrics import mean_squared_error, r2_score
import math
mask = ~np.isnan(preds)
print(f"\n  BART LOSO: RMSE={math.sqrt(mean_squared_error(y[mask], preds[mask])):.2f}, R²={r2_score(y[mask], preds[mask]):+.3f}")
