"""E2E tests for Kubernetes mock server."""

import pytest
import httpx


@pytest.fixture
def k8s_mock_url():
    """Kubernetes mock server URL."""
    return "http://localhost:5004"


@pytest.fixture
def auth_headers():
    """Authentication headers for mock server."""
    return {"Authorization": "Bearer mock-bearer-token-67890"}


@pytest.mark.asyncio
async def test_health_check(k8s_mock_url):
    """Test health check endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{k8s_mock_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_list_namespaces(k8s_mock_url, auth_headers):
    """Test listing namespaces."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{k8s_mock_url}/api/v1/namespaces",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kind"] == "NamespaceList"
        assert "items" in data
        assert len(data["items"]) > 0


@pytest.mark.asyncio
async def test_list_pods(k8s_mock_url, auth_headers):
    """Test listing pods in a namespace."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{k8s_mock_url}/api/v1/namespaces/production/pods",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kind"] == "PodList"
        assert "items" in data
        # Should have at least 2 pods from fixtures (api-server-abc123, api-server-def456)
        assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_get_pod(k8s_mock_url, auth_headers):
    """Test getting a specific pod."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{k8s_mock_url}/api/v1/namespaces/production/pods/api-server-abc123",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kind"] == "Pod"
        assert data["metadata"]["name"] == "api-server-abc123"
        assert data["metadata"]["namespace"] == "production"
        assert data["status"]["phase"] == "Running"


@pytest.mark.asyncio
async def test_get_pod_not_found(k8s_mock_url, auth_headers):
    """Test getting a non-existent pod."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{k8s_mock_url}/api/v1/namespaces/production/pods/nonexistent",
            headers=auth_headers,
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_pod_logs(k8s_mock_url, auth_headers):
    """Test getting pod logs."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{k8s_mock_url}/api/v1/namespaces/production/pods/api-server-abc123/log?tail=10",
            headers=auth_headers,
        )
        assert response.status_code == 200
        logs = response.text
        assert "INFO" in logs
        assert "Processing request" in logs


@pytest.mark.asyncio
async def test_list_deployments(k8s_mock_url, auth_headers):
    """Test listing deployments."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{k8s_mock_url}/apis/apps/v1/namespaces/production/deployments",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kind"] == "DeploymentList"
        assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_scale_deployment(k8s_mock_url, auth_headers):
    """Test scaling a deployment."""
    async with httpx.AsyncClient() as client:
        # Scale to 5 replicas
        response = await client.patch(
            f"{k8s_mock_url}/apis/apps/v1/namespaces/production/deployments/api-server/scale",
            headers=auth_headers,
            json={"spec": {"replicas": 5}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["spec"]["replicas"] == 5
        assert data["status"]["replicas"] == 5


@pytest.mark.asyncio
async def test_list_nodes(k8s_mock_url, auth_headers):
    """Test listing nodes."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{k8s_mock_url}/api/v1/nodes",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kind"] == "NodeList"
        assert len(data["items"]) >= 2  # node-01, node-02


@pytest.mark.asyncio
async def test_authentication_required(k8s_mock_url):
    """Test that authentication is required."""
    async with httpx.AsyncClient() as client:
        # No auth header
        response = await client.get(f"{k8s_mock_url}/api/v1/namespaces")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token(k8s_mock_url):
    """Test that invalid tokens are rejected."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{k8s_mock_url}/api/v1/namespaces",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_pod(k8s_mock_url, auth_headers):
    """Test deleting a pod."""
    async with httpx.AsyncClient() as client:
        # Delete pod
        response = await client.delete(
            f"{k8s_mock_url}/api/v1/namespaces/production/pods/api-server-def456",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "Success"

        # Verify pod is gone
        response = await client.get(
            f"{k8s_mock_url}/api/v1/namespaces/production/pods/api-server-def456",
            headers=auth_headers,
        )
        assert response.status_code == 404
