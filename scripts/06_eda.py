"""
Phase 4: Exploratory Data Analysis.
Outputs: project/figures/*.png + console summary tables.
"""
import csv, math, os, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

IN  = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/data/processed/clean_dataset.csv"
FIG = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/figures"
os.makedirs(FIG, exist_ok=True)

# ── Load ───────────────────────────────────────────────────────────────────────
with open(IN, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

def flt(v):
    try: return float(v) if v not in (None, "", "None") else None
    except: return None

def intt(v):
    try: return int(float(v)) if v not in (None, "", "None") else None
    except: return None

# Parse numerics
for r in rows:
    r["ITT_Rate"]         = flt(r["ITT_Rate"])
    r["PP_Rate"]          = flt(r["PP_Rate"])
    r["Primary_Rate"]     = flt(r["Primary_Rate"])
    r["CLR_Resistance_pct"] = flt(r["CLR_Resistance_pct"])
    r["MTZ_Resistance_pct"] = flt(r["MTZ_Resistance_pct"])
    r["AMX_Resistance_pct"] = flt(r["AMX_Resistance_pct"])
    r["LFX_Resistance_pct"] = flt(r["LFX_Resistance_pct"])
    r["Duration_Days"]    = flt(r["Duration_Days"])
    r["N_ITT"]            = intt(r["N_ITT"])
    r["Is_Dual"]          = intt(r["Is_Dual"])
    r["Is_Triple"]        = intt(r["Is_Triple"])
    r["Is_Quadruple"]     = intt(r["Is_Quadruple"])
    r["Is_PCAB"]          = intt(r["Is_PCAB"])
    r["Is_Standard_PPI"]  = intt(r["Is_Standard_PPI"])
    r["Has_Bismuth"]      = intt(r["Has_Bismuth"])
    r["Is_High_CLR_Region"] = intt(r["Is_High_CLR_Region"])
    r["Is_East_Asia"]     = intt(r["Is_East_Asia"])

PALETTE = {
    "dual":      "#2196F3",
    "triple":    "#FF9800",
    "quadruple": "#4CAF50",
    "nonbismuth_quadruple": "#9C27B0",
}

def ttype_color(r):
    return PALETTE.get(r["Treatment_Type"], "#999999")

def mean_ci(values):
    n = len(values)
    if n == 0: return None, None, None
    m = sum(values) / n
    if n < 2: return m, m, m
    sd = math.sqrt(sum((x-m)**2 for x in values) / (n-1))
    se = sd / math.sqrt(n)
    return m, m - 1.96*se, m + 1.96*se


# ═══════════════════════════════════════════════════════════════════════════════
# FIG 1: ITT rate distribution (histogram)
# ═══════════════════════════════════════════════════════════════════════════════
itts = [r["ITT_Rate"] for r in rows if r["ITT_Rate"] is not None]
pps  = [r["PP_Rate"]  for r in rows if r["PP_Rate"]  is not None]

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
for ax, vals, label, color in [
        (axes[0], itts, "ITT Eradication Rate (%)", "#2196F3"),
        (axes[1], pps,  "PP Eradication Rate (%)",  "#FF9800")]:
    ax.hist(vals, bins=16, color=color, edgecolor="white", alpha=0.85)
    ax.axvline(sum(vals)/len(vals), color="black", linestyle="--", linewidth=1.5,
               label=f"Mean={sum(vals)/len(vals):.1f}%")
    ax.axvline(85, color="red", linestyle=":", linewidth=1.2, label="85% threshold")
    ax.axvline(90, color="darkred", linestyle=":", linewidth=1.2, label="90% threshold")
    ax.set_xlabel(label, fontsize=11)
    ax.set_ylabel("Number of arms", fontsize=11)
    ax.set_title(f"{label.split()[0]} distribution (n={len(vals)})", fontsize=12)
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)
plt.suptitle("H. pylori Eradication Rate Distributions (84 arms)", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(f"{FIG}/fig1_rate_distributions.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ fig1_rate_distributions.png")


# ═══════════════════════════════════════════════════════════════════════════════
# FIG 2: Forest plot – ITT rate by study arm
# ═══════════════════════════════════════════════════════════════════════════════
forest_rows = sorted(
    [r for r in rows if r["ITT_Rate"] is not None],
    key=lambda x: (x["Treatment_Type"], -x["ITT_Rate"])
)
n = len(forest_rows)
fig, ax = plt.subplots(figsize=(9, n * 0.28 + 1.5))
for i, r in enumerate(forest_rows):
    rate = r["ITT_Rate"]
    n_itt = r["N_ITT"] or 80
    # approximate 95% CI from binomial
    p = rate / 100
    se = math.sqrt(p*(1-p)/n_itt) * 100
    lo, hi = max(0, rate - 1.96*se), min(100, rate + 1.96*se)
    color = ttype_color(r)
    ax.plot([lo, hi], [i, i], color=color, linewidth=1.2, alpha=0.7)
    ax.plot(rate, i, "o", color=color, markersize=4)
    label = f"Ref{r['Ref']} {r['Arm_Label'][:20]}"
    ax.text(101, i, label, va="center", fontsize=5.5, color="#333333")

ax.axvline(85, color="red",    linestyle=":", linewidth=1.0, alpha=0.8)
ax.axvline(90, color="darkred",linestyle=":", linewidth=1.0, alpha=0.8)
ax.set_xlim(40, 145)
ax.set_ylim(-1, n)
ax.set_xlabel("ITT Eradication Rate (%)", fontsize=11)
ax.set_yticks([])
ax.set_title("Forest Plot: ITT Eradication Rate by Study Arm", fontsize=12, fontweight="bold")
patches = [mpatches.Patch(color=c, label=l) for l, c in [
    ("Dual","#2196F3"), ("Triple","#FF9800"),
    ("Quadruple","#4CAF50"), ("Non-bismuth quad","#9C27B0")]]
ax.legend(handles=patches, fontsize=8, loc="lower right")
ax.grid(axis="x", alpha=0.2)
plt.tight_layout()
plt.savefig(f"{FIG}/fig2_forest_plot.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ fig2_forest_plot.png")


# ═══════════════════════════════════════════════════════════════════════════════
# FIG 3: Mean ITT by treatment type (bar + individual points)
# ═══════════════════════════════════════════════════════════════════════════════
groups = ["dual", "triple", "quadruple"]
labels = ["Dual\n(PPI+Amox)", "Triple\n(+ Clari/Metro)", "Quadruple\n(+ Bismuth)"]
colors = ["#2196F3", "#FF9800", "#4CAF50"]

fig, ax = plt.subplots(figsize=(8, 5))
for xi, (g, lbl, col) in enumerate(zip(groups, labels, colors)):
    vals = [r["ITT_Rate"] for r in rows if r["Treatment_Type"] == g and r["ITT_Rate"] is not None]
    if not vals: continue
    m, lo, hi = mean_ci(vals)
    ax.bar(xi, m, color=col, alpha=0.75, width=0.5, label=f"{lbl} n={len(vals)}")
    ax.errorbar(xi, m, yerr=[[m-lo],[hi-m]], fmt="none", color="black", capsize=5, linewidth=1.5)
    jitter = [xi + np.random.uniform(-0.18, 0.18) for _ in vals]
    ax.scatter(jitter, vals, color=col, s=22, alpha=0.5, zorder=3, edgecolors="white", linewidths=0.3)

ax.axhline(85, color="red",    linestyle="--", linewidth=1.2, label="85% target")
ax.axhline(90, color="darkred",linestyle="--", linewidth=1.2, label="90% target")
ax.set_xticks(range(len(groups)))
ax.set_xticklabels(labels, fontsize=10)
ax.set_ylabel("Mean ITT Eradication Rate (%)", fontsize=11)
ax.set_ylim(50, 100)
ax.set_title("ITT Eradication Rate by Treatment Type\n(mean ± 95% CI, individual arms overlaid)", fontsize=12, fontweight="bold")
ax.legend(fontsize=9)
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(f"{FIG}/fig3_treatment_type_comparison.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ fig3_treatment_type_comparison.png")


# ═══════════════════════════════════════════════════════════════════════════════
# FIG 4: P-CAB vs standard PPI (within dual therapy)
# ═══════════════════════════════════════════════════════════════════════════════
dual_pcab = [r["ITT_Rate"] for r in rows if r["Is_Dual"]==1 and r["Is_PCAB"]==1 and r["ITT_Rate"] is not None]
dual_ppi  = [r["ITT_Rate"] for r in rows if r["Is_Dual"]==1 and r["Is_Standard_PPI"]==1 and r["ITT_Rate"] is not None]
all_pcab  = [r["ITT_Rate"] for r in rows if r["Is_PCAB"]==1 and r["ITT_Rate"] is not None]
all_ppi   = [r["ITT_Rate"] for r in rows if r["Is_Standard_PPI"]==1 and r["ITT_Rate"] is not None]

fig, axes = plt.subplots(1, 2, figsize=(11, 5))
for ax, (g1, g2, lbl1, lbl2, title) in [
        (axes[0], (dual_pcab, dual_ppi, "P-CAB dual", "PPI dual", "Dual Therapy: P-CAB vs Standard PPI")),
        (axes[1], (all_pcab, all_ppi, "P-CAB (all)", "PPI (all)", "All Arms: P-CAB vs Standard PPI"))]:
    for xi, (vals, lbl, col) in enumerate([(g1, lbl1, "#E91E63"), (g2, lbl2, "#607D8B")]):
        if not vals: continue
        m, lo, hi = mean_ci(vals)
        ax.bar(xi, m, color=col, alpha=0.8, width=0.4)
        ax.errorbar(xi, m, yerr=[[m-lo],[hi-m]], fmt="none", color="black", capsize=5)
        jit = [xi + np.random.uniform(-0.12, 0.12) for _ in vals]
        ax.scatter(jit, vals, color=col, s=25, alpha=0.55, zorder=3, edgecolors="white")
        ax.text(xi, m+1.5, f"{m:.1f}%\nn={len(vals)}", ha="center", fontsize=9, fontweight="bold")
    ax.axhline(85, color="red", linestyle="--", linewidth=1.0, alpha=0.8)
    ax.axhline(90, color="darkred", linestyle="--", linewidth=1.0, alpha=0.8)
    ax.set_xticks([0,1]); ax.set_xticklabels([lbl1, lbl2], fontsize=10)
    ax.set_ylim(55, 100); ax.set_ylabel("ITT Rate (%)", fontsize=11)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.grid(axis="y", alpha=0.3)
plt.suptitle("P-CAB vs Standard PPI Eradication Rates", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(f"{FIG}/fig4_pcab_vs_ppi.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ fig4_pcab_vs_ppi.png")


# ═══════════════════════════════════════════════════════════════════════════════
# FIG 5: Scatter – ITT rate vs CLR resistance
# ═══════════════════════════════════════════════════════════════════════════════
scatter_rows = [r for r in rows if r["ITT_Rate"] is not None and r["CLR_Resistance_pct"] is not None]
fig, ax = plt.subplots(figsize=(8, 5.5))
for ttype in ["dual", "triple", "quadruple"]:
    sub = [r for r in scatter_rows if r["Treatment_Type"] == ttype]
    if not sub: continue
    ax.scatter([r["CLR_Resistance_pct"] for r in sub],
               [r["ITT_Rate"] for r in sub],
               color=PALETTE.get(ttype, "#999"), label=ttype.capitalize(),
               s=55, alpha=0.75, edgecolors="white", linewidths=0.5)

# regression line (all arms)
xs = [r["CLR_Resistance_pct"] for r in scatter_rows]
ys = [r["ITT_Rate"] for r in scatter_rows]
n_reg = len(xs)
x_mean, y_mean = sum(xs)/n_reg, sum(ys)/n_reg
num = sum((xs[i]-x_mean)*(ys[i]-y_mean) for i in range(n_reg))
den = sum((xs[i]-x_mean)**2 for i in range(n_reg))
slope = num/den if den else 0
intercept = y_mean - slope * x_mean
xline = [min(xs), max(xs)]
ax.plot(xline, [slope*x+intercept for x in xline], "k--", linewidth=1.5,
        label=f"Trend (slope={slope:.2f}%/1%)")

# correlation
ss_tot = sum((y-y_mean)**2 for y in ys)
ss_res = sum((ys[i]-(slope*xs[i]+intercept))**2 for i in range(n_reg))
r2 = 1 - ss_res/ss_tot if ss_tot else 0
ax.text(0.97, 0.97, f"R² = {r2:.3f}", transform=ax.transAxes,
        ha="right", va="top", fontsize=10, style="italic")

ax.set_xlabel("CLR Resistance Rate (%)", fontsize=11)
ax.set_ylabel("ITT Eradication Rate (%)", fontsize=11)
ax.set_title("ITT Rate vs Clarithromycin Resistance by Treatment Type", fontsize=12, fontweight="bold")
ax.legend(fontsize=9)
ax.grid(alpha=0.2)
plt.tight_layout()
plt.savefig(f"{FIG}/fig5_scatter_clr_resistance.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ fig5_scatter_clr_resistance.png")


# ═══════════════════════════════════════════════════════════════════════════════
# FIG 6: Resistance heatmap by region × antibiotic
# ═══════════════════════════════════════════════════════════════════════════════
antibiotics = ["CLR_Resistance_pct", "MTZ_Resistance_pct", "AMX_Resistance_pct", "LFX_Resistance_pct"]
ab_labels   = ["CLR\n(Clarithromycin)", "MTZ\n(Metronidazole)", "AMX\n(Amoxicillin)", "LFX\n(Levofloxacin)"]
region_col  = "Geographic_Region"
regions = sorted(set(r[region_col] for r in rows if r[region_col]))
# Compute per-region means
matrix = []
for reg in regions:
    row_vals = []
    for ab in antibiotics:
        vals = [r[ab] for r in rows if r[region_col] == reg and r[ab] is not None]
        row_vals.append(sum(vals)/len(vals) if vals else float("nan"))
    matrix.append(row_vals)

fig, ax = plt.subplots(figsize=(9, max(4, len(regions)*0.7 + 1.5)))
mat = np.array(matrix, dtype=float)
im = ax.imshow(mat, cmap="YlOrRd", aspect="auto", vmin=0, vmax=80)
plt.colorbar(im, ax=ax, label="Mean Resistance Rate (%)")
ax.set_xticks(range(len(antibiotics))); ax.set_xticklabels(ab_labels, fontsize=10)
ax.set_yticks(range(len(regions))); ax.set_yticklabels(regions, fontsize=10)
for i in range(len(regions)):
    for j in range(len(antibiotics)):
        val = mat[i, j]
        if not math.isnan(val):
            ax.text(j, i, f"{val:.1f}%", ha="center", va="center",
                    fontsize=9, color="black" if val < 50 else "white", fontweight="bold")
ax.set_title("Mean Antibiotic Resistance by Geographic Region\n(weighted by study-arm count)", fontsize=12, fontweight="bold")
plt.tight_layout()
plt.savefig(f"{FIG}/fig6_resistance_heatmap.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ fig6_resistance_heatmap.png")


# ═══════════════════════════════════════════════════════════════════════════════
# FIG 7: Duration × Treatment type
# ═══════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(9, 5))
dur_groups = collections.defaultdict(lambda: collections.defaultdict(list))
for r in rows:
    if r["ITT_Rate"] is not None and r["Duration_Days"] is not None:
        dur_groups[r["Treatment_Type"]][int(r["Duration_Days"])].append(r["ITT_Rate"])

x_positions = []
x_labels    = []
x_colors    = []
bar_means   = []
bar_errs_lo = []
bar_errs_hi = []
xi = 0
for ttype in ["dual", "triple", "quadruple"]:
    durs = sorted(dur_groups[ttype].keys())
    for d in durs:
        vals = dur_groups[ttype][d]
        m, lo, hi = mean_ci(vals)
        x_positions.append(xi)
        x_labels.append(f"{ttype[:4]}\n{d}d\nn={len(vals)}")
        x_colors.append(PALETTE.get(ttype, "#999"))
        bar_means.append(m)
        bar_errs_lo.append(m - lo)
        bar_errs_hi.append(hi - m)
        xi += 1
    xi += 0.5  # gap between treatment types

bars = ax.bar(x_positions, bar_means, color=x_colors, alpha=0.8, width=0.6)
ax.errorbar(x_positions, bar_means,
            yerr=[bar_errs_lo, bar_errs_hi],
            fmt="none", color="black", capsize=4, linewidth=1.2)
ax.axhline(85, color="red", linestyle="--", linewidth=1.0, alpha=0.8)
ax.axhline(90, color="darkred", linestyle="--", linewidth=1.0, alpha=0.8)
ax.set_xticks(x_positions); ax.set_xticklabels(x_labels, fontsize=8.5)
ax.set_ylabel("Mean ITT Rate (%)", fontsize=11)
ax.set_ylim(60, 100)
ax.set_title("ITT Rate by Treatment Type × Duration", fontsize=12, fontweight="bold")
patches = [mpatches.Patch(color=PALETTE[t], label=t.capitalize()) for t in ["dual","triple","quadruple"]]
ax.legend(handles=patches, fontsize=9)
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(f"{FIG}/fig7_duration_effect.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ fig7_duration_effect.png")


# ═══════════════════════════════════════════════════════════════════════════════
# FIG 8: PPI breakdown within dual therapy
# ═══════════════════════════════════════════════════════════════════════════════
dual_rows = [r for r in rows if r["Is_Dual"] == 1 and r["ITT_Rate"] is not None]
ppi_counts = collections.Counter(r["PPI"] for r in dual_rows)
ppi_order = [p for p, _ in ppi_counts.most_common()]
ppi_colors = {"Vonoprazan": "#E91E63", "Tegoprazan": "#9C27B0",
              "Esomeprazole": "#2196F3", "Rabeprazole": "#03A9F4",
              "Lansoprazole": "#00BCD4", "Omeprazole": "#009688",
              "Pantoprazole": "#4CAF50", "Ilaprazole": "#FF9800", "Unknown": "#999"}

fig, ax = plt.subplots(figsize=(10, 5))
for xi, ppi in enumerate(ppi_order):
    vals = [r["ITT_Rate"] for r in dual_rows if r["PPI"] == ppi]
    m, lo, hi = mean_ci(vals)
    col = ppi_colors.get(ppi, "#999")
    ax.bar(xi, m, color=col, alpha=0.8, width=0.55)
    ax.errorbar(xi, m, yerr=[[m-lo],[hi-m]], fmt="none", color="black", capsize=4)
    jit = [xi + np.random.uniform(-0.15, 0.15) for _ in vals]
    ax.scatter(jit, vals, color=col, s=30, alpha=0.5, zorder=3, edgecolors="white")
    ax.text(xi, m+2, f"{m:.1f}%\nn={len(vals)}", ha="center", fontsize=8, fontweight="bold")

ax.axhline(85, color="red", linestyle="--", linewidth=1.0, alpha=0.8)
ax.axhline(90, color="darkred", linestyle="--", linewidth=1.0, alpha=0.8)
ax.set_xticks(range(len(ppi_order))); ax.set_xticklabels(ppi_order, rotation=30, ha="right", fontsize=9)
ax.set_ylabel("Mean ITT Rate (%)", fontsize=11)
ax.set_ylim(55, 100)
ax.set_title("Dual Therapy ITT Rates by PPI Type\n(P-CABs: Vonoprazan, Tegoprazan)", fontsize=12, fontweight="bold")
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(f"{FIG}/fig8_ppi_comparison_dual.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ fig8_ppi_comparison_dual.png")


# ═══════════════════════════════════════════════════════════════════════════════
# FIG 9: ITT vs PP comparison (paired)
# ═══════════════════════════════════════════════════════════════════════════════
paired = [(r["ITT_Rate"], r["PP_Rate"]) for r in rows
          if r["ITT_Rate"] is not None and r["PP_Rate"] is not None]
fig, ax = plt.subplots(figsize=(6, 6))
itts_p, pps_p = zip(*paired)
ax.scatter(itts_p, pps_p, color="#2196F3", alpha=0.65, s=45, edgecolors="white")
lims = [min(min(itts_p), min(pps_p))-2, max(max(itts_p), max(pps_p))+2]
ax.plot(lims, lims, "k--", linewidth=1.2, label="ITT = PP")
ax.set_xlim(lims); ax.set_ylim(lims)
ax.set_xlabel("ITT Rate (%)", fontsize=11)
ax.set_ylabel("PP Rate (%)", fontsize=11)
ax.set_title(f"ITT vs PP Eradication Rates\n(n={len(paired)} arms with both)", fontsize=12, fontweight="bold")
diffs = [pp - it for it, pp in paired]
ax.text(0.05, 0.95, f"Mean PP−ITT = {sum(diffs)/len(diffs):.1f}pp",
        transform=ax.transAxes, fontsize=10, va="top", style="italic")
ax.legend(fontsize=9)
ax.grid(alpha=0.25)
plt.tight_layout()
plt.savefig(f"{FIG}/fig9_itt_vs_pp.png", dpi=150, bbox_inches="tight")
plt.close()
print("✓ fig9_itt_vs_pp.png")


# ═══════════════════════════════════════════════════════════════════════════════
# Console summary tables
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("TABLE 1: Mean ITT by Treatment Type")
print("═"*60)
print(f"{'Type':<22} {'N':>4} {'Mean':>6} {'SD':>6} {'Min':>5} {'Max':>5} {'≥85%':>5}")
for ttype in ["dual","triple","quadruple","nonbismuth_quadruple"]:
    vals = [r["ITT_Rate"] for r in rows if r["Treatment_Type"] == ttype and r["ITT_Rate"] is not None]
    if not vals: continue
    m = sum(vals)/len(vals)
    sd = math.sqrt(sum((x-m)**2 for x in vals)/(len(vals)-1)) if len(vals)>1 else 0
    n85 = sum(1 for x in vals if x >= 85)
    print(f"  {ttype:<20} {len(vals):>4} {m:>6.1f} {sd:>6.1f} {min(vals):>5.1f} {max(vals):>5.1f} {100*n85/len(vals):>4.0f}%")

print("\n" + "═"*60)
print("TABLE 2: Mean ITT by PPI Class")
print("═"*60)
print(f"{'PPI':<18} {'N':>4} {'Mean':>6} {'SD':>6} {'≥85%':>5} {'≥90%':>5}")
ppis = sorted(set(r["PPI"] for r in rows if r["PPI"]), key=lambda p: -sum(1 for r in rows if r["PPI"]==p))
for ppi in ppis:
    vals = [r["ITT_Rate"] for r in rows if r["PPI"] == ppi and r["ITT_Rate"] is not None]
    if not vals: continue
    m = sum(vals)/len(vals)
    sd = math.sqrt(sum((x-m)**2 for x in vals)/(len(vals)-1)) if len(vals)>1 else 0
    n85 = sum(1 for x in vals if x >= 85)
    n90 = sum(1 for x in vals if x >= 90)
    print(f"  {ppi:<16} {len(vals):>4} {m:>6.1f} {sd:>6.1f} {100*n85/len(vals):>4.0f}% {100*n90/len(vals):>4.0f}%")

print("\n" + "═"*60)
print("TABLE 3: Mean ITT by Geographic Region")
print("═"*60)
print(f"{'Region':<20} {'N':>4} {'Mean':>6} {'CLR resist':>11} {'MTZ resist':>11}")
for reg in sorted(set(r["Geographic_Region"] for r in rows)):
    vals = [r["ITT_Rate"] for r in rows if r["Geographic_Region"]==reg and r["ITT_Rate"] is not None]
    clrs = [r["CLR_Resistance_pct"] for r in rows if r["Geographic_Region"]==reg and r["CLR_Resistance_pct"] is not None]
    mtzs = [r["MTZ_Resistance_pct"] for r in rows if r["Geographic_Region"]==reg and r["MTZ_Resistance_pct"] is not None]
    if not vals: continue
    m = sum(vals)/len(vals)
    clr_m = f"{sum(clrs)/len(clrs):.1f}%" if clrs else "N/A"
    mtz_m = f"{sum(mtzs)/len(mtzs):.1f}%" if mtzs else "N/A"
    print(f"  {reg:<18} {len(vals):>4} {m:>6.1f}  {clr_m:>9}  {mtz_m:>9}")

print("\n" + "═"*60)
print("TABLE 4: High CLR resistance region effect")
print("═"*60)
hi = [r["ITT_Rate"] for r in rows if r["Is_High_CLR_Region"]==1 and r["ITT_Rate"] is not None]
lo_r = [r["ITT_Rate"] for r in rows if r["Is_High_CLR_Region"]==0 and r["ITT_Rate"] is not None]
print(f"  High CLR region (≥30%): n={len(hi)}, mean={sum(hi)/len(hi):.1f}%")
print(f"  Low  CLR region (<30%): n={len(lo_r)}, mean={sum(lo_r)/len(lo_r):.1f}%")

print(f"\n✓ All figures saved to {FIG}/")
