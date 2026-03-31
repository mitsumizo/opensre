"""Chat branch nodes - routing, LLM response, and tool execution."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import ToolNode

from app.agent.prompts import ROUTER_PROMPT, SYSTEM_PROMPT
from app.agent.state import AgentState, ChatMessage
from app.agent.tools.clients import get_llm
from app.agent.tools.tool_actions.github.github_mcp_actions import (
    get_github_file_contents,
    get_github_repository_tree,
    list_github_commits,
    search_github_code,
)
from app.agent.tools.tool_actions.sentry.sentry_actions import (
    get_sentry_issue_details,
    list_sentry_issue_events,
    search_sentry_issues,
)
from app.agent.tools.tool_actions.tracer.tracer_jobs import (
    get_failed_jobs,
    get_failed_tools,
)
from app.agent.tools.tool_actions.tracer.tracer_logs import get_error_logs
from app.agent.tools.tool_actions.tracer.tracer_metrics import (
    get_batch_statistics,
    get_host_metrics,
)
from app.agent.tools.tool_actions.tracer.tracer_runs import (
    fetch_failed_run,
    get_tracer_run,
    get_tracer_tasks,
)

# チャットに向けた関数群
_CHAT_FUNCTIONS: list[Callable[..., Any]] = [
    fetch_failed_run,
    get_tracer_run,
    get_tracer_tasks,
    get_failed_jobs,
    get_failed_tools,
    get_error_logs,
    get_batch_statistics,
    get_host_metrics,
    search_github_code,
    get_github_file_contents,
    get_github_repository_tree,
    list_github_commits,
    search_sentry_issues,
    get_sentry_issue_details,
    list_sentry_issue_events,
]

# チャットで使うTools
CHAT_TOOLS: list[StructuredTool] = [
    # TODO : 何をしてる？
    StructuredTool.from_function(fn, return_direct=False) for fn in _CHAT_FUNCTIONS
]

# LangChain type -> ChatMessage role mapping
_TYPE_TO_ROLE: dict[str, str] = {
    "human": "user",
    "ai": "assistant",
    "system": "system",
    "tool": "tool",
}


def _normalize_messages(msgs: list[Any]) -> list[ChatMessage]:
    """Normalize messages from LangChain format to plain ChatMessage dicts safely."""
    result: list[ChatMessage] = []
    for m in msgs:
        # LangChain BaseMessage instances
        if isinstance(m, BaseMessage):
            role = "assistant" if m.type == "ai" else _TYPE_TO_ROLE.get(m.type, "user")
            result.append({"role": role, "content": str(m.content)})
            continue

        # Dictionary formats
        if isinstance(m, dict):
            content = str(m.get("content", ""))
            if "role" in m:
                result.append({"role": str(m["role"]), "content": content})
                continue
            if "type" in m:
                role = "assistant" if m["type"] == "ai" else _TYPE_TO_ROLE.get(m["type"], "user")
                result.append({"role": role, "content": content})

    return result


# ── Chat LLM (LangChain ChatAnthropic for real-time streaming) ──────────

_chat_llm: ChatAnthropic | None = None
_chat_llm_with_tools: ChatAnthropic | None = None


def _get_chat_llm(*, with_tools: bool = False) -> ChatAnthropic:
    """Get a LangChain ChatAnthropic for chat nodes (supports streaming)."""
    global _chat_llm, _chat_llm_with_tools

    # 1. Instantiate the base model once
    if _chat_llm is None:
        from app.config import DEFAULT_MAX_TOKENS, DEFAULT_MODEL

        _chat_llm = ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL),
            max_tokens=DEFAULT_MAX_TOKENS,
            streaming=True,
        )

    # 2. Bind tools if requested
    if with_tools:
        if _chat_llm_with_tools is None:
            _chat_llm_with_tools = _chat_llm.bind_tools(CHAT_TOOLS)
        return _chat_llm_with_tools

    return _chat_llm


# ── Node functions ───────────────────────────────────────────────────────


def router_node(state: AgentState) -> dict[str, Any]:
    """Route chat messages by intent."""
    # メッセージを正規化
    msgs = _normalize_messages(list(state.get("messages", [])))
    if not msgs or msgs[-1].get("role") != "user":
        raise ValueError("Router node requires a recent user message to classify.")

    response = get_llm().invoke([
        {"role": "system", "content": ROUTER_PROMPT},
        {"role": "user", "content": str(msgs[-1].get("content", ""))},
    ])
    route = str(response.content).strip().lower()
    return {"route": route if route in ("tracer_data", "general") else "general"}


def chat_agent_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:  # noqa: ARG001
    """Chat agent with tools for Tracer data queries.

    Uses ChatAnthropic with bound tools. The LLM can make tool_calls
    which will be executed by the tool_executor node.
    """
    msgs = list(state.get("messages", []))

    has_system = any(
        (hasattr(m, "type") and m.type == "system")
        or (isinstance(m, dict) and m.get("type") == "system")
        for m in msgs
    )
    if not has_system:
        msgs = [SystemMessage(content=SYSTEM_PROMPT), *msgs]

    llm = _get_chat_llm(with_tools=True)
    response = llm.invoke(msgs)
    return {"messages": [response]}


def general_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:  # noqa: ARG001
    """Direct LLM response without tools for general questions."""
    msgs = list(state.get("messages", []))

    has_system = any(
        (hasattr(m, "type") and m.type == "system")
        or (isinstance(m, dict) and m.get("type") == "system")
        for m in msgs
    )
    if not has_system:
        msgs = [SystemMessage(content=SYSTEM_PROMPT), *msgs]

    llm = _get_chat_llm(with_tools=False)
    response = llm.invoke(msgs)
    return {"messages": [response]}


tool_executor_node = ToolNode(CHAT_TOOLS)
