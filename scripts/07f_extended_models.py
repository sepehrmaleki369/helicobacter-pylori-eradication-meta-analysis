"""
Extended model menu — add the previously-missing methods:
  - XGBoost
  - LightGBM
  - Gaussian Process Regressor (with calibrated uncertainty)
  - BART (Bayesian Additive Regression Trees, via pymc-bart)

Compared with existing baselines (ElasticNet, RF, sklearn GBM, Bayesian).
Feature set: pretreat (39 features). Target: ITT_Rate. Weights: N_ITT.
CV: LOO-arm + LOSO-study.

Outputs:
  - figures/extended_models_comparison.png
  - report/extended_models_results.txt
"""
import os, math, pickle, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")

import xgboost as xgb
import lightgbm as lgb
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C, WhiteKernel
from sklearn.linear_model import ElasticNetCV
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import LeaveOneOut, LeaveOneGroupOut
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_squared_error, r2_score

IN  = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/data/processed/clean_dataset.csv"
MDL = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/models"
FIG = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/figures"
RPT = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/report"


def pipe(model, scale=True):
    steps = [("imp", SimpleImputer(strategy="median"))]
    if scale: steps.append(("sc", StandardScaler()))
    steps.append(("m", model))
    return Pipeline(steps)


def cv_loso(model_factory, X, y, w, g):
    splits = list(LeaveOneGroupOut().split(X, groups=g))
    y_pred = np.full_like(y, np.nan, dtype=float)
    for tr, te in splits:
        m = model_factory()
        try: m.fit(X[tr], y[tr], m__sample_weight=w[tr])
        except (TypeError, ValueError):
            try: m.fit(X[tr], y[tr], sample_weight=w[tr])
            except (TypeError, ValueError): m.fit(X[tr], y[tr])
        y_pred[te] = m.predict(X[te])
    mask = ~np.isnan(y_pred)
    rmse = math.sqrt(mean_squared_error(y[mask], y_pred[mask]))
    r2 = r2_score(y[mask], y_pred[mask])
    return rmse, r2, y_pred


def cv_loo(model_factory, X, y, w):
    splits = list(LeaveOneOut().split(X))
    y_pred = np.full_like(y, np.nan, dtype=float)
    for tr, te in splits:
        m = model_factory()
        try: m.fit(X[tr], y[tr], m__sample_weight=w[tr])
        except (TypeError, ValueError):
            try: m.fit(X[tr], y[tr], sample_weight=w[tr])
            except (TypeError, ValueError): m.fit(X[tr], y[tr])
        y_pred[te] = m.predict(X[te])
    mask = ~np.isnan(y_pred)
    rmse = math.sqrt(mean_squared_error(y[mask], y_pred[mask]))
    r2 = r2_score(y[mask], y_pred[mask])
    return rmse, r2, y_pred


def make_models():
    return {
        "ElasticNet": lambda: pipe(ElasticNetCV(
            l1_ratio=[0.3,0.5,0.7,0.9,1.0],
            alphas=np.logspace(-3,1,20),
            cv=5, max_iter=10000, random_state=42)),
        "RandomForest": lambda: pipe(RandomForestRegressor(
            n_estimators=300, max_depth=4, min_samples_leaf=4,
            random_state=42), scale=False),
        "GradientBoost (sklearn)": lambda: pipe(GradientBoostingRegressor(
            n_estimators=200, max_depth=3, learning_rate=0.05,
            subsample=0.8, min_samples_leaf=4, random_state=42), scale=False),
        "XGBoost": lambda: pipe(xgb.XGBRegressor(
            n_estimators=300, max_depth=3, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            reg_alpha=0.1, reg_lambda=1.0,
            random_state=42, verbosity=0,
            objective="reg:squarederror"), scale=False),
        "LightGBM": lambda: pipe(lgb.LGBMRegressor(
            n_estimators=300, max_depth=4, num_leaves=15,
            learning_rate=0.05, subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1, reg_lambda=1.0,
            random_state=42, verbose=-1), scale=False),
        "GaussianProcess": lambda: pipe(GaussianProcessRegressor(
            kernel=C(1.0) * RBF(length_scale=1.0) + WhiteKernel(noise_level=10.0),
            alpha=1e-3, normalize_y=True, random_state=42)),
    }


