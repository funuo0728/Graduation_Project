from __future__ import annotations

from typing import Any

from .settings import settings


def langchain_available() -> bool:
    try:
        import langchain_openai  # noqa: F401
        import langchain_core  # noqa: F401

        return True
    except Exception:
        return False


def call_openai_compatible_via_langchain(messages: list[dict[str, Any]]) -> str:
    """
    Call an OpenAI-compatible Chat Completions endpoint using LangChain.

    This uses the same env-driven config as the rest of the backend:
    - settings.effective_llm_base_url()
    - settings.effective_llm_api_key()
    - settings.effective_llm_model()
    """
    base_url = settings.effective_llm_base_url()
    model = settings.effective_llm_model()
    api_key = settings.effective_llm_api_key()

    if not base_url or not model:
        raise RuntimeError("LLM not configured")

    # Imports are inside function to keep backend usable without langchain deps.
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    lc_messages = []
    for m in messages:
        role = (m.get("role") or "").lower()
        content = m.get("content") or ""
        if role == "system":
            lc_messages.append(SystemMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))
        else:
            lc_messages.append(HumanMessage(content=content))

    llm = ChatOpenAI(
        model=model,
        temperature=0.2,
        base_url=base_url,
        api_key=api_key or "EMPTY",
    )

    resp = llm.invoke(lc_messages)
    return (getattr(resp, "content", None) or "").strip()

