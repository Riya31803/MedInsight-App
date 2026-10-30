from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import fitz
from docx import Document


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def docx_text(path: Path) -> str:
    doc = Document(path)
    values = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            values.extend(cell.text for cell in row.cells)
    for section in doc.sections:
        values.extend(p.text for p in section.header.paragraphs)
        values.extend(p.text for p in section.footer.paragraphs)
    return "\n".join(values)


def pdf_text(path: Path) -> str:
    with fitz.open(path) as doc:
        return "\n".join(page.get_text() for page in doc)


def extract(path: Path) -> str:
    return pdf_text(path) if path.suffix.lower() == ".pdf" else docx_text(path)


def score_file(output: Path, phi_values: list[str], preserve_values: list[str]):
    text = normalize(extract(output))
    leaked = [v for v in phi_values if normalize(v) in text]
    missing = [v for v in preserve_values if normalize(v) not in text]
    recall = (len(phi_values) - len(leaked)) / len(phi_values) if phi_values else 1.0
    preservation = (len(preserve_values) - len(missing)) / len(preserve_values) if preserve_values else 1.0
    return {"phi_recall": recall, "leaked_phi": leaked, "preservation": preservation, "missing_clinical": missing}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--outputs", type=Path, required=True, help="Folder containing pdf/ and docx/ redacted outputs")
    args = parser.parse_args()
    manifest = json.loads((args.benchmark / "ground_truth.json").read_text(encoding="utf-8"))
    results = []
    for case in manifest:
        for modality in ("pdf", "docx"):
            input_path = args.benchmark / case[f"{modality}_input"]
            output = args.outputs / modality / f"{case['id']}_redacted.{modality}"
            if case["expected_behavior"] == "BLOCK_OR_LOCAL_OCR" and not normalize(extract(input_path)):
                results.append({"id": case["id"], "modality": modality, "status": "OCR_OR_BLOCK_REQUIRED"})
                continue
            if not output.exists():
                results.append({"id": case["id"], "modality": modality, "status": "MISSING_OUTPUT"})
                continue
            score = score_file(output, case["phi_values"], case["preserve_values"])
            score.update({"id": case["id"], "modality": modality, "status": "PASS" if not score["leaked_phi"] and not score["missing_clinical"] else "FAIL"})
            results.append(score)
    report = args.outputs / "benchmark_report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(results, indent=2), encoding="utf-8")
    scored = [r for r in results if "phi_recall" in r]
    if scored:
        print(f"Files scored: {len(scored)}")
        print(f"Mean PHI recall: {sum(r['phi_recall'] for r in scored)/len(scored):.2%}")
        print(f"Mean preservation: {sum(r['preservation'] for r in scored)/len(scored):.2%}")
        print(f"Zero-leak pass rate: {sum(not r['leaked_phi'] for r in scored)/len(scored):.2%}")
    print(f"Report: {report}")


if __name__ == "__main__":
    main()
