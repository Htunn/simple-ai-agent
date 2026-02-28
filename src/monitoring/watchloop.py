"""
K8s Watchloop - background polling task for proactive cluster monitoring.

Detects anomalies (CrashLoopBackOff, NotReady nodes, replication failures)
and publishes events to alerts queue for downstream processing.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Coroutine

import structlog

from src.config import get_settings

if TYPE_CHECKING:
    from src.k8s.client import KubernetesClient

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class ClusterEvent:
    """A detected cluster anomaly event."""
    event_type: str          # crash_loop | not_ready_node | replication_failure | oom_killed
    severity: str            # critical | warning | info
    namespace: str
    resource_kind: str
    resource_name: str
    message: str
    labels: dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "severity": self.severity,
            "namespace": self.namespace,
            "resource_kind": self.resource_kind,
            "resource_name": self.resource_name,
            "message": self.message,
            "labels": self.labels,
            "detected_at": self.detected_at.isoformat(),
        }


class K8sWatchLoop:
    """
    Background watchloop polling the Kubernetes cluster at a configurable interval.

    On each tick:
    1. Scan for CrashLoopBackOff / OOMKilled pods
    2. Scan for NotReady nodes
    3. Scan for deployments with 0 available replicas
    4. Publish detected events to the event queue for alert routing

    Usage:
        loop = K8sWatchLoop(event_callback=my_handler)
        await loop.start()
        # ... application runs ...
        await loop.stop()
    """

    def __init__(
        self,
        event_callback: Callable[[ClusterEvent], Coroutine] | None = None,
        interval: int | None = None,
    ) -> None:
        self._event_callback = event_callback
        self._interval = interval or settings.k8s_watchloop_interval
        self._running = False
        self._task: asyncio.Task | None = None
        self._known_issues: dict[str, datetime] = {}  # resource_key -> first_seen, to avoid duplicate alerts
        self._k8s: "KubernetesClient | None" = None

    async def start(self) -> None:
        """Start the watchloop background task."""
        if self._running:
            return
        try:
            from src.k8s.client import get_k8s_client
            self._k8s = await get_k8s_client()
            if not self._k8s.is_available:
                logger.warning("watchloop_k8s_unavailable", msg="K8s client not initialized, watchloop disabled")
                return
        except Exception as e:
            logger.warning("watchloop_k8s_init_failed", error=str(e))
            return

        self._running = True
        self._task = asyncio.create_task(self._run(), name="k8s-watchloop")
        logger.info("k8s_watchloop_started", interval_seconds=self._interval)

    async def stop(self) -> None:
        """Stop the watchloop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("k8s_watchloop_stopped")

    @property
    def is_running(self) -> bool:
        return self._running and (self._task is not None) and not (self._task.done())

    async def _run(self) -> None:
        """Main watchloop polling loop."""
        while self._running:
            try:
                await self._tick()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("watchloop_tick_error", error=str(e))
            await asyncio.sleep(self._interval)

    async def _tick(self) -> None:
        """Single poll iteration across all namespaces."""
        if self._k8s is None:
            return
        events: list[ClusterEvent] = []

        # 1. Scan for crashloop and OOMKilled pods
        try:
            crash_pods = await self._k8s.get_crashloop_pods()
            for pod in crash_pods:
                key = f"pod/{pod['namespace']}/{pod['name']}"
                if key not in self._known_issues:
                    self._known_issues[key] = datetime.now(timezone.utc)
                    status = pod.get("status", "CrashLoopBackOff")
                    severity = "critical" if "CrashLoop" in status or "OOM" in status else "warning"
                    events.append(ClusterEvent(
                        event_type="crash_loop" if "OOM" not in status else "oom_killed",
                        severity=severity,
                        namespace=pod["namespace"],
                        resource_kind="Pod",
                        resource_name=pod["name"],
                        message=f"Pod {pod['name']} in {pod['namespace']} is {status} (restarts: {pod.get('restarts', 0)})",
                        labels=pod.get("labels", {}),
                    ))
                # Clear resolved pods from known issues
                elif pod.get("status") not in ("CrashLoopBackOff", "Error", "OOMKilled"):
                    self._known_issues.pop(key, None)
        except Exception as e:
            logger.debug("watchloop_crashloop_check_error", error=str(e))

        # 2. Scan for NotReady nodes
        try:
            not_ready = await self._k8s.get_not_ready_nodes()
            not_ready_keys = {f"node/{node['name']}" for node in not_ready}

            # Clean up recovered nodes
            for key in list(self._known_issues):
                if key.startswith("node/") and key not in not_ready_keys:
                    self._known_issues.pop(key, None)
                    logger.info("watchloop_node_recovered", node=key.split("/", 1)[-1])

            for node in not_ready:
                key = f"node/{node['name']}"
                if key not in self._known_issues:
                    self._known_issues[key] = datetime.now(timezone.utc)
                    events.append(ClusterEvent(
                        event_type="not_ready_node",
                        severity="critical",
                        namespace="",
                        resource_kind="Node",
                        resource_name=node["name"],
                        message=f"Node {node['name']} is NotReady",
                        labels=node.get("labels", {}),
                    ))
        except Exception as e:
            logger.debug("watchloop_node_check_error", error=str(e))

        # 3. Scan for deployments with 0 available replicas (desired > 0)
        try:
            namespaces_resp = await self._k8s._core_v1.list_namespace()  # type: ignore[union-attr]
            current_failed_deployments: set[str] = set()

            for ns in namespaces_resp.items:
                ns_name = ns.metadata.name
                if ns_name in ("kube-system", "kube-public", "kube-node-lease"):
                    continue
                deployments = await self._k8s.list_deployments(namespace=ns_name)
                for dep in deployments:
                    key = f"deployment/{ns_name}/{dep['name']}"
                    if dep.get("replicas", 0) > 0 and dep.get("available_replicas", 0) == 0:
                        current_failed_deployments.add(key)
                        if key not in self._known_issues:
                            self._known_issues[key] = datetime.now(timezone.utc)
                            events.append(ClusterEvent(
                                event_type="replication_failure",
                                severity="critical",
                                namespace=ns_name,
                                resource_kind="Deployment",
                                resource_name=dep["name"],
                                message=f"Deployment {dep['name']} in {ns_name} has 0/{dep['replicas']} replicas available",
                                labels=dep.get("labels", {}),
                            ))

            # Clean up recovered deployments
            for key in list(self._known_issues):
                if key.startswith("deployment/") and key not in current_failed_deployments:
                    self._known_issues.pop(key, None)
                    _, ns_name, dep_name = key.split("/", 2)
                    logger.info("watchloop_deployment_recovered", deployment=dep_name, namespace=ns_name)

        except Exception as e:
            logger.debug("watchloop_deployment_check_error", error=str(e))

        # Publish events
        for event in events:
            logger.info("watchloop_event_detected", event_type=event.event_type,
                       resource=f"{event.resource_kind}/{event.resource_name}",
                       severity=event.severity)
            if self._event_callback:
                try:
                    await self._event_callback(event)
                except Exception as e:
                    logger.error("watchloop_callback_error", error=str(e))

        if events:
            logger.info("watchloop_tick_complete", events_detected=len(events))
