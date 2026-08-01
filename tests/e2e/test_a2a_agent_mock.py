"""E2E tests for A2A Agent mock server."""

import pytest
import httpx
import asyncio


@pytest.fixture
def a2a_agent_url():
    """A2A Agent mock server URL."""
    return "http://localhost:5006"


@pytest.fixture
def auth_headers():
    """Authentication headers with bearer token."""
    return {"Authorization": "Bearer mock-a2a-token-12345"}


@pytest.mark.asyncio
async def test_health_check(a2a_agent_url):
    """Test health check endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{a2a_agent_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "agent_id" in data


@pytest.mark.asyncio
async def test_get_agent_info(a2a_agent_url):
    """Test getting agent info from root endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{a2a_agent_url}/")
        assert response.status_code == 200
        data = response.json()
        assert "agent_id" in data
        assert "capabilities" in data
        assert isinstance(data["capabilities"], list)


@pytest.mark.asyncio
async def test_register_agent(a2a_agent_url, auth_headers):
    """Test registering an agent."""
    async with httpx.AsyncClient() as client:
        agent_data = {
            "id": "test-agent-001",
            "name": "Test Agent",
            "capabilities": ["test_capability"],
            "status": "active",
        }
        response = await client.post(
            f"{a2a_agent_url}/api/a2a/register",
            headers=auth_headers,
            json=agent_data,
        )
        assert response.status_code == 200
        data = response.json()
        assert "registered successfully" in data["message"]


@pytest.mark.asyncio
async def test_list_agents(a2a_agent_url, auth_headers):
    """Test listing all agents."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{a2a_agent_url}/api/a2a/agents",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert data["count"] >= 1  # At least the default agent


@pytest.mark.asyncio
async def test_get_agent(a2a_agent_url, auth_headers):
    """Test getting specific agent details."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{a2a_agent_url}/api/a2a/agents/mock-agent-001",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "mock-agent-001"
        assert "capabilities" in data


@pytest.mark.asyncio
async def test_get_agent_not_found(a2a_agent_url, auth_headers):
    """Test getting a non-existent agent."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{a2a_agent_url}/api/a2a/agents/nonexistent",
            headers=auth_headers,
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_delegate_task(a2a_agent_url, auth_headers):
    """Test delegating a task to the agent."""
    async with httpx.AsyncClient() as client:
        task_data = {
            "task_id": "test-task-001",
            "task_type": "log_analysis",
            "description": "Test task",
            "parameters": {"test": "data"},
            "priority": "normal",
        }
        response = await client.post(
            f"{a2a_agent_url}/api/a2a/delegate",
            headers=auth_headers,
            json=task_data,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test-task-001"
        assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_get_task_status(a2a_agent_url, auth_headers):
    """Test getting task status."""
    async with httpx.AsyncClient() as client:
        # First delegate a task
        task_data = {
            "task_id": "test-task-status-001",
            "task_type": "default",
            "description": "Test task",
            "parameters": {},
        }
        await client.post(
            f"{a2a_agent_url}/api/a2a/delegate",
            headers=auth_headers,
            json=task_data,
        )

        # Get task status
        response = await client.get(
            f"{a2a_agent_url}/api/a2a/tasks/test-task-status-001",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test-task-status-001"
        assert data["status"] in ["pending", "running", "completed"]


@pytest.mark.asyncio
async def test_task_execution(a2a_agent_url, auth_headers):
    """Test that task executes asynchronously."""
    async with httpx.AsyncClient() as client:
        # Delegate a task
        task_data = {
            "task_id": "test-exec-001",
            "task_type": "default",
            "description": "Test execution",
            "parameters": {},
        }
        await client.post(
            f"{a2a_agent_url}/api/a2a/delegate",
            headers=auth_headers,
            json=task_data,
        )

        # Wait for task to complete (default scenario takes 2s)
        await asyncio.sleep(3)

        # Check task status
        response = await client.get(
            f"{a2a_agent_url}/api/a2a/tasks/test-exec-001",
            headers=auth_headers,
        )
        data = response.json()
        assert data["status"] in ["completed", "failed"]
        if data["status"] == "completed":
            assert data["progress"] == 100
            assert data["result"] is not None


@pytest.mark.asyncio
async def test_list_tasks(a2a_agent_url, auth_headers):
    """Test listing all tasks."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{a2a_agent_url}/api/a2a/tasks",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert "count" in data


