"""
Build the Word (.docx) export of the manuscript.

Renders the LaTeX section files in document order, resolves \\cite{} keys to
numbered callouts in citation order, embeds the main and supplementary
figures, and appends Supplementary Tables S1 and S2 plus the bibliography.

Output: paper/my_version/word_doc/main_my_version.docx
"""
import re
from pathlib import Path
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

ROOT = Path("/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/paper/my_version")
DST = ROOT / "word_doc" / "main_my_version.docx"
FIG = Path("/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/figures/MAIN_FIGURES")
DST.parent.mkdir(parents=True, exist_ok=True)

FIGURE_AFTER = {
    "section_3_1_study_selection": [(FIG / "Fig1_PRISMA.png",
        "Figure 1. Study selection and analytic pipeline (PRISMA flow diagram). "
        "140 arms from 60 RCTs entered the final analysis.", 6.0)],
    "section_3_3_bayesian": [(FIG / "Fig2_Bayesian_forest.png",
        "Figure 2. Bayesian hierarchical posterior effect sizes. "
        "sigma_study = 0.512 [0.406-0.644]; max R-hat = 1.010; min ESS = 1006.", 6.0)],
    "section_3_4_subgroup_sensitivity": [(FIG / "Fig3_subgroup_forest.png",
        "Figure 3. Subgroup forest plot. High-CLR OR 1.98 [1.53, 2.57] vs "
        "low-CLR OR 1.04 [0.65, 1.65]; interaction p = 0.0003.", 6.0)],
    "section_3_5_predictive": [
        (FIG / "Fig4_calibration.png",
         "Figure 4. Calibration of marginal predictions. Bayesian hierarchical: "
         "slope = 1.070, intercept = -0.074, Brier = 0.0086.", 5.0),
        (FIG / "Fig5_SHAP_importance.png",
         "Figure 5. SHAP attributions for the final predictive model "
         "(RFE top-10 + RandomForest).", 6.0)],
}
SUPP_FIGS = [
    (FIG / "SuppFig_funnel.png",
     "Supplementary Figure S1. Funnel plot. Egger's intercept = 0.139 (p = 0.88).", 5.5),
    (FIG / "SuppFig_sensitivity.png",
     "Supplementary Figure S2. Sensitivity forest. Vonoprazan OR remains "
     "1.65-1.75 across sequential exclusions.", 5.5),
]

SECTIONS = [
    ("abstract", None), ("section_1_introduction", None),
    ("__H1__", "Methods"),
    ("section_2_1_search_strategy", None), ("section_2_2_data_extraction", None),
    ("section_2_3_feature_engineering", None), ("section_2_4_inference", None),
    ("section_2_5_prediction", None), ("section_2_6_software", None),
    ("__H1__", "Results"),
    ("section_3_1_study_selection", None), ("table_1_characteristics", None),
    ("section_3_2_pooled_frequentist", None), ("section_3_3_bayesian", None),
    ("__BAYESTAB__", None),
    ("section_3_4_subgroup_sensitivity", None), ("section_3_5_predictive", None),
    ("table_2_regression", None), ("table_3_classification", None),
    ("section_3_6_findings_summary", None), ("section_4_discussion", None),
    ("section_5_conclusions", None), ("__DECL__", None),
]

