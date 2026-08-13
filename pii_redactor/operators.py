"""
operators.py
============
Faker-backed OperatorConfig for every entity type.

Each entity maps to a method on FakerOperators so that:
  1. The fake data is contextually realistic (en_IN locale).
  2. Adding a new entity only requires one method + one dict entry.
  3. The seed makes outputs reproducible across runs.
"""

from __future__ import annotations

import random
import string
from typing import Callable, Dict, Optional

from faker import Faker
from presidio_anonymizer.entities import OperatorConfig

from pii_redactor.config import FAKER_LOCALE, FAKER_SEED


class FakerOperators:
    """
    Builds and exposes {entity_type: OperatorConfig} backed by Faker.

    Locale: en_IN (Indian locale) for realistic Indian phone/address format.
    US providers (SSN, credit card) fall back to en_US as needed.
    """

    def __init__(
        self,
        locale: str = FAKER_LOCALE,
        seed: Optional[int] = FAKER_SEED,
    ) -> None:
        self._fake_in = Faker(locale)
        self._fake_us = Faker("en_US")
        if seed is not None:
            Faker.seed(seed)
            random.seed(seed)
        self._operators: Dict[str, OperatorConfig] = self._build()

    # ── Faker helpers — one per entity type ──────────────────────────────────

    def _name(self, _: str) -> str:
        return self._fake_in.name()

    def _email(self, _: str) -> str:
        return self._fake_in.email()

    def _phone(self, original: str) -> str:
        # Preserve the +91 prefix if original had it
        if "+91" in original or original.lstrip().startswith("91"):
            digits = "".join(random.choices(string.digits, k=10))
            # Ensure first digit is 6-9 (valid Indian mobile)
            digits = str(random.randint(6, 9)) + digits[1:]
            return f"+91 {digits[:5]} {digits[5:]}"
        return self._fake_in.phone_number()

    def _org(self, _: str) -> str:
        return self._fake_in.company()

    def _location(self, _: str) -> str:
        return self._fake_in.city()

    def _ssn(self, _: str) -> str:
        return self._fake_us.ssn()

    def _credit_card(self, _: str) -> str:
        return self._fake_us.credit_card_number()

    def _date(self, _: str) -> str:
        return self._fake_in.date_of_birth(minimum_age=18, maximum_age=75).strftime(
            "%d %B %Y"
        )

    def _ip(self, _: str) -> str:
        return self._fake_us.ipv4_private()

    def _url(self, _: str) -> str:
        return self._fake_in.url()

    def _pan(self, _: str) -> str:
        letters = string.ascii_uppercase
        return (
            "".join(random.choices(letters, k=5))
            + "".join(random.choices(string.digits, k=4))
            + random.choice(letters)
        )

    def _aadhaar(self, _: str) -> str:
        # First digit must be non-zero
        d = str(random.randint(2, 9)) + "".join(random.choices(string.digits, k=11))
        return f"{d[0:4]} {d[4:8]} {d[8:12]}"

    def _cin(self, _: str) -> str:
        L = string.ascii_uppercase
        D = string.digits
        status = random.choice(["U", "L"])
        return (
            status
            + "".join(random.choices(D, k=5))
            + "".join(random.choices(L, k=2))
            + "".join(random.choices(D, k=4))
            + "".join(random.choices(L, k=3))
            + "".join(random.choices(D, k=6))
        )

    def _gstin(self, _: str) -> str:
        L = string.ascii_uppercase
        D = string.digits
        state = str(random.randint(1, 35)).zfill(2)
        pan = (
            "".join(random.choices(L, k=5))
            + "".join(random.choices(D, k=4))
            + random.choice(L)
        )
        entity_num = "1"  # default entity number for individual
        z_char = "Z"      # always Z per GSTIN spec
        checksum = random.choice(string.digits + L)
        return state + pan + entity_num + z_char + checksum

    def _ifsc(self, _: str) -> str:
        bank = "".join(random.choices(string.ascii_uppercase, k=4))
        branch = "".join(random.choices(string.digits, k=6))
        return f"{bank}0{branch}"

    def _voter_id(self, _: str) -> str:
        return (
            "".join(random.choices(string.ascii_uppercase, k=3))
            + "".join(random.choices(string.digits, k=7))
        )

    def _passport(self, _: str) -> str:
        return random.choice(string.ascii_uppercase) + "".join(
            random.choices(string.digits, k=7)
        )

    def _driving_license(self, _: str) -> str:
        states = ["MH", "DL", "KA", "TN", "GJ", "UP", "RJ"]
        state = random.choice(states)
        year = str(random.randint(2000, 2023))
        num = "".join(random.choices(string.digits, k=7))
        # Format: <STATE_CODE><2-digit year><4-digit year><7-digit number>
        # e.g. MH20200123456
        return f"{state}{year[2:]}{year}{num}"

    def _iban(self, _: str) -> str:
        return self._fake_us.iban()

    def _nrp(self, _: str) -> str:
        """Generic national registration number."""
        return "NRP-" + "".join(random.choices(string.digits, k=9))

    def _medical_license(self, _: str) -> str:
        prefix = "".join(random.choices(string.ascii_uppercase, k=2))
        return prefix + "-MED-" + "".join(random.choices(string.digits, k=6))

    # ── Builder ───────────────────────────────────────────────────────────────

    def _op(self, fn: Callable[[str], str]) -> OperatorConfig:
        """Wrap a callable as a Presidio 'custom' OperatorConfig."""
        return OperatorConfig("custom", {"lambda": fn})

    def _build(self) -> Dict[str, OperatorConfig]:
        return {
            "PERSON":               self._op(self._name),
            "EMAIL_ADDRESS":        self._op(self._email),
            "PHONE_NUMBER":         self._op(self._phone),
            "ORGANIZATION":         self._op(self._org),
            "LOCATION":             self._op(self._location),
            "US_SSN":               self._op(self._ssn),
            "CREDIT_CARD":          self._op(self._credit_card),
            "DATE_TIME":            self._op(self._date),
            "IP_ADDRESS":           self._op(self._ip),
            "URL":                  self._op(self._url),
            "IN_PAN":               self._op(self._pan),
            "IN_AADHAAR":           self._op(self._aadhaar),
            "IN_CIN":               self._op(self._cin),
            "IN_GSTIN":             self._op(self._gstin),
            "IN_IFSC":              self._op(self._ifsc),
            "IN_VOTER_ID":          self._op(self._voter_id),
            "IN_PASSPORT":          self._op(self._passport),
            "IN_DRIVING_LICENSE":   self._op(self._driving_license),
            "IBAN_CODE":            self._op(self._iban),
            "NRP":                  self._op(self._nrp),
            "MEDICAL_LICENSE":      self._op(self._medical_license),
            # Catch-all for any unrecognised entity type
            "DEFAULT":              OperatorConfig("replace", {"new_value": "<REDACTED>"}),
        }

    @property
    def operators(self) -> Dict[str, OperatorConfig]:
        return self._operators
