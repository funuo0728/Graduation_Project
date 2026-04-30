from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import engine
from .models import Base
from .routers import admin, agents, articles, scrape
from .settings import settings
from .langchain_llm import langchain_available


app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(articles.router)
app.include_router(scrape.router)
app.include_router(agents.router)
app.include_router(admin.router)


@app.on_event("startup")
async def _startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/api/health")
async def health() -> dict:
    llm_base_url = settings.effective_llm_base_url()
    llm_model = settings.effective_llm_model()
    llm_enabled = bool(llm_base_url and llm_model)

    provider = "offline"
    if settings.llm_base_url:
        provider = "openai-compatible"
    elif settings.dashscope_api_key:
        provider = "dashscope-compatible"

    tools: list[str] = []
    try:
        from .mcp_server import mcp

        tool_objs = await mcp.list_tools()
        tools = [t.name for t in tool_objs]
    except Exception:
        tools = []

    return {
        "ok": True,
        "app": settings.app_name,
        "llm": {"enabled": llm_enabled, "provider": provider, "model": llm_model},
        "langchain": {"enabled": bool(langchain_available())},
        "mcp": {"tools": tools},
    }

