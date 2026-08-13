"""
consistency.py
==============
ConsistencyMapper guarantees that every unique original PII span always maps
to exactly one synthetic replacement for the lifetime of a processing run.

This is critical for coherence: "Rashi Patil" must become the same fake name
on page 1 and page 200, not two different names.

Thread-safety: not required (single-threaded CLI / script context).
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, Tuple

logger = logging.getLogger(__name__)


class ConsistencyMapper:
    """
    Caches (entity_type, normalised_original) → synthetic_replacement.

    Normalisation: strip whitespace + fold to lower-case for the lookup key,
    but store and return the *original* casing in the fake value.
    """

    def __init__(self) -> None:
        # {(entity_type, normalised_original): fake_value}
        self._cache: Dict[Tuple[str, str], str] = {}

    # ── Public ────────────────────────────────────────────────────────────────

    def get_or_create(
        self,
        entity_type: str,
        original: str,
        generator: Callable[[str], str],
    ) -> str:
        """
        Return the cached fake for (entity_type, original), or generate and
        cache a new one using `generator(original)`.
        """
        key = (entity_type, original.strip().lower())
        if key not in self._cache:
            self._cache[key] = generator(original)
        return self._cache[key]

    def __len__(self) -> int:
        return len(self._cache)

    def log_summary(self, verbose: bool = False) -> None:
        logger.info("Consistency map: %d unique PII spans cached.", len(self._cache))
        if verbose:
            for (etype, orig), fake in sorted(self._cache.items()):
                logger.debug("  [%s]  %r  →  %r", etype, orig, fake)

    @property
    def mapping(self) -> Dict[Tuple[str, str], str]:
        """Read-only view of the full cache (for reporting / evaluation)."""
        return dict(self._cache)
