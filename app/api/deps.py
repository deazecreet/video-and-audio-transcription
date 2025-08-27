from __future__ import annotations
import asyncio
from fastapi import Depends
from app.core.config import settings
from app.services.transcriber import WhisperTranscriber

# Batasi concurrency (opsional)
_semaphore = asyncio.Semaphore(settings.max_concurrency)

async def rate_limit():
    async with _semaphore:
        yield

def get_transcriber() -> WhisperTranscriber:
    return WhisperTranscriber.get(
        model_local_dir=settings.model_local_dir,
        default_lang=settings.default_lang
    )
