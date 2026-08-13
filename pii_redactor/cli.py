"""
cli.py
======
Command-line interface for the PII Redaction Tool.

Usage:
    python redact_pii.py [INPUT] [OPTIONS]

Examples:
    python redact_pii.py "Red Herring Prospectus.docx"
    python redact_pii.py "Red Herring Prospectus.docx" -o redacted.docx --verbose
    python redact_pii.py "Red Herring Prospectus.docx" --locale en_US --seed 0
    python redact_pii.py "Red Herring Prospectus.docx" --evaluate ground_truth.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from pii_redactor.consistency import ConsistencyMapper
from pii_redactor.document import DocxRedactor
from pii_redactor.engine import build_analyzer, build_anonymizer
from pii_redactor.evaluator import SpanEvaluator
from pii_redactor.operators import FakerOperators


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="redact_pii",
        description="Redact PII from .docx files using Presidio + Faker.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="Red Herring Prospectus.docx",
        help="Path to the input .docx file (default: 'Red Herring Prospectus.docx')",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        metavar="PATH",
        help="Output path (default: <input>_REDACTED.docx)",
    )
    parser.add_argument(
        "--locale",
        default="en_IN",
        help="Faker locale for synthetic replacements (default: en_IN)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible outputs (default: 42)",
    )
    parser.add_argument(
        "--evaluate",
        metavar="GROUND_TRUTH_JSON",
        default=None,
        help="Path to ground-truth JSON file; triggers evaluation mode",
    )
    parser.add_argument(
        "--export-predictions",
        metavar="PATH",
        default=None,
        help="Export detected spans as JSON (useful for building ground truth)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG logging",
    )
    return parser.parse_args(argv)


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def run(argv=None) -> None:
    args = parse_args(argv)
    _setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("Input file not found: %s", input_path)
        sys.exit(1)

    output_path = (
        Path(args.output)
        if args.output
        else input_path.parent / (input_path.stem + "_REDACTED" + input_path.suffix)
    )

    logger.info("═" * 60)
    logger.info("  PII Redaction Tool  |  github: presidio + faker + python-docx")
    logger.info("═" * 60)
    logger.info("Input : %s", input_path.resolve())
    logger.info("Output: %s", output_path.resolve())
    logger.info("Locale: %s  |  Seed: %s", args.locale, args.seed)

    # ── Build engines ─────────────────────────────────────────────────────────
    logger.info("Building Presidio AnalyzerEngine …")
    analyzer = build_analyzer()
    anonymizer = build_anonymizer()

    logger.info("Initialising Faker operators …")
    faker_ops = FakerOperators(locale=args.locale, seed=args.seed)
    mapper = ConsistencyMapper()

    redactor = DocxRedactor(
        analyzer=analyzer,
        anonymizer=anonymizer,
        faker_operators=faker_ops,
        consistency_mapper=mapper,
    )

    # ── Redact ────────────────────────────────────────────────────────────────
    stats = redactor.redact(input_path, output_path)
    logger.info("Done — %d total PII spans replaced.", stats.total)

    # ── Optional: export predictions JSON ─────────────────────────────────────
    if args.export_predictions:
        pred_path = Path(args.export_predictions)
        pred_path.write_text(json.dumps(stats.detections, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Predictions exported to: %s", pred_path)

    # ── Optional: evaluation ──────────────────────────────────────────────────
    if args.evaluate:
        gt_path = Path(args.evaluate)
        if not gt_path.exists():
            logger.warning("Ground truth file not found: %s — skipping evaluation.", gt_path)
        else:
            logger.info("Running span-level evaluation against: %s", gt_path)
            if args.export_predictions:
                ev = SpanEvaluator.from_json_files(
                    ground_truth_path=str(gt_path),
                    predictions_path=args.export_predictions,
                )
            else:
                ev = SpanEvaluator.from_records(
                    ground_truth_records=json.loads(gt_path.read_text(encoding="utf-8")),
                    prediction_records=stats.detections,
                )
            logger.info(ev.report())
