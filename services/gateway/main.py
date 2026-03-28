"""Infra API gateway — reverse proxy and CORS entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from proxy import forward_request
from shared.logging_utils import get_logger
from shared.schemas import HealthResponse

logger = get_logger(__name__)

_PROXY_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    fastapi_app.state.http = httpx.AsyncClient(
        timeout=settings.proxy_timeout_s,
        follow_redirects=False,
    )
    yield
    await fastapi_app.state.http.aclose()


app = FastAPI(title="Infra Gateway", version="0.1.0", lifespan=lifespan)

_cors_origins = settings.cors_origin_list()
_allow_credentials = _cors_origins != ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def hello() -> dict[str, str]:
    logger.info("hello world")
    return {"message": "Hello from Infra gateway"}


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    """Global gateway health (does not probe upstreams)."""
    return HealthResponse(service="gateway")


async def _datasets_root(request: Request) -> Response:
    client: httpx.AsyncClient = request.app.state.http
    return await forward_request(
        client,
        request,
        base_url=settings.dataset_manager_url,
        path="",
    )


async def _datasets_subpath(request: Request, full_path: str) -> Response:
    client: httpx.AsyncClient = request.app.state.http
    return await forward_request(
        client,
        request,
        base_url=settings.dataset_manager_url,
        path=full_path,
    )


async def _intelligence_root(request: Request) -> Response:
    client: httpx.AsyncClient = request.app.state.http
    return await forward_request(
        client,
        request,
        base_url=settings.intelligence_service_url,
        path="",
    )


async def _intelligence_subpath(request: Request, full_path: str) -> Response:
    client: httpx.AsyncClient = request.app.state.http
    return await forward_request(
        client,
        request,
        base_url=settings.intelligence_service_url,
        path=full_path,
    )


async def _speech_root(request: Request) -> Response:
    client: httpx.AsyncClient = request.app.state.http
    return await forward_request(
        client,
        request,
        base_url=settings.speech_service_url,
        path="",
    )


async def _speech_subpath(request: Request, full_path: str) -> Response:
    client: httpx.AsyncClient = request.app.state.http
    return await forward_request(
        client,
        request,
        base_url=settings.speech_service_url,
        path=full_path,
    )


app.add_api_route(
    "/api/datasets",
    _datasets_root,
    methods=_PROXY_METHODS,
    name="proxy_datasets_root",
    include_in_schema=False,
)
app.add_api_route(
    "/api/datasets/{full_path:path}",
    _datasets_subpath,
    methods=_PROXY_METHODS,
    name="proxy_datasets",
    include_in_schema=False,
)
app.add_api_route(
    "/api/intelligence",
    _intelligence_root,
    methods=_PROXY_METHODS,
    name="proxy_intelligence_root",
    include_in_schema=False,
)
app.add_api_route(
    "/api/intelligence/{full_path:path}",
    _intelligence_subpath,
    methods=_PROXY_METHODS,
    name="proxy_intelligence",
    include_in_schema=False,
)
app.add_api_route(
    "/api/speech",
    _speech_root,
    methods=_PROXY_METHODS,
    name="proxy_speech_root",
    include_in_schema=False,
)
app.add_api_route(
    "/api/speech/{full_path:path}",
    _speech_subpath,
    methods=_PROXY_METHODS,
    name="proxy_speech",
    include_in_schema=False,
)
