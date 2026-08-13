"""
engine.py
=========
Factory functions for building the Presidio AnalyzerEngine and AnonymizerEngine.

v2 CHANGES (precision + recall fixes):
  - ALL-CAPS text pre-processing: convert to Title Case before NER, map spans back
  - PERSON deny-list filtering (location words, abbreviations, role titles)
  - DATE standalone year filtering (Act references like "2013", "2008")
  - PERSON deny-substring filtering (Taluka, District, Limited, etc.)
  - URL / domain fragment filtering (email domain parts)
  - Improved overlap merging
"""

from __future__ import annotations

import logging
import re
import sys
from typing import List, Optional

from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

from pii_redactor.config import (
    ENTITIES_TO_DETECT,
    ENTITY_THRESHOLDS,
    DEFAULT_THRESHOLD,
    ORGANIZATION_DENY_LIST,
    PERSON_DENY_LIST,
    PERSON_DENY_SUBSTRINGS,
    DATE_DENY_LIST,
    DATE_DENY_STANDALONE_YEARS,
    NON_PII_REGEX_PATTERNS,
)
from pii_redactor.recognizers import get_all_custom_recognizers

logger = logging.getLogger(__name__)

_NON_PII_COMPILED = [re.compile(p) for p in NON_PII_REGEX_PATTERNS]
_PERSON_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "by",
    "for", "from", "in", "into", "is", "of", "on", "or", "that", "the",
    "these", "this", "those", "to", "under", "was", "were", "with",
    "accordance", "against", "code", "email", "fiscal", "fiscals", "jointly",
    "manner", "may", "not", "our", "pursuant", "scan", "timely", "view",
    "within",
}


# ═══════════════════════════════════════════════════════════════════════════════
# ALL-CAPS PRE-PROCESSING
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_for_ner(text: str) -> tuple[str, bool]:
    """
    If the text is predominantly ALL-CAPS, convert to Title Case for NER.
    Returns (normalized_text, was_normalized).

    spaCy's NER relies heavily on casing features. ALL-CAPS text removes
    this signal entirely, causing massive recall drops. By normalizing to
    Title Case, we restore the casing signal for NER.

    The detected spans are still at the correct offsets because we preserve
    the exact same character count (Title Case doesn't change string length
    for ASCII text — and Indian names are ASCII in this document).
    """
    if not text.strip():
        return text, False

    # Count uppercase vs total alpha chars
    alpha_chars = [c for c in text if c.isalpha()]
    if not alpha_chars:
        return text, False

    upper_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)

    # If > 70% uppercase, normalize
    if upper_ratio > 0.70:
        # Use title() for a simple, reliable normalization
        normalized = text.title()
        return normalized, True

    return text, False


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYZER ENGINE FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

def build_analyzer() -> AnalyzerEngine:
    """Build a Presidio AnalyzerEngine backed by the best available spaCy model."""
    import os
    env_model = os.environ.get("SPACY_MODEL")
    candidates = [env_model] if env_model else ["en_core_web_sm", "en_core_web_md", "en_core_web_lg", "en_core_web_trf"]
    candidates = [c for c in candidates if c]

    for model_name in candidates:
        try:
            configuration = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": model_name}],
            }
            provider = NlpEngineProvider(nlp_configuration=configuration)
            nlp_engine = provider.create_engine()
            logger.info("Loaded spaCy model: %s", model_name)
            break
        except Exception as exc:
            logger.debug("spaCy model '%s' unavailable: %s", model_name, exc)
    else:
        sys.exit(
            "No spaCy model found. Run:\n"
            "  python -m spacy download en_core_web_sm"
        )

    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])

    for recognizer in get_all_custom_recognizers():
        analyzer.registry.add_recognizer(recognizer)
        logger.debug("Registered recognizer: %s", recognizer.name)

    logger.info(
        "AnalyzerEngine ready with %d recognizers.",
        len(analyzer.registry.recognizers),
    )
    return analyzer


