from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings
from app.db import SessionLocal
from app.services.collector import fetch_all_sources


scheduler = BackgroundScheduler(timezone="UTC")


def run_collection_job() -> None:
    db = SessionLocal()
    try:
        fetch_all_sources(db)
    finally:
        db.close()


def start_scheduler() -> None:
    settings = get_settings()
    if not settings.scheduler_enabled or scheduler.running:
        return
    scheduler.add_job(
        run_collection_job,
        trigger=IntervalTrigger(hours=settings.fetch_interval_hours),
        id="collect_sources",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
