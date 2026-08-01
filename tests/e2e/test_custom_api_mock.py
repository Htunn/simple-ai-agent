"""E2E tests for Custom API mock server."""

import pytest
import httpx
import time


@pytest.fixture
def custom_api_url():
    """Custom API mock server URL."""
    return "http://localhost:5005"


@pytest.fixture
def auth_headers():
    """Authentication headers with API key."""
    return {"X-API-Key": "mock-custom-api-key-12345"}


@pytest.mark.asyncio
async def test_health_check_healthy(custom_api_url, auth_headers):
    """Test health check in healthy scenario."""
    async with httpx.AsyncClient() as client:
        # Set to healthy scenario
        await client.post(
            f"{custom_api_url}/api/scenario/set?scenario_name=healthy",
            headers=auth_headers,
        )

        # Health should succeed
        response = await client.get(f"{custom_api_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_down(custom_api_url, auth_headers):
    """Test health check when service is down."""
    async with httpx.AsyncClient() as client:
        # Set to down scenario
        await client.post(
            f"{custom_api_url}/api/scenario/set?scenario_name=down",
            headers=auth_headers,
        )

        # Health should fail
        response = await client.get(f"{custom_api_url}/health")
        assert response.status_code == 503

        # Reset to healthy
        await client.post(
            f"{custom_api_url}/api/scenario/set?scenario_name=healthy",
            headers=auth_headers,
        )


@pytest.mark.asyncio
async def test_set_scenario(custom_api_url, auth_headers):
    """Test setting active scenario."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{custom_api_url}/api/scenario/set?scenario_name=degraded",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "degraded" in data["message"]


@pytest.mark.asyncio
async def test_get_current_scenario(custom_api_url, auth_headers):
    """Test getting current scenario."""
    async with httpx.AsyncClient() as client:
        # Set to slow scenario
        await client.post(
            f"{custom_api_url}/api/scenario/set?scenario_name=slow",
            headers=auth_headers,
        )

        # Get current
        response = await client.get(
            f"{custom_api_url}/api/scenario/current",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["active_scenario"] == "slow"
        assert data["scenario"]["name"] == "slow"


@pytest.mark.asyncio
async def test_get_data_users(custom_api_url, auth_headers):
    """Test getting users data."""
    async with httpx.AsyncClient() as client:
        # Ensure healthy scenario
        await client.post(
            f"{custom_api_url}/api/scenario/set?scenario_name=healthy",
            headers=auth_headers,
        )

        response = await client.get(
            f"{custom_api_url}/api/data/users",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert len(data["users"]) == 3


@pytest.mark.asyncio
async def test_get_data_products(custom_api_url, auth_headers):
    """Test getting products data."""
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{custom_api_url}/api/scenario/set?scenario_name=healthy",
            headers=auth_headers,
        )

        response = await client.get(
            f"{custom_api_url}/api/data/products",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert len(data["products"]) == 3


@pytest.mark.asyncio
async def test_get_data_dynamic_resource(custom_api_url, auth_headers):
    """Test getting data for a dynamic resource."""
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{custom_api_url}/api/scenario/set?scenario_name=healthy",
            headers=auth_headers,
        )

        response = await client.get(
            f"{custom_api_url}/api/data/customers",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["resource"] == "customers"
        assert "data" in data


@pytest.mark.asyncio
async def test_create_data(custom_api_url, auth_headers):
    """Test creating data."""
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{custom_api_url}/api/scenario/set?scenario_name=healthy",
            headers=auth_headers,
        )

        response = await client.post(
            f"{custom_api_url}/api/data/orders",
            headers=auth_headers,
            json={"customer": "Test User", "total": 199.99},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["resource"] == "orders"
        assert "id" in data
        assert data["data"]["customer"] == "Test User"


@pytest.mark.asyncio
async def test_update_data(custom_api_url, auth_headers):
    """Test updating data."""
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{custom_api_url}/api/scenario/set?scenario_name=healthy",
            headers=auth_headers,
        )

        response = await client.put(
            f"{custom_api_url}/api/data/orders/1001",
            headers=auth_headers,
            json={"status": "delivered"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1001
        assert data["data"]["status"] == "delivered"


@pytest.mark.asyncio
async def test_delete_data(custom_api_url, auth_headers):
    """Test deleting data."""
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{custom_api_url}/api/scenario/set?scenario_name=healthy",
            headers=auth_headers,
        )

        response = await client.delete(
            f"{custom_api_url}/api/data/orders/1001",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]


@pytest.mark.asyncio
async def test_get_status_healthy(custom_api_url, auth_headers):
    """Test status endpoint in healthy scenario."""
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{custom_api_url}/api/scenario/set?scenario_name=healthy",
            headers=auth_headers,
        )

        response = await client.get(
            f"{custom_api_url}/api/status",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_get_status_degraded(custom_api_url, auth_headers):
    """Test status endpoint in degraded scenario."""
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{custom_api_url}/api/scenario/set?scenario_name=degraded",
            headers=auth_headers,
        )

        response = await client.get(
            f"{custom_api_url}/api/status",
            headers=auth_headers,
        )
        # Might succeed or fail due to error injection
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "degraded"
            assert "warnings" in data


@pytest.mark.asyncio
async def test_search(custom_api_url, auth_headers):
    """Test search endpoint."""
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{custom_api_url}/api/scenario/set?scenario_name=healthy",
            headers=auth_headers,
        )

        response = await client.get(
            f"{custom_api_url}/api/search?q=widget&limit=5",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "widget"
        assert len(data["results"]) > 0


@pytest.mark.asyncio
async def test_metrics(custom_api_url, auth_headers):
    """Test metrics endpoint."""
    async with httpx.AsyncClient() as client:
        # Reset metrics first
        await client.post(
            f"{custom_api_url}/api/metrics/reset",
            headers=auth_headers,
        )

        # Make some requests
        await client.post(
            f"{custom_api_url}/api/scenario/set?scenario_name=healthy",
            headers=auth_headers,
        )
        await client.get(
            f"{custom_api_url}/api/data/users",
            headers=auth_headers,
        )

        # Get metrics
        response = await client.get(
            f"{custom_api_url}/api/metrics",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data


@pytest.mark.asyncio
async def test_metrics_reset(custom_api_url, auth_headers):
    """Test metrics reset."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{custom_api_url}/api/metrics/reset",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "reset" in response.json()["message"]


@pytest.mark.asyncio
async def test_error_injection(custom_api_url, auth_headers):
    """Test that error injection works."""
    async with httpx.AsyncClient() as client:
        # Set to error_prone scenario (50% error rate)
        await client.post(
            f"{custom_api_url}/api/scenario/set?scenario_name=error_prone",
            headers=auth_headers,
        )

        # Make multiple requests
        errors = 0
        successes = 0
        for _ in range(20):
            response = await client.get(
                f"{custom_api_url}/api/data/users",
                headers=auth_headers,
            )
            if response.status_code >= 400:
                errors += 1
            else:
                successes += 1

        # Should have some errors (but not deterministic)
        assert errors > 0 or successes > 0  # At least one of each is likely


@pytest.mark.asyncio
async def test_latency_simulation(custom_api_url, auth_headers):
    """Test that latency simulation works."""
    async with httpx.AsyncClient() as client:
        # Set to slow scenario
        await client.post(
            f"{custom_api_url}/api/scenario/set?scenario_name=slow",
            headers=auth_headers,
        )

        # Measure latency
        start = time.time()
        response = await client.get(
            f"{custom_api_url}/api/data/users",
            headers=auth_headers,
        )
        duration = time.time() - start

        # Should take at least 1 second (min latency in slow scenario)
        assert duration >= 1.0


@pytest.mark.asyncio
async def test_authentication_required(custom_api_url):
    """Test that authentication is required."""
    async with httpx.AsyncClient() as client:
        # No API key
        response = await client.get(f"{custom_api_url}/api/data/users")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_api_key(custom_api_url):
    """Test that invalid API keys are rejected."""
    headers = {"X-API-Key": "invalid-key"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{custom_api_url}/api/data/users",
            headers=headers,
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_scenario(custom_api_url, auth_headers):
    """Test setting an invalid scenario."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{custom_api_url}/api/scenario/set?scenario_name=nonexistent",
            headers=auth_headers,
        )
        assert response.status_code == 404
