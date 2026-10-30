# Updated local PDF and DOCX de-identification

## 1. Install (Windows PowerShell)

```powershell
python -m pip install -r requirements.txt
python -m spacy download en_core_web_lg
```

If `en_core_web_lg` is too large for the test computer, try
`en_core_web_sm`, although person/location recall may be lower.

## 2. Run the PDF redactor

1. Put the input file beside the scripts and name it `sample.pdf`.
2. Run:

```powershell
python redact_pdf.py
```

The result is written to `output/redacted_all_phi.pdf`.

## 3. Run the DOCX redactor

1. Put the input file beside the scripts and name it `sample.docx`.
2. Run:

```powershell
python redact_docx.py
```

The result is written to `output/redacted_all_phi.docx`.

## Important limits

- PDF processing requires selectable text. A scanned/image-only PDF needs a
  local OCR stage before this script.
- `python-docx` does not reliably expose text inside every Word shape/text box,
  comment, tracked change, embedded object, or image. Those must be separately
  removed or processed before a HIPAA release workflow.
- No de-identification detector should be assumed HIPAA-safe based only on this
  synthetic benchmark. Test against representative, locally held documents and
  require human review until the measured leak rate is acceptable.
- Expand `CLINICAL_ALLOW_LIST` in `phi_detector.py` with medication and clinical
  terms present in your dataset to reduce false positives.
