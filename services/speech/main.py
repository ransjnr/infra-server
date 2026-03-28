"""Infra speech service."""

from __future__ import annotations

import asyncio
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, File, HTTPException, Request, UploadFile

from config import settings
from intelligence_client import analyze_transcription
from schemas import TranscribeResponse
from shared.logging_utils import get_logger
from shared.schemas import HealthResponse
from transcription import AudioDecodeError, load_whisper_model, transcribe_file

logger = get_logger(__name__)

_ALLOWED_AUDIO_SUFFIXES = frozenset({".mp3", ".wav"})


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    logger.info("loading Whisper model %s", settings.whisper_model)
    fastapi_app.state.whisper = await asyncio.to_thread(
        load_whisper_model,
        settings.whisper_model,
    )
    fastapi_app.state.http = httpx.AsyncClient(timeout=settings.intelligence_request_timeout_s)
    yield
    await fastapi_app.state.http.aclose()


app = FastAPI(title="Infra Speech", version="0.1.0", lifespan=lifespan)


@app.get("/")
def hello() -> dict[str, str]:
    logger.info("hello world")
    return {"message": "Hello from Infra speech"}


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(service="speech")


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(
    request: Request,
    file: UploadFile = File(..., description="Audio file (.mp3 or .wav)."),
) -> TranscribeResponse:
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in _ALLOWED_AUDIO_SUFFIXES:
        raise HTTPException(
            status_code=415,
            detail="Only .mp3 and .wav uploads are supported.",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty upload.")
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {settings.max_upload_bytes} bytes.",
        )

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(raw)
            tmp_path = tmp.name

        try:
            text = await asyncio.to_thread(
                transcribe_file,
                request.app.state.whisper,
                tmp_path,
            )
        except AudioDecodeError as exc:
            logger.warning("transcription decode error: %s", exc)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if tmp_path is not None:
            Path(tmp_path).unlink(missing_ok=True)

    if not text:
        raise HTTPException(
            status_code=422,
            detail="No speech could be detected in the audio.",
        )

    client: httpx.AsyncClient = request.app.state.http
    try:
        analysis = await analyze_transcription(
            client,
            base_url=settings.intelligence_service_url,
            text=text,
        )
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        logger.warning("intelligence HTTP error: %s", code)
        if code == 503:
            raise HTTPException(
                status_code=502,
                detail="Intelligence service unavailable (e.g. missing GHANA_NLP_API_KEY).",
            ) from exc
        raise HTTPException(
            status_code=502,
            detail=f"Intelligence service returned {code}.",
        ) from exc
    except httpx.RequestError as exc:
        logger.warning("intelligence request failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Could not reach the intelligence service.",
        ) from exc

    return TranscribeResponse(
        transcription=text,
        translation=str(analysis.get("translation", "")),
        detected_languages=list(analysis.get("detected_languages", [])),
        sentiment_score=float(analysis.get("sentiment_score", 0.0)),
        modality=str(analysis.get("modality", "unknown")),
    )
