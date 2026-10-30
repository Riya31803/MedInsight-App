"""Shared, fully local PHI detector used by the PDF and DOCX redactors."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from presidio_analyzer import AnalyzerEngine


@dataclass(frozen=True)
class Finding:
    start: int
    end: int
    entity_type: str
    score: float = 1.0


# Add project-specific medications and clinical terms here. Entries are compared
# case-insensitively. They are never removed solely because an NLP model calls
# them a PERSON, LOCATION, ORGANIZATION, or DATE_TIME.
CLINICAL_ALLOW_LIST = {
    "aspirin",
    "atorvastatin",
    "insulin glargine",
    "lisinopril",
    "metformin",
    "st. john's wort",
}

DOSING_PHRASES = {
    "daily",
    "nightly",
    "morning",
    "evening",
    "once daily",
    "twice daily",
    "three times daily",
    "four times daily",
    "every morning",
    "every evening",
    "every night",
    "as needed",
}

MONTH = (
    r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?"
)

GENERAL_PATTERNS = {
    "US_SSN": re.compile(r"(?<!\d)\d{3}[- ]\d{2}[- ]\d{4}(?!\d)"),
    "PHONE_NUMBER": re.compile(
        r"(?<!\w)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)"
        r"\d{3}[-.\s]?\d{4}(?:\s*(?:x|ext\.?|extension)\s*\d{1,6})?(?!\w)",
        re.IGNORECASE,
    ),
    "EMAIL_ADDRESS": re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    ),
    "IP_ADDRESS": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "URL": re.compile(r"\b(?:https?://|www\.)[^\s<>]+", re.IGNORECASE),
    "DATE_TIME": re.compile(
        rf"\b(?:"
        rf"\d{{1,2}}[/-]\d{{1,2}}[/-](?:\d{{2}}|\d{{4}})"
        rf"|(?:{MONTH})\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}"
        rf"|\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{MONTH})\s+\d{{4}}"
        rf"|\d{{4}}-\d{{2}}-\d{{2}}"
        rf")\b",
        re.IGNORECASE,
    ),
    "STREET_ADDRESS": re.compile(
        r"\b\d{1,6}\s+[A-Za-z0-9.'-]+(?:\s+[A-Za-z0-9.'-]+){0,6}\s+"
        r"(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|"
        r"Court|Ct|Way|Place|Pl|Parkway|Pkwy|Highway|Hwy)\.?\b",
        re.IGNORECASE,
    ),
    "ADDRESS_UNIT": re.compile(
        r"\b(?:Apt\.?|Apartment|Unit|Suite|Ste\.?|Floor|Fl\.?)\s*#?\s*[A-Za-z0-9-]+\b",
        re.IGNORECASE,
    ),
    "ZIP_CODE": re.compile(r"(?<!\d)\d{5}(?:-\d{4})?(?!\d)"),
    "AGE_OVER_89": re.compile(
        r"\b(?:age(?:d)?\s*[:=-]?\s*|)(?:9[0-9]|1[01][0-9]|120)\s*(?:years?\s*old|y/?o)\b",
        re.IGNORECASE,
    ),
    "FACILITY": re.compile(
        r"\b(?:[A-Z][\w'&.-]+(?:\s+|$)){1,6}"
        r"(?:Medical\s+Center|Health\s+Center|Hospital|Clinic|Pharmacy|"
        r"Nursing\s+Home|Rehabilitation\s+Center|Laboratory|Lab)\b"
    ),
    # Common standalone identifier formats seen in the benchmark.
    "PATIENT_ID": re.compile(r"\bPT-[A-Z0-9-]{4,}\b", re.IGNORECASE),
    "POLICY_NUMBER": re.compile(r"\bPOL-[A-Z0-9-]{4,}\b", re.IGNORECASE),
    "MRN": re.compile(r"\bMRN[-\s]?[A-Z0-9-]{4,}\b", re.IGNORECASE),
    "RX_NUMBER": re.compile(r"\bRX[-\s]?[A-Z0-9-]{4,}\b", re.IGNORECASE),
    "ACCOUNT_NUMBER": re.compile(r"\bAC[-\s]?[A-Z0-9-]{4,}\b", re.IGNORECASE),
    "MEMBER_ID": re.compile(r"\b(?:BCBS|MEMBER|INS)[-]?[A-Z0-9-]{4,}\b", re.IGNORECASE),
}


# Group 1 must contain only the PHI value; the label remains in the document.
FIELD_PATTERNS = {
    "PERSON": re.compile(
        r"\b(?:patient(?:\s+name)?|name|spouse|wife|husband|partner|mother|"
        r"father|daughter|son|emergency\s+contact|physician|doctor|provider|"
        r"prescriber)\s*(?:name)?\s*[:=-]\s*"
        r"([A-Z][A-Za-z'.-]+(?:\s+[A-Z][A-Za-z'.-]+){0,3})",
        re.IGNORECASE,
    ),
    "DATE_TIME": re.compile(
        r"\b(?:DOB|date\s+of\s+birth|birth\s+date|admission\s+date|"
        r"discharge\s+date|service\s+date)\s*[:=-]\s*([^\n\r|;]+)",
        re.IGNORECASE,
    ),
    "STREET_ADDRESS": re.compile(
        r"\b(?:address|street\s+address)\s*[:=-]\s*([^\n\r|;]+)",
        re.IGNORECASE,
    ),
    "LOCATION": re.compile(
        r"\b(?:city|state|county|country)\s*[:=-]\s*([^\n\r|;]+)",
        re.IGNORECASE,
    ),
    "MRN": re.compile(
        r"\b(?:MRN|medical\s+record(?:\s+(?:number|no\.?))?|medical\s+record\s*#)"
        r"\s*[:#=-]?\s*([A-Z0-9-]{4,})",
        re.IGNORECASE,
    ),
    "PATIENT_ID": re.compile(
        r"\b(?:patient|chart)\s*(?:ID|number|no\.?|#)\s*[:#=-]?\s*([A-Z0-9-]{3,})",
        re.IGNORECASE,
    ),
    "RX_NUMBER": re.compile(
        r"\b(?:Rx|prescription)\s*(?:ID|number|no\.?|#)?\s*[:#=-]?\s*([A-Z0-9-]{3,})",
        re.IGNORECASE,
    ),
    "ACCOUNT_NUMBER": re.compile(
        r"\baccount\s*(?:ID|number|no\.?|#)?\s*[:#=-]?\s*([A-Z0-9-]{3,})",
        re.IGNORECASE,
    ),
    "MEMBER_ID": re.compile(
        r"\b(?:member|insurance|health\s+plan)\s*(?:ID|number|no\.?|#)"
        r"\s*[:#=-]?\s*([A-Z0-9-]{3,})",
        re.IGNORECASE,
    ),
    "POLICY_NUMBER": re.compile(
        r"\bpolicy\s*(?:ID|number|no\.?|#)?\s*[:#=-]?\s*([A-Z0-9-]{3,})",
        re.IGNORECASE,
    ),
    "LICENSE_NUMBER": re.compile(
        r"\b(?:driver'?s?\s+license|license)\s*(?:ID|number|no\.?|#)?"
        r"\s*[:#=-]?\s*([A-Z0-9-]{4,})",
        re.IGNORECASE,
    ),
    "US_PASSPORT": re.compile(
        r"\bpassport\s*(?:ID|number|no\.?|#)?\s*[:#=-]?\s*([A-Z0-9-]{5,})",
        re.IGNORECASE,
    ),
    "ROOM_NUMBER": re.compile(
        r"\b(?:room|bed)\s*(?:number|no\.?|#)?\s*[:#=-]?\s*([A-Z0-9-]{1,})",
        re.IGNORECASE,
    ),
    "AGE_OVER_89": re.compile(
        r"\bage\s*[:=-]\s*((?:9[0-9]|1[01][0-9]|120))\b",
        re.IGNORECASE,
    ),
}


PRESIDIO_ENTITIES = [
    "PERSON",
    "LOCATION",
    "DATE_TIME",
    "PHONE_NUMBER",
    "EMAIL_ADDRESS",
    "US_SSN",
    "US_DRIVER_LICENSE",
    "US_PASSPORT",
    "IP_ADDRESS",
    "URL",
]


def _trim_span(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and (text[end - 1].isspace() or text[end - 1] in ",.;:"):
        end -= 1
    return start, end


def _is_clinical_false_positive(value: str, entity_type: str) -> bool:
    normalized = re.sub(r"\s+", " ", value.strip()).casefold()
    if normalized in CLINICAL_ALLOW_LIST:
        return True
    if entity_type == "DATE_TIME":
        if normalized in DOSING_PHRASES:
            return True
        if re.fullmatch(
            r"(?:once|twice|three|four)\s+(?:a\s+)?(?:day|daily)|"
            r"every\s+\d+\s+hours?|\d+\s+times?\s+(?:a\s+)?day",
            normalized,
        ):
            return True
    return False


def _deduplicate(findings: Iterable[Finding]) -> list[Finding]:
    # Prefer field/regex findings (score 1) and longer spans. This prevents a
    # small NLP span from breaking a larger, more precise address or name.
    ordered = sorted(
        findings,
        key=lambda f: (-f.score, -(f.end - f.start), f.start),
    )
    accepted: list[Finding] = []
    for candidate in ordered:
        if any(candidate.start < old.end and candidate.end > old.start for old in accepted):
            continue
        accepted.append(candidate)
    return sorted(accepted, key=lambda f: f.start)


class LocalPHIDetector:
    def __init__(self, score_threshold: float = 0.60):
        self.analyzer = AnalyzerEngine()
        self.score_threshold = score_threshold

    def detect(self, text: str) -> list[Finding]:
        findings: list[Finding] = []

        for entity_type, pattern in FIELD_PATTERNS.items():
            for match in pattern.finditer(text):
                start, end = _trim_span(text, *match.span(1))
                value = text[start:end]
                if value and not _is_clinical_false_positive(value, entity_type):
                    findings.append(Finding(start, end, entity_type, 1.0))

        for entity_type, pattern in GENERAL_PATTERNS.items():
            for match in pattern.finditer(text):
                start, end = _trim_span(text, *match.span())
                value = text[start:end]
                if value and not _is_clinical_false_positive(value, entity_type):
                    findings.append(Finding(start, end, entity_type, 1.0))

        for result in self.analyzer.analyze(
            text=text,
            entities=PRESIDIO_ENTITIES,
            language="en",
            score_threshold=self.score_threshold,
        ):
            start, end = _trim_span(text, result.start, result.end)
            value = text[start:end]
            if value and not _is_clinical_false_positive(value, result.entity_type):
                findings.append(
                    Finding(start, end, result.entity_type, float(result.score))
                )

        return _deduplicate(findings)


def replace_findings(text: str, findings: Iterable[Finding]) -> tuple[str, list[Finding]]:
    findings = list(findings)
    output = text
    for finding in sorted(findings, key=lambda f: f.start, reverse=True):
        output = (
            output[: finding.start]
            + f"[{finding.entity_type}]"
            + output[finding.end :]
        )
    return output, findings
