"""
Risk of Bias 2.0 — single clinical reviewer ingest, summary, and figures.

Reads the completed rating workbook returned by the clinical reviewer,
normalises the domain judgements, writes a tidy CSV, and regenerates the
traffic-light and per-domain summary figures used in the manuscript.

Supersedes the earlier algorithmic assessments (rob_assessments.csv,
rob_assessments_reviewer2.csv), which are retained only as a provenance
record and are NOT used in the manuscript.
"""
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib.lines import Line2D

ROOT = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri"
SRC = f"{ROOT}/03_rating_template--Final.xlsx"
OUT_CSV = f"{ROOT}/verification/rob_clinician.csv"
FIGDIR = f"{ROOT}/project/figures/MAIN_FIGURES"

DOMAINS = [
    ("D1a_random_seq",   "D1a. Random sequence generation"),
    ("D1b_concealment",  "D1b. Allocation concealment"),
    ("D2_blinding",      "D2. Deviations from intended interventions"),
    ("D3_missing",       "D3. Missing outcome data"),
    ("D4_outcome",       "D4. Measurement of the outcome"),
    ("D5_reporting",     "D5. Selection of the reported result"),
]
LEVELS = ["Low", "Some concerns", "High"]
COLORS = {"Low": "#2E9B57", "Some concerns": "#E8B33A", "High": "#C8443B",
          "Not assessed": "#BEBEBE"}
SYMBOL = {"Low": "+", "Some concerns": "!", "High": "−", "Not assessed": "?"}


def normalise(v):
    """Canonicalise a judgement string: strip NBSP/whitespace, fix case."""
    if pd.isna(v):
        return "Not assessed"
    s = str(v).replace("\xa0", " ").strip().lower()
    s = re.sub(r"\s+", " ", s)
    if s in {"", "nan", "na", "n/a"}:
        return "Not assessed"
    if s.startswith("low"):
        return "Low"
    if s.startswith("some"):
        return "Some concerns"
    if s.startswith("high"):
        return "High"
    return "Not assessed"


def short_label(study):
    """'29 KimSY 2012' -> 'Kim 2012 [29]'."""
    s = str(study).strip()
    m = re.match(r"^(\d+)\s+(.+)$", s)
    ref, rest = (m.group(1), m.group(2)) if m else ("", s)
    m2 = re.match(r"^([A-Z][a-z]+)", rest)
    surname = m2.group(1) if m2 else rest.split()[0]
    y = re.search(r"(19|20)\d{2}", rest)
    year = y.group(0) if y else ""
    return f"{surname} {year} [{ref}]".strip()


# Reports retained in the workbook but excluded from the review after the
# reviewer identified them as non-randomised (prospective observational and
# retrospective propensity-matched respectively).  They are dropped here so
# the risk-of-bias summary describes only the eligible cohort.
EXCLUDED_NON_RCT = [39, 72]

# ---------------------------------------------------------------- ingest
df = pd.read_excel(SRC, sheet_name=0)
df = df[~df["Ref"].isin(EXCLUDED_NON_RCT)].copy()
tidy = pd.DataFrame({
    "Ref": df["Ref"].astype(int),
    "Study": df["Study"].astype(str).str.strip(),
    "Label": df["Study"].map(short_label),
    "Country": df["Country"].astype(str).str.strip(),
})
JUST_COL = {"D1a_random_seq": "D1a_just", "D1b_concealment": "D1b_just",
            "D2_blinding": "D2_just", "D3_missing": "D3_just",
            "D4_outcome": "D4_just", "D5_reporting": "D5_just"}
for col, _ in DOMAINS:
    tidy[col] = df[col].map(normalise)
    tidy[col + "_just"] = df[JUST_COL[col]]
tidy["Overall_reported"] = df["Overall"].map(normalise)
tidy["Reviewer_notes"] = df["Reviewer_notes"]

