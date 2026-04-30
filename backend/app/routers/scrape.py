from __future__ import annotations

import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import engine, get_session
from ..models import Article, Base
from ..schemas import ScrapeRequest
from ..scrape_sources import SOURCES
from ..scraper import fetch_article_detail, fetch_list_items

router = APIRouter(prefix="/api/scrape", tags=["scrape"])


async def _init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@router.post("")
async def scrape(req: ScrapeRequest, session: AsyncSession = Depends(get_session)) -> dict:
    await _init_db()

    want = set(req.categories or [])
    sources = [s for s in SOURCES if (not want or s.category in want)]

    created = 0
    updated = 0
    skipped = 0
    errors: list[str] = []

    for source in sources:
        for page in range(1, req.max_pages + 1):
            page_suffix = "" if page == 1 else f"_{page}"
            if "{page_suffix}" in source.list_url_template:
                list_url = source.list_url_template.format(page_suffix=page_suffix)
            else:
                # e.g. homepage sources
                list_url = source.list_url_template
            try:
                items = fetch_list_items(list_url)
            except Exception as e:
                errors.append(f"{source.category} page {page}: {e}")
                continue

            # Some categories might be missing / renamed; skip empties silently
            if not items:
                skipped += 1
                continue

            for it in items:
                existing = (
                    await session.execute(select(Article).where(Article.source_url == it.source_url))
                ).scalars().first()

                if existing and existing.content_text:
                    skipped += 1
                    continue

                try:
                    title, content_html, content_text = fetch_article_detail(it.source_url)
                except Exception as e:
                    errors.append(f"detail {it.source_url}: {e}")
                    continue

                if existing:
                    existing.title = title or existing.title
                    existing.summary = it.summary or existing.summary
                    existing.published_at = it.published_at or existing.published_at
                    existing.content_html = content_html
                    existing.content_text = content_text
                    existing.scraped_at = datetime.utcnow()
                    updated += 1
                else:
                    session.add(
                        Article(
                            category=source.category,
                            source_url=it.source_url,
                            title=title or it.title,
                            summary=it.summary,
                            published_at=it.published_at,
                            content_html=content_html,
                            content_text=content_text,
                        )
                    )
                    created += 1

            await session.commit()
            await asyncio.sleep(0.3)

    return {"created": created, "updated": updated, "skipped": skipped, "errors": errors}

