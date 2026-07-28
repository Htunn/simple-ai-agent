"""E2E tests for VMware vCenter mock server."""

import pytest
import httpx
import base64


@pytest.fixture
def vmware_mock_url():
    """VMware mock server URL."""
    return "http://localhost:5002"


@pytest.fixture
async def session_token(vmware_mock_url):
    """Create a session and return the token."""
    credentials = base64.b64encode(
        b"administrator@vsphere.local:password"
    ).decode("utf-8")
    headers = {"Authorization": f"Basic {credentials}"}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{vmware_mock_url}/rest/com/vmware/cis/session",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        return data["value"]


@pytest.mark.asyncio
async def test_health_check(vmware_mock_url):
    """Test health check endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{vmware_mock_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "vms_count" in data
        assert "hosts_count" in data


@pytest.mark.asyncio
async def test_create_session(vmware_mock_url):
    """Test session creation (login)."""
    credentials = base64.b64encode(
        b"administrator@vsphere.local:password"
    ).decode("utf-8")
    headers = {"Authorization": f"Basic {credentials}"}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{vmware_mock_url}/rest/com/vmware/cis/session",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "value" in data
        assert len(data["value"]) > 0  # Session token returned


@pytest.mark.asyncio
async def test_delete_session(vmware_mock_url, session_token):
    """Test session deletion (logout)."""
    headers = {"vmware-api-session-id": session_token}

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{vmware_mock_url}/rest/com/vmware/cis/session",
            headers=headers,
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_vms(vmware_mock_url, session_token):
    """Test listing VMs."""
    headers = {"vmware-api-session-id": session_token}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{vmware_mock_url}/rest/vcenter/vm",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "value" in data
        assert len(data["value"]) >= 4  # At least 4 VMs from fixtures


@pytest.mark.asyncio
async def test_get_vm(vmware_mock_url, session_token):
    """Test getting a specific VM."""
    headers = {"vmware-api-session-id": session_token}
    vm_id = "vm-1001"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{vmware_mock_url}/rest/vcenter/vm/{vm_id}",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["value"]["vm"] == vm_id
        assert data["value"]["name"] == "production-api-01"
        assert data["value"]["power_state"] == "POWERED_ON"


@pytest.mark.asyncio
async def test_get_vm_not_found(vmware_mock_url, session_token):
    """Test getting a non-existent VM."""
    headers = {"vmware-api-session-id": session_token}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{vmware_mock_url}/rest/vcenter/vm/nonexistent",
            headers=headers,
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_start_vm(vmware_mock_url, session_token):
    """Test powering on a VM."""
    headers = {"vmware-api-session-id": session_token}
    vm_id = "vm-1003"  # staging-web-01 (POWERED_OFF)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{vmware_mock_url}/rest/vcenter/vm/{vm_id}/power/start",
            headers=headers,
            json={},
        )
        assert response.status_code == 200

        # Verify power state changed
        response = await client.get(
            f"{vmware_mock_url}/rest/vcenter/vm/{vm_id}",
            headers=headers,
        )
        data = response.json()
        assert data["value"]["power_state"] == "POWERED_ON"


@pytest.mark.asyncio
async def test_stop_vm(vmware_mock_url, session_token):
    """Test powering off a VM."""
    headers = {"vmware-api-session-id": session_token}
    vm_id = "vm-1001"  # production-api-01 (POWERED_ON)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{vmware_mock_url}/rest/vcenter/vm/{vm_id}/power/stop",
            headers=headers,
            json={},
        )
        assert response.status_code == 200

        # Verify power state changed
        response = await client.get(
            f"{vmware_mock_url}/rest/vcenter/vm/{vm_id}",
            headers=headers,
        )
        data = response.json()
        assert data["value"]["power_state"] == "POWERED_OFF"


@pytest.mark.asyncio
async def test_reset_vm(vmware_mock_url, session_token):
    """Test resetting a VM."""
    headers = {"vmware-api-session-id": session_token}
    vm_id = "vm-1004"  # dev-test-vm (POWERED_ON)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{vmware_mock_url}/rest/vcenter/vm/{vm_id}/power/reset",
            headers=headers,
            json={},
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_hosts(vmware_mock_url, session_token):
    """Test listing hosts."""
    headers = {"vmware-api-session-id": session_token}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{vmware_mock_url}/rest/vcenter/host",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["value"]) >= 3  # At least 3 hosts


@pytest.mark.asyncio
async def test_get_host(vmware_mock_url, session_token):
    """Test getting host details."""
    headers = {"vmware-api-session-id": session_token}
    host_id = "host-10"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{vmware_mock_url}/rest/vcenter/host/{host_id}",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["value"]["host"] == host_id
        assert data["value"]["name"] == "esxi-prod-01.example.com"
        assert data["value"]["connection_state"] == "CONNECTED"


@pytest.mark.asyncio
async def test_disconnect_host(vmware_mock_url, session_token):
    """Test disconnecting a host."""
    headers = {"vmware-api-session-id": session_token}
    host_id = "host-12"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{vmware_mock_url}/rest/vcenter/host/{host_id}/disconnect",
            headers=headers,
        )
        assert response.status_code == 200

        # Verify connection state changed
        response = await client.get(
            f"{vmware_mock_url}/rest/vcenter/host/{host_id}",
            headers=headers,
        )
        data = response.json()
        assert data["value"]["connection_state"] == "DISCONNECTED"


@pytest.mark.asyncio
async def test_list_datastores(vmware_mock_url, session_token):
    """Test listing datastores."""
    headers = {"vmware-api-session-id": session_token}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{vmware_mock_url}/rest/vcenter/datastore",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["value"]) >= 3  # At least 3 datastores


@pytest.mark.asyncio
async def test_get_datastore(vmware_mock_url, session_token):
    """Test getting datastore details."""
    headers = {"vmware-api-session-id": session_token}
    ds_id = "datastore-20"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{vmware_mock_url}/rest/vcenter/datastore/{ds_id}",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["value"]["datastore"] == ds_id
        assert data["value"]["name"] == "production-ssd-01"
        assert data["value"]["type"] == "VMFS"


@pytest.mark.asyncio
async def test_list_clusters(vmware_mock_url, session_token):
    """Test listing clusters."""
    headers = {"vmware-api-session-id": session_token}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{vmware_mock_url}/rest/vcenter/cluster",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["value"]) >= 2  # At least 2 clusters


@pytest.mark.asyncio
async def test_delete_vm(vmware_mock_url, session_token):
    """Test deleting a VM."""
    headers = {"vmware-api-session-id": session_token}
    vm_id = "vm-1002"  # production-db-01

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{vmware_mock_url}/rest/vcenter/vm/{vm_id}",
            headers=headers,
        )
        assert response.status_code == 200

        # Verify VM is deleted
        response = await client.get(
            f"{vmware_mock_url}/rest/vcenter/vm/{vm_id}",
            headers=headers,
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_authentication_required(vmware_mock_url):
    """Test that authentication is required."""
    async with httpx.AsyncClient() as client:
        # No session token
        response = await client.get(f"{vmware_mock_url}/rest/vcenter/vm")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_session(vmware_mock_url):
    """Test that invalid session tokens are rejected."""
    headers = {"vmware-api-session-id": "invalid-token"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{vmware_mock_url}/rest/vcenter/vm",
            headers=headers,
        )
        assert response.status_code == 401
