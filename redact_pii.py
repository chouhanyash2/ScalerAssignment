"""
redact_pii.py
=============
Entry point for the PII Redaction Tool.

Run:
    python redact_pii.py "Red Herring Prospectus.docx"
    python redact_pii.py "Red Herring Prospectus.docx" -o out.docx --verbose
    python redact_pii.py "Red Herring Prospectus.docx" --locale en_IN --seed 42

See `pii_redactor/` package for the full modular implementation.
"""

from pii_redactor.cli import run

if __name__ == "__main__":
    run()
