"""Heuristic detection of English–Twi code-switching in raw text."""

from __future__ import annotations

import re
from typing import Literal

Modality = Literal["code-switched", "english", "twi", "unknown"]

# Common English fragments (lowercased substring match).
_ENGLISH_MARKERS: tuple[str, ...] = (
    "i am ",
    "i'm ",
    " i am",
    "we are",
    "you are",
    "they are",
    " is ",
    " the ",
    " and ",
    "what ",
    "how ",
)

# Twi lexical cues (Unicode); includes user examples and frequent particles.
_TWI_MARKERS: tuple[str, ...] = (
    "kɔ",
    "paa",
    "charlie",
    "ɔ",
    "ɛ",
    "nti",
    "sɛ",
    "ɛyɛ",
    "yɛ",
)


def _normalize(text: str) -> str:
    return text.lower().strip()


def _has_english_marker(text: str) -> bool:
    low = _normalize(text)
    return any(m in low for m in _ENGLISH_MARKERS)


def _has_twi_marker(text: str) -> bool:
    low = _normalize(text)
    if any(m in low for m in _TWI_MARKERS):
        return True
    # Word-token Twi-like roots (ASCII approximations).
    return bool(re.search(r"\b(charlie|paa|nti)\b", low, re.IGNORECASE))


def scan_code_switch(text: str) -> tuple[Modality, list[str]]:
    """
    Scan input text and infer modality plus coarse language labels.

    If both English-like and Twi-like material appear, modality is
    ``code-switched`` and languages default to English + Twi.
    """
    if not text or not text.strip():
        return "unknown", []

    en = _has_english_marker(text)
    tw = _has_twi_marker(text)

    if en and tw:
        return "code-switched", ["en", "tw"]
    if en and not tw:
        return "english", ["en"]
    if tw and not en:
        return "twi", ["tw"]
    return "unknown", []


def default_translation_pair(modality: Modality) -> str:
    """Pick a sensible Khaya pair for the inferred modality."""
    if modality == "twi":
        return "tw-en"
    if modality == "english":
        return "en-tw"
    if modality == "code-switched":
        # Mixed text: translate toward English for a single readable line.
        return "tw-en"
    return "en-tw"
