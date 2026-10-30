# Synthetic PHI Redaction Benchmark

This benchmark contains 18 synthetic cases in both PDF and DOCX format. No real patient information is included.

## Coverage

- Standard labelled patient fields
- Free-form spouse and caregiver information
- Hyphenated, apostrophe, suffix, nickname, and initial-based names
- Several date formats
- MRNs, prescription, account, member, policy, passport, and license identifiers
- Phone, email, URL, and IP address values
- Physician, facility, room, and caregiver identifiers
- Multiline addresses
- PHI inside tables, headers, and footers
- Repeated identifiers
- Age over 89
- Medication and diagnosis false-positive traps
- Ambiguous names and locations
- Long unstructured narrative
- Dense mixed-PHI stress case
- Image-only PDF and DOCX requiring local OCR or explicit blocking

This suite is representative, not exhaustive. Add cases based on errors observed in your real document formats.

## Recommended test workflow

1. Batch-process every file under `inputs/pdf` and `inputs/docx`.
2. Name outputs `<case_id>_redacted.pdf` and `<case_id>_redacted.docx`.
3. Put them under `redacted_outputs/pdf` and `redacted_outputs/docx`.
4. Run:

```powershell
python evaluate_benchmark.py --benchmark . --outputs .\redacted_outputs
```

The evaluator creates `redacted_outputs/benchmark_report.json`.

## Metrics

- `phi_recall`: fraction of known PHI values absent from the sanitized output.
- `preservation`: fraction of required medication and clinical values retained.
- `zero-leak pass rate`: fraction of documents with no known PHI remaining.

Do not rely on mean recall alone. A document with one leaked identifier should fail even when the overall percentage is high.

## Scan safety requirement

`case_18_scanned_image` intentionally contains no extractable text. A safe pipeline must either process it with fully local OCR before redaction or block it. Producing an apparently successful output without OCR is a failure.
