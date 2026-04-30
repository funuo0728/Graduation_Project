from __future__ import annotations

import time
from dataclasses import dataclass
import re

import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Article
from .settings import settings
from .langchain_llm import call_openai_compatible_via_langchain, langchain_available


@dataclass(frozen=True)
class Agent:
    id: str
    name: str
    system_prompt: str


PUBLIC_AGENT = {"id": "assistant", "name": "学院智能助手"}


SPECIALISTS: dict[str, Agent] = {
    "retriever": Agent(
        id="retriever",
        name="检索智能体（RAG）",
        system_prompt=(
            "你是检索智能体，只负责从给定证据片段中挑选与问题最相关的要点。"
            "不要给办理建议，不要扩写常识，不要编造。输出要点+引用编号[1][2]。"
        ),
    ),
    "affairs": Agent(
        id="affairs",
        name="事务办理智能体",
        system_prompt=(
            "你是学院事务办理助手。你要把证据片段中的信息整理成可执行的办理步骤/材料清单/注意事项。"
            "硬性约束：证据片段没有出现的具体信息（材料、截止日期、地点、邮箱电话、表格文件名、部门名称）一律禁止输出。"
            "如果证据不足，请明确写“原文片段未包含该信息，请打开链接核对”。"
        ),
    ),
    "academic": Agent(
        id="academic",
        name="学业成长智能体",
        system_prompt=(
            "你是学业成长顾问，擅长学习规划、课程与能力建设建议、竞赛科研路径、风险提示。"
            "如果涉及具体制度/通知细节，必须引用证据片段；证据不足就说明不足并给核对路径。"
            "输出结构固定为：目标-现状-方案-风险-下一步。"
        ),
    ),
    "verifier": Agent(
        id="verifier",
        name="校验智能体",
        system_prompt=(
            "你是校验智能体，检查回答是否满足：\n"
            "1) 关键事实是否有[编号]引用\n"
            "2) 是否出现证据片段里没有的具体信息（材料/时间地点/电话邮箱/表格名）\n"
            "如果发现问题，用简短清单指出问题，并给出如何修改的建议。不要重写长答案。"
        ),
    ),
}

def _chunk_text(text: str, chunk_size: int = 650, overlap: int = 120) -> list[str]:
    t = " ".join(text.split())
    if not t:
        return []
    if len(t) <= chunk_size:
        return [t]
    out: list[str] = []
    i = 0
    while i < len(t):
        out.append(t[i : i + chunk_size])
        i += max(1, chunk_size - overlap)
    return out


_CACHE: dict = {"built_at": 0.0, "rows_sig": None, "vectorizer": None, "X": None, "chunks": None}


async def retrieve(session: AsyncSession, query: str, top_k: int = 6) -> list[dict]:
    """
    Lightweight RAG retriever:
    - chunk article content into passages
    - run TF-IDF over passages
    - return top passages with article metadata
    """
    stmt = (
        select(Article)
        .where(Article.content_text.is_not(None))
        .order_by(desc(Article.published_at), desc(Article.scraped_at))
        .limit(500)
    )
    rows = (await session.execute(stmt)).scalars().all()
    if not rows:
        return []

    # Cache index for a short period to avoid rebuilding for every chat
    now = time.time()
    rows_sig = (len(rows), rows[0].id, rows[-1].id)
    cache_ok = (
        _CACHE["vectorizer"] is not None
        and _CACHE["X"] is not None
        and _CACHE["chunks"] is not None
        and _CACHE["rows_sig"] == rows_sig
        and (now - float(_CACHE["built_at"])) < 180
    )

    if not cache_ok:
        chunks: list[dict] = []
        for r in rows:
            for ch in _chunk_text(r.content_text or ""):
                if len(ch) < 80:
                    continue
                chunks.append({"article_id": r.id, "title": r.title, "source_url": r.source_url, "text": ch})

        if not chunks:
            return []

        texts = [c["text"] for c in chunks]
        # Chinese-friendly TF-IDF: character n-grams (works for zh/en mixed).
        vectorizer = TfidfVectorizer(
            analyzer="char",
            ngram_range=(2, 4),
            max_features=30000,
            min_df=1,
        )
        X = vectorizer.fit_transform(texts)
        _CACHE.update({"built_at": now, "rows_sig": rows_sig, "vectorizer": vectorizer, "X": X, "chunks": chunks})

    vectorizer: TfidfVectorizer = _CACHE["vectorizer"]
    X = _CACHE["X"]
    chunks = _CACHE["chunks"]

    qv = vectorizer.transform([query])
    sims = (X @ qv.T).toarray().ravel()
    ranked = sorted(range(len(chunks)), key=lambda i: sims[i], reverse=True)

    out: list[dict] = []
    for i in ranked[: max(top_k * 2, 10)]:
        score = float(sims[i])
        if score <= 0:
            continue
        c = chunks[i]
        out.append(
            {
                "article_id": c["article_id"],
                "title": c["title"],
                "source_url": c["source_url"],
                "score": score,
                "snippet": c["text"][:520],
            }
        )
        if len(out) >= top_k:
            break
    return out


def _call_openai_compatible(messages: list[dict]) -> str:
    # Prefer LangChain implementation when available (thesis: LangChain integration).
    if langchain_available():
        return call_openai_compatible_via_langchain(messages)

    base_url = settings.effective_llm_base_url()
    model = settings.effective_llm_model()
    api_key = settings.effective_llm_api_key()

    if not base_url or not model:
        raise RuntimeError("LLM not configured")

    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }
    r = requests.post(url, json=payload, headers=headers, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]


