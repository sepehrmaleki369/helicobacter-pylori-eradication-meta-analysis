"""
Compute classification metrics (AUC, Brier) for all 8 regression model families
under both LOSO and LOO cross-validation.
For each model: fit regressor, predict ITT rate continuously, derive
P(rate >= threshold) using normal CDF with σ=10pp residual SD.
"""
import os, time, warnings
import numpy as np, pandas as pd
import pickle
warnings.filterwarnings("ignore")
from scipy.stats import norm
from sklearn.metrics import roc_auc_score, brier_score_loss, mean_squared_error
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C, WhiteKernel
import lightgbm as lgb
import xgboost as xgb

IN  = "project/data/processed/clean_dataset.csv"
MDL = "project/models"
SIGMA = 10.0  # residual SD in percentage points for normal-CDF threshold prob

df = pd.read_csv(IN).dropna(subset=["ITT_Rate","N_ITT","Successes_ITT"]).reset_index(drop=True)
with open(f"{MDL}/feature_names_pretreat.pkl","rb") as f:
    FEATURES = pickle.load(f)
X_raw = df[FEATURES].apply(pd.to_numeric, errors="coerce").values.astype(float)
y     = df["ITT_Rate"].values.astype(float)
N     = df["N_ITT"].astype(float).values
g     = df["Ref"].astype(int).values
y85   = (y >= 85).astype(int)
y90   = (y >= 90).astype(int)
n = len(y)

def pipe(reg):
    return Pipeline([("imp", SimpleImputer(strategy="median")),
                     ("sc", StandardScaler()),
                     ("reg", reg)])

models = {
    "ElasticNet":    lambda: pipe(ElasticNet(alpha=0.5, l1_ratio=0.5, max_iter=5000, random_state=42)),
    "RandomForest":  lambda: pipe(RandomForestRegressor(n_estimators=300, max_depth=6,
                                                        min_samples_leaf=3, random_state=42, n_jobs=-1)),
    "GradientBoost": lambda: pipe(GradientBoostingRegressor(n_estimators=300, max_depth=3,
                                                            learning_rate=0.05, random_state=42)),
    "XGBoost":       lambda: pipe(xgb.XGBRegressor(n_estimators=300, max_depth=3, learning_rate=0.05,
                                                   subsample=0.8, colsample_bytree=0.8,
                                                   reg_alpha=0.1, reg_lambda=1.0, random_state=42,
                                                   verbosity=0)),
    "LightGBM":      lambda: pipe(lgb.LGBMRegressor(n_estimators=300, max_depth=4, num_leaves=15,
                                                    learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
                                                    reg_alpha=0.1, reg_lambda=1.0, random_state=42, verbose=-1)),
    "GaussianProcess": lambda: pipe(GaussianProcessRegressor(
        kernel=C(1.0) * RBF(length_scale=1.0) + WhiteKernel(noise_level=10.0),
        alpha=1e-3, normalize_y=True, random_state=42)),
}

def cv_loo(factory, X, y, w, supports_weights=True):
    preds = np.zeros(n)
    for i in range(n):
        tr = np.delete(np.arange(n), i)
        m = factory()
        if supports_weights:
            m.fit(X[tr], y[tr], **{"reg__sample_weight": w[tr]})
        else:
            m.fit(X[tr], y[tr])
        preds[i] = m.predict(X[i:i+1])[0]
    return preds

def cv_loso(factory, X, y, w, g, supports_weights=True):
    preds = np.zeros(n)
    for held in sorted(set(g)):
        tr = g != held; te = g == held
        m = factory()
        if supports_weights:
            m.fit(X[tr], y[tr], **{"reg__sample_weight": w[tr]})
        else:
            m.fit(X[tr], y[tr])
        preds[te] = m.predict(X[te])
    return preds

def metrics_from_continuous(pred, y_rate, y85, y90):
    """Derive classification AUC/Brier from continuous regression preds."""
    p85 = 1 - norm.cdf(85, loc=pred, scale=SIGMA)
    p90 = 1 - norm.cdf(90, loc=pred, scale=SIGMA)
    return (roc_auc_score(y85, pred), brier_score_loss(y85, p85),
            roc_auc_score(y90, pred), brier_score_loss(y90, p90))