SUBS = [
    (r"\\textit\{([^{}]*)\}", r"*\1*"), (r"\\emph\{([^{}]*)\}", r"*\1*"),
    (r"\\textbf\{([^{}]*)\}", r"**\1**"), (r"\\mathbf\{([^{}]*)\}", r"**\1**"),
    (r"\\url\{([^{}]*)\}", r"\1"), (r"\\href\{([^{}]*)\}\{([^{}]*)\}", r"\2 (\1)"),
    (r"\\texttt\{([^{}]*)\}", r"`\1`"), (r"\\text\{([^{}]*)\}", r"\1"),
    (r"\\textrm\{([^{}]*)\}", r"\1"),
    (r"\$\\hat\{R\}\$", "R-hat"), (r"\\hat\{R\}", "R-hat"),
    (r"\\sigma_\{\\text\{study\}\}", "sigma_study"),
    (r"\\tau\^2", "tau-squared"), (r"I\^2", "I-squared"), (r"R\^2", "R-squared"),
    (r"N_\{\\text\{ITT\}\}", "N_ITT"),
    (r"\\times", "x"), (r"\\geq", ">="), (r"\\leq", "<="),
    (r"\\downarrow", "(down)"), (r"\\uparrow", "(up)"),
    (r"\\label\{[^}]*\}", ""), (r"\\ref\{fig:prisma\}", "Figure 1"),
    (r"\\ref\{fig:bayes\}", "Figure 2"), (r"\\ref\{fig:subgroup\}", "Figure 3"),
    (r"\\ref\{fig:calibration\}", "Figure 4"), (r"\\ref\{fig:shap\}", "Figure 5"),
    (r"\\ref\{tab:characteristics\}", "Table 1"), (r"\\ref\{tab:regression\}", "Table 2"),
    (r"\\ref\{tab:classification\}", "Table 3"),
    (r"\\ref\{tab:bayesian\}", "the Bayesian posterior table"),
    (r"\\ref\{[^}]*\}", ""), (r"\$([^$]*)\$", r"\1"),
    (r"\\&", "&"), (r"\\%", "%"), (r"\\_", "_"), (r"\\#", "#"),
    (r"\\,", " "), (r"\\;", " "), (r"~", " "),
]


def clean(s):
    for pat, rep in SUBS:
        s = re.sub(pat, rep, s)
    s = s.replace("H.\\ pylori", "H. pylori").replace("\\ ", " ")
    s = s.replace("--", "\u2013").replace("\\{", "{").replace("\\}", "}")
    s = re.sub(r"\\[a-zA-Z]+\*?(\{[^}]*\})?", "", s)
    s = re.sub(r"[{}]", "", s)
    return re.sub(r"\s+", " ", s).strip()


cites = {}
def sub_cites(s):
    def r(m):
        return "[" + ", ".join(
            str(cites.setdefault(k.strip(), len(cites) + 1))
            for k in m.group(1).split(",")) + "]"
    return re.sub(r"\\cite\{([^}]+)\}", r, s)


doc = Document()
doc.styles["Normal"].font.name = "Calibri"
doc.styles["Normal"].font.size = Pt(11)


