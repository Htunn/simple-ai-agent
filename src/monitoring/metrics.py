"""
Application-level Prometheus metrics.

Exposes key counters / gauges for the AI agent so Prometheus can scrape `/metrics`.
"""

from prometheus_client import Counter, Gauge, Histogram, Info, REGISTRY, CollectorRegistry
from prometheus_client.core import GaugeMetricFamily

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

# ── MCP ───────────────────────────────────────────────────────────────────────

mcp_tool_calls_total = Counter(
    "aiagent_mcp_tool_calls_total",
    "Total MCP tool invocations",
    ["server", "tool", "status"],
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

build_info.info({
    "version": "0.1.0",
    "environment": "production",
})
