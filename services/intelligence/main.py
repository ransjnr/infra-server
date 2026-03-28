"""Infra intelligence service."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from starlette.requests import Request

from code_switch import default_translation_pair, scan_code_switch
from config import settings
from khaya_translate import translate_text
from schemas import AnalyzeRequest, AnalyzeResponse
from sentiment import load_sentiment_pipeline, score_to_sentiment_scalar
from shared.logging_utils import get_logger
from shared.schemas import HealthResponse

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=settings.khaya_timeout_s)
    logger.info("loading sentiment model %s", "cardiffnlp/twitter-xlm-roberta-base-sentiment")
    await asyncio.to_thread(load_sentiment_pipeline)
    yield
    await app.state.http.aclose()


app = FastAPI(title="Infra Intelligence", version="0.1.0", lifespan=lifespan)


@app.get("/")
def hello() -> dict[str, str]:
    logger.info("hello world")
    return {"message": "Hello from Infra intelligence"}


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(service="intelligence")


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(body: AnalyzeRequest, request: Request) -> AnalyzeResponse:
    if not settings.ghana_nlp_api_key:
        raise HTTPException(
            status_code=503,
            detail="GHANA_NLP_API_KEY is not configured; cannot call Khaya translation.",
        )

    modality, detected_languages = scan_code_switch(body.text)
    pair = body.language_pair or default_translation_pair(modality)

    client: httpx.AsyncClient = request.app.state.http
    try:
        translation = await translate_text(
            client,
            api_key=settings.ghana_nlp_api_key,
            text=body.text,
            language_pair=pair,
            base_url=settings.khaya_base_url,
        )
    except httpx.HTTPStatusError as exc:
        logger.warning("Khaya HTTP error: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=f"Khaya translation failed: {exc.response.status_code}",
        ) from exc
    except httpx.RequestError as exc:
        logger.warning("Khaya request error: %s", exc)
        raise HTTPException(status_code=502, detail="Khaya translation request failed.") from exc

    pipe = load_sentiment_pipeline()

    def _run_sentiment() -> float:
        out = pipe(body.text)
        if isinstance(out, dict):
            out = [out]
        return score_to_sentiment_scalar(out)

    sentiment_score = await asyncio.to_thread(_run_sentiment)

    return AnalyzeResponse(
        detected_languages=detected_languages,
        translation=translation,
        sentiment_score=sentiment_score,
        modality=modality,
    )
