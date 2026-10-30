from pathlib import Path
from collections import Counter
import re

from docx import Document
from presidio_analyzer import AnalyzerEngine


print("DOCX redaction script started")

BASE_DIR = Path(__file__).resolve().parent
INPUT_DOCX = BASE_DIR / "sample.docx"
OUTPUT_DOCX = BASE_DIR / "output" / "redacted_all_phi.docx"

OUTPUT_DOCX.parent.mkdir(parents=True, exist_ok=True)

if not INPUT_DOCX.exists():
    raise FileNotFoundError(
        f"Could not find {INPUT_DOCX}. "
        "Put your Word document in this folder and name it sample.docx."
    )


# ------------------------------------------------------
# SETTINGS
# ------------------------------------------------------

# Add medication names or medical terms that must be preserved.
ALLOW_LIST = {
    "metformin",
    "lisinopril",
    "atorvastatin",
    "aspirin",
}

PRESIDIO_ENTITIES = [
    "PERSON",
    "LOCATION",
    "PHONE_NUMBER",
    "EMAIL_ADDRESS",
    "DATE_TIME",
    "US_SSN",
    "US_DRIVER_LICENSE",
    "US_PASSPORT",
    "IP_ADDRESS",
    "URL",
]


# ------------------------------------------------------
# DIRECT REGEX PATTERNS
# ------------------------------------------------------

PATTERNS = {
    "SSN": re.compile(
        r"\b\d{3}-\d{2}-\d{4}\b"
    ),

    "PHONE": re.compile(
        r"\b(?:\+?1[-.\s]?)?"
        r"(?:\(?\d{3}\)?[-.\s]?)"
        r"\d{3}[-.\s]?\d{4}\b"
    ),

    "EMAIL": re.compile(
        r"\b[A-Za-z0-9._%+-]+@"
        r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    ),

    "DATE": re.compile(
        r"\b(?:"
        r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
        r"|"
        r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|"
        r"Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
        r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
        r"Nov(?:ember)?|Dec(?:ember)?)"
        r"\s+\d{1,2},?\s+\d{4}"
        r")\b",
        re.IGNORECASE,
    ),

    "MRN": re.compile(
        r"\bMRN[-\s]?[A-Za-z0-9]{4,}\b",
        re.IGNORECASE,
    ),

    "RX_NUMBER": re.compile(
        r"\bRX[-\s]?[A-Za-z0-9]{4,}\b",
        re.IGNORECASE,
    ),

    "ACCOUNT_NUMBER": re.compile(
        r"\bAC\d{4,}\b",
        re.IGNORECASE,
    ),

    "MEMBER_ID": re.compile(
        r"\b(?:BCBS|MEMBER|INS)[-]?[A-Za-z0-9]{4,}\b",
        re.IGNORECASE,
    ),

    "LICENSE_NUMBER": re.compile(
        r"\b[A-Z]{2}\d{5,10}\b"
    ),

    "STREET_ADDRESS": re.compile(
        r"\b\d{1,6}\s+"
        r"[A-Za-z0-9.'\- ]+\s+"
        r"(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|"
        r"Lane|Ln|Boulevard|Blvd|Court|Ct|Way|Place|Pl)"
        r"\b",
        re.IGNORECASE,
    ),

    "ZIP_CODE": re.compile(
        r"\b\d{5}(?:-\d{4})?\b"
    ),

    "IP_ADDRESS": re.compile(
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
    ),

    "URL": re.compile(
        r"\b(?:https?://|www\.)\S+\b",
        re.IGNORECASE,
    ),
}


# ------------------------------------------------------
# FIELD-BASED PATTERNS
# Only captured values are replaced, not field labels.
# ------------------------------------------------------

