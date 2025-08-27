from __future__ import annotations
import os
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes_transcribe import router as transcribe_router
from app.core.config import settings
from app.services.transcriber import WhisperTranscriber

# ── Logging setup (console + file)
def _setup_logging() -> logging.Logger:
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "app.log"

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    root = logging.getLogger()
    # hindari duplikasi handler saat reload
    if not root.handlers:
        root.setLevel(logging.INFO)

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter(fmt, datefmt))

        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter(fmt, datefmt))

        root.addHandler(ch)
        root.addHandler(fh)

    return logging.getLogger("yt_transcriber")

logger = _setup_logging()

def create_app() -> FastAPI:
    app = FastAPI(title="YouTube Transcriber", version="0.1.0")

    # CORS sederhana (opsional)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def _startup():
        # set offline/cache environment
        os.environ["HF_HOME"] = settings.hf_home
        os.environ["TRANSFORMERS_OFFLINE"] = str(settings.transformers_offline)
        # warmup: load model sekali
        logger.info("Warming up model from: %s", settings.model_local_dir)
        WhisperTranscriber.get(settings.model_local_dir, settings.default_lang)
        logger.info("Model ready. Default language: %s", settings.default_lang)

    @app.get("/")
    async def root():
        return {"app": "YouTube Transcriber", "status": "ok"}

    app.include_router(transcribe_router)
    return app

app = create_app()
