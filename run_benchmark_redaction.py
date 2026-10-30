from pathlib import Path
import shutil

import pymupdf
from docx import Document

from phi_detector import LocalPHIDetector, replace_findings


BASE_DIR = Path(__file__).resolve().parent

BENCHMARK_DIR = BASE_DIR / "phi_redaction_benchmark"

PDF_INPUT_DIR = BENCHMARK_DIR / "inputs" / "pdf"
DOCX_INPUT_DIR = BENCHMARK_DIR / "inputs" / "docx"

OUTPUT_DIR = BENCHMARK_DIR / "redacted_outputs"
PDF_OUTPUT_DIR = OUTPUT_DIR / "pdf"
DOCX_OUTPUT_DIR = OUTPUT_DIR / "docx"

PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DOCX_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

detector = LocalPHIDetector(score_threshold=0.60)


def redact_pdf(input_path: Path, output_path: Path):
    print(f"Processing PDF: {input_path.name}")

    document = pymupdf.open(input_path)

    try:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text", sort=True)

            if not text.strip():
                print(
                    f"  Page {page_number}: "
                    "no selectable text; local OCR is required"
                )
                continue

            page_has_redactions = False

            for finding in detector.detect(text):
                value = text[finding.start:finding.end].strip()

                if not value:
                    continue

                rectangles = page.search_for(
                    value,
                    flags=pymupdf.TEXT_DEHYPHENATE,
                )

                for rectangle in rectangles:
                    page.add_redact_annot(
                        rectangle,
                        fill=(0, 0, 0),
                    )

                if rectangles:
                    page_has_redactions = True

            if page_has_redactions:
                page.apply_redactions(
                    images=pymupdf.PDF_REDACT_IMAGE_PIXELS
                )

        document.save(
            output_path,
            garbage=4,
            clean=True,
            deflate=True,
        )

    finally:
        document.close()


def redact_docx(input_path: Path, output_path: Path):
    print(f"Processing DOCX: {input_path.name}")

    document = Document(input_path)

    def process_paragraph(paragraph):
        original_text = paragraph.text

        if not original_text.strip():
            return

        findings = detector.detect(original_text)

        sanitized_text, _ = replace_findings(
            original_text,
            findings,
        )

        if sanitized_text != original_text:
            paragraph.text = sanitized_text

    def process_table(table):
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    process_paragraph(paragraph)

                for nested_table in cell.tables:
                    process_table(nested_table)

    # Main paragraphs
    for paragraph in document.paragraphs:
        process_paragraph(paragraph)

    # Main tables
    for table in document.tables:
        process_table(table)

    # Headers and footers
    for section in document.sections:
        for paragraph in section.header.paragraphs:
            process_paragraph(paragraph)

        for table in section.header.tables:
            process_table(table)

        for paragraph in section.footer.paragraphs:
            process_paragraph(paragraph)

        for table in section.footer.tables:
            process_table(table)

    # Remove document metadata
    properties = document.core_properties

    metadata_fields = [
        "author",
        "category",
        "comments",
        "content_status",
        "identifier",
        "keywords",
        "language",
        "last_modified_by",
        "subject",
        "title",
        "version",
    ]

    for field in metadata_fields:
        try:
            setattr(properties, field, "")
        except (AttributeError, ValueError):
            pass

    document.save(output_path)


def clear_previous_outputs():
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DOCX_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    clear_previous_outputs()

    pdf_files = sorted(PDF_INPUT_DIR.glob("*.pdf"))
    docx_files = sorted(DOCX_INPUT_DIR.glob("*.docx"))

    print(f"PDF inputs found: {len(pdf_files)}")
    print(f"DOCX inputs found: {len(docx_files)}")
    print(f"Total inputs: {len(pdf_files) + len(docx_files)}")

    print("\nProcessing PDF files")

    for input_path in pdf_files:
        output_path = (
            PDF_OUTPUT_DIR
            / f"{input_path.stem}_redacted.pdf"
        )

        redact_pdf(input_path, output_path)

    print("\nProcessing DOCX files")

    for input_path in docx_files:
        output_path = (
            DOCX_OUTPUT_DIR
            / f"{input_path.stem}_redacted.docx"
        )

        redact_docx(input_path, output_path)

    print("\n================================")
    print("BATCH REDACTION FINISHED")
    print("================================")

    generated_pdfs = list(PDF_OUTPUT_DIR.glob("*.pdf"))
    generated_docx = list(DOCX_OUTPUT_DIR.glob("*.docx"))

    print(f"Redacted PDFs: {len(generated_pdfs)}")
    print(f"Redacted DOCX files: {len(generated_docx)}")
    print(
        f"Total outputs: "
        f"{len(generated_pdfs) + len(generated_docx)}"
    )


if __name__ == "__main__":
    main()