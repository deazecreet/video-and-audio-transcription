from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path

class Settings(BaseSettings):
    app_env: str = Field(default="dev", alias="APP_ENV")

    model_id: str = Field(default="openai/whisper-large-v3-turbo", alias="MODEL_ID")
    model_local_dir: str = Field(default="./models/whisper-large-v3-turbo", alias="MODEL_LOCAL_DIR")
    hf_home: str = Field(default="./.hf_cache", alias="HF_HOME")
    transformers_offline: int = Field(default=1, alias="TRANSFORMERS_OFFLINE")

    yt_cookies_path: str | None = Field(default=None, alias="YT_COOKIES_PATH")
    default_lang: str = Field(default="id", alias="DEFAULT_LANG")

    data_tmp_dir: str = Field(default="./data/tmp_audio", alias="DATA_TMP_DIR")
    data_out_dir: str = Field(default="./data/transcripts", alias="DATA_OUT_DIR")

    max_concurrency: int = Field(default=1, alias="MAX_CONCURRENCY")

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()

# ensure dirs exist
Path(settings.data_tmp_dir).mkdir(parents=True, exist_ok=True)
Path(settings.data_out_dir).mkdir(parents=True, exist_ok=True)
Path(settings.hf_home).mkdir(parents=True, exist_ok=True)
