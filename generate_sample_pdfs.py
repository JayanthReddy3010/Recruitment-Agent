"""
Turns 2 of our text resumes into actual PDF files so the PDF-parsing path
has something real to chew on. Run once: python3 generate_sample_pdfs.py
Not part of the main app - just a data-prep helper.
"""
import os
from fpdf import FPDF

HERE = os.path.dirname(__file__)
RESUME_DIR = os.path.join(HERE, "data", "resumes")
PDF_DIR = os.path.join(HERE, "data", "resumes_pdf")

# a couple of candidates get a "real" PDF version instead of / alongside the txt
PDF_CANDIDATES = ["candidate_10", "candidate_17"]


def make_pdf(txt_path, pdf_path):
    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()

    pdf = FPDF(format="A4")
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    pdf.set_auto_page_break(auto=True, margin=15)
    for line in text.split("\n"):
        if line.strip() == "":
            pdf.ln(4)
        else:
            pdf.multi_cell(pdf.epw, 6, line)
    pdf.output(pdf_path)


def main():
    os.makedirs(PDF_DIR, exist_ok=True)
    for cid in PDF_CANDIDATES:
        src = os.path.join(RESUME_DIR, f"{cid}.txt")
        dst = os.path.join(PDF_DIR, f"{cid}.pdf")
        make_pdf(src, dst)
        print(f"wrote {dst}")


if __name__ == "__main__":
    main()
