"""Unified agent pipeline - wires nodes and edges into a LangGraph."""

from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agent.nodes import (
    node_diagnose_root_cause,
    node_extract_alert,
    node_plan_actions,
    node_publish_findings,
    node_resolve_integrations,
)
from app.agent.nodes.auth import inject_auth_node
from app.agent.nodes.chat import (
    chat_agent_node,
    general_node,
    router_node,
    tool_executor_node,
)
from app.agent.nodes.investigate.node import node_investigate
from app.agent.routing import (
    route_after_extract,
    route_by_mode,
    route_chat,
    route_investigation_loop,
    should_call_tools,
)
from app.agent.runners import SimpleAgent
from app.agent.state import AgentState
from app.agent.constants import NodeName, RouteName


def build_graph(config: None = None) -> CompiledStateGraph:
    """Build and compile the LangGraph agent."""
    _ = config
    graph = StateGraph(AgentState)

    # ── 1. エントリーポイント（入り口） ──
    graph.add_node(NodeName.INJECT_AUTH, inject_auth_node)
    graph.set_entry_point(NodeName.INJECT_AUTH)
    graph.add_conditional_edges(
        NodeName.INJECT_AUTH, 
        route_by_mode, 
        {RouteName.CHAT: NodeName.ROUTER, RouteName.INVESTIGATION: NodeName.EXTRACT_ALERT}
    )

    # ── 2. チャットボット機能のフロー（Chat Agent） ──
    graph.add_node(NodeName.ROUTER, router_node)
    graph.add_node(NodeName.CHAT_AGENT, chat_agent_node)  # type: ignore[arg-type]
    graph.add_node(NodeName.GENERAL, general_node)  # type: ignore[arg-type]
    graph.add_node(NodeName.TOOL_EXECUTOR, tool_executor_node)

    graph.add_conditional_edges(
        NodeName.ROUTER, 
        route_chat, 
        {RouteName.TRACER_DATA: NodeName.CHAT_AGENT, RouteName.GENERAL: NodeName.GENERAL}
    )
    graph.add_conditional_edges(
        NodeName.CHAT_AGENT, 
        should_call_tools, 
        {RouteName.CALL_TOOLS: NodeName.TOOL_EXECUTOR, RouteName.DONE: END}
    )
    graph.add_edge(NodeName.TOOL_EXECUTOR, NodeName.CHAT_AGENT)
    graph.add_edge(NodeName.GENERAL, END)

    # ── 3. 自動調査機能のフロー（RCA Investigation） ──
    # ログを構造化
    graph.add_node(NodeName.EXTRACT_ALERT, node_extract_alert)
    # 必要なキーを取得
    graph.add_node(NodeName.RESOLVE_INTEGRATIONS, node_resolve_integrations)
    # 行動のプランニング
    graph.add_node(NodeName.PLAN_ACTIONS, node_plan_actions)
    graph.add_node(NodeName.INVESTIGATE, node_investigate)
    graph.add_node(NodeName.DIAGNOSE, node_diagnose_root_cause)
    graph.add_node(NodeName.PUBLISH, node_publish_findings)

    graph.add_conditional_edges(
        NodeName.EXTRACT_ALERT, 
        route_after_extract, 
        {RouteName.END: END, RouteName.INVESTIGATE: NodeName.RESOLVE_INTEGRATIONS}
    )
    graph.add_edge(NodeName.RESOLVE_INTEGRATIONS, NodeName.PLAN_ACTIONS)
    graph.add_edge(NodeName.PLAN_ACTIONS, NodeName.INVESTIGATE)
    graph.add_edge(NodeName.INVESTIGATE, NodeName.DIAGNOSE)
    graph.add_conditional_edges(
        NodeName.DIAGNOSE, 
        route_investigation_loop, 
        {RouteName.INVESTIGATE: NodeName.PLAN_ACTIONS, RouteName.PUBLISH: NodeName.PUBLISH}
    )
    graph.add_edge(NodeName.PUBLISH, END)

    return graph.compile()


agent = SimpleAgent()
graph = build_graph()
