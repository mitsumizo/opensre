"""Alert extraction and classification - single LLM call."""

import json
from typing import Any, cast

from app.agent.nodes.extract_alert.models import AlertDetails, AlertExtractionInput
from app.agent.output import debug_print
from app.agent.state import InvestigationState
from app.agent.prompts import EXTRACT_ALERT_PROMPT
from app.agent.tools.clients import get_llm


def extract_alert_details(state: InvestigationState) -> AlertDetails:
    """Single LLM call: classify noise + extract all routing fields simultaneously."""

    raw_alert = state.get("raw_alert")
    if raw_alert is None:
        raise RuntimeError("raw_alert is required for alert extraction")

    text = AlertExtractionInput(raw_alert=_format_raw_alert(raw_alert)).raw_alert

    prompt = EXTRACT_ALERT_PROMPT.format(text=text)
    llm = get_llm()
    try:
        details = cast(
            AlertDetails,
            llm.with_structured_output(AlertDetails)
               .with_config(run_name="LLM – Classify + extract alert")
               .invoke(prompt),
        )
        debug_print(
            f"Alert classified: {'NOISE' if details.is_noise else 'ALERT'} | "
            f"namespace={details.kube_namespace} | error={details.error_message}"
        )
        return details
    except Exception as err:
        debug_print(f"LLM alert extraction failed, using fallback: {err}")
        return _fallback_details(state, raw_alert)


def _fallback_details(state: InvestigationState, raw_alert: str | dict[str, Any]) -> AlertDetails:
    """Best-effort extraction without LLM when it fails."""
    alert_name = state.get("alert_name", "unknown")
    pipeline_name = state.get("pipeline_name", "unknown")
    severity = state.get("severity", "unknown")

    if isinstance(raw_alert, dict):
        labels = raw_alert.get("labels", {})
        annotations = raw_alert.get("annotations", {}) or raw_alert.get("commonAnnotations", {})
        alert_name = labels.get("alertname", alert_name)
        pipeline_name = (
            labels.get("pipeline")
            or annotations.get("pipeline_name")
            or raw_alert.get("pipeline_name")
            or pipeline_name
        )
        severity = labels.get("severity", severity)

    return AlertDetails(
        is_noise=False,
        alert_name=alert_name or "unknown",
        pipeline_name=pipeline_name or "unknown",
        severity=severity or "unknown",
    )


def _format_raw_alert(raw_alert: str | dict[str, Any]) -> str:
    if isinstance(raw_alert, str):
        return raw_alert
    # For Slack alerts, prefer the human-readable text field
    if isinstance(raw_alert, dict) and raw_alert.get("text"):
        return str(raw_alert["text"])
    return json.dumps(raw_alert, indent=2, sort_keys=True)
