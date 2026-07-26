"""
Application-level Prometheus metrics.

Exposes key counters / gauges for the AI agent so Prometheus can scrape `/metrics`.
"""

from prometheus_client import Counter, Gauge, Histogram, Info

# ── Request / message counters ────────────────────────────────────────────────

messages_received_total = Counter(
    "aiagent_messages_received_total",
    "Total messages received by channel",
    ["channel"],
)

messages_sent_total = Counter(
    "aiagent_messages_sent_total",
    "Total messages sent by channel",
    ["channel"],
)

ai_requests_total = Counter(
    "aiagent_ai_requests_total",
    "Total AI inference requests",
    ["model", "status"],
)

ai_request_duration_seconds = Histogram(
    "aiagent_ai_request_duration_seconds",
    "AI inference latency",
    ["model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

# ── Kubernetes / AIOps ────────────────────────────────────────────────────────

k8s_watchloop_events_total = Counter(
    "aiagent_k8s_watchloop_events_total",
    "Total K8s watch-loop event detections",
    ["event_type", "severity"],
)

aiops_playbooks_executed_total = Counter(
    "aiagent_aiops_playbooks_executed_total",
    "Total AIOps playbooks executed",
    ["playbook_id", "status"],
)

aiops_approvals_pending = Gauge(
    "aiagent_aiops_approvals_pending",
    "Number of pending human-in-the-loop approvals",
)

aiops_active_incidents = Gauge(
    "aiagent_aiops_active_incidents",
    "Number of active (open) incidents in the database",
)

# ── API Backend Monitoring ────────────────────────────────────────────────────

api_backend_up = Gauge(
    "aiagent_api_backend_up",
    "API backend health status (1 = up, 0 = down)",
    ["endpoint"],
)

api_backend_latency_seconds = Histogram(
    "aiagent_api_backend_latency_seconds",
    "API backend response latency",
    ["endpoint"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0],
)

api_backend_errors_total = Counter(
    "aiagent_api_backend_errors_total",
    "Total API backend errors",
    ["endpoint", "status_code"],
)

api_backend_checks_total = Counter(
    "aiagent_api_backend_checks_total",
    "Total API backend health checks performed",
    ["endpoint", "status"],
)

# ── MCP ───────────────────────────────────────────────────────────────────────

mcp_tool_calls_total = Counter(
    "aiagent_mcp_tool_calls_total",
    "Total MCP tool invocations",
    ["server", "tool", "status"],
)

# ── Granular AIOps metrics ────────────────────────────────────────────────────

aiops_watchloop_check_duration_seconds = Histogram(
    "aiagent_aiops_watchloop_check_duration_seconds",
    "Duration of individual watchloop checks",
    ["check_type"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

aiops_rca_analysis_duration_seconds = Histogram(
    "aiagent_aiops_rca_analysis_duration_seconds",
    "End-to-end RCA analysis latency",
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

aiops_rca_fallback_total = Counter(
    "aiagent_aiops_rca_fallback_total",
    "Number of times RCA fell back to keyword-based analysis (AI timeout or error)",
)

aiops_playbook_step_duration_seconds = Histogram(
    "aiagent_aiops_playbook_step_duration_seconds",
    "Duration of individual playbook step executions",
    ["playbook_id", "step"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
)

aiops_approval_total = Counter(
    "aiagent_aiops_approval_total",
    "Approval lifecycle events",
    ["outcome"],  # requested | approved | rejected | expired | failed
)

# ── Webhooks ──────────────────────────────────────────────────────────────────

webhook_requests_total = Counter(
    "aiagent_webhook_requests_total",
    "Total webhook POST requests",
    ["channel", "status"],
)

# ── Build info ────────────────────────────────────────────────────────────────

build_info = Info(
    "aiagent_build",
    "Build / version metadata for the AI agent",
)

build_info.info(
    {
        "version": "0.1.0",
        "environment": "production",
    }
)

# ── A2A (Agent-to-Agent) Metrics ──────────────────────────────────────────────

a2a_agents_registered = Gauge(
    "aiagent_a2a_agents_registered",
    "Total number of registered A2A agents",
)

a2a_agents_online = Gauge(
    "aiagent_a2a_agents_online",
    "Number of online A2A agents",
)

a2a_tasks_delegated_total = Counter(
    "aiagent_a2a_tasks_delegated_total",
    "Total tasks delegated to other agents",
    ["to_agent", "capability", "status"],
)

a2a_tasks_received_total = Counter(
    "aiagent_a2a_tasks_received_total",
    "Total tasks received from other agents",
    ["from_agent", "capability", "status"],
)

a2a_task_duration_seconds = Histogram(
    "aiagent_a2a_task_duration_seconds",
    "A2A task execution duration",
    ["capability", "status"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)

a2a_webhooks_sent_total = Counter(
    "aiagent_a2a_webhooks_sent_total",
    "Total A2A webhooks sent",
    ["status"],
)

a2a_webhooks_received_total = Counter(
    "aiagent_a2a_webhooks_received_total",
    "Total A2A webhooks received",
    ["task_status"],
)

a2a_auth_failures_total = Counter(
    "aiagent_a2a_auth_failures_total",
    "Total A2A authentication failures",
    ["reason"],
)

a2a_capability_requests_total = Counter(
    "aiagent_a2a_capability_requests_total",
    "Total requests for each capability",
    ["capability", "found"],
)
