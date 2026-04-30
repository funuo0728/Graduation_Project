from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Article
from ..schemas import ArticleDetailOut, ArticleOut

router = APIRouter(prefix="/api/articles", tags=["articles"])


@router.get("", response_model=list[ArticleOut])
async def list_articles(
    category: str | None = None,
    q: str | None = Query(default=None, min_length=1),
    limit: int = Query(default=30, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> list[ArticleOut]:
    stmt: Select = select(Article)
    if category:
        stmt = stmt.where(Article.category == category)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Article.title.like(like), Article.summary.like(like), Article.content_text.like(like)))
    stmt = stmt.order_by(desc(Article.published_at), desc(Article.scraped_at)).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [ArticleOut.model_validate(r, from_attributes=True) for r in rows]


@router.get("/{article_id}", response_model=ArticleDetailOut)
async def get_article(
    article_id: int,
    session: AsyncSession = Depends(get_session),
) -> ArticleDetailOut:
    row = await session.get(Article, article_id)
    if not row:
        raise HTTPException(status_code=404, detail="Article not found")
    return ArticleDetailOut.model_validate(row, from_attributes=True)

