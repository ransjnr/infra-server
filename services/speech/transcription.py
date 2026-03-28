"""Whisper-based transcription with clear errors for bad audio."""

from __future__ import annotations

import subprocess
from typing import Any


class AudioDecodeError(Exception):
    """Raised when audio cannot be decoded or transcribed (likely corrupt or unsupported)."""


def load_whisper_model(model_name: str) -> Any:
    """Load a Whisper model by size name (e.g. ``base``)."""
    import whisper

    return whisper.load_model(model_name)


def transcribe_file(model: Any, path: str) -> str:
    """
    Run Whisper on a file path. ``ffmpeg`` must be on ``PATH``.

    Raises:
        AudioDecodeError: On corrupt/invalid audio or decode failures.
    """
    try:
        result = model.transcribe(path)
    except subprocess.CalledProcessError as exc:
        raise AudioDecodeError("ffmpeg failed while decoding audio.") from exc
    except Exception as exc:
        raise AudioDecodeError(
            "Transcription failed; the file may be corrupt, truncated, or not valid audio."
        ) from exc

    return (result.get("text") or "").strip()
