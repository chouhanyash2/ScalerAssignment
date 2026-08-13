"""
config.py
=========
Central configuration: entity list, deny-lists, per-entity thresholds,
and the non-PII preservation rules.

To add a new entity type:
  1. Add its name to ENTITIES_TO_DETECT.
  2. Add a per-entity threshold in ENTITY_THRESHOLDS (optional).
  3. If it needs a deny-list, add it to ENTITY_DENY_LISTS.

v2 CHANGES (precision + recall fixes):
  - Massively expanded ORG deny-list (financial terms, roles, regulatory bodies)
  - Added PERSON deny-list (location patterns, abbreviations)
  - Added DATE deny-list (standalone years, time expressions, Act references)
  - Lowered PERSON threshold (0.40) — compensated by deny-list guard
  - Added PROSPECTUS_BUSINESS_TERMS for non-PII section headings
"""

from __future__ import annotations

# ─── Entities Presidio should detect ─────────────────────────────────────────
ENTITIES_TO_DETECT: list[str] = [
    # Core assignment requirements
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "ORGANIZATION",
    "LOCATION",
    "US_SSN",
    "CREDIT_CARD",
    "DATE_TIME",
    "IP_ADDRESS",
    "URL",
    # India-specific (custom recognizers in recognizers.py)
    "IN_PAN",
    "IN_AADHAAR",
    "IN_CIN",
    "IN_GSTIN",
    "IN_IFSC",
    "IN_VOTER_ID",
    "IN_PASSPORT",
    "IN_DRIVING_LICENSE",
    # Financial / generic extras
    "IBAN_CODE",
    "MEDICAL_LICENSE",
    "NRP",
]

# ─── Per-entity confidence thresholds ────────────────────────────────────────
ENTITY_THRESHOLDS: dict[str, float] = {
    "PERSON":             0.40,   # Lowered for recall; deny-list guards precision
    "EMAIL_ADDRESS":      0.80,
    "PHONE_NUMBER":       0.55,   # Slightly lowered for Indian formats
    "ORGANIZATION":       0.50,   # Raised from 0.45 — deny-list handles recall
    "LOCATION":           0.50,
    "US_SSN":             0.85,
    "CREDIT_CARD":        0.85,
    "DATE_TIME":          0.60,   # Raised — deny-list catches non-PII dates
    "IP_ADDRESS":         0.85,
    "URL":                0.85,   # Raised — was catching domain fragments
    "IN_PAN":             0.85,
    "IN_AADHAAR":         0.70,
    "IN_CIN":             0.90,
    "IN_GSTIN":           0.90,
    "IN_IFSC":            0.80,
    "IN_VOTER_ID":        0.85,
    "IN_PASSPORT":        0.85,
    "IN_DRIVING_LICENSE":  0.80,
    "IBAN_CODE":          0.85,
    "MEDICAL_LICENSE":    0.70,
    "NRP":                0.65,
}

DEFAULT_THRESHOLD: float = 0.40

# ═══════════════════════════════════════════════════════════════════════════════
# DENY-LISTS: spans that must NEVER be redacted
# These are the #1 precision fix. Each category was identified by running
# diagnostics on the actual document.
# ═══════════════════════════════════════════════════════════════════════════════

# ─── ORGANIZATION deny-list ───────────────────────────────────────────────────
# Split into categories for maintainability.

_REGULATORS: set[str] = {
    "sebi", "rbi", "irdai", "pfrda", "irda", "nabard", "sidbi",
    "nsdl", "cdsl", "csdl", "nseindia", "amfi", "epfo",
    "securities and exchange board of india",
    "reserve bank of india",
    "insurance regulatory and development authority",
    "pension fund regulatory and development authority",
    "the reserve bank", "the sebi",
    "sebi icdr", "sebi icdr regulations", "the sebi icdr regulations",
    "sebi lodr", "sebi lodr regulations",
    "sebi regulations", "the sebi regulations",
}

_EXCHANGES_AND_DEPOSITORIES: set[str] = {
    "nse", "bse", "mse", "mcx", "ncdex", "iccl", "nsccl",
    "national stock exchange", "bombay stock exchange",
    "metropolitan stock exchange",
    "national stock exchange of india",
    "national stock exchange of india limited",
    "bombay stock exchange limited",
    "nse limited", "bse limited",
}

_FINANCIAL_ROLE_TERMS: set[str] = {
    # These are financial categories/roles, not company names
    "anchor investors", "anchor investor",
    "book running lead managers", "book running lead manager",
    "the book running lead managers", "the book running lead manager",
    "brlm", "brlms",
    "lead managers", "lead manager", "the lead managers",
    "qualified institutional buyers", "qualified institutional buyer",
    "qib", "qibs",
    "non-institutional investors", "non-institutional investor",
    "nii", "niis",
    "retail individual investors", "retail individual investor",
    "rii", "riis",
    "selling shareholders", "selling shareholder",
    "the selling shareholders",
    "promoter group", "the promoter group", "promoter",
    "promoters", "the promoters",
    "registrar to the offer", "registrar",
    "sponsor bank", "sponsor banks",
    "underwriters", "underwriter",
    "syndicate members", "syndicate member",
    "designated intermediaries", "designated intermediary",
    "monitoring agency",
}

