"""
Grafana client for posting incident annotations.

Annotations appear as vertical markers on Grafana dashboards,
providing visible correlation between incidents and metrics.
"""

import httpx
import structlog

from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class GrafanaClient:
    """Post incident lifecycle annotations to Grafana dashboards."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        self._base_url = (base_url or settings.grafana_url or "").rstrip("/")
        self._api_key = api_key or settings.grafana_api_key
        self._timeout = 10.0

    @property
    def is_configured(self) -> bool:
        return bool(self._base_url and self._api_key)

    async def post_annotation(self, text: str, tags: list[str] | None = None, time_ms: int | None = None) -> bool:
        """Post a Grafana annotation."""
        if not self.is_configured:
            return False
        try:
            import time as time_module
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/api/annotations",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "text": text,
                        "tags": tags or ["aiops"],
                        "time": time_ms or int(time_module.time() * 1000),
                    },
                )
                resp.raise_for_status()
                return True
        except Exception as e:
            logger.warning("grafana_annotation_failed", error=str(e))
            return False

    async def annotate_incident_opened(self, incident_id: str, title: str, severity: str) -> bool:
        """Annotate when an incident is opened."""
        return await self.post_annotation(
            text=f"🚨 [{severity.upper()}] Incident opened: {title} (ID: {incident_id})",
            tags=["aiops", "incident", "opened", severity],
        )

    async def annotate_incident_resolved(self, incident_id: str, title: str) -> bool:
        """Annotate when an incident is resolved."""
        return await self.post_annotation(
            text=f"✅ Incident resolved: {title} (ID: {incident_id})",
            tags=["aiops", "incident", "resolved"],
        )

    async def annotate_remediation(self, action: str, resource: str, namespace: str) -> bool:
        """Annotate a remediation action."""
        return await self.post_annotation(
            text=f"🔧 Remediation: {action} on {resource} in {namespace}",
            tags=["aiops", "remediation"],
        )
