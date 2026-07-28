"""E2E tests for OpenShift mock server."""

import pytest
import httpx


@pytest.fixture
def openshift_mock_url():
    """OpenShift mock server URL."""
    return "http://localhost:5003"


@pytest.fixture
def auth_headers():
    """Authentication headers with bearer token."""
    return {"Authorization": "Bearer mock-openshift-token-12345"}


@pytest.mark.asyncio
async def test_health_check(openshift_mock_url):
    """Test health check endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{openshift_mock_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "projects_count" in data
        assert "pods_count" in data
        assert "routes_count" in data


@pytest.mark.asyncio
async def test_list_projects(openshift_mock_url, auth_headers):
    """Test listing projects."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{openshift_mock_url}/apis/project.openshift.io/v1/projects",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kind"] == "ProjectList"
        assert len(data["items"]) >= 3  # At least 3 projects from fixtures


@pytest.mark.asyncio
async def test_get_project(openshift_mock_url, auth_headers):
    """Test getting a specific project."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{openshift_mock_url}/apis/project.openshift.io/v1/projects/production",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kind"] == "Project"
        assert data["metadata"]["name"] == "production"
        assert data["status"]["phase"] == "Active"


@pytest.mark.asyncio
async def test_get_project_not_found(openshift_mock_url, auth_headers):
    """Test getting a non-existent project."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{openshift_mock_url}/apis/project.openshift.io/v1/projects/nonexistent",
            headers=auth_headers,
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_pods(openshift_mock_url, auth_headers):
    """Test listing pods in a namespace."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{openshift_mock_url}/api/v1/namespaces/production/pods",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kind"] == "PodList"
        assert len(data["items"]) >= 2  # At least 2 pods in production


@pytest.mark.asyncio
async def test_get_pod(openshift_mock_url, auth_headers):
    """Test getting a specific pod."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{openshift_mock_url}/api/v1/namespaces/production/pods/api-server-7b4f6d8c9-abc12",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kind"] == "Pod"
        assert data["metadata"]["name"] == "api-server-7b4f6d8c9-abc12"
        assert data["status"]["phase"] == "Running"


@pytest.mark.asyncio
async def test_delete_pod(openshift_mock_url, auth_headers):
    """Test deleting a pod."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{openshift_mock_url}/api/v1/namespaces/staging/pods/test-app-1a2b3c4d5-test1",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Verify pod is deleted
        response = await client.get(
            f"{openshift_mock_url}/api/v1/namespaces/staging/pods/test-app-1a2b3c4d5-test1",
            headers=auth_headers,
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_deployments(openshift_mock_url, auth_headers):
    """Test listing deployments."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{openshift_mock_url}/apis/apps/v1/namespaces/production/deployments",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kind"] == "DeploymentList"
        assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_get_deployment(openshift_mock_url, auth_headers):
    """Test getting a specific deployment."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{openshift_mock_url}/apis/apps/v1/namespaces/production/deployments/api-server",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kind"] == "Deployment"
        assert data["metadata"]["name"] == "api-server"
        assert data["status"]["replicas"] == 3


@pytest.mark.asyncio
async def test_list_routes(openshift_mock_url, auth_headers):
    """Test listing routes."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{openshift_mock_url}/apis/route.openshift.io/v1/namespaces/production/routes",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kind"] == "RouteList"
        assert len(data["items"]) >= 2  # At least 2 routes in production


@pytest.mark.asyncio
async def test_get_route(openshift_mock_url, auth_headers):
    """Test getting a specific route."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{openshift_mock_url}/apis/route.openshift.io/v1/namespaces/production/routes/api-server-route",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kind"] == "Route"
        assert data["metadata"]["name"] == "api-server-route"
        assert data["spec"]["host"] == "api.example.com"
        assert data["spec"]["tls"]["termination"] == "edge"


@pytest.mark.asyncio
async def test_list_buildconfigs(openshift_mock_url, auth_headers):
    """Test listing buildconfigs."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{openshift_mock_url}/apis/build.openshift.io/v1/namespaces/production/buildconfigs",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kind"] == "BuildConfigList"
        assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_get_buildconfig(openshift_mock_url, auth_headers):
    """Test getting a specific buildconfig."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{openshift_mock_url}/apis/build.openshift.io/v1/namespaces/production/buildconfigs/api-server-build",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kind"] == "BuildConfig"
        assert data["metadata"]["name"] == "api-server-build"
        assert data["spec"]["strategy"]["type"] == "Docker"


@pytest.mark.asyncio
async def test_list_builds(openshift_mock_url, auth_headers):
    """Test listing builds."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{openshift_mock_url}/apis/build.openshift.io/v1/namespaces/production/builds",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kind"] == "BuildList"
        assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_get_build(openshift_mock_url, auth_headers):
    """Test getting a specific build."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{openshift_mock_url}/apis/build.openshift.io/v1/namespaces/production/builds/api-server-build-5",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kind"] == "Build"
        assert data["metadata"]["name"] == "api-server-build-5"
        assert data["status"]["phase"] == "Complete"


@pytest.mark.asyncio
async def test_get_build_log_complete(openshift_mock_url, auth_headers):
    """Test getting logs for a completed build."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{openshift_mock_url}/apis/build.openshift.io/v1/namespaces/production/builds/api-server-build-5/log",
            headers=auth_headers,
        )
        assert response.status_code == 200
        log = response.text
        assert "Cloning repository" in log
        assert "Successfully built image" in log
        assert "Build complete" in log


@pytest.mark.asyncio
async def test_get_build_log_failed(openshift_mock_url, auth_headers):
    """Test getting logs for a failed build."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{openshift_mock_url}/apis/build.openshift.io/v1/namespaces/staging/builds/test-build-failed-3/log",
            headers=auth_headers,
        )
        assert response.status_code == 200
        log = response.text
        assert "Error" in log or "Failed" in log


@pytest.mark.asyncio
async def test_list_imagestreams(openshift_mock_url, auth_headers):
    """Test listing imagestreams."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{openshift_mock_url}/apis/image.openshift.io/v1/namespaces/production/imagestreams",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kind"] == "ImageStreamList"
        assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_get_imagestream(openshift_mock_url, auth_headers):
    """Test getting a specific imagestream."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{openshift_mock_url}/apis/image.openshift.io/v1/namespaces/production/imagestreams/api-server",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kind"] == "ImageStream"
        assert data["metadata"]["name"] == "api-server"
        assert len(data["status"]["tags"]) >= 2  # latest and v2.1.0


@pytest.mark.asyncio
async def test_authentication_required(openshift_mock_url):
    """Test that authentication is required."""
    async with httpx.AsyncClient() as client:
        # No auth header
        response = await client.get(
            f"{openshift_mock_url}/apis/project.openshift.io/v1/projects"
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token(openshift_mock_url):
    """Test that invalid tokens are rejected."""
    headers = {"Authorization": "Bearer invalid-token"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{openshift_mock_url}/apis/project.openshift.io/v1/projects",
            headers=headers,
        )
        assert response.status_code == 401
