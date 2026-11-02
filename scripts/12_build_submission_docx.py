"""
Build the submission-ready Word (.docx) manuscript from the with-RoB source.

Walks paper/with rob test/main.tex sequentially so that sections, figures,
and tables appear in document order, resolves \\cite{} keys to numbered
callouts, embeds every figure, expands the \\input{} supplementary tables,
and appends the bibliography in citation order.

Output: paper/with rob test/word_doc/main_with_rob.docx
"""
import re
from pathlib import Path
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

BASE = Path("/Users/sepehrmaleki/Documents/spring 2026/helico pilouri")
SRC = BASE / "paper/with rob test/main.tex"
ROOT = SRC.parent
DST = ROOT / "word_doc" / "main_with_rob.docx"
DST.parent.mkdir(parents=True, exist_ok=True)

TITLE = ("Predicting and explaining Helicobacter pylori eradication efficacy "
         "across 140 RCT arms: a Bayesian hierarchical meta-analysis with "
         "machine-learning-assisted modelling")

# Tables whose LaTeX header uses nested \multicolumn and needs a flat header.
FLAT_HEADERS = {
    "tab:classification": [
        "Model", "LOO >=85% AUC", "LOO >=85% Brier", "LOO >=90% AUC",
        "LOO >=90% Brier", "LOSO >=85% AUC", "LOSO >=85% Brier",
        "LOSO >=90% AUC", "LOSO >=90% Brier"],
}

SUBS = [
    (r"\\textit\{([^{}]*)\}", r"*\1*"), (r"\\emph\{([^{}]*)\}", r"*\1*"),
    (r"\\textbf\{([^{}]*)\}", r"**\1**"), (r"\\mathbf\{([^{}]*)\}", r"**\1**"),
    (r"\\url\{([^{}]*)\}", r"\1"), (r"\\href\{([^{}]*)\}\{([^{}]*)\}", r"\2 (\1)"),
    (r"\\texttt\{([^{}]*)\}", r"`\1`"), (r"\\text\{([^{}]*)\}", r"\1"),
    (r"\\textrm\{([^{}]*)\}", r"\1"), (r"\\textsuperscript\{([^{}]*)\}", r"\1"),
    (r"\$\\hat\{R\}\$", "R-hat"), (r"\\hat\{R\}", "R-hat"),
    (r"\\sigma_\{\\text\{study\}\}", "sigma_study"), (r"\\sigma", "sigma"),
    (r"\\tau\^2", "tau-squared"), (r"I\^2", "I-squared"), (r"R\^2", "R-squared"),
    (r"N_\{\\text\{ITT\}\}", "N_ITT"), (r"\\kappa", "kappa"), (r"\\tau\b", "\u03c4"), (r"\\alpha\b", "\u03b1"),
    (r"\\beta\b", "\u03b2"), (r"\\mathcal\{N\}", "Normal"),
    (r"\\times", "x"), (r"\\geq", ">="), (r"\\leq", "<="), (r"\\equiv", "="),
    (r"\\downarrow", "(down)"), (r"\\uparrow", "(up)"),
    (r"\\label\{[^}]*\}", ""),
    # Strip a preceding "Table"/"Figure" word so \ref expansion doesn't duplicate it.
    (r"\b(?:Table|Figure)s?~?\s*(?=\\ref\{(?:tab|fig):)", ""),
    (r"\\ref\{fig:prisma\}", "Figure 1"), (r"\\ref\{fig:rob\}", "Figure 2"),
    (r"\\ref\{fig:bayes\}", "Figure 3"), (r"\\ref\{fig:subgroup\}", "Figure 4"),
    (r"\\ref\{fig:calibration\}", "Figure 5"), (r"\\ref\{fig:shap\}", "Figure 6"),
    (r"\\ref\{fig:supp_rob\}", "Supplementary Figure S1"),
    (r"\\ref\{fig:supp_funnel\}", "Supplementary Figure S2"),
    (r"\\ref\{fig:supp_sens\}", "Supplementary Figure S3"),
    (r"\\ref\{fig:supp_models\}", "Supplementary Figure S4"),
    (r"\\ref\{tab:characteristics\}", "Table 1"),
    (r"\\ref\{tab:bayesian\}", "Table 2"),
    (r"\\ref\{tab:robsens\}", "Table 3"),
    (r"\\ref\{tab:regression\}", "Table 4"),
    (r"\\ref\{tab:classification\}", "Table 5"),
    (r"\\ref\{tab:supp_studies\}", "Supplementary Table S1"),
    (r"\\ref\{tab:supp_excluded\}", "Supplementary Table S2"),
    (r"\\ref\{tab:supp_rob\}", "Supplementary Table S3"),
    (r"\\ref\{[^}]*\}", ""), (r"\$([^$]*)\$", r"\1"),
    (r"\\&", "&"), (r"\\%", "%"), (r"\\_", "_"), (r"\\#", "#"),
    (r"\\,", " "), (r"\\;", " "), (r"~", " "),
]


