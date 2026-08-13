"""
recognizers.py
==============
All custom PatternRecognizer definitions for India-specific PII types
plus any additional patterns not covered by Presidio's built-in recognizers.

Design principle: each recognizer has:
  - A tight regex (high specificity)
  - Context words that boost the confidence score
  - A baseline score calibrated to the entity's false-positive risk

Adding a new type:
  1. Write a function returning a PatternRecognizer.
  2. Add that function call to get_all_custom_recognizers().
"""

from __future__ import annotations

from presidio_analyzer import PatternRecognizer, Pattern


# ─── India-specific PII ───────────────────────────────────────────────────────

def _pan_recognizer() -> PatternRecognizer:
    """Indian PAN Card: AAAAA9999A (5 upper letters, 4 digits, 1 upper letter)."""
    return PatternRecognizer(
        supported_entity="IN_PAN",
        name="IndianPAN",
        patterns=[
            Pattern("pan_full", r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", score=0.85),
        ],
        context=["pan", "permanent", "account", "number", "income", "tax"],
        supported_language="en",
    )


def _aadhaar_recognizer() -> PatternRecognizer:
    """
    Indian Aadhaar: 12 digits, optionally grouped as XXXX XXXX XXXX.
    Uses strict context scoring so standalone 12-digit codes don't fire.
    """
    return PatternRecognizer(
        supported_entity="IN_AADHAAR",
        name="IndianAadhaar",
        patterns=[
            Pattern("aadhaar_spaced",   r"\b\d{4}[\s\-]\d{4}[\s\-]\d{4}\b", score=0.80),
            Pattern("aadhaar_compact",  r"\b\d{12}\b",                        score=0.50),
        ],
        context=["aadhaar", "aadhar", "uid", "unique", "identification", "uidai"],
        supported_language="en",
    )


def _cin_recognizer() -> PatternRecognizer:
    """
    Indian Company Identification Number (CIN).
    Format: [UL][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}
    Example: L21091MH2020PLC123456
    """
    return PatternRecognizer(
        supported_entity="IN_CIN",
        name="IndianCIN",
        patterns=[
            Pattern("cin_full", r"\b[UL][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}\b", score=0.92),
        ],
        context=["cin", "company", "identification", "registered", "registration"],
        supported_language="en",
    )


def _gstin_recognizer() -> PatternRecognizer:
    """
    Indian GSTIN: 2-digit state code + PAN-like 10 chars + 3 checksum chars.
    Example: 27AABCU9603R1ZX
    """
    return PatternRecognizer(
        supported_entity="IN_GSTIN",
        name="IndianGSTIN",
        patterns=[
            Pattern("gstin_full", r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]\b", score=0.92),
        ],
        context=["gstin", "gst", "goods", "services", "tax", "registration"],
        supported_language="en",
    )


def _ifsc_recognizer() -> PatternRecognizer:
    """
    Indian IFSC Code: 4 alpha (bank) + '0' + 6 alphanumeric (branch).
    Example: SBIN0001234
    """
    return PatternRecognizer(
        supported_entity="IN_IFSC",
        name="IndianIFSC",
        patterns=[
            Pattern("ifsc_full", r"\b[A-Z]{4}0[A-Z0-9]{6}\b", score=0.80),
        ],
        context=["ifsc", "bank", "branch", "rtgs", "neft", "imps", "swift"],
        supported_language="en",
    )


def _voter_id_recognizer() -> PatternRecognizer:
    """
    Indian Voter ID (EPIC): 3 letters + 7 digits.
    Example: ABC1234567
    """
    return PatternRecognizer(
        supported_entity="IN_VOTER_ID",
        name="IndianVoterID",
        patterns=[
            Pattern("voter_id", r"\b[A-Z]{3}[0-9]{7}\b", score=0.80),
        ],
        context=["voter", "epic", "election", "electoral", "commission"],
        supported_language="en",
    )


def _passport_recognizer() -> PatternRecognizer:
    """
    Indian Passport Number: 1 letter + 7 digits.
    Example: A1234567
    """
    return PatternRecognizer(
        supported_entity="IN_PASSPORT",
        name="IndianPassport",
        patterns=[
            Pattern("passport_full", r"\b[A-Z][0-9]{7}\b", score=0.80),
        ],
        context=["passport", "travel", "document", "visa", "foreign"],
        supported_language="en",
    )


def _driving_license_recognizer() -> PatternRecognizer:
    """
    Indian Driving License: state code (2 letters) + year (2-4 digits) + 7 digits.
    Example: MH0220120000001
    """
    return PatternRecognizer(
        supported_entity="IN_DRIVING_LICENSE",
        name="IndianDrivingLicense",
        patterns=[
            Pattern(
                "dl_full",
                r"\b[A-Z]{2}[0-9]{2}[0-9]{4}[0-9]{7}\b",
                score=0.80,
            ),
        ],
        context=["driving", "license", "licence", "dl", "vehicle"],
        supported_language="en",
    )


# ─── Generic extras not in Presidio by default ───────────────────────────────

def _indian_phone_recognizer() -> PatternRecognizer:
    """
    Supplement Presidio's phone recognizer for Indian formats specifically:
    +91 XXXXX XXXXX, 0XXXXXXXXXX, +91-XXXXX-XXXXX
    """
    return PatternRecognizer(
        supported_entity="PHONE_NUMBER",
        name="IndianPhone",
        patterns=[
            Pattern("in_mobile", r"\b(?:\+91[\s\-]?)?[6-9][0-9]{9}\b",     score=0.75),
            Pattern("in_std",    r"\b0[0-9]{2,4}[\s\-][0-9]{6,8}\b",        score=0.70),
            Pattern("in_intl",   r"\+91[\s\-][0-9]{5}[\s\-][0-9]{5}\b",     score=0.85),
            Pattern("in_landline_intl", r"\+91[\s\-][0-9]{2,4}[\s\-][0-9]{6,8}\b", score=0.85),
            Pattern("in_landline_intl_split", r"\+91[\s\-][0-9]{2,4}[\s\-][0-9]{3,4}[\s\-][0-9]{3,4}\b", score=0.85),
        ],
        context=["phone", "mobile", "contact", "tel", "telephone", "call", "whatsapp"],
        supported_language="en",
    )


def _pin_code_recognizer() -> PatternRecognizer:
    """
    Indian PIN / Postal Code: 6 digits, first digit 1-9.
    Example: 400001
    """
    return PatternRecognizer(
        supported_entity="LOCATION",
        name="IndianPinCode",
        patterns=[
            Pattern("pin_code", r"\b[1-9][0-9]{5}\b", score=0.55),
        ],
        context=["pin", "pincode", "pin code", "postal", "zip"],
        supported_language="en",
    )


# ─── RECALL BOOSTERS ─────────────────────────────────────────────────────────
# These recognizers catch names/entities that spaCy NER misses.

def _honorific_name_recognizer() -> PatternRecognizer:
    """
    Catch names preceded by Indian/formal honorifics that spaCy may miss.
    e.g., "Mr. Sarthak Malvadkar", "Shri Rajesh Hegde", "Dr. Pushpa Hegde"

    This is a KEY recall fix: the diagnostics showed names like
    "Sarthak Malvadkar" being missed when appearing after "Contact Person:".
    """
    return PatternRecognizer(
        supported_entity="PERSON",
        name="HonorificNameRecognizer",
        patterns=[
            # Mr./Mrs./Ms./Dr. + 1-3 capitalized words
            Pattern(
                "honorific_name",
                r"\b(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Shri\.?|Smt\.?|Capt\.?|Col\.?|Prof\.?)\s+"
                r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b",
                score=0.90,
            ),
        ],
        supported_language="en",
    )


def _contact_context_name_recognizer() -> PatternRecognizer:
    """
    Catch names that appear after role/contact context keywords.
    e.g., "Contact Person: Sarthak Malvadkar"
          "Compliance Officer: Rajesh Hegde"
    """
    return PatternRecognizer(
        supported_entity="PERSON",
        name="ContactContextNameRecognizer",
        patterns=[
            # 2-3 capitalized words (name pattern)
            Pattern(
                "capitalized_name_2",
                r"\b[A-Z][a-z]{1,15}\s+[A-Z][a-z]{1,15}\b",
                score=0.25,
            ),
            Pattern(
                "capitalized_name_3",
                r"\b[A-Z][a-z]{1,15}\s+[A-Z][a-z]{1,15}\s+[A-Z][a-z]{1,15}\b",
                score=0.30,
            ),
        ],
        context=[
            "contact", "person", "compliance", "officer", "director",
            "manager", "secretary", "promoter", "shareholder",
            "name", "nominee", "authorized", "signatory",
            "key managerial", "key management",
        ],
        supported_language="en",
    )


def _email_prefix_name_recognizer() -> PatternRecognizer:
    """
    Extract person names from email local-parts.
    e.g., "rashi.patil@gmail.com" → likely "Rashi Patil" appears nearby.

    Also catches names in patterns like "Name: xyz@email.com" where the
    name before the colon might not be detected by NER.
    """
    return PatternRecognizer(
        supported_entity="EMAIL_ADDRESS",
        name="EmailPrefixRecognizer",
        patterns=[
            Pattern(
                "email_dotted",
                r"\b[a-z]+\.[a-z]+@[a-z]+\.[a-z]{2,}\b",
                score=0.90,
            ),
        ],
        supported_language="en",
    )


# ─── Public API ───────────────────────────────────────────────────────────────

def get_all_custom_recognizers() -> list[PatternRecognizer]:
    """Return all custom recognizers to register with the AnalyzerEngine."""
    return [
        _pan_recognizer(),
        _aadhaar_recognizer(),
        _cin_recognizer(),
        _gstin_recognizer(),
        _ifsc_recognizer(),
        _voter_id_recognizer(),
        _passport_recognizer(),
        _driving_license_recognizer(),
        _indian_phone_recognizer(),
        _pin_code_recognizer(),
        # Recall boosters
        _honorific_name_recognizer(),
        _contact_context_name_recognizer(),
        _email_prefix_name_recognizer(),
    ]