def build_anonymizer() -> AnonymizerEngine:
    return AnonymizerEngine()


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS WITH FULL FILTERING PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_text(
    analyzer: AnalyzerEngine,
    text: str,
    entities: Optional[List[str]] = None,
    language: str = "en",
) -> List[RecognizerResult]:
    """
    Run Presidio analysis with a 6-stage filtering pipeline:
      1. ALL-CAPS normalization (recall fix)
      2. Per-entity confidence thresholds (precision fix)
      3. ORGANIZATION deny-list filtering (precision fix)
      4. PERSON deny-list + substring filtering (precision fix)
      5. DATE standalone year + time filtering (precision fix)
      6. Non-PII regex pattern filtering (precision fix)
      7. Span overlap merging (dedup fix)
    """
    if entities is None:
        entities = ENTITIES_TO_DETECT

    # ── Stage 0: ALL-CAPS normalization for better NER recall ──────────────
    normalized_text, was_normalized = normalize_for_ner(text)
    analysis_text = normalized_text if was_normalized else text

    global_min = min(ENTITY_THRESHOLDS.values(), default=DEFAULT_THRESHOLD)

    raw_results: List[RecognizerResult] = analyzer.analyze(
        text=analysis_text,
        entities=entities,
        language=language,
        score_threshold=global_min,
    )

    # ── Stage 1: Per-entity thresholds ────────────────────────────────────
    filtered = _apply_per_entity_thresholds(raw_results)

    # ── Stage 2: ORGANIZATION deny-list ───────────────────────────────────
    filtered = _apply_org_deny_list(filtered, analysis_text)

    # ── Stage 3: PERSON deny-list + substring checks ─────────────────────
    filtered = _apply_person_deny_list(filtered, analysis_text)

    # ── Stage 4: DATE deny-list + standalone years ────────────────────────
    filtered = _apply_date_deny_list(filtered, analysis_text)

    # ── Stage 5: Non-PII regex patterns (ISIN, SEBI reg, etc.) ───────────
    filtered = _apply_non_pii_patterns(filtered, analysis_text)

    # ── Stage 6: URL domain fragment filtering ────────────────────────────
    filtered = _apply_url_filtering(filtered, analysis_text)

    # ── Stage 7: Overlap merging ──────────────────────────────────────────
    filtered = _merge_overlapping(filtered)

    return filtered


# ═══════════════════════════════════════════════════════════════════════════════
# INDIVIDUAL FILTER STAGES
# ═══════════════════════════════════════════════════════════════════════════════

def _apply_per_entity_thresholds(
    results: List[RecognizerResult],
) -> List[RecognizerResult]:
    kept = []
    for r in results:
        threshold = ENTITY_THRESHOLDS.get(r.entity_type, DEFAULT_THRESHOLD)
        if r.score >= threshold:
            kept.append(r)
    return kept


def _apply_org_deny_list(
    results: List[RecognizerResult],
    text: str,
) -> List[RecognizerResult]:
    kept = []
    for r in results:
        if r.entity_type == "ORGANIZATION":
            span = text[r.start: r.end].strip().lower()
            # Exact match
            if span in ORGANIZATION_DENY_LIST:
                logger.debug("Deny-list ORG drop: %r", span)
                continue
            # Also check if span starts with "the " and rest is in deny-list
            if span.startswith("the ") and span[4:] in ORGANIZATION_DENY_LIST:
                logger.debug("Deny-list ORG drop (the-prefix): %r", span)
                continue
        kept.append(r)
    return kept


def _apply_person_deny_list(
    results: List[RecognizerResult],
    text: str,
) -> List[RecognizerResult]:
    kept = []
    for r in results:
        if r.entity_type == "PERSON":
            span = text[r.start: r.end].strip()
            span_lower = span.lower()

            # Exact deny-list match
            if span_lower in PERSON_DENY_LIST:
                logger.debug("Deny-list PERSON drop: %r", span)
                continue

            # Substring checks (e.g., "Chakan Taluka - Khed" contains "taluka")
            if any(sub in span_lower for sub in PERSON_DENY_SUBSTRINGS):
                logger.debug("Deny-substring PERSON drop: %r", span)
                continue

            words = re.findall(r"[A-Za-z]+", span_lower)
            if any(word in _PERSON_STOPWORDS for word in words):
                logger.debug("Stopword PERSON drop: %r", span)
                continue

            # Single-word all-caps abbreviations (SCRR, DRHP, FEMA, etc.)
            if span.isupper() and len(span) <= 6 and " " not in span:
                logger.debug("Abbreviation PERSON drop: %r", span)
                continue

            # Very short single-word detections (≤2 chars) are usually noise
            if len(span) <= 2:
                logger.debug("Short PERSON drop: %r", span)
                continue

        kept.append(r)
    return kept


