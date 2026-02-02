"""Health check endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.database import get_redis
from src.database.postgres import engine

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    database: str
    redis: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint for Docker and monitoring."""
    db_status = "healthy"
    redis_status = "healthy"

    # Check database connection
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # Check Redis connection
    try:
        redis_client = get_redis()
        await redis_client.ping()
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"

    overall_status = (
        "healthy" if db_status == "healthy" and redis_status == "healthy" else "unhealthy"
    )

    if overall_status == "unhealthy":
        raise HTTPException(status_code=503, detail="Service unhealthy")

    return HealthResponse(
        status=overall_status, database=db_status, redis=redis_status
    )


@router.get("/ready")
async def readiness_check() -> dict:
    """Readiness check endpoint."""
    return {"ready": True}