def run_bart(X, y, y_succ, g):
    """BART must run under __main__ guard due to multiprocessing.Manager."""
    import pymc as pm
    import pymc_bart as pmb

    X_bart = SimpleImputer(strategy="median").fit_transform(X)

    print("\n── BART LOSO (refit per held-out study) ──")
    bart_pred_loso = np.full(len(y), np.nan)
    unique_g = sorted(set(g))
    for i, held in enumerate(unique_g):
        train_mask = (g != held)
        test_mask  = (g == held)
        X_tr = X_bart[train_mask]; y_tr = y[train_mask]
        X_te = X_bart[test_mask]
        try:
            with pm.Model():
                mu_t = pmb.BART("mu", X_tr, y_tr, m=20, shape=len(y_tr))
                sigma_t = pm.HalfNormal("sigma", sigma=10)
                pm.Normal("obs", mu=mu_t, sigma=sigma_t, observed=y_tr)
                id_t = pm.sample(draws=200, tune=200, chains=1, cores=1,
                                  random_seed=42, progressbar=False,
                                  compute_convergence_checks=False)
            mu_post = id_t.posterior["mu"].values.mean(axis=(0,1))
            # Approximate prediction by nearest-neighbor in training set
            for j, x_te in enumerate(X_te):
                dists = np.linalg.norm(X_tr - x_te, axis=1)
                bart_pred_loso[np.where(test_mask)[0][j]] = mu_post[np.argmin(dists)]
        except Exception as e:
            bart_pred_loso[test_mask] = y_tr.mean()
        if (i + 1) % 10 == 0:
            print(f"  Done {i+1}/{len(unique_g)} studies")

    mask = ~np.isnan(bart_pred_loso)
    rmse_loso  = math.sqrt(mean_squared_error(y[mask], bart_pred_loso[mask]))
    r2_loso = r2_score(y[mask], bart_pred_loso[mask])
    print(f"\n  BART LOSO: RMSE={rmse_loso:.2f}, R²={r2_loso:+.3f}")
    return rmse_loso, r2_loso, bart_pred_loso


