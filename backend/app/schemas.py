from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ArticleOut(BaseModel):
    id: int
    category: str
    source_url: str
    title: str
    summary: str | None = None
    published_at: datetime | None = None
    scraped_at: datetime


class ArticleDetailOut(ArticleOut):
    content_html: str | None = None
    content_text: str | None = None


class ScrapeRequest(BaseModel):
    categories: list[str] | None = None
    max_pages: int = Field(default=2, ge=1, le=30)


class ChatRequest(BaseModel):
    agent_id: str | None = None
    message: str
    session_key: str | None = None


class ChatResponse(BaseModel):
    agent_id: str
    reply: str
    citations: list[dict] = Field(default_factory=list)
    session_key: str | None = None
    trace: list[dict] = Field(default_factory=list)


class ChatHistoryItem(BaseModel):
    role: str
    content: str
    created_at: datetime


class AdminArticleCreate(BaseModel):
    category: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=512)
    summary: str | None = Field(default=None, max_length=1000)
    content_text: str | None = None
    content_html: str | None = None
    published_at: datetime | None = None


class AdminArticleUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=1, max_length=64)
    title: str | None = Field(default=None, min_length=1, max_length=512)
    summary: str | None = Field(default=None, max_length=1000)
    content_text: str | None = None
    content_html: str | None = None
    published_at: datetime | None = None

