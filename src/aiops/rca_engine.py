"""
AI-powered Root Cause Analysis engine.

Takes an incident context (pod events, logs, metrics snapshot) and
sends it to the AI model with an SRE-specialist prompt to produce
a structured RCA report with confidence score and recommended actions.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any

import structlog

from src.config import get_settings

logger = structlog.get_logger()
Settings = get_settings


@dataclass
class RCAReport:
    """Structured output from the RCA engine."""

    root_cause: str
    confidence: float  # 0.0 - 1.0
    failure_pattern: str  # e.g., "OOMKill", "Config Error", "Network Timeout"
    recommended_actions: list[str]
    supporting_evidence: list[str]
    incident_context: dict[str, Any] = field(default_factory=dict)

    def to_markdown(self) -> str:
        confidence_pct = int(self.confidence * 100)
        evidence_lines = "\n".join(f"  - {e}" for e in self.supporting_evidence)
        actions_lines = "\n".join(f"  {i + 1}. {a}" for i, a in enumerate(self.recommended_actions))
        return (
            f"**🔍 Root Cause Analysis**\n\n"
            f"**Pattern:** {self.failure_pattern}\n"
            f"**Root Cause:** {self.root_cause}\n"
            f"**Confidence:** {confidence_pct}%\n\n"
            f"**Supporting Evidence:**\n{evidence_lines}\n\n"
            f"**Recommended Actions:**\n{actions_lines}"
        )


_RCA_SYSTEM_PROMPT = """\
You are an expert Site Reliability Engineer (SRE) specialized in Kubernetes and cloud-native systems.
Your task is to perform root cause analysis (RCA) on the provided incident context.

Respond ONLY with a JSON object with this exact structure:
{
  "root_cause": "Clear one-sentence description of the root cause",
  "confidence": 0.85,
  "failure_pattern": "One of: OOMKill | CrashLoop | ConfigError | NetworkTimeout | ImagePullError | ResourceExhaustion | DependencyFailure | NodePressure | StorageFailure | Unknown",
  "recommended_actions": ["Action 1", "Action 2", "Action 3"],
  "supporting_evidence": ["Evidence item 1", "Evidence item 2"]
}

Analyze the incident context carefully:
- Pod events (reason, message fields)
- Log content (errors, stack traces, connection failures)
- Resource metrics (restart count, memory usage)
- Node conditions
- Deployment history
"""


class RCAEngine:
    """
    AI-powered root cause analysis.

    Usage:
        rca = RCAEngine(ai_client)
        report = await rca.analyze(incident_context)
    """

    def __init__(self, ai_client: Any = None) -> None:
        self._ai_client = ai_client

    async def analyze(self, incident_context: dict[str, Any]) -> RCAReport:
        """
        Run RCA on an incident context dict.

        Context should contain:
          - resource_name, namespace, resource_kind
          - events: list of K8s events
          - logs: log lines as string
          - restarts: int
          - metrics: dict (optional)
        """
        if not self._ai_client:
            return self._fallback_rca(incident_context)

        settings = get_settings()
        timeout = getattr(settings, "rca_timeout_seconds", 30)
        user_message = self._build_context_message(incident_context)
        try:
            import json

            response = await asyncio.wait_for(
                self._ai_client.complete(
                    system_prompt=_RCA_SYSTEM_PROMPT,
                    user_message=user_message,
                    model="gpt-4o",
                    max_tokens=800,
                ),
                timeout=float(timeout),
            )
            # Extract JSON from response (handle code-fenced output)
            content = response.strip()
            if "```" in content:
                parts = content.split("```")
                content = parts[1] if len(parts) > 1 else content
                if content.startswith("json"):
                    content = content[4:]
            try:
                data = json.loads(content)
            except (json.JSONDecodeError, ValueError) as parse_err:
                logger.warning("rca_json_parse_failed", error=str(parse_err))
                return self._fallback_rca(incident_context)

            raw_confidence = float(data.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, raw_confidence))  # clamp to [0.0, 1.0]
            return RCAReport(
                root_cause=data.get("root_cause") or "Unknown",
                confidence=confidence,
                failure_pattern=data.get("failure_pattern") or "Unknown",
                recommended_actions=data.get("recommended_actions") or [],
                supporting_evidence=data.get("supporting_evidence") or [],
                incident_context=incident_context,
            )
        except TimeoutError:
            logger.warning("rca_ai_timeout", timeout_seconds=timeout)
            return self._fallback_rca(incident_context)
        except Exception as e:
            logger.warning("rca_ai_analysis_failed", error=str(e))
            return self._fallback_rca(incident_context)

    @staticmethod
    def _build_context_message(ctx: dict[str, Any]) -> str:
        lines = [
            "## Incident Context",
            f"Resource: {ctx.get('resource_kind', 'Pod')}/{ctx.get('resource_name', 'unknown')}",
            f"Namespace: {ctx.get('namespace', 'default')}",
            f"Restart Count: {ctx.get('restarts', 0)}",
            "",
            "## Recent Events",
        ]
        for ev in (ctx.get("events") or [])[:10]:
            lines.append(
                f"- [{ev.get('type', '')}] {ev.get('reason', '')}: {ev.get('message', '')}"
            )

        lines += ["", "## Recent Logs"]
        logs = ctx.get("logs", "")
        if logs:
            # Show last 50 lines
            log_lines = logs.strip().split("\n")[-50:]
            lines.extend(log_lines)
        else:
            lines.append("(no logs available)")

        if ctx.get("metrics"):
            lines += ["", "## Metrics"]
            for k, v in ctx["metrics"].items():
                lines.append(f"- {k}: {v}")

        return "\n".join(lines)

    @staticmethod
    def _fallback_rca(ctx: dict[str, Any]) -> RCAReport:
        """Simple heuristic-based fallback when AI is unavailable."""
        logs = ctx.get("logs", "").lower()
        restarts = ctx.get("restarts", 0)

        if "oomkill" in logs or "out of memory" in logs:
            return RCAReport(
                root_cause="Container exceeded memory limits and was killed by the OOM reaper",
                confidence=0.85,
                failure_pattern="OOMKill",
                recommended_actions=[
                    "Increase memory limits",
                    "Profile application memory usage",
                    "Add memory limit alerts",
                ],
                supporting_evidence=["OOM kill detected in logs"],
                incident_context=ctx,
            )
        if restarts > 5:
            return RCAReport(
                root_cause="Application is crashing repeatedly due to an unhandled error on startup or runtime",
                confidence=0.70,
                failure_pattern="CrashLoop",
                recommended_actions=[
                    "Check application logs for exceptions",
                    "Verify configuration/secrets",
                    "Check liveness probe settings",
                ],
                supporting_evidence=[f"Pod has {restarts} restarts"],
                incident_context=ctx,
            )
        return RCAReport(
            root_cause="Unknown — insufficient data for automated analysis",
            confidence=0.30,
            failure_pattern="Unknown",
            recommended_actions=[
                "Inspect pod events manually",
                "Review recent deployments",
                "Check cluster events",
            ],
            supporting_evidence=[],
            incident_context=ctx,
        )
