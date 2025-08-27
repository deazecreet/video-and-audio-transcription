import os
from huggingface_hub import snapshot_download

MODEL_ID  = os.getenv("MODEL_ID", "openai/whisper-large-v3-turbo")
LOCAL_DIR = os.getenv("MODEL_LOCAL_DIR", "./models/whisper-large-v3-turbo")

os.makedirs(LOCAL_DIR, exist_ok=True)

snapshot_download(
    repo_id=MODEL_ID,
    local_dir=LOCAL_DIR,
    local_dir_use_symlinks=False,
    revision="main",
)

print(f"✅ Model stored at: {LOCAL_DIR}")
