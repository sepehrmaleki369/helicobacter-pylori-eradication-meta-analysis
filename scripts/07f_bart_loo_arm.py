"""
Compute true LOO-arm R² for BART (Bayesian Additive Regression Trees).
Refits BART on n-1 arms, predicts held-out arm by nearest-neighbour
in feature space (BART's standard prediction approach for held-out points).
"""
import os, math, time, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

import pymc as pm
import pymc_bart as pmb
import pickle
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_squared_error, r2_score

IN = "project/data/processed/clean_dataset.csv"
MDL = "project/models"

with open(f"{MDL}/feature_names_pretreat.pkl", "rb") as f:
    FEATURES = pickle.load(f)

df = pd.read_csv(IN).dropna(subset=["ITT_Rate","N_ITT","Successes_ITT"]).reset_index(drop=True)
X_raw = df[FEATURES].apply(pd.to_numeric, errors="coerce").values.astype(float)
X = SimpleImputer(strategy="median").fit_transform(X_raw)
y = df["ITT_Rate"].values.astype(float)
n = len(y)
print(f"BART LOO-arm: {n} arms, {X.shape[1]} features")

out_path = f"{MDL}/bart_loo_arm_ypred.npy"
print(f"Computing LOO-arm BART predictions for {n} arms ...", flush=True)
if os.path.isfile(out_path):
    preds = np.load(out_path)
    done = int((~np.isnan(preds)).sum())
    print(f"  resumed from checkpoint: {done}/{n} already done", flush=True)
else:
    preds = np.full(n, np.nan)
    done = 0
t0 = time.time()
for i in range(n):
    if not np.isnan(preds[i]):
        continue
    train = np.delete(np.arange(n), i)
    X_tr = X[train]; y_tr = y[train]
    x_te = X[i]
    try:
        with pm.Model():
            mu_t = pmb.BART("mu", X_tr, y_tr, m=20, shape=len(y_tr))
            sigma_t = pm.HalfNormal("sigma", sigma=10)
            pm.Normal("obs", mu=mu_t, sigma=sigma_t, observed=y_tr)
            id_t = pm.sample(draws=150, tune=150, chains=1, cores=1,
                              random_seed=42, progressbar=False,
                              compute_convergence_checks=False)
        mu_post = id_t.posterior["mu"].values.mean(axis=(0,1))
        dists = np.linalg.norm(X_tr - x_te, axis=1)
        preds[i] = mu_post[np.argmin(dists)]
    except Exception as e:
        print(f"  arm {i} failed: {type(e).__name__}: {str(e)[:60]}", flush=True)
        preds[i] = np.mean(y_tr)  # fallback
    elapsed = time.time() - t0
    done += 1
    bar_pct = (i+1) / n
    bar = "█" * int(40 * bar_pct) + "░" * (40 - int(40 * bar_pct))
    eta = elapsed / done * (n - (i+1))
    print(f"  [{bar}] {i+1:3d}/{n}  ({bar_pct*100:5.1f}%)  "
          f"elapsed {elapsed/60:5.1f}m  ETA {eta/60:5.1f}m  pred={preds[i]:.1f}%", flush=True)
    if (i+1) % 5 == 0:
        np.save(out_path, preds)
np.save(out_path, preds)

mask = ~np.isnan(preds)
rmse = math.sqrt(mean_squared_error(y[mask], preds[mask]))
r2 = r2_score(y[mask], preds[mask])
print(f"\n══ BART LOO-arm ══")
print(f"  RMSE = {rmse:.2f}%")
print(f"  R²   = {r2:+.3f}")
