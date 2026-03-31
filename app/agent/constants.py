"""Constants for the LangGraph agent nodes and routes."""

from enum import Enum


class NodeName(str, Enum):
    """Names of the nodes in the LangGraph."""

    INJECT_AUTH = "inject_auth"
    ROUTER = "router"
    CHAT_AGENT = "chat_agent"
    GENERAL = "general"
    TOOL_EXECUTOR = "tool_executor"
    EXTRACT_ALERT = "extract_alert"
    RESOLVE_INTEGRATIONS = "resolve_integrations"
    PLAN_ACTIONS = "plan_actions"
    INVESTIGATE = "investigate"
    DIAGNOSE = "diagnose"
    PUBLISH = "publish"


class RouteName(str, Enum):
    """Keywords returned by routing functions."""

    CHAT = "chat"
    INVESTIGATION = "investigation"
    TRACER_DATA = "tracer_data"
    GENERAL = "general"
    CALL_TOOLS = "call_tools"
    DONE = "done"
    END = "end"
    INVESTIGATE = "investigate"
    PUBLISH = "publish"
