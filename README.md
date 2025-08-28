# 🎙️ Video & Audio Transcription API

This is a **FastAPI service** for transcribing **YouTube videos** or **audio files** using **Whisper (Hugging Face Transformers)**.

It supports input:

* 🎥 **YouTube URL** → audio is downloaded with `yt-dlp`
* 🎵 **Audio file** (`.mp3`, `.m4a`, `.aac`, `.wav`)

It creates output:

* **JSON** → language, full text, segments, file paths
* **TXT** → plain text transcript

---

## ✨ Features

* REST API built with FastAPI
* Can work **offline** (download model once, then run without internet)
* Save outputs in `data/transcripts/`
* Concurrency limit for safe memory use
* Logging to console and file

---

## 📂 Project Structure

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

## ✅ Requirements

* **Python 3.10+**
* **ffmpeg** installed

### Install ffmpeg

* **Ubuntu/Debian**

  ```bash
  sudo apt update && sudo apt install -y ffmpeg
  ```
* **Windows**: download from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html) and add `bin` to PATH.

---

## 🚀 Setup

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

### 3) Config `.env`

Copy from example:

```bash
cp .env.example .env
```

Edit important values:

```ini
MODEL_ID=openai/whisper-large-v3-turbo
MODEL_LOCAL_DIR=./models/whisper-large-v3-turbo
HF_HOME=./.hf_cache
TRANSFORMERS_OFFLINE=0   # set 1 to force offline
DEFAULT_LANG=id
MAX_CONCURRENCY=2
DATA_TMP_DIR=./data/tmp_audio
DATA_OUT_DIR=./data/transcripts
```

---

## 🧰 Offline Mode (optional)

1. Download model:

```bash
python scripts/prefetch_model.py
```

2. Edit `.env`:

```
TRANSFORMERS_OFFLINE=1
MODEL_LOCAL_DIR=./models/whisper-large-v3-turbo
HF_HOME=./.hf_cache
```

3. Run server.

> Note: `models/` folder is ignored in git.

---

## ▶️ Run Server

```bash
uvicorn app.main:app --reload
# Open: http://127.0.0.1:8000
```

Check health:

```bash
curl http://127.0.0.1:8000/
```

Response:

```json
{"app": "YouTube Transcriber", "status": "ok"}
```

---

## 📡 API Endpoints

### 1) `POST /transcribe` — YouTube

**Body (JSON):**

```json
{ "youtube_url": "https://www.youtube.com/watch?v=...", "language": "id" }
```

**Example cURL:**

```bash
curl -X POST http://127.0.0.1:8000/transcribe \
  -H "Content-Type: application/json" \
  -d '{"youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID", "language": "id"}'
```

**Response:**

```json
{
  "ok": true,
  "title": "Video_Title",
  "language": "id",
  "text_preview": "...",
  "paths": {
    "json": "data/transcripts/Video_Title.json",
    "txt": "data/transcripts/Video_Title.txt"
  }
}
```

---

### 2) `POST /transcribe/file` — Upload file

**Form-Data:**

* `file`: audio file
* `language`: (optional)

**Example cURL:**

```bash
curl -X POST http://127.0.0.1:8000/transcribe/file \
  -F "file=@/path/to/audio.mp3" \
  -F "language=id"
```

---

## 📁 Output

* JSON and TXT in `data/transcripts/`
* Temp audio in `data/tmp_audio/`

---

## 🐳 Docker (optional)

**Dockerfile**

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

## 🤝 Contribute

Contributions welcome! Open an issue first for big changes.

---

## ❓ FAQ

* **Model big?** Folder `models/` is not in git. Download with script.
* **Offline mode?** Yes, download model then set `TRANSFORMERS_OFFLINE=1`.
* **Languages?** Whisper supports many languages, set via request or `.env`.