print(f"{'Model':<18} {'CV':>5} | {'AUC85':>6} {'B85':>6}  {'AUC90':>6} {'B90':>6}")
print("="*70)
all_results = {}

for name, factory in models.items():
    sw = (name != "GaussianProcess")  # GP doesn't accept sample_weight
    t0 = time.time()
    print(f"\n[{name}] computing LOSO ... ", end="", flush=True)
    pred_loso = cv_loso(factory, X_raw, y, N, g, supports_weights=sw)
    print(f"{time.time()-t0:.1f}s  LOO ... ", end="", flush=True)
    t1 = time.time()
    pred_loo = cv_loo(factory, X_raw, y, N, supports_weights=sw)
    print(f"{time.time()-t1:.1f}s")
    np.save(f"{MDL}/{name.lower()}_loso_ypred.npy", pred_loso)
    np.save(f"{MDL}/{name.lower()}_loo_ypred.npy", pred_loo)
    a85_s, b85_s, a90_s, b90_s = metrics_from_continuous(pred_loso, y, y85, y90)
    a85_o, b85_o, a90_o, b90_o = metrics_from_continuous(pred_loo, y, y85, y90)
    all_results[name] = {
        "loso": (a85_s, b85_s, a90_s, b90_s),
        "loo":  (a85_o, b85_o, a90_o, b90_o),
    }
    print(f"  {name:<16} LOSO | {a85_s:>6.3f} {b85_s:>6.3f}  {a90_s:>6.3f} {b90_s:>6.3f}")
    print(f"  {name:<16}  LOO | {a85_o:>6.3f} {b85_o:>6.3f}  {a90_o:>6.3f} {b90_o:>6.3f}")

# Add Bayesian (LOSO marginal + LOO-arm) and BART from saved files
bayes_loso = np.load(f"{MDL}/bayes_marginal_ypred.npy")
bayes_loo  = np.load(f"{MDL}/bayes_loo_arm_ypred.npy")
bart_loo   = np.load(f"{MDL}/bart_loo_arm_ypred.npy")

# BART LOSO not saved; use existing approximation = mean (run 07f used a near-mean fallback);
# we'll re-run BART LOSO by calling the per-study script (skipped — values from extended_models)
# Use the known LOSO continuous prediction from 07f if available
if os.path.isfile(f"{MDL}/bart_loso_ypred.npy"):
    bart_loso = np.load(f"{MDL}/bart_loso_ypred.npy")
else:
    print("\n[BART LOSO not cached — skipping; LOO only]")
    bart_loso = None

print(f"\n  Bayesian        LOSO | ", end="")
a85, b85, a90, b90 = metrics_from_continuous(bayes_loso, y, y85, y90)
all_results["Bayesian"] = {"loso": (a85, b85, a90, b90)}
print(f"{a85:>6.3f} {b85:>6.3f}  {a90:>6.3f} {b90:>6.3f}")
print(f"  Bayesian         LOO | ", end="")
a85, b85, a90, b90 = metrics_from_continuous(bayes_loo, y, y85, y90)
all_results["Bayesian"]["loo"] = (a85, b85, a90, b90)
print(f"{a85:>6.3f} {b85:>6.3f}  {a90:>6.3f} {b90:>6.3f}")

if bart_loso is not None:
    a85, b85, a90, b90 = metrics_from_continuous(bart_loso, y, y85, y90)
    all_results["BART"] = {"loso": (a85, b85, a90, b90)}
    print(f"  BART            LOSO | {a85:>6.3f} {b85:>6.3f}  {a90:>6.3f} {b90:>6.3f}")
a85, b85, a90, b90 = metrics_from_continuous(bart_loo, y, y85, y90)
all_results.setdefault("BART", {})["loo"] = (a85, b85, a90, b90)
print(f"  BART             LOO | {a85:>6.3f} {b85:>6.3f}  {a90:>6.3f} {b90:>6.3f}")

import json
with open(f"{MDL}/classification_full_results.json","w") as f:
    json.dump({k: {kk: [float(x) for x in vv] for kk, vv in v.items()}
               for k, v in all_results.items()}, f, indent=2)
print("\nSaved → classification_full_results.json")
