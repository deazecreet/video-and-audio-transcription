from __future__ import annotations
import os, threading
from typing import Any, Dict, List
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

class WhisperTranscriber:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, model_local_dir: str, default_lang: str = "id"):
        self.model_local_dir = model_local_dir
        self.default_lang = default_lang

        torch.backends.cuda.matmul.allow_tf32 = True
        if torch.cuda.is_available():
            torch.set_float32_matmul_precision("high")

        device_str = "cuda" if torch.cuda.is_available() else "cpu"
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        device_index = 0 if torch.cuda.is_available() else -1

        self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_local_dir,
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True,
            local_files_only=True,
        ).to(device_str)

        self.processor = AutoProcessor.from_pretrained(
            model_local_dir,
            local_files_only=True,
        )

        # >>> HAPUS pengaturan chunk_length_s & stride_length_s <<<
        self.pipe = pipeline(
            "automatic-speech-recognition",
            model=self.model,
            tokenizer=self.processor.tokenizer,
            feature_extractor=self.processor.feature_extractor,
            torch_dtype=torch_dtype,
            device=device_index,
        )

    @classmethod
    def get(cls, model_local_dir: str, default_lang: str = "id") -> "WhisperTranscriber":
        with cls._lock:
            if cls._instance is None:
                cls._instance = WhisperTranscriber(model_local_dir, default_lang)
            return cls._instance

    def transcribe(self, file_path: str, language: str | None = None) -> Dict[str, Any]:
        lang = (language or self.default_lang).lower()

        result = self.pipe(
            file_path,
            return_timestamps=True,
            generate_kwargs={"language": lang, "task": "transcribe"},
        )

        chunks: List[dict] = result.get("chunks") or []
        text = " ".join([c.get("text", "").strip() for c in chunks]).strip() or result.get("text", "")

        # Normalisasi timestamp -> float
        def _fmt_ts(ts):
            if ts is None: return None
            if isinstance(ts, (list, tuple)):
                return [float(ts[0]) if ts[0] is not None else None,
                        float(ts[1]) if ts[1] is not None else None]
            return ts

        for c in chunks:
            if "timestamp" in c:
                c["timestamp"] = _fmt_ts(c["timestamp"])

        return {"language": lang, "text": text, "chunks": chunks}
