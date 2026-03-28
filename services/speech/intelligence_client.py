"""Async client for the intelligence service ``/analyze`` endpoint."""

from __future__ import annotations

from typing import Any

import httpx


async def analyze_transcription(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    text: str,
) -> dict[str, Any]:
    """POST ``/analyze`` with the transcribed text; returns parsed JSON body."""
    url = f"{base_url.rstrip('/')}/analyze"
    response = await client.post(url, json={"text": text})
    response.raise_for_status()
    return response.json()
