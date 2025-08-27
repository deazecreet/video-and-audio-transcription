from __future__ import annotations
import json
import logging
import os
import re
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field, HttpUrl

from app.api.deps import get_transcriber, rate_limit
from app.core.config import settings
from app.services.transcriber import WhisperTranscriber
from app.services.youtube import fetch_audio_mp3

logger = logging.getLogger("yt_transcriber")
router = APIRouter(prefix="/transcribe", tags=["transcribe"])

class TranscribeReq(BaseModel):
    youtube_url: HttpUrl
    language: str | None = Field(default=None, description="contoh: 'id' atau 'en'")

def _human(n: int) -> str:
    for unit in ("B","KB","MB","GB","TB"):
        if n < 1024: return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"

def _sanitize(name: str) -> str:
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s\-]+", "_", name)
    return name.strip("_") or "audio"

def _to_paragraph_text(result: Dict) -> str:
    """Gabungkan semua chunk->text jadi paragraf rapi (tanpa timestamp)."""
    chunks = result.get("chunks") or []
    if chunks:
        text = " ".join((c.get("text") or "").strip() for c in chunks)
    else:
        text = (result.get("text") or "")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"([.!?])\s+", r"\1\n\n", text)
    return text

# ---- A) YOUTUBE: JSON body (language di body juga) ----------------------------
@router.post("", dependencies=[Depends(rate_limit)])
async def transcribe_youtube(
    req: TranscribeReq,
    transcriber: WhisperTranscriber = Depends(get_transcriber)
):
    logger.info("Request(YT) | url=%s lang=%s", req.youtube_url, req.language or settings.default_lang)

    # 1) Unduh/ambil audio (skip bila mp3 sudah ada)
    try:
        audio_path, base = fetch_audio_mp3(
            youtube_url=str(req.youtube_url),
            out_dir=settings.data_tmp_dir,
            cookies_path=settings.yt_cookies_path
        )
        size = os.path.getsize(audio_path)
        logger.info("Audio siap | file=%s size=%s", audio_path, _human(size))
    except Exception as e:
        logger.exception("Gagal unduh/ambil audio")
        raise HTTPException(status_code=400, detail=f"Gagal mengunduh audio: {e}")

    # 2) Transkripsi
    try:
        logger.info("Mulai transkripsi...")
        result = transcriber.transcribe(audio_path, language=req.language)
        logger.info("Transkripsi selesai | lang=%s len_text=%d", result.get("language"), len(result.get("text") or ""))
    except Exception as e:
        logger.exception("Gagal transkripsi")
        raise HTTPException(status_code=500, detail=f"Gagal transkripsi: {e}")

    # 3) Simpan output TANPA timestamp (overwrite)
    out_json = Path(settings.data_out_dir) / f"{base}.json"
    out_txt  = Path(settings.data_out_dir) / f"{base}.txt"

    try:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        paragraph = _to_paragraph_text(result)
        with open(out_txt, "w", encoding="utf-8") as f:
            f.write(paragraph + "\n")
        logger.info("Output disimpan | json=%s txt=%s", out_json, out_txt)
    except Exception as e:
        logger.exception("Gagal menyimpan output")
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan output: {e}")

    return {
        "ok": True,
        "title": base,
        "language": result.get("language"),
        "text_preview": (_to_paragraph_text(result)[:200]),
        "paths": {"json": str(out_json), "txt": str(out_txt)}
    }

# ---- B) FILE: multipart/form-data -------------------------------------------
@router.post("/file", dependencies=[Depends(rate_limit)])
async def transcribe_file(
    file: UploadFile = File(..., description="Kirim file audio (.mp3/.m4a/.aac/.wav)"),
    language: str | None = Form(None),
    transcriber: WhisperTranscriber = Depends(get_transcriber)
):
    # Peta MIME -> ekstensi yang kita dukung
    mime_map = {
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/mp4": ".m4a",      # m4a sering terdeteksi sebagai audio/mp4
        "audio/x-m4a": ".m4a",
        "audio/m4a": ".m4a",
        "audio/aac": ".aac",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "application/octet-stream": None,  # fallback: tebak dari filename
    }
    ctype = (file.content_type or "").lower()
    ext = mime_map.get(ctype)

    if ext is None:
        # Jika octet-stream atau tidak dikenali, coba tebak dari nama file
        guessed = Path(file.filename or "").suffix.lower()
        if guessed in {".mp3", ".m4a", ".aac", ".wav"}:
            ext = guessed

    if ext not in {".mp3", ".m4a", ".aac", ".wav"}:
        raise HTTPException(status_code=400, detail=f"Tipe file tidak didukung: {file.content_type}")

    # Simpan ke tmp sesuai ekstensi asli
    base_name = _sanitize(Path(file.filename or f"audio{ext}").stem)
    tmp_in = Path(settings.data_tmp_dir) / f"{base_name}{ext}"
    try:
        with open(tmp_in, "wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        logger.info("Upload diterima | file=%s size=%s", tmp_in, _human(tmp_in.stat().st_size))
    finally:
        await file.close()

    # Jika bukan mp3, konversi cepat ke mp3 agar pipeline konsisten
    tmp_for_asr = tmp_in
    if ext != ".mp3":
        tmp_mp3 = Path(settings.data_tmp_dir) / f"{base_name}.mp3"
        # butuh ffmpeg di PATH
        import subprocess
        cmd = ["ffmpeg", "-y", "-i", str(tmp_in), "-vn", "-acodec", "libmp3lame", "-ar", "44100", "-ab", "192k", str(tmp_mp3)]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            tmp_for_asr = tmp_mp3
            logger.info("Dikonversi ke MP3 | src=%s -> dst=%s", tmp_in, tmp_mp3)
        except subprocess.CalledProcessError as e:
            logger.exception("Gagal konversi ffmpeg")
            raise HTTPException(status_code=400, detail="Gagal mengonversi audio. Pastikan ffmpeg terpasang.")

    # Transkripsi
    try:
        logger.info("Mulai transkripsi (file)...")
        result = transcriber.transcribe(str(tmp_for_asr), language=language)
        logger.info("Transkripsi selesai | lang=%s len_text=%d", result.get("language"), len(result.get("text") or ""))
    except Exception as e:
        logger.exception("Gagal transkripsi file")
        raise HTTPException(status_code=500, detail=f"Gagal transkripsi: {e}")

    # Simpan output (nama mengikuti base_name)
    out_json = Path(settings.data_out_dir) / f"{base_name}.json"
    out_txt  = Path(settings.data_out_dir) / f"{base_name}.txt"
    try:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        paragraph = _to_paragraph_text(result)
        with open(out_txt, "w", encoding="utf-8") as f:
            f.write(paragraph + "\n")
        logger.info("Output disimpan | json=%s txt=%s", out_json, out_txt)
    except Exception as e:
        logger.exception("Gagal menyimpan output")
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan output: {e}")

    return {
        "ok": True,
        "title": base_name,
        "language": result.get("language"),
        "text_preview": (_to_paragraph_text(result)[:200]),
        "paths": {"json": str(out_json), "txt": str(out_txt)}
    }