"""Async calls to Ghana NLP Khaya translation HTTP API (httpx)."""

from __future__ import annotations

import httpx


async def translate_text(
    client: httpx.AsyncClient,
    *,
    api_key: str,
    text: str,
    language_pair: str,
    base_url: str,
) -> str:
    """
    POST /v1/translate with body ``{"in": text, "lang": language_pair}``.

    Auth uses ``Ocp-Apim-Subscription-Key`` (Khaya / Azure API Management style).
    """
    url = f"{base_url.rstrip('/')}/v1/translate"
    headers = {
        "Ocp-Apim-Subscription-Key": api_key,
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }
    response = await client.post(
        url,
        json={"in": text, "lang": language_pair},
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        for key in ("text", "translation", "out", "result", "message"):
            val = data.get(key)
            if isinstance(val, str):
                return val
    return str(data)
