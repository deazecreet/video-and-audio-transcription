from __future__ import annotations
import os, re, logging
from typing import Tuple
from yt_dlp import YoutubeDL

logger = logging.getLogger("yt_transcriber")

def _sanitize(name: str) -> str:
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s\-]+", "_", name)
    return name.strip("_")

def fetch_audio_mp3(youtube_url: str, out_dir: str, cookies_path: str | None = None) -> Tuple[str, str]:
    ydl_common = {
        "quiet": True,
        # Sedikit header membantu untuk beberapa edge-case
        "http_headers": {"User-Agent": "Mozilla/5.0"},
        # Coba client Android agar signed URLs/age-gate lebih stabil
        "extractor_args": {"youtube": {"player_client": ["android"]}},
        # Jangan pakai DASH manifest saat hanya mau ambil metadata judul
        "extract_flat": False,
        "noplaylist": True,
        "retries": 10,
        "fragment_retries": 10,
    }
    if cookies_path and os.path.isfile(cookies_path):
        ydl_common["cookiefile"] = cookies_path

    # Ambil judul aman (tanpa unduh)
    with YoutubeDL({**ydl_common, "skip_download": True}) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        raw_title = info.get("title", "audio")
        safe_title = _sanitize(raw_title)

    final_path = os.path.join(out_dir, f"{safe_title}.mp3")
    if os.path.isfile(final_path):
        logger.info("Audio sudah ada | file=%s (skip download)", final_path)
        return final_path, safe_title

    # Opsi unduh dengan fallback agresif ke m4a
    ydl_opts = {
        **ydl_common,
        # Urutan preferensi: m4a -> bestaudio -> best
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": os.path.join(out_dir, f"{safe_title}.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(youtube_url, download=True)

    if not os.path.isfile(final_path):
        raise FileNotFoundError("Audio file not found after yt-dlp process.")

    logger.info("Audio baru diunduh | file=%s", final_path)
    return final_path, safe_title