"""Dataset quality scoring from registration metadata."""

from typing import Any

# Ghana NLP / Khaya platform language codes (translation & related APIs).
# See: https://translation.ghananlp.org/ — keep in sync with product docs.
GHANA_NLP_SUPPORTED_LANGUAGES: frozenset[str] = frozenset(
    {
        "en",
        "tw",
        "ee",
        "gaa",
        "dag",
        "dga",
        "fat",
        "gur",
        "nzi",
        "kpo",
        "yo",
        "ki",
    }
)

_CULTURAL_MARKERS: frozenset[str] = frozenset({"proverb", "slang"})


def calculate_health_score(metadata: dict[str, Any]) -> int:
    """
    Return a 0–100 score from registration metadata.

    - description longer than 50 characters: +20
    - language is a Ghana NLP supported code: +30
    - tags contain cultural markers (e.g. proverb, slang): +50
    """
    score = 0

    description = metadata.get("description") or ""
    if isinstance(description, str) and len(description) > 50:
        score += 20

    language = metadata.get("language") or ""
    if isinstance(language, str):
        code = language.strip().lower()
        if code in GHANA_NLP_SUPPORTED_LANGUAGES:
            score += 30

    tags = metadata.get("tags") or []
    if isinstance(tags, list):
        normalized = {str(t).lower().strip() for t in tags if t is not None}
        if normalized & _CULTURAL_MARKERS:
            score += 50

    return min(score, 100)
