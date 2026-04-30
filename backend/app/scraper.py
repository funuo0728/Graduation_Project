from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser


IEE_BASE = "https://iee.zjgsu.edu.cn/"
DETAIL_RE = re.compile(r"\?news/\d+\.html$")


@dataclass(frozen=True)
class ListItem:
    source_url: str
    title: str
    published_at: datetime | None
    summary: str | None


def _clean_text(s: str) -> str:
    return re.sub(r"\\s+", " ", s).strip()


def fetch_list_items(list_url: str) -> list[ListItem]:
    r = requests.get(list_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")

    items: list[ListItem] = []
    for a in soup.find_all("a", href=True):
        href: str = a["href"]
        full = urljoin(list_url, href)
        if not DETAIL_RE.search(full):
            continue

        title = _clean_text(a.get_text(" ", strip=True))
        if not title:
            continue

        # best-effort date detection near the anchor
        published_at: datetime | None = None
        summary: str | None = None

        container = a
        for _ in range(4):
            if container.parent is None:
                break
            container = container.parent

        block_text = _clean_text(container.get_text(" ", strip=True))
        # Try to capture YYYY-MM-DD patterns
        m = re.search(r"(20\\d{2}[-/.]\\d{1,2}[-/.]\\d{1,2})", block_text)
        if m:
            try:
                published_at = date_parser.parse(m.group(1))
            except Exception:
                published_at = None

        # Summary: remove title from block text
        if block_text and title in block_text:
            rest = _clean_text(block_text.replace(title, "", 1))
            summary = rest[:240] if rest else None

        items.append(
            ListItem(
                source_url=full,
                title=title[:512],
                published_at=published_at,
                summary=summary,
            )
        )

    # De-dup by URL, keep first occurrence
    seen: set[str] = set()
    out: list[ListItem] = []
    for it in items:
        if it.source_url in seen:
            continue
        seen.add(it.source_url)
        out.append(it)
    return out


def fetch_article_detail(detail_url: str) -> tuple[str, str, str]:
    r = requests.get(detail_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")

    # Try common title selectors
    title = None
    for sel in ["h1", ".title", ".article-title", ".news-title"]:
        el = soup.select_one(sel)
        if el and _clean_text(el.get_text(" ", strip=True)):
            title = _clean_text(el.get_text(" ", strip=True))
            break
    if not title:
        title = _clean_text(soup.title.get_text(" ", strip=True)) if soup.title else detail_url

    # Find the largest text block as content (excluding header/footer)
    candidates = []
    for el in soup.find_all(["div", "article", "section"], recursive=True):
        txt = _clean_text(el.get_text(" ", strip=True))
        if len(txt) < 200:
            continue
        # discard navigation-ish blocks
        if any(k in txt for k in ["©", "ICP备", "浙公网安备", "扫码关注公众号"]):
            continue
        candidates.append((len(txt), el))

    content_el = max(candidates, key=lambda x: x[0])[1] if candidates else soup.body
    content_html = str(content_el) if content_el else ""
    content_text = _clean_text(content_el.get_text(" ", strip=True)) if content_el else ""

    return title[:512], content_html, content_text

