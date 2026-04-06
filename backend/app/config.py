from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    nnunet_results_path: Optional[str] = None
    upload_dir: str = "./uploads"
    results_dir: str = "./results"
    max_upload_size_mb: int = 500
    max_cached_models: int = 2
    gpu_device_index: int = 0
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
