from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router
from .config import settings
from .database import Base, SessionLocal, engine
from .services.seed import seed_demo_data


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    if settings.seed_demo:
        with SessionLocal() as db:
            seed_demo_data(db)
    yield


app = FastAPI(
    title="LedgerFlow API",
    version="0.1.0",
    description="Document collection, validation, and workflow automation API.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "documentation": "/docs",
        "health": "/api/health",
    }