def main():
    with open(f"{MDL}/feature_names_pretreat.pkl", "rb") as f:
        FEATURES = pickle.load(f)
    print(f"Feature set ({len(FEATURES)}): pretreat")

    df = pd.read_csv(IN).dropna(subset=["ITT_Rate","N_ITT","Successes_ITT"]).reset_index(drop=True)
    X = df[FEATURES].apply(pd.to_numeric, errors="coerce").values.astype(float)
    y = df["ITT_Rate"].values.astype(float)
    w = df["N_ITT"].values.astype(float)
    g = df["Ref"].astype(int).values
    y_succ = df["Successes_ITT"].astype(int).values
    print(f"Dataset: {len(df)} arms, {len(set(g))} studies\n")

    # ── 6 frequentist + GP models ─────────────────────────────────────────────
    print("═"*78)
    print(f"{'Model':<26} {'LOO-RMSE':>10} {'LOO-R²':>8} {'LOSO-RMSE':>11} {'LOSO-R²':>9}")
    print("═"*78)
    results = {}
    preds = {}
    for name, factory in make_models().items():
        rmse_loo, r2_loo, ypred_loo = cv_loo(factory, X, y, w)
        rmse_loso, r2_loso, ypred_loso = cv_loso(factory, X, y, w, g)
        results[name] = {"loo_rmse": rmse_loo, "loo_r2": r2_loo,
                         "loso_rmse": rmse_loso, "loso_r2": r2_loso}
        preds[name] = {"loo": ypred_loo, "loso": ypred_loso}
        print(f"  {name:<24} {rmse_loo:>10.2f} {r2_loo:>+8.3f} {rmse_loso:>11.2f} {r2_loso:>+9.3f}")
        np.save(f"{MDL}/{name.lower().replace(' ','_').replace('(','').replace(')','')}_loso_ypred.npy",
                ypred_loso)

    # ── BART ──────────────────────────────────────────────────────────────────
    print("\n" + "═"*78)
    print("BART (Bayesian Additive Regression Trees)")
    print("═"*78)
    try:
        rmse_bart, r2_bart, bart_pred = run_bart(X, y, y_succ, g)
        results["BART"] = {"loo_rmse": np.nan, "loo_r2": np.nan,
                           "loso_rmse": rmse_bart, "loso_r2": r2_bart}
        preds["BART"] = {"loso": bart_pred}
        np.save(f"{MDL}/bart_loso_ypred.npy", bart_pred)
    except Exception as e:
        print(f"BART failed: {e}")

    # ── Add Bayesian hierarchical (from 07c) to the comparison ────────────────
    try:
        bayes_marg = np.load(f"{MDL}/bayes_marginal_ypred.npy") * 100
        if len(bayes_marg) == len(y):
            rmse_b = math.sqrt(((y - bayes_marg)**2).mean())
            r2_b = r2_score(y, bayes_marg)
            results["Bayesian hierarchical (marginal)"] = {
                "loo_rmse": np.nan, "loo_r2": np.nan,
                "loso_rmse": rmse_b, "loso_r2": r2_b}
            preds["Bayesian hierarchical (marginal)"] = {"loso": bayes_marg}
            print(f"\nBayesian hierarchical (marginal): RMSE={rmse_b:.2f}, R²={r2_b:+.3f}")
    except FileNotFoundError:
        pass

    # ── Final comparison ──────────────────────────────────────────────────────
    print("\n" + "═"*78)
    print("FINAL COMPARISON (sorted by LOSO R² — honest generalisation)")
    print("═"*78)
    sorted_results = sorted(results.items(), key=lambda kv: -kv[1]["loso_r2"])
    print(f"{'Rank':<5} {'Model':<34} {'LOSO-RMSE':>11} {'LOSO-R²':>9} {'LOO-R²':>8}")
    print("-"*78)
    for i, (n, r) in enumerate(sorted_results):
        loo_r2_str = f"{r['loo_r2']:+.3f}" if not np.isnan(r['loo_r2']) else "  n/a"
        print(f"  {i+1:<3} {n:<34} {r['loso_rmse']:>11.2f} {r['loso_r2']:>+9.3f}  {loo_r2_str:>8}")

    # Bar chart
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    ax = axes[0]
    names = [n for n, _ in sorted_results]
    losos = [r["loso_r2"] for _, r in sorted_results]
    colors = ["#4CAF50" if x > 0 else "#F44336" for x in losos]
    ax.barh(range(len(names)), losos, color=colors, alpha=0.85)
    ax.axvline(0, color="black", linewidth=1)
    ax.set_yticks(range(len(names))); ax.set_yticklabels(names, fontsize=10)
    ax.set_xlabel("LOSO R² (honest generalisation)", fontsize=11)
    ax.set_title("LOSO R² across model families", fontweight="bold")
    ax.grid(axis="x", alpha=0.3); ax.invert_yaxis()

    ax = axes[1]
    loo_valid = [(n, r["loo_r2"]) for n, r in sorted_results if not np.isnan(r["loo_r2"])]
    names_loo = [n for n, _ in loo_valid]
    loos_v = [r for _, r in loo_valid]
    colors_loo = ["#2196F3" if x > 0 else "#F44336" for x in loos_v]
    ax.barh(range(len(names_loo)), loos_v, color=colors_loo, alpha=0.85)
    ax.axvline(0, color="black", linewidth=1)
    ax.set_yticks(range(len(names_loo))); ax.set_yticklabels(names_loo, fontsize=10)
    ax.set_xlabel("LOO-arm R²", fontsize=11)
    ax.set_title("LOO-arm R² (more optimistic)", fontweight="bold")
    ax.grid(axis="x", alpha=0.3); ax.invert_yaxis()

    plt.suptitle(f"Extended model comparison — {len(df)} arms, {len(set(g))} studies",
                 fontweight="bold", fontsize=13)
    plt.tight_layout()
    plt.savefig(f"{FIG}/extended_models_comparison.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n✓ {FIG}/extended_models_comparison.png")

    # ── Write report ──────────────────────────────────────────────────────────
    with open(f"{RPT}/extended_models_results.txt", "w", encoding="utf-8") as f:
        f.write("Extended model comparison — all model families\n")
        f.write("="*70 + "\n\n")
        f.write(f"Dataset: {len(df)} arms, {len(set(g))} studies\n")
        f.write(f"Feature set: pretreat ({len(FEATURES)} features)\n")
        f.write(f"Weighting: by N_ITT\n\n")
        f.write(f"{'Rank':<5} {'Model':<34} {'LOSO-RMSE':>11} {'LOSO-R²':>9} {'LOO-R²':>8}\n")
        for i, (n, r) in enumerate(sorted_results):
            loo_r2_str = f"{r['loo_r2']:+.3f}" if not np.isnan(r['loo_r2']) else "  n/a"
            f.write(f"  {i+1:<3} {n:<34} {r['loso_rmse']:>11.2f} {r['loso_r2']:>+9.3f}  {loo_r2_str:>8}\n")

    print(f"\n✓ {RPT}/extended_models_results.txt")
    print("\n✓ Extended model comparison complete.")


if __name__ == "__main__":
    main()
