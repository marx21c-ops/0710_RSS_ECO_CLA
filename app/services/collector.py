from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
from urllib.parse import urljoin

import feedparser
import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Article, Source
from app.services.translation import translated_article_fields
from app.sources import SOURCE_DEFINITIONS


def ensure_sources(db: Session) -> None:
    existing = {source.slug: source for source in db.scalars(select(Source)).all()}
    for item in SOURCE_DEFINITIONS:
        source = existing.get(item["slug"])
        if source:
            for key, value in item.items():
                setattr(source, key, value)
            continue
        db.add(Source(**item))
    db.commit()


def fetch_all_sources(db: Session) -> dict[str, int]:
    ensure_sources(db)
    results: dict[str, int] = {}
    sources = db.scalars(select(Source).where(Source.enabled.is_(True))).all()
    for source in sources:
        if source.source_type == "rss":
            count = fetch_rss_source(db, source)
        else:
            count = fetch_html_source(db, source)
        source.last_fetched_at = datetime.now(timezone.utc)
        db.commit()
        results[source.slug] = count
    return results


def fetch_rss_source(db: Session, source: Source) -> int:
    try:
        response = httpx.get(
            source.url,
            timeout=15,
            follow_redirects=True,
            headers={"User-Agent": "EconomicRSSMonitor/1.0"},
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return 0

    feed = feedparser.parse(response.content)
    inserted = 0
    for entry in feed.entries[:30]:
        url = entry.get("link")
        title = entry.get("title")
        if not url or not title:
            continue
        clean_title = _clean_text(title)
        clean_summary = _clean_text(entry.get("summary", ""))[:1200] or None
        title_ko, summary_ko = translated_article_fields(source.slug, clean_title, clean_summary)
        article = Article(
            source_id=source.id,
            title=clean_title,
            title_ko=title_ko,
            url=url,
            summary=clean_summary,
            summary_ko=summary_ko,
            author=entry.get("author"),
            published_at=_entry_datetime(entry),
            fetched_at=datetime.now(timezone.utc),
            unique_hash=_unique_hash(source.slug, url),
        )
        inserted += _insert_article(db, article)
    return inserted


def fetch_html_source(db: Session, source: Source) -> int:
    try:
        response = httpx.get(source.url, timeout=15, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError:
        return 0

    soup = BeautifulSoup(response.text, "html.parser")
    candidates = []
    for link in soup.select("a[href]"):
        title = _clean_text(link.get_text(" ", strip=True))
        href = link.get("href")
        if not title or not href or len(title) < 8:
            continue
        url = urljoin(source.url, href)
        if "federalreserve.gov" not in url:
            continue
        if source.slug == "fed-feds-notes" and "/econres/notes/feds-notes/" not in url:
            continue
        if source.slug == "fed-selected-interest-rates" and "/releases/h15/" not in url:
            continue
        if source.slug == "fed-foreign-exchange-rates" and "/releases/h10/" not in url:
            continue
        candidates.append((title, url))

    inserted = 0
    seen: set[str] = set()
    for title, url in candidates[:30]:
        if url in seen:
            continue
        seen.add(url)
        title_ko, _ = translated_article_fields(source.slug, title, None)
        article = Article(
            source_id=source.id,
            title=title,
            title_ko=title_ko,
            url=url,
            summary=None,
            summary_ko=None,
            published_at=None,
            fetched_at=datetime.now(timezone.utc),
            unique_hash=_unique_hash(source.slug, url),
        )
        inserted += _insert_article(db, article)
    return inserted


def _insert_article(db: Session, article: Article) -> int:
    db.add(article)
    try:
        db.commit()
        return 1
    except IntegrityError:
        db.rollback()
        return 0


def _entry_datetime(entry: dict) -> datetime | None:
    for key in ("published", "updated", "created"):
        value = entry.get(key)
        if not value:
            continue
        try:
            return parsedate_to_datetime(value)
        except (TypeError, ValueError):
            continue
    return None


def _unique_hash(source_slug: str, url: str) -> str:
    return hashlib.sha256(f"{source_slug}:{url}".encode("utf-8")).hexdigest()


def _clean_text(value: str) -> str:
    value = value or ""
    if "<" in value or "&" in value:
        value = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    return " ".join(value.split())