@pytest.mark.asyncio
async def test_list_tasks_by_status(a2a_agent_url, auth_headers):
    """Test listing tasks filtered by status."""
    async with httpx.AsyncClient() as client:
        # Delegate a task and complete it manually
        task_data = {
            "task_id": "test-filter-001",
            "task_type": "default",
            "description": "Test filter",
            "parameters": {},
        }
        await client.post(
            f"{a2a_agent_url}/api/a2a/delegate",
            headers=auth_headers,
            json=task_data,
        )

        await client.post(
            f"{a2a_agent_url}/api/a2a/tasks/test-filter-001/complete",
            headers=auth_headers,
            json={"status": "completed"},
        )

        # List completed tasks
        response = await client.get(
            f"{a2a_agent_url}/api/a2a/tasks?status=completed",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Should have at least the task we just completed
        assert data["count"] >= 1


@pytest.mark.asyncio
async def test_complete_task_manually(a2a_agent_url, auth_headers):
    """Test manually completing a task."""
    async with httpx.AsyncClient() as client:
        # Delegate a task
        task_data = {
            "task_id": "test-manual-complete-001",
            "task_type": "default",
            "description": "Manual completion test",
            "parameters": {},
        }
        await client.post(
            f"{a2a_agent_url}/api/a2a/delegate",
            headers=auth_headers,
            json=task_data,
        )

        # Manually complete it
        result_data = {"custom": "result"}
        response = await client.post(
            f"{a2a_agent_url}/api/a2a/tasks/test-manual-complete-001/complete",
            headers=auth_headers,
            json=result_data,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task"]["status"] == "completed"
        assert data["task"]["result"] == result_data


@pytest.mark.asyncio
async def test_fail_task_manually(a2a_agent_url, auth_headers):
    """Test manually failing a task."""
    async with httpx.AsyncClient() as client:
        # Delegate a task
        task_data = {
            "task_id": "test-manual-fail-001",
            "task_type": "default",
            "description": "Manual failure test",
            "parameters": {},
        }
        await client.post(
            f"{a2a_agent_url}/api/a2a/delegate",
            headers=auth_headers,
            json=task_data,
        )

        # Manually fail it
        response = await client.post(
            f"{a2a_agent_url}/api/a2a/tasks/test-manual-fail-001/fail",
            headers=auth_headers,
            json={"error": "Test error"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task"]["status"] == "failed"
        assert data["task"]["error"] == "Test error"


@pytest.mark.asyncio
async def test_delete_task(a2a_agent_url, auth_headers):
    """Test deleting a task."""
    async with httpx.AsyncClient() as client:
        # Delegate a task
        task_data = {
            "task_id": "test-delete-001",
            "task_type": "default",
            "description": "Delete test",
            "parameters": {},
        }
        await client.post(
            f"{a2a_agent_url}/api/a2a/delegate",
            headers=auth_headers,
            json=task_data,
        )

        # Delete it
        response = await client.delete(
            f"{a2a_agent_url}/api/a2a/tasks/test-delete-001",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Verify it's deleted
        response = await client.get(
            f"{a2a_agent_url}/api/a2a/tasks/test-delete-001",
            headers=auth_headers,
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_task_with_callback(a2a_agent_url, auth_headers):
    """Test task with callback URL."""
    async with httpx.AsyncClient() as client:
        # Delegate task with callback
        task_data = {
            "task_id": "test-callback-001",
            "task_type": "default",
            "description": "Callback test",
            "parameters": {},
            "callback_url": "http://example.com/callback",
        }
        response = await client.post(
            f"{a2a_agent_url}/api/a2a/delegate",
            headers=auth_headers,
            json=task_data,
        )
        assert response.status_code == 200

        # Note: Webhook will be sent but may fail (example.com won't accept it)
        # This is expected in testing


@pytest.mark.asyncio
async def test_different_task_types(a2a_agent_url, auth_headers):
    """Test different task types."""
    async with httpx.AsyncClient() as client:
        task_types = [
            "log_analysis",
            "kubernetes_operations",
            "root_cause_analysis",
            "anomaly_detection",
        ]

        for task_type in task_types:
            task_data = {
                "task_id": f"test-{task_type}-001",
                "task_type": task_type,
                "description": f"Test {task_type}",
                "parameters": {},
            }
            response = await client.post(
                f"{a2a_agent_url}/api/a2a/delegate",
                headers=auth_headers,
                json=task_data,
            )
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_task_not_found(a2a_agent_url, auth_headers):
    """Test getting a non-existent task."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{a2a_agent_url}/api/a2a/tasks/nonexistent-task",
            headers=auth_headers,
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_authentication_required(a2a_agent_url):
    """Test that authentication is required."""
    async with httpx.AsyncClient() as client:
        # No auth header
        response = await client.get(f"{a2a_agent_url}/api/a2a/agents")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token(a2a_agent_url):
    """Test that invalid tokens are rejected."""
    headers = {"Authorization": "Bearer invalid-token"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{a2a_agent_url}/api/a2a/agents",
            headers=headers,
        )
        assert response.status_code == 401