# ------------------------------------------------- protocol harmonisation
# The review protocol pre-specifies that, because H. pylori eradication is
# ascertained by objective assay, lack of blinding alone does not warrant a
# High rating on D2 or D4.  One trial was rated High on those domains on the
# basis of open-label design alone, inconsistent with the protocol and with
# the reviewer's own treatment of the other 59 trials.  The judgement is
# harmonised here; the reviewer's original entry is preserved verbatim in the
# *_reviewer_original columns and the change is declared in the manuscript.
HARMONISE = {
    29: {
        "domains": {"D2_blinding": "Low", "D4_outcome": "Low"},
        "reason": ("Eradication ascertained by rapid urease test, histology, "
                   "and 13C-urea breath test with a pre-specified 2.5% cut-off; "
                   "objective outcome, so lack of blinding does not support a "
                   "High rating under the pre-specified convention."),
    },
}

for col, _ in DOMAINS:
    tidy[col + "_reviewer_original"] = tidy[col]
tidy["Harmonised"] = ""
tidy["Harmonisation_reason"] = ""

for ref, spec in HARMONISE.items():
    mask = tidy["Ref"] == ref
    if not mask.any():
        continue
    changed = []
    for col, newval in spec["domains"].items():
        old = tidy.loc[mask, col].iloc[0]
        if old != newval:
            tidy.loc[mask, col] = newval
            changed.append(f"{col}: {old} -> {newval}")
    if changed:
        tidy.loc[mask, "Harmonised"] = "; ".join(changed)
        tidy.loc[mask, "Harmonisation_reason"] = spec["reason"]
        print(f"[protocol harmonisation] Ref {ref}: " + "; ".join(changed))

# Derived overall = worst judgement across the six domains (RoB 2.0 rule).
rank = {"Low": 0, "Some concerns": 1, "High": 2, "Not assessed": -1}
inv = {0: "Low", 1: "Some concerns", 2: "High"}


def derive_overall(row):
    vals = [row[c] for c, _ in DOMAINS]
    if all(v == "Not assessed" for v in vals):
        return "Not assessed"
    scored = [rank[v] for v in vals if v != "Not assessed"]
    return inv[max(scored)]


tidy["Overall_derived"] = tidy.apply(derive_overall, axis=1)
tidy.to_csv(OUT_CSV, index=False)

assessed = tidy[tidy["Overall_derived"] != "Not assessed"]
pending = tidy[tidy["Overall_derived"] == "Not assessed"]

print("=" * 74)
print("RoB 2.0 — single clinical reviewer")
print("=" * 74)
print(f"Studies in workbook : {len(tidy)}")
print(f"Assessed            : {len(assessed)}")
print(f"Pending             : {len(pending)}"
      + (f"  -> Refs {list(pending['Ref'])}" if len(pending) else ""))
print()
print("Overall judgement (derived = worst domain):")
for lvl in LEVELS:
    n = (assessed["Overall_derived"] == lvl).sum()
    print(f"  {lvl:<15} {n:>3}  ({100*n/len(assessed):>5.1f}%)")
disagree = assessed[assessed["Overall_derived"] != assessed["Overall_reported"]]
print(f"\nReviewer's own 'Overall' differs from worst-domain rule in "
      f"{len(disagree)} studies: {list(disagree['Ref'])}")
print()
print("Per-domain distribution (assessed studies):")
for col, name in DOMAINS:
    counts = assessed[col].value_counts()
    row = "  ".join(f"{lvl}: {counts.get(lvl,0):>2}" for lvl in LEVELS)
    print(f"  {name:<46} {row}")

high_refs = sorted(assessed.loc[assessed["Overall_derived"] == "High", "Ref"])
print(f"\nHigh risk of bias: {high_refs}")

# --------------------------------------------------- Fig 6: traffic light
plot_df = tidy.sort_values("Ref").reset_index(drop=True)
n = len(plot_df)
ncols = len(DOMAINS) + 1
fig_h = max(8.0, 0.26 * n + 2.0)
fig, ax = plt.subplots(figsize=(10.5, fig_h))

