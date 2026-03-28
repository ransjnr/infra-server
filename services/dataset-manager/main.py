"""Infra dataset manager service."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routers.datasets import router as datasets_router
from database import init_db
from shared.logging_utils import get_logger
from shared.schemas import HealthResponse

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    logger.info("database tables ensured")
    yield


app = FastAPI(
    title="Infra Dataset Manager",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(datasets_router)


@app.get("/")
def hello() -> dict[str, str]:
    logger.info("hello world")
    return {"message": "Hello from Infra dataset-manager"}


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(service="dataset-manager")
