from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import Article, Source
from app.sources import TOP_NAV


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    return _render_articles(request, db, section="all", source_slug=None)


@router.get("/domestic", response_class=HTMLResponse)
def domestic(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    return _render_articles(request, db, section="domestic", source_slug=None)


@router.get("/domestic/{source_slug}", response_class=HTMLResponse)
def domestic_source(source_slug: str, request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    return _render_articles(request, db, section="domestic", source_slug=source_slug)


@router.get("/global", response_class=HTMLResponse)
def global_economy(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    return _render_articles(request, db, section="global", source_slug=None)


@router.get("/global/{source_slug}", response_class=HTMLResponse)
def global_source(source_slug: str, request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    return _render_articles(request, db, section="global", source_slug=source_slug)


def _render_articles(
    request: Request,
    db: Session,
    section: str,
    source_slug: str | None,
) -> HTMLResponse:
    sources = db.scalars(select(Source).order_by(Source.section, Source.id)).all()
    visible_sources = [source for source in sources if section == "all" or source.section == section]

    statement = select(Article).options(joinedload(Article.source)).join(Source)
    if section != "all":
        statement = statement.where(Source.section == section)
    if source_slug:
        statement = statement.where(Source.slug == source_slug)
    statement = statement.order_by(desc(Article.published_at), desc(Article.fetched_at)).limit(80)
    articles = db.scalars(statement).all()

    counts = dict(
        db.execute(
            select(Source.slug, func.count(Article.id))
            .join(Article, Article.source_id == Source.id, isouter=True)
            .group_by(Source.slug)
        ).all()
    )

    template = "partials/articles.html" if request.headers.get("HX-Request") else "index.html"
    return request.app.state.templates.TemplateResponse(
        template,
        {
            "request": request,
            "top_nav": TOP_NAV,
            "section": section,
            "source_slug": source_slug,
            "sources": sources,
            "visible_sources": visible_sources,
            "articles": articles,
            "counts": counts,
        },
    )
