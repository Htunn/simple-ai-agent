"""
Unit tests for platform clients.

Tests platform client implementations against mock servers.
These tests verify the client abstraction layer works correctly
with all supported platforms.
"""

import pytest

from src.platforms import (
    NutanixClient,
    OpenShiftClient,
    PlatformConfig,
    PlatformFactory,
    PlatformType,
    VMwareClient,
)


class TestPlatformFactory:
    """Test platform factory functionality."""

    def test_create_nutanix_client(self):
        """Test creating Nutanix client through factory."""
        config = PlatformConfig(
            platform_type=PlatformType.NUTANIX,
            endpoint="http://localhost:5001",
            username="admin",
            password="password",
            verify_ssl=False,
        )

        client = PlatformFactory.create_client(config)
        assert isinstance(client, NutanixClient)
        assert client.platform_type == PlatformType.NUTANIX

    def test_create_vmware_client(self):
        """Test creating VMware client through factory."""
        config = PlatformConfig(
            platform_type=PlatformType.VMWARE,
            endpoint="http://localhost:5002",
            username="admin",
            password="password",
            verify_ssl=False,
        )

        client = PlatformFactory.create_client(config)
        assert isinstance(client, VMwareClient)
        assert client.platform_type == PlatformType.VMWARE

    def test_create_openshift_client(self):
        """Test creating OpenShift client through factory."""
        config = PlatformConfig(
            platform_type=PlatformType.OPENSHIFT,
            endpoint="http://localhost:5003",
            token="test-token",
            verify_ssl=False,
        )

        client = PlatformFactory.create_client(config)
        assert isinstance(client, OpenShiftClient)
        assert client.platform_type == PlatformType.OPENSHIFT

    def test_unsupported_platform_raises_error(self):
        """Test that unsupported platform type raises error."""
        config = PlatformConfig(
            platform_type="unsupported",  # type: ignore
            endpoint="http://localhost:9999",
            username="admin",
            password="password",
        )

        with pytest.raises(ValueError, match="Unsupported platform type"):
            PlatformFactory.create_client(config)

    def test_get_supported_platforms(self):
        """Test getting list of supported platforms."""
        platforms = PlatformFactory.get_supported_platforms()
        
        assert PlatformType.NUTANIX in platforms
        assert PlatformType.VMWARE in platforms
        assert PlatformType.OPENSHIFT in platforms

    def test_is_platform_supported(self):
        """Test checking if platform is supported."""
        assert PlatformFactory.is_platform_supported(PlatformType.NUTANIX)
        assert PlatformFactory.is_platform_supported(PlatformType.VMWARE)
        assert PlatformFactory.is_platform_supported(PlatformType.OPENSHIFT)


class TestNutanixClient:
    """Test Nutanix client against mock server."""

    @pytest.fixture
    async def client(self):
        """Create and initialize Nutanix client."""
        config = PlatformConfig(
            platform_type=PlatformType.NUTANIX,
            endpoint="http://localhost:5001",
            username="admin",
            password="password",
            verify_ssl=False,
        )
        
        client = NutanixClient(config)
        await client.initialize()
        yield client
        await client.close()

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check returns healthy status."""
        health = await client.health_check()
        
        assert health.platform == "nutanix"
        assert health.status == "healthy"
        assert health.response_time_ms is not None

    @pytest.mark.asyncio
    async def test_list_vms(self, client):
        """Test listing VMs."""
        vms = await client.list_vms()
        
        assert len(vms) > 0
        assert all(vm.platform == "nutanix" for vm in vms)
        assert all(vm.id for vm in vms)
        assert all(vm.name for vm in vms)

    @pytest.mark.asyncio
    async def test_get_vm(self, client):
        """Test getting specific VM details."""
        # First get list of VMs
        vms = await client.list_vms()
        assert len(vms) > 0
        
        # Get details of first VM
        vm = await client.get_vm(vms[0].id)
        
        assert vm.id == vms[0].id
        assert vm.name == vms[0].name
        assert vm.power_state in ("running", "stopped", "suspended", "unknown")
        assert vm.platform == "nutanix"

    @pytest.mark.asyncio
    async def test_start_stop_vm(self, client):
        """Test VM power operations."""
        # Get a stopped VM (from mock fixtures)
        vms = await client.list_vms()
        stopped_vm = next((vm for vm in vms if not vm.is_running()), None)
        
        if stopped_vm:
            # Start VM
            result = await client.start_vm(stopped_vm.id)
            assert result is True
            
            # Stop VM
            result = await client.stop_vm(stopped_vm.id)
            assert result is True

    @pytest.mark.asyncio
    async def test_list_hosts(self, client):
        """Test listing hosts."""
        hosts = await client.list_hosts()
        
        assert len(hosts) > 0
        assert all(host.platform == "nutanix" for host in hosts)
        assert all(host.id for host in hosts)
        assert all(host.name for host in hosts)

    @pytest.mark.asyncio
    async def test_list_clusters(self, client):
        """Test listing clusters."""
        clusters = await client.list_clusters()
        
        assert len(clusters) > 0
        assert all("id" in cluster for cluster in clusters)
        assert all("name" in cluster for cluster in clusters)


class TestVMwareClient:
    """Test VMware client against mock server."""

    @pytest.fixture
    async def client(self):
        """Create and initialize VMware client."""
        config = PlatformConfig(
            platform_type=PlatformType.VMWARE,
            endpoint="http://localhost:5002",
            username="admin",
            password="password",
            verify_ssl=False,
        )
        
        client = VMwareClient(config)
        await client.initialize()
        yield client
        await client.close()

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check returns healthy status."""
        health = await client.health_check()
        
        assert health.platform == "vmware"
        assert health.status == "healthy"

    @pytest.mark.asyncio
    async def test_session_management(self, client):
        """Test session creation and deletion."""
        # Session should be created during initialization
        assert client._session_id is not None
        
        # Close should delete session
        await client.close()
        assert client._session_id is None

    @pytest.mark.asyncio
    async def test_list_vms(self, client):
        """Test listing VMs."""
        vms = await client.list_vms()
        
        assert len(vms) > 0
        assert all(vm.platform == "vmware" for vm in vms)

    @pytest.mark.asyncio
    async def test_get_vm(self, client):
        """Test getting specific VM details."""
        vms = await client.list_vms()
        assert len(vms) > 0
        
        vm = await client.get_vm(vms[0].id)
        
        assert vm.id == vms[0].id
        assert vm.platform == "vmware"

    @pytest.mark.asyncio
    async def test_vm_power_operations(self, client):
        """Test VM power operations."""
        vms = await client.list_vms()
        stopped_vm = next((vm for vm in vms if not vm.is_running()), None)
        
        if stopped_vm:
            # Start VM
            result = await client.start_vm(stopped_vm.id)
            assert result is True

    @pytest.mark.asyncio
    async def test_list_hosts(self, client):
        """Test listing hosts."""
        hosts = await client.list_hosts()
        
        assert len(hosts) > 0
        assert all(host.platform == "vmware" for host in hosts)

    @pytest.mark.asyncio
    async def test_list_clusters(self, client):
        """Test listing clusters."""
        clusters = await client.list_clusters()
        
        assert len(clusters) > 0
        assert all("id" in cluster for cluster in clusters)