_DOCUMENT_AND_LEGAL_TERMS: set[str] = {
    # Document type names — NOT company names
    "red herring", "red herring prospectus",
    "draft red herring prospectus", "drhp",
    "the prospectus", "prospectus",
    "offer document", "the offer document",
    "the companies act", "companies act",
    "the depositories act", "depositories act",
    "the indian stamp act", "indian stamp act",
    "income tax act", "the income tax act",
    "foreign exchange management act", "fema",
    "the banking regulation act", "banking regulation act",
    "the negotiable instruments act",
    "the securities contracts",
    "securities contracts regulation rules", "scrr",
    "the competition act", "competition act",
    "prevention of money laundering act", "pmla",
    "the contract act", "contract act",
    "the arbitration act", "arbitration act",
    "the consumer protection act",
    "the insolvency and bankruptcy code", "ibc",
    "general information document",
}

_AUDIT_RATING_LEGAL_FIRMS: set[str] = {
    "deloitte", "kpmg", "pwc", "ernst & young", "ey",
    "price waterhouse", "grant thornton",
    "crisil", "icra", "care ratings", "fitch", "moody's", "s&p",
    "brickwork ratings", "acuite ratings",
}

_GOVERNMENT: set[str] = {
    "government of india", "central government", "state government",
    "ministry of finance", "ministry of corporate affairs",
    "ministry of commerce",
    "supreme court", "high court", "the supreme court",
    "income tax department",
    "central board of direct taxes", "cbdt",
    "registrar of companies", "roc",
    "reserve bank",
}

ORGANIZATION_DENY_LIST: frozenset[str] = frozenset(
    _REGULATORS | _EXCHANGES_AND_DEPOSITORIES | _FINANCIAL_ROLE_TERMS
    | _DOCUMENT_AND_LEGAL_TERMS | _AUDIT_RATING_LEGAL_FIRMS | _GOVERNMENT
)


# ─── PERSON deny-list ────────────────────────────────────────────────────────
# Spans detected as PERSON that are clearly NOT personal names.
PERSON_DENY_LIST: frozenset[str] = frozenset({
    # Abbreviations mistaken for names
    "scrr", "drhp", "nsdl", "cdsl", "sebi", "bse", "nse",
    "brlm", "brlms", "qib", "qibs", "nii", "rii",
    "fema", "pmla", "ibc", "ipo", "sme",
    # Role titles (not names)
    "managing director", "chief executive officer",
    "chief financial officer", "company secretary",
    "whole time director", "independent director",
    "non-executive director", "executive director",
    "chairman", "chairperson", "vice chairman",
    "compliance officer", "contact person",
    "authorized signatory", "authorized representative",
    # Document/section labels
    "red herring", "red herring prospectus",
    "draft red herring prospectus",
})

# Words that, when they appear in a PERSON span, indicate it's NOT a person.
# Used as substring checks.
PERSON_DENY_SUBSTRINGS: frozenset[str] = frozenset({
    "taluka", "district", "village", "ward", "block",
    "tehsil", "mandal", "panchayat", "municipality",
    "regulation", "regulations", "act", "section",
    "clause", "chapter", "schedule",
    "limited", "private", "pvt", "ltd", "llp",
    "inc", "corp", "corporation", "company",
    "director", "directors", "facility", "fiscal", "fiscals",
    "management", "promoter", "shareholder", "shareholders",
})


# ─── DATE_TIME deny-list ─────────────────────────────────────────────────────
# Financial year dates, standalone years, time expressions, Act year refs.
DATE_DENY_LIST: frozenset[str] = frozenset({
    # Financial year dates
    "march 31", "31 march", "31st march",
    "april 1", "1 april", "1st april",
    "march 2024", "march 2023", "march 2022", "march 2021", "march 2020",
    "march 2025", "march 2026",
    "fy 2024", "fy 2023", "fy2024", "fy2023",
    "fy 2025", "fy 2022", "fy2025", "fy2022",
    "financial year", "fiscal year",
    # Time expressions (never PII)
    "a.m.", "p.m.",
})

# Standalone years that are Act references, not DOBs.
DATE_DENY_STANDALONE_YEARS: frozenset[str] = frozenset({
    "2013", "2008", "1999", "1992", "1956", "1961", "1969",
    "1872", "1882", "1930", "1934", "1947", "1949", "1950",
    "1996", "2002", "2003", "2005", "2006", "2010", "2011",
    "2012", "2014", "2015", "2016", "2017", "2018", "2019",
})


# ─── Non-PII regex patterns ─────────────────────────────────────────────────
NON_PII_REGEX_PATTERNS: list[str] = [
    # SEBI registration numbers
    r"\bIN[A-Z]\d{6}[A-Z0-9]{0,4}\b",
    # ISIN codes
    r"\bINE[A-Z0-9]{9}\b",
    # RBI reference numbers
    r"\bRBI[/\-]\w+\b",
]


# ─── Faker locale ─────────────────────────────────────────────────────────────
FAKER_LOCALE: str = "en_IN"
FAKER_SEED: int = 42
