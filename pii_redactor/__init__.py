"""
pii_redactor/
├── __init__.py
├── config.py          — entity registry, deny-lists, thresholds
├── recognizers.py     — all custom PatternRecognizers (India PII + extras)
├── operators.py       — Faker-backed OperatorConfig for every entity type
├── consistency.py     — ConsistencyMapper (same span → same fake, every time)
├── engine.py          — AnalyzerEngine + AnonymizerEngine factory
├── document.py        — python-docx read/write with format preservation
├── evaluator.py       — span-level Precision / Recall / F1 calculator
└── cli.py             — argparse CLI entry point

Entry point:  redact_pii.py  (thin wrapper around cli.py)
"""
