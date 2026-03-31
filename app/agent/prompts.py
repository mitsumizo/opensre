"""Prompt templates for the chat agent."""

SYSTEM_PROMPT = """You are a pipeline debugging assistant for Tracer.
You help users understand and debug their bioinformatics pipelines.

You have access to tools that can query Tracer APIs for pipeline runs, tasks, logs,
metrics, and job information. Use these tools when users ask about their pipelines.

For general questions about bioinformatics or pipeline best practices, answer directly
without using tools.

Always respond in clear markdown."""

ROUTER_PROMPT = """Classify the user message:
- "tracer_data" if asking about pipelines, runs, logs, metrics, failures, or debugging
- "general" for general questions, greetings, or best practices

Respond with ONLY: tracer_data or general"""

EXTRACT_ALERT_PROMPT = """Classify and extract fields from this alert message.

is_noise=true ONLY for: casual chat, greetings, trivial messages ("ok", "thanks"), or replies to existing investigation reports.
is_noise=false (default) for: any alert, error, failure, incident, warning, monitoring notification.
When in doubt, set is_noise=false.

Extract these fields from the message text:
- alert_name: The name of the alert (e.g. "Pipeline Error in Logs")
- pipeline_name: The affected pipeline/table/service name
- severity: critical/high/warning/info
- alert_source: Which platform fired this alert. Set to "grafana" if the URL/text mentions grafana.net, Grafana alerting, or grafana_folder. Set to "datadog" if it mentions datadoghq.com or Datadog monitors. Set to "cloudwatch" if it mentions AWS CloudWatch alarms. Set to "eks" if it mentions EKS, CrashLoopBackOff, OOMKilled, Kubernetes pods, or kube_namespace. Leave null if truly unknown.
- kube_namespace: Kubernetes namespace if mentioned (e.g. "tracer-test" from "kube_namespace:tracer-test")
- cloudwatch_log_group: AWS CloudWatch log group if mentioned (e.g. "/aws/ecs/my-service")
- error_message: The actual error line from the alert (e.g. "PIPELINE_ERROR: Schema validation failed: Missing fields ['customer_id']")
- log_query: The log search query from the alert body — usually the "Search logs:" or "monitored query" line (e.g. "OOMKilled kube_namespace:tracer-cl" or "PIPELINE_ERROR kube_namespace:tracer-test"). Leave null if not present.
- eks_cluster: EKS cluster name if mentioned (e.g. "tracer-eks-test" from eks_cluster or cluster annotation)
- pod_name: Kubernetes pod name if mentioned (e.g. "etl-worker-7d9f8b-xkp2q")
- deployment: Kubernetes deployment name if mentioned (e.g. "etl-worker")

Message:
{text}
"""
