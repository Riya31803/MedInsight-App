PDF REDACTION TEST - WINDOWS

Recommended Python:
- Python 3.11 or 3.12 (64-bit)

IMPORTANT:
- Do NOT copy the Mac venv folder to Windows.
- Create a new Windows virtual environment using setup_windows.bat.
- This prototype is designed for text-based PDFs.
- It is a redaction prototype, not a claim that the whole application is HIPAA compliant.

FILES
-----
redact_pdf.py
    Main local redaction script.

sample.pdf
    Synthetic test PDF.

requirements.txt
    Python package requirements.

setup_windows.bat
    Creates the venv and installs packages/models.

run_redaction.bat
    Runs the redaction script.

output\
    Redacted PDF is written here.

WINDOWS SETUP
-------------
1. Install Python 3.12 from python.org.
   During installation, select "Add Python to PATH".

2. Extract this ZIP.

3. Double-click:
      setup_windows.bat

   OR run in Command Prompt:
      setup_windows.bat

4. When setup finishes, double-click:
      run_redaction.bat

5. The result will be:
      output\redacted_all_phi_v2.pdf

TESTING YOUR OWN PDF
--------------------
Replace sample.pdf with another text-based PDF and keep the name:
    sample.pdf

Then run:
    run_redaction.bat

The current prototype detects/masks common text identifiers including:
- patient name in structured fields
- emergency contact name
- DOB / common dates
- MRN
- phone
- email
- street address
- SSN
- Rx number
- account number
- member/insurance ID patterns
- license-style IDs
- ZIP
- IP address
- URL

Clinical text such as medication names, doses, frequencies, symptoms, and labs should remain.

LIMITATION
----------
Scanned/image-only PDFs need an OCR-based workflow and are not the target of this first test.