def clean(s):
    for pat, rep in SUBS:
        s = re.sub(pat, rep, s)
    s = s.replace("H.\\ pylori", "H. pylori").replace("\\ ", " ")
    s = s.replace("---", "\u2013").replace("--", "\u2013")
    s = s.replace("``", "\u201c").replace("''", "\u201d")
    s = s.replace("\\{", "{").replace("\\}", "}")
    s = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^{}]*\})?", "", s)
    s = re.sub(r"[{}]", "", s)
    return re.sub(r"\s+", " ", s).strip()


cites = {}
def sub_cites(s):
    def r(m):
        return "[" + ", ".join(str(cites.setdefault(k.strip(), len(cites) + 1))
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


def para(text, lead=""):
    text = clean(text)
    if not text and not lead:
        return
    p = doc.add_paragraph()
    if lead:
        p.add_run(lead + " ").bold = True
    inline(p, text)


def add_figure(block):
    m = re.search(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", block)
    if not m:
        return
    path = (ROOT / m.group(1)).resolve()
    wm = re.search(r"width=([\d.]+)\\textwidth", block)
    width = 6.3 * float(wm.group(1)) if wm else 5.5
    cap = re.search(r"\\caption\{(.*?)\}\s*\n?\s*\\label", block, re.DOTALL) \
        or re.search(r"\\caption\{(.*)\}", block, re.DOTALL)
    if path.exists():
        q = doc.add_paragraph(); q.alignment = WD_ALIGN_PARAGRAPH.CENTER
        q.add_run().add_picture(str(path), width=Inches(min(width, 6.3)))
    else:
        doc.add_paragraph().add_run(f"[missing figure: {path.name}]").italic = True
    if cap:
        c = doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = c.add_run(clean(sub_cites(cap.group(1)))); r.italic = True; r.font.size = Pt(9.5)


def add_table(block):
    lab = re.search(r"\\label\{([^}]+)\}", block)
    lab = lab.group(1) if lab else ""
    cap = re.search(r"\\caption\{(.*?)\}\s*\\?\\?\s*\n", block, re.DOTALL)
    if cap:
        doc.add_heading(clean(sub_cites(cap.group(1))), level=3)
    flat = FLAT_HEADERS.get(lab)
    rows = [("head", flat)] if flat else []
    for ln in block.splitlines():
        ln = ln.strip()
        if "&" not in ln or not ln.endswith("\\\\"):
            continue
        if "multicolumn" in ln:
            if flat:
                continue
            rows.append(("head", [clean(re.sub(
                r"\\multicolumn\{\d+\}\{[^}]*\}\{([^}]*)\}", r"\1", ln[:-2]))]))
            continue
        rows.append(("row", [clean(sub_cites(c)) for c in ln[:-2].split("&")]))
    rows = [(k, c) for k, c in rows if any(x for x in c)]
    if not rows:
        return
    ncol = max(len(c) for _, c in rows)
    tbl = doc.add_table(rows=len(rows), cols=ncol)
    tbl.style = "Light Grid Accent 1"
    for i, (kind, cells) in enumerate(rows):
        hdr = kind == "head" or (i == 0 and not flat)
        for j in range(ncol):
            cell = tbl.rows[i].cells[j]; cell.text = ""
            pp = cell.paragraphs[0]
            inline(pp, cells[j] if j < len(cells) else "")
            for run in pp.runs:
                run.font.size = Pt(8.5)
                if hdr:
                    run.bold = True
    doc.add_paragraph()


MATH_MAP = [
    (r"\\text\{([^{}]*)\}", r"\1"), (r"\\mathcal\{N\}", "Normal"),
    (r"\\sim", "~"), (r"\\alpha", "\u03b1"), (r"\\beta", "\u03b2"),
    (r"\\sigma", "\u03c3"), (r"\\quad", "   "), (r"\\,", " "),
    (r"_\{([^{}]*)\}", r"_\1"), (r"\^\{([^{}]*)\}", r"^\1"),
]


def add_math(block):
    """Render an align/equation environment as a monospaced plain-text block."""
    body = re.sub(r"\\(begin|end)\{(align|equation|gather)\*?\}", "", block)
    for line in body.split("\\\\"):
        line = line.strip()
        if not line:
            continue
        for pat, rep in MATH_MAP:
            line = re.sub(pat, rep, line)
        line = line.replace("&", "").replace("\\", "")
        line = re.sub(r"[{}]", "", line)
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            continue
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.5)
        r = p.add_run(line)
        r.font.name = "Consolas"
        r.font.size = Pt(10)


def walk(tex):
    """Render a LaTeX body sequentially: headings, figures, tables, prose."""
    tex = re.sub(r"(?<!\\)%.*", "", tex)
    tokens = re.split(r"(\\begin\{(?:figure|table|longtable|align\*?|equation\*?|gather\*?)\}.*?"
                      r"\\end\{(?:figure|table|longtable|align\*?|equation\*?|gather\*?)\}"
                      r"|\\input\{[^}]+\})",
                      tex, flags=re.DOTALL)
    for tok in tokens:
        if not tok or not tok.strip():
            continue
        if tok.startswith("\\begin{figure}"):
            add_figure(tok); continue
        if tok.startswith("\\begin{table}") or tok.startswith("\\begin{longtable}"):
            add_table(tok); continue
        if re.match(r"\\begin\{(align|equation|gather)", tok):
            add_math(tok); continue
        if tok.startswith("\\input{"):
            name = re.match(r"\\input\{([^}]+)\}", tok).group(1)
            f = ROOT / f"{name}.tex"
            if f.exists():
                doc.add_page_break()
                add_table(f.read_text(encoding="utf-8"))
            continue
        chunk = sub_cites(tok)
        chunk = re.sub(r"\\subsection\*?\{([^}]+)\}", r"\n\n@@H2@@\1\n\n", chunk)
        chunk = re.sub(r"\\section\*?\{([^}]+)\}", r"\n\n@@H1@@\1\n\n", chunk)
        chunk = re.sub(r"\\paragraph\{([^}]+)\}", r"\n\n@@B@@\1 ", chunk)
        chunk = re.sub(r"\\(begin|end)\{(itemize|enumerate)\}", "", chunk)
        for blk in re.split(r"\n\s*\n", chunk):
            blk = blk.strip()
            if not blk:
                continue
            if blk.startswith("@@H1@@"):
                doc.add_heading(clean(blk[6:]), level=1); continue
            if blk.startswith("@@H2@@"):
                doc.add_heading(clean(blk[6:]), level=2); continue
            if blk.startswith("@@B@@"):
                m = re.match(r"@@B@@(.*?\.)\s*(.*)", blk, re.DOTALL)
                if m:
                    para(re.sub(r"\s*\n\s*", " ", m.group(2)), clean(m.group(1)))
                else:
                    para("", clean(blk[5:]))
                continue
            for item in re.split(r"\\item\s+", blk):
                item = item.strip()
                if item:
                    para(re.sub(r"\s*\n\s*", " ", item))


body = SRC.read_text(encoding="utf-8")
doc.add_heading(TITLE, level=0)
for _a, _aff in [("Sepehr Maleki", "Department of Computer Engineering, Bilkent University, Ankara, Turkey"),
                 ("Hamid Mohaghegh Shalmani", "Research Institute for Gastroenterology and Liver Diseases, Shahid Beheshti University of Medical Sciences, Tehran, Iran")]:
    _p = doc.add_paragraph(); _p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _p.add_run(_a).bold = True
    _r = _p.add_run("\n" + _aff); _r.italic = True; _r.font.size = Pt(9.5)

abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", body, re.DOTALL)
doc.add_heading("Abstract", level=1)
walk(abstract.group(1))

main_body = body[body.index("\\section{Introduction}"):body.index("\\bibliographystyle")]
walk(main_body)

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

# Supplementary material (tables via \input, then the supplementary figures)
supp = body[body.index("\\section*{Supplementary Material}"):]
doc.add_page_break()
doc.add_heading("Supplementary Material", level=1)
walk(supp.replace("\\section*{Supplementary Material}", ""))

doc.save(DST)
print(f"Wrote {DST}")
print(f"  size {DST.stat().st_size:,} bytes | {len(cites)} citations resolved")
