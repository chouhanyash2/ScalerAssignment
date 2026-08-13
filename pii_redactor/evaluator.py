"""
evaluator.py
============
Span-level evaluation: Precision, Recall, F1, and Accuracy.

Usage (programmatic):
    evaluator = SpanEvaluator()
    evaluator.add_ground_truth("PERSON", 10, 20)
    evaluator.add_prediction("PERSON", 10, 20, "John Doe")
    metrics = evaluator.compute()

Usage (from file):
    metrics = SpanEvaluator.from_json_files(
        ground_truth_path="ground_truth.json",
        predictions_path="predictions.json",
    )

Ground truth JSON format:
[
  {"entity_type": "PERSON", "start": 10, "end": 20, "text": "Rashi Patil"},
  ...
]
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

SPAN_MATCH_TOLERANCE: int = 2  # characters of allowed boundary slack


@dataclass
class Span:
    entity_type: str
    start: int
    end: int
    text: Optional[str] = None
    source: Optional[str] = None


@dataclass
class EntityMetrics:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def accuracy(self) -> float:
        """Jaccard / span-level accuracy = TP / (TP + FP + FN)."""
        denom = self.tp + self.fp + self.fn
        return self.tp / denom if denom else 0.0


class SpanEvaluator:
    """
    Computes span-level evaluation metrics.

    A prediction is a True Positive if:
      - entity_type matches the ground truth, AND
      - |pred.start - gt.start| <= SPAN_MATCH_TOLERANCE, AND
      - |pred.end   - gt.end|   <= SPAN_MATCH_TOLERANCE
    """

    def __init__(self) -> None:
        self._ground_truth: List[Span] = []
        self._predictions: List[Span] = []

    def add_ground_truth(
        self, entity_type: str, start: int, end: int, text: Optional[str] = None
    ) -> None:
        self._ground_truth.append(Span(entity_type, start, end, text))

    def add_prediction(
        self, entity_type: str, start: int, end: int, text: Optional[str] = None
    ) -> None:
        self._predictions.append(Span(entity_type, start, end, text))

    def add_ground_truth_record(self, item: dict) -> None:
        self._ground_truth.append(Span(
            item["entity_type"], item["start"], item["end"], item.get("text"), item.get("source")
        ))

    def add_prediction_record(self, item: dict) -> None:
        self._predictions.append(Span(
            item["entity_type"], item["start"], item["end"], item.get("text"), item.get("source")
        ))

    def compute(self) -> Dict[str, EntityMetrics]:
        """Return per-entity metrics dict plus an 'OVERALL' key."""
        entity_types = {s.entity_type for s in self._ground_truth + self._predictions}
        metrics: Dict[str, EntityMetrics] = {et: EntityMetrics() for et in entity_types}
        metrics["OVERALL"] = EntityMetrics()

        matched_gt: set = set()
        matched_pred: set = set()

        for pi, pred in enumerate(self._predictions):
            for gi, gt in enumerate(self._ground_truth):
                if gi in matched_gt:
                    continue
                if pred.entity_type != gt.entity_type:
                    continue
                if pred.source and gt.source and pred.source != gt.source:
                    continue
                if (
                    abs(pred.start - gt.start) <= SPAN_MATCH_TOLERANCE
                    and abs(pred.end - gt.end) <= SPAN_MATCH_TOLERANCE
                ):
                    # True Positive
                    metrics[pred.entity_type].tp += 1
                    metrics["OVERALL"].tp += 1
                    matched_gt.add(gi)
                    matched_pred.add(pi)
                    break

        # False Positives: predictions not matched
        for pi, pred in enumerate(self._predictions):
            if pi not in matched_pred:
                metrics[pred.entity_type].fp += 1
                metrics["OVERALL"].fp += 1

        # False Negatives: ground truths not matched
        for gi, gt in enumerate(self._ground_truth):
            if gi not in matched_gt:
                metrics[gt.entity_type].fn += 1
                metrics["OVERALL"].fn += 1

        return metrics

    def report(self) -> str:
        metrics = self.compute()
        lines = [
            "\n── Evaluation Report ─────────────────────────────────────────────────────",
            f"  {'Entity':<22} {'TP':>5} {'FP':>5} {'FN':>5} "
            f"{'Precision':>10} {'Recall':>8} {'F1':>8} {'Accuracy':>10}",
            "  " + "─" * 74,
        ]

        for et in sorted(metrics.keys()):
            if et == "OVERALL":
                continue
            m = metrics[et]
            lines.append(
                f"  {et:<22} {m.tp:>5} {m.fp:>5} {m.fn:>5} "
                f"{m.precision:>9.1%} {m.recall:>7.1%} {m.f1:>7.1%} {m.accuracy:>9.1%}"
            )

        ov = metrics.get("OVERALL", EntityMetrics())
        lines += [
            "  " + "─" * 74,
            f"  {'OVERALL':<22} {ov.tp:>5} {ov.fp:>5} {ov.fn:>5} "
            f"{ov.precision:>9.1%} {ov.recall:>7.1%} {ov.f1:>7.1%} {ov.accuracy:>9.1%}",
            "─" * 76,
        ]
        return "\n".join(lines)

    # ── Convenience constructors ──────────────────────────────────────────────

    @classmethod
    def from_records(
        cls,
        ground_truth_records: List[dict],
        prediction_records: List[dict],
    ) -> "SpanEvaluator":
        """Load ground truth and predictions from in-memory dictionaries."""
        ev = cls()
        for item in ground_truth_records:
            ev.add_ground_truth_record(item)
        for item in prediction_records:
            ev.add_prediction_record(item)
        return ev

    @classmethod
    def from_json_files(
        cls,
        ground_truth_path: str,
        predictions_path: str,
    ) -> "SpanEvaluator":
        """Load ground truth and predictions from JSON files and compute metrics."""
        ev = cls()

        with open(ground_truth_path, encoding="utf-8") as f:
            for item in json.load(f):
                ev.add_ground_truth_record(item)

        with open(predictions_path, encoding="utf-8") as f:
            for item in json.load(f):
                ev.add_prediction_record(item)

        return ev