def _apply_date_deny_list(
    results: List[RecognizerResult],
    text: str,
) -> List[RecognizerResult]:
    kept = []
    for r in results:
        if r.entity_type == "DATE_TIME":
            span = text[r.start: r.end].strip()
            span_lower = span.lower()

            # Deny-list substring match
            if any(d in span_lower for d in DATE_DENY_LIST):
                logger.debug("Deny-list DATE drop: %r", span)
                continue

            # Standalone year (4 digits only) that matches an Act year
            if span.strip() in DATE_DENY_STANDALONE_YEARS:
                logger.debug("Standalone year DATE drop: %r", span)
                continue

            # Pure time expressions "5:00 p.m." — never PII
            if re.match(r'^\d{1,2}:\d{2}\s*(a\.?m\.?|p\.?m\.?)?$', span, re.IGNORECASE):
                logger.debug("Time expression DATE drop: %r", span)
                continue

            # Standalone short year (any 4-digit year without month context)
            if re.match(r'^\d{4}$', span.strip()):
                # Check surrounding text for "born", "birth", "dob" — if not present, skip
                context_start = max(0, r.start - 40)
                context = text[context_start: r.start].lower()
                if not any(w in context for w in ["born", "birth", "dob", "date of birth", "age"]):
                    logger.debug("Standalone year (no birth context) DATE drop: %r", span)
                    continue

        kept.append(r)
    return kept


def _apply_non_pii_patterns(
    results: List[RecognizerResult],
    text: str,
) -> List[RecognizerResult]:
    kept = []
    for r in results:
        span = text[r.start: r.end]
        if any(pat.fullmatch(span) for pat in _NON_PII_COMPILED):
            logger.debug("Non-PII pattern drop [%s]: %r", r.entity_type, span)
            continue
        kept.append(r)
    return kept


def _apply_url_filtering(
    results: List[RecognizerResult],
    text: str,
) -> List[RecognizerResult]:
    """
    Filter URL detections that are:
    1. Just a bare domain TLD (< 15 chars) that's likely a person name fragment
       e.g., 'anand.so', 'parag.pa', 'sachin.ga'
    2. Part of an already-detected EMAIL_ADDRESS span
    Also trims trailing punctuation (., ,) from URL spans so URLs like
    'www.nseindia.com,' are correctly captured.
    """
    email_spans = [(r.start, r.end) for r in results if r.entity_type == "EMAIL_ADDRESS"]

    kept = []
    for r in results:
        if r.entity_type == "URL":
            span = text[r.start: r.end].strip()

            # Strip trailing punctuation that the URL recognizer sometimes captures
            span_clean = span.rstrip(".,;:)>]'\"")
            if span_clean != span:
                logger.debug("URL trailing punct stripped: %r -> %r", span, span_clean)
                # Adjust the end offset to exclude trailing punct
                trailing = len(span) - len(span_clean)
                r = RecognizerResult(
                    entity_type=r.entity_type,
                    start=r.start,
                    end=r.end - trailing,
                    score=r.score,
                )
                span = span_clean

            drop_url = False

            # Skip bare TLD-like fragments (< 15 chars, no protocol, no path)
            if (
                len(span) < 15
                and not span.startswith("http")
                and not span.startswith("www.")
                and "/" not in span
                and "@" not in span
            ):
                logger.debug("URL domain fragment drop: %r", span)
                continue

            # Skip URLs that overlap with email spans
            for es, ee in email_spans:
                if r.start >= es and r.end <= ee:
                    logger.debug("URL inside EMAIL drop: %r", span)
                    drop_url = True
                    break

            if drop_url:
                continue

        kept.append(r)
    return kept


def _merge_overlapping(
    results: List[RecognizerResult],
) -> List[RecognizerResult]:
    """When two spans overlap, keep the higher-scoring / longer one."""
    if not results:
        return results

    sorted_res = sorted(results, key=lambda r: (r.start, -r.score))
    merged: List[RecognizerResult] = []
    current = sorted_res[0]

    for nxt in sorted_res[1:]:
        if nxt.start < current.end:
            # Overlap — keep higher score, or longer on tie
            if nxt.score > current.score or (
                nxt.score == current.score
                and (nxt.end - nxt.start) > (current.end - current.start)
            ):
                current = nxt
        else:
            merged.append(current)
            current = nxt

    merged.append(current)
    return merged