FIELD_PATTERNS = {
    "PATIENT_NAME": re.compile(
        r"(?:Patient\s+Name|Name)\s*:\s*"
        r"([A-Z][A-Za-z'.-]+"
        r"(?:\s+[A-Z][A-Za-z'.-]+){1,3})",
        re.IGNORECASE,
    ),

    "DOB": re.compile(
        r"(?:DOB|Date\s+of\s+Birth|Birth\s+Date)"
        r"\s*:\s*([^\n]+)",
        re.IGNORECASE,
    ),

    "MRN_FIELD": re.compile(
        r"(?:MRN|Medical\s+Record(?:\s+Number)?|"
        r"Medical\s+Record\s+#)"
        r"\s*:\s*([A-Za-z0-9-]+)",
        re.IGNORECASE,
    ),

    "ADDRESS_FIELD": re.compile(
        r"(?:Address)\s*:\s*([^\n]+)",
        re.IGNORECASE,
    ),

    "RX_FIELD": re.compile(
        r"(?:Rx|Prescription)"
        r"\s*(?:Number|No\.?|#)?"
        r"\s*:\s*([A-Za-z0-9-]+)",
        re.IGNORECASE,
    ),

    "ACCOUNT_FIELD": re.compile(
        r"(?:Account)"
        r"\s*(?:Number|No\.?|#)?"
        r"\s*:\s*([A-Za-z0-9-]+)",
        re.IGNORECASE,
    ),

    "MEMBER_FIELD": re.compile(
        r"(?:Member|Insurance|Health\s+Plan)"
        r"\s*(?:ID|Number|No\.?|#)"
        r"\s*:\s*([A-Za-z0-9-]+)",
        re.IGNORECASE,
    ),

    "EMERGENCY_CONTACT": re.compile(
        r"(?:Emergency\s+Contact)\s*:\s*"
        r"([A-Z][A-Za-z'.-]+"
        r"(?:\s+[A-Z][A-Za-z'.-]+){1,3})",
        re.IGNORECASE,
    ),

    "LICENSE_FIELD": re.compile(
        r"(?:License\s+(?:Number|No\.?|#))"
        r"\s*:\s*([A-Za-z0-9-]+)",
        re.IGNORECASE,
    ),

    "ADMISSION_DATE": re.compile(
        r"(?:Admission\s+Date)\s*:\s*([^\n]+)",
        re.IGNORECASE,
    ),

    "DISCHARGE_DATE": re.compile(
        r"(?:Discharge\s+Date)\s*:\s*([^\n]+)",
        re.IGNORECASE,
    ),
}


# ------------------------------------------------------
# DETECTION AND REPLACEMENT
# ------------------------------------------------------

analyzer = AnalyzerEngine()
stats = Counter()


def add_finding(findings, start, end, entity_type, text):
    """Add one detected text span if it is valid."""

    if start >= end:
        return

    value = text[start:end].strip()

    if not value:
        return

    if value.casefold() in ALLOW_LIST:
        return

    findings.append(
        {
            "start": start,
            "end": end,
            "entity_type": entity_type,
        }
    )


def remove_overlapping_findings(findings):
    """Keep one redaction when multiple detectors find the same text."""

    ordered = sorted(
        findings,
        key=lambda item: (
            item["start"],
            -(item["end"] - item["start"]),
        ),
    )

    cleaned = []

    for finding in ordered:
        overlaps = False

        for existing in cleaned:
            if (
                finding["start"] < existing["end"]
                and finding["end"] > existing["start"]
            ):
                overlaps = True
                break

        if not overlaps:
            cleaned.append(finding)

    return cleaned


def redact_text(text):
    """Detect and replace identifying information in text."""

    if not text.strip():
        return text

    findings = []

    # 1. Field-based information
    for entity_type, pattern in FIELD_PATTERNS.items():
        for match in pattern.finditer(text):
            start, end = match.span(1)

            add_finding(
                findings,
                start,
                end,
                entity_type,
                text,
            )

    # 2. General regex values
    for entity_type, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            start, end = match.span()

            add_finding(
                findings,
                start,
                end,
                entity_type,
                text,
            )

    # 3. Presidio backup
    results = analyzer.analyze(
        text=text,
        entities=PRESIDIO_ENTITIES,
        language="en",
        score_threshold=0.55,
    )

    for result in results:
        add_finding(
            findings,
            result.start,
            result.end,
            result.entity_type,
            text,
        )

    findings = remove_overlapping_findings(findings)

    # Replace from the end so earlier indexes remain correct.
    output = text

    for finding in sorted(
        findings,
        key=lambda item: item["start"],
        reverse=True,
    ):
        entity_type = finding["entity_type"]

        output = (
            output[:finding["start"]]
            + f"[{entity_type}]"
            + output[finding["end"]:]
        )

        stats[entity_type] += 1

    return output


# ------------------------------------------------------
# DOCX CONTENT PROCESSING
# ------------------------------------------------------

def process_paragraph(paragraph):
    original_text = paragraph.text
    sanitized_text = redact_text(original_text)

    if sanitized_text != original_text:
        # This may simplify formatting across multiple Word runs.
        paragraph.text = sanitized_text


def process_table(table):
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                process_paragraph(paragraph)

            for nested_table in cell.tables:
                process_table(nested_table)


document = Document(INPUT_DOCX)

# Normal paragraphs
for paragraph in document.paragraphs:
    process_paragraph(paragraph)

# Tables
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


# ------------------------------------------------------
# REMOVE DOCUMENT METADATA
# ------------------------------------------------------

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


# ------------------------------------------------------
# SAVE
# ------------------------------------------------------

document.save(OUTPUT_DOCX)

print("\n================================")
print("FINISHED")
print("================================")

print("\nRedaction summary:")

if stats:
    for entity, count in sorted(stats.items()):
        print(f"{entity}: {count}")
else:
    print("No identifying information detected.")

print(f"\nOutput DOCX:\n{OUTPUT_DOCX}")