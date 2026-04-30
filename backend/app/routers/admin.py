from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Article, ChatMessage, ChatSession
from ..schemas import AdminArticleCreate, AdminArticleUpdate, ScrapeRequest
from ..settings import settings
from .scrape import scrape as scrape_impl

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _check_token(x_admin_token: str | None) -> None:
    if not settings.admin_token:
        raise HTTPException(status_code=500, detail="ADMIN_TOKEN is not configured on server")
    if not x_admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")


@router.get("/ping")
async def admin_ping(x_admin_token: str | None = Header(default=None)) -> dict:
    _check_token(x_admin_token)
    return {"ok": True}


@router.post("/scrape")
async def admin_scrape(
    req: ScrapeRequest,
    session: AsyncSession = Depends(get_session),
    x_admin_token: str | None = Header(default=None),
) -> dict:
    _check_token(x_admin_token)
    return await scrape_impl(req=req, session=session)


@router.get("/articles")
async def admin_list_articles(
    session: AsyncSession = Depends(get_session),
    x_admin_token: str | None = Header(default=None),
    limit: int = 50,
) -> list[dict]:
    _check_token(x_admin_token)
    stmt = select(Article).order_by(desc(Article.published_at), desc(Article.scraped_at)).limit(min(max(limit, 1), 200))
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {
            "id": r.id,
            "category": r.category,
            "title": r.title,
            "summary": r.summary,
            "published_at": r.published_at,
            "source_url": r.source_url,
            "is_manual": bool(r.source_url.startswith("manual:")),
        }
        for r in rows
    ]


@router.post("/articles")
async def admin_create_article(
    req: AdminArticleCreate,
    session: AsyncSession = Depends(get_session),
    x_admin_token: str | None = Header(default=None),
) -> dict:
    _check_token(x_admin_token)

    now = datetime.utcnow()
    source_url = f"manual:{uuid4().hex}"
    art = Article(
        category=req.category,
        source_url=source_url,
        title=req.title,
        summary=req.summary,
        published_at=req.published_at or now,
        scraped_at=now,
        content_html=req.content_html,
        content_text=req.content_text,
    )
    session.add(art)
    await session.commit()
    await session.refresh(art)
    return {"id": art.id}


@router.patch("/articles/{article_id}")
async def admin_update_article(
    article_id: int,
    req: AdminArticleUpdate,
    session: AsyncSession = Depends(get_session),
    x_admin_token: str | None = Header(default=None),
) -> dict:
    _check_token(x_admin_token)
    art = await session.get(Article, article_id)
    if not art:
        raise HTTPException(status_code=404, detail="Article not found")
    if not art.source_url.startswith("manual:"):
        raise HTTPException(status_code=403, detail="Only manual articles can be edited in admin UI")

    if req.category is not None:
        art.category = req.category
    if req.title is not None:
        art.title = req.title
    if req.summary is not None:
        art.summary = req.summary
    if req.content_text is not None:
        art.content_text = req.content_text
    if req.content_html is not None:
        art.content_html = req.content_html
    if req.published_at is not None:
        art.published_at = req.published_at

    art.scraped_at = datetime.utcnow()
    await session.commit()
    return {"ok": True}


@router.delete("/articles/{article_id}")
async def admin_delete_article(
    article_id: int,
    session: AsyncSession = Depends(get_session),
    x_admin_token: str | None = Header(default=None),
) -> dict:
    _check_token(x_admin_token)
    art = await session.get(Article, article_id)
    if not art:
        raise HTTPException(status_code=404, detail="Article not found")
    if not art.source_url.startswith("manual:"):
        raise HTTPException(status_code=403, detail="Only manual articles can be deleted in admin UI")
    await session.delete(art)
    await session.commit()
    return {"ok": True}


@router.post("/chat/purge")
async def admin_purge_chat(
    session: AsyncSession = Depends(get_session),
    x_admin_token: str | None = Header(default=None),
) -> dict:
    _check_token(x_admin_token)
    r1 = await session.execute(delete(ChatMessage))
    r2 = await session.execute(delete(ChatSession))
    await session.commit()
    return {
        "ok": True,
        "deleted_messages": int(getattr(r1, "rowcount", 0) or 0),
        "deleted_sessions": int(getattr(r2, "rowcount", 0) or 0),
    }

