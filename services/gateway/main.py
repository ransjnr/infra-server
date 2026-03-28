"""Infra API gateway — auth, reverse proxy, merged OpenAPI for Swagger UI."""

from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from starlette.responses import Response

from auth_deps import require_api_user
from auth_router import router as auth_router
from config import settings
from database import init_db
from models import User
from openapi_merge import ensure_bearer_security_scheme, merge_upstream_into_schema
from proxy import forward_request
from shared.logging_utils import get_logger
from shared.schemas import HealthResponse

logger = get_logger(__name__)

_PROXY_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    init_db()
    logger.info("gateway database tables ensured")
    fastapi_app.state.http = httpx.AsyncClient(
        timeout=settings.proxy_timeout_s,
        follow_redirects=False,
    )
    yield
    await fastapi_app.state.http.aclose()


app = FastAPI(
    title="Infra API",
    version="0.2.0",
    lifespan=lifespan,
    description=(
        "Single entry point: **JWT** (`/auth/login`) and proxied routes to "
        "**dataset-manager** (`/api/datasets/...`), **intelligence** (`/api/intelligence/...`), "
        "and **speech** (`/api/speech/...`). Use **Authorize** with a Bearer token for protected "
        "routes. Upstream OpenAPI paths are merged into this document."
    ),
    openapi_tags=[
        {"name": "authentication", "description": "Register, login, and current user (PostgreSQL-backed)."},
        {"name": "gateway", "description": "Gateway entry and health."},
    ],
)

_cors_origins = settings.cors_origin_list()
_allow_credentials = _cors_origins != ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/", tags=["gateway"])
def hello() -> dict[str, str]:
    logger.info("hello world")
    return {"message": "Hello from Infra gateway"}


@app.get("/health", response_model=HealthResponse, tags=["gateway"])
def health() -> HealthResponse:
    """Gateway health (does not probe upstreams)."""
    return HealthResponse(service="gateway")


async def _datasets_root(
    request: Request,
    _user: User | None = Depends(require_api_user),
) -> Response:
    _ = _user
    client: httpx.AsyncClient = request.app.state.http
    return await forward_request(
        client,
        request,
        base_url=settings.dataset_manager_url,
        path="",
    )


async def _datasets_subpath(
    request: Request,
    full_path: str,
    _user: User | None = Depends(require_api_user),
) -> Response:
    _ = _user
    client: httpx.AsyncClient = request.app.state.http
    return await forward_request(
        client,
        request,
        base_url=settings.dataset_manager_url,
        path=full_path,
    )


async def _intelligence_root(
    request: Request,
    _user: User | None = Depends(require_api_user),
) -> Response:
    _ = _user
    client: httpx.AsyncClient = request.app.state.http
    return await forward_request(
        client,
        request,
        base_url=settings.intelligence_service_url,
        path="",
    )


async def _intelligence_subpath(
    request: Request,
    full_path: str,
    _user: User | None = Depends(require_api_user),
) -> Response:
    _ = _user
    client: httpx.AsyncClient = request.app.state.http
    return await forward_request(
        client,
        request,
        base_url=settings.intelligence_service_url,
        path=full_path,
    )


async def _speech_root(
    request: Request,
    _user: User | None = Depends(require_api_user),
) -> Response:
    _ = _user
    client: httpx.AsyncClient = request.app.state.http
    return await forward_request(
        client,
        request,
        base_url=settings.speech_service_url,
        path="",
    )


async def _speech_subpath(
    request: Request,
    full_path: str,
    _user: User | None = Depends(require_api_user),
) -> Response:
    _ = _user
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


def custom_openapi() -> dict:
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    ensure_bearer_security_scheme(openapi_schema)
    apply_sec = settings.auth_enabled
    with httpx.Client(timeout=30.0) as client:
        merge_upstream_into_schema(
            openapi_schema,
            client=client,
            base_url=settings.dataset_manager_url,
            api_prefix="/api/datasets",
            schema_prefix="dm_",
            apply_bearer_security=apply_sec,
        )
        merge_upstream_into_schema(
            openapi_schema,
            client=client,
            base_url=settings.intelligence_service_url,
            api_prefix="/api/intelligence",
            schema_prefix="intel_",
            apply_bearer_security=apply_sec,
        )
        merge_upstream_into_schema(
            openapi_schema,
            client=client,
            base_url=settings.speech_service_url,
            api_prefix="/api/speech",
            schema_prefix="speech_",
            apply_bearer_security=apply_sec,
        )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