def inline(p, s):
    for m in re.finditer(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|[^*`]+)", s):
        tok = m.group(0)
        if tok.startswith("**"):
            p.add_run(tok[2:-2]).bold = True
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
            p.add_run(tok[1:-1]).italic = True
        elif tok.startswith("`"):
            p.add_run(tok[1:-1]).font.name = "Consolas"
        else:
            p.add_run(tok)


def add_fig(path, cap, w):
    if not path.exists():
        return
    q = doc.add_paragraph(); q.alignment = WD_ALIGN_PARAGRAPH.CENTER
    q.add_run().add_picture(str(path), width=Inches(w))
    c = doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = c.add_run(cap); r.italic = True; r.font.size = Pt(10)


FLAT_HEADERS = {
    "table_3_classification": [
        "Model", "LOO >=85% AUC", "LOO >=85% Brier", "LOO >=90% AUC",
        "LOO >=90% Brier", "LOSO >=85% AUC", "LOSO >=85% Brier",
        "LOSO >=90% AUC", "LOSO >=90% Brier"],
}


def tex_table(tex, name):
    """Render a LaTeX tabular/longtable into a Word table."""
    cap = re.search(r"\\caption\{(.*?)\}\s*\\?\\?\s*\n", tex, re.DOTALL)
    if cap:
        doc.add_heading(clean(sub_cites(cap.group(1)))[:180], level=2)
    rows = []
    flat = FLAT_HEADERS.get(name)
    if flat:
        rows.append(("head", flat))
    for ln in tex.splitlines():
        ln = ln.strip()
        if "&" not in ln or not ln.endswith("\\\\"):
            continue
        if "multicolumn" in ln:
            if flat:
                continue
            cells = [clean(re.sub(r"\\multicolumn\{\d+\}\{[^}]*\}\{([^}]*)\}", r"\1", ln[:-2]))]
            rows.append(("head", cells)); continue
        rows.append(("row", [clean(sub_cites(c)) for c in ln[:-2].split("&")]))
    if not rows:
        return
    ncol = max(len(c) for _, c in rows)
    tbl = doc.add_table(rows=len(rows), cols=ncol)
    tbl.style = "Light Grid Accent 1"
    for i, (kind, cells) in enumerate(rows):
        for j in range(ncol):
            cell = tbl.rows[i].cells[j]; cell.text = ""
            val = cells[j] if j < len(cells) else ""
            para = cell.paragraphs[0]
            inline(para, val)                      # renders **bold** / *italic*
            hdr = kind == "head" or (i == 0 and not flat)
            for run in para.runs:
                run.font.size = Pt(9)
                if hdr:
                    run.bold = True
    doc.add_paragraph()


def render(tex, tag=""):
    tex = sub_cites(re.sub(r"(?<!\\)%.*", "", tex))
    if re.search(r"\\begin\{(tabular|longtable)\}", tex):
        tex_table(tex, tag); return
    tex = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", tex, re.DOTALL).group(1) \
        if "\\begin{abstract}" in tex else tex
    tex = re.sub(r"\\subsection\*?\{([^}]+)\}", r"\n\n@@H2@@\1\n\n", tex)
    tex = re.sub(r"\\section\*?\{([^}]+)\}", r"\n\n@@H1@@\1\n\n", tex)
    tex = re.sub(r"\\paragraph\{([^}]+)\}", r"\n\n@@B@@\1 ", tex)
    for blk in re.split(r"\n\s*\n", tex):
        blk = blk.strip()
        if not blk:
            continue
        if blk.startswith("@@H1@@"):
            doc.add_heading(clean(blk[6:]), level=1); continue
        if blk.startswith("@@H2@@"):
            doc.add_heading(clean(blk[6:]), level=2); continue
        lead = ""
        if blk.startswith("@@B@@"):
            m = re.match(r"@@B@@(.*?\.)\s*(.*)", blk, re.DOTALL)
            lead, blk = (clean(m.group(1)), m.group(2)) if m else (clean(blk[5:]), "")
        body = clean(re.sub(r"\s*\n\s*", " ", blk))
        if not body and not lead:
            continue
        p = doc.add_paragraph()
        if lead:
            p.add_run(lead + " ").bold = True
        inline(p, body)


doc.add_heading("Predicting and explaining Helicobacter pylori eradication efficacy "
                "across 140 RCT arms: a Bayesian hierarchical meta-analysis with "
                "machine-learning-assisted modelling", level=0)
for _a, _aff in [("Sepehr Maleki", "Department of Computer Engineering, Bilkent University, Ankara, Turkey"),
                 ("Hamid Mohaghegh Shalmani", "Research Institute for Gastroenterology and Liver Diseases, Shahid Beheshti University of Medical Sciences, Tehran, Iran")]:
    _p = doc.add_paragraph(); _p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _p.add_run(_a).bold = True
    _r = _p.add_run("\n" + _aff); _r.italic = True; _r.font.size = Pt(9.5)

for name, arg in SECTIONS:
    if name == "__H1__":
        doc.add_heading(arg, level=1)
    elif name == "__BAYESTAB__":
        m = re.search(r"\\begin\{table\}.*?tab:bayesian.*?\\end\{table\}",
                      (ROOT / "main_my_version.tex").read_text(encoding="utf-8"), re.DOTALL)
        if m:
            render(m.group(0), "bayes_table")
    elif name == "__DECL__":
        doc.add_heading("Declarations", level=1)
        for lab, body in [
            ("Ethics approval and consent to participate.", "Not applicable. This study is a meta-analysis of previously published, ethically approved randomised controlled trials. No primary patient data were collected."),
            ("Consent for publication.", "Not applicable."),
            ("Availability of data and materials.", "The harmonised dataset, all analysis code, the deployable predictive model, model card, and a frozen pipeline manifest are publicly available at https://github.com/sepehrmaleki369/helicobacter-pylori-eradication-meta-analysis."),
            ("Competing interests.", "The authors declare no competing interests."),
            ("Funding.", "This research received no specific grant from any funding agency in the public, commercial, or not-for-profit sectors."),
            ("Authors' contributions.", "SM conceived the study, performed the literature search and data extraction, developed the analysis pipeline, carried out the statistical and machine-learning analyses, and drafted the manuscript. HMS contributed clinical and methodological expertise, performed the Cochrane Risk of Bias 2.0 assessment of all included trials, adjudicated trial eligibility, and critically revised the manuscript. Both authors read and approved the final manuscript."),
            ("Acknowledgements.", "We thank Dr Mohammad Rostami-Nejad for helpful discussions and valuable input during the preparation of this work."),
            ("Use of artificial intelligence.", "During manuscript preparation, Anthropic's Claude was used to assist with language editing, document formatting, code review, data-checking workflows, and drafting of explanatory text. All scientific decisions, data extraction, statistical analyses, interpretation of results, risk-of-bias judgments, and final manuscript content were reviewed and approved by the authors. The authors take full responsibility for the accuracy, integrity, and originality of the work."),
        ]:
            p = doc.add_paragraph(); p.add_run(lab + " ").bold = True; p.add_run(body)
    else:
        f = ROOT / f"{name}.tex"
        if not f.exists():
            print("  missing:", f.name); continue
        render(f.read_text(encoding="utf-8"), name)
        for fp, fc, fw in FIGURE_AFTER.get(name, []):
            add_fig(fp, fc, fw)

doc.add_page_break()
doc.add_heading("Supplementary Material", level=1)
doc.add_heading("Supplementary Figures", level=2)
for fp, fc, fw in SUPP_FIGS:
    add_fig(fp, fc, fw)
for s in ["supp_table_s1", "supp_table_s2"]:
    doc.add_page_break()
    render((ROOT / f"{s}.tex").read_text(encoding="utf-8"), s)

# Bibliography, in citation order
bib = (ROOT / "references.bib").read_text(encoding="utf-8")
entries, starts = {}, [m.start() for m in re.finditer(r"^@\w+\s*\{", bib, re.M)] + [len(bib)]
for s, e in zip(starts[:-1], starts[1:]):
    blk = bib[s:e]
    m = re.match(r"@(\w+)\s*\{\s*([^,]+),", blk)
    if not m:
        continue
    f = {}
    for fm in re.finditer(r"(\w+)\s*=\s*\{", blk):
        k, i, d = fm.group(1).lower(), fm.end() - 1, 0
        for j in range(i, len(blk)):
            d += (blk[j] == "{") - (blk[j] == "}")
            if d == 0:
                f[k] = blk[i + 1:j]; break
    entries[m.group(2).strip()] = f

doc.add_page_break()
doc.add_heading("References", level=1)
for key, n in sorted(cites.items(), key=lambda kv: kv[1]):
    f = entries.get(key, {})
    bits = [clean(f.get("author", "")).replace(" and ", ", "), clean(f.get("title", ""))]
    loc = clean(f.get("journal", f.get("booktitle", "")))
    if loc:
        if f.get("volume"): loc += " " + clean(f["volume"])
        if f.get("number"): loc += f"({clean(f['number'])})"
        if f.get("pages"): loc += ":" + clean(f["pages"])
        if f.get("year"): loc += ", " + clean(f["year"])
    elif f.get("year"):
        loc = clean(f["year"])
    bits.append(loc)
    if f.get("doi"): bits.append("DOI: " + clean(f["doi"]))
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.3)
    p.paragraph_format.first_line_indent = Inches(-0.3)
    p.add_run(f"[{n}] " + ". ".join(b for b in bits if b) + ".").font.size = Pt(10)

doc.save(DST)
print(f"Wrote {DST} ({DST.stat().st_size:,} bytes); {len(cites)} citations resolved")
