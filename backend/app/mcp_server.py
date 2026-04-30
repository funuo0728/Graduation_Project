from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from uuid import uuid4

from mcp.server.fastmcp import FastMCP
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from .agents import supervisor_chat
from .db import SessionLocal
from .models import Article, ChatMessage, ChatSession
from .settings import settings


@asynccontextmanager
async def _lifespan(_: FastMCP) -> AsyncIterator[dict]:
    # No global init required; DB engine/sessionmaker is in app.db.
    yield {}


mcp = FastMCP(
    "IEE-Portal-MCP",
    instructions=(
        "为学院门户提供 MCP 工具：文章检索/文章读取/智能问答/会话清理/（可选）内容发布。"
        "适合论文演示：外部智能体可通过 MCP 统一调用门户能力。"
    ),
    lifespan=_lifespan,
    json_response=True,
)


async def _db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as s:
        yield s


def _dt(v: datetime | None) -> str | None:
    return v.isoformat(timespec="seconds") if v else None


@mcp.tool()
async def search_articles(query: str, category: str | None = None, limit: int = 5) -> dict[str, Any]:
    """
    Search articles by keyword (title/content_text).
    Returns lightweight metadata; does NOT expose external source URLs.
    """
    limit = min(max(int(limit), 1), 20)
    async for session in _db():
        stmt = select(Article).order_by(desc(Article.published_at), desc(Article.scraped_at)).limit(800)
        if category:
            stmt = stmt.where(Article.category == category)
        rows = (await session.execute(stmt)).scalars().all()

        q = (query or "").strip()
        if not q:
            return {"items": []}

        # Simple scoring: count occurrences in title/content_text (keeps dependencies minimal for MCP).
        items: list[dict[str, Any]] = []
        for r in rows:
            t = r.title or ""
            c = r.content_text or ""
            score = (t.count(q) * 3) + c.count(q)
            if score <= 0:
                continue
            items.append(
                {
                    "article_id": r.id,
                    "category": r.category,
                    "title": r.title,
                    "published_at": _dt(r.published_at),
                    "score": score,
                }
            )

        items.sort(key=lambda x: x["score"], reverse=True)
        return {"items": items[:limit]}


@mcp.tool()
async def get_article(article_id: int) -> dict[str, Any]:
    """Get article detail by ID (content_html/content_text)."""
    async for session in _db():
        art = await session.get(Article, int(article_id))
        if not art:
            return {"found": False}
        return {
            "found": True,
            "id": art.id,
            "category": art.category,
            "title": art.title,
            "summary": art.summary,
            "published_at": _dt(art.published_at),
            "content_text": art.content_text,
            "content_html": art.content_html,
        }


@mcp.tool()
async def assistant_chat(message: str, session_key: str | None = None) -> dict[str, Any]:
    """
    Talk to the portal assistant (multi-agent orchestration in backend).
    Returns: reply + citations + trace + session_key.
    """
    session_key = (session_key or "mcp").strip()[:64] or "mcp"
    async for session in _db():
        reply, cites, trace = await supervisor_chat(session=session, message=message)

        # Persist minimal history (same schema as HTTP API).
        chat_sess = (
            await session.execute(select(ChatSession).where(ChatSession.session_key == session_key))
        ).scalars().first()
        if not chat_sess:
            chat_sess = ChatSession(session_key=session_key, created_at=datetime.utcnow(), last_active_at=datetime.utcnow())
            session.add(chat_sess)
            await session.flush()
        else:
            chat_sess.last_active_at = datetime.utcnow()

        session.add(
            ChatMessage(
                chat_session_id=chat_sess.id,
                agent_id="assistant",
                role="user",
                content=message,
                citations=None,
            )
        )
        session.add(
            ChatMessage(
                chat_session_id=chat_sess.id,
                agent_id="assistant",
                role="agent",
                content=reply,
                citations={"citations": cites, "trace": trace},
            )
        )
        await session.commit()

        return {"session_key": session_key, "reply": reply, "citations": cites, "trace": trace}


@mcp.tool()
async def purge_all_chats() -> dict[str, Any]:
    """Purge all chat sessions/messages (demo/local use, no auth)."""
    async for session in _db():
        r1 = await session.execute(delete(ChatMessage))
        r2 = await session.execute(delete(ChatSession))
        await session.commit()
        return {
            "ok": True,
            "deleted_messages": int(getattr(r1, "rowcount", 0) or 0),
            "deleted_sessions": int(getattr(r2, "rowcount", 0) or 0),
        }


@mcp.tool()
async def create_manual_article(
    admin_token: str,
    category: str,
    title: str,
    content_text: str | None = None,
    content_html: str | None = None,
    summary: str | None = None,
) -> dict[str, Any]:
    """
    Create a manual article (requires admin token).
    This mirrors the portal's admin capability but via MCP.
    """
    if not settings.admin_token:
        return {"ok": False, "error": "ADMIN_TOKEN is not configured on server"}
    if not admin_token or admin_token != settings.admin_token:
        return {"ok": False, "error": "Invalid admin token"}

    now = datetime.utcnow()
    source_url = f"manual:{uuid4().hex}"
    art = Article(
        category=category,
        source_url=source_url,
        title=title,
        summary=summary,
        published_at=now,
        scraped_at=now,
        content_html=content_html,
        content_text=content_text,
    )
    async for session in _db():
        session.add(art)
        await session.commit()
        await session.refresh(art)
        return {"ok": True, "id": art.id}


def main() -> None:
    # Default: stdio transport (works well with desktop MCP clients).
    mcp.run()


if __name__ == "__main__":
    main()

