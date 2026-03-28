"""Hugging Face sentiment pipeline (multilingual RoBERTa)."""

from __future__ import annotations

from typing import Any

_pipeline: Any | None = None

MODEL_ID = "cardiffnlp/twitter-xlm-roberta-base-sentiment"


def load_sentiment_pipeline() -> Any:
    """Load (once) the transformers sentiment-analysis pipeline."""
    global _pipeline
    if _pipeline is None:
        from transformers import pipeline

        _pipeline = pipeline(
            task="sentiment-analysis",
            model=MODEL_ID,
            tokenizer=MODEL_ID,
        )
    return _pipeline


def score_to_sentiment_scalar(outputs: list[dict[str, Any]]) -> float:
    """
    Map HF label + score to roughly [-1, 1].

    The model emits NEGATIVE / NEUTRAL / POSITIVE (or similar) labels.
    """
    if not outputs:
        return 0.0
    top = outputs[0]
    label = str(top.get("label", "")).lower()
    score = float(top.get("score", 0.0))
    if "neg" in label:
        return -score
    if "pos" in label:
        return score
    if "neutral" in label or "neu" in label:
        return 0.0
    return 0.0
