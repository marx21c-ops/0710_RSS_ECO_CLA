from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import Article, Source
from app.services.collector import fetch_all_sources
from app.services.translation import normalize_korean_terms, translate_missing_articles


router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/articles")
def list_articles(
    section: str | None = Query(default=None),
    source: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[dict]:
    statement = select(Article).options(joinedload(Article.source)).join(Source)
    if section and section != "all":
        statement = statement.where(Source.section == section)
    if source:
        statement = statement.where(Source.slug == source)
    statement = statement.order_by(desc(Article.published_at), desc(Article.fetched_at)).limit(limit)

    return [
        {
            "id": article.id,
            "title": normalize_korean_terms(article.title_ko or article.title),
            "original_title": article.title,
            "url": article.url,
            "summary": normalize_korean_terms(article.summary_ko or article.summary),
            "original_summary": article.summary,
            "published_at": article.published_at,
            "fetched_at": article.fetched_at,
            "source": article.source.name,
            "section": article.source.section,
            "category": article.source.category,
        }
        for article in db.scalars(statement).all()
    ]


@router.post("/fetch-now")
def fetch_now(db: Session = Depends(get_db)) -> dict[str, object]:
    return {"inserted": fetch_all_sources(db)}


@router.get("/fetch-now")
def fetch_now_from_cron(db: Session = Depends(get_db)) -> dict[str, object]:
    return {"inserted": fetch_all_sources(db)}


@router.post("/translate-now")
def translate_now(
    limit: int | None = Query(default=None, ge=1, le=300),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    return {"translated": translate_missing_articles(db, limit)}


@router.get("/translate-now")
def translate_now_from_browser(
    limit: int | None = Query(default=None, ge=1, le=300),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    return {"translated": translate_missing_articles(db, limit)}