for i, (_, row) in enumerate(plot_df.iterrows()):
    y = n - i
    judgements = [row[c] for c, _ in DOMAINS] + [row["Overall_derived"]]
    for j, jd in enumerate(judgements):
        ax.add_patch(Circle((j + 0.5, y), 0.34, facecolor=COLORS[jd],
                            edgecolor="white", linewidth=1.1, zorder=3))
        ax.text(j + 0.5, y, SYMBOL[jd], ha="center", va="center",
                fontsize=8.5, color="white", fontweight="bold", zorder=4)
    ax.text(-0.25, y, row["Label"], ha="right", va="center", fontsize=7.4)

headers = [name.split(". ")[0] for _, name in DOMAINS] + ["Overall"]
for j, h in enumerate(headers):
    ax.text(j + 0.5, n + 1.05, h, ha="center", va="bottom",
            fontsize=8.6, fontweight="bold", rotation=0)

ax.set_xlim(-4.6, ncols + 0.2)
ax.set_ylim(0.2, n + 2.2)
ax.axis("off")
handles = [Line2D([0], [0], marker="o", linestyle="", markersize=9,
                  markerfacecolor=COLORS[k], markeredgecolor="white",
                  label={"Low": "Low risk", "Some concerns": "Some concerns",
                         "High": "High risk", "Not assessed": "Not assessed"}[k])
           for k in ["Low", "Some concerns", "High", "Not assessed"]]
ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.42, -0.045),
          ncol=4, frameon=False, fontsize=9)
fig.suptitle("Cochrane Risk of Bias 2.0 assessment (single clinical assessor)",
             fontsize=11.5, y=0.995)
fig.tight_layout(rect=[0, 0.02, 1, 0.985])
fig.savefig(f"{FIGDIR}/Fig6_RoB.png", dpi=200, bbox_inches="tight")
plt.close(fig)
print(f"\nWrote {FIGDIR}/Fig6_RoB.png")

# ------------------------------------------ Fig 6b: per-domain stacked bar
fig, ax = plt.subplots(figsize=(9.2, 3.9))
labels = [name for _, name in DOMAINS] + ["Overall"]
cols = [c for c, _ in DOMAINS] + ["Overall_derived"]
ypos = np.arange(len(labels))[::-1]

left = np.zeros(len(labels))
for lvl in LEVELS:
    widths = np.array([100 * (tidy[c] == lvl).sum() / len(tidy) for c in cols])
    ax.barh(ypos, widths, left=left, color=COLORS[lvl], height=0.66,
            edgecolor="white", linewidth=0.8,
            label={"Low": "Low risk", "Some concerns": "Some concerns",
                   "High": "High risk"}[lvl])
    for y, w, l in zip(ypos, widths, left):
        if w >= 6:
            ax.text(l + w / 2, y, f"{w:.0f}%", ha="center", va="center",
                    fontsize=8, color="white", fontweight="bold")
    left += widths
na = np.array([100 * (tidy[c] == "Not assessed").sum() / len(tidy) for c in cols])
if na.sum() > 0:
    ax.barh(ypos, na, left=left, color=COLORS["Not assessed"], height=0.66,
            edgecolor="white", linewidth=0.8, label="Not assessed")

ax.set_yticks(ypos)
ax.set_yticklabels(labels, fontsize=9)
ax.set_xlim(0, 100)
ax.set_xlabel("Proportion of studies (%)", fontsize=9.5)
ax.tick_params(axis="x", labelsize=9)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.42), ncol=4,
          frameon=False, fontsize=9)
ax.set_title(f"Risk of bias by domain (n = {len(tidy)} trials)",
             fontsize=11, pad=10)
fig.tight_layout()
fig.savefig(f"{FIGDIR}/Fig6b_RoB_summary.png", dpi=200, bbox_inches="tight")
plt.close(fig)
print(f"Wrote {FIGDIR}/Fig6b_RoB_summary.png")
print(f"Wrote {OUT_CSV}")
