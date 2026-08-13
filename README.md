# PII Redaction Tool

A Python script that reads a Word (`.docx`) document, detects 21 different PII entity types using a mix of NER and regex, and replaces every detected span with a synthetic fake alternative. It preserves the original document formatting during the replacement process.

Note: The architecture borrows ideas from `pii-redaction-openmed` (deny-list filtering, modular redaction) and uses Microsoft Presidio and Faker under the hood.

---

## Repository Structure

```
redact_pii.py               <- Entry point
pii_redactor/
├── __init__.py
├── config.py               <- Entity list, deny-lists, thresholds
├── recognizers.py          <- Custom PatternRecognizers for Indian PII
├── operators.py            <- Faker configuration
├── consistency.py          <- Consistency mapper to keep fake names consistent
├── engine.py               <- Pipeline and filtering setup
├── document.py             <- docx read/write logic
├── evaluator.py            <- Metrics calculator
└── cli.py                  <- CLI parser
```

---

## Approach

### 1. Detection (Presidio)

We use a dual-layer approach for detection:
- **NER (spaCy en_core_web_lg)**: Used for free-form text like PERSON, ORGANIZATION, LOCATION, and DATE_TIME.
- **Regex (Presidio built-ins & Custom)**: Used for structured data like EMAIL_ADDRESS, PHONE_NUMBER, SSN, and India-specific IDs (PAN, Aadhaar, CIN, GSTIN, etc.).

To improve precision and avoid false positives:
- Added a deny-list for 40+ known public institutions (SEBI, RBI, NSE) so they aren't redacted as organizations.
- Added exclusions for financial dates like "FY2024" or "31 March 2024" since they are business metadata, not DOBs.
- Each entity has a custom confidence threshold (e.g. CREDIT_CARD at 0.85, ORGANIZATION at 0.45).

### 2. Replacement (Faker)

Each detected span is replaced using Faker with the `en_IN` locale to generate realistic Indian-format outputs for names, phone numbers, and addresses. US providers are used for SSNs and credit cards.

A consistency mapper ensures that every unique original string maps to the same synthetic replacement across the entire document. For example, if "Rohan Dey" is replaced by "Priya Sharma" on page 1, it will also be "Priya Sharma" on page 200.

### 3. Document I/O

The script uses `python-docx` to read all text-bearing elements (paragraphs, tables, headers, footers). Replacements happen at the "run" level, meaning text formatting like bold or italics is preserved.

---

## Installation

```bash
pip install presidio-analyzer presidio-anonymizer faker python-docx spacy
python -m spacy download en_core_web_lg
```

## Usage

```bash
# Basic run
python redact_pii.py "Red Herring Prospectus.docx" -o redacted_output.docx

# See all span replacements in terminal
python redact_pii.py "Red Herring Prospectus.docx" --verbose

# Run with evaluation against a ground-truth JSON
python redact_pii.py "Red Herring Prospectus.docx" \
    --export-predictions detected.json \
    --evaluate ground_truth.json
```

---

## Extending to a New PII Type

Adding a new type takes three steps:

**Step 1 — recognizers.py**
```python
def _voter_id_recognizer() -> PatternRecognizer:
    return PatternRecognizer(
        supported_entity="IN_VOTER_ID",
        patterns=[Pattern("voter_id", r"\b[A-Z]{3}[0-9]{7}\b", score=0.80)],
        context=["voter", "epic", "election"],
    )
# Add to get_all_custom_recognizers()
```

**Step 2 — config.py**
```python
ENTITIES_TO_DETECT.append("IN_VOTER_ID")
ENTITY_THRESHOLDS["IN_VOTER_ID"] = 0.80
```

**Step 3 — operators.py**
```python
def _voter_id(self, _: str) -> str:
    return "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=3)) + \
           "".join(random.choices("0123456789", k=7))

# Add to _build() dictionary:
"IN_VOTER_ID": self._op(self._voter_id),
```

---

## Tradeoffs and False Positives/Negatives

### Tradeoffs
- We went with Presidio over raw regex because regex can't reliably detect free-form names and addresses. Added custom patterns for Indian landlines (+91 xx xxxx xxxx) and split URL/email overlap handling to solve edge cases.
- Used `en_core_web_lg` instead of the smaller `sm` model because it had noticeably better recall on financial text, despite the larger file size.
- The consistency mapping requires caching in memory, which uses a bit more RAM but prevents the document from becoming confusing to read.

### False Positives
- Financial quarter references like "Q1 2024" might occasionally trigger the DATE_TIME recognizer if phrased strangely.
- Short locations like "Phoenix" can sometimes be confused for company names depending on the surrounding text.
- Standard 12-digit numbers without context words might not trigger the Aadhaar regex, since we set the threshold high to avoid catching random account numbers.

### False Negatives
- Names split across styled runs (e.g. if "John" is bold and "Doe" is italic) are seen as concatenated strings. Presidio usually handles this, but it can fail on edge cases.
- Non-standard phone formats like `9876-543-210` might be missed. We added custom patterns for the most common Indian formats to help with this.
- Issuer-masked values (like PAN printed as `XXXXX1234X`) are ignored by the tool since they are already obscured.
- *Note on ALL-CAPS:* NER models usually fail to detect ALL-CAPS names in table headers. We fixed this by adding a pre-processing step that normalizes ALL-CAPS text to Title Case before passing it to Presidio.
