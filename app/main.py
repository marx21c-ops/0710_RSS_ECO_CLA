from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.db import Base, SessionLocal, engine, ensure_runtime_schema
from app.routers import api, pages
from app.scheduler import run_collection_job, start_scheduler, stop_scheduler
from app.services.collector import ensure_sources


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()
    db = SessionLocal()
    try:
        ensure_sources(db)
    finally:
        db.close()

    if settings.scheduler_enabled and not os.getenv("VERCEL"):
        start_scheduler()
        if settings.fetch_on_startup:
            try:
                run_collection_job()
            except Exception:
                pass

    yield
    stop_scheduler()


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.state.templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(pages.router)
app.include_router(api.router)
