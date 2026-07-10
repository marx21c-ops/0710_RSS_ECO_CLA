import re
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.models import Article, Source

try:
    from deep_translator import GoogleTranslator
except ImportError:  # pragma: no cover - optional runtime dependency
    GoogleTranslator = None


KOREAN_RE = re.compile(r"[가-힣]")
GLOBAL_SOURCE_PREFIX = "fed-"


def should_translate(source_slug: str, text: str | None) -> bool:
    if not get_settings().translation_enabled:
        return False
    if not source_slug.startswith(GLOBAL_SOURCE_PREFIX):
        return False
    if not text:
        return False
    return not KOREAN_RE.search(text)


def translated_article_fields(
    source_slug: str,
    title: str,
    summary: str | None,
) -> tuple[str | None, str | None]:
    return (
        translate_to_korean(source_slug, title),
        translate_to_korean(source_slug, summary),
    )


def translate_to_korean(source_slug: str, text: str | None) -> str | None:
    if not should_translate(source_slug, text):
        return None
    if GoogleTranslator is None:
        return None

    normalized = " ".join((text or "").split())
    if not normalized:
        return None

    try:
        translated = _translator().translate(normalized[:4500])
    except Exception:
        return None

    translated = " ".join((translated or "").split())
    if not translated or translated == normalized:
        return None
    return translated


def translate_missing_articles(db: Session, limit: int | None = None) -> int:
    if not get_settings().translation_enabled or GoogleTranslator is None:
        return 0

    statement = (
        select(Article)
        .options(joinedload(Article.source))
        .join(Source)
        .where(Source.slug.like(f"{GLOBAL_SOURCE_PREFIX}%"))
        .where(Article.title_ko.is_(None))
        .order_by(Article.fetched_at.desc())
        .limit(limit or get_settings().translation_backfill_limit)
    )

    updated = 0
    for article in db.scalars(statement).all():
        title_ko, summary_ko = translated_article_fields(
            article.source.slug,
            article.title,
            article.summary,
        )
        if not title_ko and not summary_ko:
            continue
        article.title_ko = title_ko
        article.summary_ko = summary_ko
        updated += 1

    if updated:
        db.commit()
    return updated


@lru_cache(maxsize=1)
def _translator():
    return GoogleTranslator(source="auto", target="ko")
