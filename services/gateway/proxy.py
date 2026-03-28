"""Reverse-proxy helpers (httpx)."""

from __future__ import annotations

import httpx
from starlette.requests import Request
from starlette.responses import Response

_HOP_BY_HOP_REQUEST = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
        "host",
    }
)

_HOP_BY_HOP_RESPONSE = frozenset(
    {
        "connection",
        "keep-alive",
        "transfer-encoding",
        "content-encoding",
    }
)


def _build_target_url(base_url: str, path: str, query: str) -> str:
    base = base_url.rstrip("/")
    segment = path.lstrip("/")
    target = f"{base}/{segment}" if segment else f"{base}/"
    if query:
        target = f"{target}?{query}"
    return target


def _filter_request_headers(request: Request) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in request.headers.items():
        if key.lower() in _HOP_BY_HOP_REQUEST:
            continue
        out[key] = value
    return out


def _filter_response_headers(response: httpx.Response) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in response.headers.multi_items():
        if key.lower() in _HOP_BY_HOP_RESPONSE:
            continue
        out[key] = value
    return out


async def forward_request(
    client: httpx.AsyncClient,
    request: Request,
    *,
    base_url: str,
    path: str,
) -> Response:
    """Proxy the incoming request to ``base_url`` + ``path`` (query string preserved)."""
    target = _build_target_url(base_url, path, request.url.query)
    headers = _filter_request_headers(request)
    body = await request.body()

    upstream = await client.request(
        request.method,
        target,
        headers=headers,
        content=body if body else None,
    )

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=_filter_response_headers(upstream),
        media_type=upstream.headers.get("content-type"),
    )
