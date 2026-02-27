"""
Async Kubernetes client wrapping kubernetes-asyncio.

Provides a singleton client with lazy initialization, supporting both
in-cluster config (production) and kubeconfig file (local/dev).
"""

import asyncio
import os
from functools import lru_cache
from typing import Any

import structlog

logger = structlog.get_logger()


class KubernetesClient:
    """
    Singleton async Kubernetes client.

    Wraps kubernetes-asyncio CoreV1Api, AppsV1Api, BatchV1Api for all
    AIOps self-healing and monitoring operations.

    Usage:
        client = await KubernetesClient.get_instance()
        pods = await client.list_pods(namespace="default")
    """

    _instance: "KubernetesClient | None" = None
    _lock = asyncio.Lock()

    def __init__(self) -> None:
        self._core_v1 = None
        self._apps_v1 = None
        self._batch_v1 = None
        self._custom_objects = None
        self._config = None
        self._initialized = False

    @classmethod
    async def get_instance(cls) -> "KubernetesClient":
        """Get or create the singleton client instance."""
        async with cls._lock:
            if cls._instance is None or not cls._instance._initialized:
                instance = cls()
                await instance._initialize()
                cls._instance = instance
            return cls._instance

    async def _initialize(self) -> None:
        """Initialize the Kubernetes API clients."""
        try:
            from kubernetes_asyncio import client as k8s_client
            from kubernetes_asyncio import config as k8s_config

            # Try in-cluster config first (when running inside K8s)
            if self._is_in_cluster():
                await k8s_config.load_incluster_config()
                logger.info("k8s_client_initialized", mode="in-cluster")
            else:
                # Fall back to kubeconfig file
                kubeconfig = os.environ.get("KUBECONFIG", os.path.expanduser("~/.kube/config"))
                await k8s_config.load_kube_config(config_file=kubeconfig)
                logger.info("k8s_client_initialized", mode="kubeconfig", path=kubeconfig)

            self._core_v1 = k8s_client.CoreV1Api()
            self._apps_v1 = k8s_client.AppsV1Api()
            self._batch_v1 = k8s_client.BatchV1Api()
            self._custom_objects = k8s_client.CustomObjectsApi()
            self._initialized = True

        except Exception as e:
            logger.warning("k8s_client_init_failed", error=str(e))
            self._initialized = False
            raise

    @staticmethod
    def _is_in_cluster() -> bool:
        """Detect if running inside a Kubernetes pod."""
        return os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token")

    @property
    def is_available(self) -> bool:
        return self._initialized

    # ── Pod Operations ─────────────────────────────────────────────────────────

    async def list_pods(self, namespace: str = "default", label_selector: str | None = None) -> list[dict[str, Any]]:
        """List pods in a namespace with their status."""
        resp = await self._core_v1.list_namespaced_pod(
            namespace=namespace,
            label_selector=label_selector or "",
        )
        return [self._pod_to_dict(p) for p in resp.items]

    async def get_pod(self, name: str, namespace: str = "default") -> dict[str, Any] | None:
        """Get a single pod by name."""
        try:
            pod = await self._core_v1.read_namespaced_pod(name=name, namespace=namespace)
            return self._pod_to_dict(pod)
        except Exception:
            return None

    async def delete_pod(self, name: str, namespace: str = "default", grace_period: int = 0) -> bool:
        """Delete a pod (triggers restart if managed by a controller)."""
        from kubernetes_asyncio.client import V1DeleteOptions
        await self._core_v1.delete_namespaced_pod(
            name=name,
            namespace=namespace,
            body=V1DeleteOptions(grace_period_seconds=grace_period),
        )
        return True

    async def get_pod_logs(self, name: str, namespace: str = "default",
                           container: str | None = None, tail_lines: int = 100) -> str:
        """Fetch pod logs."""
        return await self._core_v1.read_namespaced_pod_log(
            name=name,
            namespace=namespace,
            container=container,
            tail_lines=tail_lines,
            timestamps=True,
        ) or ""

    # ── Deployment Operations ──────────────────────────────────────────────────

    async def list_deployments(self, namespace: str = "default") -> list[dict[str, Any]]:
        """List deployments in a namespace."""
        resp = await self._apps_v1.list_namespaced_deployment(namespace=namespace)
        return [self._deployment_to_dict(d) for d in resp.items]

    async def get_deployment(self, name: str, namespace: str = "default") -> dict[str, Any] | None:
        """Get a single deployment."""
        try:
            d = await self._apps_v1.read_namespaced_deployment(name=name, namespace=namespace)
            return self._deployment_to_dict(d)
        except Exception:
            return None

    async def scale_deployment(self, name: str, replicas: int, namespace: str = "default") -> bool:
        """Scale a deployment to the given replica count."""
        from kubernetes_asyncio.client import V1Scale, V1ScaleSpec, V1ObjectMeta
        scale = V1Scale(
            metadata=V1ObjectMeta(name=name, namespace=namespace),
            spec=V1ScaleSpec(replicas=replicas),
        )
        await self._apps_v1.replace_namespaced_deployment_scale(name=name, namespace=namespace, body=scale)
        return True

    async def patch_deployment(self, name: str, namespace: str, patch: dict[str, Any]) -> bool:
        """Apply a JSON merge patch to a deployment."""
        await self._apps_v1.patch_namespaced_deployment(name=name, namespace=namespace, body=patch)
        return True

    async def update_deployment_image(self, name: str, namespace: str, container: str, image: str) -> bool:
        """Update the container image in a deployment."""
        patch = {"spec": {"template": {"spec": {"containers": [{"name": container, "image": image}]}}}}
        return await self.patch_deployment(name, namespace, patch)

    # ── Rollout Operations ────────────────────────────────────────────────────

    async def restart_deployment(self, name: str, namespace: str = "default") -> bool:
        """Trigger a rolling restart by patching the annotation."""
        from datetime import timezone, datetime
        patch = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "kubectl.kubernetes.io/restartedAt": datetime.now(timezone.utc).isoformat()
                        }
                    }
                }
            }
        }
        return await self.patch_deployment(name, namespace, patch)

    async def rollback_deployment(self, name: str, namespace: str = "default", revision: int | None = None) -> bool:
        """Rollback a deployment to a previous revision via kubectl (no native API)."""
        cmd = ["kubectl", "rollout", "undo", f"deployment/{name}", "-n", namespace]
        if revision:
            cmd += [f"--to-revision={revision}"]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode())
        return True

    async def get_rollout_history(self, name: str, namespace: str = "default") -> str:
        """Get rollout history for a deployment."""
        proc = await asyncio.create_subprocess_exec(
            "kubectl", "rollout", "history", f"deployment/{name}", "-n", namespace,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode())
        return stdout.decode()

    async def get_rollout_status(self, name: str, namespace: str = "default") -> str:
        """Get rollout status for a deployment."""
        proc = await asyncio.create_subprocess_exec(
            "kubectl", "rollout", "status", f"deployment/{name}", "-n", namespace, "--timeout=30s",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        return stdout.decode()

    # ── Node Operations ───────────────────────────────────────────────────────

    async def list_nodes(self) -> list[dict[str, Any]]:
        """List cluster nodes."""
        resp = await self._core_v1.list_node()
        return [self._node_to_dict(n) for n in resp.items]

    async def cordon_node(self, name: str) -> bool:
        """Cordon a node to prevent new pod scheduling."""
        patch = {"spec": {"unschedulable": True}}
        await self._core_v1.patch_node(name=name, body=patch)
        return True

    async def uncordon_node(self, name: str) -> bool:
        """Uncordon a node to allow pod scheduling."""
        patch = {"spec": {"unschedulable": False}}
        await self._core_v1.patch_node(name=name, body=patch)
        return True

    async def drain_node(self, name: str, ignore_daemonsets: bool = True, delete_emissary_data: bool = True) -> str:
        """Drain a node of all pods."""
        cmd = ["kubectl", "drain", name, "--ignore-daemonsets"]
        if delete_emissary_data:
            cmd.append("--delete-emissary-data")
        cmd += ["--timeout=120s"]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode())
        return stdout.decode()

    async def taint_node(self, name: str, key: str, value: str, effect: str = "NoSchedule") -> bool:
        """Taint a node."""
        proc = await asyncio.create_subprocess_exec(
            "kubectl", "taint", "node", name, f"{key}={value}:{effect}",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode())
        return True

    # ── Event & Metrics Operations ────────────────────────────────────────────

    async def list_events(self, namespace: str = "default", field_selector: str | None = None) -> list[dict[str, Any]]:
        """List events in a namespace."""
        resp = await self._core_v1.list_namespaced_event(
            namespace=namespace,
            field_selector=field_selector or "",
        )
        events = sorted(resp.items, key=lambda e: e.last_timestamp or e.event_time or "", reverse=True)
        return [self._event_to_dict(e) for e in events[:50]]

    async def get_crashloop_pods(self, namespace: str | None = None) -> list[dict[str, Any]]:
        """Find all CrashLoopBackOff pods across namespaces."""
        if namespace:
            resp = await self._core_v1.list_namespaced_pod(namespace=namespace)
        else:
            resp = await self._core_v1.list_pod_for_all_namespaces()

        results = []
        for pod in resp.items:
            for cs in (pod.status.container_statuses or []):
                if cs.state and cs.state.waiting and cs.state.waiting.reason in (
                    "CrashLoopBackOff", "Error", "OOMKilled"
                ):
                    results.append(self._pod_to_dict(pod))
                    break
        return results

    async def get_not_ready_nodes(self) -> list[dict[str, Any]]:
        """Find all nodes that are not Ready."""
        nodes = await self.list_nodes()
        return [n for n in nodes if n.get("status") != "Ready"]

    async def label_resource(self, resource_type: str, name: str, namespace: str, labels: dict[str, str]) -> bool:
        """Label a kubernetes resource."""
        label_args = [f"{k}={v}" for k, v in labels.items()]
        cmd = ["kubectl", "label", resource_type, name, "-n", namespace, "--overwrite"] + label_args
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode())
        return True

    async def exec_in_pod(self, pod_name: str, namespace: str, command: list[str]) -> str:
        """
        Execute a command in a pod (allowlisted commands only for safety).
        Returns stdout output.
        """
        ALLOWED_COMMANDS = {"ls", "cat", "echo", "env", "ps", "df", "free", "date", "hostname", "uptime", "curl", "wget"}
        if command and command[0] not in ALLOWED_COMMANDS:
            raise ValueError(f"Command '{command[0]}' is not allowlisted for exec. Allowed: {sorted(ALLOWED_COMMANDS)}")

        cmd = ["kubectl", "exec", pod_name, "-n", namespace, "--"] + command
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode())
        return stdout.decode()

    # ── Serializers ───────────────────────────────────────────────────────────

    @staticmethod
    def _pod_to_dict(pod) -> dict[str, Any]:
        containers = pod.spec.containers or []
        container_statuses = pod.status.container_statuses or []
        ready_count = sum(1 for cs in container_statuses if cs.ready)
        restart_count = sum(cs.restart_count or 0 for cs in container_statuses)

        # Determine primary state
        phase = pod.status.phase or "Unknown"
        waiting_reason = None
        for cs in container_statuses:
            if cs.state and cs.state.waiting:
                waiting_reason = cs.state.waiting.reason
                break

        return {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "phase": phase,
            "status": waiting_reason or phase,
            "ready": f"{ready_count}/{len(containers)}",
            "restarts": restart_count,
            "node": pod.spec.node_name,
            "labels": pod.metadata.labels or {},
            "age": str(pod.metadata.creation_timestamp),
        }

    @staticmethod
    def _deployment_to_dict(d) -> dict[str, Any]:
        spec = d.spec or {}
        status = d.status or {}
        return {
            "name": d.metadata.name,
            "namespace": d.metadata.namespace,
            "replicas": getattr(spec, "replicas", 0),
            "ready_replicas": getattr(status, "ready_replicas", 0) or 0,
            "available_replicas": getattr(status, "available_replicas", 0) or 0,
            "labels": d.metadata.labels or {},
        }

    @staticmethod
    def _node_to_dict(node) -> dict[str, Any]:
        conditions = node.status.conditions or []
        ready_cond = next((c for c in conditions if c.type == "Ready"), None)
        status = "Ready" if (ready_cond and ready_cond.status == "True") else "NotReady"
        return {
            "name": node.metadata.name,
            "status": status,
            "unschedulable": node.spec.unschedulable or False,
            "labels": node.metadata.labels or {},
        }

    @staticmethod
    def _event_to_dict(e) -> dict[str, Any]:
        return {
            "namespace": e.metadata.namespace,
            "name": e.metadata.name,
            "reason": e.reason,
            "message": e.message,
            "type": e.type,
            "count": e.count,
            "involved_object": f"{e.involved_object.kind}/{e.involved_object.name}" if e.involved_object else "",
            "last_timestamp": str(e.last_timestamp or e.event_time or ""),
        }


# Module-level singleton accessor
_client_instance: KubernetesClient | None = None


async def get_k8s_client() -> KubernetesClient:
    """Get the global K8s async client singleton."""
    return await KubernetesClient.get_instance()
