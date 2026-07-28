#!/usr/bin/env python3
"""Test platform authentication against real or mock servers.

Usage:
    # Test against mock servers
    python scripts/test_platform_auth.py
    
    # Test against real platforms
    export USE_REAL_PLATFORMS=true
    python scripts/test_platform_auth.py
"""
import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.platforms import NutanixClient, VMwareClient, OpenShiftClient
from src.k8s.client import KubernetesClient


async def test_nutanix_auth():
    """Test Nutanix authentication."""
    print("\n🔐 Testing Nutanix Prism Central Authentication...")
    
    try:
        host = os.getenv("NUTANIX_HOST", "localhost")
        port = int(os.getenv("NUTANIX_PORT", "5001"))
        api_key = os.getenv("NUTANIX_API_KEY")
        username = os.getenv("NUTANIX_USERNAME", "admin")
        password = os.getenv("NUTANIX_PASSWORD", "password")
        verify_ssl = os.getenv("NUTANIX_VERIFY_SSL", "false").lower() == "true"
        
        print(f"   Host: {host}:{port}")
        print(f"   Auth: {'API Key' if api_key else 'Basic Auth'}")
        
        client = NutanixClient(
            host=host,
            port=port,
            api_key=api_key,
            username=username if not api_key else None,
            password=password if not api_key else None,
            verify_ssl=verify_ssl
        )
        
        health = await client.health_check()
        print(f"   Status: {health.status}")
        
        # Try listing VMs
        vms = await client.list_vms()
        print(f"   VMs: {len(vms)} found")
        
        print("   ✅ Nutanix authentication successful!")
        return True
        
    except Exception as e:
        print(f"   ❌ Nutanix authentication failed: {e}")
        return False


async def test_vmware_auth():
    """Test VMware vCenter authentication."""
    print("\n🔐 Testing VMware vCenter Authentication...")
    
    try:
        host = os.getenv("VCENTER_HOST", "localhost")
        port = int(os.getenv("VCENTER_PORT", "5002"))
        username = os.getenv("VCENTER_USERNAME", "administrator@vsphere.local")
        password = os.getenv("VCENTER_PASSWORD", "password")
        verify_ssl = os.getenv("VCENTER_VERIFY_SSL", "false").lower() == "true"
        
        print(f"   Host: {host}:{port}")
        print(f"   Username: {username}")
        
        client = VMwareClient(
            host=host,
            port=port,
            username=username,
            password=password,
            verify_ssl=verify_ssl
        )
        
        health = await client.health_check()
        print(f"   Status: {health.status}")
        
        # Try listing VMs
        vms = await client.list_vms()
        print(f"   VMs: {len(vms)} found")
        
        print("   ✅ VMware authentication successful!")
        return True
        
    except Exception as e:
        print(f"   ❌ VMware authentication failed: {e}")
        return False


async def test_kubernetes_auth():
    """Test Kubernetes authentication."""
    print("\n🔐 Testing Kubernetes Authentication...")
    
    try:
        host = os.getenv("K8S_HOST", "http://localhost:5004")
        token = os.getenv("K8S_TOKEN", "mock-bearer-token-12345")
        verify_ssl = os.getenv("K8S_VERIFY_SSL", "false").lower() == "true"
        
        print(f"   Host: {host}")
        print(f"   Auth: Bearer Token")
        
        client = KubernetesClient(
            host=host,
            token=token,
            verify_ssl=verify_ssl
        )
        
        health = await client.health_check()
        print(f"   Status: {health.status}")
        
        # Try listing namespaces
        namespaces = await client.list_namespaces()
        print(f"   Namespaces: {len(namespaces)} found")
        
        # Try listing pods
        pods = await client.list_pods()
        print(f"   Pods: {len(pods)} found")
        
        print("   ✅ Kubernetes authentication successful!")
        return True
        
    except Exception as e:
        print(f"   ❌ Kubernetes authentication failed: {e}")
        return False


async def test_openshift_auth():
    """Test OpenShift authentication."""
    print("\n🔐 Testing OpenShift Authentication...")
    
    try:
        host = os.getenv("OPENSHIFT_HOST", "http://localhost:5003")
        token = os.getenv("OPENSHIFT_TOKEN", "mock-openshift-token-12345")
        verify_ssl = os.getenv("OPENSHIFT_VERIFY_SSL", "false").lower() == "true"
        
        print(f"   Host: {host}")
        print(f"   Auth: OAuth Token")
        
        client = OpenShiftClient(
            host=host,
            token=token,
            verify_ssl=verify_ssl
        )
        
        health = await client.health_check()
        print(f"   Status: {health.status}")
        
        # Try listing projects
        projects = await client.list_projects()
        print(f"   Projects: {len(projects)} found")
        
        print("   ✅ OpenShift authentication successful!")
        return True
        
    except Exception as e:
        print(f"   ❌ OpenShift authentication failed: {e}")
        return False


async def main():
    """Run all authentication tests."""
    use_real = os.getenv("USE_REAL_PLATFORMS", "false").lower() == "true"
    
    print("=" * 70)
    print("  Platform Authentication Test")
    print("=" * 70)
    
    if use_real:
        print("\n⚠️  Testing against REAL platforms")
        print("   Make sure credentials are set in environment variables")
    else:
        print("\n🧪 Testing against MOCK servers (default)")
        print("   Set USE_REAL_PLATFORMS=true to test real platforms")
    
    results = await asyncio.gather(
        test_nutanix_auth(),
        test_vmware_auth(),
        test_kubernetes_auth(),
        test_openshift_auth(),
        return_exceptions=False
    )
    
    print("\n" + "=" * 70)
    print("  Summary")
    print("=" * 70)
    
    platforms = ["Nutanix", "VMware", "Kubernetes", "OpenShift"]
    for platform, result in zip(platforms, results):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {platform:15} {status}")
    
    print("=" * 70)
    
    if all(results):
        print("\n✅ All platform authentications successful!")
        return 0
    else:
        print("\n❌ Some platform authentications failed")
        print("\nTroubleshooting:")
        print("  1. Check environment variables are set correctly")
        print("  2. Verify platform mock servers are running: make start-platform-mocks")
        print("  3. Check connectivity: curl http://localhost:5001/health")
        print("  4. Review logs for detailed error messages")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
