"""
Async Prometheus client for AIOps metrics queries.

Queries the Prometheus HTTP API to retrieve metrics relevant to
cluster health: restart rates, OOMKills, error rates, CPU throttling.
"""

import asyncio
from typing import Any

import httpx
import structlog

from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class PrometheusClient:
    """
    Async HTTP client for Prometheus query API.

    Usage:
        client = PrometheusClient()
        result = await client.query('rate(container_restarts_total[5m])')
    """

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = (base_url or settings.prometheus_url or "").rstrip("/")
        self._timeout = 10.0

    @property
    def is_configured(self) -> bool:
        return bool(self._base_url)

    async def query(self, promql: str) -> list[dict[str, Any]]:
        """Run an instant PromQL query and return the result vector."""
        if not self.is_configured:
            return []
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{self._base_url}/api/v1/query",
                params={"query": promql},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {}).get("result", [])

    async def query_range(self, promql: str, start: str, end: str, step: str = "1m") -> list[dict[str, Any]]:
        """Run a range PromQL query."""
        if not self.is_configured:
            return []
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{self._base_url}/api/v1/query_range",
                params={"query": promql, "start": start, "end": end, "step": step},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {}).get("result", [])

    # ── Convenience queries ───────────────────────────────────────────────────

    async def get_pod_restart_rate(self, namespace: str = "", window: str = "5m") -> list[dict[str, Any]]:
        """Get pod restart rates over the given window."""
        ns_filter = f', namespace="{namespace}"' if namespace else ""
        return await self.query(
            f'sum by (pod, namespace) (rate(kube_pod_container_status_restarts_total{{container!=""{ns_filter}}}[{window}]))'
        )

    async def get_oom_kills(self, namespace: str = "") -> list[dict[str, Any]]:
        """Get recent OOMKill events."""
        ns_filter = f', namespace="{namespace}"' if namespace else ""
        return await self.query(
            f'kube_pod_container_status_last_terminated_reason{{reason="OOMKilled"{ns_filter}}}'
        )

    async def get_unavailable_deployments(self, namespace: str = "") -> list[dict[str, Any]]:
        """Get deployments with unavailable replicas."""
        ns_filter = f', namespace="{namespace}"' if namespace else ""
        return await self.query(
            f'kube_deployment_status_replicas_unavailable{{replicas_unavailable!="0"{ns_filter}}}'
        )

    async def get_cpu_throttling(self, namespace: str = "", threshold: float = 0.5) -> list[dict[str, Any]]:
        """Find pods with high CPU throttling ratio."""
        ns_filter = f', namespace="{namespace}"' if namespace else ""
        return await self.query(
            f'rate(container_cpu_cfs_throttled_seconds_total{{container!=""{ns_filter}}}[5m]) / '
            f'rate(container_cpu_cfs_periods_total{{container!=""{ns_filter}}}[5m]) > {threshold}'
        )

    async def get_cluster_health_summary(self) -> dict[str, Any]:
        """Return a high-level cluster health summary from Prometheus."""
        if not self.is_configured:
            return {"available": False, "reason": "Prometheus not configured"}

        try:
            async with asyncio.timeout(15):
                restarts = await self.get_pod_restart_rate()
                ooms = await self.get_oom_kills()
                unavailable = await self.get_unavailable_deployments()
                throttled = await self.get_cpu_throttling()

            return {
                "available": True,
                "high_restart_pods": len(restarts),
                "oom_killed_pods": len(ooms),
                "unavailable_deployments": len(unavailable),
                "cpu_throttled_pods": len(throttled),
            }
        except Exception as e:
            logger.warning("prometheus_health_query_failed", error=str(e))
            return {"available": False, "reason": str(e)}
