import asyncio

from sqlalchemy import select

from app.agents import supervisor_chat
from app.db import SessionLocal
from app.models import Article
from app.mcp_server import mcp


async def main() -> None:
    tools = await mcp.list_tools()
    print("mcp_tools:", [t.name for t in tools])

    async with SessionLocal() as s:
        has_article = bool((await s.execute(select(Article.id).limit(1))).first())
        print("has_article:", has_article)
        if has_article:
            reply, cites, trace = await supervisor_chat(s, "请简要概括最新一条通知/新闻的主题。")
            print("reply_len:", len(reply))
            print("citations:", len(cites))
            print("trace_steps:", len(trace))


if __name__ == "__main__":
    asyncio.run(main())

