"""Extract raw text from all PDFs into individual .txt files."""
import pdfplumber
import os
import re

PDF_DIRS = [
    "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/papers_29_79",
    "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri",
]
OUT_DIR = "/Users/sepehrmaleki/Documents/spring 2026/helico pilouri/project/data/raw_text"

# Papers in the root dir that belong to the study (not duplicates)
ROOT_PDFS = {
    "dkz046 -1.pdf": "36_TaiWC_2019",  # duplicate of papers_29_79/36_TaiWC_2019.pdf — skip
}

def extract_text(pdf_path):
    text_pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_pages.append(t)
    return "\n\n--- PAGE BREAK ---\n\n".join(text_pages)

processed = []
skipped = []

for pdf_dir in PDF_DIRS:
    for fname in sorted(os.listdir(pdf_dir)):
        if not fname.endswith(".pdf"):
            continue

        fpath = os.path.join(pdf_dir, fname)

        # For the root dir, only process numbered files (already in papers_29_79) if needed
        # Skip duplicates in root dir
        if pdf_dir.endswith("helico pilouri"):
            # Skip files that are already in papers_29_79 under a different name
            # We rely on papers_29_79 as the canonical source
            continue

        # Derive output name from filename (strip .pdf)
        stem = re.sub(r"\.pdf$", "", fname)
        out_path = os.path.join(OUT_DIR, f"{stem}.txt")

        if os.path.exists(out_path):
            print(f"  SKIP (exists): {fname}")
            processed.append(stem)
            continue

        try:
            text = extract_text(fpath)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"  OK: {fname} ({len(text):,} chars)")
            processed.append(stem)
        except Exception as e:
            print(f"  ERROR: {fname}: {e}")
            skipped.append(fname)

print(f"\nDone: {len(processed)} extracted, {len(skipped)} errors")
print("Files:", sorted(os.listdir(OUT_DIR))[:5], "...")
