# Video & Audio Transcription API

This is a FastAPI service for transcribing YouTube videos or audio files using Whisper (Hugging Face Transformers).

It supports input:

- YouTube URL — audio is downloaded with `yt-dlp`
- Audio file (`.mp3`, `.m4a`, `.aac`, `.wav`)

It creates output:

- JSON — language, full text, segments, file paths
- TXT — plain text transcript

---

## Features

- REST API built with FastAPI
- Can work offline (download model once, then run without internet)
- Saves outputs in `data/transcripts/`
- Concurrency limit for safe memory use
- Logging to console and file

---

## Project Structure

```
app/
  api/               # API routes
  core/              # config and settings
  services/          # transcription and YouTube helpers
  main.py            # FastAPI entrypoint
scripts/
  prefetch_model.py  # script to download model for offline use
data/
  transcripts/       # transcript results (JSON/TXT)
  tmp_audio/         # temporary audio files
.env.example         # environment variables template
requirements.txt
```

---

## Requirements

- Python 3.10+
- ffmpeg installed

### Install ffmpeg

- Ubuntu/Debian

  ```bash
  sudo apt update && sudo apt install -y ffmpeg
  ```
- Windows: download from https://ffmpeg.org/download.html and add `bin` to PATH.

---

## Setup

### 1) Clone repo

```bash
git clone https://github.com/<username>/<repo>.git
cd <repo>
```

### 2) Virtual environment and install

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

### 3) Environment Variables

Copy from example and edit:

```bash
cp .env.example .env
```

Example `.env`:

```ini
# Model
MODEL_ID=openai/whisper-large-v3-turbo
MODEL_LOCAL_DIR=./models/whisper-large-v3-turbo
HF_HOME=./.hf_cache
TRANSFORMERS_OFFLINE=0  # set 1 to force offline
DEFAULT_LANG=id

# I/O
DATA_TMP_DIR=./data/tmp_audio
DATA_OUT_DIR=./data/transcripts

# Concurrency
MAX_CONCURRENCY=2       # number of parallel jobs per process

# YouTube (optional)
YT_COOKIES_PATH=
```

---

## Offline Mode (optional)

1) Download model (prefetch):

```bash
python scripts/prefetch_model.py
```

2) Enable offline mode in `.env`:

```
TRANSFORMERS_OFFLINE=1
MODEL_LOCAL_DIR=./models/whisper-large-v3-turbo
HF_HOME=./.hf_cache
```

---

## Run Server

```bash
uvicorn app.main:app --reload
# Open: http://127.0.0.1:8000
```

Health check:

```bash
curl http://127.0.0.1:8000/
```

---

## API Endpoints

### 1) POST /transcribe — YouTube

Body (JSON):

```json
{ "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID", "language": "id" }
```

Example:

```bash
curl -X POST http://127.0.0.1:8000/transcribe \
  -H "Content-Type: application/json" \
  -d '{"youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID", "language": "id"}'
```

Response:

```json
{
  "ok": true,
  "title": "Video_Title-VIDEO_ID",
  "language": "id",
  "text_preview": "...",
  "paths": {
    "json": "data/transcripts/Video_Title-VIDEO_ID.json",
    "txt": "data/transcripts/Video_Title-VIDEO_ID.txt"
  }
}
```

### 2) POST /transcribe/file — Upload file

Form-Data:

- file: audio file
- language: optional

Example:

```bash
curl -X POST http://127.0.0.1:8000/transcribe/file \
  -F "file=@/path/to/audio.mp3" \
  -F "language=id"
```

---

## Concurrency

The service runs heavy work (yt-dlp download, ffmpeg convert, Whisper inference) in a threadpool, so the event loop stays responsive. Effective parallelism is controlled by `MAX_CONCURRENCY` (per process). Increase carefully based on your CPU/GPU memory.

To test parallel requests (e.g., in Postman), set `MAX_CONCURRENCY > 1` and send multiple requests simultaneously.

---

## Output

- JSON and TXT in `data/transcripts/`
- Temp audio in `data/tmp_audio/`

For YouTube inputs, output files include the video ID to avoid collisions:

```
data/transcripts/<sanitized-title>-<VIDEO_ID>.json
data/transcripts/<sanitized-title>-<VIDEO_ID>.txt
```

---

## Docker (optional)

```Dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Run:

```bash
docker build -t transcriber .
docker run --rm -p 8000:8000 -v $(pwd)/data:/app/data transcriber
```

---

## Notes

- Ensure `ffmpeg` is installed and in PATH (Windows: add `bin` to PATH).
- For GPU installs, consider installing PyTorch following the official guide for your CUDA version rather than a fixed wheel.

---

## Contribute

Contributions welcome! Open an issue first for big changes.