class TestOpenShiftClient:
    """Test OpenShift client against mock server."""

    @pytest.fixture
    async def client(self):
        """Create and initialize OpenShift client."""
        config = PlatformConfig(
            platform_type=PlatformType.OPENSHIFT,
            endpoint="http://localhost:5003",
            token="test-token",
            verify_ssl=False,
        )
        
        client = OpenShiftClient(config)
        await client.initialize()
        yield client
        await client.close()

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check returns healthy status."""
        health = await client.health_check()
        
        assert health.platform == "openshift"
        assert health.status == "healthy"

    @pytest.mark.asyncio
    async def test_list_projects(self, client):
        """Test listing OpenShift projects."""
        projects = await client.list_projects()
        
        assert len(projects) > 0
        assert all("name" in project for project in projects)

    @pytest.mark.asyncio
    async def test_get_project(self, client):
        """Test getting project details."""
        projects = await client.list_projects()
        assert len(projects) > 0
        
        project = await client.get_project(projects[0]["name"])
        
        assert project["name"] == projects[0]["name"]

    @pytest.mark.asyncio
    async def test_list_routes(self, client):
        """Test listing routes in a namespace."""
        # Use production namespace from mock fixtures
        routes = await client.list_routes("production")
        
        assert isinstance(routes, list)
        # May be empty if no routes in namespace

    @pytest.mark.asyncio
    async def test_list_buildconfigs(self, client):
        """Test listing buildconfigs in a namespace."""
        buildconfigs = await client.list_buildconfigs("production")
        
        assert isinstance(buildconfigs, list)

    @pytest.mark.asyncio
    async def test_list_builds(self, client):
        """Test listing builds in a namespace."""
        builds = await client.list_builds("production")
        
        assert isinstance(builds, list)

    @pytest.mark.asyncio
    async def test_list_imagestreams(self, client):
        """Test listing imagestreams in a namespace."""
        imagestreams = await client.list_imagestreams("production")
        
        assert isinstance(imagestreams, list)

    @pytest.mark.asyncio
    async def test_list_hosts(self, client):
        """Test listing nodes (hosts)."""
        hosts = await client.list_hosts()
        
        assert isinstance(hosts, list)
        # OpenShift mock should have nodes
        assert len(hosts) > 0
        assert all(host.platform == "openshift" for host in hosts)


class TestPlatformConfigValidation:
    """Test platform configuration validation."""

    def test_config_requires_endpoint(self):
        """Test that endpoint is required."""
        with pytest.raises(ValueError, match="endpoint is required"):
            PlatformConfig(
                platform_type=PlatformType.NUTANIX,
                endpoint="",
                username="admin",
                password="password",
            )

    def test_config_requires_auth(self):
        """Test that auth credentials are required."""
        with pytest.raises(ValueError, match="token or username/password"):
            PlatformConfig(
                platform_type=PlatformType.NUTANIX,
                endpoint="http://localhost:5001",
            )

    def test_config_with_token(self):
        """Test configuration with token auth."""
        config = PlatformConfig(
            platform_type=PlatformType.OPENSHIFT,
            endpoint="http://localhost:5003",
            token="test-token",
        )
        
        assert config.token == "test-token"
        assert config.username is None
        assert config.password is None

    def test_config_with_username_password(self):
        """Test configuration with username/password auth."""
        config = PlatformConfig(
            platform_type=PlatformType.NUTANIX,
            endpoint="http://localhost:5001",
            username="admin",
            password="secret",
        )
        
        assert config.username == "admin"
        assert config.password == "secret"
        assert config.token is None
