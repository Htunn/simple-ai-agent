"""Health check endpoints."""

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from src.config import get_settings
from src.database import get_redis
from src.database.postgres import engine

logger = structlog.get_logger()
router = APIRouter()
settings = get_settings()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    database: str
    redis: str
    kubernetes: str
    prometheus: str
    watchloop: str
    pending_approvals: int
    active_incidents: int


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint — covers DB, Redis, K8s, Prometheus, and AIOps subsystems."""
    db_status = "healthy"
    redis_status = "healthy"
    k8s_status = "disabled"
    prometheus_status = "disabled"
    watchloop_status = "disabled"
    pending_approvals = 0
    active_incidents = 0

    # ── Database ──────────────────────────────────────────────────
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # ── Redis ─────────────────────────────────────────────────────
    try:
        redis_client = get_redis()
        await redis_client.ping()
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"

    # ── Kubernetes ───────────────────────────────────────────────
    if settings.k8s_watchloop_enabled:
        try:
            from src.k8s.client import get_k8s_client
            k8s_client = await get_k8s_client()
            ns_list = await k8s_client.list_namespaces()
            k8s_status = f"healthy ({len(ns_list)} namespaces)"
        except Exception as e:
            k8s_status = f"unhealthy: {str(e)}"

    # ── Watchloop ────────────────────────────────────────────────
    if settings.k8s_watchloop_enabled:
        try:
            from src.main import get_watchloop
            wl = get_watchloop()
            if wl is None:
                watchloop_status = "not_started"
            else:
                watchloop_status = "running" if wl.is_running else "stopped"
        except Exception as e:
            watchloop_status = f"error: {str(e)}"

    # ── Prometheus ───────────────────────────────────────────────
    if settings.prometheus_url:
        try:
            from src.monitoring.prometheus import PrometheusClient
            prom = PrometheusClient()
            summary = await prom.get_cluster_health_summary()
            # summary is a dict; just confirm we got something
            prometheus_status = "healthy"
        except Exception as e:
            prometheus_status = f"unhealthy: {str(e)}"

    # ── Pending approvals (Redis scan) ───────────────────────────
    try:
        redis_client = get_redis()
        keys = await redis_client.keys("approval:*")
        pending_approvals = len(keys)
    except Exception:
        pending_approvals = 0

    # ── Active incidents (DB count) ───────────────────────────────
    if db_status == "healthy":
        try:
            async with engine.connect() as conn:
                row = await conn.execute(
                    text("SELECT COUNT(*) FROM incidents WHERE status = 'open'")
                )
                active_incidents = row.scalar() or 0
        except Exception:
            active_incidents = 0

    # ── Overall status ────────────────────────────────────────────
    degraded = any(
        v.startswith("unhealthy")
        for v in (db_status, redis_status)
    )
    overall_status = "unhealthy" if degraded else "healthy"

    if overall_status == "unhealthy":
        raise HTTPException(status_code=503, detail="Service unhealthy")

    return HealthResponse(
        status=overall_status,
        database=db_status,
        redis=redis_status,
        kubernetes=k8s_status,
        prometheus=prometheus_status,
        watchloop=watchloop_status,
        pending_approvals=pending_approvals,
        active_incidents=active_incidents,
    )


@router.get("/ready")
async def readiness_check() -> dict:
    """Readiness check endpoint."""
    return {"ready": True}


@router.get("/health/aiops")
async def aiops_health() -> dict[str, Any]:
    """
    Detailed AIOps subsystem status.

    Returns watchloop state, Prometheus metrics, and pending approval IDs.
    """
    result: dict[str, Any] = {
        "watchloop_running": False,
        "prometheus_reachable": False,
        "grafana_reachable": False,
        "pending_approvals": [],
        "cluster_health": {},
    }

    # Watchloop
    try:
        from src.main import get_watchloop
        wl = get_watchloop()
        result["watchloop_running"] = bool(wl and wl.is_running)
    except Exception as e:
        logger.debug("aiops_health_watchloop_error", error=str(e))

    # Prometheus cluster health summary
    if settings.prometheus_url:
        try:
            from src.monitoring.prometheus import PrometheusClient
            prom = PrometheusClient()
            result["cluster_health"] = await prom.get_cluster_health_summary()
            result["prometheus_reachable"] = True
        except Exception as e:
            logger.debug("aiops_health_prometheus_error", error=str(e))

    # Grafana reachability (just a HEAD on the base URL)
    if settings.grafana_url:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{settings.grafana_url}/api/health")
                result["grafana_reachable"] = resp.status_code < 500
        except Exception as e:
            logger.debug("aiops_health_grafana_error", error=str(e))

    # Pending approvals
    try:
        redis_client = get_redis()
        keys = await redis_client.keys("approval:*")
        result["pending_approvals"] = [k.split(":")[-1] for k in keys]
    except Exception:
        pass

    return result
