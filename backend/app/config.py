from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "LedgerFlow"
    database_url: str = os.getenv(
        "LEDGERFLOW_DATABASE_URL", "sqlite:///./data/ledgerflow.db"
    )
    upload_dir: Path = Path(os.getenv("LEDGERFLOW_UPLOAD_DIR", "./uploads"))
    seed_demo: bool = _as_bool(os.getenv("LEDGERFLOW_SEED_DEMO"), True)
    max_upload_bytes: int = int(os.getenv("LEDGERFLOW_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "LEDGERFLOW_CORS_ORIGINS", "http://localhost:5173,http://localhost:8080"
        ).split(",")
        if origin.strip()
    )


settings = Settings()