def format_fallback(user_message: str, citations: list[dict]) -> str:
    lines = ["（离线模式）学院智能助手：我先基于门户已抓取内容给你一个可执行答复。", ""]
    if citations:
        lines.append("我检索到可能相关的通知/新闻：")
        for c in citations[:5]:
            score = c.get("score", 0.0)
            lines.append(f"- {c['title']}（相似度 {score:.3f}）")
            lines.append(f"  原文：{c['source_url']}")
        lines.append("")
    lines.append("你的问题：")
    lines.append(user_message)
    lines.append("")
    lines.append("建议：")
    lines.append("- 如果你要我给出更精确的办理流程/材料清单，请补充：年级、事项类型、截止日期、你目前遇到的卡点。")
    lines.append("- 以学院最新通知为准；需要时我可以把相关通知原文要点再帮你提炼成清单。")
    return "\n".join(lines)


def list_public_agents() -> list[dict]:
    return [PUBLIC_AGENT]


def _format_context(cites: list[dict]) -> str:
    # Do NOT include external URLs in context (local demo / avoid exposing sources).
    return "\n\n".join(
        [
            f"[{i+1}] 标题：{c['title']}\n文章ID：{c['article_id']}\n证据片段：{c['snippet']}"
            for i, c in enumerate(cites)
        ]
    )


_URL_RE = re.compile(r"https?://\\S+")


def _strip_urls(text: str) -> str:
    # Remove any accidental URLs produced by the model.
    return _URL_RE.sub("", text).replace("（）", "（略）").strip()


def _route_intent(message: str) -> str:
    m = message.lower()
    affairs_kw = ["通知", "公示", "公告", "奖学金", "资助", "申请", "材料", "截止", "流程", "办理", "提交", "证明", "复试", "推免"]
    academic_kw = ["课程", "学习", "规划", "绩点", "选课", "竞赛", "科研", "论文", "保研", "考研", "实习", "项目", "方向"]
    if any(k in message for k in affairs_kw):
        return "affairs"
    if any(k in message for k in academic_kw):
        return "academic"
    return "affairs"


async def supervisor_chat(session: AsyncSession, message: str) -> tuple[str, list[dict], list[dict]]:
    """
    Multi-agent orchestration:
    - retriever: retrieve evidence
    - specialist (affairs/academic): draft answer
    - verifier: check answer against evidence
    - supervisor: output final answer (currently: use specialist answer, optionally patched by verifier suggestions)
    """
    trace: list[dict] = []

    cites = await retrieve(session, message, top_k=6)
    trace.append({"agent": "retriever", "name": SPECIALISTS["retriever"].name, "output": {"citations": cites}})

    if not cites:
        reply = (
            "我在当前已入库内容中没有检索到与问题直接相关的通知/新闻片段。\n\n"
            "你可以这样做：\n"
            "- 去“内容管理”里手动发布相关公告/新闻后再问我。\n"
            "- 换更具体的关键词再问（例如：奖学金名称/年级/事项全称/通知标题中的关键字）。\n"
            "- 也可以把你看到的通知标题或链接发给我，我可以按原文帮你提炼要点。"
        )
        return reply, [], trace

    # Offline mode: simple template using citations
    if not (settings.effective_llm_base_url() and settings.effective_llm_model()):
        return format_fallback(message, cites), cites, trace

    intent = _route_intent(message)
    specialist = SPECIALISTS[intent]
    context = _format_context(cites)

    specialist_messages = [
        {"role": "system", "content": specialist.system_prompt},
        {
            "role": "user",
            "content": (
                f"用户问题：{message}\n\n"
                "硬性约束：你只能基于【证据片段】回答。证据片段没有出现的具体信息（材料、截止日期、地点、邮箱电话、表格文件名、部门名称）一律禁止输出。\n"
                "如果证据不足，请直接写“原文片段未包含该信息，请打开链接核对”。不要用常识补全。\n\n"
                f"证据片段：\n{context}\n\n"
                "输出要求：\n"
                "- 尽量给出可执行清单/步骤\n"
                "- 需要引用时在句末标注[1][2]...\n"
                "- 不要输出任何URL链接；如需指引读者查看，请写“可在本站对应文章中查看（见引用编号对应的文章ID）”。\n"
            ),
        },
    ]
    draft = _strip_urls(_call_openai_compatible(specialist_messages))
    trace.append({"agent": specialist.id, "name": specialist.name, "output": {"draft": draft}})

    # Verifier
    verifier = SPECIALISTS["verifier"]
    verifier_messages = [
        {"role": "system", "content": verifier.system_prompt},
        {
            "role": "user",
            "content": (
                f"用户问题：{message}\n\n"
                f"证据片段：\n{context}\n\n"
                f"待校验回答：\n{draft}\n\n"
                "请输出：\n"
                "- issues: 发现的问题（列表）\n"
                "- fix: 建议如何修改（列表）\n"
                "用简短中文即可。"
            ),
        },
    ]
    verify_note = _strip_urls(_call_openai_compatible(verifier_messages))
    trace.append({"agent": "verifier", "name": verifier.name, "output": {"note": verify_note}})

    # Supervisor output (keep draft; user can see verifier note in trace panel)
    final = draft
    return final, cites, trace

