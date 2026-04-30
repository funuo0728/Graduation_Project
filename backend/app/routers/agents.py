from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..agents import list_public_agents, supervisor_chat
from ..db import get_session
from ..models import ChatMessage, ChatSession
from ..schemas import ChatHistoryItem, ChatRequest, ChatResponse

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("")
async def list_agents() -> list[dict]:
    return list_public_agents()


@router.post("/chat", response_model=ChatResponse)
async def agent_chat(req: ChatRequest, session: AsyncSession = Depends(get_session)) -> ChatResponse:
    # Single public entrypoint: assistant
    agent_id = req.agent_id or "assistant"
    if agent_id != "assistant":
        raise HTTPException(status_code=404, detail="Unknown agent")

    reply, cites, trace = await supervisor_chat(session=session, message=req.message)

    # Persist chat
    session_key = req.session_key or "default"
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
            agent_id=agent_id,
            role="user",
            content=req.message,
            citations=None,
        )
    )
    session.add(
        ChatMessage(
            chat_session_id=chat_sess.id,
            agent_id=agent_id,
            role="agent",
            content=reply,
            citations={"citations": cites, "trace": trace},
        )
    )
    await session.commit()

    return ChatResponse(agent_id=agent_id, reply=reply, citations=cites, trace=trace, session_key=session_key)


@router.get("/history", response_model=list[ChatHistoryItem])
async def chat_history(
    session_key: str = Query(default="default", min_length=1, max_length=64),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> list[ChatHistoryItem]:
    sess = (await session.execute(select(ChatSession).where(ChatSession.session_key == session_key))).scalars().first()
    if not sess:
        return []
    rows = (
        await session.execute(
            select(ChatMessage)
            .where(ChatMessage.chat_session_id == sess.id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
    ).scalars().all()
    return [ChatHistoryItem(role=r.role, content=r.content, created_at=r.created_at) for r in rows]


@router.post("/clear")
async def clear_chat(
    session_key: str = Query(default="default", min_length=1, max_length=64),
    delete_session: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Clear persisted chat history for a session.
    This is meant for local/demo use (no auth).
    """
    sess = (await session.execute(select(ChatSession).where(ChatSession.session_key == session_key))).scalars().first()
    if not sess:
        return {"ok": True, "cleared": 0}

    res = await session.execute(delete(ChatMessage).where(ChatMessage.chat_session_id == sess.id))
    cleared = int(getattr(res, "rowcount", 0) or 0)
    if delete_session:
        await session.delete(sess)
    await session.commit()
    return {"ok": True, "cleared": cleared, "deleted_session": delete_session}


@router.post("/purge")
async def purge_all_chats(session: AsyncSession = Depends(get_session)) -> dict:
    """
    Purge all chat sessions/messages (demo/local use).
    No auth by design.
    """
    r1 = await session.execute(delete(ChatMessage))
    r2 = await session.execute(delete(ChatSession))
    await session.commit()
    return {
        "ok": True,
        "deleted_messages": int(getattr(r1, "rowcount", 0) or 0),
        "deleted_sessions": int(getattr(r2, "rowcount", 0) or 0),
    }

