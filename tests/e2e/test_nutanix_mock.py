"""E2E tests for Nutanix mock server."""

import pytest
import httpx
import base64


@pytest.fixture
def nutanix_mock_url():
    """Nutanix mock server URL."""
    return "http://localhost:5001"


@pytest.fixture
def auth_headers():
    """Basic authentication headers for mock server."""
    credentials = base64.b64encode(b"admin:password").decode("utf-8")
    return {"Authorization": f"Basic {credentials}"}


@pytest.mark.asyncio
async def test_health_check(nutanix_mock_url):
    """Test health check endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{nutanix_mock_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "vms_count" in data
        assert "clusters_count" in data


@pytest.mark.asyncio
async def test_list_vms(nutanix_mock_url, auth_headers):
    """Test listing VMs."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{nutanix_mock_url}/api/nutanix/v3/vms/list",
            headers=auth_headers,
            json={"kind": "vm", "length": 20, "offset": 0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["api_version"] == "3.1"
        assert data["metadata"]["kind"] == "list"
        assert len(data["entities"]) >= 3  # At least 3 VMs from fixtures


@pytest.mark.asyncio
async def test_get_vm(nutanix_mock_url, auth_headers):
    """Test getting a specific VM."""
    vm_uuid = "11111111-1111-1111-1111-111111111111"
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{nutanix_mock_url}/api/nutanix/v3/vms/{vm_uuid}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["uuid"] == vm_uuid
        assert data["metadata"]["name"] == "api-server-01"
        assert data["status"]["resources"]["power_state"] == "ON"


@pytest.mark.asyncio
async def test_get_vm_not_found(nutanix_mock_url, auth_headers):
    """Test getting a non-existent VM."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{nutanix_mock_url}/api/nutanix/v3/vms/nonexistent-uuid",
            headers=auth_headers,
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_power_on_vm(nutanix_mock_url, auth_headers):
    """Test powering on a VM."""
    vm_uuid = "33333333-3333-3333-3333-333333333333"  # test-vm-staging (OFF)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{nutanix_mock_url}/api/nutanix/v3/vms/{vm_uuid}/set_power_state",
            headers=auth_headers,
            json={"transition": "ON"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "task_uuid" in data
        assert data["status"] == "QUEUED"

        # Verify power state changed
        response = await client.get(
            f"{nutanix_mock_url}/api/nutanix/v3/vms/{vm_uuid}",
            headers=auth_headers,
        )
        data = response.json()
        assert data["status"]["resources"]["power_state"] == "ON"


@pytest.mark.asyncio
async def test_power_off_vm(nutanix_mock_url, auth_headers):
    """Test powering off a VM."""
    vm_uuid = "11111111-1111-1111-1111-111111111111"  # api-server-01 (ON)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{nutanix_mock_url}/api/nutanix/v3/vms/{vm_uuid}/set_power_state",
            headers=auth_headers,
            json={"transition": "OFF"},
        )
        assert response.status_code == 200

        # Verify power state changed
        response = await client.get(
            f"{nutanix_mock_url}/api/nutanix/v3/vms/{vm_uuid}",
            headers=auth_headers,
        )
        data = response.json()
        assert data["status"]["resources"]["power_state"] == "OFF"


@pytest.mark.asyncio
async def test_invalid_power_transition(nutanix_mock_url, auth_headers):
    """Test invalid power state transition."""
    vm_uuid = "11111111-1111-1111-1111-111111111111"
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{nutanix_mock_url}/api/nutanix/v3/vms/{vm_uuid}/set_power_state",
            headers=auth_headers,
            json={"transition": "INVALID"},
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_clusters(nutanix_mock_url, auth_headers):
    """Test listing clusters."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{nutanix_mock_url}/api/nutanix/v3/clusters/list",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["kind"] == "list"
        assert len(data["entities"]) >= 2  # At least 2 clusters


@pytest.mark.asyncio
async def test_get_cluster(nutanix_mock_url, auth_headers):
    """Test getting cluster details."""
    cluster_uuid = "cluster-1111-1111-1111-111111111111"
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{nutanix_mock_url}/api/nutanix/v3/clusters/{cluster_uuid}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["name"] == "production-cluster"
        assert data["status"]["resources"]["analysis"]["vm_count"] == 25


@pytest.mark.asyncio
async def test_list_hosts(nutanix_mock_url, auth_headers):
    """Test listing hosts."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{nutanix_mock_url}/api/nutanix/v3/hosts/list",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["entities"]) >= 3  # At least 3 hosts


@pytest.mark.asyncio
async def test_list_storage_containers(nutanix_mock_url, auth_headers):
    """Test listing storage containers."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{nutanix_mock_url}/api/nutanix/v3/storage_containers/list",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["entities"]) >= 2  # At least 2 containers


@pytest.mark.asyncio
async def test_get_storage_container_stats(nutanix_mock_url, auth_headers):
    """Test getting storage container statistics."""
    container_uuid = "storage-1111-1111-1111-111111111111"
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{nutanix_mock_url}/api/nutanix/v3/storage_containers/{container_uuid}/stats",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "stats" in data
        assert "controller_avg_io_latency_usecs" in data["stats"]
        assert "controller_num_iops" in data["stats"]


@pytest.mark.asyncio
async def test_delete_vm(nutanix_mock_url, auth_headers):
    """Test deleting a VM."""
    vm_uuid = "22222222-2222-2222-2222-222222222222"  # database-01
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{nutanix_mock_url}/api/nutanix/v3/vms/{vm_uuid}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"]["state"] == "DELETE_PENDING"

        # Verify VM is deleted
        response = await client.get(
            f"{nutanix_mock_url}/api/nutanix/v3/vms/{vm_uuid}",
            headers=auth_headers,
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_authentication_required(nutanix_mock_url):
    """Test that authentication is required."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{nutanix_mock_url}/api/nutanix/v3/vms/list",
            json={"kind": "vm"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_credentials(nutanix_mock_url):
    """Test that invalid credentials are rejected."""
    credentials = base64.b64encode(b"wrong:wrong").decode("utf-8")
    headers = {"Authorization": f"Basic {credentials}"}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{nutanix_mock_url}/api/nutanix/v3/vms/list",
            headers=headers,
            json={"kind": "vm"},
        )
        assert response.status_code == 401
