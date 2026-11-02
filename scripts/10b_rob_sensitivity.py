"""
Risk-of-bias sensitivity analysis.

Refits the primary cluster-robust binomial GLM and the paired random-effects
meta-analysis under progressive exclusion of trials judged at high risk of
bias by the clinical reviewer, to test whether the vonoprazan effect is
driven by methodologically weaker trials.

Requires verification/rob_clinician.csv (written by 10_rob_clinician.py).
"""
import math
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

ROOT = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri"
DATA = f"{ROOT}/project/data/processed/clean_dataset.csv"
ROB = f"{ROOT}/verification/rob_clinician.csv"
RPT = f"{ROOT}/project/report/rob_sensitivity_results.txt"

# ── Load and merge ───────────────────────────────────────────────────────────
df = pd.read_csv(DATA)
df = df.dropna(subset=["ITT_Rate", "N_ITT", "Successes_ITT"]).copy()
df["Successes"] = df["Successes_ITT"].astype(int)
df["Failures"] = (df["N_ITT"].astype(int) - df["Successes"]).clip(lower=0)
df["Ref"] = df["Ref"].astype(int)

for c in ["Mean_Age_yr", "Compliance_pct", "CLR_Resistance_pct",
          "MTZ_Resistance_pct", "AMX_Resistance_pct", "Duration_Days"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    df[c] = df[c].fillna(df[c].median())

rob = pd.read_csv(ROB)[["Ref", "Overall_derived"]]
rob["Ref"] = rob["Ref"].astype(int)
df = df.merge(rob, on="Ref", how="left")
df["Overall_derived"] = df["Overall_derived"].fillna("Not assessed")

BASE = ("Successes + Failures ~ Is_Vonoprazan + Is_Quadruple + Duration_Days + "
        "CLR_Resistance_pct + Mean_Age_yr")


def fit_glm(data):
    m = smf.glm(BASE, data=data, family=sm.families.Binomial()).fit(
        cov_type="cluster", cov_kwds={"groups": data["Ref"]})
    b = m.params["Is_Vonoprazan"]
    se = m.bse["Is_Vonoprazan"]
    return (math.exp(b), math.exp(b - 1.96 * se), math.exp(b + 1.96 * se),
            m.pvalues["Is_Vonoprazan"])


def pooled_re(data):
    """DerSimonian-Laird random-effects pool over paired vonoprazan studies."""
    eff = []
    for ref, g in data.groupby("Ref"):
        v = g[g["Is_Vonoprazan"] == 1]
        c = g[g["Is_Vonoprazan"] == 0]
        if len(v) == 0 or len(c) == 0:
            continue
        v, c = v.iloc[0], c.iloc[0]
        a, b = v["Successes"] + 0.5, v["Failures"] + 0.5
        cc, d = c["Successes"] + 0.5, c["Failures"] + 0.5
        eff.append({"log_or": math.log((a * d) / (b * cc)),
                    "se": math.sqrt(1 / a + 1 / b + 1 / cc + 1 / d)})
    e = pd.DataFrame(eff)
    if len(e) < 2:
        return None
    w = 1 / e["se"] ** 2
    theta_f = (w * e["log_or"]).sum() / w.sum()
    Q = (w * (e["log_or"] - theta_f) ** 2).sum()
    k = len(e)
    tau2 = max(0.0, (Q - (k - 1)) / (w.sum() - (w ** 2).sum() / w.sum()))
    wr = 1 / (e["se"] ** 2 + tau2)
    theta_r = (wr * e["log_or"]).sum() / wr.sum()
    se_r = math.sqrt(1 / wr.sum())
    I2 = max(0.0, 100 * (Q - (k - 1)) / Q) if Q > 0 else 0.0
    return dict(k=k, OR=math.exp(theta_r),
                lo=math.exp(theta_r - 1.96 * se_r),
                hi=math.exp(theta_r + 1.96 * se_r),
                Q=Q, p_Q=1 - stats.chi2.cdf(Q, k - 1), tau2=tau2, I2=I2)


HIGH = sorted(df.loc[df["Overall_derived"] == "High", "Ref"].unique())
NA = sorted(df.loc[df["Overall_derived"] == "Not assessed", "Ref"].unique())

SCENARIOS = [
    ("Primary analysis (all arms)", df),
    ("Excluding high-RoB trials", df[df["Overall_derived"] != "High"]),
    ("Excluding high-RoB + unassessed",
     df[~df["Overall_derived"].isin(["High", "Not assessed"])]),
    ("Low-RoB trials only", df[df["Overall_derived"] == "Low"]),
]

lines = []
w = lines.append
w("Risk-of-bias sensitivity analysis")
w("=" * 74)
w("")
w(f"Trials judged at high risk of bias : {HIGH}")
w(f"Trials not yet assessed           : {NA}")
w("")
w("── Vonoprazan effect, cluster-robust binomial GLM ──")
w(f"{'Analysis set':<36} {'arms':>5} {'studies':>8} {'OR':>6}  {'95% CI':>16} {'p':>9}")
for name, sub in SCENARIOS:
    if sub["Is_Vonoprazan"].nunique() < 2 or len(sub) < 20:
        w(f"{name:<36} {len(sub):>5} {sub['Ref'].nunique():>8}   (not estimable)")
        continue
    orr, lo, hi, p = fit_glm(sub)
    w(f"{name:<36} {len(sub):>5} {sub['Ref'].nunique():>8} "
      f"{orr:>6.2f}  [{lo:>5.2f}, {hi:>5.2f}] {p:>9.4f}")

w("")
w("── Vonoprazan effect, paired random-effects meta-analysis (DerSimonian-Laird) ──")
w(f"{'Analysis set':<36} {'studies':>8} {'OR':>6}  {'95% CI':>16} {'I2':>7} {'tau2':>7}")
for name, sub in SCENARIOS:
    r = pooled_re(sub)
    if r is None:
        w(f"{name:<36} {'-':>8}   (insufficient paired studies)")
        continue
    w(f"{name:<36} {r['k']:>8} {r['OR']:>6.2f}  "
      f"[{r['lo']:>5.2f}, {r['hi']:>5.2f}] {r['I2']:>6.1f}% {r['tau2']:>7.4f}")

w("")
w("── Contribution of high-RoB trials ──")
hi_arms = df[df["Overall_derived"] == "High"]
w(f"  arms      : {len(hi_arms)} of {len(df)} ({100*len(hi_arms)/len(df):.1f}%)")
w(f"  patients  : {int(hi_arms['N_ITT'].sum()):,} of {int(df['N_ITT'].sum()):,} "
  f"({100*hi_arms['N_ITT'].sum()/df['N_ITT'].sum():.1f}%)")
w(f"  vonoprazan arms among them: {int(hi_arms['Is_Vonoprazan'].sum())}")
w(f"  mean ITT eradication: {hi_arms['ITT_Rate'].mean():.1f}% "
  f"vs {df[df['Overall_derived'] != 'High']['ITT_Rate'].mean():.1f}% in the remainder")

w("")
w("── Eradication rate by risk-of-bias judgement ──")
for lvl in ["Low", "Some concerns", "High", "Not assessed"]:
    s = df[df["Overall_derived"] == lvl]
    if len(s) == 0:
        continue
    w(f"  {lvl:<15} {len(s):>3} arms   mean ITT {s['ITT_Rate'].mean():>5.1f}% "
      f"(SD {s['ITT_Rate'].std():>4.1f})")

txt = "\n".join(lines)
print(txt)
with open(RPT, "w") as f:
    f.write(txt + "\n")
print(f"\nWrote {RPT}")
